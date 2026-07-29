from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from app.handlers.common import report_keyboard, result_text
from app.keyboards import START_TEST, main_menu
from app.services.assessment import Question, questions_in_order, shuffled_questions, summarize
from app.services.results import ResultsRepository


router = Router()
LETTERS = "ABCD"


class Assessment(StatesGroup):
    answering = State()
    stopping = State()


def answer_keyboard(index: int, question: Question) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=letter, callback_data=f"answer:{index}:{option_id}")
         for option_id, letter in enumerate(LETTERS)],
        [InlineKeyboardButton(text="⏸ Прервать тестирование", callback_data="test:stop")],
    ])


def stop_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💾 Сохранить ответы", callback_data="test:save")],
        [InlineKeyboardButton(text="🗑 Удалить ответы", callback_data="test:delete")],
        [InlineKeyboardButton(text="↩️ Продолжить тест", callback_data="test:continue")],
    ])


def question_text(index: int, questions: tuple[Question, ...]) -> str:
    question = questions[index]
    context = f"{question.context}\n\n" if question.context else ""
    options = "\n".join(f"{letter}. {text}" for letter, text in zip(LETTERS, question.options))
    return (
        f"Вопрос {index + 1} из {len(questions)} · {question.level} · {question.topic}\n\n"
        f"{context}{question.text}\n\n{options}"
    )


@router.message(F.text == START_TEST)
@router.message(Command("assessment"))
async def begin_assessment(message: Message, state: FSMContext,
                           questions: tuple[Question, ...],
                           results_repository: ResultsRepository) -> None:
    draft = results_repository.load_draft(message.from_user.id)
    saved_answers = draft.answers if draft else []
    try:
        ordered_questions = questions_in_order(questions, draft.question_ids) if draft else shuffled_questions(questions)
    except ValueError:
        results_repository.delete_draft(message.from_user.id)
        saved_answers = []
        ordered_questions = shuffled_questions(questions)
    if len(saved_answers) >= len(ordered_questions) or any(value not in range(4) for value in saved_answers):
        results_repository.delete_draft(message.from_user.id)
        saved_answers = []
        ordered_questions = shuffled_questions(questions)
    question_ids = [question.id for question in ordered_questions]
    index = len(saved_answers)
    await state.set_state(Assessment.answering)
    await state.set_data({
        "answers": saved_answers,
        "question_index": index,
        "question_ids": question_ids,
    })
    prefix = f"Продолжаем сохранённый тест с вопроса {index + 1}.\n\n" if saved_answers else ""
    await message.answer(
        prefix + question_text(index, ordered_questions),
        reply_markup=answer_keyboard(index, ordered_questions[index]),
    )


@router.message(Command("cancel"))
async def cancel_assessment(message: Message, state: FSMContext,
                            admin_user_ids: frozenset[int]) -> None:
    if await state.get_state() is None:
        await message.answer(
            "Сейчас нет активного тестирования.",
            reply_markup=main_menu(message.from_user.id, admin_user_ids),
        )
        return
    await state.set_state(Assessment.stopping)
    await message.answer("Сохранить уже выбранные ответы для продолжения позже?", reply_markup=stop_keyboard())


@router.callback_query(Assessment.answering, F.data == "test:stop")
async def request_stop(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(Assessment.stopping)
    await callback.answer()
    if callback.message is not None:
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.answer(
            "Сохранить уже выбранные ответы для продолжения позже?",
            reply_markup=stop_keyboard(),
        )


@router.callback_query(Assessment.stopping, F.data == "test:save")
async def save_and_stop(callback: CallbackQuery, state: FSMContext,
                        results_repository: ResultsRepository,
                        admin_user_ids: frozenset[int]) -> None:
    data = await state.get_data()
    answers = data.get("answers", [])
    results_repository.save_draft(
        callback.from_user.id,
        answers,
        data.get("question_ids", []),
    )
    await state.clear()
    await callback.answer("Прогресс сохранён")
    if callback.message is not None:
        await callback.message.edit_text(
            f"Тестирование приостановлено. Сохранено ответов: {len(answers)}.\n"
            "В следующий раз тест продолжится автоматически."
        )
        await callback.message.answer(
            "Главное меню:",
            reply_markup=main_menu(callback.from_user.id, admin_user_ids),
        )


@router.callback_query(Assessment.stopping, F.data == "test:delete")
async def delete_and_stop(callback: CallbackQuery, state: FSMContext,
                          results_repository: ResultsRepository,
                          admin_user_ids: frozenset[int]) -> None:
    results_repository.delete_draft(callback.from_user.id)
    await state.clear()
    await callback.answer("Ответы удалены")
    if callback.message is not None:
        await callback.message.edit_text("Тестирование прекращено. Все ответы текущей попытки удалены.")
        await callback.message.answer(
            "Главное меню:",
            reply_markup=main_menu(callback.from_user.id, admin_user_ids),
        )


@router.callback_query(Assessment.stopping, F.data == "test:continue")
async def continue_test(callback: CallbackQuery, state: FSMContext,
                        questions: tuple[Question, ...]) -> None:
    data = await state.get_data()
    index = data.get("question_index", 0)
    ordered_questions = questions_in_order(questions, data.get("question_ids", []))
    await state.set_state(Assessment.answering)
    await callback.answer()
    if callback.message is not None:
        await callback.message.edit_text(
            question_text(index, ordered_questions),
            reply_markup=answer_keyboard(index, ordered_questions[index]),
        )


@router.callback_query(Assessment.answering, F.data.startswith("answer:"))
async def accept_answer(callback: CallbackQuery, state: FSMContext,
                        questions: tuple[Question, ...],
                        results_repository: ResultsRepository,
                        admin_user_ids: frozenset[int]) -> None:
    if callback.message is None:
        await callback.answer()
        return
    _, raw_index, raw_option = callback.data.split(":")
    index, selected = int(raw_index), int(raw_option)
    data = await state.get_data()
    ordered_questions = questions_in_order(questions, data.get("question_ids", []))
    current_index = data.get("question_index", 0)
    if index != current_index:
        await callback.answer("Этот вопрос уже обработан.")
        return

    await callback.answer()
    answers = [*data.get("answers", []), selected]
    next_index = index + 1
    if next_index < len(ordered_questions):
        await state.update_data(answers=answers, question_index=next_index)
        await callback.message.edit_text(
            question_text(next_index, ordered_questions),
            reply_markup=answer_keyboard(next_index, ordered_questions[next_index]),
        )
        return

    summary = summarize(ordered_questions, answers)
    attempt_id = results_repository.save(
        callback.from_user.id,
        callback.from_user.username or "",
        ordered_questions,
        answers,
        summary,
    )
    await state.clear()
    attempt = results_repository.latest(callback.from_user.id)
    await callback.message.edit_text(
        "Тестирование завершено.\n\n" + result_text(attempt),
        reply_markup=report_keyboard(attempt_id),
    )
    await callback.message.answer(
        "Выберите следующий раздел:",
        reply_markup=main_menu(callback.from_user.id, admin_user_ids),
    )

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from app.keyboards import CLEAR_CHAT, VIEW_RESULTS, main_menu
from app.services.chat_history import message_id_batches
from app.services.results import ResultsRepository, build_report


router = Router()


def result_text(attempt) -> str:
    return (
        f"Последний результат\n\n"
        f"Ориентировочный грейд: {attempt.grade}\n"
        f"Правильных ответов: {attempt.correct_count} из {attempt.total_questions}\n"
        f"Баллы: {attempt.score} из {attempt.max_score}"
    )


def report_keyboard(attempt_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="📄 Выгрузить полный отчёт", callback_data=f"report:{attempt_id}")
    ]])


def clear_chat_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Удалить переписку", callback_data="chat:clear:confirm")],
        [InlineKeyboardButton(text="Отмена", callback_data="chat:clear:cancel")],
    ])


@router.message(CommandStart())
async def start(message: Message, admin_user_ids: frozenset[int]) -> None:
    await message.answer(
        "Добро пожаловать! Бот поможет определить грейд системного аналитика.\n\n"
        "Выберите действие в меню. Тест содержит 100 вопросов, для каждого нужно выбрать один ответ.",
        reply_markup=main_menu(message.from_user.id, admin_user_ids),
    )


@router.message(Command("help"))
async def help_message(message: Message, admin_user_ids: frozenset[int]) -> None:
    await message.answer(
        "В разделе тестирования последовательно ответьте на 100 вопросов. "
        "В результатах доступен последний итог и полный отчёт с выбранными ответами.\n\n"
        "/cancel — прекратить текущее тестирование",
        reply_markup=main_menu(message.from_user.id, admin_user_ids),
    )


@router.message(F.text == VIEW_RESULTS)
async def view_results(message: Message, results_repository: ResultsRepository,
                       admin_user_ids: frozenset[int]) -> None:
    attempt = results_repository.latest(message.from_user.id)
    if attempt is None:
        await message.answer(
            "У вас пока нет завершённых тестирований.",
            reply_markup=main_menu(message.from_user.id, admin_user_ids),
        )
        return
    await message.answer(result_text(attempt), reply_markup=report_keyboard(attempt.id))


@router.message(F.text == CLEAR_CHAT)
async def request_clear_chat(message: Message) -> None:
    await message.answer(
        "Удалить доступную боту историю переписки? Telegram может не разрешить "
        "удаление сообщений старше 48 часов. Результаты тестов из базы удалены не будут.",
        reply_markup=clear_chat_keyboard(),
    )


@router.callback_query(F.data == "chat:clear:cancel")
async def cancel_clear_chat(callback: CallbackQuery, admin_user_ids: frozenset[int]) -> None:
    await callback.answer("Очистка отменена")
    if callback.message is not None:
        await callback.message.edit_text("Очистка переписки отменена.")
        await callback.message.answer(
            "Главное меню:",
            reply_markup=main_menu(callback.from_user.id, admin_user_ids),
        )


@router.callback_query(F.data == "chat:clear:confirm")
async def clear_chat(callback: CallbackQuery, bot: Bot, state: FSMContext,
                     results_repository: ResultsRepository,
                     admin_user_ids: frozenset[int]) -> None:
    if callback.message is None:
        await callback.answer()
        return
    data = await state.get_data()
    answers = data.get("answers", [])
    if answers:
        results_repository.save_draft(callback.from_user.id, answers)
    await state.clear()
    chat_id = callback.message.chat.id
    latest_message_id = callback.message.message_id
    await callback.answer("Очищаю переписку")
    for batch in message_id_batches(latest_message_id):
        try:
            await bot.delete_messages(chat_id=chat_id, message_ids=batch)
        except TelegramBadRequest:
            continue
    note = " Прогресс теста сохранён." if answers else ""
    await bot.send_message(
        chat_id,
        "Доступная история переписки очищена." + note,
        reply_markup=main_menu(callback.from_user.id, admin_user_ids),
    )


@router.callback_query(F.data.startswith("report:"))
async def download_report(callback: CallbackQuery, results_repository: ResultsRepository) -> None:
    attempt_id = int(callback.data.split(":", maxsplit=1)[1])
    result = results_repository.report(attempt_id, callback.from_user.id)
    if result is None:
        await callback.answer("Отчёт не найден или недоступен.", show_alert=True)
        return
    attempt, answers = result
    document = BufferedInputFile(build_report(attempt, answers), filename=f"analyst-report-{attempt.id}.txt")
    await callback.answer()
    if callback.message is not None:
        await callback.message.answer_document(document, caption="Полный отчёт по вашему тестированию")

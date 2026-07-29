from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import BufferedInputFile, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from app.keyboards import VIEW_RESULTS, main_menu
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

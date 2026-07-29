from aiogram import F, Router
from aiogram.types import BufferedInputFile, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from app.handlers.common import result_text
from app.keyboards import ADMIN_RESULTS, main_menu
from app.services.results import ResultsRepository, build_report


router = Router()


def is_admin(user_id: int, admin_user_ids: frozenset[int]) -> bool:
    return user_id in admin_user_ids


def attempts_keyboard(attempts) -> InlineKeyboardMarkup:
    rows = []
    for attempt in attempts:
        identity = f"@{attempt.username}" if attempt.username else str(attempt.user_id)
        rows.append([InlineKeyboardButton(
            text=f"{identity} · {attempt.correct_count}/{attempt.total_questions} · {attempt.grade}",
            callback_data=f"admin:view:{attempt.id}",
        )])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_attempt_keyboard(attempt_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📄 Выгрузить полную анкету", callback_data=f"admin:report:{attempt_id}")],
        [InlineKeyboardButton(text="↩️ К списку результатов", callback_data="admin:list")],
    ])


async def reject_if_not_admin(event, admin_user_ids: frozenset[int]) -> bool:
    if is_admin(event.from_user.id, admin_user_ids):
        return False
    if isinstance(event, CallbackQuery):
        await event.answer("Недостаточно прав.", show_alert=True)
    else:
        await event.answer("Недостаточно прав.")
    return True


@router.message(F.text == ADMIN_RESULTS)
async def admin_results(message: Message, results_repository: ResultsRepository,
                        admin_user_ids: frozenset[int]) -> None:
    if await reject_if_not_admin(message, admin_user_ids):
        return
    attempts = results_repository.recent_attempts()
    if not attempts:
        await message.answer(
            "Завершённых тестирований пока нет.",
            reply_markup=main_menu(message.from_user.id, admin_user_ids),
        )
        return
    await message.answer(
        "Последние результаты пользователей. Выберите попытку:",
        reply_markup=attempts_keyboard(attempts),
    )


@router.callback_query(F.data == "admin:list")
async def admin_results_callback(callback: CallbackQuery, results_repository: ResultsRepository,
                                 admin_user_ids: frozenset[int]) -> None:
    if await reject_if_not_admin(callback, admin_user_ids):
        return
    attempts = results_repository.recent_attempts()
    await callback.answer()
    if callback.message is not None:
        if attempts:
            await callback.message.edit_text(
                "Последние результаты пользователей. Выберите попытку:",
                reply_markup=attempts_keyboard(attempts),
            )
        else:
            await callback.message.edit_text("Завершённых тестирований пока нет.")


@router.callback_query(F.data.startswith("admin:view:"))
async def admin_view_attempt(callback: CallbackQuery, results_repository: ResultsRepository,
                             admin_user_ids: frozenset[int]) -> None:
    if await reject_if_not_admin(callback, admin_user_ids):
        return
    attempt_id = int(callback.data.rsplit(":", maxsplit=1)[1])
    result = results_repository.report_by_id(attempt_id)
    if result is None:
        await callback.answer("Результат не найден.", show_alert=True)
        return
    attempt, _ = result
    identity = f"@{attempt.username}" if attempt.username else "username не указан"
    text = (
        f"Пользователь: {identity}\nTelegram ID: {attempt.user_id}\n"
        f"Дата (UTC): {attempt.finished_at[:16].replace('T', ' ')}\n\n"
        f"{result_text(attempt).replace('Последний результат', 'Результат тестирования')}"
    )
    await callback.answer()
    if callback.message is not None:
        await callback.message.edit_text(text, reply_markup=admin_attempt_keyboard(attempt.id))


@router.callback_query(F.data.startswith("admin:report:"))
async def admin_download_report(callback: CallbackQuery, results_repository: ResultsRepository,
                                admin_user_ids: frozenset[int]) -> None:
    if await reject_if_not_admin(callback, admin_user_ids):
        return
    attempt_id = int(callback.data.rsplit(":", maxsplit=1)[1])
    result = results_repository.report_by_id(attempt_id)
    if result is None:
        await callback.answer("Результат не найден.", show_alert=True)
        return
    attempt, answers = result
    document = BufferedInputFile(
        build_report(attempt, answers),
        filename=f"analyst-report-user-{attempt.user_id}-attempt-{attempt.id}.txt",
    )
    await callback.answer()
    if callback.message is not None:
        await callback.message.answer_document(document, caption="Полная анкета пользователя")

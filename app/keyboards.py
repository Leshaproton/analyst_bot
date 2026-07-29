from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


START_TEST = "📝 Пройти тестирование"
VIEW_RESULTS = "📊 Посмотреть результаты"
ADMIN_RESULTS = "🛡 Результаты пользователей"


def main_menu(user_id: int, admin_user_ids: frozenset[int]) -> ReplyKeyboardMarkup:
    rows = [[KeyboardButton(text=START_TEST)], [KeyboardButton(text=VIEW_RESULTS)]]
    if user_id in admin_user_ids:
        rows.append([KeyboardButton(text=ADMIN_RESULTS)])
    return ReplyKeyboardMarkup(
        keyboard=rows,
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder="Выберите раздел",
    )

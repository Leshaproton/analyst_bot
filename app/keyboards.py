from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


START_TEST = "📝 Пройти тестирование"
VIEW_RESULTS = "📊 Посмотреть результаты"


def main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=START_TEST)], [KeyboardButton(text=VIEW_RESULTS)]],
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder="Выберите раздел",
    )

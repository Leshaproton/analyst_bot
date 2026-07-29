from app.handlers.admin import is_admin
from app.keyboards import ADMIN_RESULTS, main_menu


def keyboard_texts(user_id: int, admin_ids: frozenset[int]) -> list[str]:
    keyboard = main_menu(user_id, admin_ids)
    return [button.text for row in keyboard.keyboard for button in row]


def test_admin_sees_admin_section() -> None:
    admin_ids = frozenset({42})
    assert is_admin(42, admin_ids)
    assert ADMIN_RESULTS in keyboard_texts(42, admin_ids)


def test_regular_user_does_not_see_admin_section() -> None:
    admin_ids = frozenset({42})
    assert not is_admin(7, admin_ids)
    assert ADMIN_RESULTS not in keyboard_texts(7, admin_ids)

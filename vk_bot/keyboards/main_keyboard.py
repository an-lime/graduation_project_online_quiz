from vkbottle import Callback
from vkbottle.tools import Keyboard


def create_main_menu_keyboard():
    kb = (
        Keyboard()
        .add(Callback("Проверить профиль", {"action": "check_profile"}))
    ).get_json()
    return kb

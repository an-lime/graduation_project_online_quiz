from vkbottle import Callback
from vkbottle.tools import Keyboard


def create_main_menu_keyboard():
    kb = (
        Keyboard()
        .add(Callback("Мой профиль", {"action": "my_profile"}))
    ).get_json()
    return kb

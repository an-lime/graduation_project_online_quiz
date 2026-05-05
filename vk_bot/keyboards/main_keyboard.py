from vkbottle import Callback
from vkbottle.tools import Keyboard


def create_main_menu_keyboard():
    kb = (
        Keyboard()
        .add(Callback("Мой профиль", {"action": "my_profile"}))
        .add(Callback("Присоединиться к игре", {"action": "join_game"}))
    ).get_json()
    return kb

from vkbottle import Keyboard, Callback


def create_lobby_keyboard(game_code: str):
    """Клавиатура для участника в лобби"""
    kb = (
        Keyboard()
        .add(Callback("🚪 Покинуть лобби", {"action": "leave_lobby", "game_code": game_code}))
    )
    return kb.get_json()
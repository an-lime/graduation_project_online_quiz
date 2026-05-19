from vkbottle import Keyboard, Callback


def create_lobby_keyboard(game_code: str):
    """Клавиатура для участника в лобби"""
    kb = (
        Keyboard()
        .add(Callback("🚪 Покинуть лобби", {"action": "leave_lobby", "game_code": game_code}))
    )
    return kb.get_json()


def create_leave_confirm_keyboard(game_code: str):
    """Клавиатура подтверждения выхода из лобби"""
    kb = (
        Keyboard(inline=True)
        .add(Callback("✅ Да, покинуть", {"action": "confirm_leave_lobby", "game_code": game_code}))
        .row()
        .add(Callback("❌ Отмена", {"action": "cancel_leave_lobby", "game_code": game_code}))
    )
    return kb.get_json()

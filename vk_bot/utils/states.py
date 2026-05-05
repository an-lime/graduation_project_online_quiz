users_waiting_for_code: set[int] = set()


def mark_waiting(user_id: int) -> None:
    """Пометить пользователя как ожидающего ввод кода"""
    users_waiting_for_code.add(user_id)


def clear_waiting(user_id: int) -> None:
    """Убрать пользователя из списка ожидающих"""
    users_waiting_for_code.discard(user_id)


def is_waiting(user_id: int) -> bool:
    """Проверить, ждёт ли пользователь ввода кода"""
    return user_id in users_waiting_for_code

from asgiref.sync import sync_to_async

from users.models import UserProfile


def db_sync(func):
    return sync_to_async(func)


@db_sync
def get_current_user(vk_id: int):
    return UserProfile.objects.filter(vk_id=vk_id).first()

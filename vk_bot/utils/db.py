from asgiref.sync import sync_to_async
from django.contrib.auth.models import User
from vkbottle_types import GroupTypes

from users.models import UserProfile


def db_sync(func):
    return sync_to_async(func)


@db_sync
def get_current_user(vk_id: int):
    user_profile = UserProfile.objects.filter(vk_id=vk_id).first()
    user = user_profile.user if user_profile else None
    return user


@db_sync
def create_user_and_profile(username: str, password: str, event: GroupTypes.MessageEvent):

    vk_id = event.object.user_id

    user = User.objects.create_user(
        username=username,
        password=password,
        first_name=f"Игрок_{vk_id}"
    )

    profile = user.profile
    profile.vk_id = vk_id
    profile.save()
from asgiref.sync import sync_to_async
from django.contrib.auth.models import User
from django.db.models import Sum
from vkbottle import Bot

from game_quiz.models import GameResult
from users.models import UserProfile
from vk_bot.config_data.config import VkBotConfig, load_config

config: VkBotConfig = load_config()
bot = Bot(token=config.vkBot.token)


def db_sync(func):
    return sync_to_async(func)


@db_sync
def get_current_user(vk_id: int):
    user_profile = UserProfile.objects.filter(vk_id=vk_id).first()
    user = user_profile.user if user_profile else None
    return user


@db_sync
def create_user_and_profile(username: str, password: str, first_name: str, last_name: str, vk_id: int):
    user = User.objects.create_user(
        username=username,
        password=password,
        first_name=first_name,
        last_name=last_name
    )

    profile = user.profile
    profile.vk_id = vk_id
    profile.save()


@db_sync
def get_user_stats(user):
    """Возвращает количество сыгранных игр и общее число очков"""
    results = GameResult.objects.filter(player=user)
    games_played = results.count()
    total_score = results.aggregate(Sum('score'))['score__sum'] or 0

    return games_played, total_score

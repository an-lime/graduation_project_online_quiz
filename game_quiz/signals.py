from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

from game_quiz.models import GameParticipant
from users.models import UserProfile


@receiver(post_save, sender=GameParticipant)
def notify_participant_joined(sender, instance, created, **kwargs):
    """Отправка уведомления о присоединении участника"""
    if created:
        channel_layer = get_channel_layer()
        game_code = instance.game.game_code

        async_to_sync(channel_layer.group_send)(
            f'lobby_{game_code}',
            {
                'type': 'participant_joined',
                'username': instance.player.username,
                'is_host': instance.player.id == instance.game.owner.id,
            }
        )


@receiver(pre_delete, sender=GameParticipant)
def notify_participant_left(sender, instance, **kwargs):
    """Отправка уведомления об отключении участника"""
    channel_layer = get_channel_layer()
    game_code = instance.game.game_code

    async_to_sync(channel_layer.group_send)(
        f'lobby_{game_code}',
        {
            'type': 'participant_left',
            'username': instance.player.username
        }
    )


@receiver(post_save, sender=UserProfile)
def sync_user_superuser_status(sender, instance, created, **kwargs):
    """
    Сигнал для автоматической синхронизации кастомных ролей платформы
    со встроенными флагами прав доступа Django (is_superuser, is_staff).
    """
    user = instance.user

    # Проверяем, назначена ли роль "Администратор"
    if instance.role and instance.role.name == 'Администратор':
        # Если у пользователя еще нет административных флагов, выставляем их
        if not user.is_superuser or not user.is_staff:
            user.is_superuser = True
            user.is_staff = True
            user.save(update_fields=['is_superuser', 'is_staff'])

    # Если роль была изменена с Администратора на любую другую (например, Участник)
    else:
        if user.is_superuser or user.is_staff:
            user.is_superuser = False
            user.is_staff = False
            user.save(update_fields=['is_superuser', 'is_staff'])

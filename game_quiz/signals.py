from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

from game_quiz.models import GameParticipant


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

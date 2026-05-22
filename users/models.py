"""
Модуль моделей приложения пользователей.

Содержит модели для управления профилями пользователей, ролями и их взаимосвязями.
"""

from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


class UserRole(models.Model):
    """
    Модель роли пользователя.

    Определяет роли, которые могут быть назначены пользователям системы
    (например, 'Участник', 'Администратор').

    Attributes:
        name: Название роли (уникальное поле, максимум 60 символов).
    """
    name = models.CharField(max_length=60, unique=True, verbose_name="Название роли")

    def __str__(self):
        """Возвращает строковое представление роли."""
        return self.name

    class Meta:
        """Мета-настройки модели."""
        verbose_name = "Роль"
        verbose_name_plural = "Роли"


class UserProfile(models.Model):
    """
    Модель профиля пользователя.

    Расширяет стандартную модель User Django, добавляя дополнительные поля:
    - VK ID для интеграции с ВКонтакте
    - Роль пользователя
    - Дата последнего сброса пароля

    Attributes:
        user: Связь один-к-одному со встроенной моделью User.
        vk_id: Идентификатор пользователя ВКонтакте (может быть null).
        role: Внешний ключ на модель UserRole.
        last_password_reset: Дата и время последнего сброса пароля.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')

    vk_id = models.BigIntegerField(unique=True, null=True, blank=True, verbose_name="VK ID")

    role = models.ForeignKey(
        UserRole,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='profiles',
        verbose_name="Роль пользователя"
    )

    last_password_reset = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        """Возвращает имя пользователя связанного аккаунта."""
        return self.user.username

    class Meta:
        """Мета-настройки модели."""
        verbose_name = 'Профиль'
        verbose_name_plural = 'Профили'


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Сигнал для автоматического создания профиля при создании нового пользователя.

    При создании нового пользователя автоматически создается соответствующий
    профиль UserProfile. Если пользователь является суперпользователем, ему
    назначается роль 'Администратор', иначе - 'Участник'.

    Args:
        sender: Класс модели, отправившей сигнал.
        instance: Экземпляр модели User.
        created: Булево значение, указывающее, был ли создан новый объект.
        **kwargs: Дополнительные аргументы.
    """
    if created:
        default_role, _ = UserRole.objects.get_or_create(name='Участник')

        if instance.is_superuser:
            admin_role, _ = UserRole.objects.get_or_create(name='Администратор')
            default_role = admin_role

        UserProfile.objects.create(user=instance, role=default_role)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """
    Сигнал для автоматического сохранения профиля при сохранении пользователя.

    Гарантирует, что профиль пользователя сохраняется вместе с изменениями
    в основной модели User.

    Args:
        sender: Класс модели, отправившей сигнал.
        instance: Экземпляр модели User.
        **kwargs: Дополнительные аргументы.
    """
    instance.profile.save()

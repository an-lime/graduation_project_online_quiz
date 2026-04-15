from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


# Create your models here.

class UserRole(models.Model):
    name = models.CharField(max_length=60, unique=True, verbose_name="Название роли")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Роль"
        verbose_name_plural = "Роли"


class UserProfile(models.Model):
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
        return self.user.username

    class Meta:
        verbose_name = 'Профиль'
        verbose_name_plural = 'Профили'


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        default_role, _ = UserRole.objects.get_or_create(name='Участник')

        if instance.is_superuser:
            admin_role, _ = UserRole.objects.get_or_create(name='Администратор')
            default_role = admin_role

        UserProfile.objects.create(user=instance, role=default_role)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()

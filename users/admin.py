from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User

from .models import UserProfile, UserRole


# 1. "Пришиваем" профиль прямо к стандартной странице Пользователя Django
class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Профиль пользователя (VK, Роль)'


# Переопределяем стандартного User'а, чтобы добавить туда профиль
admin.site.unregister(User)


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    inlines = (UserProfileInline,)
    search_fields = ('username', 'first_name', 'last_name', 'email')


# 2. Оставляем отдельную страницу для профилей
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'vk_id', 'role', 'last_password_reset')
    list_editable = ('role',)
    list_filter = ('role',)
    search_fields = ('user__username', 'vk_id')
    autocomplete_fields = ('user', 'role')


@admin.register(UserRole)
class UserRoleAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

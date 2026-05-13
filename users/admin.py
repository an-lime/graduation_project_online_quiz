from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User

from users.models import UserRole, UserProfile


# Register your models here.

@admin.register(UserRole)
class UserRoleAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)
    list_filter = ('name',)


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Профиль'


class CustomUserAdmin(UserAdmin):
    inlines = (UserProfileInline,)

    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'get_role')

    def get_role(self, obj):
        return obj.profile.role.name if obj.profile.role else '-'

    get_role.short_description = 'Роль'


admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'vk_id', 'get_email')
    list_filter = ('role',)
    search_fields = ('user__username', 'vk_id', 'user__email')
    autocomplete_fields = ('user', 'role')

    def get_email(self, obj):
        return obj.user.email

    get_email.short_description = 'Email'

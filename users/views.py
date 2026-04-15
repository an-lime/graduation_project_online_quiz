from django.contrib import messages
from django.contrib.auth import authenticate, login, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import transaction
from django.shortcuts import render, redirect
from django.urls import reverse  # Для получения строки URL

from users.utils import terminate_all_user_sessions


def login_view(request):
    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            messages.success(request, 'Вы успешно вошли')
            next_url = request.GET.get('next', 'main:index')
            return redirect(next_url)
        else:
            messages.error(request, 'Неверный логин или пароль')

    return render(request, 'users/login.html')


@login_required
def profile(request):
    user = request.user
    return render(request, 'users/profile.html')


@login_required
@transaction.atomic
def profile_edit(request):
    if request.method != "POST":
        return redirect('users:profile')

    user = request.user
    new_username = request.POST.get('username', '').strip()
    new_email = request.POST.get('email', '').strip()
    new_first_name = request.POST.get('first_name', '').strip()
    new_last_name = request.POST.get('last_name', '').strip()

    if len(new_username) < 3:
        messages.error(request, '❌ Логин должен содержать минимум 3 символа')
        return redirect(reverse('users:profile') + '#edit')

    if new_username != user.username:
        if User.objects.filter(username=new_username).exists():
            messages.error(request, '❌ Этот логин уже занят')
            return redirect(reverse('users:profile') + '#edit')

    user.username = new_username
    user.email = new_email
    user.first_name = new_first_name
    user.last_name = new_last_name

    try:
        user.save()
        messages.success(request, '✅ Профиль успешно обновлён!')
    except Exception as e:
        messages.error(request, f'❌ Ошибка сохранения: {str(e)}')
        return redirect(reverse('users:profile') + '#edit')

    return redirect('users:profile')


@login_required
@transaction.atomic
def password_change(request):
    if request.method != 'POST':
        return redirect('users:profile')

    user = request.user
    current_password = request.POST.get('current_password')
    new_password1 = request.POST.get('new_password1')
    new_password2 = request.POST.get('new_password2')

    if not user.check_password(current_password):
        messages.error(request, '❌ Неверный текущий пароль')
        return redirect(reverse('users:profile') + '#password')

    if new_password1 != new_password2:
        messages.error(request, '❌ Новые пароли не совпадают')
        return redirect(reverse('users:profile') + '#password')

    if len(new_password1) < 8:
        messages.error(request, '❌ Пароль должен быть не менее 8 символов')
        return redirect(reverse('users:profile') + '#password')

    user.set_password(new_password1)
    user.save()

    terminate_all_user_sessions(user)
    update_session_auth_hash(request, user)

    messages.success(request, 'Пароль успешно изменён! Все остальные сессии завершены.')
    return redirect('users:profile')

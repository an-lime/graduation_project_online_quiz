import json
import random
import string
from datetime import datetime, timedelta

from django.contrib import messages
from django.contrib.auth import authenticate, login, update_session_auth_hash
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from Online_Quiz_Core import settings
from users.utils import terminate_all_user_sessions

User = get_user_model()


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

    is_ajax = request.headers.get('X-Ajax-Request') == 'true'

    user = request.user
    new_username = request.POST.get('username', '').strip()
    new_email = request.POST.get('email', '').strip()
    new_first_name = request.POST.get('first_name', '').strip()
    new_last_name = request.POST.get('last_name', '').strip()

    # 1. Валидация логина
    if len(new_username) < 3:
        error_msg = '❌ Логин должен содержать минимум 3 символа'
        if is_ajax:
            return JsonResponse({'success': False, 'error': error_msg})
        messages.error(request, error_msg)
        return redirect(reverse('users:profile') + '#edit')

    # 2. Проверка уникальности логина
    if new_username != user.username:
        if User.objects.filter(username=new_username).exists():
            error_msg = '❌ Этот логин уже занят'
            if is_ajax:
                return JsonResponse({'success': False, 'error': error_msg})
            messages.error(request, error_msg)
            return redirect(reverse('users:profile') + '#edit')

    # 3. ПРОВЕРКА EMAIL (Строгая логика)
    if new_email and new_email != user.email:
        is_verified = request.session.get('is_email_verified', False)
        verified_email = request.session.get('verified_email', '')

        # Если email изменился, но не подтвержден кодом
        if not is_verified or verified_email != new_email:
            error_msg = '⚠️ Email не подтвержден! Введите код из письма.'
            if is_ajax:
                return JsonResponse({'success': False, 'error': error_msg})
            messages.warning(request, error_msg)
            return redirect(reverse('users:profile') + '#edit')

        # Уникальность Email
        if User.objects.filter(email=new_email).exclude(id=user.id).exists():
            error_msg = '❌ Этот Email уже используется другим аккаунтом'
            if is_ajax:
                return JsonResponse({'success': False, 'error': error_msg})
            messages.error(request, error_msg)
            return redirect(reverse('users:profile') + '#edit')

    # 4. Если всё ОК — сохраняем
    user.username = new_username
    user.email = new_email
    user.first_name = new_first_name
    user.last_name = new_last_name

    try:
        user.save()
        # Очищаем флаги верификации после успешного сохранения
        request.session.pop('is_email_verified', None)
        request.session.pop('verified_email', None)

        success_msg = '✅ Профиль успешно обновлён!'
        if is_ajax:
            return JsonResponse({'success': True, 'message': success_msg})
        messages.success(request, success_msg)
    except Exception as e:
        error_msg = f'❌ Ошибка сохранения: {str(e)}'
        if is_ajax:
            return JsonResponse({'success': False, 'error': error_msg})
        messages.error(request, error_msg)

    return redirect('users:profile')


@login_required
@transaction.atomic
def password_change(request):
    if request.method != 'POST':
        return redirect('users:profile')

    user = request.user

    if user.profile.last_password_reset:
        if timezone.now() - user.profile.last_password_reset < timedelta(minutes=5):
            messages.error(request, "Подождите 5 минут перед следующим сбросом пароля")
            return redirect(reverse('users:profile') + '#password')

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
    user.profile.last_password_reset = timezone.now()
    user.save()

    terminate_all_user_sessions(user)
    update_session_auth_hash(request, user)

    messages.success(request, 'Пароль успешно изменён! Все остальные сессии завершены.')
    return redirect('users:profile')


@login_required
@require_POST
def send_verify_code(request):
    """Генерирует 6-значный код и отправляет его на Email"""

    # Проверка кулдауна (60 секунд) через таймстампы
    last_send = request.session.get('last_code_send_time')
    if last_send and timezone.now().timestamp() - last_send < 60:
        return JsonResponse({'success': False, 'error': 'Подождите 60 секунд перед отправкой нового кода'})

    try:
        data = json.loads(request.body)
        email = data.get('email')

        if not email:
            # Добавил 'success': False для корректной обработки на фронтенде
            return JsonResponse({'success': False, 'error': 'Email не указан'})

        code = ''.join(random.choices(string.digits, k=6))

        request.session['email_verification_code'] = code
        request.session['email_to_verify'] = email

        now_ts = timezone.now().timestamp()
        request.session['code_sent_at'] = now_ts
        request.session['last_code_send_time'] = now_ts

        request.session.pop('is_email_verified', None)

        html_message = render_to_string('emails/verify_code.html', {'code': code})
        send_mail(
            subject='Код подтверждения: Онлайн-Викторина',
            message='',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            html_message=html_message
        )

        return JsonResponse({'success': True, 'message': 'Код отправлен'})

    except Exception as e:
        return JsonResponse({'success': False, 'error': f'Ошибка отправки: {str(e)}'})


@login_required
@require_POST
def verify_email_code(request):
    """Проверяет введенный код"""
    try:
        data = json.loads(request.body)
        user_code = data.get('code')

        session_code = request.session.get('email_verification_code')
        sent_at_str = request.session.get('code_sent_at')

        if not session_code or not sent_at_str:
            return JsonResponse({'success': False, 'error': 'Код истёк или не был отправлен'})

        if not isinstance(sent_at_str, (int, float)):
            return JsonResponse({'success': False, 'error': 'Ошибка проверки кода'})

        sent_at = datetime.fromtimestamp(sent_at_str, tz=timezone.get_current_timezone())

        if timezone.now() - sent_at > timedelta(minutes=10):
            request.session.pop('email_verification_code', None)
            request.session.pop('code_sent_at', None)
            return JsonResponse({'success': False, 'error': 'Код истёк. Отправьте новый.'})

        if str(user_code) == str(session_code):
            request.session['is_email_verified'] = True
            request.session['verified_email'] = request.session['email_to_verify']

            request.session.pop('email_verification_code', None)
            request.session.pop('email_to_verify', None)
            request.session.pop('code_sent_at', None)

            return JsonResponse({'success': True})
        else:
            return JsonResponse({'success': False, 'error': 'Неверный код'})

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


def api_get_user_by_vk(request, vk_id: int):
    """API для получения username по VK ID"""
    try:
        user = User.objects.get(profile__vk_id=vk_id)
        return JsonResponse({'username': user.username})
    except User.DoesNotExist:
        return JsonResponse({'error': 'User not found'}, status=404)

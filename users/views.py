from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login
from django.contrib import messages


# Create your views here.

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
    return render(request, 'users/profile.html')
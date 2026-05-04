from django.contrib import admin
from django.http import HttpResponse
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('main.urls', namespace='main')),
    path('users/', include('users.urls', namespace='users')),
    path('quiz/', include('game_quiz.urls', namespace='game_quiz')),

    # Заглушка для Chrome DevTools
    path('.well-known/appspecific/com.chrome.devtools.json', lambda _: HttpResponse('', status=200)),
]

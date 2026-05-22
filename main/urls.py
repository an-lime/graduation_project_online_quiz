from django.urls import path

from . import views

# Пространство имен для URL-маршрутов приложения main
app_name = 'main'

# Маршруты для основных страниц сайта
urlpatterns = [
    path('', views.index, name='index'),
    path('about/', views.about, name='about'),
    path('rules/', views.rules, name='rules'),
    path('contacts/', views.contacts, name='contacts'),
]

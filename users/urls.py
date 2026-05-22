from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.user_login, name='user_login'),
    path('logout/', views.user_logout, name='user_logout'),
    path('staff/', views.user_list, name='user_list'),
    path('staff/register/', views.register_user, name='register_user'),
    path('staff/toggle/<int:user_id>/', views.toggle_user_status, name='toggle_user_status'),
    path('', views.user_login, name='login'),
]
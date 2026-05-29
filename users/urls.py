from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [

    path('', views.user_login, name='login'),

    path('staff/', views.user_list, name='user_list'),

    path('register/', views.register_user, name='register_user'),

    path('toggle/<int:user_id>/', views.toggle_user_status, name='toggle_user_status'),

    # 1. Form where user submits their email address
    path('password-reset/', 
         auth_views.PasswordResetView.as_view(template_name='users/password_reset_form.html'), 
         name='password_reset'),
         
    # 2. Success screen showing that an email was dispatched
    path('password-reset/done/', 
         auth_views.PasswordResetDoneView.as_view(template_name='users/password_reset_done.html'), 
         name='password_reset_done'),
         
    # 3. The secure link clicked inside the user's inbox
    path('password-reset-confirm/<uidb64>/<token>/', 
         auth_views.PasswordResetConfirmView.as_view(template_name='users/password_reset_confirm.html'), 
         name='password_reset_confirm'),
         
    # 4. Final success screen confirming password was updated
    path('password-reset-complete/', 
         auth_views.PasswordResetCompleteView.as_view(template_name='registration/password_reset_complete.html'), 
         name='password_reset_complete'),
]

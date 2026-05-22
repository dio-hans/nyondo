"""
URL configuration for hardware_system project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect

urlpatterns = [
  # Admin Interface Access
    path('admin/', admin.site.urls),
    
    # Root URL redirects straight to login page
    path('', lambda request: redirect('user_login', permanent=False)),
    
    # Core Application Modules Included
    path('inventory/', include('inventory.urls')),
    path('sales/', include('sales.urls')),
    path('procurement/', include('procurement.urls')),
    path('schemes/', include('schemes.urls')),
    path('reports/', include('reports.urls')),
    path('', include('users.urls')),
    path('dashboard/', include('reports.urls')),
]


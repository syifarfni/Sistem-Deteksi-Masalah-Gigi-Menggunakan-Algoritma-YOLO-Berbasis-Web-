"""
URL configuration for yolo project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
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
from django.urls import path, re_path, include
from home.views import home, detect_camera, detect_objects, riwayat
from django.conf import settings
from django.conf.urls.static import static
from accounts.views import login_view, logout_view, register_view, ganti_password_view, profile_view


urlpatterns = [
    path('admin/', admin.site.urls), 
    path('', home, name='home'),
    # path("check/login/", check_login, name="check_login"),
    path("detect/", detect_objects, name="detect_objects"),
    path("camera/", detect_camera, name="detect_camera"),
    # Add path for camera selection - optional camera_id parameter
    path("camera/<int:camera_id>/", detect_camera, name="detect_camera_with_id"),
    # Authentication URLs
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('register/', register_view, name='register'),
    path('profile/', profile_view, name='profile'),
    path('ganti_password/', ganti_password_view, name='ganti_password'),
    # API URLs
    path('riwayat/', riwayat, name="riwayat"),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    


"""
config/urls.py  —  project-level URL configuration
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    # Django admin site
    path('admin/', admin.site.urls),

    # Built-in auth: login, logout, password change/reset
    # Templates are loaded from templates/registration/
    path('accounts/', include('django.contrib.auth.urls')),

    # Core app — all app URLs under the 'core' namespace
    path('', include('core.urls', namespace='core')),
]

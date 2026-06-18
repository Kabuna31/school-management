from django.contrib import admin
from django.urls import path, include
from django.http import HttpResponse


def health(request):
    return HttpResponse("ok", status=200)


urlpatterns = [
    path('health/', health, name='health'),
    path('admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')),
    path('', include('core.urls', namespace='core')),
]

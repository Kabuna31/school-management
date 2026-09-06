from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

# Import report card views
from core.views import (
    ReportCardListView,
    ReportCardDetailView,
    ReportCardPrintView,
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('core.urls')),
    path('accounts/', include('django.contrib.auth.urls')),  # This adds login/logout URLs
    
    # Report Card URLs
    path('report-cards/', ReportCardListView.as_view(), name='report_card_list'),
    path('report-cards/<int:student_id>/', ReportCardDetailView.as_view(), name='report_card_detail'),
    path('report-cards/<int:student_id>/print/', ReportCardPrintView.as_view(), name='report_card_print'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
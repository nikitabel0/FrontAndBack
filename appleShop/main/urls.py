from django.urls import path
from .views import MainPageView
from django.conf.urls.static import static
from django.conf import settings

urlpatterns = [
    path('mainpage/', MainPageView.as_view(), name='mainpage'),
]
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
from django.urls import path
from .views import CategoryListView, MainPageView, ProductDetailView, ProductListView
from django.conf.urls.static import static
from django.conf import settings

urlpatterns = [
    path('mainpage/', MainPageView.as_view(), name='mainpage'),
    path('products/', ProductListView.as_view(), name='product-list'),
    path('products/<int:pk>/', ProductDetailView.as_view(), name='product-detail'),
    path('categories/', CategoryListView.as_view(), name='category-list'),
]
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
from django.urls import path

from . import views
from rest_framework.routers import DefaultRouter
app_name = 'main' 

router = DefaultRouter()

# Регистрируем все ViewSets
router.register(r'products', views.ProductViewSet, basename='product')
router.register(r'orders', views.OrderViewSet, basename='order')
router.register(r'articles', views.ArticleViewSet, basename='article')
router.register(r'categories', views.CategoryViewSet, basename='category')
router.register(r'baskets', views.BasketViewSet, basename='basket')
router.register(r'profiles', views.UserProfileViewSet, basename='userprofile')


urlpatterns = [
    path('', views.home, name='home'),  # Добавьте эту строку
    path('register/', views.register, name='register'),
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', views.CustomLogoutView.as_view(), name='logout'),
    path('profile/', views.profile, name='profile'),
    path('admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin/products/', views.admin_products, name='admin_products'),
    path('admin/products/create/', views.admin_product_create, name='admin_product_create'),
    path('admin/products/<int:pk>/edit/', views.admin_product_edit, name='admin_product_edit'),
    path('admin/products/<int:pk>/delete/', views.admin_product_delete, name='admin_product_delete'),
    path('admin/users/', views.admin_users, name='admin_users'),
    path('admin/users/<int:user_id>/toggle/', views.admin_user_toggle, name='admin_user_toggle'),
    path('admin/users/<int:user_id>/delete/', views.admin_user_delete, name='admin_user_delete'),
    path('admin/users/<int:user_id>/change_role/', views.admin_user_change_role, name='admin_user_change_role'),
    path('product/<int:pk>/', views.product_detail, name='product_detail'),
    path('basket/', views.basket_view, name='basket'),
    path('basket/update/<int:item_id>/', views.update_basket_item, name='update_basket_item'),
    path('checkout/', views.checkout, name='checkout'),
    path('order-confirmation/<int:order_id>/', views.order_confirmation, name='order_confirmation'),
  
]
urlpatterns += router.urls
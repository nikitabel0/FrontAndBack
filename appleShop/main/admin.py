from django.contrib import admin
from .models import (
    UserProfile,
    Category,
    Article,
    Product,
    Discount,
    Basket,
    BasketItem,
    Order,
    OrderItem,
    MainPage
)

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone', 'address')

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)

@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ('title', 'published_at')
    list_filter = ('published_at', 'categories')
    search_fields = ('title',)

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('title', 'price')
    list_filter = ('price',)
    search_fields = ('title',)

@admin.register(Discount)
class DiscountAdmin(admin.ModelAdmin):
    list_display = ('product', 'percent', 'start_date', 'end_date')

@admin.register(Basket)
class BasketAdmin(admin.ModelAdmin):
    list_display = ('user', 'created_at')

@admin.register(BasketItem)
class BasketItemAdmin(admin.ModelAdmin):
    list_display = ('basket', 'product', 'quantity')

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'created_at')

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('order', 'product', 'quantity')
    

@admin.register(MainPage)
class MainPageAdmin(admin.ModelAdmin):
    list_display = ('title', 'subtitle', 'created_at', 'is_active')
    list_editable = ('is_active',)
    search_fields = ('title', 'subtitle')

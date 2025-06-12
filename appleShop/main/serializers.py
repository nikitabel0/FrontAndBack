# serializers.py
from rest_framework import serializers
from .models import (
    Product, Order, OrderItem, Article, 
    Category, Discount, Basket, BasketItem,
    UserProfile
)
from django.utils import timezone
from django.contrib.auth.models import User

class ProductSerializer(serializers.ModelSerializer):
    discount_info = serializers.SerializerMethodField()
    is_new = serializers.SerializerMethodField()
    has_discount = serializers.SerializerMethodField()
    
    class Meta:
        model = Product
        fields = [
            'id', 'title', 'price', 'image', 'description',
            'discount_info', 'is_new', 'has_discount', 'category'
        ]
    
    def get_discount_info(self, obj):
  
        discount = obj.current_discount
        if discount:
            return {
                'percent': discount.percent,
                'end_date': discount.end_date
            }
        return None
    
    def get_is_new(self, obj):
     
        return (timezone.now() - obj.created_at).days < 7
    
    def get_has_discount(self, obj):
  
        return obj.has_active_discount

class OrderItemSerializer(serializers.ModelSerializer):
    product_title = serializers.CharField(source='product.title', read_only=True)
    product_price = serializers.DecimalField(
        source='product.price', 
        max_digits=10, 
        decimal_places=2,
        read_only=True
    )
    
    class Meta:
        model = OrderItem
        fields = ['id', 'product', 'quantity', 'product_title', 'product_price']

class OrderSerializer(serializers.ModelSerializer):
    # Аннотированное поле
    calculated_total = serializers.DecimalField(
        max_digits=10, 
        decimal_places=2,
        read_only=True
    )
    
    # SerializerMethodField с использованием контекста
    user_info = serializers.SerializerMethodField()
    
    # Вложенный сериализатор
    items = OrderItemSerializer(many=True, read_only=True)
    
    class Meta:
        model = Order
        fields = [
            'id', 'status', 'created_at', 'calculated_total',
            'user_info', 'items', 'pdf_file'
        ]
    
    def get_user_info(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            user = request.user
            return {
                'username': user.username,
                'email': user.email,
                'is_staff': user.is_staff
            }
        return None

class ArticleSerializer(serializers.ModelSerializer):
    # SerializerMethodField для связанных данных
    category_names = serializers.SerializerMethodField()
    is_recent = serializers.SerializerMethodField()
    
    class Meta:
        model = Article
        fields = [
            'id', 'title', 'teaser', 'full_text', 'image',
            'published_at', 'category_names', 'is_recent'
        ]
    
    def get_category_names(self, obj):
        # Возвращаем названия категорий
        return list(obj.categories.values_list('name', flat=True))
    
    def get_is_recent(self, obj):
        # Проверяем, новая ли статья
        return (timezone.now() - obj.published_at).days < 3

class CategorySerializer(serializers.ModelSerializer):
    # Аннотированные поля
    product_count = serializers.IntegerField(read_only=True)
    avg_price = serializers.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        read_only=True
    )
    
    # SerializerMethodField
    featured_product = serializers.SerializerMethodField()
    
    class Meta:
        model = Category
        fields = [
            'id', 'name', 'product_count', 
            'avg_price', 'featured_product'
        ]
    
    def get_featured_product(self, obj):
        # Самый дорогой товар в категории
        featured = obj.products.order_by('-price').first()
        if featured:
            return {
                'id': featured.id,
                'title': featured.title,
                'price': featured.price
            }
        return None

class BasketItemSerializer(serializers.ModelSerializer):
    product_title = serializers.CharField(source='product.title', read_only=True)
    product_price = serializers.DecimalField(
        source='product.price', 
        max_digits=10, 
        decimal_places=2,
        read_only=True
    )
    total_price = serializers.SerializerMethodField()
    
    class Meta:
        model = BasketItem
        fields = [
            'id', 'product', 'quantity', 
            'product_title', 'product_price', 'total_price'
        ]
    
    def get_total_price(self, obj):
        return obj.quantity * obj.product.price

class BasketSerializer(serializers.ModelSerializer):
    items = BasketItemSerializer(many=True, read_only=True)
    total_price = serializers.SerializerMethodField()
    user_email = serializers.SerializerMethodField()
    
    class Meta:
        model = Basket
        fields = ['id', 'created_at', 'items', 'total_price', 'user_email']
    
    def get_total_price(self, obj):
        # Используем аннотацию из модели
        return obj.total_price
    
    def get_user_email(self, obj):
        # Используем контекст для проверки доступа
        request = self.context.get('request')
        if request and request.user == obj.user:
            return obj.user.email
        return None

class UserProfileSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(source='user.email', read_only=True)
    active_orders = serializers.SerializerMethodField()
    
    class Meta:
        model = UserProfile
        fields = [
            'id', 'phone', 'address', 'role', 
            'user_email', 'active_orders'
        ]
    
    def get_active_orders(self, obj):
        # Используем метод модели с оптимизацией
        return obj.get_active_orders_count()
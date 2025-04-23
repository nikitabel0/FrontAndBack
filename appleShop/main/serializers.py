from django.utils import timezone 
from rest_framework import serializers
from .models import Category, MainPage, Product

class MainPageSerializer(serializers.ModelSerializer):
    class Meta:
        model = MainPage
        fields = '__all__'

class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ['id', 'title', 'price', 'image', 'discount_info']
        read_only_fields = ['discount_info']
    
    discount_info = serializers.SerializerMethodField()
    
    def get_discount_info(self, obj):
        active_discount = obj.discounts.filter(
            start_date__lte=timezone.now(),
            end_date__gte=timezone.now()
        ).first()
        if active_discount:
            return {
                'percent': active_discount.percent,
                'final_price': round(float(obj.price) * (1 - active_discount.percent/100), 2)
            }
        return None

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'product_count']
    
    product_count = serializers.IntegerField(read_only=True)
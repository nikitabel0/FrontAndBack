import django_filters
from .models import Category, Product

class ProductFilter(django_filters.FilterSet):
    # Объединяем все фильтры в один класс
    price_min = django_filters.NumberFilter(
        field_name='price', 
        lookup_expr='gte', 
        label='Минимальная цена'
    )
    price_max = django_filters.NumberFilter(
        field_name='price', 
        lookup_expr='lte', 
        label='Максимальная цена'
    )
    manufacturer = django_filters.CharFilter(
        field_name='manufacturer',
        lookup_expr='icontains',
        label='Производитель'
    )
    
    category = django_filters.ModelChoiceFilter(
        queryset=Category.objects.all(),
        label='Категория',
        empty_label='Все категории'
    )
    
    ORDERING_CHOICES = [
        ('title', 'По названию (А-Я)'),
        ('-title', 'По названию (Я-А)'),
        ('price', 'Сначала дешевле'),
        ('-price', 'Сначала дороже'),
    ]
    
    ordering = django_filters.OrderingFilter(
        choices=ORDERING_CHOICES,
        fields={
            'title': 'title',
            'price': 'price'
        },
        label='Сортировка',
        empty_label='Рекомендованные'
    )

    class Meta:
        model = Product
        fields = ['category', 'manufacturer']
from django.utils import timezone
from django.db import models
from django.contrib.auth.models import User


class UserProfile(models.Model):
    
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile'
    )
    phone = models.CharField('Телефон', max_length=20, blank=True)
    address = models.TextField('Адрес', blank=True)

    def __str__(self):
        return f"Профиль {self.user.username}"


class Category(models.Model):
    name = models.CharField('Название категории', max_length=100, unique=True)

    def __str__(self):
        return self.name


class Article(models.Model):
    
    title = models.CharField('Заголовок', max_length=200)
    teaser = models.CharField('Анонс', max_length=300)
    published_at = models.DateTimeField('Дата публикации', auto_now_add=True)
    full_text = models.TextField('Полный текст')
    categories = models.ManyToManyField(
        Category,
        verbose_name='Категории',
        related_name='articles',
        blank=True
    )

    def __str__(self):
        return self.title


class Product(models.Model):
    title = models.CharField('Название', max_length=200)
    description = models.TextField('Описание', blank=True)
    price = models.DecimalField('Цена', max_digits=10, decimal_places=2)
    image = models.ImageField('Изображение', upload_to='products/')
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='products'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField('Активен', default=True)

    def __str__(self):
        return self.title

    @property
    def current_discount(self):
        return self.discounts.filter(
            start_date__lte=timezone.now().date(),  # Используем date()
            end_date__gte=timezone.now().date()
        ).first()



class Discount(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='discounts'
    )
    percent = models.PositiveSmallIntegerField('Скидка (%)')
    start_date = models.DateField('Начало действия')
    end_date = models.DateField('Окончание действия')

    def __str__(self):
        return f"{self.percent}% для {self.product.title}"  


class Basket(models.Model):
    
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='basket'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Корзина {self.user.username}"


class BasketItem(models.Model):
    basket = models.ForeignKey(
        Basket,
        on_delete=models.CASCADE,
        related_name='items'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE
    )
    quantity = models.PositiveIntegerField('Количество', default=1)

    class Meta:
        unique_together = ('basket', 'product')

    def __str__(self):
        return f"{self.product.title} в корзине {self.basket.user.username}"


class Order(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='orders'
    )
    created_at = models.DateTimeField('Дата заказа', auto_now_add=True)

    def __str__(self):
        return f"Заказ"


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT
    )
    quantity = models.PositiveIntegerField('Количество', default=1)

    def __str__(self):
        return f"{self.quantity}× {self.product.title} в заказе {self.order.id}"
    
class MainPage(models.Model):
    title = models.CharField('Заголовок', max_length=200)
    subtitle = models.CharField('Подзаголовок', max_length=300)
    image = models.ImageField(
        'Изображение', 
        upload_to='mainpage/',
        help_text='Рекомендуемый размер: 1920x1080px'
    )
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)
    is_active = models.BooleanField('Активно', default=True)

    class Meta:
        verbose_name = 'Главная страница'
        verbose_name_plural = 'Настройки главной страницы'
        ordering = ['-created_at']

    def __str__(self):
        return self.title

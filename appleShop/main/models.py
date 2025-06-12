from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.urls import reverse  
from django.db.models import Count, Sum, Avg, F 
from django.db import models
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle
from django.core.files.base import ContentFile
from django.dispatch import receiver
from django.db.models.signals import pre_save


class UserProfile(models.Model):
    def get_active_orders_count(self):
        return self.user.orders.filter(status='completed').count()
    
    phone = models.CharField('Телефон', max_length=20, blank=True)
    address = models.TextField('Адрес', blank=True)
    ROLE_CHOICES = [
        ('user', 'Пользователь'),
        ('admin', 'Администратор'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='user')

    def __str__(self):
        return f"Профиль {self.user.username}"
    
    class Meta:
        verbose_name = 'Профиль пользователя'
        verbose_name_plural = 'Профиля пользователей'


class Category(models.Model):
    name = models.CharField('Название категории', max_length=100, unique=True)

    def __str__(self):
        return self.name
    def get_active_products_titles(self):
        return self.products.filter(is_active=True).values_list('title', flat=True)

    @property
    def avg_price(self):
        return self.products.aggregate(avg_price=Avg('price'))['avg_price']
    
    class Meta:
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'


class ArticleCategory(models.Model):
    article = models.ForeignKey(
        'Article', 
        on_delete=models.CASCADE,
        related_name='article_categories'  
    )
    category = models.ForeignKey(
        Category, 
        on_delete=models.CASCADE,
        related_name='category_articles'  
    )
    added_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата добавления')
    weight = models.PositiveSmallIntegerField(
        default=1,
        verbose_name='Вес связи',
        help_text='Важность связи между статьей и категорией'
    )

    class Meta:
        unique_together = ('article', 'category')
        ordering = ['-added_at']

class Article(models.Model):
    title = models.CharField('Заголовок', max_length=200)
    teaser = models.CharField('Анонс', max_length=300)
    published_at = models.DateTimeField('Дата публикации', auto_now_add=True)
    full_text = models.TextField('Полный текст')
    source_url = models.URLField('Ссылка на источник', blank=True)
    image = models.ImageField(
        'Изображение статьи',
        upload_to='articles/',
        help_text='Рекомендуемый размер: 1200x800px',
        null=True,  # Разрешить NULL в базе данных
        blank=True  # Разрешить пустое значение в формах
    )
    
    categories = models.ManyToManyField(
        Category,
        through='ArticleCategory',
        verbose_name='Категории',
        related_name='articles',
        blank=True
    )
    
    is_featured = models.BooleanField('Избранная статья', default=False)
    
    class Meta:
        ordering = ['-published_at']
        verbose_name = 'Статья'
        verbose_name_plural = 'Статьи'
    
    def __str__(self):
        return self.title
    
    @property
    def published_date(self):
        return self.published_at.strftime("%d.%m.%Y")


#актив не актив продукт
class ProductManager(models.Manager):
    def active(self):
        return self.filter(is_active=True)


class Product(models.Model):
    title = models.CharField('Название', max_length=200)
    description = models.TextField('Описание', blank=True)
    price = models.DecimalField('Цена', max_digits=10, decimal_places=2)
    image = models.ImageField('Изображение', upload_to='products/')
    manufacturer = models.CharField(
        'Производитель', 
        max_length=100, 
        default='Apple'
    )
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

    objects = ProductManager() 
    @property
    def has_active_discount(self):
        return self.discounts.filter(
            start_date__lte=timezone.now().date(),
            end_date__gte=timezone.now().date()
        ).exists() 

    class Meta:
        verbose_name = 'Товар'
        verbose_name_plural = 'Товары'
        ordering = ['-created_at'] 

    def __str__(self):
        return self.title


  

    # дата
    @property
    def is_new(self):
        return (timezone.now() - self.created_at).days < 3

    # связь со скид
    @property
    def current_discount(self):
        return self.discounts.filter(
            start_date__lte=timezone.now().date(),
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

    class Meta:
        verbose_name = 'Скидка'
        verbose_name_plural = 'Скидки'

    def __str__(self):
        return f"{self.percent}% для {self.product.title}"


class Basket(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='basket'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Корзина'
        verbose_name_plural = 'Корзины'

    def __str__(self):
        return f"Корзина {self.user.username}"


    @property
    def total_price(self):
        return self.items.aggregate(
            total=Sum(F('quantity') * F('product__price'))
        )['total'] or 0


class BasketItem(models.Model):
    basket = models.ForeignKey(
        Basket,
        on_delete=models.CASCADE,
        related_name='items' 
    )
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField('Количество', default=1)

    class Meta:
        unique_together = ('basket', 'product')
        verbose_name = 'Товары в корзине'
        verbose_name_plural = 'Товары в корзинах'

    def __str__(self):
        return f"{self.product.title} в корзине {self.basket.user.username}"

    # тотальный прайс 
    @property
    def total_price(self):
        return self.quantity * self.product.price


class Order(models.Model):
    STATUS_CHOICES = [
        ('new', 'Новый'),
        ('processing', 'В обработке'),
        ('completed', 'Завершен'),
        ('canceled', 'Отменен'),
    ]
    PAYMENT_METHODS = [
        ('card', 'Банковская карта'),
        ('cash', 'Наличные при получении'),
        ('online', 'Онлайн-платеж'),
    ]
    
    # Основная информация
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='orders',
        verbose_name='Пользователь'
    )
    status = models.CharField(
        'Статус',
        max_length=20,
        choices=STATUS_CHOICES,
        default='new'
    )
    created_at = models.DateTimeField('Дата заказа', auto_now_add=True)
    
    # Контактная информация
    full_name = models.CharField('Полное имя', max_length=100)
    email = models.EmailField('Email')
    phone = models.CharField('Телефон', max_length=20)
    
    # Доставка и оплата
    shipping_address = models.TextField('Адрес доставки')
    payment_method = models.CharField(
        'Способ оплаты',
        max_length=10,
        choices=PAYMENT_METHODS,
        default='card'
    )
    
    # Данные карты (заполняются только при оплате картой)
    card_number = models.CharField('Номер карты', max_length=16, blank=True, null=True)
    card_expiry = models.CharField('Срок действия', max_length=5, blank=True, null=True)
    card_cvv = models.CharField('CVV', max_length=3, blank=True, null=True)
    
    # Дополнительная информация
    comments = models.TextField('Комментарии к заказу', blank=True)
    total_price = models.DecimalField(
        'Общая сумма',
        max_digits=10, 
        decimal_places=2,
        default=0.00
    )
    pdf_file = models.FileField(
        upload_to='orders_pdf/', 
        null=True, 
        blank=True,
        verbose_name='PDF-документ'
    )

    # Методы класса
    @classmethod
    def cancel_unpaid_orders(cls):
        return cls.objects.filter(
            status='new',
            created_at__lt=timezone.now() - timezone.timedelta(days=7)
        ).update(status='canceled')
    
    @classmethod
    def total_revenue(cls):
        return cls.objects.filter(status='completed').aggregate(
            total=Sum('items__product__price' * F('items__quantity'))
        )['total'] or 0

    # Методы экземпляра
    def generate_pdf(self):
        """Метод для генерации PDF-файла заказа"""
        try:
            buffer = BytesIO()
            p = canvas.Canvas(buffer, pagesize=letter)
            
            # Добавляем информацию о заказе
            p.drawString(100, 750, f"Заказ №{self.id}")
            p.drawString(100, 730, f"Статус: {self.get_status_display()}")
            p.drawString(100, 710, f"Дата: {self.created_at.strftime('%d.%m.%Y %H:%M')}")
            p.drawString(100, 690, f"Клиент: {self.full_name}")
            p.drawString(100, 670, f"Телефон: {self.phone}")
            p.drawString(100, 650, f"Email: {self.email}")
            p.drawString(100, 630, f"Адрес: {self.shipping_address}")
            p.drawString(100, 610, f"Способ оплаты: {self.get_payment_method_display()}")
            p.drawString(100, 590, f"Сумма: {self.total_price} руб.")
            
            # Добавляем список товаров
            y_position = 550
            p.drawString(100, y_position, "Состав заказа:")
            y_position -= 20
            
            for item in self.items.all():
                p.drawString(120, y_position, f"- {item.product.title}: {item.quantity} × {item.product.price} руб.")
                y_position -= 20
                if y_position < 100:
                    p.showPage()
                    y_position = 750
            
            p.showPage()
            p.save()

            buffer.seek(0)
            self.pdf_file.save(f'order_{self.id}.pdf', ContentFile(buffer.read()))
            self.save()
            return True
        except Exception as e:
            print(f"Ошибка генерации PDF: {str(e)}")
            return False

    @property
    def calculated_total(self):
        """Динамически вычисляемая сумма заказа"""
        return self.items.aggregate(
            total=Sum(F('quantity') * F('product__price'))
        )['total'] or 0

    # Метаданные
    class Meta:
        verbose_name = 'Заказ'
        verbose_name_plural = 'Заказы'
        ordering = ['-created_at']

    def __str__(self):
        return f"Заказ #{self.id} ({self.get_status_display()})"


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items'  
    )
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField('Количество', default=1)

    class Meta:
        verbose_name = 'Товары в заказе'
        verbose_name_plural = 'Товары в заказах'

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
@receiver(pre_save, sender=Order)
def generate_order_pdf(sender, instance, **kwargs):
    if instance.status == 'completed' and not instance.pdf_file:
        instance.generate_pdf()



from django.test import TestCase
from django.contrib.auth.models import User
from django.db.models import Count, Avg
from django.utils import timezone
from .models import (
    Category, Product, UserProfile, Basket, BasketItem, 
    Order, OrderItem, Article, Discount
)

class ModelTests(TestCase):
    def setUp(self):
        # Создаем тестовые данные
        self.user = User.objects.create_user(
            username='testuser', 
            password='testpass123',
            first_name='Test',
            last_name='User'
        )
        self.category = Category.objects.create(name='Electronics')
        self.product = Product.objects.create(
            title='iPhone 13',
            price=79990.00,
            manufacturer='Apple',
            category=self.category
        )
        self.discount = Discount.objects.create(
            product=self.product,
            percent=10,
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timezone.timedelta(days=7)
        )

    def test_category_creation(self):
        """Тест создания категории"""
        self.assertEqual(self.category.name, 'Electronics')
        self.assertEqual(str(self.category), 'Electronics')
        
    def test_product_creation(self):
        """Тест создания продукта"""
        self.assertEqual(self.product.title, 'iPhone 13')
        self.assertEqual(self.product.price, 79990.00)
        self.assertEqual(self.product.manufacturer, 'Apple')
        self.assertEqual(self.product.category, self.category)
        self.assertTrue(self.product.is_active)
        self.assertIsNotNone(self.product.created_at)
        self.assertIsNotNone(self.product.updated_at)
        
    def test_user_profile_creation(self):
        """Тест создания профиля пользователя"""
        profile = UserProfile.objects.create(
            user=self.user,
            phone='+79991234567',
            address='Test Address',
            role='admin'
        )
        self.assertEqual(profile.phone, '+79991234567')
        self.assertEqual(profile.address, 'Test Address')
        self.assertEqual(profile.role, 'admin')
        self.assertEqual(str(profile), f"Профиль {self.user.username}")
        
    def test_basket_operations(self):
        """Тест операций с корзиной"""
        basket = Basket.objects.create(user=self.user)
        basket_item = BasketItem.objects.create(
            basket=basket,
            product=self.product,
            quantity=2
        )
        
        self.assertEqual(basket.user, self.user)
        self.assertEqual(basket_item.quantity, 2)
        self.assertEqual(basket_item.total_price, self.product.price * 2)
        self.assertEqual(basket.total_price, self.product.price * 2)
        
    def test_order_creation(self):
        """Тест создания заказа"""
        order = Order.objects.create(
            user=self.user,
            status='new',
            full_name='Test User',
            email='test@example.com',
            phone='+79991234567',
            shipping_address='Test Address',
            payment_method='card',
            total_price=159980.00
        )
        order_item = OrderItem.objects.create(
            order=order,
            product=self.product,
            quantity=2
        )
        
        self.assertEqual(order.user, self.user)
        self.assertEqual(order.status, 'new')
        self.assertEqual(order.total_price, 159980.00)
        self.assertEqual(order_item.quantity, 2)
        self.assertEqual(order.calculated_total, self.product.price * 2)
        
    def test_article_creation(self):
        """Тест создания статьи"""
        article = Article.objects.create(
            title='New iPhone Review',
            teaser='Review of the latest iPhone',
            full_text='Detailed review...',
            source_url='https://example.com/review'
        )
        article.categories.add(self.category)
        
        self.assertEqual(article.title, 'New iPhone Review')
        self.assertEqual(article.teaser, 'Review of the latest iPhone')
        self.assertIn(self.category, article.categories.all())
        
    def test_discount_functionality(self):
        """Тест функциональности скидки"""
        self.assertTrue(self.product.has_active_discount)
        self.assertEqual(self.product.current_discount, self.discount)
        self.assertEqual(self.discount.percent, 10)
        
    def test_category_relations(self):
        """Тест связей категории"""
        # Проверка связи продукта с категорией
        self.assertEqual(self.category.products.first(), self.product)
        
        # Используем другое имя для аннотации, чтобы избежать конфликта
        category = Category.objects.annotate(
            num_products=Count('products'),
            average_price=Avg('products__price')
        ).get(pk=self.category.pk)
        
        self.assertEqual(category.num_products, 1)
        self.assertEqual(category.average_price, self.product.price)
        
    def test_user_profile_relations(self):
        """Тест связей профиля пользователя"""
        profile = UserProfile.objects.create(
            user=self.user,
            role='admin'
        )
        
        # Проверка связи 1-к-1
        self.assertEqual(self.user.profile, profile)
        self.assertEqual(profile.user, self.user)
        
    def test_basket_relations(self):
        """Тест связей корзины"""
        basket = Basket.objects.create(user=self.user)
        basket_item = BasketItem.objects.create(
            basket=basket,
            product=self.product,
            quantity=1
        )
        
        # Проверка связей
        self.assertEqual(self.user.basket, basket)
        self.assertEqual(basket.items.first(), basket_item)
        self.assertEqual(basket_item.product, self.product)

from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from main.models import Order, User
from main.tasks import cancel_unpaid_orders

class TaskTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='12345')
        
        # Создаем старый неоплаченный заказ
        self.old_order = Order.objects.create(
            user=self.user,
            status='new',
            created_at=timezone.now() - timedelta(days=8)
        )
        
        # Создаем новый заказ
        self.new_order = Order.objects.create(
            user=self.user,
            status='new',
            created_at=timezone.now() - timedelta(days=5))
    
    def test_cancel_unpaid_orders(self):
        # Выполняем задачу
        result = cancel_unpaid_orders.delay()
        result.get()  # Ждем завершения
        
        # Обновляем данные из БД
        self.old_order.refresh_from_db()
        self.new_order.refresh_from_db()
        
        # Проверяем результаты
        self.assertEqual(self.old_order.status, 'canceled')
        self.assertEqual(self.new_order.status, 'new')
        self.assertIn("Отменено 1 неоплаченных заказов", result.result)
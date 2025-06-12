import os
import random
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from django.db import connection, transaction
from django.db.models.deletion import ProtectedError
from main.models import (
    UserProfile, Category, Article, ArticleCategory,
    Product, Discount, Basket, BasketItem, Order, OrderItem, MainPage
)

class Command(BaseCommand):
    help = 'Заполняет базу данных тестовыми данными для магазина техники Apple'

    def handle(self, *args, **kwargs):
        self.stdout.write("Создание тестовых данных для Apple Store...")
        
        with transaction.atomic():
            self.clear_test_data()
            users = self.create_users()
            categories = self.create_categories()
            articles = self.create_articles(categories)
            products = self.create_products(categories)
            discounts = self.create_discounts(products)
            baskets = self.create_baskets(users, products)
      
            mainpage = self.create_mainpage()

        self.stdout.write(self.style.SUCCESS("✅ База данных успешно заполнена!"))

    def clear_test_data(self):
        # Удаляем пользователей и связанные объекты
        User.objects.filter(username__startswith='user').delete()
        
        # Удаляем объекты в правильном порядке с учетом зависимостей
        models = [
            OrderItem, Order,  # Сначала удаляем дочерние элементы заказов
            BasketItem, Basket,
            Discount,
            ArticleCategory, Article,
            Product,
            Category,
            MainPage,
            UserProfile,
        ]
        
        for model in models:
            try:
                model.objects.all().delete()
            except ProtectedError:
                # Если есть защищенные связи, пропускаем - они будут удалены выше
                pass

        # Универсальный и безопасный сброс автоинкремента
        self.reset_sequences()

        self.stdout.write("🗑️ Старые тестовые данные удалены")

    def reset_sequences(self):
        """Сброс последовательностей для всех моделей с учетом СУБД"""
        with connection.cursor() as cursor:
            if connection.vendor == 'sqlite':
                # Для SQLite
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = [row[0] for row in cursor.fetchall()]
                for table in tables:
                    if table.startswith('main_'):
                        cursor.execute(f"DELETE FROM sqlite_sequence WHERE name='{table}';")
                        cursor.execute(f"UPDATE sqlite_sequence SET seq=0 WHERE name='{table}';")
            
            elif connection.vendor == 'postgresql':
                # Для PostgreSQL
                cursor.execute("""
                    SELECT c.relname
                    FROM pg_class c
                    JOIN pg_namespace n ON c.relnamespace = n.oid
                    WHERE c.relkind = 'S' AND n.nspname = 'public';
                """)
                sequences = [row[0] for row in cursor.fetchall()]
                for seq in sequences:
                    if seq.startswith('main_'):
                        cursor.execute(f"ALTER SEQUENCE {seq} RESTART WITH 1;")
            else:
                self.stdout.write(self.style.WARNING("⚠️ Сброс автоинкремента не поддерживается для текущей СУБД"))

    def create_users(self):
        users = []
        first_names = ["Иван", "Алексей", "Мария", "Екатерина", "Дмитрий", "Ольга", "Сергей", "Анна", "Андрей", "Наталья"]
        last_names = ["Иванов", "Петров", "Сидорова", "Смирнова", "Кузнецов", "Васильева", "Попов", "Павлова", "Соколов", "Михайлова"]

        for i in range(1, 11):
            username = f'user{i}'
            user = User.objects.create_user(
                username=username,
                email=f'user{i}@example.com',
                password='password123',
                first_name=first_names[i - 1],
                last_name=last_names[i - 1]
            )
            profile = UserProfile.objects.create(
                user=user,
                phone=f'+7 (900) 123-{i:02d}',
                address=f'г. Москва, ул. Яблочная, д. {i}, кв. {i}'
            )
            users.append(profile)
            self.stdout.write(f"👤 Создан пользователь: {user.get_full_name()}")

        return users

    def create_categories(self):
        names = [
            "iPhone", "Mac", "iPad", "Apple Watch", "AirPods",
            "Apple TV", "HomePod", "Аксессуары", "Программное обеспечение", "Сервисы"
        ]
        categories = []
        for name in names:
            category, _ = Category.objects.get_or_create(name=name)
            categories.append(category)
            self.stdout.write(f"📁 Создана категория: {name}")
        return categories

    def create_articles(self, categories):
        articles = []
        titles = [
            "Новый iPhone 15: революция в камере",
            "MacBook Pro с M2: производительность нового уровня",
            "Как выбрать iPad для работы и творчества",
            "Apple Watch Series 9: здоровье под контролем",
            "AirPods Pro 2: чистейший звук",
            "iMac 24″: стиль и мощность",
            "Mac Pro: монстр производительности",
            "Apple TV 4K: кинотеатр дома",
            "HomePod mini: умный помощник",
            "Лучшие аксессуары Apple 2023"
        ]

        for i, title in enumerate(titles):
            article = Article.objects.create(
                title=title,
                teaser=f"{title} - подробный обзор",
                full_text=f"<p>{title} — полное описание.</p>" * 5,
                is_featured=(i == 0)
            )
            ArticleCategory.objects.create(
                article=article,
                category=categories[i % len(categories)],
                weight=random.randint(1, 5)
            )
            articles.append(article)
            self.stdout.write(f"📰 Создана статья: {title}")
        return articles

    def create_products(self, categories):
        products = []
        data = [
            {"name": "iPhone 15 Pro", "price": 99990, "category": "iPhone"},
            {"name": "MacBook Air M2", "price": 119990, "category": "Mac"},
            {"name": "iPad Pro", "price": 109990, "category": "iPad"},
            {"name": "Apple Watch Ultra 2", "price": 79990, "category": "Apple Watch"},
            {"name": "AirPods Pro 2", "price": 24990, "category": "AirPods"},
            {"name": "Apple TV 4K", "price": 14990, "category": "Apple TV"},
            {"name": "HomePod mini", "price": 9990, "category": "HomePod"},
            {"name": "MagSafe Charger", "price": 4990, "category": "Аксессуары"},
            {"name": "iCloud+ 2TB", "price": 1490, "category": "Сервисы"},
            {"name": "Final Cut Pro", "price": 29990, "category": "Программное обеспечение"},
        ]
        for i, item in enumerate(data):
            category = next(c for c in categories if c.name == item["category"])
            product = Product.objects.create(
                title=item["name"],
                description=f"{item['name']} — отличный выбор.",
                price=item["price"],
                category=category,
                is_active=(i % 5 != 0)
            )
            products.append(product)
            self.stdout.write(f"📱 Создан продукт: {product.title}")
        return products

    def create_discounts(self, products):
        discounts = []
        for product in products:
            if product.is_active and random.random() < 0.4:
                discount = Discount.objects.create(
                    product=product,
                    percent=random.randint(5, 30),
                    start_date=timezone.now().date() - timedelta(days=random.randint(0, 5)),
                    end_date=timezone.now().date() + timedelta(days=random.randint(5, 30))
                )
                discounts.append(discount)
                self.stdout.write(f"🎁 Скидка: {discount.percent}% на {product.title}")
        return discounts

    def create_baskets(self, users, products):
        baskets = []
        for profile in users:
            basket = Basket.objects.create(user=profile.user)
            added_products = set()
            for _ in range(random.randint(1, 5)):
                product = random.choice(products)
                if product.id in added_products:
                    item = BasketItem.objects.get(basket=basket, product=product)
                    item.quantity += random.randint(1, 2)
                    item.save()
                else:
                    BasketItem.objects.create(
                        basket=basket,
                        product=product,
                        quantity=random.randint(1, 3)
                    )
                    added_products.add(product.id)
            baskets.append(basket)
            self.stdout.write(f"🛒 Корзина для {profile.user.username}")
        return baskets

  

    def create_mainpage(self):
        if not MainPage.objects.exists():
            mainpage = MainPage.objects.create(
                title="Apple Store - Магазин Apple",
                subtitle="Легендарные продукты по лучшим ценам"
            )
            self.stdout.write("🏠 Главная страница создана")
            return mainpage
        return MainPage.objects.first()
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
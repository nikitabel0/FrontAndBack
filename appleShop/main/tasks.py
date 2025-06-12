# main/tasks.py
from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from .models import Order, Product, User
from django.db.models import Sum, F 


@shared_task
def cancel_unpaid_orders():
    """Отмена неоплаченных заказов через 7 дней"""
    count = Order.cancel_unpaid_orders()
    return f'Отменено {count} неоплаченных заказов'

@shared_task
def generate_order_pdfs():
    """Генерация PDF для завершенных заказов"""
    orders = Order.objects.filter(status='completed', pdf_file__isnull=True)
    for order in orders:
        order.generate_pdf()
    return f'Сгенерировано PDF для {orders.count()} заказов'

@shared_task
def send_weekly_stats():
    """Рассылка еженедельной статистики администраторам"""
    admins = User.objects.filter(
        is_superuser=True
    ) | User.objects.filter(profile__role='admin')
    
    # Сбор статистики
    stats = {
        'user_count': User.objects.count(),
        'order_count': Order.objects.count(),
        'product_count': Product.objects.count(),
        'revenue': Order.objects.filter(status='completed').aggregate(
            total=Sum('calculated_total')
        )['total'] or 0
    }
    
    # Формирование сообщения
    message = f"""
    Еженедельная статистика:
    - Пользователей: {stats['user_count']}
    - Заказов: {stats['order_count']}
    - Товаров: {stats['product_count']}
    - Выручка: {stats['revenue']} ₽
    """
    
    # Отправка email
    for admin in admins:
        send_mail(
            'Еженедельная статистика магазина',
            message,
            settings.DEFAULT_FROM_EMAIL,
            [admin.email],
            fail_silently=False,
        )
    
    return f'Отчет отправлен {admins.count()} администраторам'
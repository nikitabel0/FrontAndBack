from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from .models import *
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from django.template.loader import render_to_string
from django.core.files.base import ContentFile
from .models import *
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle
from django.dispatch import receiver
from django.db.models.signals import pre_save
from django.db.models import Q 
from django.http import HttpResponse  
import csv 



@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone_short', 'address_short','role')
    list_display_links = ('user',)  
    search_fields = ('user__username', 'phone')
    list_filter = ('user__is_active',)
    raw_id_fields = ('user',) 

    @admin.display(description='Телефон')
    def phone_short(self, obj):
        return obj.phone[:15] + '...' if len(obj.phone) > 15 else obj.phone

    @admin.display(description='Адрес')
    def address_short(self, obj):
        return obj.address[:50] + '...' if len(obj.address) > 50 else obj.address

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'product_count', 'article_count','active_product_count')
    search_fields = ('name',)
    list_display_links = ('name',)  
    def get_queryset(self, request):
  
        return super().get_queryset(request).annotate(
            total_products=Count('products'),
            active_products=Count('products', filter=Q(products__is_active=True))
        )
    
    @admin.display(description='Всего товаров')
    def product_count(self, obj):
        return obj.total_products  
    
    @admin.display(description='Активных товаров')
    def active_product_count(self, obj):
        return obj.active_products  

    @admin.display(description='Товаров')
    def product_count(self, obj):
        return obj.products.count()

    @admin.display(description='Статей')
    def article_count(self, obj):
        return obj.articles.count()

@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ('title', 'published_at', 'categories_list', 'source_link')
    list_filter = ('published_at', 'categories')
    search_fields = ('title', 'teaser')
    date_hierarchy = 'published_at'

    readonly_fields = ('preview_text',)
    @admin.display(description='Источник')
    def source_link(self, obj):
        if obj.source_url:
            return format_html('<a href="{0}">{0}</a>', obj.source_url)
        return "-"

    @admin.display(description='Категории')
    def categories_list(self, obj):
        return ", ".join([c.name for c in obj.categories.all()])

    @admin.display(description='Превью текста')
    def preview_text(self, obj):
        return obj.full_text[:500] + '...' if len(obj.full_text) > 500 else obj.full_text

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('product', 'quantity', 'get_total_price')
    
    @admin.display(description='Сумма')
    def get_total_price(self, obj):
        return obj.quantity * obj.product.price

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('image_preview', 'title', 'price', 'category_link', 
                   'is_active', 'current_discount_info', 'is_new','has_discount_indicator')
    list_display_links = ('title',) 
    list_filter = ('category', 'is_active', 'created_at')
    search_fields = ('title__icontains', 'description__icontains')
    list_editable = ('price', 'is_active')
    readonly_fields = ('image_preview', 'created_at', 'updated_at')
    raw_id_fields = ('category',)
    date_hierarchy = 'created_at'
    actions = ('activate_selected', 'deactivate_selected')
    actions = ['export_selected']
    @admin.action(description="Экспорт выбранных в CSV")
    def export_selected(self, request, queryset):
        # быстрого экспорта
        data = queryset.values_list('id', 'title', 'price', 'category__name')
        
        response = HttpResponse(content_type='text/csv')
        writer = csv.writer(response)
        writer.writerow(['ID', 'Название', 'Цена', 'Категория'])
        
        for row in data:
            writer.writerow(row)
        
        return response


    fieldsets = (
        (None, {
            'fields': ('title', 'description', 'price', 'category')
        }),
        ('Изображение', {
            'fields': ('image', 'image_preview'),
        }),
        ('Статус', {
            'fields': ('is_active', 'created_at', 'updated_at'),
        }),
    )
    actions = ('activate_selected', 'deactivate_selected', 'delete_selected')

    @admin.display(description='Есть скидка', boolean=True)
    def has_discount_indicator(self, obj):
        return obj.discounts.filter(
            start_date__lte=timezone.now().date(),
            end_date__gte=timezone.now().date()
        ).exists()

    @admin.action(description="Удалить выбранные товары")
    def delete_selected(self, request, queryset):
        deleted_count, _ = queryset.delete()
        self.message_user(request, f"Удалено {deleted_count} товаров")

    @admin.display(description='Превью')
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-height: 50px;"/>', obj.image.url)
        return "-"

    @admin.display(description='Категория')
    def category_link(self, obj):
        if obj.category:
            url = reverse('admin:main_category_change', args=[obj.category.id])
            return format_html('<a href="{}">{}</a>', url, obj.category.name)
        return "-"

    @admin.display(description='Текущая скидка')
    def current_discount_info(self, obj):
        discount = obj.current_discount
        if discount:
            return f"{discount.percent}% до {discount.end_date}"
        return "Нет скидки"

    @admin.display(description='Новый товар?')
    def is_new(self, obj):
        return (timezone.now() - obj.created_at).days < 3

    @admin.action(description="Активировать выбранные товары")
    def activate_selected(self, request, queryset):
        queryset.update(is_active=True)

    @admin.action(description="Деактивировать выбранные товары")
    def deactivate_selected(self, request, queryset):
        queryset.update(is_active=False)

@admin.register(Discount)
class DiscountAdmin(admin.ModelAdmin):
    list_display = ('product', 'percent', 'date_range', 'is_active')
    list_filter = ('start_date', 'end_date')
    search_fields = ('product__title',)
    date_hierarchy = 'start_date'
    list_display_links = ('product',)  

    @admin.display(description='Период действия')
    def date_range(self, obj):
        return f"{obj.start_date} - {obj.end_date}"

    @admin.display(description='Активна', boolean=True)
    def is_active(self, obj):
        return obj.start_date <= timezone.now().date() <= obj.end_date

class BasketItemInline(admin.TabularInline):
    model = BasketItem
    extra = 0
    readonly_fields = ('product', 'quantity', 'get_total_price')
    
    @admin.display(description='Сумма')
    def get_total_price(self, obj):
        return obj.quantity * obj.product.price

@admin.register(Basket)
class BasketAdmin(admin.ModelAdmin):
    list_display = ('user', 'created_at', 'total_price')
    list_filter = ('created_at',)
    search_fields = ('user__username',)
    inlines = (BasketItemInline,)
    readonly_fields = ('total_price',)
    date_hierarchy = 'created_at'

    @admin.display(description='Общая стоимость')
    def total_price(self, obj):
        return obj.total_price

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user_emails','user', 'status', 'created_at', 'total_price', 'pdf_link')
    list_filter = ('status', 'created_at')
    search_fields = ('user__username', 'id')
    inlines = (OrderItemInline,)
    readonly_fields = ('total_price',)
    actions = ('mark_completed', 'generate_pdf_action')
    date_hierarchy = 'created_at'
    def user_emails(self, obj):
        emails = obj.user.profile.user.order_set.values_list('user__email', flat=True).distinct()
        return ", ".join(emails)
    user_emails.short_description = 'Emails'

    def product_names(self, obj):
        products = obj.items.values('product__title')
        return ", ".join([p['product__title'] for p in products])
    product_names.short_description = 'Товары'

    @admin.display(description='PDF')
    def pdf_link(self, obj):
        if obj.pdf_file:
            return format_html('<a href="{}" target="_blank">Скачать PDF</a>', obj.pdf_file.url)
        return "Файл не сгенерирован"

    @admin.action(description="Сгенерировать PDF")
    def generate_pdf_action(self, request, queryset):
        for order in queryset:
            if order.generate_pdf():
                self.message_user(request, f"PDF для заказа {order.id} успешно создан")
            else:
                self.message_user(request, f"Ошибка генерации PDF для заказа {order.id}", level='ERROR')
    def generate_pdf(self):
        try:
            buffer = BytesIO()
            p = canvas.Canvas(buffer, pagesize=letter)
            width, height = letter

       
            p.setFont("Helvetica-Bold", 16)
            p.drawString(100, height - 100, f"Заказ №{self.id}")

  
            p.setFont("Helvetica", 12)
            y_position = height - 140
            profile = self.user.userprofile
            lines = [
                f"Дата: {self.created_at.strftime('%d.%m.%Y %H:%M')}",
                f"Статус: {self.get_status_display()}",
                f"Пользователь: {profile.user.username}",
                f"Телефон: {profile.phone or 'не указан'}",
                f"Адрес: {profile.address or 'не указан'}"
            ]

            for line in lines:
                p.drawString(100, y_position, line)
                y_position -= 30

     
            data = [['Товар', 'Цена', 'Количество', 'Сумма']]
            for item in self.items.all():
                data.append([
                    item.product.title,
                    f"{item.product.price} ₽",
                    str(item.quantity),
                    f"{item.quantity * item.product.price} ₽"
                ])

            table = Table(data, colWidths=[300, 80, 80, 80])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.grey),
                ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                ('FONTSIZE', (0,0), (-1,0), 12),
                ('BOTTOMPADDING', (0,0), (-1,0), 12),
                ('BACKGROUND', (0,1), (-1,-1), colors.beige),
                ('GRID', (0,0), (-1,-1), 1, colors.black)
            ]))

            table.wrapOn(p, width - 200, height)
            table.drawOn(p, 100, y_position - 150)

     
            p.setFont("Helvetica-Bold", 14)
            p.drawString(100, 100, f"Итого: {self.total_price} ₽")

            p.showPage()
            p.save()

            buffer.seek(0)
            self.pdf_file.save(f'order_{self.id}.pdf', ContentFile(buffer.read()))
            self.save()
            return True
        except Exception as e:
            print(f"Ошибка генерации PDF: {str(e)}")
            return False

    @receiver(pre_save, sender=Order)
    def generate_order_pdf(sender, instance, **kwargs):
        print(f"Сработал сигнал для заказа {instance.id}. Статус: {instance.status}, PDF существует: {bool(instance.pdf_file)}")
        if instance.status == 'completed' and not instance.pdf_file:
            print("Условия для генерации PDF выполнены")
            instance.generate_pdf()


    @admin.action(description="Пометить как завершенные")
    def mark_completed(self, request, queryset):
        updated = queryset.update(status='completed')
        self.message_user(request, f"{updated} заказов помечены как завершенные")

@admin.register(MainPage)
class MainPageAdmin(admin.ModelAdmin):
    list_display = ('image_preview', 'title', 'is_active', 'created_at')
    list_editable = ('is_active',)
    search_fields = ('title', 'subtitle')
    readonly_fields = ('image_preview',)
    date_hierarchy = 'created_at'
    list_display_links = ('title',)  

    @admin.display(description='Превью')
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-height: 50px;"/>', obj.image.url)
        return "-"
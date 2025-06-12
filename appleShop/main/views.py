from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required, user_passes_test
from .forms import ProductForm, UserRegistrationForm, CheckoutForm
from django.contrib.auth.models import User
from django.contrib.auth.views import LoginView, LogoutView
from django.db.models import Prefetch
from django.db.models import Sum, Count, Avg, F, ExpressionWrapper, DecimalField
from .models import (
    Product, Article, Order, OrderItem, 
    Category, Basket, BasketItem, UserProfile
)
from .serializers import (
    ProductSerializer, OrderSerializer, ArticleSerializer, 
    CategorySerializer, BasketSerializer, UserProfileSerializer
)
from django.http import (
    HttpRequest, HttpResponse, HttpResponseBadRequest, 
    HttpResponseRedirect, JsonResponse
)
from django.contrib import messages
from silk.profiling.profiler import silk_profile
from rest_framework import viewsets
from .filters import ProductFilter
from typing import Union, Optional, Dict, Any, Type


def admin_check(user: User) -> bool:
    """
    Проверяет, является ли пользователь администратором.

    Args:
        user: Объект пользователя Django

    Returns:
        bool: True если пользователь суперпользователь или администратор, иначе False
    """
    return user.is_superuser or (
        user.is_authenticated 
        and hasattr(user, 'profile') 
        and user.profile.role == 'admin'
    )


@login_required
def add_to_basket(request: HttpRequest, product_id: int) -> HttpResponseRedirect:
    """
    Добавляет товар в корзину пользователя.

    Получает товар по ID и добавляет указанное количество в корзину.
    Если товар уже есть в корзине, увеличивает его количество.

    Args:
        request: HTTP-запрос (должен содержать POST-данные)
        product_id: ID добавляемого товара

    Returns:
        HttpResponseRedirect: Перенаправление на страницу товара
    """
    product = get_object_or_404(Product, pk=product_id)
    quantity = int(request.POST.get('quantity', 1))
    
    # Получаем или создаем корзину пользователя
    basket, created = Basket.objects.get_or_create(user=request.user)
    
    # Добавляем товар в корзину
    basket_item, created = BasketItem.objects.get_or_create(
        basket=basket,
        product=product,
        defaults={'quantity': quantity}
    )
    
    if not created:
        basket_item.quantity += quantity
        basket_item.save()
    
    messages.success(request, f'Товар "{product.title}" добавлен в корзину')
    return redirect('main:product_detail', pk=product_id)


@silk_profile(name='Product Detail')
def product_detail(request: HttpRequest, pk: int) -> HttpResponse:
    """
    Отображает детальную информацию о товаре.

    Показывает информацию о товаре, его доступность в корзине текущего пользователя
    и обрабатывает добавление товара в корзину.

    Args:
        request: HTTP-запрос
        pk: ID товара

    Returns:
        HttpResponse: Рендер шаблона product_detail.html с контекстом
    """
    product = get_object_or_404(Product, pk=pk)
    in_basket = False
    
    if request.user.is_authenticated:
        basket, _ = Basket.objects.get_or_create(user=request.user)
        in_basket = basket.items.filter(product=product).exists()
        
        if request.method == 'POST' and 'add_to_basket' in request.POST:
            quantity = int(request.POST.get('quantity', 1))
            item, created = BasketItem.objects.get_or_create(
                basket=basket,
                product=product,
                defaults={'quantity': quantity}
            )
            if not created:
                item.quantity += quantity
                item.save()
            return redirect('main:basket')
        
    if request.method == 'POST' and 'add_to_basket' in request.POST:
        return redirect('main:basket')
    
    return render(request, 'product_detail.html', {
        'product': product,
        'in_basket': in_basket
    })


@login_required
def basket_view(request: HttpRequest) -> HttpResponse:
    """
    Отображает содержимое корзины пользователя.

    Args:
        request: HTTP-запрос

    Returns:
        HttpResponse: Рендер шаблона basket.html с содержимым корзины
    """
    basket = get_object_or_404(Basket, user=request.user)
    return render(request, 'basket.html', {'basket': basket})


@login_required
def update_basket_item(request: HttpRequest, item_id: int) -> HttpResponseRedirect:
    """
    Обновляет или удаляет товар в корзине пользователя.

    Обрабатывает изменение количества товара или его удаление из корзины.

    Args:
        request: HTTP-запрос (POST с данными для обновления)
        item_id: ID элемента корзины для обновления

    Returns:
        HttpResponseRedirect: Перенаправление на страницу корзины
    """
    item = get_object_or_404(BasketItem, id=item_id, basket__user=request.user)
    
    if request.method == 'POST':
        # Обновление количества
        if 'quantity' in request.POST:
            quantity = int(request.POST['quantity'])
            if quantity > 0:
                item.quantity = quantity
                item.save()
            else:
                item.delete()
        
        # Удаление товара
        elif 'delete' in request.POST:
            item.delete()
    
    return redirect('main:basket')


def register(request: HttpRequest) -> Union[HttpResponse, HttpResponseRedirect]:
    """
    Обрабатывает регистрацию нового пользователя.

    Отображает форму регистрации и обрабатывает ее отправку.

    Args:
        request: HTTP-запрос

    Returns:
        Union[HttpResponse, HttpResponseRedirect]: 
            Форма регистрации или перенаправление на главную страницу
    """
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('main:home')
    else:
        form = UserRegistrationForm()
    return render(request, 'registration/register.html', {'form': form})


@silk_profile(name='Home View')
def home(request: HttpRequest) -> HttpResponse:
    """
    Отображает домашнюю страницу магазина.

    Показывает новые товары, последние статьи и применяет фильтры из GET-параметров.

    Args:
        request: HTTP-запрос с возможными параметрами фильтрации

    Returns:
        HttpResponse: Рендер шаблона home.html с контекстом
    """
    # Применяем фильтрацию
    product_filter = ProductFilter(
        request.GET, 
        queryset=Product.objects.active()
    )
    
    # Получаем отфильтрованные товары
    filtered_products = product_filter.qs
    
    # Берем 4 последних товара для блока "Новые товары"
    new_products = filtered_products.order_by('-created_at')[:4]
    
    # Последние новости
    recent_articles = Article.objects.order_by('-published_at')[:3]

    context = {
        'new_products': new_products,
        'recent_articles': recent_articles,
        'filter': product_filter,  # Передаем фильтр в шаблон
    }
    return render(request, 'home.html', context)


@login_required
def profile(request: HttpRequest) -> HttpResponse:
    """
    Отображает профиль пользователя.

    Args:
        request: HTTP-запрос

    Returns:
        HttpResponse: Рендер шаблона profile.html
    """
    return render(request, 'profile.html')


class CustomLoginView(LoginView):
    """
    Кастомное представление для входа пользователя.
    
    Настройки:
        template_name: Шаблон для отображения формы входа
        redirect_authenticated_user: Перенаправлять уже авторизованных пользователей
    """
    template_name = 'registration/login.html'
    redirect_authenticated_user = True


class CustomLogoutView(LogoutView):
    """
    Кастомное представление для выхода пользователя.
    
    Настройки:
        next_page: Страница для перенаправления после выхода
    """
    next_page = 'main:home'


@user_passes_test(admin_check)
def admin_dashboard(request: HttpRequest) -> HttpResponse:
    """
    Панель управления администратора.

    Показывает статистику магазина: количество пользователей, заказов, товаров,
    выручку и последние заказы.

    Args:
        request: HTTP-запрос

    Returns:
        HttpResponse: Рендер шаблона admin/dashboard.html
    """
    user_count = User.objects.count()
    order_count = Order.objects.count()
    product_count = Product.objects.count()
    revenue = sum(order.calculated_total for order in Order.objects.filter(status='completed'))
    recent_orders = Order.objects.all().order_by('-created_at')[:10]
    
    return render(request, 'admin/dashboard.html', {
        'user_count': user_count,
        'order_count': order_count,
        'product_count': product_count,
        'revenue': revenue,
        'recent_orders': recent_orders
    })


@user_passes_test(admin_check)
def admin_products(request: HttpRequest) -> HttpResponse:
    """
    Отображает список всех товаров для администратора.

    Args:
        request: HTTP-запрос

    Returns:
        HttpResponse: Рендер шаблона admin/products.html
    """
    products = Product.objects.all().order_by('-created_at')
    return render(request, 'admin/products.html', {'products': products})


@user_passes_test(admin_check)
def admin_product_create(request: HttpRequest) -> Union[HttpResponse, HttpResponseRedirect]:
    """
    Создает новый товар (форма для администратора).

    Args:
        request: HTTP-запрос

    Returns:
        Union[HttpResponse, HttpResponseRedirect]: 
            Форма создания товара или перенаправление на список товаров
    """
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('main:admin_products')
    else:
        form = ProductForm()
    return render(request, 'admin/product_form.html', {'form': form})


@user_passes_test(admin_check)
def admin_product_edit(request: HttpRequest, pk: int) -> Union[HttpResponse, HttpResponseRedirect]:
    """
    Редактирует существующий товар (форма для администратора).

    Args:
        request: HTTP-запрос
        pk: ID редактируемого товара

    Returns:
        Union[HttpResponse, HttpResponseRedirect]: 
            Форма редактирования товара или перенаправление на список товаров
    """
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            return redirect('main:admin_products')
    else:
        form = ProductForm(instance=product)
    return render(request, 'admin/product_form.html', {'form': form})


@user_passes_test(admin_check)
def admin_product_delete(request: HttpRequest, pk: int) -> Union[HttpResponse, HttpResponseRedirect]:
    """
    Удаляет товар (подтверждение и обработка для администратора).

    Args:
        request: HTTP-запрос
        pk: ID удаляемого товара

    Returns:
        Union[HttpResponse, HttpResponseRedirect]: 
            Страница подтверждения удаления или перенаправление на список товаров
    """
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        product.delete()
        return redirect('main:admin_products')
    return render(request, 'admin/product_confirm_delete.html', {'product': product})


@user_passes_test(admin_check)
def admin_users(request: HttpRequest) -> HttpResponse:
    """
    Отображает список всех пользователей для администратора.

    Args:
        request: HTTP-запрос

    Returns:
        HttpResponse: Рендер шаблона admin/users.html
    """
    users = User.objects.all().select_related('profile').order_by('-date_joined')
    return render(request, 'admin/users.html', {'users': users})


@user_passes_test(admin_check)
def admin_user_toggle(request: HttpRequest, user_id: int) -> Union[HttpResponseRedirect, HttpResponseBadRequest]:
    """
    Активирует/деактивирует пользователя.

    Args:
        request: HTTP-запрос (POST)
        user_id: ID пользователя

    Returns:
        Union[HttpResponseRedirect, HttpResponseBadRequest]: 
            Перенаправление на список пользователей или ошибка 400
    """
    user = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        user.is_active = not user.is_active
        user.save()
        action = "разблокирован" if user.is_active else "заблокирован"
        messages.success(request, f'Пользователь {user.username} {action}')
        return redirect('main:admin_users')
    return HttpResponseBadRequest()


@user_passes_test(admin_check)
def admin_user_delete(request: HttpRequest, user_id: int) -> Union[HttpResponse, HttpResponseRedirect]:
    """
    Удаляет пользователя.

    Args:
        request: HTTP-запрос
        user_id: ID удаляемого пользователя

    Returns:
        Union[HttpResponse, HttpResponseRedirect]: 
            Страница подтверждения удаления или перенаправление на список пользователей
    """
    user = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        username = user.username
        user.delete()
        messages.success(request, f'Пользователь {username} удален')
        return redirect('main:admin_users')
    return render(request, 'admin/user_confirm_delete.html', {'user': user})


@user_passes_test(admin_check)
def admin_user_change_role(request: HttpRequest, user_id: int) -> Union[HttpResponseRedirect, HttpResponseBadRequest]:
    """
    Изменяет роль пользователя.

    Args:
        request: HTTP-запрос (POST)
        user_id: ID пользователя

    Returns:
        Union[HttpResponseRedirect, HttpResponseBadRequest]: 
            Перенаправление на список пользователей или ошибка 400
    """
    user = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        new_role = request.POST.get('role')
        if new_role in ['user', 'manager', 'admin']:
            profile = user.profile
            profile.role = new_role
            profile.save()
            messages.success(request, f'Роль пользователя {user.username} изменена на {new_role}')
            return redirect('main:admin_users')
    return HttpResponseBadRequest()


@silk_profile(name='Checkout Process')
@login_required
def checkout(request: HttpRequest) -> Union[HttpResponse, HttpResponseRedirect]:
    """
    Оформление заказа из корзины.

    Проверяет минимальную сумму заказа, обрабатывает форму оформления
    и создает заказ на основе содержимого корзины.

    Args:
        request: HTTP-запрос

    Returns:
        Union[HttpResponse, HttpResponseRedirect]: 
            Форма оформления заказа или перенаправление на подтверждение заказа
    """
    basket = get_object_or_404(Basket, user=request.user)
    
    # Если корзина пуста, перенаправляем обратно
    if not basket.items.exists():
        return redirect('main:basket')
    
    # Проверка минимальной суммы заказа
    min_order_sum = 10000
    if basket.total_price < min_order_sum:
        messages.error(request, f'Минимальная сумма заказа для доставки составляет {min_order_sum} ₽.')
        return redirect('main:basket')
    
    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        if form.is_valid():
            # Создаем заказ
            order = form.save(commit=False)
            order.user = request.user
            order.total_price = basket.total_price
            order.status = 'new'
            order.save()
            
            # Переносим товары из корзины в заказ
            for basket_item in basket.items.all():
                OrderItem.objects.create(
                    order=order,
                    product=basket_item.product,
                    quantity=basket_item.quantity,
                    price=basket_item.product.price
                )
            
            # Очищаем корзину
            basket.items.all().delete()
            
            # Перенаправляем на страницу подтверждения
            return redirect('main:order_confirmation', order_id=order.id)
    else:
        # Предзаполняем форму данными пользователя
        initial = {
            'full_name': f"{request.user.first_name} {request.user.last_name}",
            'email': request.user.email,
        }
        
        if hasattr(request.user, 'profile'):
            profile = request.user.profile
            initial['phone'] = profile.phone
            initial['shipping_address'] = profile.address
        
        form = CheckoutForm(initial=initial)
    
    return render(request, 'checkout.html', {
        'form': form,
        'basket': basket,
        'min_order_sum': min_order_sum
    })


@login_required
def order_confirmation(request: HttpRequest, order_id: int) -> HttpResponse:
    """
    Отображает подтверждение заказа.

    Args:
        request: HTTP-запрос
        order_id: ID заказа

    Returns:
        HttpResponse: Рендер шаблона order_confirmation.html
    """
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, 'order_confirmation.html', {'order': order})


# API Viewsets

class ProductViewSet(viewsets.ModelViewSet):
    """
    ViewSet для управления товарами через API.

    Предоставляет CRUD операции для товаров.
    Включает аннотацию скидочной цены и оптимизацию запросов.
    """
    serializer_class = ProductSerializer
    
    def get_queryset(self) -> Type[Product]:
        """
        Возвращает оптимизированный queryset для товаров.

        Returns:
            Type[Product]: QuerySet товаров с аннотацией скидочной цены
        """
        return Product.objects.annotate(
            discount_price=ExpressionWrapper(
                F('price') * 0.8,
                output_field=DecimalField(max_digits=10, decimal_places=2)
            )
        ).select_related('category').prefetch_related('discounts')


class OrderViewSet(viewsets.ModelViewSet):
    """
    ViewSet для управления заказами через API.

    Предоставляет CRUD операции для заказов.
    Включает аннотацию общей суммы заказа и оптимизацию запросов.
    """
    serializer_class = OrderSerializer
    
    def get_queryset(self) -> Type[Order]:
        """
        Возвращает оптимизированный queryset для заказов.

        Returns:
            Type[Order]: QuerySet заказов с аннотацией общей суммы
        """
        return Order.objects.annotate(
            calculated_total=Sum(F('items__quantity') * F('items__product__price'))
        ).select_related('user').prefetch_related(
            Prefetch('items', queryset=OrderItem.objects.select_related('product'))
        )

    def get_serializer_context(self) -> Dict[str, Any]:
        """
        Добавляет request в контекст сериализатора.

        Returns:
            Dict[str, Any]: Контекст сериализатора с request
        """
        context = super().get_serializer_context()
        context['request'] = self.request
        return context


class ArticleViewSet(viewsets.ModelViewSet):
    """
    ViewSet для управления статьями через API.

    Предоставляет CRUD операции для статей.
    Включает оптимизацию запросов для связанных категорий.
    """
    serializer_class = ArticleSerializer
    queryset = Article.objects.prefetch_related('categories')


class CategoryViewSet(viewsets.ModelViewSet):
    """
    ViewSet для управления категориями через API.

    Предоставляет CRUD операции для категорий.
    Включает аннотацию количества товаров и средней цены.
    """
    serializer_class = CategorySerializer
    
    def get_queryset(self) -> Type[Category]:
        """
        Возвращает оптимизированный queryset для категорий.

        Returns:
            Type[Category]: QuerySet категорий с аннотацией статистики
        """
        return Category.objects.annotate(
            product_count=Count('products'),
            avg_price=Avg('products__price')
        )


class BasketViewSet(viewsets.ModelViewSet):
    """
    ViewSet для управления корзинами через API.

    Предоставляет CRUD операции для корзин.
    Включает оптимизацию запросов для связанных товаров.
    """
    serializer_class = BasketSerializer
    
    def get_queryset(self) -> Type[Basket]:
        """
        Возвращает оптимизированный queryset для корзин.

        Returns:
            Type[Basket]: QuerySet корзин с оптимизацией связанных данных
        """
        return Basket.objects.select_related('user').prefetch_related(
            Prefetch('items', queryset=BasketItem.objects.select_related('product'))
        )

    def get_serializer_context(self) -> Dict[str, Any]:
        """
        Добавляет request в контекст сериализатора.

        Returns:
            Dict[str, Any]: Контекст сериализатора с request
        """
        context = super().get_serializer_context()
        context['request'] = self.request
        return context


class UserProfileViewSet(viewsets.ModelViewSet):
    """
    ViewSet для управления профилями пользователей через API.

    Предоставляет CRUD операции для профилей пользователей.
    Включает оптимизацию запросов для связанных пользователей.
    """
    serializer_class = UserProfileSerializer
    queryset = UserProfile.objects.select_related('user')
from warnings import filters
from django.shortcuts import render
from django.db import models 
from django.db.models import Count 
from rest_framework.filters import SearchFilter, OrderingFilter  

from rest_framework import generics
from .models import Category, MainPage, Product
from .serializers import CategorySerializer, MainPageSerializer, ProductSerializer

from django_filters.rest_framework import DjangoFilterBackend

class MainPageView(generics.ListAPIView):
    queryset = MainPage.objects.filter(is_active=True).order_by('-created_at')
    serializer_class = MainPageSerializer

class ProductListView(generics.ListAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]  
    filterset_fields = ['category']
    search_fields = ['title', 'description']
    ordering_fields = ['price', 'created_at']
class ProductDetailView(generics.RetrieveAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer

class CategoryListView(generics.ListAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
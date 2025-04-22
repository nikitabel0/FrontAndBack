from django.shortcuts import render

from rest_framework import generics
from .models import MainPage
from .serializers import MainPageSerializer

class MainPageView(generics.ListAPIView):
    queryset = MainPage.objects.filter(is_active=True).order_by('-created_at')
    serializer_class = MainPageSerializer

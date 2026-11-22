from rest_framework import viewsets
from django.db.models import Prefetch
from .models import Restaurant, ProductCategory, Product, Order, OrderItem
from .serializers import (
    RestaurantSerializer,
    RestaurantDetailSerializer,
    ProductCategorySerializer,
    ProductSerializer,
    OrderSerializer,
    OrderItemSerializer,
)


class RestaurantViewSet(viewsets.ModelViewSet):
    serializer_class = RestaurantSerializer
    queryset = Restaurant.objects.filter(is_active=True)

    def get_queryset(self):
        qs = super().get_queryset()
        if self.action == 'retrieve':
            qs = qs.prefetch_related(
                Prefetch(
                    'categories',
                    queryset=ProductCategory.objects.filter(is_active=True).order_by('id'),
                ),
                Prefetch(
                    'categories__products',
                    queryset=Product.objects.filter(is_active=True).order_by('id'),
                ),
            )
        return qs

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return RestaurantDetailSerializer
        return RestaurantSerializer

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class ProductCategoryViewSet(viewsets.ModelViewSet):
    serializer_class = ProductCategorySerializer
    queryset = ProductCategory.objects.filter(is_active=True)


class ProductViewSet(viewsets.ModelViewSet):
    serializer_class = ProductSerializer
    queryset = Product.objects.filter(is_active=True)


class OrderViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer
    queryset = Order.objects.all()

    def get_queryset(self):
        qs = super().get_queryset().select_related(
            'user', 'restaurant'
        ).prefetch_related('order_items__product')
        user = self.request.user
        if user.is_staff:
            return qs
        return qs.filter(user=user)


class OrderItemViewSet(viewsets.ModelViewSet):
    serializer_class = OrderItemSerializer
    queryset = OrderItem.objects.all()

    def get_queryset(self):
        qs = super().get_queryset().select_related(
            'order', 'product'
        )
        user = self.request.user
        if user.is_staff:
            return qs
        return qs.filter(order__user=user)

from rest_framework.routers import DefaultRouter
from .views import (
    RestaurantViewSet,
    ProductCategoryViewSet,
    ProductViewSet,
    OrderViewSet,
    OrderItemViewSet,
)

router = DefaultRouter()
router.register(r'restaurants', RestaurantViewSet, basename='restaurants')
router.register(r'categories', ProductCategoryViewSet, basename='categories')
router.register(r'products', ProductViewSet, basename='products')
router.register(r'orders', OrderViewSet, basename='orders')
router.register(r'order-items', OrderItemViewSet, basename='order-items')

urlpatterns = router.urls

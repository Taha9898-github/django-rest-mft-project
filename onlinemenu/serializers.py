from rest_framework import serializers
from .models import Restaurant, ProductCategory, Product, Order, OrderItem


class RestaurantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Restaurant
        fields = '__all__'
        read_only_fields = ['owner', 'created_date', 'updated_date']


class ProductCategoryBriefSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductCategory
        fields = ['id', 'name']


class RestaurantDetailSerializer(serializers.ModelSerializer):
    categories = ProductCategoryBriefSerializer(many=True, read_only=True)
    products = serializers.SerializerMethodField()

    class Meta:
        model = Restaurant
        fields = '__all__'
        read_only_fields = ['owner', 'created_date', 'updated_date']

    def get_products(self, obj) -> list:
        first_cat = obj.categories.order_by('id').first()
        if first_cat is None:
            return []
        return ProductSerializer(
            first_cat.products.filter(is_active=True).order_by('id'),
            many=True,
            context=self.context,
        ).data


class ProductCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductCategory
        fields = '__all__'
        read_only_fields = ['restaurant']


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = '__all__'


class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)

    class Meta:
        model = OrderItem
        fields = ['id', 'order', 'product', 'product_name', 'amount']

    def validate(self, attrs):
        order = attrs.get('order', getattr(self.instance, 'order', None))
        product = attrs.get('product', getattr(self.instance, 'product', None))
        request = self.context.get('request')
        if order and request and request.user.is_authenticated and not request.user.is_staff:
            if order.user_id != request.user.pk:
                raise serializers.ValidationError({
                    'order': 'You cannot modify items of another user\'s order.',
                })
        if order and product and product.category:
            if product.category.restaurant_id != order.restaurant_id:
                raise serializers.ValidationError({
                    'product': 'Product does not belong to the order\'s restaurant.',
                })
        return attrs


class OrderSerializer(serializers.ModelSerializer):
    order_items = OrderItemSerializer(many=True, read_only=True)
    total_amount = serializers.IntegerField(read_only=True)
    total_cost = serializers.DecimalField(
        max_digits=12, decimal_places=0, read_only=True
    )

    class Meta:
        model = Order
        fields = ['id', 'user', 'restaurant', 'uuid', 'is_paid',
                  'created_date', 'updated_date', 'order_items',
                  'total_amount', 'total_cost']
        read_only_fields = ['user', 'uuid', 'created_date', 'updated_date']

    def validate(self, attrs):
        if self.instance is None:
            request = self.context.get('request')
            if request is None or not request.user.is_authenticated:
                raise serializers.ValidationError(
                    'Authentication is required to create an order.'
                )
        return attrs

    def create(self, validated_data):
        request = self.context['request']
        validated_data['user'] = request.user
        return super().create(validated_data)

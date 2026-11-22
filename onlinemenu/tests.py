from datetime import time
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from onlinemenu.management.commands.seed_data import (
    CATEGORIES,
    ORDERS,
    PRODUCTS,
    RESTAURANTS,
    SEED_USER,
    seed_database,
    validate_seed_data,
)
from onlinemenu.models import Order, OrderItem, Product, ProductCategory, Restaurant

User = get_user_model()


class SeedDataTestBase:
    """Mixin that seeds the database once per test class."""

    @classmethod
    def setUpTestData(cls):
        seed_database()


class SeedDataTests(SeedDataTestBase, TestCase):
    def test_seed_user_created(self):
        owner = User.objects.get(username=SEED_USER["username"])
        self.assertTrue(owner.check_password(SEED_USER["password"]))

    def test_exactly_two_restaurants(self):
        self.assertEqual(Restaurant.objects.count(), 2)

    def test_exactly_four_categories(self):
        self.assertEqual(ProductCategory.objects.count(), 4)

    def test_exactly_three_products(self):
        self.assertEqual(Product.objects.count(), 3)

    def test_exactly_two_orders(self):
        self.assertEqual(Order.objects.count(), 2)

    def test_exactly_three_order_items(self):
        self.assertEqual(OrderItem.objects.count(), 3)

    def test_validate_seed_data_passes(self):
        is_valid, errors = validate_seed_data()
        self.assertTrue(is_valid, f"Validation errors: {errors}")


class RestaurantTests(SeedDataTestBase, TestCase):
    def test_expected_restaurant_names_exist(self):
        names = set(Restaurant.objects.values_list("name", flat=True))
        for rest in RESTAURANTS:
            self.assertIn(rest["name"], names)

    def test_restaurant_has_open_time_location_and_rank(self):
        for rest_data in RESTAURANTS:
            restaurant = Restaurant.objects.get(name=rest_data["name"])
            self.assertEqual(restaurant.open_time, rest_data["open_time"])
            self.assertEqual(restaurant.location, rest_data["location"])
            self.assertEqual(restaurant.rank, rest_data["rank"])

    def test_open_time_is_time(self):
        for restaurant in Restaurant.objects.all():
            self.assertIsInstance(restaurant.open_time, time)

    def test_rank_is_float(self):
        for restaurant in Restaurant.objects.all():
            self.assertIsInstance(restaurant.rank, float)

    def test_rank_is_between_zero_and_five(self):
        for restaurant in Restaurant.objects.all():
            self.assertGreaterEqual(restaurant.rank, 0)
            self.assertLessEqual(restaurant.rank, 5)

    def test_restaurant_fields_are_valid(self):
        for r in Restaurant.objects.all():
            self.assertTrue(r.name)
            self.assertTrue(r.phone)
            self.assertTrue(r.location)
            self.assertTrue(r.owner_id)

    def test_restaurant_name_phone_location_max_length(self):
        for r in Restaurant.objects.all():
            self.assertLessEqual(len(r.name), 255)
            self.assertLessEqual(len(r.phone), 20)
            self.assertLessEqual(len(r.location), 255)


class CategoryTests(SeedDataTestBase, TestCase):
    def test_categories_match_constants(self):
        for rest_data in RESTAURANTS:
            restaurant = Restaurant.objects.get(name=rest_data["name"])
            expected = {
                cat["name"] for cat in CATEGORIES
                if cat["restaurant"] == restaurant.name
            }
            actual = set(restaurant.categories.values_list("name", flat=True))
            self.assertEqual(actual, expected)

    def test_categories_belong_to_correct_restaurant(self):
        for cat in ProductCategory.objects.select_related("restaurant"):
            self.assertIn(
                cat.restaurant.name,
                {rest["name"] for rest in RESTAURANTS},
            )

    def test_category_name_max_length(self):
        for c in ProductCategory.objects.all():
            self.assertLessEqual(len(c.name), 255)


class ProductTests(SeedDataTestBase, TestCase):
    def test_products_match_constants(self):
        for prod_data in PRODUCTS:
            category = ProductCategory.objects.get(
                restaurant__name=prod_data["restaurant"],
                name=prod_data["category"],
            )
            product = Product.objects.get(
                category=category, name=prod_data["name"]
            )
            self.assertEqual(product.label, prod_data["label"])
            self.assertEqual(product.price, Decimal(prod_data["price"]))

    def test_products_belong_to_correct_category(self):
        for cat in ProductCategory.objects.all():
            for prod in cat.products.all():
                self.assertEqual(prod.category_id, cat.pk)

    def test_product_name_max_length(self):
        for p in Product.objects.all():
            self.assertLessEqual(len(p.name), 255)

    def test_product_price_is_positive_decimal(self):
        for p in Product.objects.all():
            self.assertIsInstance(p.price, Decimal)
            self.assertGreaterEqual(p.price, Decimal(0))

    def test_product_price_max_digits(self):
        for p in Product.objects.all():
            self.assertLessEqual(len(str(int(p.price))), 10)


class OrderTests(SeedDataTestBase, TestCase):
    def test_orders_belong_to_seed_user(self):
        owner = User.objects.get(username=SEED_USER["username"])
        self.assertEqual(Order.objects.filter(user=owner).count(), 2)

    def test_order_totals(self):
        order = Order.objects.get(restaurant__name="Kentacki")
        self.assertEqual(order.total_amount, 3)
        self.assertEqual(order.total_cost, Decimal(180000))

    def test_order_items_match_constants(self):
        order = Order.objects.get(restaurant__name="Kentacki")
        items = {item.product.name: item.amount for item in order.order_items.all()}
        self.assertEqual(items, {"نوشابه": 2, "برگر کلاسیک": 1})

    def test_order_item_product_belongs_to_restaurant(self):
        for item in OrderItem.objects.select_related(
            "order__restaurant", "product__category"
        ):
            self.assertEqual(
                item.product.category.restaurant_id,
                item.order.restaurant_id,
            )

    def test_order_str(self):
        order = Order.objects.first()
        self.assertIn(str(order.uuid), str(order))


class SeedIdempotencyTest(SeedDataTestBase, TestCase):
    def test_running_seed_again_creates_no_duplicates(self):
        counts_before = {
            "restaurants": Restaurant.objects.count(),
            "categories": ProductCategory.objects.count(),
            "products": Product.objects.count(),
            "orders": Order.objects.count(),
            "order_items": OrderItem.objects.count(),
        }

        seed_database()

        self.assertEqual(Restaurant.objects.count(), counts_before["restaurants"])
        self.assertEqual(ProductCategory.objects.count(), counts_before["categories"])
        self.assertEqual(Product.objects.count(), counts_before["products"])
        self.assertEqual(Order.objects.count(), counts_before["orders"])
        self.assertEqual(OrderItem.objects.count(), counts_before["order_items"])

    def test_validate_seed_data_passes_after_reseed(self):
        seed_database()
        is_valid, errors = validate_seed_data()
        self.assertTrue(is_valid, f"Validation errors: {errors}")


class RestaurantDetailAPITests(SeedDataTestBase, TestCase):
    """Tests for /api/v1/restaurants/ endpoints."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.test_user = User.objects.create_user(
            username="testapi", phone="09111111111", password="testpass123"
        )

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=self.test_user)
        self.restaurant = Restaurant.objects.get(name="Kentacki")
        self.url = f"/api/v1/restaurants/{self.restaurant.pk}/"

    def test_detail_returns_200(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_detail_returns_new_fields(self):
        response = self.client.get(self.url)
        self.assertEqual(response.data["open_time"], "10:00:00")
        self.assertEqual(
            response.data["location"], "Tehran, Valiasr St., No. 12"
        )
        self.assertEqual(response.data["rank"], 4.5)

    def test_detail_returns_all_categories(self):
        response = self.client.get(self.url)
        categories = response.data["categories"]
        expected_count = self.restaurant.categories.count()
        self.assertEqual(len(categories), expected_count)
        self.assertEqual(len(categories), 2)

    def test_detail_category_fields_are_brief(self):
        response = self.client.get(self.url)
        for cat in response.data["categories"]:
            self.assertIn("id", cat)
            self.assertIn("name", cat)
            self.assertNotIn("restaurant", cat)

    def test_detail_returns_first_category_products(self):
        response = self.client.get(self.url)
        products = response.data["products"]
        first_cat = self.restaurant.categories.order_by("id").first()
        expected_products = first_cat.products.filter(is_active=True)
        self.assertEqual(len(products), expected_products.count())
        self.assertEqual(len(products), 1)

    def test_detail_products_belong_to_first_category(self):
        response = self.client.get(self.url)
        first_cat = self.restaurant.categories.order_by("id").first()
        product_ids = [p["id"] for p in response.data["products"]]
        expected_ids = list(
            first_cat.products.filter(is_active=True).order_by("id").values_list(
                "id", flat=True
            )
        )
        self.assertEqual(product_ids, expected_ids)

    def test_detail_does_not_return_other_category_products(self):
        response = self.client.get(self.url)
        first_cat = self.restaurant.categories.order_by("id").first()
        other_products = Product.objects.filter(
            category__restaurant=self.restaurant
        ).exclude(category=first_cat)
        product_ids = {p["id"] for p in response.data["products"]}
        for op in other_products:
            self.assertNotIn(op.pk, product_ids)

    def test_detail_no_categories_returns_empty_products(self):
        empty_rest = Restaurant.objects.create(
            name="EmptyPlace",
            phone="021-00000000",
            owner=self.restaurant.owner,
            open_time=time(8, 0),
            location="Nowhere",
            rank=3.0,
        )
        url = f"/api/v1/restaurants/{empty_rest.pk}/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["categories"], [])
        self.assertEqual(response.data["products"], [])

    def test_detail_nonexistent_returns_404(self):
        response = self.client.get("/api/v1/restaurants/99999/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_list_endpoint_returns_active_restaurants(self):
        response = self.client.get("/api/v1/restaurants/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            len(response.data),
            Restaurant.objects.filter(is_active=True).count(),
        )

    def test_create_sets_owner_and_accepts_new_fields(self):
        payload = {
            "name": "NewPlace",
            "phone": "021-55555555",
            "open_time": "08:00",
            "location": "Tehran, Enghelab St.",
            "rank": 3.5,
        }
        response = self.client.post("/api/v1/restaurants/", payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        restaurant = Restaurant.objects.get(name="NewPlace")
        self.assertEqual(restaurant.owner, self.test_user)
        self.assertEqual(restaurant.open_time, time(8, 0))
        self.assertEqual(restaurant.rank, 3.5)

    def test_create_requires_location(self):
        payload = {
            "name": "NoLocation",
            "phone": "021-55555556",
            "open_time": "08:00",
        }
        response = self.client.post("/api/v1/restaurants/", payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("location", response.data)


class CategoryAPITests(SeedDataTestBase, TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.test_user = User.objects.create_user(
            username="categoryapi", phone="09144444444", password="testpass123"
        )

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=self.test_user)
        self.restaurant = Restaurant.objects.get(name="Kentacki")

    def test_create_category_with_restaurant(self):
        response = self.client.post(
            "/api/v1/categories/",
            {"restaurant": self.restaurant.pk, "name": "Salads"},
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            ProductCategory.objects.filter(
                restaurant=self.restaurant, name="Salads"
            ).exists()
        )

    def test_create_category_without_restaurant_rejected(self):
        response = self.client.post(
            "/api/v1/categories/", {"name": "NoRestaurant"}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("restaurant", response.data)


class OrderAPITests(SeedDataTestBase, TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.owner = User.objects.get(username=SEED_USER["username"])
        cls.other_user = User.objects.create_user(
            username="otheruser", phone="09122222222", password="testpass123"
        )
        cls.staff_user = User.objects.create_user(
            username="staffuser",
            phone="09133333333",
            password="testpass123",
            is_staff=True,
        )

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=self.owner)
        self.kentacki = Restaurant.objects.get(name="Kentacki")
        self.twotik = Restaurant.objects.get(name="20Tik")
        self.cola = Product.objects.get(name="نوشابه")
        self.burger = Product.objects.get(name="برگر کلاسیک")
        self.espresso = Product.objects.get(name="اسپرسو")

    def test_orders_require_authentication(self):
        client = APIClient()
        response = client.get("/api/v1/orders/")
        self.assertIn(
            response.status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )

    def test_create_order_sets_request_user(self):
        response = self.client.post(
            "/api/v1/orders/", {"restaurant": self.kentacki.pk}
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        order = Order.objects.get(pk=response.data["id"])
        self.assertEqual(order.user, self.owner)
        self.assertFalse(order.is_paid)

    def test_list_returns_only_own_orders(self):
        response = self.client.get("/api/v1/orders/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        returned_users = {row["user"] for row in response.data}
        self.assertEqual(returned_users, {self.owner.pk})

    def test_list_filters_out_other_users_orders(self):
        self.client.force_authenticate(user=self.other_user)
        response = self.client.get("/api/v1/orders/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    def test_staff_sees_all_orders(self):
        self.client.force_authenticate(user=self.staff_user)
        response = self.client.get("/api/v1/orders/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), Order.objects.count())

    def test_order_detail_contains_totals_and_items(self):
        order = Order.objects.get(user=self.owner, restaurant=self.kentacki)
        response = self.client.get(f"/api/v1/orders/{order.pk}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total_amount"], 3)
        self.assertEqual(Decimal(response.data["total_cost"]), Decimal(180000))
        self.assertEqual(len(response.data["order_items"]), 2)

    def test_create_order_item(self):
        order = Order.objects.get(user=self.owner, restaurant=self.twotik)
        response = self.client.post(
            "/api/v1/order-items/",
            {"order": order.pk, "product": self.espresso.pk, "amount": 2},
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            OrderItem.objects.filter(order=order, product=self.espresso).exists()
        )

    def test_create_order_item_wrong_restaurant_rejected(self):
        order = Order.objects.get(user=self.owner, restaurant=self.twotik)
        response = self.client.post(
            "/api/v1/order-items/",
            {"order": order.pk, "product": self.cola.pk, "amount": 1},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("product", response.data)

    def test_cannot_add_item_to_another_users_order(self):
        order = Order.objects.get(user=self.owner, restaurant=self.kentacki)
        self.client.force_authenticate(user=self.other_user)
        response = self.client.post(
            "/api/v1/order-items/",
            {"order": order.pk, "product": self.cola.pk, "amount": 1},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("order", response.data)

    def test_order_items_list_only_own(self):
        self.client.force_authenticate(user=self.other_user)
        response = self.client.get("/api/v1/order-items/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    def test_order_item_update_amount(self):
        order = Order.objects.get(user=self.owner, restaurant=self.kentacki)
        item = order.order_items.get(product=self.cola)
        response = self.client.patch(
            f"/api/v1/order-items/{item.pk}/", {"amount": 5}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        item.refresh_from_db()
        self.assertEqual(item.amount, 5)

    def test_delete_order(self):
        order = Order.objects.get(user=self.owner, restaurant=self.twotik)
        response = self.client.delete(f"/api/v1/orders/{order.pk}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Order.objects.filter(pk=order.pk).exists())

import glob
import os
import shutil
from datetime import time
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import BaseCommand

from onlinemenu.models import (
    Order,
    OrderItem,
    Product,
    ProductCategory,
    Restaurant,
)

User = get_user_model()

SEED_USER = {
    "username": "seedowner",
    "fullname": "Seed Owner",
    "phone": "09120000000",
    "email": "seedowner@example.com",
    "password": "seedpass123",
}

# Two restaurants.
RESTAURANTS = [
    {
        "name": "Kentacki",
        "label": "Kentacki Fast Food Restaurant",
        "phone": "021-12345678",
        "open_time": time(10, 0),
        "location": "Tehran, Valiasr St., No. 12",
        "rank": 4.5,
    },
    {
        "name": "20Tik",
        "label": "20Tik Café & Restaurant",
        "phone": "021-87654321",
        "open_time": time(9, 30),
        "location": "Tehran, Mirdamad Blvd., No. 88",
        "rank": 4.0,
    },
]

# Four categories in total.
CATEGORIES = [
    {"restaurant": "Kentacki", "name": "Drinks", "label": "نوشیدنی‌ها"},
    {"restaurant": "Kentacki", "name": "Fast Food", "label": "فست فود"},
    {"restaurant": "20Tik", "name": "Cofee", "label": "قهوه"},
    {"restaurant": "20Tik", "name": "Dessert", "label": "دسر"},
]

# Three products in total.
PRODUCTS = [
    {
        "restaurant": "Kentacki",
        "category": "Drinks",
        "name": "نوشابه",
        "label": "Cola",
        "price": 30000,
    },
    {
        "restaurant": "Kentacki",
        "category": "Fast Food",
        "name": "برگر کلاسیک",
        "label": "Classic Burger",
        "price": 120000,
    },
    {
        "restaurant": "20Tik",
        "category": "Cofee",
        "name": "اسپرسو",
        "label": "Espresso",
        "price": 55000,
    },
]

# Two sample orders (three order items in total) for the seed owner.
ORDERS = [
    {
        "restaurant": "Kentacki",
        "is_paid": True,
        "items": [
            {"product": "نوشابه", "amount": 2},
            {"product": "برگر کلاسیک", "amount": 1},
        ],
    },
    {
        "restaurant": "20Tik",
        "is_paid": False,
        "items": [
            {"product": "اسپرسو", "amount": 3},
        ],
    },
]

LOCAL_APPS = ["account", "onlinemenu"]


def _get_local_app_migrations_dirs():
    """Return migration directories for local apps only."""
    dirs = []
    for app_label in LOCAL_APPS:
        app_config_path = Path(settings.BASE_DIR) / app_label / "migrations"
        if app_config_path.is_dir():
            dirs.append(app_config_path)
    return dirs


def reset_database(stdout=None, style=None):
    """Delete the SQLite database file and local app migration files."""
    log = stdout or open(os.devnull, "w")
    msg = style.SUCCESS if style else lambda x: x

    # 1. Delete the database file
    db_path = Path(settings.DATABASES["default"]["NAME"])
    if db_path.exists():
        db_path.unlink()
        log.write(msg(f"  Deleted database: {db_path}"))
    else:
        log.write(f"  Database file not found, skipping: {db_path}")

    # 2. Delete migration files (keep __init__.py and directories)
    for migrations_dir in _get_local_app_migrations_dirs():
        py_files = glob.glob(str(migrations_dir / "*.py"))
        for f in py_files:
            if os.path.basename(f) == "__init__.py":
                continue
            os.remove(f)
            log.write(msg(f"  Deleted migration: {f}"))

        # Also clean __pycache__ to avoid stale bytecode
        pycache = migrations_dir / "__pycache__"
        if pycache.is_dir():
            shutil.rmtree(pycache)
            log.write(msg(f"  Cleaned: {pycache}"))


def recreate_migrations(stdout=None):
    """Run makemigrations + migrate."""
    call_command("makemigrations", *LOCAL_APPS, stdout=stdout)
    call_command("migrate", stdout=stdout)


def seed_database(stdout=None):
    """Create seed data: 1 user, 2 restaurants, 4 categories, 3 products.

    Two sample orders (with three order items) are created for the seed user
    so the order endpoints have data to work with. The function is
    idempotent: running it again does not create duplicates.
    """
    log = stdout or open(os.devnull, "w")

    counts = {
        "users": 0,
        "restaurants": 0,
        "categories": 0,
        "products": 0,
        "orders": 0,
        "order_items": 0,
    }

    owner, created = User.objects.get_or_create(
        username=SEED_USER["username"],
        defaults={
            "fullname": SEED_USER["fullname"],
            "phone": SEED_USER["phone"],
            "email": SEED_USER["email"],
        },
    )
    if created:
        owner.set_password(SEED_USER["password"])
        owner.save()
        counts["users"] += 1
        log.write(f'  Created owner user "{owner.username}".')

    restaurants = {}
    for rest_data in RESTAURANTS:
        restaurant, was_created = Restaurant.objects.get_or_create(
            name=rest_data["name"],
            defaults={
                "owner": owner,
                "label": rest_data["label"],
                "phone": rest_data["phone"],
                "open_time": rest_data["open_time"],
                "location": rest_data["location"],
                "rank": rest_data["rank"],
            },
        )
        if was_created:
            counts["restaurants"] += 1
        restaurants[restaurant.name] = restaurant

    categories = {}
    for cat_data in CATEGORIES:
        restaurant = restaurants[cat_data["restaurant"]]
        category, cat_created = ProductCategory.objects.get_or_create(
            restaurant=restaurant,
            name=cat_data["name"],
            defaults={"label": cat_data["label"]},
        )
        if cat_created:
            counts["categories"] += 1
        categories[(restaurant.name, category.name)] = category

    products = {}
    for prod_data in PRODUCTS:
        category = categories[(prod_data["restaurant"], prod_data["category"])]
        product, prod_created = Product.objects.get_or_create(
            category=category,
            name=prod_data["name"],
            defaults={
                "label": prod_data["label"],
                "price": Decimal(prod_data["price"]),
            },
        )
        if prod_created:
            counts["products"] += 1
        products[product.name] = product

    for order_data in ORDERS:
        restaurant = restaurants[order_data["restaurant"]]
        order, order_created = Order.objects.get_or_create(
            user=owner,
            restaurant=restaurant,
            is_paid=order_data["is_paid"],
        )
        if order_created:
            counts["orders"] += 1

        for item_data in order_data["items"]:
            _, item_created = OrderItem.objects.get_or_create(
                order=order,
                product=products[item_data["product"]],
                defaults={"amount": item_data["amount"]},
            )
            if item_created:
                counts["order_items"] += 1

    return counts


def validate_seed_data():
    """Validate that seed data is correct. Returns (is_valid, errors_list)."""
    errors = []

    if not User.objects.filter(username=SEED_USER["username"]).exists():
        errors.append(f'Seed user "{SEED_USER["username"]}" not found')

    restaurant_count = Restaurant.objects.count()
    if restaurant_count != len(RESTAURANTS):
        errors.append(
            f"Expected {len(RESTAURANTS)} restaurants, found {restaurant_count}"
        )

    category_count = ProductCategory.objects.count()
    if category_count != len(CATEGORIES):
        errors.append(
            f"Expected {len(CATEGORIES)} categories, found {category_count}"
        )

    product_count = Product.objects.count()
    if product_count != len(PRODUCTS):
        errors.append(f"Expected {len(PRODUCTS)} products, found {product_count}")

    order_count = Order.objects.count()
    if order_count != len(ORDERS):
        errors.append(f"Expected {len(ORDERS)} orders, found {order_count}")

    expected_items = sum(len(order["items"]) for order in ORDERS)
    item_count = OrderItem.objects.count()
    if item_count != expected_items:
        errors.append(
            f"Expected {expected_items} order items, found {item_count}"
        )

    for rest_data in RESTAURANTS:
        try:
            restaurant = Restaurant.objects.get(name=rest_data["name"])
        except Restaurant.DoesNotExist:
            errors.append(f'Restaurant "{rest_data["name"]}" not found')
            continue

        if restaurant.open_time is None:
            errors.append(f'Restaurant "{restaurant.name}" has no open_time')
        if not restaurant.location:
            errors.append(f'Restaurant "{restaurant.name}" has no location')
        if restaurant.rank is None:
            errors.append(f'Restaurant "{restaurant.name}" has no rank')
        elif not 0 <= restaurant.rank <= 5:
            errors.append(
                f'Restaurant "{restaurant.name}" rank is out of range: '
                f"{restaurant.rank}"
            )

        expected_categories = {
            cat["name"] for cat in CATEGORIES
            if cat["restaurant"] == restaurant.name
        }
        actual_categories = set(
            restaurant.categories.values_list("name", flat=True)
        )
        if actual_categories != expected_categories:
            errors.append(
                f'Categories mismatch for "{restaurant.name}": '
                f"expected {sorted(expected_categories)}, "
                f"found {sorted(actual_categories)}"
            )

    for prod_data in PRODUCTS:
        try:
            restaurant = Restaurant.objects.get(name=prod_data["restaurant"])
            category = ProductCategory.objects.get(
                restaurant=restaurant, name=prod_data["category"]
            )
            product = Product.objects.get(
                category=category, name=prod_data["name"]
            )
        except (Restaurant.DoesNotExist, ProductCategory.DoesNotExist,
                Product.DoesNotExist):
            errors.append(
                f'Product "{prod_data["name"]}" not found in '
                f'"{prod_data["restaurant"]} / {prod_data["category"]}"'
            )
            continue

        if product.price != Decimal(prod_data["price"]):
            errors.append(
                f'Product "{product.name}" price is {product.price}, '
                f'expected {prod_data["price"]}'
            )

    for order_data in ORDERS:
        restaurant = Restaurant.objects.filter(
            name=order_data["restaurant"]
        ).first()
        if restaurant is None:
            continue

        order = Order.objects.filter(
            user__username=SEED_USER["username"],
            restaurant=restaurant,
            is_paid=order_data["is_paid"],
        ).first()
        if order is None:
            errors.append(
                f'Order for "{order_data["restaurant"]}" '
                f'(is_paid={order_data["is_paid"]}) not found'
            )
            continue

        for item_data in order_data["items"]:
            product = Product.objects.filter(
                name=item_data["product"]
            ).first()
            if product is None:
                continue
            item = order.order_items.filter(product=product).first()
            if item is None:
                errors.append(
                    f'Order item "{item_data["product"]}" not found in '
                    f'order for "{order_data["restaurant"]}"'
                )
            elif item.amount != item_data["amount"]:
                errors.append(
                    f'Order item "{item_data["product"]}" amount is '
                    f'{item.amount}, expected {item_data["amount"]}'
                )

    return (len(errors) == 0, errors)


class Command(BaseCommand):
    help = (
        "Reset the development database, recreate migrations, "
        "and seed sample data."
    )

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("=== Development Database Reset ==="))

        self.stdout.write("\n[1/4] Deleting database and migration files...")
        reset_database(stdout=self.stdout, style=self.style)

        self.stdout.write("\n[2/4] Running makemigrations and migrate...")
        recreate_migrations(stdout=self.stdout)

        self.stdout.write("\n[3/4] Seeding data...")
        counts = seed_database(stdout=self.stdout)

        self.stdout.write("\n[4/4] Validating...")
        is_valid, errors = validate_seed_data()

        if is_valid:
            self.stdout.write(self.style.SUCCESS(
                f"\nDone! "
                f'{counts["users"]} user(s), '
                f'{counts["restaurants"]} restaurant(s), '
                f'{counts["categories"]} category(ies), '
                f'{counts["products"]} product(s), '
                f'{counts["orders"]} order(s), '
                f'{counts["order_items"]} order item(s) created. '
                f"Validation passed."
            ))
        else:
            self.stdout.write(self.style.ERROR("\nValidation failed:"))
            for err in errors:
                self.stdout.write(self.style.ERROR(f"  - {err}"))

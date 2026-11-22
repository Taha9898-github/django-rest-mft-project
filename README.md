# Online Menu — Django REST API

A REST API for an online restaurant menu: users, restaurants, categories,
products and orders, built with Django and Django REST Framework.

## Stack

- Python 3.10 / Django 5.2
- Django REST Framework (token authentication)
- drf-spectacular (OpenAPI / Swagger UI)
- SQLite (development database)

## Setup

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
```

Reset the database, recreate migrations and load demo data in one command:

```bash
python manage.py seed_data
```

The command deletes `db.sqlite3` and the local app migrations, runs
`makemigrations` + `migrate`, seeds the data and validates the result.

Run the server:

```bash
python manage.py runserver
```

Swagger UI: http://127.0.0.1:8000/

## Demo data

| Entity | Count |
| --- | --- |
| Users | 1 |
| Restaurants | 2 |
| Categories | 4 |
| Products | 3 |
| Orders | 2 |
| Order items | 3 |

Seed credentials: `seedowner` / `seedpass123`

Running `seed_data` again is idempotent — it does not create duplicates.

## Models

- **User** — custom user with `fullname` and unique `phone`.
- **Restaurant** — `owner`, `name`, `label`, `phone`, `open_time` (time),
  `location` (address), `rank` (float, 0–5), `is_active`, timestamps.
- **ProductCategory** — belongs to a restaurant.
- **Product** — belongs to a category; decimal price and 1–5 rank.
- **Order** — belongs to a user and a restaurant, has a UUID and `is_paid`;
  exposes `total_amount` and `total_cost`.
- **OrderItem** — belongs to an order and a product; `amount` is a positive int.

## API endpoints

| Endpoint | Description |
| --- | --- |
| `POST /account/register/` | Register and receive a token |
| `POST /account/obtain-token/` | Log in and receive a token |
| `POST /account/logout/` | Invalidate the current token |
| `/api/v1/restaurants/` | Restaurant CRUD; detail includes categories and the first category's products |
| `/api/v1/categories/` | Category CRUD |
| `/api/v1/products/` | Product CRUD |
| `/api/v1/orders/` | Order CRUD; regular users see only their own orders, staff see all |
| `/api/v1/order-items/` | Order item CRUD; regular users see only items of their own orders |
| `/api/schema/` | OpenAPI schema |
| `/api/schema/swagger-ui/`, `/api/schema/redoc/` | API docs |

All endpoints except registration and login require
`Authorization: Token <key>`.

## Tests

```bash
python manage.py check
python manage.py test
```

The suite covers seed data/idempotency, the restaurant detail endpoint,
order/order-item serializers and API permissions, and account endpoints.

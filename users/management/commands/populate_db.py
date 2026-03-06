import random
import string
from faker import Faker
from django.core.management.base import BaseCommand
from django.contrib.auth.hashers import make_password
from django.utils.timezone import now
from django.db.utils import IntegrityError
from users.models import CustomUser, UserProfile
from products.models import Product, Category
from orders.models import Order, OrderItem
from checkout.models import ShippingAddress
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Generate test data for users, products, orders, and categories"

    def add_arguments(self, parser):
        parser.add_argument(
            '--users',
            type=int,
            default=100,
            help='Number of users to create'
        )
        parser.add_argument(
            '--products',
            type=int,
            default=50,
            help='Number of products to create'
        )
        parser.add_argument(
            '--orders',
            type=int,
            default=200,
            help='Number of orders to create'
        )

    def handle(self, *args, **options):
        fake = Faker()
        
        # Create users
        users = []
        for _ in range(options['users']):
            try:
                user = CustomUser(
                    username=fake.unique.user_name(),
                    email=fake.unique.email(),
                    password=make_password(fake.password()),
                    first_name=fake.first_name(),
                    last_name=fake.last_name(),
                    date_joined=fake.date_time_between(start_date="-5y", end_date="now"),
                    last_login=fake.date_time_between(start_date="-5y", end_date="now"),
                    is_active=True,
                    is_staff=False,
                    is_superuser=False
                )
                users.append(user)
            except IntegrityError:
                logger.warning("Duplicate username/email found, skipping...")
                continue

        # Bulk create users
        CustomUser.objects.bulk_create(users)
        self.stdout.write(self.style.SUCCESS(f"Created {len(users)} users"))

        # Create user profiles
        for user in CustomUser.objects.all():
            UserProfile.objects.create(
                user=user,
                phone_number=fake.phone_number(),
                birth_date=fake.date_of_birth(minimum_age=18, maximum_age=65),
                bio=fake.paragraph(nb_sentences=2)
            )
        self.stdout.write(self.style.SUCCESS("Created user profiles"))

        # Create categories
        categories = []
        for _ in range(10):
            category = Category.objects.create(
                name=fake.unique.word().title(),
                description=fake.paragraph(nb_sentences=2),
                is_active=True
            )
            categories.append(category)
        self.stdout.write(self.style.SUCCESS("Created categories"))

        # Create products
        products = []
        for _ in range(options['products']):
            categories_for_product = random.sample(categories, random.randint(1, 3))
            product = Product(
                name=fake.unique.word().title(),
                description=fake.paragraph(nb_sentences=3),
                price=random.uniform(100, 10000),
                stock=random.randint(0, 100),
                is_active=True,
                is_featured=random.choice([True, False])
            )
            product.save()
            product.categories.set(categories_for_product)
            products.append(product)
        self.stdout.write(self.style.SUCCESS(f"Created {len(products)} products"))

        # Create shipping addresses
        for user in CustomUser.objects.all():
            ShippingAddress.objects.create(
                user=user,
                full_name=f"{user.first_name} {user.last_name}",
                phone_number=fake.phone_number(),
                email=user.email,
                address_line1=fake.street_address(),
                address_line2=fake.secondary_address(),
                city=fake.city(),
                state=fake.state(),
                pincode=fake.postcode(),
                country=fake.country(),
                is_default=random.choice([True, False])
            )
        self.stdout.write(self.style.SUCCESS("Created shipping addresses"))

        # Create orders
        orders = []
        for _ in range(options['orders']):
            user = random.choice(CustomUser.objects.all())
            shipping_address = random.choice(user.shipping_addresses.all())
            order = Order(
                user=user,
                shipping_address=shipping_address,
                payment_method=random.choice(['cash_on_delivery', 'online_payment']),
                status=random.choice(['pending', 'processing', 'packed', 'out_for_delivery', 'delivered', 'cancelled']),
                payment_status=random.choice(['pending', 'completed', 'failed']),
                expected_delivery_date=fake.date_time_between(start_date="now", end_date="+7d")
            )
            order.save()
            
            # Add random items to order
            items_count = random.randint(1, 5)
            items = random.sample(products, items_count)
            for item in items:
                OrderItem.objects.create(
                    order=order,
                    product=item,
                    quantity=random.randint(1, 3),
                    price=item.price
                )
            
            orders.append(order)
        self.stdout.write(self.style.SUCCESS(f"Created {len(orders)} orders"))

        # Create order tracking
        for order in orders:
            status_choices = ['pending', 'processing', 'packed', 'out_for_delivery', 'delivered']
            current_status_index = status_choices.index(order.status)
            
            # Create tracking updates for each status
            for i in range(current_status_index + 1):
                OrderTracking.objects.create(
                    order=order,
                    status=status_choices[i],
                    notes=fake.sentence(),
                    location=fake.city() if i > 1 else None
                )
        self.stdout.write(self.style.SUCCESS("Created order tracking"))

        self.stdout.write(self.style.SUCCESS("Data population completed successfully!"))


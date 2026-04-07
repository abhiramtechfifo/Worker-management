import os
import django
import random

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'worker_management.settings')
django.setup()

from api.models import Worker, Owner

def seed():
    # Create Workers
    for i in range(1, 21):
        Worker.objects.create(
            name=f"Kooli Worker {i}",
            phone=f"98765432{i:02d}",
            role="KOOLI",
            status="AVAILABLE"
        )
    
    for i in range(1, 11):
        Worker.objects.create(
            name=f"Grass Cutter {i}",
            phone=f"98765412{i:02d}",
            role="GRASS_CUTTER",
            status="AVAILABLE"
        )

    # Create some Owners for testing
    owners_data = [
        {"name": "Anil Kumar", "phone": "1234567890", "address": "Muvattupuzha, Kerala"},
        {"name": "Biju Joseph", "phone": "2345678901", "address": "Thodupuzha, Kerala"},
        {"name": "Saji Varghese", "phone": "3456789012", "address": "Kothamangalam, Kerala"},
    ]
    for owner_info in owners_data:
        Owner.objects.create(**owner_info)

    print("Seeding complete: 30 workers and 3 owners created.")

if __name__ == "__main__":
    seed()

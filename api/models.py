from django.db import models
from django.utils import timezone

class Worker(models.Model):
    ROLE_CHOICES = [
        ('KOOLI', 'Kooli'),
        ('GRASS_CUTTER', 'Grass Cutter'),
    ]
    STATUS_CHOICES = [
        ('AVAILABLE', 'Available'),
        ('ASSIGNED', 'Assigned'),
        ('UNAVAILABLE', 'Unavailable'),
    ]
    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=20)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='AVAILABLE')
    # is_active = False means worker is on leave; won't appear as "available" for assignment
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class Owner(models.Model):
    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=20)
    address = models.TextField()

    def __str__(self):
        return self.name

class Assignment(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Half Payment', 'Half Payment'),
        ('Full Payment', 'Full Payment'),
    ]
    worker = models.ForeignKey(Worker, on_delete=models.CASCADE, related_name='assignments')
    owner = models.ForeignKey(Owner, on_delete=models.CASCADE, related_name='assignments')
    work_type = models.CharField(max_length=20)
    hours_worked = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    date = models.DateField(default=timezone.now)
    # is_active = False means work was cancelled / marked inactive for the night
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.worker.name} for {self.owner.name} on {self.date}"

class Payment(models.Model):
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name='payments')
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2)
    payment_status = models.CharField(max_length=20)
    date = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"Payment of {self.amount_paid} for {self.assignment}"

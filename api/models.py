from django.db import models

# Create your models here.

class User(models.Model):
    USER_TYPE_CHOICES = [
        ('buyer', 'Buyer'),
        ('seller', 'Seller'),
    ]
    username = models.CharField(max_length=100, unique=True)
    user_type = models.CharField(max_length=10, choices=USER_TYPE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.username} ({self.user_type})"

class BuyerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, limit_choices_to={'user_type': 'buyer'})
    terms_accepted = models.BooleanField(default=False)
    payment_status = models.BooleanField(default=True)

class SellerProfile(models.Model):
    DAY_CHOICES = [
        ('monday', 'Monday'),
        ('tuesday', 'Tuesday'),
        ('wednesday', 'Wednesday'),
        ('thursday', 'Thursday'),
        ('friday', 'Friday'),
        ('saturday', 'Saturday'),
        ('sunday', 'Sunday'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE, limit_choices_to={'user_type': 'seller'})
    terms_accepted = models.BooleanField(default=False)
    payment_status = models.BooleanField(default=True)
    address = models.CharField(max_length=255, blank=True)
    selected_day = models.CharField(max_length=10, choices=DAY_CHOICES, blank=True, null=True)
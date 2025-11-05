from django.db import models
from django.contrib.auth.models import User


class Course(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    price_in_paise = models.PositiveIntegerField(help_text="Price in paise (e.g., 49900 = ₹499.00)")
    is_active = models.BooleanField(default=True)

    def __str__(self) -> str:
        return f"{self.title} (₹{self.price_in_paise / 100:.2f})"


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    purchased_courses = models.ManyToManyField(Course, blank=True, related_name="purchasers")

    def __str__(self) -> str:
        return f"Profile({self.user.username})"


class Transaction(models.Model):
    STATUS_CHOICES = [
        ("created", "Created"),
        ("paid", "Paid"),
        ("failed", "Failed"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="transactions")
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="transactions")
    amount_in_paise = models.PositiveIntegerField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="created")
    razorpay_order_id = models.CharField(max_length=100, blank=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True)
    razorpay_signature = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"Txn {self.id} - {self.user.username} - {self.course.title} - {self.status}"


# Create your models here.

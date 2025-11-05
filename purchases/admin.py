from django.contrib import admin
from .models import Course, Transaction, Profile


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("title", "price_in_paise", "is_active")
    list_filter = ("is_active",)
    search_fields = ("title",)


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "course",
        "amount_in_paise",
        "status",
        "razorpay_order_id",
        "razorpay_payment_id",
        "created_at",
    )
    list_filter = ("status", "created_at")
    search_fields = ("razorpay_order_id", "razorpay_payment_id", "user__username")


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user",)
    filter_horizontal = ("purchased_courses",)


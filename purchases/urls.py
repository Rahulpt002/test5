from django.urls import path
from . import views

urlpatterns = [
    path('', views.course_list, name='course_list'),
    path('buy/<int:course_id>/', views.create_order, name='buy_course'),
    path('payment/callback/', views.payment_callback, name='payment_callback'),
    path('profile/', views.profile_view, name='profile'),
    path('cart/add/<int:course_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/', views.cart_view, name='cart_view'),
    path('cart/checkout/', views.cart_checkout, name='cart_checkout'),
    path('cart/remove/<int:course_id>/', views.remove_from_cart, name='remove_from_cart'),
]



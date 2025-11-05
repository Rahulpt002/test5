from django.urls import path
from . import views

urlpatterns = [
    path('', views.course_list, name='course_list'),
    path('buy/<int:course_id>/', views.create_order, name='buy_course'),
    path('payment/callback/', views.payment_callback, name='payment_callback'),
    path('profile/', views.profile_view, name='profile'),
]



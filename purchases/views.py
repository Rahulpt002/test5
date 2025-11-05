from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponseBadRequest
import razorpay

from .models import Course, Transaction


def _razorpay_client() -> razorpay.Client:
    return razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))


def course_list(request):
    courses = Course.objects.filter(is_active=True).order_by('id')
    items = []
    for c in courses:
        rupees = c.price_in_paise / 100.0
        items.append({
            'id': c.id,
            'title': c.title,
            'description': c.description,
            'price_display': f"₹{rupees:.2f}",
        })
    return render(request, 'purchases/course_list.html', {'courses': items, 'razorpay_key_id': settings.RAZORPAY_KEY_ID})


@login_required
def create_order(request, course_id: int):
    course = get_object_or_404(Course, pk=course_id, is_active=True)
    client = _razorpay_client()

    transaction = Transaction.objects.create(
        user=request.user,
        course=course,
        amount_in_paise=course.price_in_paise,
        status='created',
    )

    order = client.order.create({
        'amount': course.price_in_paise,
        'currency': 'INR',
        'payment_capture': 1,
        'notes': {'transaction_id': str(transaction.id)},
    })
    transaction.razorpay_order_id = order['id']
    transaction.save(update_fields=["razorpay_order_id"])

    
    return render(
        request,
        'purchases/checkout.html',
        {
            'transaction': transaction,
            'course': course,
            'razorpay_key_id': settings.RAZORPAY_KEY_ID,
            'order_id': order['id'],
            'amount': course.price_in_paise,
            'amount_display': f"{course.price_in_paise / 100:.2f}",
            'currency': 'INR',
        },
    )


@csrf_exempt  
def payment_callback(request):
    if request.method != 'POST':
        return HttpResponseBadRequest('Invalid method')

    payload = request.POST
    razorpay_payment_id = payload.get('razorpay_payment_id')
    razorpay_order_id = payload.get('razorpay_order_id')
    razorpay_signature = payload.get('razorpay_signature')

    if not (razorpay_payment_id and razorpay_order_id and razorpay_signature):
        return HttpResponseBadRequest('Missing parameters')

    try:
        client = _razorpay_client()
       
        client.utility.verify_payment_signature({
            'razorpay_order_id': razorpay_order_id,
            'razorpay_payment_id': razorpay_payment_id,
            'razorpay_signature': razorpay_signature,
        })
    except Exception:
       
        Transaction.objects.filter(razorpay_order_id=razorpay_order_id).update(
            status='failed',
            razorpay_payment_id=razorpay_payment_id or '',
            razorpay_signature=razorpay_signature or '',
        )
        return render(request, 'purchases/payment_result.html', {'success': False})

    
    txn = Transaction.objects.select_related('user', 'course').get(razorpay_order_id=razorpay_order_id)
    txn.status = 'paid'
    txn.razorpay_payment_id = razorpay_payment_id
    txn.razorpay_signature = razorpay_signature
    txn.save()

    profile = txn.user.profile  
    profile.purchased_courses.add(txn.course)

    return render(request, 'purchases/payment_result.html', {'success': True, 'course': txn.course})


@login_required
def profile_view(request):
    profile = request.user.profile
    return render(request, 'purchases/profile.html', {'profile': profile})




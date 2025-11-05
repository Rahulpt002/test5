from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponseBadRequest
from django.http import JsonResponse
import razorpay

from .models import Course, Transaction


def _razorpay_client() -> razorpay.Client:
    return razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))


def course_list(request):
    courses = Course.objects.filter(is_active=True).order_by('id')
    items = []
    purchased_ids = set()
    cart_ids = request.session.get('cart') if isinstance(request.session.get('cart'), list) else []
    cart_set = set(cart_ids)
    if request.user.is_authenticated and hasattr(request.user, 'profile'):
        purchased_ids = set(request.user.profile.purchased_courses.values_list('id', flat=True))
    for c in courses:
        rupees = c.price_in_paise / 100.0
        items.append({
            'id': c.id,
            'title': c.title,
            'description': c.description,
            'price_display': f"₹{rupees:.2f}",
            'purchased': c.id in purchased_ids,
            'in_cart': c.id in cart_set,
        })
    return render(request, 'purchases/course_list.html', {
        'courses': items,
        'razorpay_key_id': settings.RAZORPAY_KEY_ID,
        'cart_count': len(cart_set),
    })


@login_required
def create_order(request, course_id: int):
    course = get_object_or_404(Course, pk=course_id, is_active=True)
    # Prevent repurchase if already owned
    if hasattr(request.user, 'profile') and request.user.profile.purchased_courses.filter(id=course.id).exists():
        return render(request, 'purchases/payment_result.html', {'success': True, 'course': course, 'already': True})
    client = _razorpay_client()

    transaction = Transaction.objects.create(
        user=request.user,
        course=course,
        amount_in_paise=course.price_in_paise,
        status='created',
    )

    try:
        order = client.order.create({
            'amount': course.price_in_paise,
            'currency': 'INR',
            'payment_capture': 1,
            'notes': {'transaction_id': str(transaction.id)},
        })
    except Exception:
        # Mark transaction as failed and show failure page without crashing
        transaction.status = 'failed'
        transaction.save(update_fields=['status'])
        return render(request, 'purchases/payment_result.html', {'success': False})
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

    # Handle single or multi-item orders: update all transactions with this order id
    txns = list(Transaction.objects.select_related('user', 'course').filter(razorpay_order_id=razorpay_order_id))
    for t in txns:
        t.status = 'paid'
        t.razorpay_payment_id = razorpay_payment_id
        t.razorpay_signature = razorpay_signature
        t.save()
        profile = t.user.profile
        profile.purchased_courses.add(t.course)

    # Clear session cart if present
    if 'cart' in request.session:
        request.session.pop('cart', None)

    course = txns[0].course if len(txns) == 1 else None
    return render(request, 'purchases/payment_result.html', {'success': True, 'course': course})


@login_required
def profile_view(request):
    profile = request.user.profile
    return render(request, 'purchases/profile.html', {'profile': profile})


def _get_cart(request):
    cart = request.session.get('cart')
    if not isinstance(cart, list):
        cart = []
    return cart


def _save_cart(request, cart_ids):
    request.session['cart'] = cart_ids
    request.session.modified = True


@login_required
def add_to_cart(request, course_id: int):
    course = get_object_or_404(Course, pk=course_id, is_active=True)
    if hasattr(request.user, 'profile') and request.user.profile.purchased_courses.filter(id=course.id).exists():
        if request.headers.get('x-requested-with') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Accept', ''):
            return JsonResponse({'ok': False, 'reason': 'already_owned'})
        return redirect('cart_view')
    cart = _get_cart(request)
    if course_id not in cart:
        cart.append(course_id)
        _save_cart(request, cart)
    if request.headers.get('x-requested-with') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Accept', ''):
        return JsonResponse({'ok': True, 'course_id': course_id, 'cart_count': len(cart)})
    return redirect('cart_view')


@login_required
def cart_view(request):
    cart_ids = _get_cart(request)
    owned_ids = set()
    if hasattr(request.user, 'profile'):
        owned_ids = set(request.user.profile.purchased_courses.values_list('id', flat=True))
    courses = list(Course.objects.filter(id__in=cart_ids, is_active=True))
    items = []
    total_paise = 0
    for c in courses:
        if c.id in owned_ids:
            continue
        total_paise += c.price_in_paise
        items.append({
            'id': c.id,
            'title': c.title,
            'description': c.description,
            'price_display': f"₹{c.price_in_paise / 100:.2f}",
        })
    return render(request, 'purchases/cart.html', {
        'items': items,
        'total_paise': total_paise,
        'total_display': f"₹{total_paise / 100:.2f}",
    })


@login_required
def cart_checkout(request):
    cart_ids = _get_cart(request)
    if not cart_ids:
        return redirect('cart_view')
    owned_ids = set()
    if hasattr(request.user, 'profile'):
        owned_ids = set(request.user.profile.purchased_courses.values_list('id', flat=True))
    courses = list(Course.objects.filter(id__in=cart_ids, is_active=True).exclude(id__in=owned_ids))
    if not courses:
        return redirect('cart_view')

    total_paise = sum(c.price_in_paise for c in courses)

    client = _razorpay_client()

    transactions = []
    for c in courses:
        t = Transaction.objects.create(
            user=request.user,
            course=c,
            amount_in_paise=c.price_in_paise,
            status='created',
        )
        transactions.append(t)

    try:
        order = client.order.create({
            'amount': total_paise,
            'currency': 'INR',
            'payment_capture': 1,
            'notes': {'cart_count': str(len(courses))},
        })
    except Exception:
        for t in transactions:
            t.status = 'failed'
            t.save(update_fields=['status'])
        return render(request, 'purchases/payment_result.html', {'success': False})

    for t in transactions:
        t.razorpay_order_id = order['id']
        t.save(update_fields=['razorpay_order_id'])

    return render(
        request,
        'purchases/checkout.html',
        {
            'transaction': None,
            'course': {'title': 'Cart Purchase'},
            'razorpay_key_id': settings.RAZORPAY_KEY_ID,
            'order_id': order['id'],
            'amount': total_paise,
            'amount_display': f"{total_paise / 100:.2f}",
            'currency': 'INR',
        },
    )


@login_required
def remove_from_cart(request, course_id: int):
    cart = _get_cart(request)
    if course_id in cart:
        cart.remove(course_id)
        _save_cart(request, cart)
    # Support AJAX removal
    if request.headers.get('x-requested-with') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Accept', ''):
        return JsonResponse({'ok': True, 'course_id': course_id, 'cart_count': len(cart)})
    return redirect('cart_view')



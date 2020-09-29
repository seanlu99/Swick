import json
from django.utils import timezone
from django.http import JsonResponse
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from .models import User, Restaurant, Customer, Server, ServerRequest, Meal, \
    Customization, Order, OrderItem, OrderItemCustomization
from .serializers import RestaurantSerializer, CategorySerializer, MealSerializer, \
    CustomizationSerializer, OrderSerializerForCustomer, OrderDetailsSerializerForCustomer, \
    OrderSerializerForServer, OrderDetailsSerializerForServer
from rest_framework.decorators import api_view
import stripe
from swick.settings import STRIPE_API_KEY

stripe.api_key = STRIPE_API_KEY

##### CUSTOMER AND SERVER SHARED API URLS #####

# GET request
# Update account information
@api_view(['POST'])
def update_info(request):
    """
    header:
        Authorization: Token ...
    params:
        name
        email
    return:
        status
    """
    # Update name
    request.user.name = request.POST["name"]
    request.user.save()
    # Update email if given
    email = request.POST["email"]
    if email != "":
        email = request.POST["email"]
        # Check if email is already taken
        try:
            user = User.objects.get(email=email)
            if user != request.user:
                return JsonResponse({"status": "email_already_taken"})
        # If email is not taken
        except User.DoesNotExist:
            request.user.email = email
            request.user.save()
    return JsonResponse({"status": "success"})

##### CUSTOMER APIS #####

# POST request
# Create customer account if not created
@api_view(['POST'])
def customer_create_account(request):
    """
    header:
        Authorization: Token ...
    return:
        status
    """
    customers = Customer.objects.filter(user=request.user)
    if not customers:
        try:
            stripe_id = stripe.Customer.create().id
        except stripe.error.StripeError:
            return JsonResponse({"status" : "stripe_api_error"})
        Customer.objects.create(user=request.user, stripe_cust_id=stripe_id)

    return JsonResponse({"status": "success"})

# GET request
# Get list of restaurants
def customer_get_restaurants(request):
    """
    return:
        [restaurants]
            id
            name
            address
            image
        status
    """
    restaurants = RestaurantSerializer(
        Restaurant.objects.all().order_by("name"),
        many=True,
        # Needed to get absolute image url
        context={"request": request}
    ).data

    return JsonResponse({"restaurants": restaurants, "status": "success"})

# GET request
# Get restaurant associated with restaurant_id
def customer_get_restaurant(request, restaurant_id):
    """
    return:
        restaurant
            id
            name
            address
            image
        status
    """
    try:
        restaurant_object = Restaurant.objects.get(id=restaurant_id)
    except Restaurant.DoesNotExist:
        return JsonResponse({"status": "restaurant_does_not_exist"})
    restaurant = RestaurantSerializer(
        restaurant_object,
        context={"request": request}
    ).data
    return JsonResponse({"restaurant": restaurant, "status": "success"})

# GET request
# Get categories associated with restaurant_id
def customer_get_categories(request, restaurant_id):
    """
    return:
        [categories]
    """
    categories = CategorySerializer(
        Meal.objects.filter(restaurant_id=restaurant_id).order_by("category")
            .distinct("category"),
        many=True,
    ).data
    return JsonResponse({"categories": categories, "status": "success"})

# GET request
# Get menu associated with category
def customer_get_menu(request, restaurant_id, category):
    """
    return:
        [menu]
            id
            name
            description
            price
            image
        status
    """
    if category == "All":
        meals = MealSerializer(
            Meal.objects.filter(restaurant_id=restaurant_id).order_by("name"),
            many=True,
            context={"request": request}
        ).data
    else:
        meals = MealSerializer(
            Meal.objects.filter(restaurant_id=restaurant_id, category=category).order_by("name"),
            many=True,
            context={"request": request}
        ).data
    return JsonResponse({"menu": meals, "status": "success"})

# GET request
# Get meal associated with meal_id
def customer_get_meal(request, meal_id):
    """
    return:
        [customizations]
            id
            name
            options
            price_additions
            min
            max
        status
    """
    customizations = CustomizationSerializer(
        Customization.objects.filter(meal_id=meal_id).order_by("name"),
        many=True,
        context={"request": request}
    ).data
    return JsonResponse({"customizations": customizations, "status": "success"})

# POST request
# Create order in database
@api_view(['POST'])
def customer_place_order(request):
    """
    header:
        Authorization: Token ...
    params:
        restaurant_id
        table
        [order_items]
            meal_id
            quantity
            [customizations]
                customization_id
                [options]
        payment_method_id
    return:
        intent_status
        card_error (optional)
        payment_intent_id (optional)
        client_secret (optional)
        status
    """

    # Create order in database
    order = Order.objects.create(
        customer=request.user.customer,
        restaurant_id=request.POST["restaurant_id"],
        table=request.POST["table"],
        status=Order.COOKING
    )

    # Variable for calculating order total
    order_total = 0

    order_items = json.loads(request.POST["order_items"])
    # Loop through order items
    for item in order_items:
        # Create order item in database
        order_item = OrderItem.objects.create(
            order=order,
            meal_name=Meal.objects.get(id=item["meal_id"]).name,
            meal_price=Meal.objects.get(id=item["meal_id"]).price,
            quantity=item["quantity"]
        )
        # Variable for calculating price of one meal in order item
        meal_total = order_item.meal_price
        # Loop through customizations of order items
        for cust in item["customizations"]:
            cust_id = cust["customization_id"]
            cust_object = Customization.objects.get(id=cust_id)
            # Build options and price_additions arrays with option indices
            options = []
            price_additions = []
            for opt_idx in cust["options"]:
                options.append(cust_object.options[opt_idx])
                price_additions.append(cust_object.price_additions[opt_idx])
                meal_total += cust_object.price_additions[opt_idx]

            # Create order item customization in database
            order_item_customization = OrderItemCustomization.objects.create(
                order_item=order_item,
                customization_name=Customization.objects.get(id=cust_id).name,
                options=options,
                price_additions=price_additions
            )
        # Calculate order item total and update field
        order_item.total = meal_total * order_item.quantity
        order_item.save()

        order_total += order_item.total
    # Update order total field
    order.total = order_total

    # STRIPE PAYMENT PROCESSING
    # Note: Return value 'intent_status: String' can be refactored to boolean values
    # at the cost of readability
    try:
        # Direct payments to stripe connected account if in production
        if request.is_secure():
            stripe_acct_id = Restaurant.objects.get(id=request.POST["restaurant_id"]).stripe_acct_id
            payment_intent = stripe.PaymentIntent.create(amount = int(order.total * 100),
                                                    currency="usd",
                                                    customer=request.user.customer.stripe_cust_id,
                                                    payment_method=request.POST["payment_method_id"],
                                                    receipt_email=request.user.email,
                                                    use_stripe_sdk=True,
                                                    confirmation_method='manual',
                                                    confirm=True,
                                                    transfer_data={
                                                        'destination' : stripe_acct_id
                                                    },
                                                    metadata={'order_id': order.id})
        # Direct payments to developer Stripe account if in development
        else:
            payment_intent = stripe.PaymentIntent.create(amount = int(order.total * 100),
                                                     currency="usd",
                                                     customer=request.user.customer.stripe_cust_id,
                                                     payment_method=request.POST["payment_method_id"],
                                                     receipt_email=request.user.email,
                                                     use_stripe_sdk=True,
                                                     confirmation_method='manual',
                                                     confirm=True,
                                                     metadata={'order_id': order.id})
    except stripe.error.CardError as e:
        error = e.user_message
        order.delete()
        return JsonResponse({"intent_status" : "card_error", "error" : error, "status" : "success"})
    except stripe.error.StripeError as e:
        print(e)
        return JsonResponse({"status" : "stripe_api_error"})

    intent_status = payment_intent.status
    # Card requires further action
    if intent_status == 'requires_action' or intent_status == 'requires_source_action':
        # Card requires more action
        order.stripe_payment_id = payment_intent.id
        order.save()
        return JsonResponse({"intent_status" : intent_status,
                             "payment_intent" : payment_intent.id,
                             "client_secret": payment_intent.client_secret,
                             "status" : "success"})

    # Card is invalid (this 'elif' branch should never occur due to previous card setup validation)
    elif intent_status == 'requires_payment_method':
        error = payment_intent.last_payment_error.message if payment_intent.get('last_payment_error') else None
        order.delete()
        return JsonResponse({"intent_status" : intent_status, "error" : error, "status" : "success"})

    # Payment is succesful
    elif intent_status == 'succeeded':
        order.stripe_payment_id = payment_intent.id
        order.payment_completed = True
        order.save()
        return JsonResponse({"intent_status" : intent_status, "status" : "success"})

    # should never reach this return
    return JsonResponse({"status": "unhandled_status"})

# POST requires_action
# Retry payment after client completes nextAction request on payment SetupIntent
@api_view(['POST'])
def customer_retry_payment(request):
    """
    header:
        Authorization: Token ...
        params:
            payment_intent_id
        return:
            intent_status
            error
            status
    """
    try:
        payment_intent = stripe.PaymentIntent.retrieve(
            request.POST["payment_intent_id"]
        )
        payment_intent = stripe.PaymentIntent.confirm(payment_intent.id)
    except stripe.error.CardError as e:
        order = Order.objects.get(id = payment_intent.metadata["order_id"])
        order.delete()
        return JsonResponse({"intent_status" : "card_error", "error" : e.user_message, "status" : "success"})
    except stripe.error.StripeError:
        return JsonResponse({"status" : "stripe_api_error"})

    intent_status = payment_intent.status

    # Card is invalid (this 'elif' branch should never occur due to previous card setup validation)
    if intent_status == 'requires_payment_method' or intent_status == 'requires_source':
        error = payment_intent.last_payment_error.message if payment_intent.get('last_payment_error') else None
        order.delete()
        return JsonResponse({"intent_status" : intent_status, "error" : error, "status" : "success"})
    # Payment is succesful
    elif intent_status == 'succeeded':
        order = Order.objects.get(id = payment_intent.metadata["order_id"])
        order.payment_completed = True
        order.save()
        return JsonResponse({"intent_status" : "succeeded", "status" : "success"})

    # should never reach this return
    return JsonResponse({"status": "unhandled_status"})

# GET request
# Get list of customer's orders
@api_view()
def customer_get_orders(request):
    """
    header:
        Authorization: Token ...
    return:
        [orders]
            id
            restaurant
                name
            status
            order_time
        status
    """
    orders = OrderSerializerForCustomer(
        Order.objects
            .filter(customer=request.user.customer, total__isnull=False, payment_completed=True)
            .order_by("-id"),
        many=True
    ).data

    return JsonResponse({"orders": orders, "status": "success"})

# GET request
# Get customer's order details
@api_view()
def customer_get_order_details(request, order_id):
    """
    header:
        Authorization: Token ...
    return:
        order_details
            status
            table
            server
                name
            total
            [order_item]
                meal
                    name
                quantity
                total
        status
    """
    order = Order.objects.get(id=order_id)
    # Check if order's customer is the customer making the request
    if order.customer == request.user.customer:
        order_details=OrderDetailsSerializerForCustomer(
            order
        ).data
        return JsonResponse({"order_details": order_details, "status": "success"})
    else:
        return JsonResponse({"status": "invalid_order_id"})

# GET request
# Get customer's information
@api_view()
def customer_get_info(request):
    """
    header:
        Authorization: Token ...
    return:
        name
        email
        status
    """
    name = request.user.name
    email = request.user.email
    return JsonResponse({"name": name, "email": email, "status": "success"})

@api_view()
def customer_setup_card(request):
    """
    header:
        Authorization: Token ...
    return:
        client_secret
        status
    """
    stripe_cust_id = request.user.customer.stripe_cust_id

    try:
        setup_intent = stripe.SetupIntent.create(customer=stripe_cust_id)
    except stripe.error.StripeError as e:
        return JsonResponse({"status" : "stripe_api_error"})

    return JsonResponse({"client_secret": setup_intent.client_secret, "status": "success"})

@api_view(['POST'])
def customer_remove_card(request):
    """
    header:
        Authorization: Token ...
    params:
        payment_method_id
    """
    try:
        stripe.PaymentMethod.detach(request.POST["payment_method_id"])
    except stripe.error.StripeError as e:
        return JsonResponse({"status" : "stripe_api_error"})

    return JsonResponse({"status": "success"})

@api_view()
def customer_get_cards(request):
    """
    header:
        Authorization: Token ...
    return:
        [cards]
            payment_method_id
            brand
            exp_month
            exp_year
            last4
        status
    """
    stripe_cust_id = request.user.customer.stripe_cust_id
    try:
        payment_methods = stripe.PaymentMethod.list(
                            customer=stripe_cust_id,
                            type="card").data
    except stripe.error.StripeError:
        return JsonResponse({"status" : "stripe_api_error"})

    cards = []
    for payment_method in payment_methods:
        card = {
            "payment_method_id": payment_method.id,
            "brand": payment_method.card.brand,
            "exp_month": payment_method.card.exp_month,
            "exp_year": payment_method.card.exp_year,
            "last4": payment_method.card.last4
        }
        cards.append(card)

    return JsonResponse({"cards": cards, "status": "success"})


##### SERVER APIS #####

# POST request
# Create server account if not created
@api_view(['POST'])
def server_create_account(request):
    """
    header:
        Authorization: Token ...
    return:
        status
    """
    try:
        Server.objects.get(user=request.user)
    # Create server object if it does not exist
    except Server.DoesNotExist:
        server = Server.objects.create(user=request.user)
        # Set server's restaurant if server has already accepted request
        # from restaurant
        try:
            server_request = ServerRequest.objects.get(
                email=request.user.email,
                accepted=True
            )
            server.restaurant = server_request.restaurant
            server.save()
            server_request.delete()
        except ServerRequest.DoesNotExist:
            pass

    return JsonResponse({"status": "success"})

# GET request
# Get list of restaurant's orders
@api_view()
def server_get_orders(request, status):
    """
    header:
        Authorization: Token ...
    return:
        [orders]
            id
            customer
                name
            table
            order_time
        status
    """
    restaurant = request.user.server.restaurant
    if restaurant is None:
        return JsonResponse({
            "status": "restaurant_not_set"
        })
    # Reverse order if retrieving completed orders
    if status == Order.COMPLETE:
        orders = OrderSerializerForServer(
            Order.objects.filter(restaurant=restaurant, status=status, total__isnull=False, payment_completed=True)
                .order_by("-id"),
            many=True
        ).data
    else:
        orders = OrderSerializerForServer(
            Order.objects.filter(restaurant=restaurant, status=status, total__isnull=False, payment_completed=True)
                .order_by("id"),
            many=True
        ).data
    return JsonResponse({"orders": orders, "status": "success"})

# GET request
# Get restaurant's order details
@api_view()
def server_get_order_details(request, order_id):
    """
    header:
        Authorization: Token ...
    return:
        order_details
            chef
                name
            server
                name
            total
            [order_item]
                meal
                    name
                quantity
                total
        status
    """
    restaurant = request.user.server.restaurant
    order = Order.objects.get(id=order_id)
    # Check if a restaurant's server is making the request
    if order.restaurant == restaurant:
        order_details = OrderDetailsSerializerForServer(
            order
        ).data
        return JsonResponse({"order_details": order_details, "status": "success"})

# Update order status
@api_view(['POST'])
def server_update_order_status(request):
    """
    header:
        Authorization: Token ...
    params:
        order_id
        status
    return:
        status
    """
    order = Order.objects.get(id=request.POST.get("order_id"))
    # Check if a restaurant's server is making the request
    if order.restaurant == request.user.server.restaurant:
        status = request.POST.get("status")
        order.status = status
        if status == "2":
            order.chef = request.user.server
        elif status == "3":
            order.server = request.user.server
        order.save()
        return JsonResponse({"status": "success"})

# GET request
# Get server's information
@api_view()
def server_get_info(request):
    """
    header:
        Authorization: Token ...
    return:
        name
        email
        restaurant_name
        status
    """
    name = request.user.name
    email = request.user.email
    restaurant = request.user.server.restaurant
    restaurant_name = "none"
    if restaurant is not None:
        restaurant_name = restaurant.name
    return JsonResponse({
        "name": name,
        "email": email,
        "restaurant_name": restaurant_name,
        "status": "success"
    })

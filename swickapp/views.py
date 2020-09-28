from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.forms import formset_factory, modelformset_factory
from django.http import Http404
from django.utils import timezone
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.urls import reverse
from .forms import UserForm, UserUpdateForm, RestaurantForm, ServerRequestForm, \
    MealForm, CustomizationForm
from .models import User, Server, ServerRequest, Meal, Customization, Order
import pytz

# Home page: redirect to restaurant home page
def home(request):
    return redirect(restaurant_home)

# Restaurant sign up page
def restaurant_sign_up(request):
    # Prefix required because both forms share a field with the same name
    user_form = UserForm(prefix="user")
    restaurant_form = RestaurantForm(prefix="restaurant")

    if request.method == "POST":
        # Get data from user and restaurant forms
        user_form = UserForm(request.POST, prefix="user")
        restaurant_form = RestaurantForm(request.POST, request.FILES, prefix="restaurant")

        # Create user and restaurant objects in database
        if user_form.is_valid() and restaurant_form.is_valid():
            email = user_form.cleaned_data["email"]
            # If a user already exists from mobile app login
            # Grab user and set name and password
            try:
                user = User.objects.get(email=email)
                user.name = user_form.cleaned_data["name"]
                user.set_password(user_form.cleaned_data["password"])
                user.save()
            # Otherwise create user
            except User.DoesNotExist:
                user = User.objects.create_user(**user_form.cleaned_data)
            # Create restaurant
            new_restaurant = restaurant_form.save(commit=False)
            new_restaurant.user = user
            new_restaurant.save()

            # Login with user form data
            login(request, user)

            return redirect(restaurant_home)

    # Display user form and restaurant form
    return render(request, 'registration/sign_up.html', {
        "user_form": user_form,
        "restaurant_form": restaurant_form,
    })

# Restaurant home page
@login_required(login_url='/accounts/login/')
def restaurant_home(request):
    return redirect(restaurant_menu)

# Restaurant menu page
@login_required(login_url='/accounts/login/')
def restaurant_menu(request):
    meals = Meal.objects.filter(restaurant=request.user.restaurant).order_by("name")
    return render(request, 'restaurant/menu.html', {"meals": meals})

# Restaurant add meal page
@login_required(login_url='/accounts/login/')
def restaurant_add_meal(request):
    meal_form = MealForm()
    CustomizationFormset = formset_factory(CustomizationForm, extra=0)
    customization_formset = CustomizationFormset()

    # Add new meal and customizations
    if request.method == "POST":
        meal_form = MealForm(request.POST, request.FILES)
        customization_formset = CustomizationFormset(request.POST)

        if meal_form.is_valid() and customization_formset.is_valid():
            new_meal = meal_form.save(commit=False)
            new_meal.restaurant = request.user.restaurant
            new_meal.save()
            # Loop through each form in customization formset
            for form in customization_formset:
                new_customization = form.save(commit=False)
                new_customization.meal = new_meal
                new_customization.save()
            return redirect(restaurant_menu)

    return render(request, 'restaurant/add_meal.html', {
        "meal_form": meal_form,
        "customization_formset": customization_formset
    })

# Restaurant edit meal page
@login_required(login_url='/accounts/login/')
def restaurant_edit_meal(request, meal_id):
    meal = get_object_or_404(Meal, id=meal_id)
    # Checks if requested meal belongs to user's restaurant
    if request.user.restaurant != meal.restaurant:
        raise Http404()

    meal_form = MealForm(instance=meal)
    CustomizationFormset = modelformset_factory(Customization, form=CustomizationForm, extra=0)
    customization_objects = Customization.objects.filter(meal__id=meal_id)
    customization_formset = CustomizationFormset(queryset=customization_objects)

    # Update meal
    if request.method == "POST" and "update" in request.POST:
        meal_form = MealForm(request.POST, request.FILES,
            instance=meal)
        customization_formset = CustomizationFormset(request.POST)

        if meal_form.is_valid() and customization_formset.is_valid():
            meal_form.save()
            # Delete previous customizations
            Customization.objects.filter(meal__id=meal_id).delete()
            # Add updated customizations
            for form in customization_formset:
                new_customization = form.save(commit=False)
                new_customization.meal_id = meal_id
                new_customization.save()
            return redirect(restaurant_menu)

    # Delete meal
    if request.method == "POST" and "delete" in request.POST:
        Meal.objects.filter(id=meal_id).delete()
        return redirect(restaurant_menu)

    return render(request, 'restaurant/edit_meal.html', {
        "meal_form": meal_form,
        "customization_formset": customization_formset
    })

# Restaurant orders page
@login_required(login_url='/accounts/login/')
def restaurant_orders(request):
    orders = Order.objects.filter(restaurant=request.user.restaurant).order_by("-id")
    return render(request, 'restaurant/orders.html', {"orders": orders})

# Restaurant view order page
@login_required(login_url='/accounts/login/')
def restaurant_view_order(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    # Checks if requested order belongs to user's restaurant
    if request.user.restaurant != order.restaurant:
        raise Http404()

    return render(request, 'restaurant/view_order.html', {"order": order})

# Restaurant servers page
@login_required(login_url='/accounts/login/')
def restaurant_servers(request):
    servers = Server.objects.filter(restaurant=request.user.restaurant)
    server_requests = ServerRequest.objects.filter(restaurant=request.user.restaurant)
    # Combine server and server requests to send to template
    all_servers = []
    for s in servers:
        new_server = {}
        new_server["id"] = s.id
        new_server["name"] = s.user.name
        new_server["email"] = s.user.email
        new_server["status"] = "Accepted"
        new_server["request"] = False
        all_servers.append(new_server)
    for s in server_requests:
        new_server = {}
        new_server["id"] = s.id
        new_server["name"] = s.name
        new_server["email"] = s.email
        if s.accepted:
            new_server["status"] = "Accepted"
        else:
            new_server["status"] = "Pending"
        new_server["request"] = True
        all_servers.append(new_server)
    all_servers = sorted(all_servers, key=lambda s: s["name"])
    return render(request, 'restaurant/servers.html', {"servers": all_servers})

# Restaurant add server page
@login_required(login_url='/accounts/login/')
def restaurant_add_server(request):
    # Pass in request so it can be used in form validation
    server_request_form = ServerRequestForm(request=request)

    if request.method == "POST":
        server_request_form = ServerRequestForm(request.POST, request=request)

        if server_request_form.is_valid():
            # Create server request object
            server_request = server_request_form.save(commit=False)
            server_request.restaurant = request.user.restaurant
            server_request.save()

            # Send email to server
            body = render_to_string(
                'registration/server_link_restaurant_email.txt', {
                    'restaurant': server_request.restaurant,
                    'url': request.build_absolute_uri(
                        reverse('server_link_restaurant', args=[server_request.token])
                        )
                    }
                )
            send_mail(
                'Swick Add Server Request',
                body,
                None,
                [server_request.email]
            )
            return redirect(restaurant_servers)

    return render(request, 'restaurant/add_server.html', {
        "server_request_form": server_request_form,
    })

# Remove server's link to restaurant
@login_required(login_url='/accounts/login/')
def restaurant_delete_server(request, id):
    server = get_object_or_404(Server, id=id)
    if server.restaurant != request.user.restaurant:
        raise Http404()
    server.restaurant = None
    server.save()
    return redirect(restaurant_servers)

# Delete request to add server
@login_required(login_url='/accounts/login/')
def restaurant_delete_server_request(request, id):
    server_request = get_object_or_404(ServerRequest, id=id)
    if server_request.restaurant != request.user.restaurant:
        raise Http404()
    server_request.delete()
    return redirect(restaurant_servers)

# Restaurant account page
@login_required(login_url='/accounts/login/')
def restaurant_account(request):
    # Prefix required because both forms share a field with the same name
    user_form = UserUpdateForm(prefix="user", instance=request.user)
    restaurant_form = RestaurantForm(prefix="restaurant", instance=request.user.restaurant)

    # Update account info
    if request.method == "POST":
        user_form = UserUpdateForm(request.POST, prefix="user", instance=request.user)
        restaurant_form = RestaurantForm(
            request.POST,
            request.FILES,
            prefix="restaurant",
            instance=request.user.restaurant
        )
        if user_form.is_valid() and restaurant_form.is_valid():
            user_form.save()
            restaurant_form.save()
            timezone.activate(pytz.timezone(request.POST["restaurant-timezone"]))

    return render(request, 'restaurant/account.html', {
        "user_form": user_form,
        "restaurant_form": restaurant_form,
    })

# When server clicks on url to link restaurant
def server_link_restaurant(request, token):
    server_request = get_object_or_404(ServerRequest, token=token)
    # Set server's restaurant if they have already created account
    try:
        server = Server.objects.get(user__email=server_request.email)
        server.restaurant = server_request.restaurant
        server.save()
        server_request.delete()
    except Server.DoesNotExist:
        server_request.accepted = True
        server_request.save()

    return render(request, 'registration/server_link_restaurant_confirm.html', {
        "restaurant": server_request.restaurant.name
    })

from django.http import JsonResponse
from drf_multiple_model.mixins import FlatMultipleModelMixin
from rest_framework.decorators import api_view
from rest_framework.generics import GenericAPIView

from .models import (Order, OrderItem, Request, Restaurant, Server,
                     ServerRequest)
from .serializers import (OrderDetailsSerializer, OrderItemToCookSerializer,
                          OrderItemToSendSerializer, OrderSerializer,
                          RequestSerializer)

from swick.settings import PUSHER_APP_ID, PUSHER_KEY, PUSHER_SECRET, PUSHER_CLUSTER

from .pusher_events import send_event_order_placed, send_event_tip_added, \
    send_event_item_status_updated, send_event_order_status_updated, send_event_request_deleted
import pusher


@api_view(['POST'])
def login(request):
    """
    header:
        Authorization: Token ...
    return:
        id
        restaurant_id
        name_set
        status
    """
    # Create server account if not created
    try:
        server = Server.objects.get(user=request.user)
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

    restaurant_id = None if server.restaurant is None else server.restaurant.id
    # Check that user's name is set
    if not request.user.name:
        return JsonResponse({"id": server.id, "restaurant_id": restaurant_id, "name_set": False, "status": "success"})
    return JsonResponse({"id": server.id, "restaurant_id": restaurant_id, "name_set": True, "status": "success"})


@api_view(['POST'])
def pusher_auth(request):
    """
    header:
        Authorization: Token ...
    params:
        channel_name
        socket_id
    return:
        channel_name
        socket_id
    """
    channel = request.POST['channel_name']
    try:
        server = Server.objects.get(user=request.user)
        channel_id = int(channel.split('-')[2])
        if channel.startswith("private-server"):
            if server.id != channel_id:
                raise AssertionError("Requested unauthorized channel")
        elif channel.startswith("private-restaurant"):
            if server.restaurant is not None and server.restaurant.id != channel_id:
                raise AssertionError(
                    "Server does not have access to restaurant")
        else:
            raise AssertionError("Unknown channel requested: " + channel)

        pusher_client = pusher.Pusher(app_id=PUSHER_APP_ID,
                                      key=PUSHER_KEY,
                                      secret=PUSHER_SECRET,
                                      cluster=PUSHER_CLUSTER)

        # We must generate the token with pusher's service
        payload = pusher_client.authenticate(
            channel=request.POST['channel_name'],
            socket_id=request.POST['socket_id'])

        return JsonResponse(payload)

    except (Server.DoesNotExist, ValueError, AssertionError, IndexError) as e:
        return HttpResponseForbidden()


@api_view()
def get_orders(request):
    """
    Get list of restaurant's last 20 orders
    header:
        Authorization: Token ...
    return:
        [orders]
            id
            restaurant_name (unused)
            customer_name
            order_time
            status
        status
    """
    restaurant = request.user.server.restaurant
    if restaurant is None:
        return JsonResponse({
            "status": "restaurant_not_set"
        })
    orders = OrderSerializer(
        Order.objects.filter(restaurant=restaurant)
        .order_by("-id")[:20],
        many=True
    ).data
    return JsonResponse({"orders": orders, "status": "success"})


@api_view()
def get_order(request, order_id):
    """
    header:
        Authorization: Token ...
    return:
        order
            id
            restaurant_name (unused)
            customer_name
            order_time
            status
        status
    """
    restaurant = request.user.server.restaurant
    if restaurant is None:
        return JsonResponse({
            "status": "restaurant_not_set"
        })
    try:
        order_object = Order.objects.get(id=order_id)
    except Restaurant.DoesNotExist:
        return JsonResponse({"status": "order_does_not_exist"})
    order = OrderSerializer(order_object).data
    return JsonResponse({"order": order, "status": "success"})


@api_view()
def get_order_details(request, order_id):
    """
    header:
        Authorization: Token ...
    return:
        order_details
            id
            customer_name
            table
            order_time
            subtotal
            tax
            tip
            total
            [cooking_order_items] / [sending_order_items] / [complete_order_items]
                id
                meal_name
                quantity
                total
                status
                [order_item_cust]
                    id
                    name
                    [options]
        status
    """
    restaurant = request.user.server.restaurant
    order = Order.objects.get(id=order_id)
    # Check if a restaurant's server is making the request
    if order.restaurant != restaurant:
        return JsonResponse({"status": "invalid_request"})

    order_details = OrderDetailsSerializer(
        order
    ).data
    return JsonResponse({"order_details": order_details, "status": "success"})


@api_view()
def get_order_items_to_cook(request):
    """
    header:
        Authorization: Token ...
    return:
        [order_items]
            id
            order_id
            table
            meal_name
            quantity
            [order_item_cust]
                id
                name
                [options]
    """
    restaurant = request.user.server.restaurant
    if restaurant is None:
        return JsonResponse({
            "status": "restaurant_not_set"
        })
    order_items = OrderItemToCookSerializer(
        OrderItem.objects.filter(
            order__restaurant=restaurant, status=OrderItem.COOKING)
        .order_by("id"),
        many=True
    ).data
    return JsonResponse({"order_items": order_items, "status": "success"})


class ServerGetItemsToSend(FlatMultipleModelMixin, GenericAPIView):
    """
    Get list of restaurant's order items to send and requests
    Uses django-rest-multiple-models to sort and send different models together
    header:
        Authorization: Token ...
    return:
        [OrderItem or Request]
            id
            order_id (only for OrderItem)
            customer_name
            table
            meal_name or request_name
            time
            type
    """

    # Sort combined query list by time
    sorting_fields = ['time', 'id']

    # Overrided function to build combined query list
    def get_querylist(self):
        restaurant = self.request.user.server.restaurant
        order_items = OrderItem.objects.filter(
            order__restaurant=restaurant,
            status=OrderItem.SENDING
        )
        requests = Request.objects.filter(
            request_option__restaurant=restaurant)

        querylist = [
            {'queryset': order_items, 'serializer_class': OrderItemToSendSerializer},
            {'queryset': requests, 'serializer_class': RequestSerializer}
        ]
        return querylist

    # GET request
    def get(self, request, *args, **kwargs):
        restaurant = request.user.server.restaurant
        if restaurant is None:
            return JsonResponse({
                "status": "restaurant_not_set"
            })
        return self.list(request, *args, **kwargs)


@api_view(['POST'])
def update_order_item_status(request):
    """
    header:
        Authorization: Token ...
    params:
        order_item_id
        status
    return:
        status
    """
    restaurant = request.user.server.restaurant
    item = OrderItem.objects.get(id=request.POST.get("order_item_id"))

    # Check if a restaurant's server is making the request
    if item.order.restaurant != restaurant:
        return JsonResponse({"status": "invalid_request"})

    order = item.order
    if item.status != request.POST.get("status"):
        new_status = request.POST.get("status")

        # Update item with new status
        item.status = new_status
        item.save()
        send_event_item_status_updated(item)

        # Check if order status needs to be updated
        if new_status == OrderItem.COMPLETE:
            if not OrderItem.objects.filter(order=order).exclude(status=OrderItem.COMPLETE).exists():
                order.status = Order.COMPLETE
                order.save()
                send_event_order_status_updated(order)
        else:
            if order.status != Order.ACTIVE:
                order.status = Order.ACTIVE
                order.save()
                send_event_order_status_updated(order)

    return JsonResponse({"status": "success"})


@api_view(['POST'])
def delete_request(request):
    """
    header:
        Authorization: Token ...
    params:
        id
    return:
        status
    """
    restaurant = request.user.server.restaurant
    request_object = Request.objects.get(id=request.POST.get("id"))

    # Check if a restaurant's server is making the request
    if request_object.request_option.restaurant != restaurant:
        return JsonResponse({"status": "invalid_request"})

    send_event_request_deleted(request_object)
    request_object.delete()

    return JsonResponse({"status": "success"})


@api_view()
def get_info(request):
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

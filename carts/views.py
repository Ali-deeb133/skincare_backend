from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404

from .models import Cart, CartItem
from products.models import Product
from .serializers import CartSerializer


def get_user_cart(user):
    cart, created = Cart.objects.get_or_create(user=user)
    return cart


class CartDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cart = get_user_cart(request.user)
        serializer = CartSerializer(cart)
        return Response(serializer.data)


# إضافة منتج
class AddToCartAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        product_id = request.data.get("product_id")
        quantity = int(request.data.get("quantity", 1))

        product = get_object_or_404(Product, id=product_id)
        cart = get_user_cart(request.user)

        item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product
        )

        if not created:
            item.quantity += quantity
        else:
            item.quantity = quantity

        item.save()
        serializer = CartSerializer(cart)
        return Response({
            "message": "Product added to cart",
            "cart": serializer.data
        })

class UpdateCartItemAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        item_id = request.data.get("item_id")
        action = request.data.get("action")  # increase / decrease

        item = get_object_or_404(
            CartItem,
            id=item_id,
            cart__user=request.user
        )

        cart = item.cart

        if action == "increase":
            item.quantity += 1

        elif action == "decrease":
            item.quantity -= 1
            if item.quantity <= 0:
                item.delete()
                serializer = CartSerializer(cart)
                return Response({
                    "message": "Item removed",
                    "cart": serializer.data
                })

        item.save()
        serializer = CartSerializer(cart)
        return Response({
            "message": "Cart updated",
            "cart": serializer.data
            })

class RemoveCartItemAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        item_id = request.data.get("item_id")

        item = get_object_or_404(
            CartItem,
            id=item_id,
            cart__user=request.user
        )
        cart = item.cart
        item.delete()

        serializer = CartSerializer(cart)
        return Response({
            "message": "Item removed",
            "cart": serializer.data
        })
    
class ClearCartAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        cart = get_user_cart(request.user)
        cart.items.all().delete()

        serializer = CartSerializer(cart)
        return Response({
            "message": "Cart cleared",
            "cart": serializer.data
        })

from django.urls import path
from .views import *

urlpatterns = [
    path("", CartDetailAPIView.as_view()),
    path("add/", AddToCartAPIView.as_view()),
    path("update/", UpdateCartItemAPIView.as_view()),
    path("remove/", RemoveCartItemAPIView.as_view()),
    path("clear/", ClearCartAPIView.as_view()),
]

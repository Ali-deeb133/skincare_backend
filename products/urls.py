from django.urls import path
from .views import ProductListView
from .views import ProductTypeListAPIView

urlpatterns = [
    path("", ProductListView.as_view(), name="product-list"),
    path("product-types/", ProductTypeListAPIView.as_view()),
    
]

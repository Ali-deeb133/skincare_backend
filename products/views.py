from rest_framework import generics
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from .models import Product
from .serializers import ProductSerializer
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.response import Response

# List all products + filter by product_type + price range
class ProductListView(generics.ListAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = {
        'price': ['gte', 'lte'],  # min/max price
        'product_type': ['exact'],  # filter by type
    }
    search_fields = ['product_name', 'clean_ingreds']  # optional text search
    ordering_fields = ['price', 'product_name']

class ProductTypeListAPIView(APIView):
    def get(self, request):
        types = Product.objects.values_list(
            'product_type', flat=True
        ).distinct()

        return Response(types)
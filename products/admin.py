from django.contrib import admin
from .models import Product

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("id", "product_name", "product_type", "price")
    list_filter = ("product_type",)
    search_fields = ("product_name", "clean_ingreds")

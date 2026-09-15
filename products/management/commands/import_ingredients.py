import csv
from django.core.management.base import BaseCommand
from products.models import Product


class Command(BaseCommand):
    help = "Import ingredients and match with product name"

    def handle(self, *args, **kwargs):

        with open("products.csv", newline='', encoding="utf-8") as f:
            reader = csv.DictReader(f)

            updated = 0
            not_found = 0

            for row in reader:
                name = row.get("product_name", "").strip()
                ingreds = row.get("clean_ingreds", "").strip()

                try:
                    product = Product.objects.get(product_name__iexact=name)
                    product.clean_ingreds = ingreds
                    product.save()
                    updated += 1
                except Product.DoesNotExist:
                    not_found += 1

            print(f"Updated: {updated}")
            print(f"Not Found: {not_found}")

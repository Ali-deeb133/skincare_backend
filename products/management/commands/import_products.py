# products/management/commands/import_products.py

import csv
import os
from django.core.management.base import BaseCommand
from products.models import Product
from django.conf import settings

class Command(BaseCommand):
    help = 'Import products from CSV'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='Path to the CSV file')

    def handle(self, *args, **kwargs):
        csv_file = kwargs['csv_file']

        default_image = '1.jpg'  # الصورة الافتراضية
        media_path = os.path.join(settings.MEDIA_ROOT, 'product_images')

        with open(csv_file, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)

            for row in reader:

                # تحقق إذا الصورة موجودة
                image_filename = os.path.basename(row.get('url', '').strip())
                image_path_full = os.path.join(media_path, image_filename)

                if not image_filename or not os.path.exists(image_path_full):
                    image_filename = default_image  # استخدم الصورة الافتراضية

                # path داخل media/ فقط
                final_image_path = os.path.join('product_images', image_filename)

                # إنشاء المنتج
                product = Product.objects.create(
                    product_name=row.get('product_name', '').strip(),
                    product_type=row.get('product_type', '').strip(),
                    clean_ingreds=row.get('clean_ingreds', '').strip(),
                    price=float(row.get('price', 0)),
                    url=final_image_path
                )

                self.stdout.write(self.style.SUCCESS(f'Inserted: {product.product_name}'))

        self.stdout.write(self.style.SUCCESS('CSV import completed!'))

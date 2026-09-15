from django.db import models

# Create your models here.
from django.db import models

class Product(models.Model):
    product_name = models.CharField(max_length=255)
    product_type = models.CharField(max_length=100)
    clean_ingreds = models.TextField()
    price = models.FloatField()
    url = models.CharField(max_length=500)
    clean_ingreds = models.TextField(blank=True, null=True)


    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.product_name

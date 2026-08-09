"""
apps/products/signals.py

Maintains Product.search_vector from Product.name and Product.description.

The stored SearchVectorField is required by the DDS for PostgreSQL full-text
search. A post_save signal keeps it synchronized without recursively calling
Product.save().
"""

from django.contrib.postgres.search import SearchVector
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Product


@receiver(post_save, sender=Product)
def update_product_search_vector(sender, instance, **kwargs):
    """
    Synchronize the stored search vector after a Product is saved.

    QuerySet.update() is deliberately used instead of instance.save() to
    prevent recursive signal execution.
    """
    sender.objects.filter(pk=instance.pk).update(
        search_vector=SearchVector(
            "name",
            "description",
            config="english",
        ),
    )

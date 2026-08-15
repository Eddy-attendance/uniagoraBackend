from django.db import models

from apps.common.managers import SoftDeleteQuerySet


class ProductQuerySet(SoftDeleteQuerySet):
    def visible(self):
        from .models import ProductStatus

        return self.alive().filter(status=ProductStatus.ACTIVE)

    def for_university(self, university):
        return self.filter(university=university)


class ProductManager(models.Manager.from_queryset(ProductQuerySet)):
    pass

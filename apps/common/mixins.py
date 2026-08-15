"""
Generic, domain-agnostic model mixins. Configured by the consuming model
via class attributes rather than hardcoding any field name, so this file
carries no domain knowledge of its own.
"""

from django.utils.text import slugify


class AutoSlugMixin:
    slug_source_field: str = "name"
    slug_field_name: str = "slug"
    slug_max_length: int = 255

    def _generate_unique_slug(self) -> str:
        source_value = getattr(self, self.slug_source_field)
        base_slug = slugify(source_value)[: self.slug_max_length]
        model_class = self.__class__

        slug = base_slug
        counter = 1
        while (
            model_class.objects.filter(**{self.slug_field_name: slug})
            .exclude(pk=self.pk)
            .exists()
        ):
            suffix = f"-{counter}"
            slug = f"{base_slug[: self.slug_max_length - len(suffix)]}{suffix}"
            counter += 1
        return slug

    def save(self, *args, **kwargs):
        if not getattr(self, self.slug_field_name):
            setattr(self, self.slug_field_name, self._generate_unique_slug())
        super().save(*args, **kwargs)

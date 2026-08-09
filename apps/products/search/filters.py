"""
apps/products/search/filters.py

Category / price / condition filter composition (Architecture §11: search
composition lives inside `products/search/`, not a standalone `search` app).
Plain, composable functions over a queryset — not a DRF FilterBackend class —
so they apply identically whether the request is a plain browse or a keyword
search (Architecture §11's stated reason for folding search into `products`).
"""


def apply_category_filter(queryset, category_slug):
    if not category_slug:
        return queryset
    return queryset.filter(
        category_links__category__slug=category_slug,
        category_links__category__is_active=True,
    ).distinct()


def apply_price_filter(queryset, min_price=None, max_price=None):
    if min_price is not None:
        queryset = queryset.filter(price__gte=min_price)
    if max_price is not None:
        queryset = queryset.filter(price__lte=max_price)
    return queryset


def apply_condition_filter(queryset, condition):
    if not condition:
        return queryset
    return queryset.filter(condition=condition)


_ORDERING_MAP = {
    "newest": "-listed_at",
    "price_asc": "price",
    "price_desc": "-price",
}


def apply_ordering(queryset, ordering):
    """Defaults to 'newest' (-listed_at) for any unrecognized/absent value —
    DDS §8 names `listed_at` as the field driving 'Newest' sort."""
    return queryset.order_by(_ORDERING_MAP.get(ordering, "-listed_at"))

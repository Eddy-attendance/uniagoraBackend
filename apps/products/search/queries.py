"""
apps/products/search/queries.py

PostgreSQL full-text search composition (Architecture §11, DDS §4.7). MVP
implementation uses `django.contrib.postgres.search` `SearchQuery`/`SearchRank`
against the stored, GIN-indexed `search_vector` field — no external search
engine is introduced (instruction §14/§25).
"""

from django.contrib.postgres.search import SearchQuery, SearchRank
from django.db.models import F


def apply_keyword_search(queryset, keyword):
    """Filters by `search_vector` and orders by relevance rank when a keyword
    is present. Covers `Product.name` + `Product.description` only, per the
    DDS's explicit MVP search-strategy statement (DDS §13, Assumption 10).
    """
    if not keyword:
        return queryset
    query = SearchQuery(keyword, config="english")
    return (
        queryset.filter(search_vector=query)
        .annotate(rank=SearchRank(F("search_vector"), query))
        .order_by("-rank")
    )

from django.contrib.postgres.search import SearchQuery, SearchRank
from django.db.models import F


def apply_keyword_search(queryset, keyword):
    """Filters by `search_vector` and orders by relevance rank when a keyword
    is present. Covers `Product.name` + `Product.description` only
    """
    if not keyword:
        return queryset
    query = SearchQuery(keyword, config="english")
    return (
        queryset.filter(search_vector=query)
        .annotate(rank=SearchRank(F("search_vector"), query))
        .order_by("-rank")
    )

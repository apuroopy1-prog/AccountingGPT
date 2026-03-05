"""
Shared cache invalidation — call invalidate_user_caches(user_id) whenever
new transaction data is added so AI insights and anomaly detection refresh.
"""

# These are populated at import time by the respective routers.
# Using a mutable dict so routers can register their own cache dicts.
_caches: dict[str, dict] = {}


def register_cache(name: str, cache_dict: dict) -> None:
    _caches[name] = cache_dict


def invalidate_user_caches(user_id: int) -> None:
    for cache in _caches.values():
        cache.pop(user_id, None)

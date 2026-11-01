"""Integration boundary for OFTLY INTELLIGENCE (and any other local intelligence service).

OFTLY's core never imports a model. It talks to a *provider* through this small, versioned contract
(docs/INTELLIGENCE_CONTRACT.md). Default = NullProvider (does nothing, deterministic). Set OFTLY_INTELLIGENCE_URL to a
loopback address to enable the HTTP provider. Every call is bounded, validated and failure-tolerant: if the provider is
slow, down, malformed or hostile, OFTLY behaves exactly as if it were not configured."""
import os
from functools import lru_cache

from .base import CONTRACT, NullProvider, Provider
from .http_provider import HttpProvider, UnsafeURL

__all__ = ["CONTRACT", "Provider", "NullProvider", "HttpProvider", "UnsafeURL", "get_provider", "reset"]


@lru_cache(maxsize=1)
def get_provider() -> Provider:
    url = os.environ.get("OFTLY_INTELLIGENCE_URL", "").strip()
    if not url:
        return NullProvider()
    try:
        return HttpProvider(url)
    except UnsafeURL:
        return NullProvider(reason="OFTLY_INTELLIGENCE_URL must be a loopback http:// address; ignored.")


def reset():
    get_provider.cache_clear()

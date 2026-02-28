"""Tests for protocollab.loader.cache — MemoryCache and BaseCache contract."""

import pytest
from protocollab.loader.cache.memory_cache import MemoryCache


@pytest.fixture()
def cache():
    return MemoryCache()


class TestMemoryCache:
    def test_get_on_empty_returns_none(self, cache):
        assert cache.get("any_key") is None

    def test_set_and_get_round_trip(self, cache):
        value = {"version": "1.0"}
        cache.set("key1", value)
        assert cache.get("key1") == value

    def test_get_unknown_key_returns_none(self, cache):
        cache.set("key1", {"a": 1})
        assert cache.get("unknown") is None

    def test_set_overwrites_existing(self, cache):
        cache.set("k", {"v": 1})
        cache.set("k", {"v": 2})
        assert cache.get("k") == {"v": 2}

    def test_clear_removes_all_entries(self, cache):
        cache.set("k1", {"a": 1})
        cache.set("k2", {"b": 2})
        cache.clear()
        assert cache.get("k1") is None
        assert cache.get("k2") is None
        assert len(cache) == 0

    def test_len_reflects_entry_count(self, cache):
        assert len(cache) == 0
        cache.set("k1", {})
        assert len(cache) == 1
        cache.set("k2", {})
        assert len(cache) == 2

    def test_clear_on_empty_is_safe(self, cache):
        cache.clear()  # must not raise
        assert len(cache) == 0

    def test_multiple_independent_caches(self):
        c1, c2 = MemoryCache(), MemoryCache()
        c1.set("k", {"source": "c1"})
        assert c2.get("k") is None  # isolated

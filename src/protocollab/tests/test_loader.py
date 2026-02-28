"""Tests for protocollab.loader — load_protocol() and ProtocolLoader."""

import pytest
from unittest.mock import patch, call

from protocollab.exceptions import FileLoadError, YAMLParseError
from protocollab.loader import ProtocolLoader, load_protocol, _default_loader
from protocollab.loader.cache.memory_cache import MemoryCache


# ---------------------------------------------------------------------------
# load_protocol() — public API
# ---------------------------------------------------------------------------

class TestLoadProtocol:
    def test_load_simple_returns_dict(self, simple_yaml):
        data = load_protocol(str(simple_yaml))
        assert isinstance(data, dict)
        assert data["version"] == "1.0"
        assert data["description"] == "Simple test protocol"

    def test_load_with_include(self, yaml_with_include):
        data = load_protocol(str(yaml_with_include))
        assert isinstance(data, dict)
        assert "types" in data
        assert "uint32" in data["types"]

    def test_missing_file_raises_file_load_error(self):
        with pytest.raises(FileLoadError):
            load_protocol("/nonexistent/missing.yaml")

    def test_invalid_yaml_raises_yaml_parse_error(self, invalid_yaml):
        with pytest.raises(YAMLParseError):
            load_protocol(str(invalid_yaml))

    def test_returns_plain_dict_not_commented_map(self, simple_yaml):
        data = load_protocol(str(simple_yaml))
        # Must be a plain dict, not ruamel CommentedMap
        assert type(data) is dict


# ---------------------------------------------------------------------------
# Caching behaviour
# ---------------------------------------------------------------------------

class TestLoadProtocolCache:
    def test_cache_hit_skips_disk_on_second_call(self, simple_yaml):
        _default_loader.clear_cache()
        with patch.object(
            _default_loader, "_load_raw", wraps=_default_loader._load_raw
        ) as spy:
            load_protocol(str(simple_yaml))
            load_protocol(str(simple_yaml))
            assert spy.call_count == 1  # second call served from cache

    def test_no_cache_default_creates_memory_cache(self, simple_yaml):
        # ProtocolLoader(cache=None) creates an internal MemoryCache by default,
        # so the second call is served from cache (1 disk read total).
        loader = ProtocolLoader(cache=None)
        with patch.object(loader, "_load_raw", wraps=loader._load_raw) as spy:
            loader.load(str(simple_yaml))
            loader.load(str(simple_yaml))
            assert spy.call_count == 1  # second call from cache

    def test_use_cache_false_bypasses_cache(self, simple_yaml):
        # Each call with use_cache=False gets a fresh loader (no shared cache)
        data1 = load_protocol(str(simple_yaml), use_cache=False)
        data2 = load_protocol(str(simple_yaml), use_cache=False)
        assert data1 == data2  # results are equal even without cache

    def test_clear_cache_forces_reload(self, simple_yaml):
        _default_loader.clear_cache()
        with patch.object(
            _default_loader, "_load_raw", wraps=_default_loader._load_raw
        ) as spy:
            load_protocol(str(simple_yaml))
            _default_loader.clear_cache()
            load_protocol(str(simple_yaml))
            assert spy.call_count == 2  # reloaded after clear


# ---------------------------------------------------------------------------
# ProtocolLoader — low-level class
# ---------------------------------------------------------------------------

class TestProtocolLoader:
    def test_custom_cache_is_populated(self, simple_yaml):
        cache = MemoryCache()
        loader = ProtocolLoader(cache=cache)
        assert len(cache) == 0
        loader.load(str(simple_yaml))
        assert len(cache) == 1

    def test_load_twice_uses_cache(self, simple_yaml):
        cache = MemoryCache()
        loader = ProtocolLoader(cache=cache)
        loader.load(str(simple_yaml))
        with patch.object(loader, "_load_raw", wraps=loader._load_raw) as spy:
            loader.load(str(simple_yaml))
            spy.assert_not_called()

    def test_clear_cache_method(self, simple_yaml):
        cache = MemoryCache()
        loader = ProtocolLoader(cache=cache)
        loader.load(str(simple_yaml))
        assert len(cache) == 1
        loader.clear_cache()
        assert len(cache) == 0

    def test_config_forwarded_to_load(self, simple_yaml):
        """Loader accepts config dict without error."""
        loader = ProtocolLoader(config={"max_struct_depth": 10})
        data = loader.load(str(simple_yaml))
        assert isinstance(data, dict)

    def test_missing_file_propagates_as_file_load_error(self):
        loader = ProtocolLoader()
        with pytest.raises(FileLoadError):
            loader.load("/does/not/exist.yaml")

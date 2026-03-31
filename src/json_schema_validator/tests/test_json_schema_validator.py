"""Tests for json_schema_validator — models, backends, and factory."""

from __future__ import annotations

import json
import pytest

from json_schema_validator.models import SchemaValidationError
from json_schema_validator.backends.base import AbstractSchemaValidator
from json_schema_validator.backends.jsonschema_backend import JsonschemaBackend
from json_schema_validator.factory import ValidatorFactory, BackendNotAvailableError, available_backends


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

SIMPLE_SCHEMA: dict = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "required": ["name"],
    "properties": {
        "name": {"type": "string"},
        "age": {"type": "integer", "minimum": 0},
    },
    "additionalProperties": False,
}

VALID_DATA: dict = {"name": "Alice", "age": 30}
MISSING_NAME: dict = {"age": 30}
BAD_TYPE_DATA: dict = {"name": 42}
EXTRA_KEY_DATA: dict = {"name": "Alice", "unexpected": True}


# ===========================================================================
# SchemaValidationError model
# ===========================================================================


class TestSchemaValidationError:
    def test_str_includes_path_and_message(self) -> None:
        err = SchemaValidationError(path="meta.id", message="does not match pattern")
        assert "meta.id" in str(err)
        assert "does not match pattern" in str(err)

    def test_default_schema_path_is_empty(self) -> None:
        err = SchemaValidationError(path="x", message="y")
        assert err.schema_path == ""

    def test_fields_stored(self) -> None:
        err = SchemaValidationError(path="a.b", message="msg", schema_path="props/a")
        assert err.path == "a.b"
        assert err.message == "msg"
        assert err.schema_path == "props/a"


# ===========================================================================
# AbstractSchemaValidator ABC
# ===========================================================================


class TestAbstractSchemaValidator:
    def test_is_abstract(self) -> None:
        with pytest.raises(TypeError):
            AbstractSchemaValidator()  # type: ignore[abstract]

    def test_concrete_subclass_works(self) -> None:
        class AlwaysOk(AbstractSchemaValidator):
            def validate(self, schema, data):
                return []

        v = AlwaysOk()
        assert v.validate({}, {}) == []


# ===========================================================================
# JsonschemaBackend
# ===========================================================================


class TestJsonschemaBackend:
    def test_valid_data_returns_empty(self) -> None:
        v = JsonschemaBackend()
        assert v.validate(SIMPLE_SCHEMA, VALID_DATA) == []

    def test_missing_required_field(self) -> None:
        v = JsonschemaBackend()
        errors = v.validate(SIMPLE_SCHEMA, MISSING_NAME)
        assert len(errors) > 0
        assert all(isinstance(e, SchemaValidationError) for e in errors)

    def test_missing_required_field_path(self) -> None:
        v = JsonschemaBackend()
        errors = v.validate(SIMPLE_SCHEMA, MISSING_NAME)
        # root-level missing required → path is "(root)"
        assert any("(root)" in e.path or "name" in e.message for e in errors)

    def test_wrong_type_detected(self) -> None:
        v = JsonschemaBackend()
        errors = v.validate(SIMPLE_SCHEMA, BAD_TYPE_DATA)
        assert len(errors) > 0
        assert any("name" in e.path for e in errors)

    def test_additional_properties_rejected(self) -> None:
        v = JsonschemaBackend()
        errors = v.validate(SIMPLE_SCHEMA, EXTRA_KEY_DATA)
        assert len(errors) > 0

    def test_error_has_non_empty_message(self) -> None:
        v = JsonschemaBackend()
        errors = v.validate(SIMPLE_SCHEMA, MISSING_NAME)
        assert all(len(e.message) > 0 for e in errors)

    def test_error_has_schema_path(self) -> None:
        v = JsonschemaBackend()
        errors = v.validate(SIMPLE_SCHEMA, MISSING_NAME)
        assert all(isinstance(e.schema_path, str) for e in errors)

    def test_cache_enabled_by_default(self) -> None:
        v = JsonschemaBackend()
        assert v._cache_enabled is True

    def test_cache_disabled(self) -> None:
        v = JsonschemaBackend(cache=False)
        assert v._cache_enabled is False
        # Should still work correctly
        assert v.validate(SIMPLE_SCHEMA, VALID_DATA) == []

    def test_nested_path_dot_notation(self) -> None:
        schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "required": ["meta"],
            "properties": {
                "meta": {
                    "type": "object",
                    "required": ["id"],
                    "properties": {"id": {"type": "string", "pattern": "^[a-z_]+$"}},
                }
            },
        }
        v = JsonschemaBackend()
        errors = v.validate(schema, {"meta": {"id": "INVALID_UPPER"}})
        assert any("id" in e.path for e in errors)

    def test_seq_array_index_dot_notation(self) -> None:
        schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "properties": {
                "seq": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["id"],
                        "properties": {"id": {"type": "string"}},
                    },
                }
            },
        }
        v = JsonschemaBackend()
        errors = v.validate(schema, {"seq": [{"id": 123}]})
        assert any("[0]" in e.path for e in errors)

    def test_validator_cached_same_schema(self) -> None:
        v = JsonschemaBackend(cache=True)
        schema = dict(SIMPLE_SCHEMA)
        v.validate(schema, VALID_DATA)
        v.validate(schema, VALID_DATA)
        assert id(schema) in v._cache

    def test_empty_schema_accepts_anything(self) -> None:
        v = JsonschemaBackend()
        assert v.validate({}, {"any": "value"}) == []


# ===========================================================================
# ValidatorFactory
# ===========================================================================


class TestValidatorFactory:
    def test_auto_returns_backend(self) -> None:
        v = ValidatorFactory.create(backend="auto")
        assert isinstance(v, AbstractSchemaValidator)

    def test_explicit_jsonschema_backend(self) -> None:
        v = ValidatorFactory.create(backend="jsonschema")
        assert isinstance(v, JsonschemaBackend)

    def test_unknown_backend_raises(self) -> None:
        with pytest.raises(BackendNotAvailableError):
            ValidatorFactory.create(backend="nonexistent_backend")

    def test_auto_mode_validates_correctly(self) -> None:
        v = ValidatorFactory.create(backend="auto")
        errors = v.validate(SIMPLE_SCHEMA, MISSING_NAME)
        assert len(errors) > 0

    def test_auto_mode_valid_data(self) -> None:
        v = ValidatorFactory.create(backend="auto")
        assert v.validate(SIMPLE_SCHEMA, VALID_DATA) == []

    def test_cache_false_still_works(self) -> None:
        v = ValidatorFactory.create(backend="jsonschema", cache=False)
        assert v.validate(SIMPLE_SCHEMA, VALID_DATA) == []

    def test_instance_method_returns_same_instance(self) -> None:
        factory = ValidatorFactory()
        v1 = factory._get_or_create("jsonschema")
        v2 = factory._get_or_create("jsonschema")
        assert v1 is v2

    def test_fastjsonschema_unavailable_raises(self) -> None:
        # fastjsonschema is not installed in the test environment
        try:
            import fastjsonschema  # noqa: F401

            pytest.skip("fastjsonschema is installed; skipping unavailability test")
        except ImportError:
            pass
        with pytest.raises(BackendNotAvailableError):
            ValidatorFactory.create(backend="fastjsonschema")


# ===========================================================================
# available_backends()
# ===========================================================================


class TestAvailableBackends:
    def test_returns_list(self) -> None:
        result = available_backends()
        assert isinstance(result, list)

    def test_jsonschema_always_available(self) -> None:
        result = available_backends()
        assert "jsonschema" in result

    def test_fastjsonschema_not_in_auto(self) -> None:
        # fastjsonschema requires explicit opt-in and should NOT be returned
        # by auto mode — verified by checking it's not in _AUTO_PRIORITY
        from json_schema_validator.factory import _AUTO_PRIORITY

        assert "fastjsonschema" not in _AUTO_PRIORITY


# ===========================================================================
# Error path normalization — edge cases
# ===========================================================================


class TestErrorPathNormalization:
    def test_root_level_error_returns_root(self) -> None:
        v = JsonschemaBackend()
        errors = v.validate({"type": "object", "required": ["x"]}, {})
        assert any("(root)" in e.path or e.path == "(root)" for e in errors)

    def test_nested_key_path(self) -> None:
        schema = {
            "type": "object",
            "properties": {
                "a": {
                    "type": "object",
                    "properties": {"b": {"type": "integer"}},
                }
            },
        }
        v = JsonschemaBackend()
        errors = v.validate(schema, {"a": {"b": "not-an-int"}})
        assert any("a" in e.path for e in errors)
        assert any("b" in e.path for e in errors)


# ===========================================================================
# Integration: protocollab-like schema
# ===========================================================================


class TestProtocollabLikeSchema:
    """Verify the backend handles the actual protocollab base.schema.json."""

    BASE_SCHEMA: dict = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "required": ["meta"],
        "properties": {
            "meta": {
                "type": "object",
                "required": ["id"],
                "properties": {
                    "id": {
                        "type": "string",
                        "pattern": "^[a-z_][a-z0-9_]*$",
                    },
                    "endian": {"type": "string", "enum": ["le", "be"]},
                },
                "additionalProperties": True,
            },
            "seq": {"type": "array", "items": {"type": "object"}},
        },
        "additionalProperties": True,
    }

    def test_valid_spec(self) -> None:
        v = JsonschemaBackend()
        assert v.validate(self.BASE_SCHEMA, {"meta": {"id": "ping_protocol"}}) == []

    def test_missing_meta(self) -> None:
        v = JsonschemaBackend()
        errors = v.validate(self.BASE_SCHEMA, {"seq": []})
        assert len(errors) > 0

    def test_bad_id_pattern(self) -> None:
        v = JsonschemaBackend()
        errors = v.validate(self.BASE_SCHEMA, {"meta": {"id": "PingProtocol"}})
        assert len(errors) > 0
        assert any("id" in e.path for e in errors)

    def test_bad_endian_enum(self) -> None:
        v = JsonschemaBackend()
        errors = v.validate(
            self.BASE_SCHEMA, {"meta": {"id": "ping_protocol", "endian": "middle"}}
        )
        assert len(errors) > 0
        assert any("endian" in e.path for e in errors)

    def test_seq_items_type_error(self) -> None:
        v = JsonschemaBackend()
        errors = v.validate(self.BASE_SCHEMA, {"meta": {"id": "p"}, "seq": ["not-an-object"]})
        assert len(errors) > 0

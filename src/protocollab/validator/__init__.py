"""Structural validation for ProtocolLab protocol specifications."""

from typing import Optional

from protocollab.exceptions import FileLoadError, YAMLParseError
from protocollab.loader import load_protocol
from protocollab.validator.models import ValidationError, ValidationResult
from protocollab.validator.schema_validator import SchemaValidator

__all__ = [
    "validate_protocol",
    "ValidationResult",
    "ValidationError",
    "SchemaValidator",
]


def validate_protocol(
    file_path: str,
    schema_path: Optional[str] = None,
) -> ValidationResult:
    """Load and structurally validate a protocol YAML file.

    Parameters
    ----------
    file_path:
        Path to the root protocol YAML file.
    schema_path:
        Optional path to a custom JSON Schema.  Defaults to
        ``validator/schemas/base.schema.json``.

    Returns
    -------
    ValidationResult
        Contains ``is_valid``, ``errors`` (list of :class:`ValidationError`),
        and ``file_path``.

    Raises
    ------
    FileLoadError
        When the file cannot be opened.
    YAMLParseError
        When the file contains invalid YAML.
    """
    data = load_protocol(file_path)
    validator = SchemaValidator(schema_path=schema_path)
    errors = validator.validate(data)
    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        file_path=file_path,
    )

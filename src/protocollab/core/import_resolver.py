"""Resolve ``imports:`` directives in protocol specs, detect cyclic imports."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, FrozenSet, Optional

from protocollab.core.models import ProtocolSpec
from protocollab.core.parser import parse_spec
from protocollab.exceptions import YAMLParseError
from protocollab.loader import load_protocol


class CyclicImportError(YAMLParseError):
    """Raised when a cyclic chain of ``imports:`` is detected.

    Corresponds to CLI exit code 2 (inherited from :class:`YAMLParseError`).
    """


class ImportResolver:
    """Walk the ``imports:`` graph of a protocol spec, resolving every file.

    The resolver caches already-loaded specs by their resolved absolute path so
    that a spec referenced from multiple parents is parsed only once.

    Example
    -------
    >>> resolver = ImportResolver()
    >>> spec = resolver.resolve(Path("examples/simple/ping_protocol.yaml"))
    >>> spec.meta.id
    'ping_protocol'
    """

    def __init__(self) -> None:
        self._cache: Dict[str, ProtocolSpec] = {}

    def resolve(
        self,
        spec_path: Path,
        *,
        _visited: Optional[FrozenSet[str]] = None,
    ) -> ProtocolSpec:
        """Load *spec_path*, recursively resolving all transitive imports.

        Parameters
        ----------
        spec_path:
            Path (relative or absolute) to the ``.yaml`` spec file.
        _visited:
            Internal — set of already-visited absolute paths used for cycle
            detection.  Callers should not pass this argument.

        Returns
        -------
        ProtocolSpec
            Fully resolved spec, with ``resolved_imports`` populated.

        Raises
        ------
        CyclicImportError
            If a cycle is detected in the ``imports:`` graph.
        protocollab.exceptions.FileLoadError
            If *spec_path* (or any transitive import) cannot be read.
        protocollab.exceptions.YAMLParseError
            If *spec_path* (or any transitive import) contains invalid YAML.
        """
        abs_path = str(spec_path.resolve())

        if _visited is None:
            _visited = frozenset()

        if abs_path in _visited:
            raise CyclicImportError(
                f"Cyclic import detected: {abs_path!r} is already in the "
                f"current import chain: {sorted(_visited)}"
            )

        if abs_path in self._cache:
            return self._cache[abs_path]

        _visited = _visited | {abs_path}

        # Load & parse the spec itself
        raw_data = load_protocol(str(spec_path))
        spec = parse_spec(raw_data, base_path=spec_path.parent)

        # Recursively resolve every declared import
        resolved: Dict[str, ProtocolSpec] = {}
        for import_path in spec.imports:
            child_path = spec_path.parent / import_path
            resolved[import_path] = self.resolve(child_path, _visited=_visited)

        # Attach resolved imports and cache
        spec = spec.model_copy(update={"resolved_imports": resolved})
        self._cache[abs_path] = spec
        return spec

    def clear_cache(self) -> None:
        """Evict all cached specs (useful in tests)."""
        self._cache.clear()

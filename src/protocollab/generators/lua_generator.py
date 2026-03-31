"""Lua / Wireshark dissector generator for `protocollab` protocol specifications."""

import json
from pathlib import Path
from typing import Any, Dict, List

from jinja2 import Environment, FileSystemLoader

from protocollab.expression import (
    Attribute,
    BinOp,
    Literal,
    Name,
    Subscript,
    Ternary,
    UnaryOp,
    parse_expr,
)
from protocollab.generators.base_generator import BaseGenerator, GeneratorError

# lua_type, size_bytes, optional_base
_LUA_TYPE_MAP: Dict[str, tuple] = {
    "u1": ("uint8", 1, None),
    "u2": ("uint16", 2, "base.DEC"),
    "u4": ("uint32", 4, "base.DEC"),
    "u8": ("uint64", 8, "base.DEC"),
    "s1": ("int8", 1, None),
    "s2": ("int16", 2, "base.DEC"),
    "s4": ("int32", 4, "base.DEC"),
    "s8": ("int64", 8, "base.DEC"),
    "str": ("string", None, None),  # requires 'size' in field spec
}

_TEMPLATES_DIR = Path(__file__).parent / "templates" / "lua"


def _lua_string_literal(value: str) -> str:
    return json.dumps(value)


def _lua_literal(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        return _lua_string_literal(value)
    return repr(value)


def _compile_lua_expr(node: Any) -> str:
    if isinstance(node, Literal):
        return _lua_literal(node.value)
    if isinstance(node, Name):
        return f"value_{node.name}"
    if isinstance(node, Attribute):
        return f"({_compile_lua_expr(node.obj)}).{node.attr}"
    if isinstance(node, Subscript):
        return f"({_compile_lua_expr(node.obj)})[{_compile_lua_expr(node.index)}]"
    if isinstance(node, UnaryOp):
        operand = _compile_lua_expr(node.operand)
        if node.op == "-":
            return f"(-({operand}))"
        if node.op == "not":
            return f"(not ({operand}))"
        raise GeneratorError(
            f"Unsupported unary operator {node.op!r} in Lua expression generation."
        )
    if isinstance(node, BinOp):
        left = _compile_lua_expr(node.left)
        right = _compile_lua_expr(node.right)
        if node.op == "!=":
            return f"(({left}) ~= ({right}))"
        if node.op == "//":
            return f"math.floor(({left}) / ({right}))"
        if node.op == "<<":
            return f"bit32.lshift(({left}), ({right}))"
        if node.op == ">>":
            return f"bit32.rshift(({left}), ({right}))"
        if node.op == "&":
            return f"bit32.band(({left}), ({right}))"
        if node.op == "^":
            return f"bit32.bxor(({left}), ({right}))"
        if node.op == "|":
            return f"bit32.bor(({left}), ({right}))"
        return f"(({left}) {node.op} ({right}))"
    if isinstance(node, Ternary):
        condition = _compile_lua_expr(node.condition)
        value_if_true = _compile_lua_expr(node.value_if_true)
        value_if_false = _compile_lua_expr(node.value_if_false)
        return f"(({condition}) and ({value_if_true}) or ({value_if_false}))"

    raise GeneratorError(f"Unsupported AST node {type(node)!r} in Lua expression generation.")


def _field_value_expr(spec_type: str, endian: str) -> str:
    if spec_type == "str":
        return "range:string()"
    if spec_type == "u1":
        return "range:uint()"
    if spec_type == "s1":
        return "range:int()"
    if spec_type in {"u2", "u4"}:
        return "range:le_uint()" if endian == "le" else "range:uint()"
    if spec_type == "u8":
        return "range:le_uint64()" if endian == "le" else "range:uint64()"
    if spec_type in {"s2", "s4"}:
        return "range:le_int()" if endian == "le" else "range:int()"
    if spec_type == "s8":
        return "range:le_int64()" if endian == "le" else "range:int64()"
    raise GeneratorError(f"Unsupported field type {spec_type!r} for Lua value extraction.")


def _uses_little_endian(spec_type: str, endian: str) -> bool:
    return endian == "le" and spec_type not in {"u1", "s1", "str"}


def _normalize_wireshark_instances(spec: Dict[str, Any], proto_id: str) -> list[dict[str, Any]]:
    instances = spec.get("instances") or {}
    if not isinstance(instances, dict):
        raise GeneratorError("'instances' must be a mapping when used by the Wireshark generator.")

    normalized: list[dict[str, Any]] = []
    for instance_id, instance_def in instances.items():
        if not isinstance(instance_def, dict):
            continue

        wireshark_def = instance_def.get("wireshark")
        if not isinstance(wireshark_def, dict):
            continue

        value_expr = instance_def.get("value")
        if not isinstance(value_expr, str):
            raise GeneratorError(
                f"Wireshark instance '{instance_id}' requires a string 'value' expression."
            )

        field_type = wireshark_def.get("type")
        if field_type not in {"bool", "string"}:
            raise GeneratorError(
                "Wireshark instance "
                f"'{instance_id}' must declare wireshark.type as 'bool' or 'string'."
            )

        filter_only = bool(wireshark_def.get("filter-only", False))
        if filter_only and field_type != "bool":
            raise GeneratorError(
                f"Wireshark instance '{instance_id}' uses filter-only but is not a bool field."
            )

        normalized.append(
            {
                "id": instance_id,
                "label": wireshark_def.get("label") or instance_id.replace("_", " ").title(),
                "lua_type": field_type,
                "filter_only": filter_only,
                "expr": _compile_lua_expr(parse_expr(value_expr)),
                "field_path": f"{proto_id}.{instance_id}",
            }
        )

    return normalized


class LuaGenerator(BaseGenerator):
    """Generates a Wireshark Lua dissector from a protocol specification."""

    def generate(self, spec: Dict[str, Any], output_dir: Path) -> List[Path]:
        """Generate a ``.lua`` dissector file into *output_dir*.

        Returns
        -------
        List[Path]
            Single-element list with the path of the written ``.lua`` file.
        """
        meta = spec.get("meta", {})
        proto_id: str = meta.get("id", "protocol")
        proto_title: str = meta.get("title", proto_id)
        endian: str = meta.get("endian", "le")

        seq = spec.get("seq") or []
        fields = []

        for raw in seq:
            field_id = raw.get("id")
            spec_type = raw.get("type")
            if not field_id or not spec_type:
                continue

            if spec_type not in _LUA_TYPE_MAP:
                raise GeneratorError(
                    f"Unsupported field type '{spec_type}' for field '{field_id}'. "
                    f"Supported types: {', '.join(sorted(_LUA_TYPE_MAP))}."
                )

            lua_type, size, lua_base = _LUA_TYPE_MAP[spec_type]

            if spec_type == "str":
                size = raw.get("size")
                if size is None:
                    raise GeneratorError(
                        f"Field '{field_id}' of type 'str' requires a 'size' attribute."
                    )

            fields.append(
                {
                    "id": field_id,
                    "spec_type": spec_type,
                    "label": field_id.replace("_", " ").title(),
                    "lua_type": lua_type,
                    "lua_base": lua_base,
                    "size": size,
                    "value_expr": _field_value_expr(spec_type, endian),
                    "use_add_le": _uses_little_endian(spec_type, endian),
                }
            )

        instance_fields = _normalize_wireshark_instances(spec, proto_id)
        all_fields = fields + instance_fields

        env = Environment(loader=FileSystemLoader(str(_TEMPLATES_DIR)), keep_trailing_newline=True)
        template = env.get_template("dissector.lua.j2")

        context = {
            "source_file": str(spec.get("_source_file", "<unknown>")),
            "proto_id": proto_id,
            "proto_title": proto_title,
            "proto_id_upper": proto_id.upper(),
            "fields": fields,
            "instance_fields": instance_fields,
            "fields_list": ", ".join(f"f_{f['id']}" for f in all_fields),
        }

        output_dir.mkdir(parents=True, exist_ok=True)
        out_path = output_dir / f"{proto_id}.lua"
        out_path.write_text(template.render(**context), encoding="utf-8")
        return [out_path]

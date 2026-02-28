"""Tests for the protocollab CLI (protocollab.main)."""

import json
import sys
import pytest
from unittest.mock import patch


def run_cli(*args) -> tuple[int, str, str]:
    """Run main() with the given CLI args. Returns (exit_code, stdout, stderr)."""
    from protocollab.main import main
    with patch("sys.argv", ["protocollab", *args]):
        with pytest.raises(SystemExit) as exc_info:
            main()
        exit_code = exc_info.value.code
    return exit_code


def run_cli_captured(*args, capsys) -> tuple[int, str, str]:
    """Run main() and capture stdout/stderr. Returns (exit_code, stdout, stderr)."""
    exit_code = run_cli(*args)
    captured = capsys.readouterr()
    return exit_code, captured.out, captured.err


# ---------------------------------------------------------------------------
# protocollab load — success paths
# ---------------------------------------------------------------------------

class TestCLILoadSuccess:
    def test_load_exits_zero(self, simple_yaml, capsys):
        code, out, _ = run_cli_captured("load", str(simple_yaml), capsys=capsys)
        assert code == 0

    def test_load_default_format_is_yaml(self, simple_yaml, capsys):
        code, out, _ = run_cli_captured("load", str(simple_yaml), capsys=capsys)
        assert code == 0
        assert "version" in out

    def test_load_json_format(self, simple_yaml, capsys):
        code, out, _ = run_cli_captured(
            "load", str(simple_yaml), "--output-format", "json", capsys=capsys
        )
        assert code == 0
        parsed = json.loads(out)
        assert parsed["version"] == "1.0"

    def test_load_yaml_format_explicit(self, simple_yaml, capsys):
        code, out, _ = run_cli_captured(
            "load", str(simple_yaml), "--output-format", "yaml", capsys=capsys
        )
        assert code == 0
        assert "version:" in out

    def test_load_no_cache_flag(self, simple_yaml, capsys):
        code, out, _ = run_cli_captured(
            "load", str(simple_yaml), "--no-cache", capsys=capsys
        )
        assert code == 0

    def test_load_with_include(self, yaml_with_include, capsys):
        code, out, _ = run_cli_captured("load", str(yaml_with_include), capsys=capsys)
        assert code == 0


# ---------------------------------------------------------------------------
# protocollab load — error paths
# ---------------------------------------------------------------------------

class TestCLILoadErrors:
    def test_missing_file_exits_one(self, capsys):
        code, _, err = run_cli_captured(
            "load", "/nonexistent/missing.yaml", capsys=capsys
        )
        assert code == 1
        assert "Error" in err or "error" in err.lower()

    def test_invalid_yaml_exits_two(self, invalid_yaml, capsys):
        code, _, err = run_cli_captured("load", str(invalid_yaml), capsys=capsys)
        assert code == 2

    def test_missing_file_message_on_stderr(self, capsys):
        run_cli_captured("load", "/no/such/file.yaml", capsys=capsys)
        _, _, err = run_cli_captured("load", "/no/such/file.yaml", capsys=capsys)
        assert len(err) > 0


# ---------------------------------------------------------------------------
# protocollab — top-level help
# ---------------------------------------------------------------------------

class TestCLIHelp:
    def test_help_exits_zero(self):
        with patch("sys.argv", ["protocollab", "--help"]):
            with pytest.raises(SystemExit) as exc_info:
                from protocollab.main import _build_parser
                _build_parser().parse_args(["--help"])
        assert exc_info.value.code == 0

    def test_load_subcommand_exists(self):
        from protocollab.main import _build_parser
        parser = _build_parser()
        # Must not raise for a known subcommand
        args = parser.parse_args(["load", "/tmp/any.yaml"])
        assert args.command == "load"

    def test_load_default_output_format(self):
        from protocollab.main import _build_parser
        parser = _build_parser()
        args = parser.parse_args(["load", "/tmp/any.yaml"])
        assert args.output_format == "yaml"

    def test_no_cache_flag_default_false(self):
        from protocollab.main import _build_parser
        parser = _build_parser()
        args = parser.parse_args(["load", "/tmp/any.yaml"])
        assert args.no_cache is False

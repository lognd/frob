"""Unit tests for frob.vet: lockfile parsers, allow conformance, quarantine,
typosquat, and hook-command parsing (docs/modules/vet.md). No real network calls."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from frob.vet._allow import load_vet_config
from frob.vet._hook import check_package, parse_hook_command
from frob.vet._lockfile import find_lockfile, parse_lockfile
from frob.vet._models import Dependency
from frob.vet._registry import RegistryResult
from frob.vet._typosquat import damerau_levenshtein, find_typosquat

# ---------------------------------------------------------------------------
# lockfile parsers
# ---------------------------------------------------------------------------

UV_LOCK = """\
version = 1
requires-python = ">=3.11"

[[package]]
name = "requests"
version = "2.31.0"
source = { registry = "https://pypi.org/simple" }

[[package]]
name = "idna"
version = "3.6"
source = { registry = "https://pypi.org/simple" }
"""

PACKAGE_LOCK_JSON_V3 = json.dumps(
    {
        "name": "app",
        "lockfileVersion": 3,
        "packages": {
            "": {"name": "app", "version": "1.0.0"},
            "node_modules/lodash": {"version": "4.17.21"},
            "node_modules/chalk": {"version": "5.3.0"},
        },
    }
)

PACKAGE_LOCK_JSON_V1 = json.dumps(
    {
        "name": "app",
        "lockfileVersion": 1,
        "dependencies": {
            "express": {"version": "4.18.2"},
        },
    }
)

PNPM_LOCK_YAML = """\
lockfileVersion: '6.0'

packages:
  /lodash@4.17.21:
    resolution: {integrity: sha512-xyz}
  /chalk@5.3.0:
    resolution: {integrity: sha512-abc}
"""

CARGO_LOCK = """\
version = 3

[[package]]
name = "serde"
version = "1.0.195"

[[package]]
name = "tokio"
version = "1.35.1"
"""


class TestLockfileParsers:
    def test_find_lockfile_uv(self, tmp_path: Path) -> None:
        (tmp_path / "uv.lock").write_text(UV_LOCK)
        assert find_lockfile(tmp_path) == tmp_path / "uv.lock"

    def test_find_lockfile_none(self, tmp_path: Path) -> None:
        assert find_lockfile(tmp_path) is None

    def test_parse_uv_lock(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_lockfile.py::parse_lockfile kind="unit"
        path = tmp_path / "uv.lock"
        path.write_text(UV_LOCK)
        result = parse_lockfile(path)
        assert result.is_ok
        deps = result.danger_ok
        assert Dependency(ecosystem="pypi", name="requests", version="2.31.0") in deps
        assert len(deps) == 2

    def test_parse_package_lock_json_v3(self, tmp_path: Path) -> None:
        path = tmp_path / "package-lock.json"
        path.write_text(PACKAGE_LOCK_JSON_V3)
        result = parse_lockfile(path)
        assert result.is_ok
        deps = result.danger_ok
        assert Dependency(ecosystem="npm", name="lodash", version="4.17.21") in deps
        assert Dependency(ecosystem="npm", name="chalk", version="5.3.0") in deps

    def test_parse_package_lock_json_v1(self, tmp_path: Path) -> None:
        path = tmp_path / "package-lock.json"
        path.write_text(PACKAGE_LOCK_JSON_V1)
        result = parse_lockfile(path)
        assert result.is_ok
        deps = result.danger_ok
        assert Dependency(ecosystem="npm", name="express", version="4.18.2") in deps

    def test_parse_pnpm_lock(self, tmp_path: Path) -> None:
        path = tmp_path / "pnpm-lock.yaml"
        path.write_text(PNPM_LOCK_YAML)
        result = parse_lockfile(path)
        assert result.is_ok
        deps = result.danger_ok
        assert Dependency(ecosystem="npm", name="lodash", version="4.17.21") in deps

    def test_parse_cargo_lock(self, tmp_path: Path) -> None:
        path = tmp_path / "Cargo.lock"
        path.write_text(CARGO_LOCK)
        result = parse_lockfile(path)
        assert result.is_ok
        deps = result.danger_ok
        assert Dependency(ecosystem="cargo", name="serde", version="1.0.195") in deps

    def test_unsupported_lockfile(self, tmp_path: Path) -> None:
        path = tmp_path / "yarn.lock"
        result = parse_lockfile(path)
        assert result.is_err

    def test_malformed_uv_lock(self, tmp_path: Path) -> None:
        path = tmp_path / "uv.lock"
        path.write_text("not valid = [ toml")
        result = parse_lockfile(path)
        assert result.is_err


# ---------------------------------------------------------------------------
# allow conformance / config loading
# ---------------------------------------------------------------------------


class TestAllowConfig:
    def test_no_frob_toml_is_advisory_only(self, tmp_path: Path) -> None:
        cfg = load_vet_config(tmp_path)
        assert cfg.present is False

    def test_no_vet_section_is_advisory_only(self, tmp_path: Path) -> None:
        (tmp_path / "frob.toml").write_text("check_base = 'main'\n")
        cfg = load_vet_config(tmp_path)
        assert cfg.present is False

    def test_vet_section_present(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_allow.py::load_vet_config kind="unit"
        (tmp_path / "frob.toml").write_text(
            """
[vet]
enforce = true
osv = false
quarantine_days = 7

[vet.allow]
requests = true
jinja2 = ["sandboxed template compilation, reviewed"]
"""
        )
        cfg = load_vet_config(tmp_path)
        assert cfg.present is True
        assert cfg.enforce is True
        assert cfg.quarantine_days == 7
        assert cfg.allow["requests"] is True
        assert cfg.allow["jinja2"] == ("sandboxed template compilation, reviewed",)


# ---------------------------------------------------------------------------
# quarantine logic (monkeypatched registry)
# ---------------------------------------------------------------------------


class TestQuarantine:
    def test_fresh_package_blocked(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/vet/_hook.py::check_package kind="unit"
        from frob.vet import _registry

        def fake_fetch(
            ecosystem, name, version, *, cache_path, base_url=None, timeout_s=5.0
        ):
            return RegistryResult(
                ok=True,
                published_at=datetime.now(UTC) - timedelta(days=2),
                resolved_version=version,
            )

        monkeypatch.setattr(_registry, "fetch_publish_date", fake_fetch)
        verdict = check_package("pypi", "some-new-pkg", "1.0.0", root=tmp_path)
        assert verdict.verdict == "quarantine"
        assert verdict.blocked is True

    def test_old_package_ok(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from frob.vet import _registry

        def fake_fetch(
            ecosystem, name, version, *, cache_path, base_url=None, timeout_s=5.0
        ):
            return RegistryResult(
                ok=True,
                published_at=datetime.now(UTC) - timedelta(days=900),
                resolved_version=version,
            )

        monkeypatch.setattr(_registry, "fetch_publish_date", fake_fetch)
        verdict = check_package("pypi", "requests", "2.31.0", root=tmp_path)
        assert verdict.verdict == "ok"
        assert verdict.blocked is False

    def test_network_failure_degrades_to_unverified(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from frob.vet import _registry

        def fake_fetch(
            ecosystem, name, version, *, cache_path, base_url=None, timeout_s=5.0
        ):
            return RegistryResult(
                ok=False, note="could not verify publish date: timeout"
            )

        monkeypatch.setattr(_registry, "fetch_publish_date", fake_fetch)
        verdict = check_package("pypi", "requests", "2.31.0", root=tmp_path)
        assert verdict.verdict == "unverified"
        assert verdict.blocked is False


# ---------------------------------------------------------------------------
# typosquat
# ---------------------------------------------------------------------------


class TestTyposquat:
    def test_damerau_levenshtein_basic(self) -> None:
        assert damerau_levenshtein("requests", "requests") == 0
        assert damerau_levenshtein("requets", "requests") == 1
        assert damerau_levenshtein("laodash", "lodash") == 1

    def test_requets_flags_requests(self) -> None:
        # frob:tests src/frob/vet/_typosquat.py::find_typosquat kind="unit"
        assert find_typosquat("pypi", "requets") == "requests"

    def test_laodash_flags_lodash(self) -> None:
        assert find_typosquat("npm", "laodash") == "lodash"

    def test_known_popular_package_not_flagged(self) -> None:
        assert find_typosquat("pypi", "requests") is None

    def test_unrelated_name_not_flagged(self) -> None:
        assert find_typosquat("pypi", "some-totally-unrelated-package-xyz") is None


# ---------------------------------------------------------------------------
# hook-command parsing table
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("command", "expected"),
    [
        ("uv add requests", ("pypi", (("requests", ""),))),
        ("uv add requests==2.31.0", ("pypi", (("requests", "2.31.0"),))),
        ("uv pip install requests", ("pypi", (("requests", ""),))),
        ("pip install requests==2.31.0", ("pypi", (("requests", "2.31.0"),))),
        ("pip3 install foo bar", ("pypi", (("foo", ""), ("bar", "")))),
        ("npm install lodash", ("npm", (("lodash", ""),))),
        ("npm i chalk@5.0.0", ("npm", (("chalk", "5.0.0"),))),
        ("pnpm add express", ("npm", (("express", ""),))),
        ("yarn add react react-dom", ("npm", (("react", ""), ("react-dom", "")))),
        (
            "npx some-plausible-nonexistent-name-2026",
            ("npm", (("some-plausible-nonexistent-name-2026", ""),)),
        ),
        ("cargo add serde@1.0", ("cargo", (("serde", "1.0"),))),
        ("cargo add serde", ("cargo", (("serde", ""),))),
        ("npm install --save-dev lodash", ("npm", (("lodash", ""),))),
        ("git status", None),
        ("ls -la", None),
        ("echo hello", None),
        ("", None),
    ],
)
def test_parse_hook_command(command: str, expected) -> None:
    assert parse_hook_command(command) == expected


def test_parse_hook_command_scoped_npm_package() -> None:
    result = parse_hook_command("npm install @babel/core@7.23.0")
    assert result == ("npm", (("@babel/core", "7.23.0"),))


# ---------------------------------------------------------------------------
# capability scan (T-0008)
# ---------------------------------------------------------------------------


class TestCapabilityScan:
    def test_python_exec_and_net_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.py"
        pkg.write_text(
            "import subprocess\nimport requests\nsubprocess.run(['ls'])\nrequests.get('x')\n"
        )
        capabilities = scan_file_capabilities(pkg)
        assert "exec" in capabilities
        assert "net" in capabilities

    def test_rust_exec_detected(self, tmp_path: Path) -> None:
        from frob.vet._capability import scan_file_capabilities

        build_rs = tmp_path / "build.rs"
        build_rs.write_text('fn main() { std::process::Command::new("sh"); }\n')
        capabilities = scan_file_capabilities(build_rs)
        assert "exec" in capabilities

    def test_no_pattern_table_for_c(self, tmp_path: Path) -> None:
        from frob.vet._capability import scan_file_capabilities

        c_file = tmp_path / "foo.c"
        c_file.write_text('int main() { system("ls"); return 0; }\n')
        assert scan_file_capabilities(c_file) == frozenset()

    def test_decode_to_exec_same_function(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::decode_to_exec_signal kind="unit"
        from frob.vet._capability import decode_to_exec_signal

        pkg = tmp_path / "pkg.py"
        pkg.write_text(
            "import base64\n"
            "def run(payload):\n"
            "    data = base64.b64decode(payload)\n"
            "    exec(data)\n"
        )
        assert decode_to_exec_signal(pkg) is True

    def test_decode_to_exec_absent_when_separate(self, tmp_path: Path) -> None:
        from frob.vet._capability import decode_to_exec_signal

        pkg = tmp_path / "pkg.py"
        pkg.write_text(
            "import base64\n"
            "def decode(payload):\n"
            "    return base64.b64decode(payload)\n"
            "def other():\n"
            "    return 1\n"
        )
        assert decode_to_exec_signal(pkg) is False

    def test_language_for_known_and_unknown_extensions(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::language_for kind="unit"
        from frob.vet._capability import language_for

        assert language_for(tmp_path / "mod.py") == "python"
        assert language_for(tmp_path / "mod.rs") == "rust"
        assert language_for(tmp_path / "mod.ts") == "typescript"
        assert language_for(tmp_path / "mod.c") is None

    def test_scan_directory_capabilities_aggregates_across_files(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_directory_capabilities kind="unit"
        from frob.vet._capability import scan_directory_capabilities

        (tmp_path / "a.py").write_text("import subprocess\nsubprocess.run(['ls'])\n")
        (tmp_path / "b.py").write_text("import requests\nrequests.get('x')\n")
        capabilities, decode_to_exec_hit = scan_directory_capabilities(tmp_path)
        assert "exec" in capabilities
        assert "net" in capabilities
        assert decode_to_exec_hit is False

    def test_re_compile_alone_does_not_report_eval(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # T-0151: bare `compile(` used to match `re.compile(`/`ast.compile(`
        # dotted calls, spuriously reporting "eval" for ordinary regex code.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.py"
        pkg.write_text(
            "import re\nimport ast\n"
            "_RE = re.compile(r'^x$')\n"
            "tree = ast.compile('1', '<s>', 'eval')\n"
        )
        assert "eval" not in scan_file_capabilities(pkg)

    def test_bare_compile_call_still_reports_eval(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # T-0151: the bare builtin `compile()` (not a dotted method access) is
        # a genuine eval-adjacent primitive and must still be caught.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.py"
        pkg.write_text("code = compile(source, '<s>', 'exec')\n")
        assert "eval" in scan_file_capabilities(pkg)

    def test_genuine_eval_still_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.py"
        pkg.write_text("eval(user_input)\n")
        assert "eval" in scan_file_capabilities(pkg)

    def test_capability_module_self_scan_documented_false_positive(self) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # T-0151: `_capability.py` stores every needle as literal string data,
        # so scanning IT directly (not via directory aggregation) still shows
        # the accepted false-positive class documented in the module
        # docstring and docs/modules/vet.md -- this locks that decision so a
        # future "fix" doesn't silently change the behavior either way.
        from frob.vet._capability import scan_file_capabilities

        own_path = (
            Path(__file__).resolve().parents[1]
            / "src"
            / "frob"
            / "vet"
            / "_capability.py"
        )
        capabilities = scan_file_capabilities(own_path)
        assert "install-hook" in capabilities  # "cmdclass" appears as data

    def test_scan_directory_capabilities_excludes_own_module(self) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_directory_capabilities kind="unit"
        # T-0151: directory aggregation over vet's REAL package path must not
        # self-inflate "eval"/"exec" from _capability.py's own pattern-table
        # literals (its needle tuples contain "eval(", "subprocess.", etc as
        # data, and nowhere ELSE in src/frob/vet does real eval/exec-ish code
        # exist -- direct grep confirms zero non-_capability.py hits for
        # eval(/exec(/__import__(/importlib.import_module(). "install-hook"
        # is deliberately NOT asserted absent here: _ecosystem.py's genuine
        # cmdclass-detection logic contains the literal substring "cmdclass"
        # as its own check target, which is the separate, documented,
        # accepted false-positive class from the module docstring and
        # docs/modules/vet.md -- not something this exclusion targets.
        from frob.vet._capability import scan_directory_capabilities

        vet_src = Path(__file__).resolve().parents[1] / "src" / "frob" / "vet"
        capabilities, _ = scan_directory_capabilities(vet_src)
        assert "eval" not in capabilities
        assert "exec" not in capabilities


class TestObfuscationEnsemble:
    def test_high_entropy_string_flagged(self) -> None:
        # frob:tests src/frob/vet/_obfuscation.py::scan_text_obfuscation kind="unit"
        from frob.vet._obfuscation import scan_text_obfuscation

        text = 'x = "aGVsbG8gd29ybGQsIHRoaXMgaXMgYSB0ZXN0IHBheWxvYWQ="\n'
        assert "high-entropy-string" in scan_text_obfuscation(text)

    def test_plain_string_not_flagged(self) -> None:
        from frob.vet._obfuscation import scan_text_obfuscation

        text = 'greeting = "hello world, this is a normal string literal"\n'
        assert "high-entropy-string" not in scan_text_obfuscation(text)

    def test_bidi_override_is_fatal(self) -> None:
        # frob:tests src/frob/vet/_obfuscation.py::invisible_text_signal kind="unit"
        from frob.vet._obfuscation import invisible_text_signal

        text = "x = 1" + chr(0x202E) + "y = 2"
        assert invisible_text_signal(text) is True

    def test_clean_text_no_bidi(self) -> None:
        from frob.vet._obfuscation import invisible_text_signal

        assert invisible_text_signal("x = 1\ny = 2\n") is False

    def test_hex_identifier_ratio_flagged(self) -> None:
        # frob:tests src/frob/vet/_obfuscation.py::hex_identifier_ratio_signal kind="unit"
        from frob.vet._obfuscation import hex_identifier_ratio_signal

        idents = " ".join(f"_0x{i:04x}" for i in range(30))
        assert hex_identifier_ratio_signal(idents) is True

    def test_normal_identifiers_not_flagged(self) -> None:
        from frob.vet._obfuscation import hex_identifier_ratio_signal

        idents = " ".join(f"variable_name_{i}" for i in range(30))
        assert hex_identifier_ratio_signal(idents) is False

    def test_high_entropy_strings_returns_the_literal(self) -> None:
        # frob:tests src/frob/vet/_obfuscation.py::high_entropy_strings kind="unit"
        from frob.vet._obfuscation import high_entropy_strings

        text = 'x = "aGVsbG8gd29ybGQsIHRoaXMgaXMgYSB0ZXN0IHBheWxvYWQ="\n'
        hits = high_entropy_strings(text)
        assert len(hits) == 1
        assert hits[0].startswith("aGVsbG8")

    def test_high_entropy_strings_empty_for_plain_text(self) -> None:
        from frob.vet._obfuscation import high_entropy_strings

        text = 'greeting = "hello world, this is a normal string literal"\n'
        assert high_entropy_strings(text) == ()

    def test_scan_directory_obfuscation_finds_signal_in_one_file(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_obfuscation.py::scan_directory_obfuscation kind="unit"
        from frob.vet._obfuscation import scan_directory_obfuscation

        (tmp_path / "clean.py").write_text("x = 1\n")
        (tmp_path / "evil.py").write_text(
            'x = "aGVsbG8gd29ybGQsIHRoaXMgaXMgYSB0ZXN0IHBheWxvYWQ="\n'
        )
        signals = scan_directory_obfuscation(tmp_path)
        assert "high-entropy-string" in signals


class TestVerdictCache:
    def test_store_and_retrieve_latest(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_cache.py::store_verdict kind="unit"
        # frob:tests src/frob/vet/_cache.py::latest_verdict kind="unit"
        from frob.vet import _cache
        from frob.vet._models import PackageVerdict

        db_path = tmp_path / ".frob" / "vet.db"
        v1 = PackageVerdict(
            name="foo",
            version="1.0.0",
            ecosystem="pypi",
            artifact_hash="hash1",
            capabilities=frozenset({"net"}),
        )
        _cache.store_verdict(db_path, v1)
        latest = _cache.latest_verdict(db_path, "pypi", "foo")
        assert latest is not None
        assert latest.artifact_hash == "hash1"
        assert latest.capabilities == frozenset({"net"})

    def test_missing_cache_returns_none(self, tmp_path: Path) -> None:
        from frob.vet import _cache

        assert (
            _cache.latest_verdict(tmp_path / ".frob" / "vet.db", "pypi", "nope") is None
        )


class TestCapabilityDiff:
    def test_added_capability_detected(self) -> None:
        # frob:tests src/frob/vet/_models.py::capability_diff kind="unit"
        from frob.vet._models import PackageVerdict, capability_diff

        prev = PackageVerdict(
            name="foo",
            version="1.0.0",
            ecosystem="pypi",
            capabilities=frozenset({"net"}),
        )
        cur = PackageVerdict(
            name="foo",
            version="1.1.0",
            ecosystem="pypi",
            capabilities=frozenset({"net", "exec"}),
        )
        assert capability_diff(prev, cur) == ("exec",)

    def test_no_diff_when_unchanged(self) -> None:
        from frob.vet._models import PackageVerdict, capability_diff

        prev = PackageVerdict(
            name="foo",
            version="1.0.0",
            ecosystem="pypi",
            capabilities=frozenset({"net"}),
        )
        cur = PackageVerdict(
            name="foo",
            version="1.1.0",
            ecosystem="pypi",
            capabilities=frozenset({"net"}),
        )
        assert capability_diff(prev, cur) == ()


class TestEcosystemRules:
    # frob:waive PERF003 reason="a set comprehension plus a sibling any() generator with == on rule name, not a nested join"
    def test_python_setup_py_cmdclass_flagged(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_ecosystem.py::python_rules kind="unit"
        from frob.gates._models import Severity
        from frob.vet import _ecosystem

        (tmp_path / "setup.py").write_text(
            "from setuptools import setup\nsetup(cmdclass={'install': Foo})\n"
        )
        dep = Dependency(ecosystem="pypi", name="evilpkg", version="1.0.0")
        violations = _ecosystem.python_rules(dep, tmp_path, "uv.lock")
        rules = {v.rule for v in violations}
        assert "VET-PY001" in rules
        assert any(
            v.severity is Severity.ERROR for v in violations if v.rule == "VET-PY001"
        )

    def test_python_pth_file_flagged(self, tmp_path: Path) -> None:
        from frob.vet import _ecosystem

        (tmp_path / "evil.pth").write_text("import os; os.system('echo hi')\n")
        dep = Dependency(ecosystem="pypi", name="evilpkg", version="1.0.0")
        violations = _ecosystem.python_rules(dep, tmp_path, "uv.lock")
        assert any(v.rule == "VET-PY002" for v in violations)

    def test_rust_build_rs_capability_flagged(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_ecosystem.py::rust_rules kind="unit"
        from frob.vet import _ecosystem

        (tmp_path / "build.rs").write_text(
            'fn main() { std::process::Command::new("curl"); }\n'
        )
        dep = Dependency(ecosystem="cargo", name="evilcrate", version="1.0.0")
        violations = _ecosystem.rust_rules(dep, tmp_path, "Cargo.lock")
        assert any(v.rule == "VET-RS001" for v in violations)

    def test_npm_non_registry_source_flagged(self) -> None:
        # frob:tests src/frob/vet/_ecosystem.py::npm_non_registry_rule kind="unit"
        from frob.vet import _ecosystem

        dep = Dependency(
            ecosystem="npm",
            name="evilpkg",
            version="1.0.0",
            resolved="git+https://example.com/evil/evilpkg.git",
        )
        violation = _ecosystem.npm_non_registry_rule(dep, "package-lock.json")
        assert violation is not None
        assert violation.rule == "VET-JS004"

    def test_npm_registry_source_not_flagged(self) -> None:
        from frob.vet import _ecosystem

        dep = Dependency(
            ecosystem="npm",
            name="lodash",
            version="4.17.21",
            resolved="https://registry.npmjs.org/lodash/-/lodash-4.17.21.tgz",
        )
        violation = _ecosystem.npm_non_registry_rule(dep, "package-lock.json")
        assert violation is None


class TestScanTreeWithLocalSource:
    def test_scan_tree_detects_capabilities_from_node_modules(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """End-to-end: a lockfile dep whose node_modules source uses net/exec
        surfaces those capabilities in the report's verdict."""
        from frob.vet._scan import scan_tree

        (tmp_path / "package-lock.json").write_text(
            json.dumps(
                {
                    "name": "app",
                    "lockfileVersion": 3,
                    "packages": {
                        "": {"name": "app", "version": "1.0.0"},
                        "node_modules/sketchy-pkg": {"version": "1.0.0"},
                    },
                }
            )
        )
        pkg_dir = tmp_path / "node_modules" / "sketchy-pkg"
        pkg_dir.mkdir(parents=True)
        (pkg_dir / "index.js").write_text(
            "const cp = require('child_process');\ncp.execSync('ls');\n"
        )
        (tmp_path / "frob.toml").write_text(
            "[vet]\nenforce = true\n\n[vet.allow]\nsketchy-pkg = true\n"
        )

        result = scan_tree(tmp_path, fetch=False)
        assert result.is_ok
        report = result.danger_ok
        verdict = next(v for v in report.verdicts if v.name == "sketchy-pkg")
        assert "exec" in verdict.capabilities

    def test_scan_tree_flags_undeclared_capability(self, tmp_path: Path) -> None:
        """VET002: a declared capability list narrower than what's observed fires."""
        from frob.vet._scan import scan_tree

        (tmp_path / "package-lock.json").write_text(
            json.dumps(
                {
                    "name": "app",
                    "lockfileVersion": 3,
                    "packages": {
                        "": {"name": "app", "version": "1.0.0"},
                        "node_modules/sketchy-pkg": {"version": "1.0.0"},
                    },
                }
            )
        )
        pkg_dir = tmp_path / "node_modules" / "sketchy-pkg"
        pkg_dir.mkdir(parents=True)
        (pkg_dir / "index.js").write_text(
            "const cp = require('child_process');\ncp.execSync('ls');\n"
        )
        (tmp_path / "frob.toml").write_text(
            '[vet]\nenforce = true\n\n[vet.allow]\nsketchy-pkg = ["net"]\n'
        )

        result = scan_tree(tmp_path, fetch=False)
        assert result.is_ok
        report = result.danger_ok
        assert any(v.rule == "VET002" for v in report.violations)


# ---------------------------------------------------------------------------
# lifecycle scripts
# ---------------------------------------------------------------------------


class TestLifecycleScripts:
    def test_finds_postinstall_script(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_lifecycle.py::scan_lifecycle_scripts kind="unit"
        from frob.vet._lifecycle import scan_lifecycle_scripts

        pkg_dir = tmp_path / "node_modules" / "sketchy-pkg"
        pkg_dir.mkdir(parents=True)
        (pkg_dir / "package.json").write_text(
            json.dumps(
                {
                    "name": "sketchy-pkg",
                    "scripts": {"postinstall": "node evil.js"},
                }
            )
        )
        found = scan_lifecycle_scripts(tmp_path)
        assert found == {"sketchy-pkg": ("postinstall",)}

    def test_no_node_modules_returns_empty(self, tmp_path: Path) -> None:
        from frob.vet._lifecycle import scan_lifecycle_scripts

        assert scan_lifecycle_scripts(tmp_path) == {}


# ---------------------------------------------------------------------------
# osv-scanner adapter
# ---------------------------------------------------------------------------


class TestOsvAdapter:
    def test_is_available_reflects_path_lookup(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/vet/_osv.py::is_available kind="unit"
        from frob.vet import _osv

        monkeypatch.setattr(
            _osv.shutil, "which", lambda _binary: "/usr/bin/osv-scanner"
        )
        assert _osv.is_available() is True

        monkeypatch.setattr(_osv.shutil, "which", lambda _binary: None)
        assert _osv.is_available() is False

    def test_run_osv_scan_none_when_binary_absent(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/vet/_osv.py::run_osv_scan kind="unit"
        from frob.vet import _osv

        monkeypatch.setattr(_osv.shutil, "which", lambda _binary: None)
        lockfile = tmp_path / "uv.lock"
        lockfile.write_text("version = 1\n")
        assert _osv.run_osv_scan(lockfile) is None


# ---------------------------------------------------------------------------
# registry publish-date lookups
# ---------------------------------------------------------------------------


class TestRegistryLookup:
    def test_fetch_publish_date_degrades_on_network_failure(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_registry.py::fetch_publish_date kind="unit"
        from frob.vet._registry import fetch_publish_date

        result = fetch_publish_date(
            "pypi",
            "some-package-that-should-not-resolve",
            "1.0.0",
            cache_path=tmp_path / "vet.db",
            base_url="http://127.0.0.1:1",
            timeout_s=0.5,
        )
        assert result.ok is False
        assert result.published_at is None


# ---------------------------------------------------------------------------
# local-cache source location
# ---------------------------------------------------------------------------


class TestSourceLocation:
    def test_locate_pypi_source_from_venv(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_source.py::locate_pypi_source kind="unit"
        from frob.vet._source import locate_pypi_source

        site_packages = tmp_path / ".venv" / "lib" / "python3.11" / "site-packages"
        pkg_dir = site_packages / "some_pkg"
        pkg_dir.mkdir(parents=True)
        found = locate_pypi_source(tmp_path, "some-pkg", "1.0.0")
        assert found == pkg_dir

    def test_locate_pypi_source_missing_returns_none(self, tmp_path: Path) -> None:
        from frob.vet._source import locate_pypi_source

        assert locate_pypi_source(tmp_path, "totally-absent-pkg", "1.0.0") is None

    def test_locate_npm_source_from_node_modules(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_source.py::locate_npm_source kind="unit"
        from frob.vet._source import locate_npm_source

        pkg_dir = tmp_path / "node_modules" / "lodash"
        pkg_dir.mkdir(parents=True)
        assert locate_npm_source(tmp_path, "lodash") == pkg_dir

    def test_locate_npm_source_missing_returns_none(self, tmp_path: Path) -> None:
        from frob.vet._source import locate_npm_source

        assert locate_npm_source(tmp_path, "not-installed") is None

    def test_locate_cargo_source_missing_registry_returns_none(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/vet/_source.py::locate_cargo_source kind="unit"
        from frob.vet._source import locate_cargo_source

        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        assert locate_cargo_source("serde", "1.0.195") is None

    def test_locate_source_dispatches_by_ecosystem(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_source.py::locate_source kind="unit"
        from frob.vet._source import locate_source

        pkg_dir = tmp_path / "node_modules" / "lodash"
        pkg_dir.mkdir(parents=True)
        assert locate_source(tmp_path, "npm", "lodash", "4.17.21") == pkg_dir
        assert locate_source(tmp_path, "unknown-ecosystem", "x", "1.0.0") is None

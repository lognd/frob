"""Unit tests for frob.vet: lockfile parsers, allow conformance, quarantine,
typosquat, and hook-command parsing (docs/modules/vet.md). No real network calls."""

from __future__ import annotations

import json
import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from frob.vet._allow import _load_vet_config
from frob.vet._hook import check_package, parse_hook_command
from frob.vet._lockfile import _find_lockfile, _parse_lockfile
from frob.vet._models import Dependency
from frob.vet._registry import _RegistryResult
from frob.vet._typosquat import _damerau_levenshtein, _find_typosquat

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
        assert _find_lockfile(tmp_path) == tmp_path / "uv.lock"

    def test_find_lockfile_none(self, tmp_path: Path) -> None:
        assert _find_lockfile(tmp_path) is None

    def test_find_lockfile_direct(self, tmp_path: Path) -> None:
        """T-0221: `frob vet uv.lock` passes the lockfile itself as `root`;
        it must resolve directly, not be misread as a directory to search
        under (which would look for uv.lock/uv.lock)."""
        lockfile = tmp_path / "uv.lock"
        lockfile.write_text(UV_LOCK)
        assert _find_lockfile(lockfile) == lockfile

    def test_find_lockfile_bad_name(self, tmp_path: Path) -> None:
        """A file path that isn't one of the supported lockfile names is not
        silently accepted just because it exists."""
        path = tmp_path / "yarn.lock"
        path.write_text("{}")
        assert _find_lockfile(path) is None

    def test_parse_uv_lock(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_lockfile.py::_parse_lockfile kind="unit"
        path = tmp_path / "uv.lock"
        path.write_text(UV_LOCK)
        result = _parse_lockfile(path)
        assert result.is_ok
        deps = result.danger_ok
        assert Dependency(ecosystem="pypi", name="requests", version="2.31.0") in deps
        assert len(deps) == 2

    def test_parse_package_lock_json_v3(self, tmp_path: Path) -> None:
        path = tmp_path / "package-lock.json"
        path.write_text(PACKAGE_LOCK_JSON_V3)
        result = _parse_lockfile(path)
        assert result.is_ok
        deps = result.danger_ok
        assert Dependency(ecosystem="npm", name="lodash", version="4.17.21") in deps
        assert Dependency(ecosystem="npm", name="chalk", version="5.3.0") in deps

    def test_parse_package_lock_json_v1(self, tmp_path: Path) -> None:
        path = tmp_path / "package-lock.json"
        path.write_text(PACKAGE_LOCK_JSON_V1)
        result = _parse_lockfile(path)
        assert result.is_ok
        deps = result.danger_ok
        assert Dependency(ecosystem="npm", name="express", version="4.18.2") in deps

    def test_parse_pnpm_lock(self, tmp_path: Path) -> None:
        path = tmp_path / "pnpm-lock.yaml"
        path.write_text(PNPM_LOCK_YAML)
        result = _parse_lockfile(path)
        assert result.is_ok
        deps = result.danger_ok
        assert Dependency(ecosystem="npm", name="lodash", version="4.17.21") in deps

    def test_parse_cargo_lock(self, tmp_path: Path) -> None:
        path = tmp_path / "Cargo.lock"
        path.write_text(CARGO_LOCK)
        result = _parse_lockfile(path)
        assert result.is_ok
        deps = result.danger_ok
        assert Dependency(ecosystem="cargo", name="serde", version="1.0.195") in deps

    def test_unsupported_lockfile(self, tmp_path: Path) -> None:
        path = tmp_path / "yarn.lock"
        result = _parse_lockfile(path)
        assert result.is_err

    def test_malformed_uv_lock(self, tmp_path: Path) -> None:
        path = tmp_path / "uv.lock"
        path.write_text("not valid = [ toml")
        result = _parse_lockfile(path)
        assert result.is_err

    def test_find_all_lockfiles_polyglot_repo(self, tmp_path: Path) -> None:
        # T-0400 audit finding #2: a repo with BOTH a uv.lock and a
        # package-lock.json must have both discovered -- the old
        # `_find_lockfile` returning only the first left every npm
        # dependency completely unscanned.
        # frob:tests src/frob/vet/_lockfile.py::_find_all_lockfiles kind="unit"
        from frob.vet._lockfile import _find_all_lockfiles

        (tmp_path / "uv.lock").write_text(UV_LOCK)
        (tmp_path / "package-lock.json").write_text(PACKAGE_LOCK_JSON_V3)
        found = _find_all_lockfiles(tmp_path)
        assert found == (tmp_path / "uv.lock", tmp_path / "package-lock.json")

    def test_find_all_lockfiles_single(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_lockfile.py::_find_all_lockfiles kind="unit"
        from frob.vet._lockfile import _find_all_lockfiles

        (tmp_path / "uv.lock").write_text(UV_LOCK)
        assert _find_all_lockfiles(tmp_path) == (tmp_path / "uv.lock",)

    def test_find_all_lockfiles_none(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_lockfile.py::_find_all_lockfiles kind="unit"
        from frob.vet._lockfile import _find_all_lockfiles

        assert _find_all_lockfiles(tmp_path) == ()

    def test_find_all_lockfiles_direct_path(self, tmp_path: Path) -> None:
        # T-0221 parity: a direct lockfile path resolves to a 1-tuple of
        # itself, not a directory search.
        # frob:tests src/frob/vet/_lockfile.py::_find_all_lockfiles kind="unit"
        from frob.vet._lockfile import _find_all_lockfiles

        lockfile = tmp_path / "uv.lock"
        lockfile.write_text(UV_LOCK)
        assert _find_all_lockfiles(lockfile) == (lockfile,)


# ---------------------------------------------------------------------------
# allow conformance / config loading
# ---------------------------------------------------------------------------


class TestAllowConfig:
    def test_no_frob_toml_is_advisory_only(self, tmp_path: Path) -> None:
        cfg = _load_vet_config(tmp_path)
        assert cfg.present is False

    def test_no_vet_section_is_advisory_only(self, tmp_path: Path) -> None:
        (tmp_path / "frob.toml").write_text("check_base = 'main'\n")
        cfg = _load_vet_config(tmp_path)
        assert cfg.present is False

    def test_vet_section_present(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_allow.py::_load_vet_config kind="unit"
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
        cfg = _load_vet_config(tmp_path)
        assert cfg.present is True
        assert cfg.enforce is True
        assert cfg.quarantine_days == 7
        assert cfg.allow["requests"] is True
        assert cfg.allow["jinja2"] == ("sandboxed template compilation, reviewed",)

    def test_wrong_typed_scalars_fall_back_to_defaults(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_allow.py::_load_vet_config kind="unit"
        # A malformed `[vet]` scalar (wrong TOML type) must degrade to the
        # field default, never crash the whole `frob` invocation.
        (tmp_path / "frob.toml").write_text(
            """
[vet]
quarantine_days = ["not", "an", "int"]
registry_base_url = 42
"""
        )
        cfg = _load_vet_config(tmp_path)
        assert cfg.present is True
        assert cfg.quarantine_days == 14
        assert cfg.registry_base_url is None


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
            return _RegistryResult(
                ok=True,
                published_at=datetime.now(UTC) - timedelta(days=2),
                resolved_version=version,
            )

        monkeypatch.setattr(_registry, "_fetch_publish_date", fake_fetch)
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
            return _RegistryResult(
                ok=True,
                published_at=datetime.now(UTC) - timedelta(days=900),
                resolved_version=version,
            )

        monkeypatch.setattr(_registry, "_fetch_publish_date", fake_fetch)
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
            return _RegistryResult(
                ok=False, note="could not verify publish date: timeout"
            )

        monkeypatch.setattr(_registry, "_fetch_publish_date", fake_fetch)
        verdict = check_package("pypi", "requests", "2.31.0", root=tmp_path)
        assert verdict.verdict == "unverified"
        assert verdict.blocked is False


# ---------------------------------------------------------------------------
# typosquat
# ---------------------------------------------------------------------------


class TestTyposquat:
    def test_damerau_levenshtein_basic(self) -> None:
        assert _damerau_levenshtein("requests", "requests") == 0
        assert _damerau_levenshtein("requets", "requests") == 1
        assert _damerau_levenshtein("laodash", "lodash") == 1

    def test_requets_flags_requests(self) -> None:
        # frob:tests src/frob/vet/_typosquat.py::_find_typosquat kind="unit"
        assert _find_typosquat("pypi", "requets") == "requests"

    def test_laodash_flags_lodash(self) -> None:
        assert _find_typosquat("npm", "laodash") == "lodash"

    def test_known_popular_package_not_flagged(self) -> None:
        assert _find_typosquat("pypi", "requests") is None

    def test_unrelated_name_not_flagged(self) -> None:
        assert _find_typosquat("pypi", "some-totally-unrelated-package-xyz") is None


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


def _make_fake_frob_repo_root(dest: Path) -> Path:
    """Build a `dest` directory that `_is_frob_repo_root` (T-0253) recognizes
    as frob's own checkout: `pyproject.toml` declaring `name = "frob"`, plus
    the `frob-core`/`strata-core` marker directories, plus a copy of the
    real `src/frob` tree underneath. `is_self_pattern_path`'s scan-target
    discriminator checks the exact directory passed as the scan root (no
    upward ancestor search -- see that function's docstring for why:
    ascending from a dependency located under frob's own `.venv` during
    frob vetting its OWN dependencies would otherwise wrongly classify that
    dependency's tree as "self" too), so tests exercising the discriminator
    must pass THIS directory itself as the scan root, not a subdirectory of
    it."""
    dest.mkdir(parents=True)
    repo_root = Path(__file__).resolve().parents[1]
    (dest / "pyproject.toml").write_text('[project]\nname = "frob"\n')
    (dest / "frob-core").mkdir()
    (dest / "strata-core").mkdir()
    shutil.copytree(
        repo_root / "src" / "frob",
        dest / "src" / "frob",
        ignore=shutil.ignore_patterns("__pycache__"),
    )
    return dest


class TestCapabilityScan:
    def test_scan_file_operations_names_registry_entry(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::_scan_file_operations kind="unit"
        from frob.vet._capability import _scan_file_operations

        pkg = tmp_path / "pkg.py"
        pkg.write_text("import subprocess\nsubprocess.run(['ls'])\n")
        ops = _scan_file_operations(pkg)
        assert any(op.capability_kind == "exec" for op in ops)
        matched = next(op for op in ops if op.capability_kind == "exec")
        assert matched.library == "subprocess"
        assert matched.safer_alternative

    def test_scan_file_operations_no_language(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::_scan_file_operations kind="unit"
        from frob.vet._capability import _scan_file_operations

        assert _scan_file_operations(tmp_path / "foo.unknownext") == ()

    def test_scan_file_operations_bare_compile(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::_scan_file_operations kind="unit"
        from frob.vet._capability import _scan_file_operations

        pkg = tmp_path / "pkg.py"
        pkg.write_text("code = compile(source, '<s>', 'exec')\n")
        ops = _scan_file_operations(pkg)
        assert any(op.function_or_pattern.startswith("compile(") for op in ops)

    def test_scan_file_operations_dotted_compile_not_matched(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability.py::_scan_file_operations kind="unit"
        from frob.vet._capability import _scan_file_operations

        pkg = tmp_path / "pkg.py"
        pkg.write_text("import re\n_RE = re.compile(r'^x$')\n")
        ops = _scan_file_operations(pkg)
        assert not any(op.function_or_pattern.startswith("compile(") for op in ops)

    def test_scan_file_operations_unreadable_file(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::_scan_file_operations kind="unit"
        from frob.vet._capability import _scan_file_operations

        missing = tmp_path / "gone.py"
        assert _scan_file_operations(missing) == ()

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

    # frob:waive DUP001 reason="parallel vet-rule case table: independent \
    # cases sharing an arrange-act scaffold typical of exhaustive per-rule \
    # coverage; extracting would obscure per-case intent"
    def test_kotlin_net_okhttp_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # T-0170: OkHttp is the dominant Android HTTP client -- one of the
        # per-cell fire fixtures for the new kotlin column.
        from frob.vet._capability import scan_file_capabilities

        kt = tmp_path / "Client.kt"
        kt.write_text(
            "import okhttp3.OkHttpClient\nfun makeClient() = OkHttpClient()\n"
        )
        assert "net" in scan_file_capabilities(kt)

    def test_kotlin_exec_runtime_exec_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        from frob.vet._capability import scan_file_capabilities

        kt = tmp_path / "Shell.kt"
        kt.write_text("fun run(cmd: String) {\n    Runtime.getRuntime().exec(cmd)\n}\n")
        assert "exec" in scan_file_capabilities(kt)

    # frob:waive DUP001 reason="parallel vet-rule case table: independent \
    # cases sharing an arrange-act scaffold typical of exhaustive per-rule \
    # coverage; extracting would obscure per-case intent"
    def test_kotlin_client_storage_shared_preferences_detected(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        from frob.vet._capability import scan_file_capabilities

        kt = tmp_path / "Prefs.kt"
        kt.write_text(
            "fun load(ctx: Context) {\n"
            '    val prefs = ctx.getSharedPreferences("app", 0)\n'
            "}\n"
        )
        assert "client_storage" in scan_file_capabilities(kt)

    def test_kotlin_benign_file_has_no_capabilities(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # T-0170: a kotlin file that touches none of the patterned needles
        # observes an empty capability set -- confirms the column does not
        # over-fire on ordinary Kotlin code.
        from frob.vet._capability import scan_file_capabilities

        kt = tmp_path / "Math.kt"
        kt.write_text("fun add(a: Int, b: Int): Int = a + b\n")
        assert scan_file_capabilities(kt) == frozenset()

    def test_c_source_exec_detected(self, tmp_path: Path) -> None:
        # T-0158: C/C++ is now a first-class scanned language (the old
        # blanket "honestly-empty" exemption is retired) -- system() is a
        # patterned c-cpp/exec _DangerousOperation.
        from frob.vet._capability import scan_file_capabilities

        c_file = tmp_path / "foo.c"
        c_file.write_text('int main() { system("ls"); return 0; }\n')
        assert "exec" in scan_file_capabilities(c_file)

    def test_c_source_fs_write_detected(self, tmp_path: Path) -> None:
        # T-0400 audit finding #4: fopen/fwrite is the actual fs-write
        # surface -- the pre-existing strcpy-family entry is a memory-safety
        # bucket, not a real file write, so this used to scan as zero
        # capabilities.
        from frob.vet._capability import scan_file_capabilities

        c_file = tmp_path / "foo.c"
        c_file.write_text(
            "void f(const char *path) {\n"
            '    FILE *fp = fopen(path, "w");\n'
            '    fwrite("x", 1, 1, fp);\n'
            "}\n"
        )
        assert "fs-write" in scan_file_capabilities(c_file)

    def test_c_source_raw_fd_read_detected(self, tmp_path: Path) -> None:
        # T-0400 audit finding #4: open()/read() are the actual POSIX read
        # syscalls; only the buffered fread/fgets wrappers were patterned.
        from frob.vet._capability import scan_file_capabilities

        c_file = tmp_path / "foo.c"
        c_file.write_text(
            "void f(const char *path) {\n"
            "    int fd = open(path, 0);\n"
            "    char buf[16];\n"
            "    read(fd, buf, sizeof(buf));\n"
            "}\n"
        )
        assert "fs-read" in scan_file_capabilities(c_file)

    def test_c_source_windows_exec_detected(self, tmp_path: Path) -> None:
        # T-0400 audit finding #4: the exec table was POSIX-only; a
        # Windows-targeted dependency can launch a process via the Win32
        # API entirely, evading every prior needle.
        from frob.vet._capability import scan_file_capabilities

        c_file = tmp_path / "foo.c"
        c_file.write_text(
            "void f(const char *cmd) {\n"
            '    ShellExecuteA(NULL, "open", cmd, NULL, NULL, 1);\n'
            "}\n"
        )
        assert "exec" in scan_file_capabilities(c_file)

    def test_c_source_net_recv_detected(self, tmp_path: Path) -> None:
        # T-0400 audit finding #4: send/recv/getaddrinfo were entirely
        # absent from the net table.
        from frob.vet._capability import scan_file_capabilities

        c_file = tmp_path / "foo.c"
        c_file.write_text(
            "void f(int fd) {\n"
            "    char buf[16];\n"
            "    recv(fd, buf, sizeof(buf), 0);\n"
            "}\n"
        )
        assert "net" in scan_file_capabilities(c_file)

    def test_decode_to_exec_same_function(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::_decode_to_exec_signal kind="unit"
        from frob.vet._capability import _decode_to_exec_signal

        pkg = tmp_path / "pkg.py"
        pkg.write_text(
            "import base64\n"
            "def run(payload):\n"
            "    data = base64.b64decode(payload)\n"
            "    exec(data)\n"
        )
        assert _decode_to_exec_signal(pkg) is True

    def test_decode_to_exec_absent_when_separate(self, tmp_path: Path) -> None:
        from frob.vet._capability import _decode_to_exec_signal

        pkg = tmp_path / "pkg.py"
        pkg.write_text(
            "import base64\n"
            "def decode(payload):\n"
            "    return base64.b64decode(payload)\n"
            "def other():\n"
            "    return 1\n"
        )
        assert _decode_to_exec_signal(pkg) is False

    def test_language_for_known_and_unknown_extensions(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::language_for kind="unit"
        from frob.vet._capability import language_for

        assert language_for(tmp_path / "mod.py") == "python"
        assert language_for(tmp_path / "mod.rs") == "rust"
        assert language_for(tmp_path / "mod.ts") == "typescript"
        # T-0158: C/C++ is now a first-class "c-cpp" bucket, not None.
        assert language_for(tmp_path / "mod.c") == "c-cpp"
        # T-0170: .kt/.kts extension mapping for the new kotlin column.
        assert language_for(tmp_path / "mod.kt") == "kotlin"
        assert language_for(tmp_path / "mod.kts") == "kotlin"
        assert language_for(tmp_path / "mod.unknownext") is None

    def test_scan_directory_capabilities_aggregates_across_files(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability.py::_scan_directory_capabilities kind="unit"
        from frob.vet._capability import _scan_directory_capabilities

        (tmp_path / "a.py").write_text("import subprocess\nsubprocess.run(['ls'])\n")
        (tmp_path / "b.py").write_text("import requests\nrequests.get('x')\n")
        capabilities, decode_to_exec_hit = _scan_directory_capabilities(tmp_path)
        assert "exec" in capabilities
        assert "net" in capabilities
        assert decode_to_exec_hit is False

    # frob:waive DUP001 reason="parallel vet-rule case table: independent \
    # cases sharing an arrange-act scaffold typical of exhaustive per-rule \
    # coverage; extracting would obscure per-case intent"
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

    # frob:waive DUP001 reason="parallel vet-rule case table: independent \
    # cases sharing an arrange-act scaffold typical of exhaustive per-rule \
    # coverage; extracting would obscure per-case intent"
    def test_comment_only_needle_does_not_fire(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # T-0209: pilot P2 -- a needle appearing only inside a `#` comment
        # describing forbidden network calls must not be reported as an
        # observation. The file's actual code never calls requests.get.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "starter.py"
        pkg.write_text(
            "# starter.py\n"
            "# Do not use requests.get() for real network calls here.\n"
            "def main():\n"
            "    pass\n"
        )
        assert "net" not in scan_file_capabilities(pkg)

    # frob:waive DUP001 reason="parallel vet-rule case table: independent \
    # cases sharing an arrange-act scaffold typical of exhaustive per-rule \
    # coverage; extracting would obscure per-case intent"
    def test_real_code_needle_still_fires_alongside_comment(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # T-0209: the comment-exclusion filter must not mask a genuine
        # needle hit elsewhere in real code, even when the same needle also
        # appears in a comment in the same file.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "real.py"
        pkg.write_text(
            "# calls requests.get under the hood\n"
            "import requests\n"
            "requests.get('http://example.com')\n"
        )
        assert "net" in scan_file_capabilities(pkg)

    def test_string_literal_needle_still_fires(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # T-0209: only COMMENT spans are filtered -- a needle inside a string
        # literal (not a comment) is deliberately left unfiltered (module
        # docstring's T-0209 note: distinguishing exec-vector strings from
        # prose strings needs per-registry judgment this scanner lacks).
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "stringy.py"
        pkg.write_text("cmd = 'requests.get(\"http://x\")'\n")
        assert "net" in scan_file_capabilities(pkg)

    def test_capability_module_self_scan_documented_false_positive(self) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # T-0151: `_capability.py` stores every needle as literal string data,
        # so scanning IT directly (not via directory aggregation) still shows
        # the accepted false-positive class documented in the module
        # docstring and docs/modules/vet.md -- this locks that decision so a
        # future "fix" doesn't silently change the behavior either way.
        #
        # T-0769: the ORIGINAL "cmdclass"/"install-hook" instance of this
        # class no longer applies -- "cmdclass" only ever appeared inside
        # this module's own module-docstring PROSE (never as real table
        # data in this file; the actual DANGEROUS_OPERATIONS needle lives in
        # `_capability_registry.py`), and T-0769 now excludes docstring
        # spans from the raw-text scan the same way T-0209 already excludes
        # comment spans -- that is precisely the false-positive class T-0769
        # closes, not a regression of this one. The accepted false-positive
        # class this test locks still holds for genuine non-comment,
        # non-docstring CODE-level string literal data: `_has_bare_compile_
        # call`'s own `needle = b"compile("` bytes literal (a real code
        # statement, not prose) still makes this module observe "eval" on
        # itself, exactly the self-match class the module docstring
        # documents.
        from frob.vet._capability import scan_file_capabilities

        own_path = (
            Path(__file__).resolve().parents[1]
            / "src"
            / "frob"
            / "vet"
            / "_capability.py"
        )
        capabilities = scan_file_capabilities(own_path)
        assert "eval" in capabilities  # b"compile(" appears as real code data
        assert "install-hook" not in capabilities  # T-0769: was docstring-only

    def test_scan_directory_capabilities_excludes_own_module(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability.py::_scan_directory_capabilities kind="unit"
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
        #
        # T-0253: the exclusion only fires when the scan root passed to
        # `_scan_directory_capabilities` itself identifies as frob's own
        # repo (`_is_frob_repo_root`, no ancestor search) -- scanning a bare
        # subdirectory like `src/frob/vet` directly no longer qualifies on
        # its own. Build a fake repo root carrying the pyproject-name +
        # crate-dir markers, with ONLY the real `vet/` package copied under
        # it (not the whole `src/frob` tree -- other packages like
        # `strata/_facts.py` have their OWN genuine, non-self-match eval
        # hits that would make a repo-wide assertion of "eval" absent
        # false; this test is specifically about vet/'s own self-match
        # exclusion, so it keeps the scan scoped the same way the pre-
        # T-0253 version did).
        from frob.vet._capability import _scan_directory_capabilities

        repo_root = Path(__file__).resolve().parents[1]
        fake_repo = tmp_path / "self-scan"
        fake_repo.mkdir()
        (fake_repo / "pyproject.toml").write_text('[project]\nname = "frob"\n')
        (fake_repo / "frob-core").mkdir()
        (fake_repo / "strata-core").mkdir()
        shutil.copytree(
            repo_root / "src" / "frob" / "vet",
            fake_repo / "src" / "frob" / "vet",
            ignore=shutil.ignore_patterns("__pycache__"),
        )

        capabilities, _ = _scan_directory_capabilities(
            fake_repo / "src" / "frob" / "vet", max_files=500
        )
        assert "eval" in capabilities  # discriminator refuses a subdir scan root
        assert "exec" in capabilities

        capabilities_from_repo_root, _ = _scan_directory_capabilities(
            fake_repo, max_files=500
        )
        assert "eval" not in capabilities_from_repo_root
        assert "exec" not in capabilities_from_repo_root


class TestCapabilityScanBindingResolution:
    """T-0328: import/binding-aware symbol resolution -- the plain
    substring needle scan in `TestCapabilityScan` above is evadable by
    ordinary Python aliasing/from-import syntax (`import subprocess as sp`,
    `from subprocess import run`); these tests lock the fix's litmus: every
    evasion case now DETECTED, every shadowing case NOT detected (no false
    positives), and a bare unimported name never fires."""

    def test_import_as_alias_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # Evasion case 1: `import subprocess as sp; sp.run(x)` -- the raw
        # text never contains "subprocess.run(" so the pre-T-0328 scanner
        # missed this entirely.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.py"
        pkg.write_text("import subprocess as sp\nsp.run(['ls'])\n")
        assert "exec" in scan_file_capabilities(pkg)

    def test_from_import_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # Evasion case 2: `from subprocess import run; run(x)` -- a bare
        # call with no dotted prefix at the call site at all.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.py"
        pkg.write_text("from subprocess import run\nrun(['ls'])\n")
        assert "exec" in scan_file_capabilities(pkg)

    def test_from_import_as_detected_with_correct_kind(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # Evasion case 3: `from os import system as e; e(x)` must resolve to
        # `os.system` -- capability "exec", NOT "eval" (the pre-T-0328
        # scanner reported nothing at all; a naive fix that just matched
        # "system" anywhere would have risked the wrong kind).
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.py"
        pkg.write_text("from os import system as e\ne('ls')\n")
        capabilities = scan_file_capabilities(pkg)
        assert "exec" in capabilities
        assert "eval" not in capabilities

    def test_import_as_alias_operation_names_registry_entry(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability.py::_scan_file_operations kind="unit"
        # `_scan_file_operations`'s resolver-backed sibling: an aliased call
        # still names the real registry entry (library="subprocess"), not
        # just a bare kind label.
        from frob.vet._capability import _scan_file_operations

        pkg = tmp_path / "pkg.py"
        pkg.write_text("import subprocess as sp\nsp.run(['ls'])\n")
        ops = _scan_file_operations(pkg)
        assert any(
            op.capability_kind == "exec" and op.library == "subprocess" for op in ops
        )

    def test_method_shadowing_import_not_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # Shadow case: a class method named `run` on an unrelated object
        # (`Job().run()`) must NOT resolve to a dangerous `run` symbol --
        # `Job()` is a call, not an import-bound name, so resolution
        # deliberately stops there.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.py"
        pkg.write_text("class Job:\n    def run(self):\n        pass\n\nJob().run()\n")
        assert "exec" not in scan_file_capabilities(pkg)

    def test_param_shadowing_import_not_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # Shadow case: a function parameter named `system` shadows a
        # `from os import system` import for the duration of that function
        # -- calling the param must not resolve to `os.system`.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.py"
        pkg.write_text("from os import system\n\n\ndef g(system):\n    system('ls')\n")
        assert "exec" not in scan_file_capabilities(pkg)

    # frob:waive DUP001 reason="parallel vet-rule case table: independent \
    # cases sharing an arrange-act scaffold typical of exhaustive per-rule \
    # coverage; extracting would obscure per-case intent"
    def test_local_variable_shadowing_import_not_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # Shadow case: a local variable named `run` (assigned a harmless
        # value) shadows an imported dangerous `run` for the rest of that
        # function's scope.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.py"
        pkg.write_text(
            "from subprocess import run\n\n\ndef f():\n"
            "    run = 'not a subprocess call'\n"
            "    run.upper()\n"
        )
        assert "exec" not in scan_file_capabilities(pkg)

    def test_bare_name_call_with_no_import_not_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # No naive bare-name false positive: calling an undefined/locally-
        # scoped `run()` with no matching import anywhere in the file must
        # not resolve to anything.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.py"
        pkg.write_text("run('ls')\n")
        assert "exec" not in scan_file_capabilities(pkg)

    def test_direct_call_still_detected_via_resolver(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # Regression: an ordinary unaliased `subprocess.run()` call (already
        # caught by the raw-text scan) must still fire once the resolver
        # path is unioned in -- no regression on the common case.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.py"
        pkg.write_text("import subprocess\nsubprocess.run(['ls'])\n")
        assert "exec" in scan_file_capabilities(pkg)

    def test_attribute_only_env_access_via_alias_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # Non-call attribute access (no argument_list) through an aliased
        # import: `import os as o; o.environ` must resolve to `os.environ`.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.py"
        pkg.write_text("import os as o\nx = o.environ\n")
        assert "env" in scan_file_capabilities(pkg)


class TestCapabilityScanLocalRebindResolution:
    """T-0337: follow-on to T-0328 -- the import/binding resolver above
    correctly resolves import ALIASES but does no intraprocedural
    dataflow, so a LOCAL rebinding of an already-imported dangerous name
    (`xyz = run; xyz(...)`) evaded the scan entirely. These tests lock the
    scope-local copy-propagation fix: single/chained/attribute rebinds now
    DETECTED, while every T-0328 no-false-positive/shadow guarantee
    (benign rebind, parameter shadow) stays silent."""

    def test_single_rebind_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # `xyz = run; xyz(...)` -- a plain local rebind of an imported
        # dangerous name must resolve through the alias to "exec".
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.py"
        pkg.write_text("from subprocess import run\nxyz = run\nxyz(['pwned'])\n")
        assert "exec" in scan_file_capabilities(pkg)

    def test_chained_rebind_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # `a = run; b = a; b(...)` -- transitive copy-propagation across
        # two hops in document order.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.py"
        pkg.write_text("from subprocess import run\na = run\nb = a\nb(['pwned'])\n")
        assert "exec" in scan_file_capabilities(pkg)

    def test_attribute_rebind_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # `e = os.system; e("x")` -- rebind to a dangerous ATTRIBUTE chain
        # (not a bare imported name) must also resolve.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.py"
        pkg.write_text("import os\ne = os.system\ne('ls')\n")
        assert "exec" in scan_file_capabilities(pkg)

    def test_benign_rebind_not_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # `run = lambda x: x; run()` -- a name that is never bound to any
        # dangerous target anywhere in the file must stay silent; a lambda
        # RHS is not a resolvable identifier/attribute chain, so it never
        # gets an alias-table entry.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.py"
        pkg.write_text("run = lambda x: x\nrun()\n")
        assert "exec" not in scan_file_capabilities(pkg)

    def test_parameter_shadow_still_not_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # T-0328 regression guard: a parameter named `run` shadowing an
        # imported dangerous `run` must stay silent -- a parameter binds no
        # alias-table entry (it is not an assignment RHS this pass ever
        # inspects), so the copy-propagation fix must not reopen this hole.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.py"
        pkg.write_text("from subprocess import run\n\n\ndef f(run):\n    run(['ls'])\n")
        assert "exec" not in scan_file_capabilities(pkg)

    def test_dangerous_then_benign_rebind_stays_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # Documented may-analysis over-approximation (T-0337): once a name
        # is EVER bound to a dangerous target in a scope, a later benign
        # reassignment of that same name does not clear the flag -- a call
        # anywhere in the scope through that name is still reported. This
        # is a deliberate soundness choice, not a bug: a flow-insensitive
        # "may" analysis over-approximates rather than risk a false
        # negative from tracking reassignment order.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.py"
        pkg.write_text("from subprocess import run\nx = run\nx(['a'])\nx = 5\n")
        assert "exec" in scan_file_capabilities(pkg)

    def test_call_before_rebinding_still_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # T-0468: Python sibling of the T-0378 Rust ordering fix. The
        # Python `_shadowing_scope`/`_py_scope_bound_names` pair collects
        # every name bound ANYWHERE in the enclosing scope with no byte-
        # position tracking, so a capability call textually BEFORE a
        # same-named rebind is wrongly treated as already shadowed and the
        # real dangerous call is silently dropped. `o.system(...)` here
        # executes before `o = None` takes effect (Python assignment does
        # not hoist), so it MUST still resolve through the `import os as o`
        # alias to "exec". Uses an ALIASED import (not bare `os.system`) so
        # the raw-text lexical pass cannot mask a resolver regression --
        # the raw source never contains the literal substring "os.system".
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.py"
        pkg.write_text("import os as o\no.system('ls')\no = None\n")
        assert "exec" in scan_file_capabilities(pkg)

    def test_call_after_rebinding_still_not_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # T-0468 sibling of the ordering test above: the position-aware
        # fix must not become unconditionally permissive -- a call AFTER
        # the same `o = None` rebind is still correctly shadowed.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.py"
        pkg.write_text("import os as o\no = None\no.system('ls')\n")
        assert "exec" not in scan_file_capabilities(pkg)


class TestCapabilityScanTsBindingResolution:
    """T-0377: TS/JS sibling of `TestCapabilityScanBindingResolution` --
    before this, TypeScript/JS capability scanning was pure lexical
    needle-matching, so any renamed/destructured/namespaced import to a
    dangerous module evaded it entirely. These tests lock the fix's
    litmus: every evasion case now DETECTED, every shadowing case NOT
    detected (no false positives).

    Deliberately uses the `net`/"axios." needle (dotted, no bare-module-
    name needle) rather than `exec`/"child_process" for the evasion-
    detection cases: `exec`'s needle table includes the bare substring
    "child_process", which the PRE-EXISTING raw-text lexical scan already
    matches on the import line itself regardless of aliasing -- a test
    built on it would pass even with the resolver disabled, and would not
    actually prove anything about the binding-aware fix. "axios." never
    appears literally in an aliased/namespaced/required import's source
    text (only the bare string literal `'axios'` does), so a positive
    result here can only come from the resolver."""

    def test_default_import_alias_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # Evasion case 1: `import ax from 'axios'; ax.get(url)` -- a
        # renamed default import; the raw text never contains "axios."
        # (only the quoted module specifier 'axios').
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.ts"
        pkg.write_text("import ax from 'axios';\nax.get(url);\n")
        assert "net" in scan_file_capabilities(pkg)

    def test_require_bare_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # Evasion case 2: `const ax = require('axios'); ax.get(url)` --
        # CommonJS require bound to a renamed local, no ES `import` at all.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.ts"
        pkg.write_text("const ax = require('axios');\nax.get(url);\n")
        assert "net" in scan_file_capabilities(pkg)

    def test_require_destructure_rename_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # Evasion case 3: `const {get: g} = require('axios'); g(url)` --
        # CommonJS destructure WITH rename (`pair_pattern`), the sharpest
        # evasion: the call site is a bare `g(url)`, matching no needle at
        # all lexically.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.ts"
        pkg.write_text("const {get: g} = require('axios');\ng(url);\n")
        assert "net" in scan_file_capabilities(pkg)

    def test_namespace_import_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # Evasion case 4: `import * as ax from 'axios'; ax.get(url)` --
        # namespace import, member access through the namespace alias.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.ts"
        pkg.write_text("import * as ax from 'axios';\nax.get(url);\n")
        assert "net" in scan_file_capabilities(pkg)

    def test_ts_import_require_clause_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # Evasion case 5: `import ax = require('axios'); ax.get(url)` --
        # TS-only import-equals-require form.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.ts"
        pkg.write_text("import ax = require('axios');\nax.get(url);\n")
        assert "net" in scan_file_capabilities(pkg)

    def test_operation_names_registry_entry_for_aliased_import(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability.py::_scan_file_operations kind="unit"
        # `_scan_file_operations`'s resolver-backed sibling: a renamed
        # default import still names the real registry entry
        # (library="axios"), not just a bare kind label.
        from frob.vet._capability import _scan_file_operations

        pkg = tmp_path / "pkg.ts"
        pkg.write_text("import ax from 'axios';\nax.get(url);\n")
        ops = _scan_file_operations(pkg)
        assert any(op.capability_kind == "net" and op.library == "axios" for op in ops)

    def test_param_named_get_not_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # No false positive: a LOCAL function parameter named `get` (never
        # imported from anywhere dangerous) must not be flagged.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.ts"
        pkg.write_text("function fetch(get) {\n  get(url);\n}\n")
        assert "net" not in scan_file_capabilities(pkg)

    def test_param_shadowing_import_not_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # Shadow case: a function parameter named `ax` shadows a `import
        # ax from 'axios'` default import for the duration of that
        # function -- calling `ax.get(...)` inside must not resolve to
        # `axios.get`.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.ts"
        pkg.write_text("import ax from 'axios';\nfunction g(ax) {\n  ax.get(url);\n}\n")
        assert "net" not in scan_file_capabilities(pkg)

    def test_method_on_unrelated_object_not_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # Shadow case: a class method named `get` on an unrelated object
        # (`new Job().get()`) must NOT resolve to a dangerous `get` symbol
        # -- `new Job()` is a `new_expression`, not an import-bound name,
        # so resolution deliberately stops there.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.ts"
        pkg.write_text("class Job {\n  get() {}\n}\nnew Job().get();\n")
        assert "net" not in scan_file_capabilities(pkg)

    def test_bare_name_call_with_no_import_not_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # No naive bare-name false positive: calling an undefined `get()`
        # with no matching import anywhere in the file must not resolve.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.ts"
        pkg.write_text("get(url);\n")
        assert "net" not in scan_file_capabilities(pkg)

    def test_direct_unaliased_call_still_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # Regression: the pre-existing raw-text lexical scan (needle
        # "child_process") is unaffected by adding the TS resolver pass --
        # an ordinary unaliased `require('child_process').exec()` call
        # still fires once the resolver path is unioned in.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.ts"
        pkg.write_text("import {exec} from 'child_process';\nexec(cmd);\n")
        assert "exec" in scan_file_capabilities(pkg)

    def test_bracket_access_inline_require_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # T-0377 reviewer round 2: bracket/computed-member access,
        # `require('axios')['get'](url)` -- a plain bracket-access RCE
        # shape the round-1 resolver missed entirely (it only ever
        # inspected `identifier`/`member_expression` nodes, never
        # `subscript_expression`).
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.ts"
        pkg.write_text("require('axios')['get'](url);\n")
        assert "net" in scan_file_capabilities(pkg)

    def test_bracket_access_aliased_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # T-0377 reviewer round 2: bracket access through an aliased
        # `require()` rebind -- `const ax = require('axios'); ax['get']
        # (url)`.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.ts"
        pkg.write_text("const ax = require('axios');\nax['get'](url);\n")
        assert "net" in scan_file_capabilities(pkg)

    def test_dynamic_import_then_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # T-0377 reviewer round 2: `import('axios').then(ax => ax.get(url))`
        # -- dynamic import is the STANDARD way to conditionally load a
        # module in TS/JS, a natural place to hide a dangerous one; the
        # round-1 resolver never recognized an `import(...)` call site at
        # all.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.ts"
        pkg.write_text("import('axios').then(ax => ax.get(url));\n")
        assert "net" in scan_file_capabilities(pkg)

    def test_await_dynamic_import_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # T-0377 reviewer round 2: `const ax = await import('axios');
        # ax.get(url)` -- the `async`/`await` sibling of `.then(cb)`.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.ts"
        pkg.write_text(
            "async function f() {\n"
            "  const ax = await import('axios');\n"
            "  ax.get(url);\n"
            "}\n"
        )
        assert "net" in scan_file_capabilities(pkg)

    def test_child_process_bracket_and_dynamic_import_caught(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # Realism confirmation (reviewer-requested): both new evasion
        # classes against the ACTUAL exec-family library, not just the
        # isolation proxy above. Note the raw-text lexical scan ALSO
        # matches these two (needle "child_process" is a bare substring
        # present on the `require('child_process')` line itself) -- this
        # test confirms the full production path (lexical union resolver)
        # still fires end-to-end on the real dangerous module; the axios/
        # "net" tests above are what isolate the RESOLVER's own
        # contribution from the lexical layer.
        from frob.vet._capability import scan_file_capabilities

        bracket_pkg = tmp_path / "bracket.ts"
        bracket_pkg.write_text("require('child_process')['exec'](cmd);\n")
        assert "exec" in scan_file_capabilities(bracket_pkg)

        dynamic_pkg = tmp_path / "dynamic.ts"
        dynamic_pkg.write_text("import('child_process').then(cp => cp.exec(cmd));\n")
        assert "exec" in scan_file_capabilities(dynamic_pkg)

    def test_computed_subscript_not_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # Documented conservative limitation (module docstring, T-draft-e7c8b53c
        # follow-up filed): a FULLY COMPUTED (non-string-literal) subscript
        # whose key has no resolvable single-literal binding anywhere in
        # the file (T-0432's `_ts_local_string_bindings` closes the case
        # where it DOES, see `test_local_const_string_subscript_detected`)
        # -- `ax[dynamicKey](url)` where `dynamicKey` is never assigned a
        # literal -- cannot be resolved statically; the actual property
        # name is a genuine runtime value. This is an accepted
        # false-negative gap, not a bug: recorded here so the gap is a
        # checkable fact, not a silent one.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.ts"
        pkg.write_text("const ax = require('axios');\nax[dynamicKey](url);\n")
        assert "net" not in scan_file_capabilities(pkg)

    def test_static_template_literal_subscript_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # T-0377 reviewer round 3: a NO-INTERPOLATION template-literal
        # subscript -- `` ax[`get`](url) `` -- carries identical static
        # text to `ax['get'](url)` and must resolve the same. Template
        # literals are an everyday idiom (many lint configs PREFER them
        # over quotes), not an obfuscation trick, on the exact dangerous-
        # capability surface this ticket protects.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.ts"
        pkg.write_text("const ax = require('axios');\nax[`get`](url);\n")
        assert "net" in scan_file_capabilities(pkg)

    def test_interpolated_template_subscript_not_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # Documented conservative limitation (module docstring, T-draft-
        # e7c8b53c follow-up filed): an INTERPOLATED template-literal
        # subscript whose substituted name has no resolvable single-
        # literal binding -- `` ax[`${dynamicKey}`](url) `` where
        # `dynamicKey` is never assigned a literal (T-0432's dataflow
        # closes the case where it IS, see
        # `test_local_const_template_substitution_subscript_detected`) --
        # is a genuinely computed key, unlike a static no-interpolation
        # template literal (`test_static_template_literal_subscript_detected`
        # above), and stays under the same accepted false-negative gap as
        # `test_computed_subscript_not_detected`.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.ts"
        pkg.write_text("const ax = require('axios');\nax[`${dynamicKey}`](url);\n")
        assert "net" not in scan_file_capabilities(pkg)

    def test_local_const_string_subscript_detected(self, tmp_path: Path) -> None:
        # T-0432: the trivial indirection the audit called out --
        # `const key = 'get'; ax[key](url)` -- is a local name bound to
        # exactly one string literal in the file, so the light dataflow
        # pass resolves it the same as `ax['get'](url)`.
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.ts"
        pkg.write_text(
            "const ax = require('axios');\nconst key = 'get';\nax[key](url);\n"
        )
        assert "net" in scan_file_capabilities(pkg)

    def test_local_const_template_substitution_subscript_detected(
        self, tmp_path: Path
    ) -> None:
        # T-0432: the same trivial indirection through a single-
        # substitution template literal -- `` ax[`${key}`](url) `` where
        # `key` is a local single-literal constant.
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.ts"
        pkg.write_text(
            "const ax = require('axios');\nconst key = 'get';\nax[`${key}`](url);\n"
        )
        assert "net" in scan_file_capabilities(pkg)

    def test_reassigned_const_string_subscript_not_detected(
        self, tmp_path: Path
    ) -> None:
        # Honest limit (T-0432, not a regression): a name bound to TWO
        # different literal values anywhere in the file is ambiguous --
        # this dataflow-lite pass never guesses which one is live at the
        # subscript site, so it stays silent (same as an unresolved
        # computed subscript) rather than risk resolving to the wrong
        # value.
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.ts"
        pkg.write_text(
            "const ax = require('axios');\n"
            "let key = 'get';\n"
            "if (cond) { key = 'post'; }\n"
            "ax[key](url);\n"
        )
        assert "net" not in scan_file_capabilities(pkg)

    def test_non_literal_bound_subscript_not_detected(self, tmp_path: Path) -> None:
        # Honest limit (T-0432, NOT closed by this ticket, out of scope):
        # a name bound to a non-literal value (a function call result, a
        # concatenation, another variable) anywhere in the file is
        # excluded from the local-constant table entirely -- resolving it
        # would need real reaching-definitions dataflow, not the light
        # single-literal-binding heuristic this ticket implements.
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.ts"
        pkg.write_text(
            "const ax = require('axios');\n"
            "const key = computeMethodName();\n"
            "ax[key](url);\n"
        )
        assert "net" not in scan_file_capabilities(pkg)

    def test_multi_substitution_template_subscript_not_detected(
        self, tmp_path: Path
    ) -> None:
        # Honest limit (T-0432, NOT closed by this ticket, out of scope):
        # a template literal with MORE than one substitution, or any
        # surrounding literal text, is still a genuinely computed key even
        # when every piece happens to be a single-literal-bound local --
        # only the exact `` `${key}` `` (one substitution, no other
        # content) shape resolves.
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.ts"
        pkg.write_text(
            "const ax = require('axios');\n"
            "const a = 'g';\n"
            "const b = 'et';\n"
            "ax[`${a}${b}`](url);\n"
        )
        assert "net" not in scan_file_capabilities(pkg)


class TestCapabilityScanRustBindingResolution:
    """T-0378: Rust sibling of `TestCapabilityScanBindingResolution`/
    `TestCapabilityScanTsBindingResolution` -- before this, Rust capability
    scanning was pure lexical needle-matching, so an `as`-aliased `use`
    import to a dangerous path evaded it entirely (`use std::process::
    Command as C; C::new(cmd)` never contains the literal "Command::new("
    text the needle table looks for). These tests lock the fix's litmus:
    the aliased evasion now DETECTED, local shadowing still NOT detected
    (no false positives)."""

    def test_use_as_alias_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # Evasion case: `use std::process::Command as C; C::new(cmd)` -- the
        # raw text never contains "Command::new(", only the `use` line's
        # own "std::process::Command" text.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.rs"
        pkg.write_text('use std::process::Command as C;\nfn f() { C::new("sh"); }\n')
        assert "exec" in scan_file_capabilities(pkg)

    def test_operation_names_registry_entry_for_use_alias(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::_scan_file_operations kind="unit"
        # `_scan_file_operations`'s resolver-backed sibling: an `as`-aliased
        # `use` still names the real registry entry (library="std::
        # process"), not just a bare kind label.
        from frob.vet._capability import _scan_file_operations

        pkg = tmp_path / "pkg.rs"
        pkg.write_text('use std::process::Command as C;\nfn f() { C::new("sh"); }\n')
        ops = _scan_file_operations(pkg)
        assert any(
            op.capability_kind == "exec" and op.library == "std::process" for op in ops
        )

    def test_bare_use_import_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # An unaliased `use` (no rename) still resolves through the same
        # binding table -- `Command::new(cmd)` after `use std::process::
        # Command;`.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.rs"
        pkg.write_text('use std::process::Command;\nfn f() { Command::new("sh"); }\n')
        assert "exec" in scan_file_capabilities(pkg)

    def test_param_shadowing_use_alias_not_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # Shadow case: a function parameter named `C` shadows a `use
        # std::process::Command as C` alias for the duration of that
        # function -- calling `C::new(...)` inside must not resolve to
        # `std::process::Command::new`.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.rs"
        pkg.write_text(
            'use std::process::Command as C;\nfn f(C: i32) { C::new("sh"); }\n'
        )
        assert "exec" not in scan_file_capabilities(pkg)

    def test_let_shadowing_use_alias_not_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # Shadow case: a local `let C = ...` binding shadows the `use`
        # alias for the rest of that function body.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.rs"
        pkg.write_text(
            'use std::process::Command as C;\nfn f() { let C = 5; C::new("sh"); }\n'
        )
        assert "exec" not in scan_file_capabilities(pkg)

    def test_bare_name_call_with_no_use_not_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # No naive bare-name false positive: calling `C::new(...)` with no
        # `use` binding anywhere in the file must not resolve.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.rs"
        pkg.write_text('fn f() { C::new("sh"); }\n')
        assert "exec" not in scan_file_capabilities(pkg)

    def test_call_before_rebinding_still_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # T-0378 round 2 (reviewer REJECT, T-0339 fail-closed): round 1's
        # shadow check was ORDER-INSENSITIVE -- it collected every name
        # bound ANYWHERE in the scope regardless of position, so a call
        # textually BEFORE a same-named `let` rebinding was wrongly
        # treated as already shadowed and the real dangerous call got
        # silently dropped. A `let` does not hoist in Rust: the call here
        # executes before `let C = 5` takes effect, so it MUST still
        # resolve through the `use`-bound alias.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.rs"
        pkg.write_text(
            "use std::process::Command as C;\n"
            "fn f() {\n"
            '    C::new("sh");\n'
            "    let C = 5;\n"
            "}\n"
        )
        assert "exec" in scan_file_capabilities(pkg)

    def test_call_after_rebinding_still_not_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # T-0378 round 2 sibling of the ordering test above: the position-
        # aware fix must not become UNCONDITIONALLY permissive -- a call
        # AFTER the same `let C = 5` rebinding is still correctly shadowed
        # (this is `test_let_shadowing_use_alias_not_detected` restated
        # with an explicit two-statement body so both orderings are
        # exercised side by side).
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.rs"
        pkg.write_text(
            "use std::process::Command as C;\n"
            "fn f() {\n"
            "    let C = 5;\n"
            '    C::new("sh");\n'
            "}\n"
        )
        assert "exec" not in scan_file_capabilities(pkg)


class TestCapabilityScanCBindingResolution:
    """T-0379: C/C++ sibling of `TestCapabilityScanRustBindingResolution` --
    before this, C/C++ capability scanning was pure lexical needle-matching,
    so a `#define`-renamed dangerous call evaded it entirely (`#define SYS
    system; SYS("sh")` never contains the literal "system(" text the needle
    table looks for). These tests lock the fix's litmus: the macro-aliased
    evasion now DETECTED, local shadowing still NOT detected (no false
    positives)."""

    def test_macro_alias_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # Evasion case: `#define SYS system` then `SYS("sh")` -- the raw
        # text never contains "system(", only the `#define` line's own
        # "system" token.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.c"
        pkg.write_text('#define SYS system\nvoid f() { SYS("sh"); }\n')
        assert "exec" in scan_file_capabilities(pkg)

    def test_operation_names_registry_entry_for_macro_alias(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability.py::_scan_file_operations kind="unit"
        # `_scan_file_operations`'s resolver-backed sibling: a macro-renamed
        # call still names the real registry entry (library="libc"), not
        # just a bare kind label.
        from frob.vet._capability import _scan_file_operations

        pkg = tmp_path / "pkg.c"
        pkg.write_text('#define SYS system\nvoid f() { SYS("sh"); }\n')
        ops = _scan_file_operations(pkg)
        assert any(op.capability_kind == "exec" and op.library == "libc" for op in ops)

    def test_transitive_macro_alias_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # A chained rename (`#define A B` + `#define B system`) still
        # resolves `A(...)` all the way through to `system`.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.c"
        pkg.write_text('#define A B\n#define B system\nvoid f() { A("sh"); }\n')
        assert "exec" in scan_file_capabilities(pkg)

    def test_bare_macro_no_define_not_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # No naive bare-name false positive: calling `SYS(...)` with no
        # `#define` anywhere in the file must not resolve.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.c"
        pkg.write_text('void f() { SYS("sh"); }\n')
        assert "exec" not in scan_file_capabilities(pkg)

    def test_param_shadowing_macro_alias_not_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # Shadow case: a function parameter named `SYS` shadows the macro
        # alias for the duration of that function -- calling `SYS(...)`
        # inside must not resolve to `system`. (`SYS` as a parameter name is
        # contrived C -- macros do not normally collide with identifiers
        # this way -- but exercises the same no-false-positive discipline
        # as the python/rust resolvers' shadow tests.)
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.c"
        pkg.write_text('#define SYS system\nvoid f(int SYS) { SYS("sh"); }\n')
        assert "exec" not in scan_file_capabilities(pkg)

    def test_local_shadowing_macro_alias_not_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # Shadow case: a local variable declaration named `SYS` shadows the
        # macro alias for the rest of that function body.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.c"
        pkg.write_text('#define SYS system\nvoid f() { int SYS; SYS("sh"); }\n')
        assert "exec" not in scan_file_capabilities(pkg)

    def test_call_before_local_shadow_still_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # T-0379 mirrors the T-0378 round 2 ordering fix: a call textually
        # BEFORE the same-named local declaration must still resolve
        # through the macro alias -- the C preprocessor's own textual
        # substitution has no notion of "not yet declared" either, so this
        # also matches real preprocessor behavior, not just the scanner's
        # approximation.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.c"
        pkg.write_text(
            '#define SYS system\nvoid f() {\n    SYS("sh");\n    int SYS;\n}\n'
        )
        assert "exec" in scan_file_capabilities(pkg)

    def test_function_like_macro_not_resolved(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # Documented limitation: a function-like macro (`#define SYS(x)
        # system(x)`) is a structurally different `preproc_function_def`
        # node and is not resolved by this pass -- its own expansion
        # already contains literal "system(" text most of the time anyway,
        # so the raw-text lexical scan still has a real shot at typical
        # usage. Here the definition line itself is what carries "system("
        # so the lexical scan (not the binding resolver) is what fires.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.c"
        pkg.write_text('#define SYS(x) system(x)\nvoid f() { SYS("sh"); }\n')
        assert "exec" in scan_file_capabilities(pkg)


class TestEmbeddedCodeCapability:
    """T-0244: HTML/JS string literals embedded in python source (the
    malmberg pilot P3 dashboard-as-a-string shape) -- fail-closed
    `embedded_code` declaration plus best-effort typescript-needle
    re-scan of the region's own text."""

    def test_embedded_html_script_string_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # T-0244: a large HTML/JS-shaped string literal inside a python
        # module (the malmberg pilot P3 shape) surfaces `embedded_code`
        # AND, since the embedded script itself calls `eval(`, the
        # typescript-needle re-scan's `eval` hit too.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "dashboard.py"
        padding = "x" * 40
        pkg.write_text(
            "DASHBOARD_HTML = '''\n"
            "<!doctype html>\n"
            "<html><body>\n"
            "<script>\n"
            f"// {padding}\n"
            f"// {padding}\n"
            "function render(payload) { eval(payload); }\n"
            "document.getElementById('root').innerHTML = render();\n"
            "</script>\n"
            "</body></html>\n"
            "'''\n"
        )
        capabilities = scan_file_capabilities(pkg)
        assert "embedded_code" in capabilities
        assert "eval" in capabilities

    def test_embedded_code_region_below_size_threshold_not_detected(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # T-0244: a short string that merely mentions an HTML tag (e.g. an
        # error message fragment) must not fire -- the heuristic requires
        # both the size floor and a signal token, not either alone.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.py"
        pkg.write_text("MSG = 'invalid <script> tag in input'\n")
        assert "embedded_code" not in scan_file_capabilities(pkg)

    def test_embedded_code_declared_even_when_content_opaque_to_needles(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # T-0244 fail-closed guarantee: a large embedded HTML region whose
        # content matches no specific typescript needle (plain markup, no
        # script) still declares `embedded_code` -- the region is never
        # silently passed just because the best-effort re-scan is empty.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.py"
        filler = "\n".join(f"<div>row {i}</div>" for i in range(20))
        pkg.write_text(
            f"PAGE_HTML = '''\n<html><body>\n{filler}\n</body></html>\n'''\n"
        )
        capabilities = scan_file_capabilities(pkg)
        assert "embedded_code" in capabilities

    def test_embedded_code_regions_scanned_via_operations(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::_scan_file_operations kind="unit"
        # T-0244: _scan_file_operations names the specific typescript
        # DANGEROUS_OPERATIONS entry that fired inside the embedded region,
        # not just the bare "eval" capability kind.
        from frob.vet._capability import _scan_file_operations

        pkg = tmp_path / "dashboard.py"
        padding = "x" * 80
        pkg.write_text(
            "DASHBOARD_HTML = '''\n"
            "<!doctype html>\n"
            "<script>\n"
            f"// {padding}\n"
            f"// {padding}\n"
            "function render(payload) { eval(payload); }\n"
            "</script>\n"
            "'''\n"
        )
        ops = _scan_file_operations(pkg)
        assert any(
            op.capability_kind == "eval" and op.language == "typescript" for op in ops
        )


class TestFingerprintScan:
    """T-0153: `_scan_file_fingerprints` -- the CVE-fingerprint sibling of
    `_scan_file_operations`, joined to `frob.strata.CVE_FINGERPRINTS`."""

    # frob:waive DUP001 reason="parallel vet-rule case table: independent \
    # cases sharing an arrange-act scaffold typical of exhaustive per-rule \
    # coverage; extracting would obscure per-case intent"
    def test_matches_a_known_fingerprint(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::_scan_file_fingerprints kind="unit"
        from frob.vet._capability import _scan_file_fingerprints

        pkg = tmp_path / "pkg.py"
        pkg.write_text("data = yaml.load(raw_bytes)\n")
        matches = _scan_file_fingerprints(pkg)
        assert any(m.id == "FP-DESERIALIZE-YAML-001" for m in matches)

    def test_no_match_on_clean_source(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::_scan_file_fingerprints kind="unit"
        from frob.vet._capability import _scan_file_fingerprints

        pkg = tmp_path / "pkg.py"
        pkg.write_text("def add(a, b):\n    return a + b\n")
        assert _scan_file_fingerprints(pkg) == ()

    def test_whitespace_reformatted_needle_still_matches(self, tmp_path: Path) -> None:
        # T-0400 audit finding #3: `shell=True` reformatted with spaces
        # around the `=` used to evade FP-EXEC-SHELL-001 (raw substring
        # search only); the fingerprint scan is now whitespace-tolerant.
        # frob:tests src/frob/vet/_capability.py::_scan_file_fingerprints kind="unit"
        from frob.vet._capability import _scan_file_fingerprints

        pkg = tmp_path / "pkg.py"
        pkg.write_text("subprocess.run(cmd, shell = True)\n")
        matches = _scan_file_fingerprints(pkg)
        assert any(m.id == "FP-EXEC-SHELL-001" for m in matches)

    def test_whitespace_tolerant_match_still_respects_comment_spans(
        self, tmp_path: Path
    ) -> None:
        # The whitespace-tolerant matcher must still exclude comment-only
        # occurrences (T-0209), same as the exact-match path.
        # frob:tests src/frob/vet/_capability.py::_scan_file_fingerprints kind="unit"
        from frob.vet._capability import _scan_file_fingerprints

        pkg = tmp_path / "pkg.py"
        pkg.write_text("# example: subprocess.run(cmd, shell = True)\n")
        matches = _scan_file_fingerprints(pkg)
        assert not any(m.id == "FP-EXEC-SHELL-001" for m in matches)

    # frob:waive DUP001 reason="parallel vet-rule case table: independent \
    # cases sharing an arrange-act scaffold typical of exhaustive per-rule \
    # coverage; extracting would obscure per-case intent"
    def test_matches_the_xxe_fingerprint_positive(self, tmp_path: Path) -> None:
        # T-0189 litmus positive: an lxml parser explicitly left resolving
        # external entities matches FP-XXE-PARSE-001.
        # frob:tests src/frob/vet/_capability.py::_scan_file_fingerprints kind="unit"
        from frob.vet._capability import _scan_file_fingerprints

        pkg = tmp_path / "pkg.py"
        pkg.write_text(
            "parser = etree.XMLParser(resolve_entities=True)\n"
            "tree = etree.parse(untrusted_source, parser)\n"
        )
        matches = _scan_file_fingerprints(pkg)
        assert any(m.id == "FP-XXE-PARSE-001" for m in matches)

    # frob:waive DUP001 reason="parallel vet-rule case table: independent \
    # cases sharing an arrange-act scaffold typical of exhaustive per-rule \
    # coverage; extracting would obscure per-case intent"
    def test_does_not_match_the_xxe_fingerprint_negative(self, tmp_path: Path) -> None:
        # T-0189 litmus negative: the hardened lxml configuration (entity
        # resolution explicitly disabled) must not fire.
        # frob:tests src/frob/vet/_capability.py::_scan_file_fingerprints kind="unit"
        from frob.vet._capability import _scan_file_fingerprints

        pkg = tmp_path / "pkg.py"
        pkg.write_text(
            "parser = etree.XMLParser(resolve_entities=False, "
            "no_network=True, load_dtd=False)\n"
            "tree = etree.parse(untrusted_source, parser)\n"
        )
        matches = _scan_file_fingerprints(pkg)
        assert not any(m.id == "FP-XXE-PARSE-001" for m in matches)

    def test_no_language_returns_empty(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::_scan_file_fingerprints kind="unit"
        from frob.vet._capability import _scan_file_fingerprints

        assert _scan_file_fingerprints(tmp_path / "foo.unknownext") == ()

    def test_unreadable_file_returns_empty(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::_scan_file_fingerprints kind="unit"
        from frob.vet._capability import _scan_file_fingerprints

        missing = tmp_path / "gone.py"
        assert _scan_file_fingerprints(missing) == ()

    # frob:waive DUP001 reason="parallel vet-rule case table: independent \
    # cases sharing an arrange-act scaffold typical of exhaustive per-rule \
    # coverage; extracting would obscure per-case intent"
    def test_language_mismatch_does_not_match(self, tmp_path: Path) -> None:
        # a typescript-only fingerprint's needle appearing in a .py file
        # must never match -- the language gate is enforced independently
        # of the needle text.
        # frob:tests src/frob/vet/_capability.py::_scan_file_fingerprints kind="unit"
        from frob.vet._capability import _scan_file_fingerprints

        pkg = tmp_path / "pkg.py"
        pkg.write_text("x = 'new Function(\"return 1\")'\n")
        matches = _scan_file_fingerprints(pkg)
        assert not any(m.id == "FP-CODEEVAL-TEMPLATE-001" for m in matches)

    # frob:waive DUP001 reason="parallel vet-rule case table: independent \
    # cases sharing an arrange-act scaffold typical of exhaustive per-rule \
    # coverage; extracting would obscure per-case intent"
    def test_matches_tls_verify_false_python(self, tmp_path: Path) -> None:
        # T-0188: FP-TLS-VERIFY-001 -- requests/httpx/aiohttp verify=False.
        # frob:tests src/frob/vet/_capability.py::_scan_file_fingerprints kind="unit"
        from frob.vet._capability import _scan_file_fingerprints

        pkg = tmp_path / "pkg.py"
        pkg.write_text("resp = requests.get(url, verify=False)\n")
        matches = _scan_file_fingerprints(pkg)
        assert any(m.id == "FP-TLS-VERIFY-001" for m in matches)

    # frob:waive DUP001 reason="parallel vet-rule case table: independent \
    # cases sharing an arrange-act scaffold typical of exhaustive per-rule \
    # coverage; extracting would obscure per-case intent"
    def test_no_match_on_verified_tls_python(self, tmp_path: Path) -> None:
        # negative sibling: verify=True never fires FP-TLS-VERIFY-001.
        # frob:tests src/frob/vet/_capability.py::_scan_file_fingerprints kind="unit"
        from frob.vet._capability import _scan_file_fingerprints

        pkg = tmp_path / "pkg.py"
        pkg.write_text("resp = requests.get(url, verify=True)\n")
        matches = _scan_file_fingerprints(pkg)
        assert not any(m.id == "FP-TLS-VERIFY-001" for m in matches)

    # frob:waive DUP001 reason="parallel vet-rule case table: independent \
    # cases sharing an arrange-act scaffold typical of exhaustive per-rule \
    # coverage; extracting would obscure per-case intent"
    def test_matches_tls_reject_unauthorized_false_node(self, tmp_path: Path) -> None:
        # T-0188: FP-TLS-VERIFY-002 -- Node https/tls rejectUnauthorized: false.
        # frob:tests src/frob/vet/_capability.py::_scan_file_fingerprints kind="unit"
        from frob.vet._capability import _scan_file_fingerprints

        pkg = tmp_path / "pkg.ts"
        pkg.write_text("const opts = { host, rejectUnauthorized: false };\n")
        matches = _scan_file_fingerprints(pkg)
        assert any(m.id == "FP-TLS-VERIFY-002" for m in matches)

    # frob:waive DUP001 reason="parallel vet-rule case table: independent \
    # cases sharing an arrange-act scaffold typical of exhaustive per-rule \
    # coverage; extracting would obscure per-case intent"
    def test_no_match_on_reject_unauthorized_true_node(self, tmp_path: Path) -> None:
        # negative sibling: rejectUnauthorized: true never fires
        # FP-TLS-VERIFY-002.
        # frob:tests src/frob/vet/_capability.py::_scan_file_fingerprints kind="unit"
        from frob.vet._capability import _scan_file_fingerprints

        pkg = tmp_path / "pkg.ts"
        pkg.write_text("const opts = { host, rejectUnauthorized: true };\n")
        matches = _scan_file_fingerprints(pkg)
        assert not any(m.id == "FP-TLS-VERIFY-002" for m in matches)

    # frob:waive DUP001 reason="parallel vet-rule case table: independent \
    # cases sharing an arrange-act scaffold typical of exhaustive per-rule \
    # coverage; extracting would obscure per-case intent"
    def test_matches_tls_danger_accept_invalid_certs_rust(self, tmp_path: Path) -> None:
        # T-0188: FP-TLS-VERIFY-003 -- Rust reqwest danger_accept_invalid_certs.
        # frob:tests src/frob/vet/_capability.py::_scan_file_fingerprints kind="unit"
        from frob.vet._capability import _scan_file_fingerprints

        pkg = tmp_path / "pkg.rs"
        pkg.write_text(
            "let client = Client::builder()"
            ".danger_accept_invalid_certs(true).build()?;\n"
        )
        matches = _scan_file_fingerprints(pkg)
        assert any(m.id == "FP-TLS-VERIFY-003" for m in matches)

    # frob:waive DUP001 reason="parallel vet-rule case table: independent \
    # cases sharing an arrange-act scaffold typical of exhaustive per-rule \
    # coverage; extracting would obscure per-case intent"
    def test_no_match_on_default_reqwest_builder_rust(self, tmp_path: Path) -> None:
        # negative sibling: a builder with no danger_accept_invalid_certs
        # call never fires FP-TLS-VERIFY-003.
        # frob:tests src/frob/vet/_capability.py::_scan_file_fingerprints kind="unit"
        from frob.vet._capability import _scan_file_fingerprints

        pkg = tmp_path / "pkg.rs"
        pkg.write_text("let client = Client::builder().build()?;\n")
        matches = _scan_file_fingerprints(pkg)
        assert not any(m.id == "FP-TLS-VERIFY-003" for m in matches)

    def test_own_catalog_file_excluded_from_directory_aggregation(self) -> None:
        # T-0153 self-match note (docs/strata/threat.md#cve-fingerprints-
        # code-level-pattern-catalog-t-0153): _cve_fingerprint.py stores
        # every needle as literal data, so it must be excluded from
        # _scan_directory_capabilities the same way _capability_registry.py
        # already is.
        # frob:tests src/frob/vet/_capability.py::_is_self_path kind="unit"
        from frob.vet._capability import _FINGERPRINT_CATALOG_PATH, _is_self_path

        repo_root = Path(__file__).resolve().parents[1]
        assert _is_self_path(_FINGERPRINT_CATALOG_PATH, repo_root)

    def test_self_pattern_exclusion_covers_every_needle_table_module(self) -> None:
        # T-0201 drift-lock: a registry-of-pattern-files check. Any module
        # under src/frob/ that DEFINES a literal needle table (a
        # `needles=(...)` catalog-entry call, or a `needles: tuple[str, ...]`
        # pydantic field on a catalog model -- the two literal shapes
        # `_capability_registry.py::DANGEROUS_OPERATIONS` and
        # `_cve_fingerprint.py::CVE_FINGERPRINTS` actually use) is the T-0151
        # self-match class this ticket's root cause traces to: scanning that
        # module's own file "observes" every capability its table stores as
        # data, regardless of what the module's code does. This test fails
        # loudly (a future catalog file must widen `is_self_pattern_path`'s
        # exclusion set, not silently produce fresh SYS100/vet noise like
        # T-0201 did for _cve_fingerprint.py) rather than let a new
        # pattern-table file slip past both join paths unexcluded again.
        # frob:tests src/frob/vet/_capability.py::is_self_pattern_path kind="unit"
        import re

        from frob.vet._capability import (
            _FINGERPRINT_CATALOG_PATH,
            _REGISTRY_PATH,
            _SELF_PATH,
            is_self_pattern_path,
        )

        repo_root = Path(__file__).resolve().parents[1]
        src_root = repo_root / "src" / "frob"
        needle_table_marker = re.compile(r"needles\s*=\s*\(|needles\s*:\s*tuple\[")
        offenders: list[Path] = []
        for path in src_root.rglob("*.py"):
            text = path.read_text(encoding="utf-8", errors="replace")
            if needle_table_marker.search(text) and not is_self_pattern_path(
                path, repo_root
            ):
                offenders.append(path)

        assert offenders == [], (
            f"module(s) define a literal needle table but are not covered by "
            f"is_self_pattern_path: {offenders} -- widen the exclusion set "
            f"in frob.vet._capability"
        )
        # sanity: the exclusion set is exactly the three known catalog/
        # scanner modules, not accidentally empty (which would make the
        # `offenders == []` assertion above vacuously true).
        assert {_SELF_PATH, _REGISTRY_PATH, _FINGERPRINT_CATALOG_PATH} == {
            p.resolve()
            for p in (
                Path(__file__).resolve().parents[1] / "src/frob/vet/_capability.py",
                Path(__file__).resolve().parents[1]
                / "src/frob/vet/_capability_registry.py",
                Path(__file__).resolve().parents[1]
                / "src/frob/strata/_cve_fingerprint.py",
            )
        }

    def test_self_pattern_exclusion_survives_a_foreign_install_copy(
        self, tmp_path: Path
    ) -> None:
        # T-0253 round 0: is_self_pattern_path used to compare the SCANNED
        # path's resolved identity against the RUNNING package's own
        # resolved file paths (_SELF_PATH/_REGISTRY_PATH/
        # _FINGERPRINT_CATALOG_PATH). That only matches when the scanned
        # tree and the running package are literally the same checkout (an
        # editable install run via `uv run frob ...`). Under a non-editable
        # global binary (`uv tool install frob`), the running package's
        # files resolve into a site-packages copy, so scanning frob's OWN
        # repo checkout with that binary self-matched every pattern-catalog
        # needle again (36 false SYS100s).
        #
        # Simulate that split here: build a full fake frob repo root (see
        # `_make_fake_frob_repo_root`) at an unrelated tmp path -- standing
        # in for "the tree being scanned is a frob checkout that is not
        # where the running package lives" -- and confirm the three known
        # pattern files are still recognized/excluded THROUGH the T-0253
        # round-2 discriminator (`root` correctly identifies as frob's own
        # repo because it carries the pyproject-name + crate-dir markers,
        # not because of file identity or suffix alone).
        # frob:tests src/frob/vet/_capability.py::is_self_pattern_path kind="unit"
        from frob.vet._capability import _aggregate_capabilities, is_self_pattern_path

        fake_repo = _make_fake_frob_repo_root(tmp_path / "foreign-install")
        foreign_frob_src = fake_repo / "src" / "frob"

        foreign_capability = foreign_frob_src / "vet" / "_capability.py"
        foreign_registry = foreign_frob_src / "vet" / "_capability_registry.py"
        foreign_fingerprint = foreign_frob_src / "strata" / "_cve_fingerprint.py"
        # the discriminator checks the exact scan root passed in (no
        # ancestor search, see `_make_fake_frob_repo_root`'s docstring), so
        # `root` here must be `fake_repo` itself, the directory that
        # actually carries the pyproject-name + crate-dir markers.
        assert is_self_pattern_path(foreign_capability, fake_repo)
        assert is_self_pattern_path(foreign_registry, fake_repo)
        assert is_self_pattern_path(foreign_fingerprint, fake_repo)

        # end-to-end: scanning starting AT the fake repo root (the scan
        # root the discriminator actually recognizes) must skip all three
        # catalog/scanner files while still walking into src/frob/vet.
        _capabilities, _hit, scanned = _aggregate_capabilities(
            fake_repo, max_files=2000
        )
        scanned_paths = {
            p
            for ext in (".py",)
            for p in fake_repo.rglob(f"*{ext}")
            if not is_self_pattern_path(p, fake_repo)
        }
        assert scanned == len(scanned_paths)
        assert foreign_capability not in scanned_paths
        assert foreign_registry not in scanned_paths

    def test_self_pattern_exclusion_does_not_match_unrelated_same_name_file(
        self, tmp_path: Path
    ) -> None:
        # Narrowness check (T-0253): a third-party dependency that happens
        # to ship its own unrelated `_capability.py` at a DIFFERENT package
        # path must not be excluded just because the filename matches --
        # the suffix match requires all three path components
        # (`frob/vet/_capability.py`), not just the final filename. `root`
        # here is not a frob repo either, so both the discriminator AND the
        # suffix check independently refuse this path.
        # frob:tests src/frob/vet/_capability.py::is_self_pattern_path kind="unit"
        from frob.vet._capability import is_self_pattern_path

        unrelated_root = tmp_path / "some_other_pkg"
        unrelated = unrelated_root / "utils" / "_capability.py"
        unrelated.parent.mkdir(parents=True)
        unrelated.write_text("# not frob's file\n")
        assert not is_self_pattern_path(unrelated, unrelated_root)

    def test_self_pattern_exclusion_does_not_fire_when_vetting_a_dependency(
        self, tmp_path: Path
    ) -> None:
        # T-0253 REJECT-round adversarial test (required by review): a
        # malicious dependency that deliberately reproduces the exact
        # 3-segment suffix (`frob/vet/_capability.py`) under a DIFFERENT,
        # non-frob root must be SCANNED -- not silently excluded -- when
        # `frob vet` scans it as a dependency. The dependency's own root is
        # NOT frob's repo (no pyproject.toml name=="frob", no frob-core/
        # strata-core dirs), so `_is_frob_repo_root` must refuse and the
        # suffix match must never be reached, regardless of how closely the
        # nested path mimics frob's own layout.
        # frob:tests src/frob/vet/_capability.py::is_self_pattern_path kind="unit"
        from frob.vet._capability import (
            _aggregate_capabilities,
            is_self_pattern_path,
            scan_file_capabilities,
        )

        evil_root = tmp_path / "evil-pkg"
        evil_capability = evil_root / "frob" / "vet" / "_capability.py"
        evil_capability.parent.mkdir(parents=True)
        evil_capability.write_text('import os\nos.system("evil")\n')

        # the file itself really does carry a live capability...
        assert "exec" in scan_file_capabilities(evil_capability)
        # ...and the discriminator must refuse the exclusion for this root,
        # even though the path suffix is an exact match for frob's own
        # `_capability.py` layout.
        assert not is_self_pattern_path(evil_capability, evil_root)

        # end-to-end: frob vet's own directory-aggregation entrypoint must
        # actually observe the capability, not silently skip the file.
        capabilities, _hit, scanned = _aggregate_capabilities(evil_root, max_files=500)
        assert scanned == 1
        assert "exec" in capabilities

    def test_scan_directory_fingerprints_aggregates_across_files(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability.py::_scan_directory_fingerprints kind="unit"
        from frob.vet._capability import _scan_directory_fingerprints

        (tmp_path / "a.py").write_text("data = yaml.load(raw_bytes)\n")
        (tmp_path / "b.py").write_text("def add(a, b):\n    return a + b\n")
        matched = _scan_directory_fingerprints(tmp_path)
        assert any(m.id == "FP-DESERIALIZE-YAML-001" for m in matched)

    def test_scan_directory_fingerprints_excludes_the_catalog_itself(
        self, tmp_path: Path
    ) -> None:
        # scanning frob's own src tree must not self-match every fingerprint
        # via _cve_fingerprint.py's own needle literals (self-match note,
        # docs/strata/threat.md#cve-fingerprints-code-level-pattern-catalog-t-0153).
        # T-0253: the exclusion only fires when the scan root itself
        # identifies as frob's own repo (see the sibling capability-scan
        # test above for why); scan from a fake repo root instead of the
        # bare `src/frob/strata` subdirectory.
        # frob:tests src/frob/vet/_capability.py::_scan_directory_fingerprints kind="unit"
        from frob.vet._capability import _scan_directory_fingerprints

        fake_repo = _make_fake_frob_repo_root(tmp_path / "self-scan")
        matched = _scan_directory_fingerprints(fake_repo, max_files=2000)
        assert not any(m.id == "FP-DESERIALIZE-YAML-001" for m in matched)


class TestObfuscationEnsemble:
    def test_high_entropy_string_flagged(self) -> None:
        # frob:tests src/frob/vet/_obfuscation.py::_scan_text_obfuscation kind="unit"
        from frob.vet._obfuscation import _scan_text_obfuscation

        text = 'x = "aGVsbG8gd29ybGQsIHRoaXMgaXMgYSB0ZXN0IHBheWxvYWQ="\n'
        assert "high-entropy-string" in _scan_text_obfuscation(text)

    def test_plain_string_not_flagged(self) -> None:
        from frob.vet._obfuscation import _scan_text_obfuscation

        text = 'greeting = "hello world, this is a normal string literal"\n'
        assert "high-entropy-string" not in _scan_text_obfuscation(text)

    def test_bidi_override_is_fatal(self) -> None:
        # frob:tests src/frob/vet/_obfuscation.py::_invisible_text_signal kind="unit"
        from frob.vet._obfuscation import _invisible_text_signal

        text = "x = 1" + chr(0x202E) + "y = 2"
        assert _invisible_text_signal(text) is True

    def test_clean_text_no_bidi(self) -> None:
        from frob.vet._obfuscation import _invisible_text_signal

        assert _invisible_text_signal("x = 1\ny = 2\n") is False

    def test_hex_identifier_ratio_flagged(self) -> None:
        # frob:tests src/frob/vet/_obfuscation.py::_hex_identifier_ratio_signal kind="unit"
        from frob.vet._obfuscation import _hex_identifier_ratio_signal

        idents = " ".join(f"_0x{i:04x}" for i in range(30))
        assert _hex_identifier_ratio_signal(idents) is True

    def test_normal_identifiers_not_flagged(self) -> None:
        from frob.vet._obfuscation import _hex_identifier_ratio_signal

        idents = " ".join(f"variable_name_{i}" for i in range(30))
        assert _hex_identifier_ratio_signal(idents) is False

    def test_high_entropy_strings_returns_the_literal(self) -> None:
        # frob:tests src/frob/vet/_obfuscation.py::_high_entropy_strings kind="unit"
        from frob.vet._obfuscation import _high_entropy_strings

        text = 'x = "aGVsbG8gd29ybGQsIHRoaXMgaXMgYSB0ZXN0IHBheWxvYWQ="\n'
        hits = _high_entropy_strings(text)
        assert len(hits) == 1
        assert hits[0].startswith("aGVsbG8")

    def test_high_entropy_strings_empty_for_plain_text(self) -> None:
        from frob.vet._obfuscation import _high_entropy_strings

        text = 'greeting = "hello world, this is a normal string literal"\n'
        assert _high_entropy_strings(text) == ()

    def test_scan_directory_obfuscation_finds_signal_in_one_file(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_obfuscation.py::_scan_directory_obfuscation kind="unit"
        from frob.vet._obfuscation import _scan_directory_obfuscation

        (tmp_path / "clean.py").write_text("x = 1\n")
        (tmp_path / "evil.py").write_text(
            'x = "aGVsbG8gd29ybGQsIHRoaXMgaXMgYSB0ZXN0IHBheWxvYWQ="\n'
        )
        signals = _scan_directory_obfuscation(tmp_path)
        assert "high-entropy-string" in signals

    def test_bidi_override_detected_in_c_file(self, tmp_path: Path) -> None:
        # T-0400 audit finding #5: C/C++/Kotlin were entirely excluded from
        # `_SCANNABLE_SUFFIXES`, so the deterministic Trojan-Source bidi
        # scan (CVE-2021-42574, demonstrated in C/C++) never ran on a
        # dependency's .c files at all.
        # frob:tests src/frob/vet/_obfuscation.py::_scan_directory_obfuscation kind="unit"
        from frob.vet._obfuscation import _scan_directory_obfuscation

        rlo = chr(0x202E)
        (tmp_path / "evil.c").write_text(f"// {rlo}nommoc si sti\nint main() {{}}\n")
        signals = _scan_directory_obfuscation(tmp_path)
        assert "invisible-text" in signals

    def test_bidi_override_detected_in_kotlin_file(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_obfuscation.py::_scan_directory_obfuscation kind="unit"
        from frob.vet._obfuscation import _scan_directory_obfuscation

        rlo = chr(0x202E)
        (tmp_path / "Evil.kt").write_text(f"// {rlo}nommoc si sti\nfun main() {{}}\n")
        signals = _scan_directory_obfuscation(tmp_path)
        assert "invisible-text" in signals

    def test_split_string_payload_still_not_detected(self, tmp_path: Path) -> None:
        # Honest documented limitation (T-0400 audit finding #5, NOT
        # closed by this ticket): `_MIN_STRING_LEN` (24) is a PER-LITERAL
        # floor, so a base64 payload split into concatenated pieces each
        # shorter than 24 chars (`"aGVsb" + "G8gd" + ...`) never fires --
        # no single literal is ever long enough to be scored. Closing this
        # needs a real string-concatenation-aware rewrite, out of scope
        # for this pass.
        # frob:tests src/frob/vet/_obfuscation.py::_scan_directory_obfuscation kind="unit"
        from frob.vet._obfuscation import _scan_directory_obfuscation

        pieces = [
            "aGVsb",
            "G8gd2",
            "9ybGQ",
            "sIHRo",
            "aXMgaX",
            "MgYSB0",
            "ZXN0IH",
            "BheWxv",
            "YWQ",
        ]
        joined = " + ".join(f'"{p}"' for p in pieces)
        (tmp_path / "evil.py").write_text(f"x = {joined}\n")
        signals = _scan_directory_obfuscation(tmp_path)
        assert "high-entropy-string" not in signals


class TestVerdictCache:
    def test_store_and_retrieve_latest(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_cache.py::_store_verdict kind="unit"
        # frob:tests src/frob/vet/_cache.py::_latest_verdict kind="unit"
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
        _cache._store_verdict(db_path, v1)
        latest = _cache._latest_verdict(db_path, "pypi", "foo")
        assert latest is not None
        assert latest.artifact_hash == "hash1"
        assert latest.capabilities == frozenset({"net"})

    def test_missing_cache_returns_none(self, tmp_path: Path) -> None:
        from frob.vet import _cache

        assert (
            _cache._latest_verdict(tmp_path / ".frob" / "vet.db", "pypi", "nope")
            is None
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
    def test_python_setup_py_cmdclass_flagged(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_ecosystem.py::_python_rules kind="unit"
        from frob.gates._models import Severity
        from frob.vet import _ecosystem

        (tmp_path / "setup.py").write_text(
            "from setuptools import setup\nsetup(cmdclass={'install': Foo})\n"
        )
        dep = Dependency(ecosystem="pypi", name="evilpkg", version="1.0.0")
        violations = _ecosystem._python_rules(dep, tmp_path, "uv.lock")
        rules = {v.rule for v in violations}
        assert "VET-PY001" in rules
        assert any(
            v.severity is Severity.ERROR for v in violations if v.rule == "VET-PY001"
        )

    def test_python_pth_file_flagged(self, tmp_path: Path) -> None:
        from frob.vet import _ecosystem

        (tmp_path / "evil.pth").write_text("import os; os.system('echo hi')\n")
        dep = Dependency(ecosystem="pypi", name="evilpkg", version="1.0.0")
        violations = _ecosystem._python_rules(dep, tmp_path, "uv.lock")
        assert any(v.rule == "VET-PY002" for v in violations)

    def test_rust_build_rs_capability_flagged(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_ecosystem.py::_rust_rules kind="unit"
        from frob.vet import _ecosystem

        (tmp_path / "build.rs").write_text(
            'fn main() { std::process::Command::new("curl"); }\n'
        )
        dep = Dependency(ecosystem="cargo", name="evilcrate", version="1.0.0")
        violations = _ecosystem._rust_rules(dep, tmp_path, "Cargo.lock")
        assert any(v.rule == "VET-RS001" for v in violations)

    def test_npm_non_registry_source_flagged(self) -> None:
        # frob:tests src/frob/vet/_ecosystem.py::_npm_non_registry_rule kind="unit"
        from frob.vet import _ecosystem

        dep = Dependency(
            ecosystem="npm",
            name="evilpkg",
            version="1.0.0",
            resolved="git+https://example.com/evil/evilpkg.git",
        )
        violation = _ecosystem._npm_non_registry_rule(dep, "package-lock.json")
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
        violation = _ecosystem._npm_non_registry_rule(dep, "package-lock.json")
        assert violation is None


class TestScanTreeLockArg:
    def test_scan_tree_lockfile_arg(self, tmp_path: Path) -> None:
        """T-0221 regression: `scan_tree(<path to a lockfile file>)` must vet
        that lockfile, not treat it as a directory root and fail to find
        anything under it."""
        from frob.vet._scan import scan_tree

        lockfile = tmp_path / "uv.lock"
        lockfile.write_text(UV_LOCK)

        result = scan_tree(lockfile, fetch=False)
        assert result.is_ok
        report = result.danger_ok
        assert len(report.verdicts) == 2

    def test_scan_tree_unsupp_err(self, tmp_path: Path) -> None:
        """T-0221 regression: an unresolvable lockfile is a typed Err, not a
        silent empty-ok report -- callers (the CLI) rely on this to exit
        nonzero rather than gate-poisoning with a vacuous pass."""
        from frob.vet._models import VetError
        from frob.vet._scan import scan_tree

        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        result = scan_tree(empty_dir, fetch=False)
        assert result.is_err
        assert result.danger_err is VetError.LockfileUnsupported


class TestVetRunnerLockArg:
    def test_run_lockfile_arg(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """T-0221 regression: `frob vet <path/to/uv.lock>` (CLI entry point)
        vets that lockfile rather than misreading the path as a directory
        root and reporting no supported lockfile."""
        from frob.app.config import AppConfig
        from frob.app.vet_runner import run

        lockfile = tmp_path / "uv.lock"
        lockfile.write_text(UV_LOCK)

        cfg = AppConfig(vet_path=lockfile)
        with pytest.raises(SystemExit) as exc_info:
            run(cfg)
        assert exc_info.value.code == 0
        out = capsys.readouterr().out
        assert "requests" in out

    def test_run_unsupp_nonzero(self, tmp_path: Path) -> None:
        """T-0221 regression: a LockfileUnsupported Err must not be a silent
        exit-0 -- that is the same vacuous-pass class as T-0184 and poisons
        any gate relying on `frob vet`'s exit code."""
        from frob.app.config import AppConfig
        from frob.app.vet_runner import run

        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        cfg = AppConfig(vet_path=empty_dir)
        with pytest.raises(SystemExit) as exc_info:
            run(cfg)
        assert exc_info.value.code != 0


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

    def test_scan_tree_surfaces_a_cve_fingerprint_finding(self, tmp_path: Path) -> None:
        # T-0153: a dependency whose source contains a fingerprinted
        # vulnerable-usage pattern (here, FP-DESERIALIZE-YAML-001's
        # yaml.load() needle) must surface a VET006 finding through the
        # REAL `frob vet` pipeline (scan_tree), not just via a direct
        # _scan_file_fingerprints import -- proving the wiring, not just
        # the detector.
        # frob:tests src/frob/vet/_scan.py::_scan_source kind="unit"
        from frob.vet._scan import scan_tree

        (tmp_path / "uv.lock").write_text(
            '[[package]]\nname = "sketchy-pkg"\nversion = "1.0.0"\n'
        )
        pkg_dir = (
            tmp_path / ".venv" / "lib" / "python3.11" / "site-packages" / "sketchy_pkg"
        )
        pkg_dir.mkdir(parents=True)
        (pkg_dir / "__init__.py").write_text(
            "import yaml\n\ndef load_config(raw):\n    return yaml.load(raw)\n"
        )
        (tmp_path / "frob.toml").write_text(
            "[vet]\nenforce = true\n\n[vet.allow]\nsketchy-pkg = true\n"
        )

        result = scan_tree(tmp_path, fetch=False)
        assert result.is_ok
        report = result.danger_ok
        fp_violations = [v for v in report.violations if v.rule == "VET006"]
        assert fp_violations
        assert "FP-DESERIALIZE-YAML-001" in fp_violations[0].message
        verdict = next(v for v in report.verdicts if v.name == "sketchy-pkg")
        assert "cve-fingerprint" in verdict.signals


class TestScanTreeSourceUnavailableFailClosed:
    """T-0400 audit finding #1: a dependency whose source is not present
    locally used to be silently APPROVED (empty capability set, zero
    violations) -- indistinguishable from "checked and clean". This is now
    a fail-closed VET-SOURCE-UNAVAILABLE ERROR finding."""

    def test_missing_source_surfaces_error_violation(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_scan.py::_scan_located_source kind="unit"
        from frob.gates._models import Severity
        from frob.vet._scan import scan_tree

        (tmp_path / "uv.lock").write_text(
            '[[package]]\nname = "unfetched-pkg"\nversion = "1.0.0"\n'
        )
        # No .venv/site-packages entry for unfetched-pkg -- source is
        # genuinely not present locally.
        (tmp_path / "frob.toml").write_text(
            "[vet]\nenforce = true\n\n[vet.allow]\nunfetched-pkg = true\n"
        )

        result = scan_tree(tmp_path, fetch=False)
        assert result.is_ok
        report = result.danger_ok
        source_violations = [
            v for v in report.violations if v.rule == "VET-SOURCE-UNAVAILABLE"
        ]
        assert len(source_violations) == 1
        assert source_violations[0].severity is Severity.ERROR
        assert "unfetched-pkg" in source_violations[0].message
        verdict = next(v for v in report.verdicts if v.name == "unfetched-pkg")
        assert "source-unavailable" in verdict.signals
        assert verdict.capabilities == frozenset()

    def test_enforced_missing_source_fails_the_gate(self, tmp_path: Path) -> None:
        # The whole point of fail-closed: `enforce = true` + an
        # ERROR-severity VET-SOURCE-UNAVAILABLE must make the report
        # non-passing via the same enforce/ERROR contract every other
        # vet rule uses.
        from frob.gates._models import Severity
        from frob.vet._scan import scan_tree

        (tmp_path / "uv.lock").write_text(
            '[[package]]\nname = "unfetched-pkg"\nversion = "1.0.0"\n'
        )
        (tmp_path / "frob.toml").write_text(
            "[vet]\nenforce = true\n\n[vet.allow]\nunfetched-pkg = true\n"
        )

        result = scan_tree(tmp_path, fetch=False)
        assert result.is_ok
        report = result.danger_ok
        assert report.enforce is True
        assert any(v.severity is Severity.ERROR for v in report.violations)


class TestScanTreeMultipleLockfiles:
    """T-0400 audit finding #2: a repo with more than one supported
    lockfile used to have every lockfile after the first silently
    unscanned."""

    def test_scan_tree_scans_every_lockfile(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_scan.py::scan_tree kind="unit"
        from frob.vet._scan import scan_tree

        (tmp_path / "uv.lock").write_text(UV_LOCK)
        (tmp_path / "package-lock.json").write_text(PACKAGE_LOCK_JSON_V3)

        result = scan_tree(tmp_path, fetch=False)
        assert result.is_ok
        report = result.danger_ok
        names = {v.name for v in report.verdicts}
        # uv.lock's pypi deps (requests + one other) AND package-lock.json's
        # npm deps (lodash, chalk) must all be represented -- the old
        # first-lockfile-only search would have dropped lodash/chalk
        # entirely.
        assert "requests" in names
        assert "lodash" in names
        assert "chalk" in names


class TestScanTreeTimeout:
    # frob:tests src/frob/vet/_scan.py::_run_with_timeout kind="unit"
    def test_slow_package_returns_within_timeout_not_task_duration(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-0208 review round 1: a naive `with ThreadPoolExecutor(...)`
        around the timeout-bound call blocks in `__exit__` (shutdown(wait=
        True)) until the abandoned task finishes, silently defeating the
        timeout -- only the verdict label would change, wall time would
        not. Assert an upper bound on wall time (a few multiples of the
        configured timeout, well under the task's real 3s duration) so a
        regression back to that shape is caught by a measurement, not an
        inspection."""
        import time

        from frob.vet import _scan

        (tmp_path / "uv.lock").write_text(
            '[[package]]\nname = "slow-pkg"\nversion = "1.0.0"\n'
        )
        (tmp_path / "frob.toml").write_text(
            "[vet]\nenforce = true\n\n[vet.allow]\nslow-pkg = true\n"
        )

        def _slow_process_dependency(*args, **kwargs):
            time.sleep(3.0)
            raise AssertionError("should have been abandoned at the timeout")

        monkeypatch.setattr(_scan, "_process_dependency", _slow_process_dependency)

        t0 = time.monotonic()
        result = _scan.scan_tree(tmp_path, fetch=False, timeout=0.2)
        elapsed = time.monotonic() - t0

        assert result.is_ok
        assert elapsed < 1.5, (
            f"scan_tree took {elapsed:.2f}s with timeout=0.2 -- "
            f"the timeout is not actually bounding wall time"
        )
        report = result.danger_ok
        assert any(v.rule == "VET-TIMEOUT" for v in report.violations)
        verdict = next(v for v in report.verdicts if v.name == "slow-pkg")
        assert "timeout" in verdict.signals


# ---------------------------------------------------------------------------
# lifecycle scripts
# ---------------------------------------------------------------------------


class TestLifecycleScripts:
    def test_finds_postinstall_script(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_lifecycle.py::_scan_lifecycle_scripts kind="unit"
        from frob.vet._lifecycle import _scan_lifecycle_scripts

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
        found = _scan_lifecycle_scripts(tmp_path)
        assert found == {"sketchy-pkg": ("postinstall",)}

    def test_no_node_modules_returns_empty(self, tmp_path: Path) -> None:
        from frob.vet._lifecycle import _scan_lifecycle_scripts

        assert _scan_lifecycle_scripts(tmp_path) == {}


# ---------------------------------------------------------------------------
# osv-scanner adapter
# ---------------------------------------------------------------------------


class TestOsvAdapter:
    def test_is_available_reflects_path_lookup(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/vet/_osv.py::_is_available kind="unit"
        from frob.vet import _osv

        monkeypatch.setattr(
            _osv.shutil, "which", lambda _binary: "/usr/bin/osv-scanner"
        )
        assert _osv._is_available() is True

        monkeypatch.setattr(_osv.shutil, "which", lambda _binary: None)
        assert _osv._is_available() is False

    def test_run_osv_scan_none_when_binary_absent(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/vet/_osv.py::_run_osv_scan kind="unit"
        from frob.vet import _osv

        monkeypatch.setattr(_osv.shutil, "which", lambda _binary: None)
        lockfile = tmp_path / "uv.lock"
        lockfile.write_text("version = 1\n")
        assert _osv._run_osv_scan(lockfile) is None


# ---------------------------------------------------------------------------
# registry publish-date lookups
# ---------------------------------------------------------------------------


class TestRegistryLookup:
    def test_fetch_publish_date_degrades_on_network_failure(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_registry.py::_fetch_publish_date kind="unit"
        from frob.vet._registry import _fetch_publish_date

        result = _fetch_publish_date(
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
        # frob:tests src/frob/vet/_source.py::_locate_pypi_source kind="unit"
        from frob.vet._source import _locate_pypi_source

        site_packages = tmp_path / ".venv" / "lib" / "python3.11" / "site-packages"
        pkg_dir = site_packages / "some_pkg"
        pkg_dir.mkdir(parents=True)
        found = _locate_pypi_source(tmp_path, "some-pkg", "1.0.0")
        assert found == pkg_dir

    def test_locate_pypi_source_missing_returns_none(self, tmp_path: Path) -> None:
        from frob.vet._source import _locate_pypi_source

        assert _locate_pypi_source(tmp_path, "totally-absent-pkg", "1.0.0") is None

    def test_locate_npm_source_from_node_modules(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_source.py::_locate_npm_source kind="unit"
        from frob.vet._source import _locate_npm_source

        pkg_dir = tmp_path / "node_modules" / "lodash"
        pkg_dir.mkdir(parents=True)
        assert _locate_npm_source(tmp_path, "lodash") == pkg_dir

    def test_locate_npm_source_missing_returns_none(self, tmp_path: Path) -> None:
        from frob.vet._source import _locate_npm_source

        assert _locate_npm_source(tmp_path, "not-installed") is None

    def test_locate_cargo_source_missing_registry_returns_none(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/vet/_source.py::_locate_cargo_source kind="unit"
        from frob.vet._source import _locate_cargo_source

        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        assert _locate_cargo_source("serde", "1.0.195") is None

    def test_locate_source_dispatches_by_ecosystem(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_source.py::_locate_source kind="unit"
        from frob.vet._source import _locate_source

        pkg_dir = tmp_path / "node_modules" / "lodash"
        pkg_dir.mkdir(parents=True)
        assert _locate_source(tmp_path, "npm", "lodash", "4.17.21") == pkg_dir
        assert _locate_source(tmp_path, "unknown-ecosystem", "x", "1.0.0") is None


class TestClosedWorldAccounting:
    """T-0158 addendum 2 remainder / T-0180: closed-world import
    accounting -- every import resolves to registry/no-capability/vetted,
    or the loud unknown fallthrough."""

    def _site_packages(self, tmp_path: Path) -> Path:
        site_packages = tmp_path / ".venv" / "lib" / "python3.11" / "site-packages"
        site_packages.mkdir(parents=True)
        return site_packages

    def test_walk_python_imports_collects_absolute_imports_only(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_closedworld.py::walk_python_imports kind="unit"
        from frob.vet._closedworld import walk_python_imports

        pkg_dir = tmp_path / "some_pkg"
        pkg_dir.mkdir()
        (pkg_dir / "__init__.py").write_text(
            "import os\n"
            "import requests.sessions\n"
            "from json import loads\n"
            "from . import helper\n"
            "from .sub import thing\n"
        )
        roots = walk_python_imports(pkg_dir)
        assert roots == frozenset({"os", "requests", "json"})

    def test_walk_python_imports_skips_unparseable_files(self, tmp_path: Path) -> None:
        from frob.vet._closedworld import walk_python_imports

        pkg_dir = tmp_path / "broken_pkg"
        pkg_dir.mkdir()
        (pkg_dir / "good.py").write_text("import sys\n")
        (pkg_dir / "bad.py").write_text("def f(:\n  this is not python\n")
        assert walk_python_imports(pkg_dir) == frozenset({"sys"})

    # frob:waive DUP001 reason="parallel vet-rule case table: independent \
    # cases sharing an arrange-act scaffold typical of exhaustive per-rule \
    # coverage; extracting would obscure per-case intent"
    def test_resolve_import_registry_match(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_closedworld.py::resolve_import kind="unit"
        from frob.vet._closedworld import resolve_import

        result = resolve_import(
            "subprocess", root=tmp_path, cache_path=tmp_path / ".frob" / "vet.db"
        )
        assert result.resolution == "registry"

    # frob:waive DUP001 reason="parallel vet-rule case table: independent \
    # cases sharing an arrange-act scaffold typical of exhaustive per-rule \
    # coverage; extracting would obscure per-case intent"
    def test_resolve_import_registry_match_via_pypi_name_override(
        self, tmp_path: Path
    ) -> None:
        # python-dotenv's DANGEROUS_OPERATIONS library field is the PyPI
        # distribution name "python-dotenv", not the import root "dotenv" --
        # the override table must bridge that.
        from frob.vet._closedworld import resolve_import

        result = resolve_import(
            "dotenv", root=tmp_path, cache_path=tmp_path / ".frob" / "vet.db"
        )
        assert result.resolution == "registry"

    # frob:waive DUP001 reason="parallel vet-rule case table: independent \
    # cases sharing an arrange-act scaffold typical of exhaustive per-rule \
    # coverage; extracting would obscure per-case intent"
    def test_resolve_import_no_capability_match(self, tmp_path: Path) -> None:
        from frob.vet._closedworld import resolve_import

        result = resolve_import(
            "collections", root=tmp_path, cache_path=tmp_path / ".frob" / "vet.db"
        )
        assert result.resolution == "no-capability"

    def test_resolve_import_vetted_via_local_source_scan_and_cache(
        self, tmp_path: Path
    ) -> None:
        site_packages = self._site_packages(tmp_path)
        dep_dir = site_packages / "leaf_dep"
        dep_dir.mkdir()
        (dep_dir / "__init__.py").write_text("import subprocess\n")

        cache_path = tmp_path / ".frob" / "vet.db"
        from frob.vet._cache import _latest_verdict
        from frob.vet._closedworld import resolve_import

        result = resolve_import("leaf_dep", root=tmp_path, cache_path=cache_path)
        assert result.resolution == "vetted"
        # second call must hit the cache, not rescan
        cached = _latest_verdict(cache_path, "pypi", "leaf_dep")
        assert cached is not None
        result2 = resolve_import("leaf_dep", root=tmp_path, cache_path=cache_path)
        assert result2.resolution == "vetted"
        assert result2.detail.startswith("cached verdict")

    def test_resolve_import_unknown_when_unresolvable(self, tmp_path: Path) -> None:
        from frob.vet._closedworld import resolve_import

        result = resolve_import(
            "totally_unresolvable_pkg_xyz",
            root=tmp_path,
            cache_path=tmp_path / ".frob" / "vet.db",
        )
        assert result.resolution == "unknown"

    def test_closed_world_accounting_source_unavailable(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_closedworld.py::closed_world_accounting kind="unit"
        from frob.vet._closedworld import closed_world_accounting

        acc = closed_world_accounting(
            tmp_path,
            "pypi",
            "no-such-package",
            "1.0.0",
            cache_path=tmp_path / ".frob" / "vet.db",
        )
        assert acc.source_available is False
        assert acc.resolutions == ()
        assert acc.closed is False
        assert "source unavailable" in acc.accounting_line()

    # frob:tests src/frob/vet/_models.py::ClosedWorldAccounting.registry_count kind="unit"
    # frob:tests src/frob/vet/_models.py::ClosedWorldAccounting.no_capability_count kind="unit"
    # frob:tests src/frob/vet/_models.py::ClosedWorldAccounting.vetted_count kind="unit"
    # frob:tests src/frob/vet/_models.py::ClosedWorldAccounting.unknown_count kind="unit"
    # frob:tests src/frob/vet/_models.py::ClosedWorldAccounting.accounting_line kind="unit"
    def test_closed_world_accounting_full_pass(self, tmp_path: Path) -> None:
        site_packages = self._site_packages(tmp_path)
        pkg_dir = site_packages / "top_pkg"
        pkg_dir.mkdir()
        (pkg_dir / "__init__.py").write_text(
            "import subprocess\n"
            "import collections\n"
            "import totally_unresolvable_pkg_xyz\n"
        )

        from frob.vet._closedworld import closed_world_accounting

        acc = closed_world_accounting(
            tmp_path,
            "pypi",
            "top_pkg",
            "1.0.0",
            cache_path=tmp_path / ".frob" / "vet.db",
        )
        assert acc.source_available is True
        assert acc.registry_count == 1
        assert acc.no_capability_count == 1
        assert acc.unknown_count == 1
        assert acc.closed is False
        assert "1 registry op(s)" in acc.accounting_line()
        assert "1 unknown" in acc.accounting_line()

    # frob:tests src/frob/vet/_models.py::ClosedWorldAccounting.closed kind="unit"
    def test_closed_world_accounting_closed_when_no_unknowns(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_models.py::ClosedWorldAccounting kind="unit"
        site_packages = self._site_packages(tmp_path)
        pkg_dir = site_packages / "clean_pkg"
        pkg_dir.mkdir()
        (pkg_dir / "__init__.py").write_text("import subprocess\nimport collections\n")

        from frob.vet._closedworld import closed_world_accounting

        acc = closed_world_accounting(
            tmp_path,
            "pypi",
            "clean_pkg",
            "1.0.0",
            cache_path=tmp_path / ".frob" / "vet.db",
        )
        assert acc.unknown_count == 0
        assert acc.closed is True

    def test_import_resolution_model_fields(self) -> None:
        # frob:tests src/frob/vet/_models.py::ImportResolution kind="unit"
        from frob.vet._models import ImportResolution

        r = ImportResolution(import_name="os", resolution="no-capability")
        assert r.import_name == "os"
        assert r.resolution == "no-capability"
        assert r.detail == ""

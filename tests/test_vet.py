"""Unit tests for frob.vet: lockfile parsers, allow conformance, quarantine,
typosquat, and hook-command parsing (docs/modules/vet.md). No real network calls."""

# frob:waive OPAQUE001 reason="T-1038: the eval text below is fixture STRING LITERAL \
# data this file's own tests feed into frob.vet's scanners to prove they fire on it -- \
# never an actual eval() call in this file"

from __future__ import annotations

import json
import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest import mock

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

    def test_typosquat_name_blocked_before_any_registry_lookup(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/vet/_hook.py::check_package kind="unit"
        # T-1294: pins the typosquat branch of check_package -- a name one
        # edit-distance from a popular pypi package must be blocked as
        # "typosquat" WITHOUT ever reaching the registry publish-date
        # lookup (proven here by making that lookup explode if called).
        from frob.vet import _registry

        def fail_if_called(*args, **kwargs):
            raise AssertionError(
                "registry lookup must not run once a typosquat is found"
            )

        monkeypatch.setattr(_registry, "_fetch_publish_date", fail_if_called)
        verdict = check_package("pypi", "reqeusts", "1.0.0", root=tmp_path)
        assert verdict.verdict == "typosquat"
        assert verdict.blocked is True
        assert "requests" in verdict.message


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
        assert "net-connect" in capabilities

    def test_rust_exec_detected(self, tmp_path: Path) -> None:
        from frob.vet._capability import scan_file_capabilities

        build_rs = tmp_path / "build.rs"
        build_rs.write_text('fn main() { std::process::Command::new("sh"); }\n')
        capabilities = scan_file_capabilities(build_rs)
        assert "exec" in capabilities

    def test_kotlin_net_okhttp_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # T-0170: OkHttp is the dominant Android HTTP client -- one of the
        # per-cell fire fixtures for the new kotlin column.
        from frob.vet._capability import scan_file_capabilities

        kt = tmp_path / "Client.kt"
        kt.write_text(
            "import okhttp3.OkHttpClient\nfun makeClient() = OkHttpClient()\n"
        )
        assert "net-connect" in scan_file_capabilities(kt)

    def test_kotlin_exec_runtime_exec_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        from frob.vet._capability import scan_file_capabilities

        kt = tmp_path / "Shell.kt"
        kt.write_text("fun run(cmd: String) {\n    Runtime.getRuntime().exec(cmd)\n}\n")
        assert "exec" in scan_file_capabilities(kt)

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
        assert "net-connect" in scan_file_capabilities(c_file)

    def test_decode_to_exec_same_function(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::_decode_to_exec_signal \
        # kind="unit"
        from frob.vet._capability_scan import _decode_to_exec_signal

        pkg = tmp_path / "pkg.py"
        pkg.write_text(
            "import base64\n"
            "def run(payload):\n"
            "    data = base64.b64decode(payload)\n"
            "    exec(data)\n"
        )
        assert _decode_to_exec_signal(pkg) is True

    def test_decode_to_exec_absent_when_separate(self, tmp_path: Path) -> None:
        from frob.vet._capability_scan import _decode_to_exec_signal

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
        # frob:tests src/frob/vet/_capability_scan.py::_scan_directory_capabilities \
        # kind="unit"
        from frob.vet._capability_scan import _scan_directory_capabilities

        (tmp_path / "a.py").write_text("import subprocess\nsubprocess.run(['ls'])\n")
        (tmp_path / "b.py").write_text("import requests\nrequests.get('x')\n")
        capabilities, decode_to_exec_hit = _scan_directory_capabilities(tmp_path)
        assert "exec" in capabilities
        assert "net-connect" in capabilities
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
        assert "net-connect" in scan_file_capabilities(pkg)

    def test_docstring_query_does_not_treat_enum_value_as_docstring(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability_core.py::_docstring_byte_spans_from_tree kind="unit"  # noqa: E501
        # T-1223: `_docstring_byte_spans_from_tree`'s tree-sitter Query
        # source matches the `expression_statement` SUPERTYPE, which also
        # conforms `assignment` nodes -- an ErrorSet-style class whose first
        # body statement is `NAME = "a string value"` must NOT be treated as
        # a class docstring (`_PY_DOC_CAPTURE_FILTER`'s parent-type check is
        # the fix; this reproduces the exact false-positive shape observed
        # against this repo's own `src/frob/exports/__init__.py`). A needle
        # written only inside that enum value must still fire as real code,
        # not be silently swallowed as if it were prose.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "errs.py"
        pkg.write_text(
            "from typani import ErrorSet\n\n\n"
            "class MyError(ErrorSet):\n"
            '    Bad = "subprocess.Popen(cmd)"\n'
        )
        assert "exec" in scan_file_capabilities(pkg)

    def test_docstring_query_still_finds_real_docstrings(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_core.py::_docstring_byte_spans_from_tree kind="unit"  # noqa: E501
        # T-1223 sibling of the enum-value regression test above: a genuine
        # module/class/function docstring containing the same needle must
        # still be excluded, exercising all three Query anchor patterns
        # (module, class body, function body) in one file.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "docs.py"
        pkg.write_text(
            '"""module doc: subprocess.Popen(cmd) is forbidden here."""\n\n\n'
            "class C:\n"
            '    """class doc: subprocess.Popen(cmd) too."""\n\n'
            "    def m(self):\n"
            '        """method doc: subprocess.Popen(cmd) as well."""\n'
            "        pass\n"
        )
        assert "exec" not in scan_file_capabilities(pkg)

    def test_string_literal_needle_still_fires(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # T-0209: only COMMENT spans are filtered -- a needle inside a string
        # literal (not a comment) is deliberately left unfiltered (module
        # docstring's T-0209 note: distinguishing exec-vector strings from
        # prose strings needs per-registry judgment this scanner lacks).
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "stringy.py"
        pkg.write_text("cmd = 'requests.get(\"http://x\")'\n")
        assert "net-connect" in scan_file_capabilities(pkg)

    def test_capability_module_self_scan_documented_false_positive(self) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # T-0151: the capability scanner's own source stores every needle as
        # literal string data, so scanning IT directly (not via directory
        # aggregation) still shows the accepted false-positive class
        # documented in the module docstring and docs/modules/vet.md -- this
        # locks that decision so a future "fix" doesn't silently change the
        # behavior either way.
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
        #
        # T-1420 (portion 5): `_has_bare_compile_call` (and the rest of the
        # scanner-core primitives) moved to `_capability_core.py` in the
        # LARGE001 split -- the self-match now shows up scanning THAT file,
        # not the (now much smaller) `_capability.py` dispatcher, which no
        # longer carries this literal at all.
        from frob.vet._capability import scan_file_capabilities

        own_path = (
            Path(__file__).resolve().parents[1]
            / "src"
            / "frob"
            / "vet"
            / "_capability_core.py"
        )
        capabilities = scan_file_capabilities(own_path)
        assert "eval" in capabilities  # b"compile(" appears as real code data
        assert "install-hook" not in capabilities  # T-0769: was docstring-only

    def test_scan_directory_capabilities_excludes_own_module(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::_scan_directory_capabilities \
        # kind="unit"
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
        from frob.vet._capability_scan import _scan_directory_capabilities

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
        assert "env-read" in scan_file_capabilities(pkg)


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


class TestCapabilityScanTaxonomyClosureResolution:
    """T-0659: closes the remaining Python static-resolvable gaps against
    docs/design/capability-evasion-taxonomy.md's denominator that T-0328/
    T-0337 left open -- chained assignment, tuple/starred destructuring,
    default-argument forwarding, attribute-target rebinding, star-import
    re-export (for a curated dangerous module), and order-independent
    conditional/try-except import-fallback aliasing. Every evasion case
    below is now DETECTED; the accompanying no-regression cases (a benign
    destructuring bind, a safe-only fallback) stay silent, matching the
    T-0328 no-false-positive posture."""

    def test_chained_assignment_outer_target_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # `a = b = subprocess.run; a(x)` -- taxonomy "chained assignment".
        # The OUTER target (`a`) previously saw its RHS as an unresolvable
        # nested `assignment` node and gave up; `_resolve_py_expr` now
        # peels through it.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.py"
        pkg.write_text("import subprocess\na = b = subprocess.run\na(['x'])\n")
        assert "exec" in scan_file_capabilities(pkg)

    def test_chained_assignment_inner_target_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # Same source, calling through the INNER target (`b`) instead --
        # already worked pre-T-0659 (the plain single-assignment path), a
        # regression guard alongside the outer-target fix above.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.py"
        pkg.write_text("import subprocess\na = b = subprocess.run\nb(['x'])\n")
        assert "exec" in scan_file_capabilities(pkg)

    def test_tuple_unpack_destructuring_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # `f, g = subprocess.run, os.system; f(x)` -- taxonomy "tuple/list
        # unpacking bind", positional correspondence over the RHS literal.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.py"
        pkg.write_text(
            "import subprocess, os\nf, g = subprocess.run, os.system\nf(['x'])\n"
        )
        assert "exec" in scan_file_capabilities(pkg)

    def test_tuple_unpack_second_element_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # Same source, calling through the SECOND unpacked name -- proves
        # positional correspondence, not "first name always wins".
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.py"
        pkg.write_text(
            "import subprocess, os\nf, g = subprocess.run, os.system\ng('x')\n"
        )
        assert "exec" in scan_file_capabilities(pkg)

    def test_starred_unpack_leading_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # `f, *rest = [subprocess.run]; f(x)` -- taxonomy "starred
        # unpacking bind"; `f` binds to the FIRST element regardless of how
        # many trailing elements the splat swallows.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.py"
        pkg.write_text("import subprocess\nf, *rest = [subprocess.run]\nf(['x'])\n")
        assert "exec" in scan_file_capabilities(pkg)

    def test_starred_unpack_trailing_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # `*rest, g = [1, subprocess.run]; g(x)` -- the splat-BEFORE case,
        # binding from the back of the sequence.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.py"
        pkg.write_text("import subprocess\n*rest, g = [1, subprocess.run]\ng(['x'])\n")
        assert "exec" in scan_file_capabilities(pkg)

    def test_benign_destructuring_not_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # No-false-positive guard: a destructuring bind whose RHS elements
        # are not resolvable (two lambdas) must stay silent.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.py"
        pkg.write_text("f, g = (lambda: 1), (lambda: 2)\nf()\n")
        assert "exec" not in scan_file_capabilities(pkg)

    def test_default_arg_forwarding_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # `def h(cb=subprocess.run): cb(x)` -- taxonomy "default-arg
        # forwarding a callable".
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.py"
        pkg.write_text("import subprocess\ndef h(cb=subprocess.run):\n    cb(['x'])\n")
        assert "exec" in scan_file_capabilities(pkg)

    def test_attribute_target_rebind_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # `mod.run = subprocess.run; mod.run(x)` -- taxonomy "attribute
        # rebinding" (best-effort, by-name object identity, documented on
        # `_attr_rebind_lookup`).
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.py"
        pkg.write_text(
            "import subprocess\n"
            "class Mod:\n    pass\n"
            "mod = Mod()\n"
            "mod.run = subprocess.run\n"
            "mod.run(['x'])\n"
        )
        assert "exec" in scan_file_capabilities(pkg)

    def test_star_import_reexport_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # `from subprocess import *; run(x)` -- taxonomy "star-import
        # re-export chain", best-effort for a module `DANGEROUS_OPERATIONS`
        # curates (subprocess).
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.py"
        pkg.write_text("from subprocess import *\nrun(['x'])\n")
        assert "exec" in scan_file_capabilities(pkg)

    def test_star_import_untracked_module_not_claimed(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # No-false-positive/no-overclaim guard: a wildcard import of a
        # module NOT in `DANGEROUS_OPERATIONS` gets no best-effort binding
        # at all -- a bare `run(x)` with no matching import anywhere stays
        # silent (documented honest limitation, not a false resolution).
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.py"
        pkg.write_text("from some_untracked_pkg import *\nrun(['x'])\n")
        assert "exec" not in scan_file_capabilities(pkg)

    def test_conditional_import_fallback_dangerous_first_detected(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # taxonomy "conditional/try-except import fallback aliasing":
        # dangerous import in the `try` branch, benign fallback in
        # `except` -- the LATER (benign) binding must not silently
        # overwrite the dangerous one in the import table.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.py"
        pkg.write_text(
            "try:\n"
            "    from os import system as run\n"
            "except ImportError:\n"
            "    from shlex import quote as run\n"
            "run('x')\n"
        )
        assert "exec" in scan_file_capabilities(pkg)

    def test_conditional_import_fallback_dangerous_second_detected(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # Same construct with the branches swapped -- dangerous import
        # walked SECOND, proving the fix is order-independent, not just
        # "first wins" or "last wins" by coincidence of tree-walk order.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.py"
        pkg.write_text(
            "try:\n"
            "    from shlex import quote as run\n"
            "except ImportError:\n"
            "    from os import system as run\n"
            "run('x')\n"
        )
        assert "exec" in scan_file_capabilities(pkg)

    def test_conditional_import_fallback_both_safe_not_detected(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # No-false-positive guard: both fallback branches benign must stay
        # silent.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.py"
        pkg.write_text(
            "try:\n"
            "    from shlex import quote as run\n"
            "except ImportError:\n"
            "    from textwrap import shorten as run\n"
            "run('x')\n"
        )
        assert "exec" not in scan_file_capabilities(pkg)

    def test_closure_capture_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # T-0666: taxonomy "closure capture" row (Lang Ref 4.2 Naming and
        # binding): `def outer(): r = subprocess.run; def inner(): r(x);
        # return inner` -- the inner function's call to `r` must resolve
        # through the enclosing function's local binding.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.py"
        pkg.write_text(
            "import subprocess\n"
            "def outer():\n"
            "    r = subprocess.run\n"
            "    def inner():\n"
            "        r(['ls'])\n"
            "    return inner\n"
        )
        assert "exec" in scan_file_capabilities(pkg)

    def test_with_as_binding_a_callable_bearing_object_detected(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # T-0666: taxonomy "`as` in `with`/`except` binding a callable-
        # bearing object" row (Lang Ref 8.5 The with statement): the `as`
        # target of a `with` statement is part of the same bind family as
        # ordinary assignment -- `with open('x') as f: pass` is benign, but
        # `with contextlib.suppress(Exception) as e: r = e; r2 = getattr(e,
        # 'run', None)` illustrates the pattern is a genuine binding site.
        # The litmus below binds a dangerous callable through a `with ...
        # as` target directly and calls it inside the block.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.py"
        pkg.write_text(
            "import subprocess\n"
            "import contextlib\n"
            "@contextlib.contextmanager\n"
            "def give_run():\n"
            "    yield subprocess.run\n"
            "with give_run() as r:\n"
            "    r(['ls'])\n"
        )
        assert "exec" in scan_file_capabilities(pkg)

    def test_walrus_operator_bind_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # T-0666: taxonomy "walrus operator bind" row (Lang Ref 6.12
        # Assignment expressions): `(f := subprocess.run)(x)` binds AND
        # calls in one expression.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.py"
        pkg.write_text("import subprocess\n(f := subprocess.run)(['ls'])\n")
        assert "exec" in scan_file_capabilities(pkg)


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
        assert "net-connect" in scan_file_capabilities(pkg)

    def test_require_bare_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # Evasion case 2: `const ax = require('axios'); ax.get(url)` --
        # CommonJS require bound to a renamed local, no ES `import` at all.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.ts"
        pkg.write_text("const ax = require('axios');\nax.get(url);\n")
        assert "net-connect" in scan_file_capabilities(pkg)

    def test_require_destructure_rename_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # Evasion case 3: `const {get: g} = require('axios'); g(url)` --
        # CommonJS destructure WITH rename (`pair_pattern`), the sharpest
        # evasion: the call site is a bare `g(url)`, matching no needle at
        # all lexically.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.ts"
        pkg.write_text("const {get: g} = require('axios');\ng(url);\n")
        assert "net-connect" in scan_file_capabilities(pkg)

    def test_namespace_import_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # Evasion case 4: `import * as ax from 'axios'; ax.get(url)` --
        # namespace import, member access through the namespace alias.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.ts"
        pkg.write_text("import * as ax from 'axios';\nax.get(url);\n")
        assert "net-connect" in scan_file_capabilities(pkg)

    def test_ts_import_require_clause_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # Evasion case 5: `import ax = require('axios'); ax.get(url)` --
        # TS-only import-equals-require form.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.ts"
        pkg.write_text("import ax = require('axios');\nax.get(url);\n")
        assert "net-connect" in scan_file_capabilities(pkg)

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
        assert any(
            op.capability_kind == "net-connect" and op.library == "axios" for op in ops
        )

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
        assert "net-connect" in scan_file_capabilities(pkg)

    def test_bracket_access_aliased_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # T-0377 reviewer round 2: bracket access through an aliased
        # `require()` rebind -- `const ax = require('axios'); ax['get']
        # (url)`.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.ts"
        pkg.write_text("const ax = require('axios');\nax['get'](url);\n")
        assert "net-connect" in scan_file_capabilities(pkg)

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
        assert "net-connect" in scan_file_capabilities(pkg)

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
        assert "net-connect" in scan_file_capabilities(pkg)

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
        assert "net-connect" in scan_file_capabilities(pkg)

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
        assert "net-connect" in scan_file_capabilities(pkg)

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
        assert "net-connect" in scan_file_capabilities(pkg)

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


class TestCapabilityScanRustTaxonomyClosureResolution:
    """T-0661: Rust sibling of `TestCapabilityScanTaxonomyClosureResolution`
    (python T-0659)/`TestCapabilityScanTsTaxonomyClosureResolution` (TS
    T-0660) -- T-0378 covered aliased `use`/`use ... as` and local-shadow
    discipline, but left grouped/nested `use` lists, glob `use`, and any
    `let`-binding alias-copy-propagation entirely unbound (documented
    limitation). These tests lock the T-0661 fix's litmus against
    capability-evasion-taxonomy.md's Rust static-resolvable rows not
    already covered by T-0378: grouped/nested `use`, `pub use`, glob `use`,
    `let` binding, chained/shadowed `let`, tuple destructuring, and closure
    capture. Uses an `as`-aliased target throughout (`Command as C`/local
    let-bound names) so the raw text never contains the literal
    `"Command::new("` needle -- same isolation rationale as
    `TestCapabilityScanRustBindingResolution`."""

    def test_grouped_use_alias_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # Taxonomy "use path::{a, b}" (grouped/nested) row, combined with
        # an `as` rename inside the group: `use std::process::{Command as
        # C, Stdio}; C::new(cmd)`.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.rs"
        pkg.write_text(
            'use std::process::{Command as C, Stdio};\nfn f() { C::new("sh"); }\n'
        )
        assert "exec" in scan_file_capabilities(pkg)

    def test_nested_grouped_use_alias_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # A further-nested group (`a::{b, c::{d as e}}`) recurses correctly.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.rs"
        pkg.write_text(
            'use std::{fs, process::{Command as C}};\nfn f() { C::new("sh"); }\n'
        )
        assert "exec" in scan_file_capabilities(pkg)

    def test_pub_use_reexport_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # Taxonomy "pub use re-export" row, combined with an `as` rename so
        # the raw text never contains "Command::new(".
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.rs"
        pkg.write_text(
            'pub use std::process::Command as C;\nfn f() { C::new("sh"); }\n'
        )
        assert "exec" in scan_file_capabilities(pkg)

    def test_glob_use_let_alias_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # Taxonomy "use path::*" (glob) row: `use std::process::*;` binds
        # the wildcard-fallback sentinel, and a further `let`-bound alias
        # off the glob-brought-in name resolves through it.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.rs"
        pkg.write_text(
            'use std::process::*;\nfn f() { let c = Command::new; c("sh"); }\n'
        )
        assert "exec" in scan_file_capabilities(pkg)

    def test_let_binding_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # Taxonomy "let binding" row: `let f = std::process::Command::new;
        # f("sh").spawn();`.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.rs"
        pkg.write_text(
            'use std::process::Command as C;\nfn f() { let g = C::new; g("sh"); }\n'
        )
        assert "exec" in scan_file_capabilities(pkg)

    def test_chained_shadowed_let_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # Taxonomy "chained/shadowed let" row: `let f = cmd_new; let f = f;`.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.rs"
        pkg.write_text(
            "use std::process::Command as C;\n"
            'fn f() { let g = C::new; let g = g; g("sh"); }\n'
        )
        assert "exec" in scan_file_capabilities(pkg)

    def test_tuple_destructure_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # Taxonomy "tuple/struct destructuring bind" row: `let (f, _) =
        # (Command::new, 0); f("sh");`.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.rs"
        pkg.write_text(
            "use std::process::Command as C;\n"
            'fn f() { let (g, _) = (C::new, 0); g("sh"); }\n'
        )
        assert "exec" in scan_file_capabilities(pkg)

    def test_closure_capture_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # Taxonomy "closure capturing a bound path" row: `let f =
        # Command::new; let c = move |a| f(a).spawn();`.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.rs"
        pkg.write_text(
            "use std::process::Command as C;\n"
            'fn f() { let g = C::new; let c = move |a: &str| { g(a); }; c("sh"); }\n'
        )
        assert "exec" in scan_file_capabilities(pkg)

    def test_glob_use_untracked_module_not_claimed(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # No false claim: a glob `use` of a module `DANGEROUS_OPERATIONS`
        # does NOT curate must not resolve any bare name (honest
        # under-approximation, mirrors `_RUST_WILDCARD_DANGEROUS_MODULES`).
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.rs"
        pkg.write_text('use my_own_crate::*;\nfn f() { helper("sh"); }\n')
        assert "exec" not in scan_file_capabilities(pkg)

    def test_closure_param_shadowing_let_alias_not_detected(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # No regression: a CLOSURE parameter of the same name as an
        # enclosing `let`-aliased dangerous target shadows it FOR THE
        # CLOSURE'S OWN BODY -- the alias table must not resolve through a
        # local closure-param shadow (the closure's own scope binds `g` to
        # nothing dangerous, unlike the enclosing function's scope).
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.rs"
        pkg.write_text(
            "use std::process::Command as C;\n"
            "fn f() {\n"
            "    let g = C::new;\n"
            "    let c = move |g: i32| { g(5); };\n"
            "    c(5);\n"
            "}\n"
        )
        assert "exec" not in scan_file_capabilities(pkg)

    def test_let_binding_benign_not_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # No regression: a `let` binding to an ORDINARY (non-`use`-bound)
        # value must stay silent.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.rs"
        pkg.write_text('fn f() { let x = 5; println!("{}", x); }\n')
        assert "exec" not in scan_file_capabilities(pkg)

    def test_function_pointer_coercion_from_named_fn_detected(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # T-0666: taxonomy "function-pointer coercion from a named fn" row:
        # `let f: fn(&str) -> _ = Command::new; f("sh");` -- an explicit
        # `fn(...)` type annotation on the `let` target does not change the
        # binding grammar from an ordinary `let` (per `_capability.py`'s
        # T-0662 comment: a typedef/type annotation only renames the
        # declared TYPE, not the binding shape), so this reduces to the
        # same code path `test_let_binding_detected` already locks.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.rs"
        pkg.write_text(
            "use std::process::Command as C;\n"
            'fn f() { let g: fn(&str) -> _ = C::new; g("sh"); }\n'
        )
        assert "exec" in scan_file_capabilities(pkg)

    def test_type_alias_for_function_pointer_type_detected(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # T-0666: taxonomy "`type` alias (data, not routing by itself, but
        # aliases the function-pointer type)" row: `type Spawner = fn(&str)
        # -> Child;` then `let f: Spawner = Command::new; f("sh");` -- the
        # `type` item itself never routes a call (the doc's own note); what
        # this row needs a litmus for is the SUBSEQUENT `let` binding typed
        # through the alias, same reduction as the fn-pointer-coercion row
        # above.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.rs"
        pkg.write_text(
            "use std::process::Command as C;\n"
            "type Spawner = fn(&str) -> std::process::Child;\n"
            'fn f() { let g: Spawner = C::new; g("sh"); }\n'
        )
        assert "exec" in scan_file_capabilities(pkg)

    def test_struct_update_field_rebind_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # T-0666/T-1063: taxonomy "field rebinding via struct update" row:
        # `let h = Handlers { run: Command::new, ..default }; (h.run)
        # ("sh");`. Closed by T-1063's `_record_rust_field_alias`/`_build_
        # rust_field_alias_table` (file-wide field-name-keyed table, mirrors
        # C's `_record_c_field_alias`/`_c_field_alias_table`) plus a new
        # parenthesized-field-expression call-target shape in `_collect_
        # rust_candidates`.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.rs"
        pkg.write_text(
            "use std::process::Command as C;\n"
            "struct Handlers { run: fn(&str) -> std::process::Child }\n"
            "fn f(default: Handlers) {\n"
            "    let h = Handlers { run: C::new, ..default };\n"
            '    (h.run)("sh");\n'
            "}\n"
        )
        assert "exec" in scan_file_capabilities(pkg)

    def test_macro_rules_expansion_emitting_fixed_call_not_detected(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # T-0666: taxonomy "`macro_rules!` expansion emitting a fixed call"
        # row. Honest documented limitation: this module's own comment
        # ("`macro`-free language has no analog to Rust's `macro_rules!`
        # row") is about OTHER languages lacking the row, not about Rust
        # itself having macro-expansion-aware resolution -- there is no
        # `macro_rules!`/macro-invocation handling anywhere in the Rust
        # resolver (no `macro_rule`/`macro_invocation` node type is ever
        # matched). A macro invocation SITE (`run!("sh")`) produces no
        # finding since the resolver never expands it to see the
        # `Command::new(...).spawn()` the macro body defines. This fixture
        # locks that honest current gap rather than leaving the row
        # unregistered.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.rs"
        pkg.write_text(
            "use std::process::Command as C;\n"
            'macro_rules! run { ($x:expr) => { C::new("sh").arg($x).spawn() } }\n'
            'fn f() { run!("x"); }\n'
        )
        assert "exec" not in scan_file_capabilities(pkg)


class TestCapabilityScanTsTaxonomyClosureResolution:
    """T-0660: TS/JS sibling of `TestCapabilityScanTaxonomyClosureResolution`
    (python T-0659) -- T-0377/T-0432 closed import/require/subscript-
    binding evasions but left this module's own documented gap open: "no
    scope-local alias copy-propagation" -- a name shadowed by a local
    binding was simply unresolved past that point, never chased through a
    further local reassignment. These tests lock the T-0660 fix's litmus
    against capability-evasion-taxonomy.md's TS/JS static-resolvable rows
    not already covered by T-0377/T-0432: simple/chained assignment, array
    destructuring, default-parameter forwarding, and member rebinding.
    Deliberately uses the axios/"net" needle (dotted, no bare-module-name
    needle), same isolation rationale as `TestCapabilityScanTsBindingResolution`."""

    def test_simple_assignment_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # Taxonomy "simple assignment": `const f = require("child_process")
        # .exec; f(x)` -- here `const f = require('axios').get; f(url);`.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.ts"
        pkg.write_text("const f = require('axios').get;\nf(url);\n")
        assert "net-connect" in scan_file_capabilities(pkg)

    def test_chained_assignment_outer_target_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # Taxonomy "chained assignment": `let a, b; a = b = cp.exec; b(x);`
        # -- here the OUTER target `a` is called.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.ts"
        pkg.write_text(
            "const ax = require('axios');\nlet a, b;\na = b = ax.get;\na(url);\n"
        )
        assert "net-connect" in scan_file_capabilities(pkg)

    def test_chained_assignment_inner_target_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # Same chained assignment, INNER target `b` called instead.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.ts"
        pkg.write_text(
            "const ax = require('axios');\nlet a, b;\na = b = ax.get;\nb(url);\n"
        )
        assert "net-connect" in scan_file_capabilities(pkg)

    def test_array_destructure_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # Taxonomy "destructuring bind (array)": `const [f] = [cp.exec];
        # f(x);`.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.ts"
        pkg.write_text("const ax = require('axios');\nconst [f] = [ax.get];\nf(url);\n")
        assert "net-connect" in scan_file_capabilities(pkg)

    def test_default_param_forwarding_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # Taxonomy "default parameter forwarding": `function f(cb = cp.exec)
        # { cb(x); }`.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.ts"
        pkg.write_text(
            "const ax = require('axios');\nfunction h(cb = ax.get) {\n  cb(url);\n}\n"
        )
        assert "net-connect" in scan_file_capabilities(pkg)

    def test_member_rebind_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # Taxonomy "member rebinding": `obj.run = cp.exec; obj.run(x);`.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.ts"
        pkg.write_text(
            "const ax = require('axios');\n"
            "const obj = {};\n"
            "obj.run = ax.get;\n"
            "obj.run(url);\n"
        )
        assert "net-connect" in scan_file_capabilities(pkg)

    def test_closure_capture_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # Taxonomy "closure capture": `function outer(){ const r = cp.exec;
        # return function(){ r(x); }; }`.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.ts"
        pkg.write_text(
            "const ax = require('axios');\n"
            "function outer() {\n"
            "  const r = ax.get;\n"
            "  return function() { r(url); };\n"
            "}\n"
        )
        assert "net-connect" in scan_file_capabilities(pkg)

    def test_default_param_benign_not_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # No regression: a default parameter forwarding an ORDINARY (non-
        # dangerous) callable must stay silent.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.ts"
        pkg.write_text("function h(cb = doSomethingSafe) {\n  cb(url);\n}\n")
        assert "net" not in scan_file_capabilities(pkg)

    def test_member_rebind_benign_not_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # No regression: rebinding a member to an ORDINARY value must stay
        # silent.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.ts"
        pkg.write_text("const obj = {};\nobj.run = doSomethingSafe;\nobj.run(url);\n")
        assert "net" not in scan_file_capabilities(pkg)

    def test_reassigned_alias_call_via_chained_target_still_detected(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # Sanity check on the alias table's own resolution chain, not just
        # the raw bare-member-expression finding a plain `const f =
        # ax.get;` already produces on its own (this scanner treats ANY
        # resolvable member-expression as a candidate, called or not,
        # T-0377): calling the ALIASED name a second time through a further
        # local copy (`const g = f; g(url);`) still resolves.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.ts"
        pkg.write_text(
            "const ax = require('axios');\nconst f = ax.get;\nconst g = f;\ng(url);\n"
        )
        assert "net-connect" in scan_file_capabilities(pkg)

    def test_named_import_with_alias_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # T-0666: taxonomy "`import { name as alias } from`" row (ECMA-262
        # 16.2.2 ImportSpecifier) -- distinct from the CommonJS destructure-
        # rename case (`test_require_destructure_rename_detected` on the
        # sibling binding-resolution class): this is the ESM
        # `import {a as b} from` syntax specifically.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.ts"
        pkg.write_text("import { exec as e } from 'child_process';\ne(cmd);\n")
        assert "exec" in scan_file_capabilities(pkg)

    def test_export_from_reexport_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # T-0666: taxonomy "`export ... from` re-export" row. `_capability.py`
        # documents that TRUE cross-module linking of the re-export's own
        # USE site is not attempted (single-file scope) -- but the scanner's
        # file-wide member-expression over-approximation (T-0377: any
        # resolvable member-expression is a candidate, called or not) still
        # fires on the `child_process.exec` reference the re-export line
        # itself contains, so this row IS covered end to end, just via the
        # coarser mechanism rather than true re-export linking.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.ts"
        pkg.write_text("export { exec } from 'child_process';\n")
        assert "exec" in scan_file_capabilities(pkg)

    def test_export_star_from_reexport_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # T-0666: taxonomy "`export * from` re-export" row -- the taxonomy
        # doc tags this row "best-effort; needs source-module
        # enumerability"; the scanner's raw operations scan still flags the
        # dangerous `child_process` module name on the re-export line.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.ts"
        pkg.write_text("export * from 'child_process';\n")
        assert "exec" in scan_file_capabilities(pkg)

    def test_export_default_binding_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # T-0666: taxonomy "`export default` binding" row. True resolution
        # at the import USE site (`import run from './m'; run(x)`) needs
        # cross-module linking this single-file scanner does not attempt --
        # but the `cp.exec` member-expression on the export line itself is
        # still a resolvable candidate under the file-wide over-
        # approximation, so the construct is covered.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.ts"
        pkg.write_text(
            "const cp = require('child_process');\nexport default cp.exec;\n"
        )
        assert "exec" in scan_file_capabilities(pkg)

    def test_class_field_holding_bound_reference_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # T-0666: taxonomy "class field/method holding a bound reference"
        # row (`class C { run = cp.exec; }`). `_capability.py` documents
        # that TRUE points-to tracking through a later `new C().run(x)` call
        # site is not attempted -- but the field initializer's own
        # `cp.exec` member-expression is still a resolvable candidate under
        # the file-wide over-approximation (any resolvable member-
        # expression counts, called or not), so this row is covered, just
        # not via genuine instance points-to.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.ts"
        pkg.write_text(
            "const cp = require('child_process');\n"
            "class C {\n"
            "  run = cp.exec;\n"
            "}\n"
            "new C().run(cmd);\n"
        )
        assert "exec" in scan_file_capabilities(pkg)


def _ts_find(node, node_type: str):  # noqa: ANN001, ANN201
    """First descendant of `node` (inclusive) with `.type == node_type`, or
    `None` -- a small DFS helper `TestCapabilityScanTsAliasTablePredicates`
    uses to pluck a specific tree-sitter node out of a parsed fixture for a
    white-box call into a private resolver function."""
    if node.type == node_type:
        return node
    for child in node.children:
        found = _ts_find(child, node_type)
        if found is not None:
            return found
    return None


def _ts_find_all(node, node_type: str, out: list) -> None:  # noqa: ANN001
    """Every descendant of `node` (inclusive) with `.type == node_type`,
    appended to `out` in document order -- `_ts_find`'s multi-match
    sibling."""
    if node.type == node_type:
        out.append(node)
    for child in node.children:
        _ts_find_all(child, node_type, out)


class TestCapabilityScanTsAliasTablePredicates:
    """T-0660 mutation-evidence follow-up (TEST016 land refusal): the
    `scan_file_capabilities`-level "detected"/"not detected" tests in
    `TestCapabilityScanTsTaxonomyClosureResolution` do NOT actually kill
    mutants of several alias-table guard predicates, because
    `_collect_ts_candidates`'s own file-wide tree walk independently
    re-resolves the SAME bare member/subscript expression a fixture's RHS
    happens to contain (e.g. `const f = ax.get;` flags "net" the instant
    `ax.get` exists ANYWHERE in the file, whether or not the alias-table
    machinery that copies it to `f` even runs) -- the full-scan API masks
    these predicates entirely. These tests call the private resolver
    functions DIRECTLY with a hand-parsed AST so each guard's outcome is
    the thing under test, not incidentally reproduced by a parallel code
    path. Confirmed by hand: reverting each guard's operator (`==`<->`!=`,
    `and`<->`or`, `strict=False`<->`strict=True`) locally and re-running the
    single matching test here flips it from pass to fail; reverted before
    committing (frob:ticket T-0660's Done report records which mutation was
    hand-verified for which test)."""

    def test_member_rebind_lookup_used_only_for_identifier_object(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability_typescript.py::_resolve_ts_member \
        # kind="unit"
        # Kills the `_capability.py:2217` compare-Eq-swap mutant
        # (`obj.type == "identifier"` -> `!=`): with a real `identifier`
        # object and a matching alias-table rebind entry, `_resolve_ts_
        # member` must reach the rebind fallback and return its value;
        # the swapped comparison would skip the fallback for this exact
        # case and return `None` instead.
        from frob.lang import raw_tree
        from frob.vet._capability_typescript import _TS_SCOPE_TYPES, _resolve_ts_member

        pkg = tmp_path / "pkg.ts"
        pkg.write_text("obj.run(url);\n")
        tree, _source, _lang = raw_tree(pkg).danger_ok
        member = _ts_find(tree.root_node, "member_expression")
        assert member is not None
        program = tree.root_node
        assert program.type in _TS_SCOPE_TYPES
        alias_table = {program.id: {"obj.run": "axios.get"}}
        resolved = _resolve_ts_member(member, {}, {}, {}, alias_table)
        assert resolved == "axios.get"

    def test_member_rebind_lookup_skipped_without_alias_table(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability_typescript.py::_resolve_ts_member \
        # kind="unit"
        # Kills the `_capability.py:2217` boolop-And-swap mutant (`and` ->
        # `or`): with `alias_table=None`, the real `and` short-circuits
        # before ever touching `_ts_attr_rebind_lookup`, returning `None`
        # cleanly; the swapped `or` would call `_ts_attr_rebind_lookup`
        # with `alias_table=None` anyway (since the identifier check alone
        # is enough to satisfy `or`), raising `AttributeError` the instant
        # it tries `None.get(...)`.
        from frob.lang import raw_tree
        from frob.vet._capability_typescript import _resolve_ts_member

        pkg = tmp_path / "pkg.ts"
        pkg.write_text("obj.run(url);\n")
        tree, _source, _lang = raw_tree(pkg).danger_ok
        member = _ts_find(tree.root_node, "member_expression")
        assert member is not None
        resolved = _resolve_ts_member(member, {}, {}, {}, None)
        assert resolved is None

    def test_attr_rebind_lookup_climbs_past_non_matching_scope(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability_typescript.py::_ts_attr_rebind_lookup \
        # kind="unit"
        # Kills the `_capability.py:2246` compare-Eq-swap mutant (`cur.type
        # == "program"` -> `!=`): the rebind entry lives TWO scope levels
        # above the call site (the outer function, not the immediately
        # enclosing inner one, which is a real intervening non-matching
        # scope) -- the real code must climb PAST that inner scope to find
        # it. The swapped comparison breaks the climb at the very first
        # non-"program" scope it checks (i.e. immediately), so it would
        # never reach the outer scope's entry at all.
        from frob.lang import raw_tree
        from frob.vet._capability_typescript import _ts_attr_rebind_lookup

        pkg = tmp_path / "pkg.ts"
        pkg.write_text(
            "function outer() {\n  function inner() {\n    obj.run(url);\n  }\n}\n"
        )
        tree, _source, _lang = raw_tree(pkg).danger_ok
        call_site = _ts_find(tree.root_node, "member_expression")
        assert call_site is not None
        functions = []
        _ts_find_all(tree.root_node, "function_declaration", functions)
        assert len(functions) == 2
        outer_fn, inner_fn = functions
        assert outer_fn.start_byte < inner_fn.start_byte
        # inner's own scope binds nothing for "obj.run" -- only outer does.
        alias_table = {
            inner_fn.id: {},
            outer_fn.id: {"obj.run": "axios.get"},
        }
        resolved = _ts_attr_rebind_lookup("obj", "run", call_site, alias_table)
        assert resolved == "axios.get"

    def test_resolve_expr_peels_through_chained_assignment(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability_typescript.py::_resolve_ts_expr \
        # kind="unit"
        # Kills the `_capability.py:2292` compare-Eq-swap mutant
        # (`node.type == "assignment_expression"` -> `!=`): resolving the
        # OUTER assignment_expression node of `a = b = ax.get` directly
        # must peel through to `ax.get`'s own resolution; the swapped
        # comparison would skip the peel-through branch entirely and fall
        # through to `_resolve_ts_expr`'s final `return None`.
        from frob.lang import raw_tree
        from frob.vet._capability_typescript import _resolve_ts_expr

        pkg = tmp_path / "pkg.ts"
        pkg.write_text("a = b = ax.get;\n")
        tree, _source, _lang = raw_tree(pkg).danger_ok
        outer_assignment = _ts_find(tree.root_node, "assignment_expression")
        assert outer_assignment is not None
        resolved = _resolve_ts_expr(outer_assignment, {"ax": "axios"}, {}, {}, None)
        assert resolved == "axios.get"

    def test_default_param_alias_recorded_for_identifier_pattern(
        self, tmp_path: Path
    ) -> None:
        # frob:tests \
        # src/frob/vet/_capability_typescript.py::_record_ts_default_param_aliases \
        # kind="unit"
        # Kills the `_capability.py:2472` compare-NotEq-swap mutant
        # (`pattern.type != "identifier"` -> `==`): a real identifier
        # default-parameter pattern with a resolvable default value must
        # get an alias entry; the swapped comparison would treat the
        # ordinary identifier case as the one to SKIP.
        from frob.lang import raw_tree
        from frob.vet._capability_typescript import _record_ts_default_param_aliases

        pkg = tmp_path / "pkg.ts"
        pkg.write_text("function h(cb = ax.get) { cb(url); }\n")
        tree, _source, _lang = raw_tree(pkg).danger_ok
        func = _ts_find(tree.root_node, "function_declaration")
        assert func is not None
        alias_table: dict = {}
        _record_ts_default_param_aliases(func, {"ax": "axios"}, {}, {}, alias_table)
        assert alias_table[func.id]["cb"] == "axios.get"

    def test_default_param_alias_skips_missing_default_value(
        self, tmp_path: Path
    ) -> None:
        # frob:tests \
        # src/frob/vet/_capability_typescript.py::_record_ts_default_param_aliases \
        # kind="unit"
        # Kills the `_capability.py:2472` boolop-Or-swap mutant (`or` ->
        # `and`): a plain parameter with NO default (`value is None`, the
        # other two clauses false) must be skipped by the real `or`. The
        # swapped `and` would let it through and call `_resolve_ts_expr`
        # on a `None` value node, raising `AttributeError`.
        from frob.lang import raw_tree
        from frob.vet._capability_typescript import _record_ts_default_param_aliases

        pkg = tmp_path / "pkg.ts"
        pkg.write_text("function h(cb) { cb(url); }\n")
        tree, _source, _lang = raw_tree(pkg).danger_ok
        func = _ts_find(tree.root_node, "function_declaration")
        assert func is not None
        alias_table: dict = {}
        _record_ts_default_param_aliases(func, {}, {}, {}, alias_table)
        assert alias_table.get(func.id, {}) == {}

    def test_destructure_alias_tolerates_length_mismatch(self, tmp_path: Path) -> None:
        # frob:tests \
        # src/frob/vet/_capability_typescript.py::_record_ts_destructure_alias \
        # kind="unit"
        # Kills the `_capability.py:2499` bool-False-negated mutant
        # (`strict=False` -> `strict=True`): the array pattern binds FEWER
        # names than the array literal has elements (a real, benign
        # over-provisioned RHS) -- the real `zip(..., strict=False)` must
        # silently truncate to the shorter side; `strict=True` would raise
        # `ValueError` instead.
        from frob.lang import raw_tree
        from frob.vet._capability_typescript import _record_ts_destructure_alias

        pkg = tmp_path / "pkg.ts"
        pkg.write_text("const [f] = [ax.get, 0];\n")
        tree, _source, _lang = raw_tree(pkg).danger_ok
        left_pattern = _ts_find(tree.root_node, "array_pattern")
        right_array = _ts_find(tree.root_node, "array")
        assert left_pattern is not None
        assert right_array is not None
        scope_aliases: dict = {}
        _record_ts_destructure_alias(
            left_pattern, right_array, {"ax": "axios"}, {}, {}, {}, scope_aliases
        )
        assert scope_aliases["f"] == "axios.get"

    def test_destructure_alias_binds_only_identifier_elements(
        self, tmp_path: Path
    ) -> None:
        # frob:tests \
        # src/frob/vet/_capability_typescript.py::_record_ts_destructure_alias \
        # kind="unit"
        # Kills the `_capability.py:2500` compare-NotEq-swap mutant
        # (`left_el.type != "identifier"` -> `==`): a real identifier
        # destructuring element paired with a resolvable RHS element must
        # get an alias entry; the swapped comparison would SKIP the
        # ordinary identifier case instead of an unsupported one.
        from frob.lang import raw_tree
        from frob.vet._capability_typescript import _record_ts_destructure_alias

        pkg = tmp_path / "pkg.ts"
        pkg.write_text("const [f] = [ax.get];\n")
        tree, _source, _lang = raw_tree(pkg).danger_ok
        left_pattern = _ts_find(tree.root_node, "array_pattern")
        right_array = _ts_find(tree.root_node, "array")
        assert left_pattern is not None
        assert right_array is not None
        scope_aliases: dict = {}
        _record_ts_destructure_alias(
            left_pattern, right_array, {"ax": "axios"}, {}, {}, {}, scope_aliases
        )
        assert scope_aliases["f"] == "axios.get"


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


class TestCapabilityScanCTaxonomyClosureResolution:
    """T-0662: C sibling of `TestCapabilityScanTaxonomyClosureResolution`
    (python)/`TestCapabilityScanRustTaxonomyClosureResolution` (rust) --
    closes the remaining `docs/design/capability-evasion-taxonomy.md` C
    table static rows T-0379 (macro aliasing only) left unbound:
    function-pointer variable init from a named function, a `typedef`'d
    function-pointer type, plain assignment of a function pointer, a
    struct field statically initialized to a function pointer, and an
    array of function pointers read at a CONSTANT index."""

    def test_fn_ptr_var_init_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # Taxonomy row: `void (*f)(const char*) = system_wrapper; f(x);`
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.c"
        pkg.write_text('void (*f)(const char*) = system;\nvoid g() { f("sh"); }\n')
        assert "exec" in scan_file_capabilities(pkg)

    def test_typedef_fn_ptr_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # Taxonomy row: `typedef void (*Handler)(const char*); Handler f = do_exec; f(x);`
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.c"
        pkg.write_text(
            "typedef void (*Handler)(const char*);\n"
            'Handler h = system;\nvoid g() { h("sh"); }\n'
        )
        assert "exec" in scan_file_capabilities(pkg)

    # frob:waive PII012 reason="'address_of' names the C `&` address-of operator, not a mailing/contact address"  # noqa: E501
    def test_assignment_address_of_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # Taxonomy row: `f = &do_exec; f(x);` -- plain assignment, not a
        # declaration init.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.c"
        pkg.write_text('void (*f)(const char*);\nvoid g() { f = &system; f("sh"); }\n')
        assert "exec" in scan_file_capabilities(pkg)

    def test_assignment_bare_name_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # Same row, without the `&` (a bare function name decays to a
        # pointer in an assignment context too).
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.c"
        pkg.write_text('void (*f)(const char*);\nvoid g() { f = system; f("sh"); }\n')
        assert "exec" in scan_file_capabilities(pkg)

    def test_struct_field_static_init_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # Taxonomy row: `struct Ops ops = { .run = system }; ops.run(x);`
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.c"
        pkg.write_text(
            "struct Ops { void (*run)(const char*); };\n"
            "struct Ops ops = { .run = system };\n"
            'void g() { ops.run("sh"); }\n'
        )
        assert "exec" in scan_file_capabilities(pkg)

    def test_array_fn_ptr_constant_index_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # Taxonomy row: `void (*tbl[])(const char*) = { system }; tbl[0](x);`
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.c"
        pkg.write_text(
            'void (*tbl[])(const char*) = { system };\nvoid g() { tbl[0]("sh"); }\n'
        )
        assert "exec" in scan_file_capabilities(pkg)

    def test_array_fn_ptr_nonconstant_index_not_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # The taxonomy's own "runtime-opaque" sibling row: a non-constant
        # index must NOT resolve (no false positive claiming static
        # resolution of what is genuinely a runtime read).
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.c"
        pkg.write_text(
            "void (*tbl[])(const char*) = { system };\n"
            'void g(int i) { tbl[i]("sh"); }\n'
        )
        assert "exec" not in scan_file_capabilities(pkg)

    def test_chained_var_alias_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # `f` aliases `system`; `g` (a second function-pointer var) is
        # initialized FROM `f` -- resolves transitively, document-order.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.c"
        pkg.write_text(
            "void (*f)(const char*) = system;\n"
            "void (*g)(const char*) = f;\n"
            'void h() { g("sh"); }\n'
        )
        assert "exec" in scan_file_capabilities(pkg)

    def test_param_shadowing_var_alias_not_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # A function parameter named `f` (an `int`, not a function pointer,
        # no alias entry recorded for it) shadows the file-scope alias `f`
        # for the duration of that function -- must not resolve (T-0339
        # fail-closed, no false positive).
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.c"
        pkg.write_text(
            "void (*f)(const char*) = system;\n"
            "void g(int f) { f = 0; }\n"
            'void h() { void (*local)(const char*) = f; local("sh"); }\n'
        )
        # `f` inside `g` is a shadowing int parameter with no alias entry;
        # inside `h`, the unqualified `f` still resolves at file scope.
        assert "exec" in scan_file_capabilities(pkg)

    def test_unaliased_local_shadow_not_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # A locally-declared function-pointer variable with NO resolvable
        # initializer (a forward declaration `void (*f)(const char*);`
        # inside a function, never assigned) must not be treated as
        # resolving to anything -- fail-closed, no guess.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.c"
        pkg.write_text('void g() { void (*f)(const char*); f("sh"); }\n')
        assert "exec" not in scan_file_capabilities(pkg)


class TestCapabilityScanCAliasTablePredicates:
    """White-box mutation-kill coverage (TEST016) for the private
    predicates `TestCapabilityScanCTaxonomyClosureResolution`'s end-to-end
    `scan_file_capabilities` tests exercise only indirectly -- imports and
    calls each guard directly, mirroring T-0660/T-0661's
    `TestCapabilityScanTsAliasTablePredicates` white-box pattern."""

    def test_declared_name_returns_none_for_none_node(self) -> None:
        # frob:tests src/frob/vet/_capability_c.py::_c_declared_name kind="unit"
        # Kills the `while node is not None:` loop-condition mutant: a
        # `None` input must never crash and must return `None`.
        from frob.vet._capability_c import _c_declared_name

        assert _c_declared_name(None) is None

    def test_declared_name_direct_identifier(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_c.py::_c_declared_name kind="unit"
        # Kills `node.type == "identifier"`'s Eq mutant: a bare identifier
        # node must resolve to its own text, not fall through to the
        # `declarator`-field walk.
        from frob.lang import raw_tree
        from frob.vet._capability_c import _c_declared_name

        pkg = tmp_path / "pkg.c"
        pkg.write_text("int x;\n")
        tree, _source, _lang = raw_tree(pkg).danger_ok
        ident = _ts_find(tree.root_node, "identifier")
        assert ident is not None
        assert _c_declared_name(ident) == "x"

    def test_declared_name_walks_declarator_field_to_identifier(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability_c.py::_c_declared_name kind="unit"
        # Kills `next_node = node.child_by_field_name("declarator")` being
        # skipped/misrouted: a `pointer_declarator` (which HAS a labeled
        # `declarator` field, no `parenthesized_declarator` fallback
        # needed) must still resolve through to its inner identifier.
        from frob.lang import raw_tree
        from frob.vet._capability_c import _c_declared_name

        pkg = tmp_path / "pkg.c"
        pkg.write_text("int *p;\n")
        tree, _source, _lang = raw_tree(pkg).danger_ok
        pd = _ts_find(tree.root_node, "pointer_declarator")
        assert pd is not None
        assert _c_declared_name(pd) == "p"

    def test_declared_name_parenthesized_declarator_fallback(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability_c.py::_c_declared_name kind="unit"
        # Kills `node.type == "parenthesized_declarator"`'s Eq mutant AND
        # the `next_node is None and ...` And-swapped-to-Or mutant
        # directly: a `parenthesized_declarator` (the `(*f)` wrapper) has
        # no `declarator` FIELD at all, so `next_node` is `None` from the
        # field lookup -- ONLY the fallback branch can resolve it.
        from frob.lang import raw_tree
        from frob.vet._capability_c import _c_declared_name

        pkg = tmp_path / "pkg.c"
        pkg.write_text("void (*f)(const char*);\n")
        tree, _source, _lang = raw_tree(pkg).danger_ok
        paren = _ts_find(tree.root_node, "parenthesized_declarator")
        assert paren is not None
        assert _c_declared_name(paren) == "f"

    def test_declared_name_returns_none_for_abstract_declarator(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability_c.py::_c_declared_name kind="unit"
        # An `abstract_pointer_declarator` (a type-only declarator with no
        # name at all, e.g. a bare `const char*` parameter) has NO
        # `declarator` field AND is not itself a `parenthesized_
        # declarator` -- the fallback's own `if named else None` must
        # still terminate the loop with `None`, not loop forever or crash.
        from frob.lang import raw_tree
        from frob.vet._capability_c import _c_declared_name

        pkg = tmp_path / "pkg.c"
        pkg.write_text("void f(const char*);\n")
        tree, _source, _lang = raw_tree(pkg).danger_ok
        abstract = _ts_find(tree.root_node, "abstract_pointer_declarator")
        assert abstract is not None
        assert _c_declared_name(abstract) is None

    def test_collect_declaration_names_bare_identifier(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_c.py::_c_collect_declaration_names kind="unit"  # noqa: E501
        # Kills `child.type in _C_DECLARATOR_CHILD_TYPES`'s membership
        # mutant for the bare `identifier` shape (`int x, y;`).
        from frob.lang import raw_tree
        from frob.vet._capability_c import _c_collect_declaration_names

        pkg = tmp_path / "pkg.c"
        pkg.write_text("int x, y;\n")
        tree, _source, _lang = raw_tree(pkg).danger_ok
        decl = _ts_find(tree.root_node, "declaration")
        assert decl is not None
        bound: dict = {}
        _c_collect_declaration_names(decl, 0, bound)
        assert bound == {"x": 0, "y": 0}

    def test_collect_declaration_names_init_declarator(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_c.py::_c_collect_declaration_names kind="unit"  # noqa: E501
        # Kills `child.type == "init_declarator"`'s Eq mutant.
        from frob.lang import raw_tree
        from frob.vet._capability_c import _c_collect_declaration_names

        pkg = tmp_path / "pkg.c"
        pkg.write_text("int x = 5;\n")
        tree, _source, _lang = raw_tree(pkg).danger_ok
        decl = _ts_find(tree.root_node, "declaration")
        assert decl is not None
        bound: dict = {}
        _c_collect_declaration_names(decl, 7, bound)
        assert bound == {"x": 7}

    def test_collect_declaration_names_uninitialized_fn_ptr(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability_c.py::_c_collect_declaration_names kind="unit"  # noqa: E501
        # T-0662's own new shape: an uninitialized function-pointer
        # declaration (`void (*f)(const char*);`) has no `init_declarator`
        # wrapper -- only the extended `_C_DECLARATOR_CHILD_TYPES`
        # membership check (`function_declarator` in the tuple) reaches it.
        from frob.lang import raw_tree
        from frob.vet._capability_c import _c_collect_declaration_names

        pkg = tmp_path / "pkg.c"
        pkg.write_text("void (*f)(const char*);\n")
        tree, _source, _lang = raw_tree(pkg).danger_ok
        decl = _ts_find(tree.root_node, "declaration")
        assert decl is not None
        bound: dict = {}
        _c_collect_declaration_names(decl, 3, bound)
        assert bound == {"f": 3}

    # frob:waive PII012 reason="'address_of' names the C `&` address-of operator, not a mailing/contact address"  # noqa: E501
    def test_resolve_alias_source_unwraps_address_of(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_c.py::_resolve_c_alias_source kind="unit"
        from frob.lang import raw_tree
        from frob.vet._capability_c import _resolve_c_alias_source

        pkg = tmp_path / "pkg.c"
        pkg.write_text("void g() { f = &system; }\n")
        tree, _source, _lang = raw_tree(pkg).danger_ok
        pointer_expr = _ts_find(tree.root_node, "pointer_expression")
        assert pointer_expr is not None
        resolved = _resolve_c_alias_source(pointer_expr, {}, {}, {})
        assert resolved == "system"

    # frob:waive PII012 reason="'address_of' names the C `&` address-of operator, not a mailing/contact address"  # noqa: E501
    def test_resolve_alias_source_rejects_non_identifier_address_of(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability_c.py::_resolve_c_alias_source kind="unit"
        from frob.lang import raw_tree
        from frob.vet._capability_c import _resolve_c_alias_source

        pkg = tmp_path / "pkg.c"
        pkg.write_text("void g() { int x; f = &x[0]; }\n")
        tree, _source, _lang = raw_tree(pkg).danger_ok
        pointer_expr = _ts_find(tree.root_node, "pointer_expression")
        assert pointer_expr is not None
        assert _resolve_c_alias_source(pointer_expr, {}, {}, {}) is None

    def test_resolve_alias_source_rejects_non_identifier_non_pointer(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability_c.py::_resolve_c_alias_source kind="unit"
        from frob.lang import raw_tree
        from frob.vet._capability_c import _resolve_c_alias_source

        pkg = tmp_path / "pkg.c"
        pkg.write_text("void g() { int x = 1 + 2; }\n")
        tree, _source, _lang = raw_tree(pkg).danger_ok
        binary_expr = _ts_find(tree.root_node, "binary_expression")
        assert binary_expr is not None
        assert _resolve_c_alias_source(binary_expr, {}, {}, {}) is None

    def test_resolve_alias_source_via_macro_table(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_c.py::_resolve_c_alias_source kind="unit"
        from frob.lang import raw_tree
        from frob.vet._capability_c import _resolve_c_alias_source

        pkg = tmp_path / "pkg.c"
        pkg.write_text("void g() { f = SYS; }\n")
        tree, _source, _lang = raw_tree(pkg).danger_ok
        assignment = _ts_find(tree.root_node, "assignment_expression")
        assert assignment is not None
        right = assignment.child_by_field_name("right")
        resolved = _resolve_c_alias_source(right, {"SYS": "system"}, {}, {})
        assert resolved == "system"

    def test_record_field_alias_skips_non_field_designator(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability_c.py::_record_c_field_alias kind="unit"
        # An array-designated initializer (`[0] = system`) is not a
        # `field_designator` -- must be skipped, not mis-recorded.
        from frob.lang import raw_tree
        from frob.vet._capability_c import _record_c_field_alias

        pkg = tmp_path / "pkg.c"
        pkg.write_text("void (*tbl[1])(const char*) = { [0] = system };\n")
        tree, _source, _lang = raw_tree(pkg).danger_ok
        init_list = _ts_find(tree.root_node, "initializer_list")
        assert init_list is not None
        field_alias_table: dict = {}
        _record_c_field_alias(init_list, {}, {}, {}, field_alias_table)
        assert field_alias_table == {}

    def test_c_call_target_resolved_rejects_non_constant_field_type(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability_c.py::_c_call_target_resolved kind="unit"
        # A call target that is none of identifier/field_expression/
        # subscript_expression (a parenthesized function-pointer
        # dereference `(*f)(x)`) must resolve to `None`, not crash.
        from frob.lang import raw_tree
        from frob.vet._capability_c import _c_call_target_resolved

        pkg = tmp_path / "pkg.c"
        pkg.write_text('void g() { void (*f)(const char*); (*f)("sh"); }\n')
        tree, _source, _lang = raw_tree(pkg).danger_ok
        call = _ts_find(tree.root_node, "call_expression")
        assert call is not None
        func = call.child_by_field_name("function")
        assert func is not None
        assert _c_call_target_resolved(func, {}, {}, {}, {}, {}) is None

    def test_c_call_target_resolved_subscript_non_number_index(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability_c.py::_c_call_target_resolved kind="unit"
        from frob.lang import raw_tree
        from frob.vet._capability_c import _c_call_target_resolved

        pkg = tmp_path / "pkg.c"
        pkg.write_text(
            "void (*tbl[])(const char*) = { system };\n"
            'void g(int i) { tbl[i]("sh"); }\n'
        )
        tree, _source, _lang = raw_tree(pkg).danger_ok
        calls: list = []
        _ts_find_all(tree.root_node, "call_expression", calls)
        assert calls
        call = calls[-1]
        func = call.child_by_field_name("function")
        assert func is not None and func.type == "subscript_expression"
        assert _c_call_target_resolved(func, {}, {}, {}, {}, {("tbl", 0): "x"}) is None


class TestCapabilityScanCppTaxonomyClosureResolution:
    """T-0663: C++ sibling of `TestCapabilityScanCTaxonomyClosureResolution`,
    building on the SAME `_c_resolved_candidates`/`_build_c_alias_tables`
    entry point (the C fragment already covers every C++ construct that
    reduces to a shared grammar shape -- `.cpp`/`.cc`/`.hpp` all dispatch
    through `frob.lang`'s `"cpp"` language label into the identical C/C++
    resolver, T-0379's original design). Closes the taxonomy's remaining
    C++-only rows: `using`/`namespace` aliasing (documented as needing NO
    new code -- see the class docstring below), `std::function`, default
    argument forwarding a callable, and structured bindings."""

    def test_using_declaration_needs_no_special_resolution(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # Taxonomy row: `using std::system; system(x);` -- a `using`
        # declaration imports a name AS-IS (no rename), so the call site's
        # own text already contains the literal needle "system(" -- caught
        # by the pre-existing lexical scan with zero new resolver code,
        # exactly like T-0662's "function declaration + direct call" row.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.cpp"
        pkg.write_text('using std::system;\nvoid g() { system("sh"); }\n')
        assert "exec" in scan_file_capabilities(pkg)

    def test_namespace_alias_qualified_call_needs_no_special_resolution(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # Taxonomy row: `namespace fs = std; fs::system(x);` -- the
        # registry's own needle is the bare substring "system(", which
        # still occurs verbatim INSIDE a namespace-qualified call
        # (`fs::system(` contains `system(`), so no alias table lookup is
        # needed for this row either.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.cpp"
        pkg.write_text('namespace fs = std;\nvoid g() { fs::system("sh"); }\n')
        assert "exec" in scan_file_capabilities(pkg)

    def test_fn_ptr_var_init_detected_on_cpp_extension(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # T-0662's fn-ptr-var-init resolver applies unchanged to the "cpp"
        # language label (same tree-sitter-c grammar fragment).
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.cpp"
        pkg.write_text('void (*f)(const char*) = system;\nvoid g() { f("sh"); }\n')
        assert "exec" in scan_file_capabilities(pkg)

    def test_using_alias_declaration_fn_ptr_typedef_detected(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # Taxonomy row: `using Handler = void(*)(const char*); Handler f =
        # do_exec; f(x);` -- C++11's `using` alias-declaration spelling of
        # a typedef'd function-pointer type; needs no separate branch (the
        # `alias_declaration` node itself is never visited -- only the
        # LATER `Handler h = system;` declaration, an ordinary `init_
        # declarator`, is).
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.cpp"
        pkg.write_text(
            "using Handler = void(*)(const char*);\n"
            'Handler h = system;\nvoid g() { h("sh"); }\n'
        )
        assert "exec" in scan_file_capabilities(pkg)

    def test_std_function_init_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # Taxonomy row: `std::function<void(const char*)> f = system; f(x);`
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.cpp"
        pkg.write_text(
            'std::function<void(const char*)> f = system;\nvoid g() { f("sh"); }\n'
        )
        assert "exec" in scan_file_capabilities(pkg)

    def test_default_arg_forwarding_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # Taxonomy row: `void call(void(*cb)(const char*) = system) { cb(x); }`
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.cpp"
        pkg.write_text('void call(void(*cb)(const char*) = system) { cb("sh"); }\n')
        assert "exec" in scan_file_capabilities(pkg)

    def test_default_arg_param_shadowing_call_site_not_detected(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # A default-valued parameter's own alias entry must NOT leak
        # outside its own function -- calling a DIFFERENT, unrelated `cb`
        # elsewhere must not resolve.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.cpp"
        pkg.write_text(
            'void call(void(*cb)(const char*) = system) { cb("sh"); }\n'
            'void other(void (*cb)(const char*)) { cb("sh"); }\n'
        )
        # `other`'s own `cb` parameter has no default value at all -- no
        # alias entry recorded for it, so its call site must not resolve.
        result = scan_file_capabilities(pkg)
        # both functions are named `cb`; the aliased one (`call`) still
        # correctly resolves overall.
        assert "exec" in result

    def test_structured_binding_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # Taxonomy row: `auto [a, b] = std::pair{system, 0}; a(x);`
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.cpp"
        pkg.write_text('auto [a, b] = std::pair{system, 0};\nvoid g() { a("sh"); }\n')
        assert "exec" in scan_file_capabilities(pkg)

    def test_structured_binding_non_literal_rhs_not_detected(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # A structured binding whose RHS is a plain variable (no positional
        # initializer-list to walk) must not resolve -- fail-closed, no
        # guess at what a runtime value's members might be.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.cpp"
        pkg.write_text('auto [a, b] = some_pair_var;\nvoid g() { a("sh"); }\n')
        assert "exec" not in scan_file_capabilities(pkg)

    def test_lambda_capturing_fn_ptr_var_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # Taxonomy row: a lambda capturing a bound function-pointer name
        # resolves the call inside its own body -- needs NO special lambda-
        # scope handling: a `lambda_expression`'s body is not itself a
        # `_C_SCOPE_TYPES` boundary, so the shadow-scope walk climbs
        # straight past it to the SAME enclosing function scope the
        # capture's own alias entry was recorded under.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.cpp"
        pkg.write_text(
            "void g() {\n"
            "    void (*ptr)(const char*) = system;\n"
            "    auto lam = [ptr](const char* x){ ptr(x); };\n"
            "}\n"
        )
        assert "exec" in scan_file_capabilities(pkg)

    def test_using_namespace_directive_qualified_call_detected(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # T-0666: taxonomy "`using namespace` directive" row (distinct from
        # "`using` declaration" above -- a directive opens a whole
        # namespace rather than importing one name): `using namespace std;
        # system(x);`. Same "no special resolution needed" shape as the
        # using-declaration/namespace-alias rows: the bare-name call site's
        # own text already contains the literal needle "system(".
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.cpp"
        pkg.write_text('using namespace std;\nvoid g() { system("sh"); }\n')
        assert "exec" in scan_file_capabilities(pkg)

    def test_define_macro_aliasing_detected_on_cpp_extension(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # T-0666: taxonomy "`#define` macro aliasing" row, C++'s copy of the
        # same construct C's `test_macro_alias_detected` already locks --
        # the preprocessor is shared grammar, so the ".cpp" language label
        # exercises the identical macro-alias-table code path.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.cpp"
        pkg.write_text('#define RUN system\nvoid g() { RUN("sh"); }\n')
        assert "exec" in scan_file_capabilities(pkg)

    def test_member_function_pointer_bound_to_named_member_not_detected(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # T-0666: taxonomy "member-function pointer bound to a named member"
        # row: `auto p = &Ops::run; (obj.*p)(x);`. Genuine, currently
        # UNRESOLVED gap: there is no pointer-to-member (`&Ops::run`,
        # `.*`/`->*` dereference) handling anywhere in the C/C++ resolver --
        # only ordinary function pointers, typedefs, `using` aliases,
        # `std::function`, and structured bindings are tracked. This
        # fixture locks the CURRENT honest under-detection rather than
        # silently having no fixture for the row; T-1047 tracks adding
        # pointer-to-member alias tracking to close it.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.cpp"
        pkg.write_text(
            "struct Ops { static void run(const char*); };\n"
            "void g() {\n"
            "    auto p = &Ops::run;\n"
            '    (Ops::*p)("sh");\n'
            "}\n"
        )
        assert "exec" not in scan_file_capabilities(pkg)

    def test_argument_dependent_lookup_call_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # T-0666: taxonomy "argument-dependent lookup (ADL)" row: `run(x);`
        # resolves to `ns::run` purely via ADL, no `using` in scope. Same
        # "no special resolution needed" shape as the other qualified-call
        # rows above -- the unqualified call site's own text already
        # contains the literal needle "system(" (the taxonomy's own
        # dangerous-target example is `run(x)` resolving via ADL; this
        # fixture substitutes the registry's actual dangerous needle,
        # `system`, in the analogous position).
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.cpp"
        pkg.write_text(
            "namespace ns { struct Tag {}; void system(Tag, const char*); }\n"
            'void g(ns::Tag t) { system(t, "sh"); }\n'
        )
        assert "exec" in scan_file_capabilities(pkg)


class TestCapabilityScanCppAliasTablePredicates:
    """T-0663 white-box mutation-kill coverage (TEST016) for the two new
    C++-only predicates -- mirrors `TestCapabilityScanCAliasTablePredicates`
    (T-0662)."""

    def test_structured_binding_alias_skips_non_initializer_list_rhs(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability_c.py::_record_c_structured_binding_alias kind="unit"  # noqa: E501
        from frob.lang import raw_tree
        from frob.vet._capability_c import _record_c_structured_binding_alias

        pkg = tmp_path / "pkg.cpp"
        pkg.write_text("auto [a, b] = some_pair_var;\n")
        tree, _source, _lang = raw_tree(pkg).danger_ok
        declarator = _ts_find(tree.root_node, "structured_binding_declarator")
        init_declarator = _ts_find(tree.root_node, "init_declarator")
        assert declarator is not None and init_declarator is not None
        value = init_declarator.child_by_field_name("value")
        assert value is not None
        var_alias_table: dict = {}
        _record_c_structured_binding_alias(declarator, value, {}, {}, var_alias_table)
        assert var_alias_table == {}

    def test_default_param_alias_skips_node_with_no_default_value_field(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability_c.py::_record_c_default_param_alias kind="unit"  # noqa: E501
        # A plain (non-default-valued) `parameter_declaration` has no
        # `default_value` field at all -- passing one through directly
        # must be a clean no-op (`.child_by_field_name("default_value")`
        # returns `None`), not a crash.
        from frob.lang import raw_tree
        from frob.vet._capability_c import _record_c_default_param_alias

        pkg = tmp_path / "pkg.cpp"
        pkg.write_text("void call(void(*cb)(const char*)) {}\n")
        tree, _source, _lang = raw_tree(pkg).danger_ok
        node = _ts_find(tree.root_node, "parameter_declaration")
        assert node is not None
        var_alias_table: dict = {}
        _record_c_default_param_alias(node, {}, {}, var_alias_table)
        assert var_alias_table == {}

    def test_default_param_alias_records_resolvable_default(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability_c.py::_record_c_default_param_alias kind="unit"  # noqa: E501
        from frob.lang import raw_tree
        from frob.vet._capability_c import _record_c_default_param_alias

        pkg = tmp_path / "pkg.cpp"
        pkg.write_text("void call(void(*cb)(const char*) = system) {}\n")
        tree, _source, _lang = raw_tree(pkg).danger_ok
        node = _ts_find(tree.root_node, "optional_parameter_declaration")
        assert node is not None
        var_alias_table: dict = {}
        _record_c_default_param_alias(node, {}, {}, var_alias_table)
        assert any(
            "cb" in scope and scope["cb"] == "system"
            for scope in var_alias_table.values()
        )

    def test_scope_bind_step_binds_optional_parameter_declaration(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability_c.py::_c_scope_bind_step kind="unit"
        # Kills the `node_type in ("parameter_declaration", "optional_
        # parameter_declaration")` membership mutant directly: without the
        # T-0663 extension, an `optional_parameter_declaration`'s name is
        # never bound, so `_c_scope_bound_names` would not know `cb` is a
        # parameter at all.
        from frob.lang import raw_tree
        from frob.vet._capability_c import _c_scope_bound_names

        pkg = tmp_path / "pkg.cpp"
        pkg.write_text("void call(void(*cb)(const char*) = system) { cb(0); }\n")
        tree, _source, _lang = raw_tree(pkg).danger_ok
        func_def = _ts_find(tree.root_node, "function_definition")
        assert func_def is not None
        bound = _c_scope_bound_names(func_def)
        assert "cb" in bound

    def test_declaration_alias_dispatches_structured_binding_declarator(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability_c.py::_record_c_declaration_alias kind="unit"  # noqa: E501
        # Kills `declarator.type == "structured_binding_declarator"`'s Eq
        # mutant at the DISPATCH site in `_record_c_declaration_alias`
        # itself (as opposed to `_record_c_structured_binding_alias`'s own
        # internal logic, already covered above) -- without this dispatch
        # check, a structured-binding `init_declarator` would fall through
        # to the single-name `_c_declared_name` path and record nothing
        # useful (or crash on a multi-name declarator).
        from frob.lang import raw_tree
        from frob.vet._capability_c import _record_c_declaration_alias

        pkg = tmp_path / "pkg.cpp"
        pkg.write_text("auto [a, b] = std::pair{system, 0};\n")
        tree, _source, _lang = raw_tree(pkg).danger_ok
        init_declarator = _ts_find(tree.root_node, "init_declarator")
        assert init_declarator is not None
        var_alias_table: dict = {}
        field_alias_table: dict = {}
        array_alias_table: dict = {}
        _record_c_declaration_alias(
            init_declarator,
            {},
            {},
            var_alias_table,
            field_alias_table,
            array_alias_table,
        )
        assert any("a" in scope for scope in var_alias_table.values())
        assert field_alias_table == {}
        assert array_alias_table == {}


class TestCapabilityScanKotlinTaxonomyClosureResolution:
    """T-0664: kotlin sibling of `TestCapabilityScanCTaxonomyClosureResolution`/
    `TestCapabilityScanCppTaxonomyClosureResolution` -- import/`::`-reference/
    typealias name-binding resolution for
    `docs/design/capability-evasion-taxonomy.md`'s Kotlin table, closing
    the gap `frob.lang`'s T-0723 central-dispatch wiring opened (kotlin
    files now reach `frob.lang.parse_file`, but `frob.vet._capability` had
    no import/alias-aware resolution pass for the language until this
    ticket -- only the pre-existing raw-text needle scan)."""

    def test_plain_import_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # Taxonomy row: `import java.lang.Runtime; Runtime.getRuntime().exec(x)`
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.kt"
        pkg.write_text(
            'import java.lang.ProcessBuilder\nfun f() { ProcessBuilder("sh") }\n'
        )
        assert "exec" in scan_file_capabilities(pkg)

    def test_import_as_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # Taxonomy row: `import java.lang.Runtime as Rt; Rt.getRuntime().exec(x)`
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.kt"
        pkg.write_text(
            'import java.lang.Runtime as Rt\nfun f() { Rt.getRuntime().exec("sh") }\n'
        )
        assert "exec" in scan_file_capabilities(pkg)

    def test_import_as_bare_constructor_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # Simpler `import ... as` shape (no chained method call): a bare
        # constructor-call needle ("ProcessBuilder(") through an alias.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.kt"
        pkg.write_text('import java.lang.ProcessBuilder as PB\nfun f() { PB("sh") }\n')
        assert "exec" in scan_file_capabilities(pkg)

    def test_bare_callable_reference_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # Taxonomy row: `val f = ::runCmd; f(x)` -- an UNTYPED `::` callable
        # reference to a plain top-level name.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.kt"
        pkg.write_text('val f = ::ProcessBuilder\nfun g() { f("sh") }\n')
        assert "exec" in scan_file_capabilities(pkg)

    def test_typed_callable_reference_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # Taxonomy row: `val f = Runtime::exec; f(x)` -- a receiver-typed
        # `::` bound-member reference.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.kt"
        pkg.write_text(
            "class SomeClass\n"
            "val f = SomeClass::getSharedPreferences\n"
            'fun g() { f("sh") }\n'
        )
        assert "client_storage" in scan_file_capabilities(pkg)

    def test_typealias_for_function_type_needs_no_special_resolution(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # Taxonomy row: `typealias Handler = (String) -> Unit; val f:
        # Handler = ::runCmd; f(x)` -- the `typealias` only renames the
        # DECLARED TYPE (never touched by this resolver); the `val`'s own
        # VALUE is still a plain `::`-reference, resolved unchanged.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.kt"
        pkg.write_text(
            "typealias Handler = (String) -> Unit\n"
            "val f: Handler = ::ProcessBuilder\n"
            'fun g() { f("sh") }\n'
        )
        assert "exec" in scan_file_capabilities(pkg)

    def test_chained_val_alias_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # `f` aliases `ProcessBuilder` via `::`; `g` (a second `val`) is
        # initialized FROM `f` -- resolves transitively, document-order.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.kt"
        pkg.write_text('val f = ::ProcessBuilder\nval g = f\nfun h() { g("sh") }\n')
        assert "exec" in scan_file_capabilities(pkg)

    def test_curated_wildcard_import_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # Taxonomy row: `import java.lang.*; Runtime.getRuntime().exec(x)`
        # -- a wildcard import of a CURATED dangerous package resolves an
        # unqualified name through it.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.kt"
        pkg.write_text('import java.lang.*\nfun f() { ProcessBuilder("sh") }\n')
        assert "exec" in scan_file_capabilities(pkg)

    def test_uncurated_wildcard_import_not_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # A wildcard import of a package NOT in the curated set must not
        # resolve an otherwise-unrelated unqualified name -- fail-closed,
        # no false claim of resolving an untracked package's contents.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.kt"
        pkg.write_text(
            'import com.example.untracked.*\nfun f() { totallyUnrelatedName("sh") }\n'
        )
        assert scan_file_capabilities(pkg) == frozenset()

    def test_unaliased_bare_reference_not_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # A `val` bound to an ordinary (non-callable-reference, non-chained)
        # expression must not resolve -- fail-closed, no guess.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.kt"
        pkg.write_text('val f = 5\nfun g() { println("sh") }\n')
        assert scan_file_capabilities(pkg) == frozenset()

    def test_destructuring_declaration_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # T-0666/T-1063: taxonomy "destructuring declaration" row: `val (a,
        # b) = Pair(::runCmd, 0); a(x)`. Closed by T-1063's `_record_kt_
        # destructure_alias`/`_kt_destructure_value_elements` (positional
        # binding of each `multi_variable_declaration` element to its RHS
        # call-argument, mirrors rust's tuple-destructure alias table).
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.kt"
        pkg.write_text('val (a, b) = Pair(::ProcessBuilder, 0)\nfun g() { a("sh") }\n')
        assert "exec" in scan_file_capabilities(pkg)

    def test_lambda_closure_capturing_bound_name_detected(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # T-0666: taxonomy "lambda/closure capturing a bound name" row:
        # `val f = ::runCmd; val g = { x: String -> f(x) }; g(x)`. The
        # kotlin var-alias table is built file-wide (no per-function scope
        # split, T-0664), so a lambda body's call to an outer `val` alias
        # resolves the same as any other reference.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.kt"
        pkg.write_text(
            "val f = ::ProcessBuilder\n"
            'val g = { x: String -> f() }\nfun h() { g("sh") }\n'
        )
        assert "exec" in scan_file_capabilities(pkg)

    def test_default_parameter_forwarding_callable_detected(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # T-0666/T-1063: taxonomy "default parameter forwarding a callable"
        # row: `fun call(cb: (String) -> Unit = ::runCmd) { cb(x) }`. Closed
        # by T-1063's `_record_kt_param_default_aliases` -- kotlin's grammar
        # hangs a parameter's default value as a SIBLING of the `parameter`
        # node inside `function_value_parameters` (not a child of
        # `parameter` itself), so this walks the sibling list positionally
        # rather than mirroring C++'s single-node `_record_c_default_param_
        # alias` shape directly.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.kt"
        pkg.write_text(
            'fun call(cb: (String) -> Unit = ::ProcessBuilder) { cb("sh") }\n'
        )
        assert "exec" in scan_file_capabilities(pkg)

    def test_extension_function_reference_bound_via_import_detected(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # T-0666: taxonomy "extension function reference bound via import"
        # row: `import kotlin.io.path.exists` -- the pattern for binding a
        # top-level callable via an ordinary import. This reduces to the
        # SAME import-table code path `test_plain_import_detected` already
        # locks (an extension function's qualified name is bound and
        # resolved identically to any other top-level import).
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.kt"
        pkg.write_text(
            'import java.lang.ProcessBuilder\nfun g() { ProcessBuilder("sh") }\n'
        )
        assert "exec" in scan_file_capabilities(pkg)

    def test_operator_fun_invoke_making_object_directly_callable_not_detected(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
        # T-0666: taxonomy "`operator fun invoke` making an object directly
        # callable" row: `class Handler { operator fun invoke(x: String) =
        # Runtime.getRuntime().exec(x) }; val h = Handler(); h(x)`. The
        # taxonomy doc's own caveat says this "still needs points-to on the
        # receiver instance" -- a genuine, currently UNRESOLVED gap: the
        # kotlin resolver has no receiver-instance points-to (no tracking
        # from `val h = Handler()` to a later bare `h(x)` call resolving
        # through the class's `invoke` operator). This fixture locks the
        # CURRENT honest under-detection; T-1047 tracks adding
        # instance-points-to for `operator fun invoke` to close it.
        from frob.vet._capability import scan_file_capabilities

        pkg = tmp_path / "pkg.kt"
        pkg.write_text(
            "import java.lang.Runtime\n"
            "class Handler { operator fun invoke(x: String) { "
            "Runtime.getRuntime() } }\n"
            'fun g() { val h = Handler(); h("sh") }\n'
        )
        assert scan_file_capabilities(pkg) == frozenset()


class TestCapabilityScanKotlinAliasTablePredicates:
    """T-0664 white-box mutation-kill coverage (TEST016) for the private
    kotlin resolver predicates -- mirrors `TestCapabilityScanCAliasTable
    Predicates`/`TestCapabilityScanCppAliasTablePredicates`'s pattern."""

    def test_import_table_plain_import_binds_last_segment(self) -> None:
        # frob:tests src/frob/vet/_capability_kotlin.py::_kt_import_table kind="unit"
        # Kills the plain-import branch's `.rsplit(".", 1)[-1]` mutant and
        # the `elif alias_node is not None:`/`is_wildcard` dispatch: a
        # plain `import a.b.C` (no `as`, no `*`) must bind `"C"` (the last
        # dotted segment), not the full path or nothing at all.
        from frob.lang._walk_kotlin import parse_kotlin
        from frob.vet._capability_kotlin import _kt_import_table

        tree = parse_kotlin(b"import java.lang.ProcessBuilder\n")
        table, wildcard = _kt_import_table(tree.root_node)
        assert table == {"ProcessBuilder": "java.lang.ProcessBuilder"}
        assert wildcard == frozenset()

    def test_import_table_as_alias_binds_alias_name(self) -> None:
        # frob:tests src/frob/vet/_capability_kotlin.py::_kt_import_table kind="unit"
        # Kills `elif alias_node is not None:`'s Is-swap mutant: an `as`
        # import must bind the ALIAS name, not the last dotted segment.
        from frob.lang._walk_kotlin import parse_kotlin
        from frob.vet._capability_kotlin import _kt_import_table

        tree = parse_kotlin(b"import java.lang.Runtime as Rt\n")
        table, wildcard = _kt_import_table(tree.root_node)
        assert table == {"Rt": "java.lang.Runtime"}
        assert "Runtime" not in table
        assert wildcard == frozenset()

    def test_import_table_curated_wildcard_recorded(self) -> None:
        # frob:tests src/frob/vet/_capability_kotlin.py::_kt_import_table kind="unit"
        # Kills `dotted in _KT_WILDCARD_DANGEROUS_MODULES`'s membership
        # mutant: a wildcard import of a CURATED package must land in the
        # wildcard set, not the plain import table.
        from frob.lang._walk_kotlin import parse_kotlin
        from frob.vet._capability_kotlin import _kt_import_table

        tree = parse_kotlin(b"import java.lang.*\n")
        table, wildcard = _kt_import_table(tree.root_node)
        assert table == {}
        assert wildcard == frozenset({"java.lang"})

    def test_import_table_uncurated_wildcard_not_recorded(self) -> None:
        # frob:tests src/frob/vet/_capability_kotlin.py::_kt_import_table kind="unit"
        from frob.lang._walk_kotlin import parse_kotlin
        from frob.vet._capability_kotlin import _kt_import_table

        tree = parse_kotlin(b"import com.example.untracked.*\n")
        table, wildcard = _kt_import_table(tree.root_node)
        assert table == {}
        assert wildcard == frozenset()

    def test_property_name_and_value_returns_none_none_without_variable_declaration(
        self,
    ) -> None:
        # frob:tests src/frob/vet/_capability_kotlin.py::_kt_property_name_and_value kind="unit"  # noqa: E501
        # Kills `if name_node is None: return None, None`'s guard: a
        # `property_declaration` node itself passed with no `variable_
        # declaration` child at all (constructed here via a destructuring
        # declaration, which has no plain `variable_declaration` child)
        # must return `(None, None)`, not crash on a `None` var_decl.
        from frob.lang._walk_kotlin import parse_kotlin
        from frob.vet._capability_kotlin import _kt_property_name_and_value

        tree = parse_kotlin(b"val (a, b) = Pair(1, 2)\n")
        prop = _ts_find(tree.root_node, "property_declaration")
        assert prop is not None
        name_node, value = _kt_property_name_and_value(prop)
        assert name_node is None
        assert value is None

    def test_property_name_and_value_extracts_name_and_value(self) -> None:
        # frob:tests src/frob/vet/_capability_kotlin.py::_kt_property_name_and_value kind="unit"  # noqa: E501
        # Kills the `seen_eq`/`if c.type == "=":`'s Eq mutant: the VALUE
        # returned must be the child strictly AFTER the `=` token, not the
        # `=` token itself or an earlier child.
        from frob.lang._walk_kotlin import parse_kotlin
        from frob.vet._capability_kotlin import _kt_property_name_and_value

        tree = parse_kotlin(b"val f = runCmd\n")
        prop = _ts_find(tree.root_node, "property_declaration")
        assert prop is not None
        name_node, value = _kt_property_name_and_value(prop)
        assert name_node is not None and name_node.text == b"f"
        assert value is not None and value.type == "simple_identifier"
        assert value.text == b"runCmd"

    def test_resolve_callable_reference_rejects_non_identifier_member(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability_kotlin.py::_kt_resolve_callable_reference kind="unit"  # noqa: E501
        from frob.lang._walk_kotlin import parse_kotlin
        from frob.vet._capability_kotlin import _kt_resolve_callable_reference

        tree = parse_kotlin(b"val f = ::runCmd\n")
        ref = _ts_find(tree.root_node, "callable_reference")
        assert ref is not None
        assert _kt_resolve_callable_reference(ref, {}) == "runCmd"

    def test_resolve_callable_reference_typed_falls_back_to_literal_receiver(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability_kotlin.py::_kt_resolve_callable_reference kind="unit"  # noqa: E501
        # `tree-sitter-kotlin` only parses `X::Y` as `callable_reference`
        # (as opposed to a bare `navigation_expression`) once `X` is a
        # KNOWN type in the file -- a preceding `class` declaration for
        # the receiver, matching real kotlin usage (referencing a member
        # of an unresolvable/undeclared type is not valid kotlin either).
        from frob.lang._walk_kotlin import parse_kotlin
        from frob.vet._capability_kotlin import _kt_resolve_callable_reference

        tree = parse_kotlin(
            b'class Runtime\nval f = Runtime::exec\nfun g() { f("x") }\n'
        )
        ref = _ts_find(tree.root_node, "callable_reference")
        assert ref is not None
        assert _kt_resolve_callable_reference(ref, {}) == "Runtime.exec"
        assert (
            _kt_resolve_callable_reference(ref, {"Runtime": "java.lang.Runtime"})
            == "java.lang.Runtime.exec"
        )

    def test_resolve_expr_text_returns_none_for_unbound_identifier(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability_kotlin.py::_kt_resolve_expr_text \
        # kind="unit"
        from frob.lang._walk_kotlin import parse_kotlin
        from frob.vet._capability_kotlin import _kt_resolve_expr_text

        tree = parse_kotlin(b"fun f() { g(x) }\n")
        call = _ts_find(tree.root_node, "call_expression")
        assert call is not None
        callee = call.children[0]
        assert _kt_resolve_expr_text(callee, {}, {}) is None

    def test_resolve_expr_text_call_expression_wraps_with_parens(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability_kotlin.py::_kt_resolve_expr_text \
        # kind="unit"
        # The intermediate-call "()" marker this resolver's own docstring
        # explains is required for the real taxonomy needle to match at
        # all -- locked in directly against the private predicate.
        from frob.lang._walk_kotlin import parse_kotlin
        from frob.vet._capability_kotlin import _kt_resolve_expr_text

        tree = parse_kotlin(b"fun f() { Rt.getRuntime() }\n")
        call = _ts_find(tree.root_node, "call_expression")
        assert call is not None
        resolved = _kt_resolve_expr_text(call, {"Rt": "java.lang.Runtime"}, {})
        assert resolved == "java.lang.Runtime.getRuntime()"

    def test_kt_call_callee_picks_last_non_call_suffix_child(self) -> None:
        # frob:tests src/frob/vet/_capability_kotlin.py::_kt_call_callee kind="unit"
        from frob.lang._walk_kotlin import parse_kotlin
        from frob.vet._capability_kotlin import _kt_call_callee

        tree = parse_kotlin(b"fun f() { g() }\n")
        call = _ts_find(tree.root_node, "call_expression")
        assert call is not None
        callee = _kt_call_callee(call)
        assert callee is not None and callee.type == "simple_identifier"


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


# frob:ticket T-0910
class TestFingerprintScan:
    """T-0153: `_scan_file_fingerprints` -- the CVE-fingerprint sibling of
    `_scan_file_operations`, joined to `frob.strata.CVE_FINGERPRINTS`."""

    def test_matches_a_known_fingerprint(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::_scan_file_fingerprints \
        # kind="unit"
        from frob.vet._capability_scan import _scan_file_fingerprints

        pkg = tmp_path / "pkg.py"
        pkg.write_text("data = yaml.load(raw_bytes)\n")
        matches = _scan_file_fingerprints(pkg)
        assert any(m.id == "FP-DESERIALIZE-YAML-001" for m in matches)

    def test_yaml_load_with_explicit_loader_is_not_flagged(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::_yaml_load_call_lacks_explicit_loader kind="unit"  # noqa: E501
        # frob:ticket T-1329
        # An explicit Loader= is FP-DESERIALIZE-YAML-001's own prescribed
        # remediation (CVE-2017-18342 is the loader-LESS default) -- the
        # substring needle alone fired on frob's own remediated
        # tickets/_store.py calls after T-1206.
        from frob.vet._capability_scan import _scan_file_fingerprints

        pkg = tmp_path / "pkg.py"
        pkg.write_text(
            "data = yaml.load(raw_bytes, Loader=yaml.CSafeLoader)\n"
            "more = yaml.load(\n"
            "    fence.group(1),\n"
            "    Loader=_yaml_loader(),\n"
            ")\n"
        )
        matches = _scan_file_fingerprints(pkg)
        assert not any(m.id == "FP-DESERIALIZE-YAML-001" for m in matches)

    def test_one_bare_yaml_load_among_remediated_calls_still_flags(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::_yaml_load_call_lacks_explicit_loader kind="unit"  # noqa: E501
        # frob:ticket T-1329
        from frob.vet._capability_scan import _scan_file_fingerprints

        pkg = tmp_path / "pkg.py"
        pkg.write_text(
            "safe = yaml.load(raw, Loader=yaml.SafeLoader)\n"
            "unsafe = yaml.load(other_bytes)\n"
        )
        matches = _scan_file_fingerprints(pkg)
        assert any(m.id == "FP-DESERIALIZE-YAML-001" for m in matches)

    def test_no_match_on_clean_source(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::_scan_file_fingerprints \
        # kind="unit"
        from frob.vet._capability_scan import _scan_file_fingerprints

        pkg = tmp_path / "pkg.py"
        pkg.write_text("def add(a, b):\n    return a + b\n")
        assert _scan_file_fingerprints(pkg) == ()

    def test_whitespace_reformatted_needle_still_matches(self, tmp_path: Path) -> None:
        # T-0400 audit finding #3: `shell=True` reformatted with spaces
        # around the `=` used to evade FP-EXEC-SHELL-001 (raw substring
        # search only); the fingerprint scan is now whitespace-tolerant.
        # frob:tests src/frob/vet/_capability_scan.py::_scan_file_fingerprints \
        # kind="unit"
        from frob.vet._capability_scan import _scan_file_fingerprints

        pkg = tmp_path / "pkg.py"
        pkg.write_text("subprocess.run(cmd, shell = True)\n")
        matches = _scan_file_fingerprints(pkg)
        assert any(m.id == "FP-EXEC-SHELL-001" for m in matches)

    def test_whitespace_tolerant_match_still_respects_comment_spans(
        self, tmp_path: Path
    ) -> None:
        # The whitespace-tolerant matcher must still exclude comment-only
        # occurrences (T-0209), same as the exact-match path.
        # frob:tests src/frob/vet/_capability_scan.py::_scan_file_fingerprints \
        # kind="unit"
        from frob.vet._capability_scan import _scan_file_fingerprints

        pkg = tmp_path / "pkg.py"
        pkg.write_text("# example: subprocess.run(cmd, shell = True)\n")
        matches = _scan_file_fingerprints(pkg)
        assert not any(m.id == "FP-EXEC-SHELL-001" for m in matches)

    def test_matches_the_xxe_fingerprint_positive(self, tmp_path: Path) -> None:
        # T-0189 litmus positive: an lxml parser explicitly left resolving
        # external entities matches FP-XXE-PARSE-001.
        # frob:tests src/frob/vet/_capability_scan.py::_scan_file_fingerprints \
        # kind="unit"
        from frob.vet._capability_scan import _scan_file_fingerprints

        pkg = tmp_path / "pkg.py"
        pkg.write_text(
            "parser = etree.XMLParser(resolve_entities=True)\n"
            "tree = etree.parse(untrusted_source, parser)\n"
        )
        matches = _scan_file_fingerprints(pkg)
        assert any(m.id == "FP-XXE-PARSE-001" for m in matches)

    def test_does_not_match_the_xxe_fingerprint_negative(self, tmp_path: Path) -> None:
        # T-0189 litmus negative: the hardened lxml configuration (entity
        # resolution explicitly disabled) must not fire.
        # frob:tests src/frob/vet/_capability_scan.py::_scan_file_fingerprints \
        # kind="unit"
        from frob.vet._capability_scan import _scan_file_fingerprints

        pkg = tmp_path / "pkg.py"
        pkg.write_text(
            "parser = etree.XMLParser(resolve_entities=False, "
            "no_network=True, load_dtd=False)\n"
            "tree = etree.parse(untrusted_source, parser)\n"
        )
        matches = _scan_file_fingerprints(pkg)
        assert not any(m.id == "FP-XXE-PARSE-001" for m in matches)

    def test_no_language_returns_empty(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::_scan_file_fingerprints \
        # kind="unit"
        from frob.vet._capability_scan import _scan_file_fingerprints

        assert _scan_file_fingerprints(tmp_path / "foo.unknownext") == ()

    def test_unreadable_file_returns_empty(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::_scan_file_fingerprints \
        # kind="unit"
        from frob.vet._capability_scan import _scan_file_fingerprints

        missing = tmp_path / "gone.py"
        assert _scan_file_fingerprints(missing) == ()

    def test_language_mismatch_does_not_match(self, tmp_path: Path) -> None:
        # a typescript-only fingerprint's needle appearing in a .py file
        # must never match -- the language gate is enforced independently
        # of the needle text.
        # frob:tests src/frob/vet/_capability_scan.py::_scan_file_fingerprints \
        # kind="unit"
        from frob.vet._capability_scan import _scan_file_fingerprints

        pkg = tmp_path / "pkg.py"
        pkg.write_text("x = 'new Function(\"return 1\")'\n")
        matches = _scan_file_fingerprints(pkg)
        assert not any(m.id == "FP-CODEEVAL-TEMPLATE-001" for m in matches)

    def test_matches_tls_verify_false_python(self, tmp_path: Path) -> None:
        # T-0188: FP-TLS-VERIFY-001 -- requests/httpx/aiohttp verify=False.
        # frob:tests src/frob/vet/_capability_scan.py::_scan_file_fingerprints \
        # kind="unit"
        from frob.vet._capability_scan import _scan_file_fingerprints

        pkg = tmp_path / "pkg.py"
        pkg.write_text("resp = requests.get(url, verify=False)\n")
        matches = _scan_file_fingerprints(pkg)
        assert any(m.id == "FP-TLS-VERIFY-001" for m in matches)

    def test_no_match_on_verified_tls_python(self, tmp_path: Path) -> None:
        # negative sibling: verify=True never fires FP-TLS-VERIFY-001.
        # frob:tests src/frob/vet/_capability_scan.py::_scan_file_fingerprints \
        # kind="unit"
        from frob.vet._capability_scan import _scan_file_fingerprints

        pkg = tmp_path / "pkg.py"
        pkg.write_text("resp = requests.get(url, verify=True)\n")
        matches = _scan_file_fingerprints(pkg)
        assert not any(m.id == "FP-TLS-VERIFY-001" for m in matches)

    def test_matches_tls_reject_unauthorized_false_node(self, tmp_path: Path) -> None:
        # T-0188: FP-TLS-VERIFY-002 -- Node https/tls rejectUnauthorized: false.
        # frob:tests src/frob/vet/_capability_scan.py::_scan_file_fingerprints \
        # kind="unit"
        from frob.vet._capability_scan import _scan_file_fingerprints

        pkg = tmp_path / "pkg.ts"
        pkg.write_text("const opts = { host, rejectUnauthorized: false };\n")
        matches = _scan_file_fingerprints(pkg)
        assert any(m.id == "FP-TLS-VERIFY-002" for m in matches)

    def test_no_match_on_reject_unauthorized_true_node(self, tmp_path: Path) -> None:
        # negative sibling: rejectUnauthorized: true never fires
        # FP-TLS-VERIFY-002.
        # frob:tests src/frob/vet/_capability_scan.py::_scan_file_fingerprints \
        # kind="unit"
        from frob.vet._capability_scan import _scan_file_fingerprints

        pkg = tmp_path / "pkg.ts"
        pkg.write_text("const opts = { host, rejectUnauthorized: true };\n")
        matches = _scan_file_fingerprints(pkg)
        assert not any(m.id == "FP-TLS-VERIFY-002" for m in matches)

    def test_matches_tls_danger_accept_invalid_certs_rust(self, tmp_path: Path) -> None:
        # T-0188: FP-TLS-VERIFY-003 -- Rust reqwest danger_accept_invalid_certs.
        # frob:tests src/frob/vet/_capability_scan.py::_scan_file_fingerprints \
        # kind="unit"
        from frob.vet._capability_scan import _scan_file_fingerprints

        pkg = tmp_path / "pkg.rs"
        pkg.write_text(
            "let client = Client::builder()"
            ".danger_accept_invalid_certs(true).build()?;\n"
        )
        matches = _scan_file_fingerprints(pkg)
        assert any(m.id == "FP-TLS-VERIFY-003" for m in matches)

    def test_no_match_on_default_reqwest_builder_rust(self, tmp_path: Path) -> None:
        # negative sibling: a builder with no danger_accept_invalid_certs
        # call never fires FP-TLS-VERIFY-003.
        # frob:tests src/frob/vet/_capability_scan.py::_scan_file_fingerprints \
        # kind="unit"
        from frob.vet._capability_scan import _scan_file_fingerprints

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
        # frob:tests src/frob/vet/_capability_scan.py::_is_self_path kind="unit"
        from frob.vet._capability_scan import _FINGERPRINT_CATALOG_PATH, _is_self_path

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
        # frob:tests src/frob/vet/_capability_scan.py::is_self_pattern_path kind="unit"
        import re

        from frob.vet._capability_scan import is_self_pattern_path

        repo_root = Path(__file__).resolve().parents[1]
        src_root = repo_root / "src" / "frob"
        needle_table_marker = re.compile(r"needles\s*=\s*\(|needles\s*:\s*tuple\[")
        offenders: list[Path] = []
        matched: list[Path] = []
        for path in src_root.rglob("*.py"):
            text = path.read_text(encoding="utf-8", errors="replace")
            if not needle_table_marker.search(text):
                continue
            matched.append(path)
            if not is_self_pattern_path(path, repo_root):
                offenders.append(path)

        assert offenders == [], (
            f"module(s) define a literal needle table but are not covered by "
            f"is_self_pattern_path: {offenders} -- widen the exclusion set "
            f"in frob.vet._capability"
        )
        # sanity: the marker itself actually matched something -- not
        # accidentally empty (which would make the `offenders == []`
        # assertion above vacuously true). T-1420 split
        # `_capability_registry.py` into a package, so this no longer
        # names a fixed count/set of files (that would re-hardcode the
        # exact thing this drift-lock exists to keep loose) -- it only
        # confirms every catalog/scanner module `_capability.py`,
        # `_cve_fingerprint.py`, and the `_capability_registry/` package's
        # table submodules are still present and still matched.
        assert len(matched) >= 3, matched
        # T-1420 (tail split): the `needles=(...)`/`needles: tuple[...]`
        # prose that used to live in `_capability.py`'s own
        # `_SELF_PATTERN_SUFFIXES` comment block moved verbatim to
        # `_capability_scan.py` along with that constant -- it is the file
        # that matches the marker now, not `_capability.py` itself.
        assert repo_root / "src/frob/vet/_capability_scan.py" in matched
        assert repo_root / "src/frob/strata/_cve_fingerprint.py" in matched
        assert any(p.parent.name == "_capability_registry" for p in matched), matched

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
        # frob:tests src/frob/vet/_capability_scan.py::is_self_pattern_path kind="unit"
        from frob.vet._capability_scan import _aggregate_capabilities, is_self_pattern_path

        fake_repo = _make_fake_frob_repo_root(tmp_path / "foreign-install")
        foreign_frob_src = fake_repo / "src" / "frob"

        foreign_capability = foreign_frob_src / "vet" / "_capability.py"
        # T-1420: _capability_registry.py split into a package -- use one
        # representative table submodule (suffix matching is per-file, not
        # per-directory, so any one of the package's listed suffixes proves
        # the same thing the old single-file path used to).
        foreign_registry = (
            foreign_frob_src
            / "vet"
            / "_capability_registry"
            / "_dangerous_ops_python.py"
        )
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
        # frob:tests src/frob/vet/_capability_scan.py::is_self_pattern_path kind="unit"
        from frob.vet._capability_scan import is_self_pattern_path

        unrelated_root = tmp_path / "some_other_pkg"
        unrelated = unrelated_root / "utils" / "_capability.py"
        unrelated.parent.mkdir(parents=True)
        unrelated.write_text("# not frob's file\n")
        assert not is_self_pattern_path(unrelated, unrelated_root)

    def test_self_pattern_exclusion_default_root_is_false(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::is_self_pattern_path kind="unit"
        # `root=None` (the default) short-circuits to False before any
        # path resolution at all -- the caller passed no scan-root
        # identity, so nothing can be confirmed as frob's own repo.
        from frob.vet._capability import is_self_pattern_path

        assert not is_self_pattern_path(tmp_path / "anything.py")

    def test_self_pattern_exclusion_resolve_oserror_is_false(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::is_self_pattern_path kind="unit"
        # A `path.resolve()` failure (e.g. a filesystem-level symlink
        # loop) degrades to "cannot confirm", never a crash.
        from pathlib import Path as _Path

        from frob.vet._capability import is_self_pattern_path

        fake_repo = _make_fake_frob_repo_root(tmp_path / "repo")
        target = fake_repo / "src" / "frob" / "vet" / "_capability.py"
        real_resolve = _Path.resolve

        def _raising_resolve(self, *args, **kwargs):
            if self == target:
                raise OSError("simulated: resolve failure")
            return real_resolve(self, *args, **kwargs)

        monkeypatch.setattr(_Path, "resolve", _raising_resolve)
        assert not is_self_pattern_path(target, fake_repo)

    def test_self_pattern_exclusion_surprising_parts_shape_is_false(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::is_self_pattern_path kind="unit"
        # A resolved path whose `.parts` is some non-standard shape the
        # suffix-slice comparison cannot safely index into (simulated via
        # a resolve() stub returning a plain object with no real `.parts`)
        # degrades to "cannot confirm", not a crash -- covers both the
        # (KeyError, TypeError) branch and the bare-Exception fallback.
        from pathlib import Path as _Path

        from frob.vet._capability import is_self_pattern_path

        fake_repo = _make_fake_frob_repo_root(tmp_path / "repo")
        target = fake_repo / "src" / "frob" / "vet" / "_capability.py"
        real_resolve = _Path.resolve

        class _BrokenParts:
            @property
            def parts(self):
                raise TypeError("simulated: surprising parts shape")

        def _raising_resolve(self, *args, **kwargs):
            if self == target:
                return _BrokenParts()
            return real_resolve(self, *args, **kwargs)

        monkeypatch.setattr(_Path, "resolve", _raising_resolve)
        assert not is_self_pattern_path(target, fake_repo)

    # frob:ticket T-0910
    def test_self_pattern_exclusion_covers_logging_checks_needle_tuples(
        self,
    ) -> None:
        # T-0910: `frob.arch._logging_checks`'s `_BOUNDARY_CALLEE_MARKERS`
        # tuple stores the same class of bare-text needle literal
        # (`subprocess.`, `requests.`, `httpx.`, `socket.`, ...) as
        # `_srp.py`'s `_IO_MODULE_PREFIXES` (T-0729) -- a classifier table
        # this module's `_is_boundary_call` compares a parsed callee STRING
        # against, not code that itself execs/opens a socket/fetches a URL.
        # Scanning the file without this exclusion misreports those
        # needles as live net/exec/fetch_url capability USE on the
        # `graphlang` design node (SELFAUDIT001/SYS100). Regression for
        # exactly that false-positive class recurring here.
        # frob:tests src/frob/vet/_capability_scan.py::is_self_pattern_path kind="unit"
        from frob.vet._capability_scan import is_self_pattern_path

        repo_root = Path(__file__).resolve().parents[1]
        logging_checks_path = repo_root / "src" / "frob" / "arch" / "_logging_checks.py"
        assert logging_checks_path.is_file()
        assert is_self_pattern_path(logging_checks_path, repo_root)

    # frob:ticket T-0910
    def test_line_effects_reports_no_capability_on_logging_checks_module(
        self,
    ) -> None:
        # T-0910: end-to-end companion to the exclusion-membership check
        # above -- `frob.strata._effects._line_effects` (the SYS100/
        # SELFAUDIT001 tier-2 effect scanner) must observe ZERO net/fs/exec
        # effects on `_logging_checks.py` now that it is excluded, not just
        # that `is_self_pattern_path` returns True in isolation.
        # frob:tests src/frob/strata/_effects.py::_line_effects kind="unit"
        from frob.strata._effects import _line_effects

        repo_root = Path(__file__).resolve().parents[1]
        logging_checks_path = repo_root / "src" / "frob" / "arch" / "_logging_checks.py"
        assert _line_effects(logging_checks_path, repo_root) == []

    # frob:ticket T-0915
    def test_self_pattern_exclusion_covers_async_hazards_needle_tuples(
        self,
    ) -> None:
        # T-0915: `frob.arch._async_hazards`'s curated blocking-call-name
        # tables (`subprocess.`, `requests.`, `socket.`, ...) are the same
        # bare-text needle-literal class as `_srp.py` (T-0729) and
        # `_logging_checks.py` (T-0910) -- classifier data compared against
        # parsed callee strings, not live I/O. Without the exclusion the
        # SYS100 scanner misreports them as net/exec capability USE on the
        # `graphlang` node (SELFAUDIT001). Regression for the third
        # recurrence of this false-positive class.
        # frob:tests src/frob/vet/_capability_scan.py::is_self_pattern_path kind="unit"
        from frob.vet._capability_scan import is_self_pattern_path

        repo_root = Path(__file__).resolve().parents[1]
        async_hazards_path = repo_root / "src" / "frob" / "arch" / "_async_hazards.py"
        assert async_hazards_path.is_file()
        assert is_self_pattern_path(async_hazards_path, repo_root)

    # frob:ticket T-0915
    def test_line_effects_reports_no_capability_on_async_hazards_module(
        self,
    ) -> None:
        # T-0915: end-to-end companion -- the SYS100/SELFAUDIT001 tier-2
        # effect scanner must observe ZERO net/fs/exec effects on
        # `_async_hazards.py` now that it is excluded, not just that
        # `is_self_pattern_path` returns True in isolation.
        # frob:tests src/frob/strata/_effects.py::_line_effects kind="unit"
        from frob.strata._effects import _line_effects

        repo_root = Path(__file__).resolve().parents[1]
        async_hazards_path = repo_root / "src" / "frob" / "arch" / "_async_hazards.py"
        assert _line_effects(async_hazards_path, repo_root) == []

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
        # frob:tests src/frob/vet/_capability_scan.py::is_self_pattern_path kind="unit"
        from frob.vet._capability import scan_file_capabilities
        from frob.vet._capability_scan import (
            _aggregate_capabilities,
            is_self_pattern_path,
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
        # frob:tests src/frob/vet/_capability_scan.py::_scan_directory_fingerprints \
        # kind="unit"
        from frob.vet._capability_scan import _scan_directory_fingerprints

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
        # frob:tests src/frob/vet/_capability_scan.py::_scan_directory_fingerprints \
        # kind="unit"
        from frob.vet._capability_scan import _scan_directory_fingerprints

        fake_repo = _make_fake_frob_repo_root(tmp_path / "self-scan")
        matched = _scan_directory_fingerprints(fake_repo, max_files=2000)
        assert not any(m.id == "FP-DESERIALIZE-YAML-001" for m in matched)


# frob:ticket T-0380
class TestFingerprintBindingResolution:
    """T-0380: `_scan_file_fingerprints` reuses the SAME binding tables
    capability scanning built (T-0328/T-0377/T-0378/T-0379) so an aliased
    import that would evade a lexical needle match is still caught --
    adversarial test per language."""

    def test_python_aliased_pickle_loads_still_matches(self, tmp_path: Path) -> None:
        # `import pickle as p; p.loads(...)` never contains the literal
        # text "pickle.loads(" the lexical scan needs -- a real fingerprint
        # (FP-DESERIALIZE-PICKLE-001) resolved through the alias table.
        # frob:tests src/frob/vet/_capability_scan.py::_scan_file_fingerprints \
        # kind="unit"
        from frob.vet._capability_scan import _scan_file_fingerprints

        pkg = tmp_path / "pkg.py"
        pkg.write_text("import pickle as p\ndata = p.loads(raw_bytes)\n")
        matches = _scan_file_fingerprints(pkg)
        assert any(m.id == "FP-DESERIALIZE-PICKLE-001" for m in matches)

    def test_python_unaliased_control_still_matches_lexically(
        self, tmp_path: Path
    ) -> None:
        # Control: the un-aliased form still matches via the pre-existing
        # lexical path (this ticket adds recall, never removes it).
        from frob.vet._capability_scan import _scan_file_fingerprints

        pkg = tmp_path / "pkg.py"
        pkg.write_text("import pickle\ndata = pickle.loads(raw_bytes)\n")
        matches = _scan_file_fingerprints(pkg)
        assert any(m.id == "FP-DESERIALIZE-PICKLE-001" for m in matches)

    def test_typescript_aliased_require_still_matches(self, tmp_path: Path) -> None:
        # `const ax = require('axios'); ax.get(url)` resolves to
        # "axios.get" through _ts_resolved_candidates -- a synthetic
        # axios-shaped fingerprint proves _binding_fingerprints' TS path
        # independent of whether the real CVE_FINGERPRINTS catalog happens
        # to carry a module.member-shaped typescript needle today.
        # frob:tests src/frob/vet/_capability_scan.py::_binding_fingerprints kind="unit"
        from frob.strata._cve_fingerprint import CveFingerprint
        from frob.vet._capability_scan import _scan_file_fingerprints

        fp = CveFingerprint(
            id="FP-TEST-AXIOS-001",
            title="test-only axios.get() fingerprint",
            cve=("CVE-0000-00000",),
            cwe_id="CWE-918",
            language="typescript",
            needles=("axios.get(",),
            remediation="test fixture only",
        )
        pkg = tmp_path / "pkg.ts"
        pkg.write_text("const ax = require('axios');\nax.get(url);\n")
        with mock.patch("frob.strata.CVE_FINGERPRINTS", (fp,)):
            matches = _scan_file_fingerprints(pkg)
        assert any(m.id == "FP-TEST-AXIOS-001" for m in matches)

    def test_typescript_clean_source_does_not_match(self, tmp_path: Path) -> None:
        from frob.strata._cve_fingerprint import CveFingerprint
        from frob.vet._capability_scan import _scan_file_fingerprints

        fp = CveFingerprint(
            id="FP-TEST-AXIOS-001",
            title="test-only axios.get() fingerprint",
            cve=("CVE-0000-00000",),
            cwe_id="CWE-918",
            language="typescript",
            needles=("axios.get(",),
            remediation="test fixture only",
        )
        pkg = tmp_path / "pkg.ts"
        pkg.write_text("const x = 1 + 2;\n")
        with mock.patch("frob.strata.CVE_FINGERPRINTS", (fp,)):
            matches = _scan_file_fingerprints(pkg)
        assert not any(m.id == "FP-TEST-AXIOS-001" for m in matches)

    def test_rust_aliased_use_still_matches(self, tmp_path: Path) -> None:
        # `use std::process::Command as C; C::new("sh")` never contains the
        # literal text "Command::new(" -- resolved via the rust `use`
        # binding table (T-0378) to "std::process::Command::new".
        # frob:tests src/frob/vet/_capability_scan.py::_binding_fingerprints kind="unit"
        from frob.strata._cve_fingerprint import CveFingerprint
        from frob.vet._capability_scan import _scan_file_fingerprints

        fp = CveFingerprint(
            id="FP-TEST-COMMAND-001",
            title="test-only Command::new() fingerprint",
            cve=("CVE-0000-00000",),
            cwe_id="CWE-78",
            language="rust",
            needles=("Command::new(",),
            remediation="test fixture only",
        )
        pkg = tmp_path / "pkg.rs"
        pkg.write_text('use std::process::Command as C;\nfn f() { C::new("sh"); }\n')
        with mock.patch("frob.strata.CVE_FINGERPRINTS", (fp,)):
            matches = _scan_file_fingerprints(pkg)
        assert any(m.id == "FP-TEST-COMMAND-001" for m in matches)

    def test_rust_clean_source_does_not_match(self, tmp_path: Path) -> None:
        from frob.strata._cve_fingerprint import CveFingerprint
        from frob.vet._capability_scan import _scan_file_fingerprints

        fp = CveFingerprint(
            id="FP-TEST-COMMAND-001",
            title="test-only Command::new() fingerprint",
            cve=("CVE-0000-00000",),
            cwe_id="CWE-78",
            language="rust",
            needles=("Command::new(",),
            remediation="test fixture only",
        )
        pkg = tmp_path / "pkg.rs"
        pkg.write_text("fn add(a: i32, b: i32) -> i32 { a + b }\n")
        with mock.patch("frob.strata.CVE_FINGERPRINTS", (fp,)):
            matches = _scan_file_fingerprints(pkg)
        assert not any(m.id == "FP-TEST-COMMAND-001" for m in matches)

    def test_c_aliased_macro_still_matches(self, tmp_path: Path) -> None:
        # `#define SYS system; SYS(cmd)` never contains the literal text
        # "system(" -- resolved via the C macro-alias table (T-0379).
        # frob:tests src/frob/vet/_capability_scan.py::_binding_fingerprints kind="unit"
        from frob.strata._cve_fingerprint import CveFingerprint
        from frob.vet._capability_scan import _scan_file_fingerprints

        fp = CveFingerprint(
            id="FP-TEST-SYSTEM-001",
            title="test-only system() fingerprint",
            cve=("CVE-0000-00000",),
            cwe_id="CWE-78",
            language="c-cpp",
            needles=("system(",),
            remediation="test fixture only",
        )
        pkg = tmp_path / "pkg.c"
        pkg.write_text("#define SYS system\nvoid f(char *cmd) { SYS(cmd); }\n")
        with mock.patch("frob.strata.CVE_FINGERPRINTS", (fp,)):
            matches = _scan_file_fingerprints(pkg)
        assert any(m.id == "FP-TEST-SYSTEM-001" for m in matches)

    def test_c_clean_source_does_not_match(self, tmp_path: Path) -> None:
        from frob.strata._cve_fingerprint import CveFingerprint
        from frob.vet._capability_scan import _scan_file_fingerprints

        fp = CveFingerprint(
            id="FP-TEST-SYSTEM-001",
            title="test-only system() fingerprint",
            cve=("CVE-0000-00000",),
            cwe_id="CWE-78",
            language="c-cpp",
            needles=("system(",),
            remediation="test fixture only",
        )
        pkg = tmp_path / "pkg.c"
        pkg.write_text("int add(int a, int b) { return a + b; }\n")
        with mock.patch("frob.strata.CVE_FINGERPRINTS", (fp,)):
            matches = _scan_file_fingerprints(pkg)
        assert not any(m.id == "FP-TEST-SYSTEM-001" for m in matches)


class TestObfuscationEnsemble:
    # invariant spec: [INV-025](invariants/INV-025.md)
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
        # frob:tests src/frob/vet/_obfuscation.py::_hex_identifier_ratio_signal \
        # kind="unit"
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
        # frob:tests src/frob/vet/_obfuscation.py::_scan_directory_obfuscation \
        # kind="unit"
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
        # frob:tests src/frob/vet/_obfuscation.py::_scan_directory_obfuscation \
        # kind="unit"
        from frob.vet._obfuscation import _scan_directory_obfuscation

        rlo = chr(0x202E)
        (tmp_path / "evil.c").write_text(f"// {rlo}nommoc si sti\nint main() {{}}\n")
        signals = _scan_directory_obfuscation(tmp_path)
        assert "invisible-text" in signals

    def test_bidi_override_detected_in_kotlin_file(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_obfuscation.py::_scan_directory_obfuscation \
        # kind="unit"
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
        # frob:tests src/frob/vet/_obfuscation.py::_scan_directory_obfuscation \
        # kind="unit"
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

    def test_run_osv_scan_flattens_advisories_from_scanner_output(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/vet/_osv.py::_run_osv_scan kind="unit"
        # T-1294: pins the real JSON-flattening behavior -- one advisory
        # per (package, vulnerability), fixed_version pulled from the LAST
        # "fixed" event across all ranges, aliases carried through.
        from frob.vet import _osv

        monkeypatch.setattr(
            _osv.shutil, "which", lambda _binary: "/usr/bin/osv-scanner"
        )
        payload = json.dumps(
            {
                "results": [
                    {
                        "packages": [
                            {
                                "package": {"name": "requests", "version": "2.0.0"},
                                "vulnerabilities": [
                                    {
                                        "id": "GHSA-xxxx",
                                        "aliases": ["CVE-2023-1234"],
                                        "affected": [
                                            {
                                                "ranges": [
                                                    {
                                                        "events": [
                                                            {"introduced": "0"},
                                                            {"fixed": "2.1.0"},
                                                        ]
                                                    },
                                                    {
                                                        "events": [
                                                            {"fixed": "2.2.0"},
                                                        ]
                                                    },
                                                ]
                                            }
                                        ],
                                    }
                                ],
                            }
                        ]
                    }
                ]
            }
        )
        monkeypatch.setattr(_osv, "_run_osv_scanner", lambda _lockfile: payload)
        lockfile = tmp_path / "requirements.txt"
        lockfile.write_text("requests==2.0.0\n")

        advisories = _osv._run_osv_scan(lockfile)

        assert advisories is not None
        assert len(advisories) == 1
        advisory = advisories[0]
        assert advisory.advisory_id == "GHSA-xxxx"
        assert advisory.package == "requests"
        assert advisory.version == "2.0.0"
        # The LAST-declared "fixed" event across all ranges wins.
        assert advisory.fixed_version == "2.2.0"
        assert advisory.aliases == ("CVE-2023-1234",)
        # cve_ids surfaces the CVE-shaped alias even though the advisory's
        # own id is a GHSA id -- proves the two adapters compose correctly.
        assert _osv.cve_ids(advisory) == ("CVE-2023-1234",)

    def test_run_osv_scan_empty_stdout_is_a_clean_no_findings_result(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/vet/_osv.py::_run_osv_scan kind="unit"
        # Empty (whitespace-only) stdout is a real "no vulnerabilities"
        # result, distinct from the None-on-failure sentinel.
        from frob.vet import _osv

        monkeypatch.setattr(
            _osv.shutil, "which", lambda _binary: "/usr/bin/osv-scanner"
        )
        monkeypatch.setattr(_osv, "_run_osv_scanner", lambda _lockfile: "   \n")
        lockfile = tmp_path / "requirements.txt"
        lockfile.write_text("requests==2.0.0\n")

        assert _osv._run_osv_scan(lockfile) == ()

    def test_run_osv_scan_unparseable_json_is_none_not_empty(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/vet/_osv.py::_run_osv_scan kind="unit"
        # A parse failure must degrade to None (adapter-failed), never to
        # the empty tuple ("scanned clean") -- conflating the two would
        # silently hide a broken adapter as "nothing found" (T-1294: the
        # dangerous-regression class this ticket calls out for vet).
        from frob.vet import _osv

        monkeypatch.setattr(
            _osv.shutil, "which", lambda _binary: "/usr/bin/osv-scanner"
        )
        monkeypatch.setattr(_osv, "_run_osv_scanner", lambda _lockfile: "{not json")
        lockfile = tmp_path / "requirements.txt"
        lockfile.write_text("requests==2.0.0\n")

        assert _osv._run_osv_scan(lockfile) is None

    def test_run_osv_scanner_reports_spawn_failure_as_none(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/vet/_osv.py::_run_osv_scanner kind="unit"
        from typani import Err

        from frob.vet import _osv

        monkeypatch.setattr(
            _osv, "run_argv", lambda argv, timeout_s=60.0: Err("spawn failed")
        )
        lockfile = tmp_path / "requirements.txt"
        lockfile.write_text("requests==2.0.0\n")
        assert _osv._run_osv_scanner(lockfile) is None

    def test_run_osv_scanner_crash_with_no_output_is_none(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/vet/_osv.py::_run_osv_scanner kind="unit"
        from typani import Ok

        from frob.gitio import ProcResult
        from frob.vet import _osv

        def fake_run_argv(argv, timeout_s=60.0):
            return Ok(ProcResult(argv=argv, returncode=1, stdout="", stderr="boom"))

        monkeypatch.setattr(_osv, "run_argv", fake_run_argv)
        lockfile = tmp_path / "requirements.txt"
        lockfile.write_text("requests==2.0.0\n")
        assert _osv._run_osv_scanner(lockfile) is None

    def test_run_osv_scanner_nonzero_with_output_is_findings_not_failure(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/vet/_osv.py::_run_osv_scanner kind="unit"
        # osv-scanner exits non-zero WHEN IT FINDS VULNERABILITIES -- that
        # must be treated as real findings, never conflated with a crash.
        from typani import Ok

        from frob.gitio import ProcResult
        from frob.vet import _osv

        def fake_run_argv(argv, timeout_s=60.0):
            return Ok(
                ProcResult(argv=argv, returncode=1, stdout='{"results": []}', stderr="")
            )

        monkeypatch.setattr(_osv, "run_argv", fake_run_argv)
        lockfile = tmp_path / "requirements.txt"
        lockfile.write_text("requests==2.0.0\n")
        assert _osv._run_osv_scanner(lockfile) == '{"results": []}'


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

    # frob:ticket T-0822
    def test_fetch_publish_date_refuses_when_net_disabled(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-0822: `FROB_DISABLE_NET` degrades `_fetch_publish_date` to
        `ok=False` without ever calling `urlopen` -- a no-connect spy
        proves the kill switch short-circuits before the socket opens."""
        # frob:tests src/frob/vet/_registry.py::_fetch_publish_date kind="unit"
        # frob:tests src/frob/vet/_registry.py::_result_from_network kind="unit"
        from frob.vet import _registry

        monkeypatch.setenv("FROB_DISABLE_NET", "1")

        def _no_connect(*_args: object, **_kwargs: object) -> object:
            raise AssertionError("urlopen must not be called while net is disabled")

        monkeypatch.setattr(_registry.urllib.request, "urlopen", _no_connect)

        result = _registry._fetch_publish_date(
            "pypi",
            "some-package",
            "1.0.0",
            cache_path=tmp_path / "vet.db",
            base_url="http://127.0.0.1:1",
            timeout_s=0.5,
        )
        assert result.ok is False
        assert result.published_at is None
        assert "net disabled" in result.note

    def test_url_for_every_supported_ecosystem_and_version_form(self) -> None:
        # frob:tests src/frob/vet/_registry.py::_url_for kind="unit"
        # T-1294: pins the real per-ecosystem URL shape -- every branch
        # (pypi latest/pinned, npm, cargo, both base_url override and the
        # real-host default) plus the unsupported-ecosystem error.
        from frob.vet._registry import _url_for

        assert _url_for("pypi", "requests", "latest", None) == (
            "https://pypi.org/pypi/requests/json"
        )
        assert _url_for("pypi", "requests", "2.31.0", None) == (
            "https://pypi.org/pypi/requests/2.31.0/json"
        )
        assert _url_for("npm", "lodash", "latest", None) == (
            "https://registry.npmjs.org/lodash"
        )
        assert _url_for("cargo", "serde", "latest", None) == (
            "https://crates.io/api/v1/crates/serde/versions"
        )
        assert _url_for("pypi", "requests", "2.31.0", "http://fake") == (
            "http://fake/pypi/requests/2.31.0/json"
        )
        assert _url_for("npm", "lodash", "latest", "http://fake") == (
            "http://fake/npm/lodash"
        )
        assert _url_for("cargo", "serde", "1.0", "http://fake") == (
            "http://fake/crates/serde/versions"
        )
        with pytest.raises(ValueError, match="unsupported ecosystem"):
            _url_for("rubygems", "rails", "latest", None)

    def test_parse_published_pypi_latest_resolves_current_release(self) -> None:
        # frob:tests src/frob/vet/_registry.py::_parse_published kind="unit"
        from frob.vet._registry import _parse_published

        body = json.dumps(
            {
                "info": {"version": "2.31.0"},
                "releases": {
                    "2.31.0": [{"upload_time_iso_8601": "2023-05-22T00:00:00"}]
                },
            }
        )
        resolved, published = _parse_published("pypi", "requests", "latest", body)
        assert resolved == "2.31.0"
        assert published is not None
        assert published.year == 2023

    def test_parse_published_npm_and_cargo(self) -> None:
        # frob:tests src/frob/vet/_registry.py::_parse_published kind="unit"
        # T-1294: npm and cargo were entirely unexercised before this --
        # a detector that only ever parsed pypi bodies would silently
        # never flag/verify anything for the other two ecosystems.
        from frob.vet._registry import _parse_published

        npm_body = json.dumps(
            {
                "dist-tags": {"latest": "4.17.21"},
                "time": {"4.17.21": "2021-02-20T00:00:00.000Z"},
            }
        )
        resolved, published = _parse_published("npm", "lodash", "latest", npm_body)
        assert resolved == "4.17.21"
        assert published is not None
        assert published.year == 2021

        cargo_body = json.dumps(
            {
                "versions": [
                    {"num": "1.0.130", "created_at": "2022-01-01T00:00:00.000Z"},
                    {"num": "1.0.100", "created_at": "2020-01-01T00:00:00.000Z"},
                ]
            }
        )
        resolved, published = _parse_published("cargo", "serde", "latest", cargo_body)
        assert resolved == "1.0.130"  # first entry = latest
        assert published is not None
        assert published.year == 2022

        resolved, published = _parse_published("cargo", "serde", "1.0.100", cargo_body)
        assert resolved == "1.0.100"
        assert published is not None
        assert published.year == 2020

        # A pinned version absent from the registry's version list must
        # degrade to (None, None), never guess a neighboring entry.
        resolved, published = _parse_published("cargo", "serde", "9.9.9", cargo_body)
        assert resolved is None
        assert published is None

    def test_result_from_cached_malformed_body_degrades_to_unverified(self) -> None:
        # frob:tests src/frob/vet/_registry.py::_result_from_cached kind="unit"
        # T-1294: a corrupted cache entry must degrade to ok=False, never
        # crash the caller or silently pass through unparsed data.
        from frob.vet._registry import _result_from_cached

        result = _result_from_cached(
            "pypi", "requests", "2.31.0", "pypi:requests:2.31.0", "{not json"
        )
        assert result.ok is False
        assert "unparseable" in result.note

    def test_fetch_publish_date_reuses_cache_without_any_network_call(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/vet/_registry.py::_fetch_publish_date kind="unit"
        # T-1294: a pinned version already cached must be served straight
        # from the TTL cache -- proven by making urlopen explode if it is
        # ever reached.
        from frob.vet import _registry
        from frob.vet._cache import ttl_cache_set

        cache_path = tmp_path / "vet.db"
        cached_body = json.dumps(
            {"releases": {"2.31.0": [{"upload_time_iso_8601": "2023-05-22T00:00:00"}]}}
        )
        ttl_cache_set(
            cache_path, _registry._CACHE_TABLE, "pypi:requests:2.31.0", cached_body
        )

        def _no_connect(*_args: object, **_kwargs: object) -> object:
            raise AssertionError("cached lookup must never reach the network")

        monkeypatch.setattr(_registry.urllib.request, "urlopen", _no_connect)

        result = _registry._fetch_publish_date(
            "pypi",
            "requests",
            "2.31.0",
            cache_path=cache_path,
            base_url="http://127.0.0.1:1",
        )
        assert result.ok is True
        assert result.resolved_version == "2.31.0"
        assert result.published_at is not None

    def test_result_from_network_unparseable_response_body(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_registry.py::_result_from_network kind="unit"
        # T-1294: a successful fetch that returns a body the parser can't
        # read must degrade to ok=False, distinct from a network failure.
        from frob.vet import _registry

        class _FakeResponse:
            def __enter__(self) -> "_FakeResponse":
                return self

            def __exit__(self, *exc: object) -> bool:
                return False

            def read(self) -> bytes:
                return b"{not json"

        monkeypatch.setattr(
            _registry.urllib.request, "urlopen", lambda *a, **kw: _FakeResponse()
        )
        result = _registry._result_from_network(
            "pypi",
            "requests",
            "2.31.0",
            "pypi:requests:2.31.0",
            "https://pypi.org/pypi/requests/2.31.0/json",
            tmp_path / "vet.db",
            5.0,
        )
        assert result.ok is False
        assert "could not verify publish date" in result.note


# ---------------------------------------------------------------------------
# NVD CVE->CWE lookups
# ---------------------------------------------------------------------------


class TestNvdLookup:
    # frob:ticket T-0822
    def test_fetch_cwe_for_cve_refuses_when_net_disabled(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-0822: `FROB_DISABLE_NET` degrades `fetch_cwe_for_cve` to
        `ok=False` without ever calling `urlopen` -- a no-connect spy
        proves the kill switch short-circuits before the socket opens."""
        # frob:tests src/frob/vet/_nvd.py::fetch_cwe_for_cve kind="unit"
        # frob:tests src/frob/vet/_nvd.py::_fetch_from_network kind="unit"
        from frob.vet import _nvd

        monkeypatch.setenv("FROB_DISABLE_NET", "1")

        def _no_connect(*_args: object, **_kwargs: object) -> object:
            raise AssertionError("urlopen must not be called while net is disabled")

        monkeypatch.setattr(_nvd.urllib.request, "urlopen", _no_connect)

        result = _nvd.fetch_cwe_for_cve(
            "CVE-2024-00000",
            cache_path=tmp_path / "vet.db",
            base_url="http://127.0.0.1:1",
            timeout_s=0.5,
        )
        assert result.ok is False
        assert result.cwe_ids == ()
        assert "net disabled" in result.note


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

    def test_resolve_import_registry_match(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_closedworld.py::resolve_import kind="unit"
        from frob.vet._closedworld import resolve_import

        result = resolve_import(
            "subprocess", root=tmp_path, cache_path=tmp_path / ".frob" / "vet.db"
        )
        assert result.resolution == "registry"

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

    # frob:tests src/frob/vet/_models.py::ClosedWorldAccounting.registry_count \
    # kind="unit"
    # frob:tests src/frob/vet/_models.py::ClosedWorldAccounting.no_capability_count \
    # kind="unit"
    # frob:tests src/frob/vet/_models.py::ClosedWorldAccounting.vetted_count kind="unit"
    # frob:tests src/frob/vet/_models.py::ClosedWorldAccounting.unknown_count \
    # kind="unit"
    # frob:tests src/frob/vet/_models.py::ClosedWorldAccounting.accounting_line \
    # kind="unit"
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


class TestOpaqueIndirectionGate:
    """T-0665: fail-closed runtime-resolved capability-indirection
    obligation -- `frob.vet._capability._opaque_indirection_findings` and
    `frob.gates._opaque.opaque_gate`'s literal/non-literal split, the
    coordinator-signed category-1 boundary."""

    def test_python_getattr_non_literal_name_fires(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::_opaque_indirection_findings kind="unit"  # noqa: E501
        from frob.vet._capability_scan import _opaque_indirection_findings

        pkg = tmp_path / "pkg.py"
        pkg.write_text("getattr(subprocess, name)(x)\n")
        findings = _opaque_indirection_findings(pkg)
        assert any(f.construct_name == "getattr" for f in findings)

    def test_python_getattr_literal_name_does_not_fire(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::_opaque_indirection_findings kind="unit"  # noqa: E501
        # Coordinator sign-off: "literal-key lookups that resolve
        # statically belong to the ordinary resolver path, not this gate."
        from frob.vet._capability_scan import _opaque_indirection_findings

        pkg = tmp_path / "pkg.py"
        pkg.write_text('getattr(subprocess, "run")(x)\n')
        findings = _opaque_indirection_findings(pkg)
        assert not any(f.construct_name == "getattr" for f in findings)

    def test_python_eval_always_fires_regardless_of_argument(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::_opaque_indirection_findings kind="unit"  # noqa: E501
        # eval/exec have literal_arg_index=None -- always opaque, no
        # literal split is possible for arbitrary evaluated source text.
        from frob.vet._capability_scan import _opaque_indirection_findings

        pkg = tmp_path / "pkg.py"
        pkg.write_text('eval("1 + 1")\n')
        findings = _opaque_indirection_findings(pkg)
        assert any(f.construct_name == "eval" for f in findings)

    def test_python_import_module_non_literal_fires(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::_opaque_indirection_findings kind="unit"  # noqa: E501
        from frob.vet._capability_scan import _opaque_indirection_findings

        pkg = tmp_path / "pkg.py"
        pkg.write_text("importlib.import_module(mod_name).run(x)\n")
        findings = _opaque_indirection_findings(pkg)
        assert any(f.construct_name == "importlib.import_module" for f in findings)

    def test_typescript_dynamic_import_non_literal_specifier_fires(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::_opaque_indirection_findings kind="unit"  # noqa: E501
        from frob.vet._capability_scan import _opaque_indirection_findings

        pkg = tmp_path / "pkg.ts"
        pkg.write_text("import(modName).then(m => m.exec(x));\n")
        findings = _opaque_indirection_findings(pkg)
        assert any(f.construct_name == "dynamic import()" for f in findings)

    def test_typescript_dynamic_import_literal_specifier_does_not_fire(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::_opaque_indirection_findings kind="unit"  # noqa: E501
        from frob.vet._capability_scan import _opaque_indirection_findings

        pkg = tmp_path / "pkg.ts"
        pkg.write_text('import("./known-module").then(m => m.run());\n')
        findings = _opaque_indirection_findings(pkg)
        assert not any(f.construct_name == "dynamic import()" for f in findings)

    def test_c_dlsym_non_literal_symbol_fires(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::_opaque_indirection_findings kind="unit"  # noqa: E501
        from frob.vet._capability_scan import _opaque_indirection_findings

        pkg = tmp_path / "pkg.c"
        pkg.write_text(
            "void g() { void (*f)(const char*) = dlsym(handle, name); f(x); }\n"
        )
        findings = _opaque_indirection_findings(pkg)
        assert any(f.construct_name == "dlsym" for f in findings)

    def test_c_dlsym_literal_symbol_does_not_fire(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::_opaque_indirection_findings kind="unit"  # noqa: E501
        from frob.vet._capability_scan import _opaque_indirection_findings

        pkg = tmp_path / "pkg.c"
        pkg.write_text(
            'void g() { void (*f)(const char*) = dlsym(handle, "run_cmd"); f(x); }\n'
        )
        findings = _opaque_indirection_findings(pkg)
        assert not any(f.construct_name == "dlsym" for f in findings)

    def test_kotlin_class_forname_always_fires(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::_opaque_indirection_findings kind="unit"  # noqa: E501
        from frob.vet._capability_scan import _opaque_indirection_findings

        pkg = tmp_path / "pkg.kt"
        pkg.write_text(
            'fun run(cls: String) { Class.forName(cls).getMethod("m").invoke(t) }\n'
        )
        findings = _opaque_indirection_findings(pkg)
        assert any(f.construct_name == "Class.forName" for f in findings)

    def test_rust_libloading_get_fires_only_when_file_uses_libloading(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::_opaque_indirection_findings kind="unit"  # noqa: E501
        # The bare `.get(` needle is deliberately broad -- gated to files
        # that actually import libloading, so an ordinary HashMap::get in
        # an unrelated rust file never trips this.
        from frob.vet._capability_scan import _opaque_indirection_findings

        with_lib = tmp_path / "with_lib.rs"
        with_lib.write_text(
            "use libloading::Library;\n"
            'fn g(lib: &Library) { let f = lib.get(b"run_cmd").unwrap(); f(x); }\n'
        )
        assert any(
            f.construct_name == "libloading symbol lookup"
            for f in _opaque_indirection_findings(with_lib)
        )

        without_lib = tmp_path / "without_lib.rs"
        without_lib.write_text(
            'fn g(m: &std::collections::HashMap<String, i32>) { m.get("x"); }\n'
        )
        assert not any(
            f.construct_name == "libloading symbol lookup"
            for f in _opaque_indirection_findings(without_lib)
        )

    def test_finding_inside_comment_span_does_not_fire(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::_opaque_indirection_findings kind="unit"  # noqa: E501
        from frob.vet._capability_scan import _opaque_indirection_findings

        pkg = tmp_path / "pkg.py"
        pkg.write_text("# eval(x) is just an example in a comment\n")
        findings = _opaque_indirection_findings(pkg)
        assert findings == ()

    def test_finding_inside_string_literal_does_not_fire(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::_byte_offset_inside_string_literal kind="unit"  # noqa: E501
        # The single-largest false-positive class the T-0665 first-turn-on
        # measurement found: this module's OWN registry constants (e.g.
        # `needle="getattr("`) tripping their own obligation.
        from frob.vet._capability_scan import _opaque_indirection_findings

        pkg = tmp_path / "pkg.py"
        pkg.write_text('NEEDLE = "getattr("\n')
        findings = _opaque_indirection_findings(pkg)
        assert findings == ()

    def test_arg_looks_literal_rejects_fstring_interpolation(self) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::_arg_looks_literal kind="unit"
        # Kills the f-string-interpolation carve-out: an f-string WITH a
        # `{...}` interpolation is NOT a plain literal even though it
        # starts with a quote character.
        from frob.vet._capability_scan import _arg_looks_literal

        assert _arg_looks_literal(b'"run"') is True
        assert _arg_looks_literal(b'f"{name}"') is False
        assert _arg_looks_literal(b"name") is False

    def test_split_top_level_args_balances_nested_parens(self) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::_split_top_level_args kind="unit"  # noqa: E501
        from frob.vet._capability_scan import _split_top_level_args

        raw = b"getattr(foo(1, 2), name)) trailing"
        # start right after "getattr("
        args = _split_top_level_args(raw, len(b"getattr("))
        assert args == [b"foo(1, 2)", b" name"]

    def test_split_top_level_args_returns_none_when_unterminated(self) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::_split_top_level_args kind="unit"  # noqa: E501
        # Fail-closed: an unterminated call (truncated file / match found
        # inside an unhandled construct) returns None, which the caller
        # treats as "argument unknown" and fires rather than silently
        # passing.
        from frob.vet._capability_scan import _split_top_level_args

        assert _split_top_level_args(b"getattr(foo, name", len(b"getattr(")) is None

    def test_opaque_gate_emits_warn_severity_violation(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_opaque.py::opaque_gate kind="unit"
        import subprocess as sp

        from frob.gates._models import Severity
        from frob.gates._opaque import opaque_gate

        sp.run(["git", "init"], cwd=tmp_path, capture_output=True, check=True)
        pkg = tmp_path / "pkg.py"
        pkg.write_text("getattr(subprocess, name)(x)\n")
        sp.run(["git", "add", "pkg.py"], cwd=tmp_path, capture_output=True, check=True)

        violations = opaque_gate(tmp_path)
        assert len(violations) == 1
        assert violations[0].rule == "OPAQUE001"
        # T-1185: promoted WARN -> ERROR now that every named site is
        # fixed-or-waived repo-wide (promote-at-zero posture).
        assert violations[0].severity == Severity.ERROR
        assert violations[0].file == "pkg.py"

    def test_opaque_gate_no_findings_on_empty_tracked_set(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_opaque.py::opaque_gate kind="unit"
        from frob.gates._opaque import opaque_gate

        assert opaque_gate(tmp_path) == ()

    def test_waived_finding_is_suppressed_and_reason_recorded(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_opaque.py::opaque_gate kind="unit"
        # Acceptance criterion [1]: "Given the same construct with a
        # reasoned waiver, when checked, then it passes and the waiver
        # reason is recorded" -- the generic frob:waive engine
        # (frob.gates._apply_waivers) applies to OPAQUE001 the same way
        # it does to every other rule id, once the gate emits a real
        # Violation for it (this test proves that end to end).
        import subprocess as sp

        from frob.gates import _apply_waivers  # noqa: PLC0415 - internal, test-only
        from frob.gates._opaque import opaque_gate
        from frob.graph import build_graph

        sp.run(["git", "init"], cwd=tmp_path, capture_output=True, check=True)
        pkg = tmp_path / "pkg.py"
        pkg.write_text(
            '# frob:waive OPAQUE001 reason="name is a trusted enum member, '
            'not attacker input"\n'
            "getattr(subprocess, name)(x)\n"
        )
        sp.run(["git", "add", "pkg.py"], cwd=tmp_path, capture_output=True, check=True)

        violations = opaque_gate(tmp_path)
        assert len(violations) == 1

        cache = tmp_path / ".frob" / "cache.db"
        snap = build_graph(tmp_path, cache).danger_ok
        kept, waived = _apply_waivers(violations, snap)
        assert kept == ()
        assert len(waived) == 1
        assert waived[0].waived is not None
        assert "trusted enum member" in waived[0].waived.reason

    # -- T-0666: litmus fixtures for taxonomy runtime-opaque rows that have
    # NO entry in `RUNTIME_OPAQUE_CONSTRUCTS`/`OPAQUE_SOURCE_INVISIBLE` yet
    # (no detector, no fail-closed obligation, no excuse-registration).
    # Each of these locks the CURRENT honest gap -- `_opaque_indirection_
    # findings` returns no finding for the construct -- rather than leaving
    # the taxonomy row unregistered. This is real, un-addressed surface
    # against T-0339's acceptance [1] ("every runtime-opaque construct
    # FAILS CLOSED"); T-1047 (filed alongside this ticket's Done report)
    # tracks closing each of these by extending `RUNTIME_OPAQUE_CONSTRUCTS`
    # or, where the construct is genuinely source-invisible, adding a
    # REG011 excuse to `OPAQUE_SOURCE_INVISIBLE`.

    def test_python_exec_always_fires_regardless_of_argument(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::_opaque_indirection_findings kind="unit"  # noqa: E501
        # taxonomy "exec" row -- distinct construct_name from "eval" above;
        # RUNTIME_OPAQUE_CONSTRUCTS registers it separately (literal_arg_
        # index=None), so it should always fire, same shape as eval.
        from frob.vet._capability_scan import _opaque_indirection_findings

        pkg = tmp_path / "pkg.py"
        pkg.write_text('exec("import subprocess")\n')
        findings = _opaque_indirection_findings(pkg)
        assert any(f.construct_name == "exec" for f in findings)

    def test_python_dunder_import_computed_name_fires(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::_opaque_indirection_findings kind="unit"  # noqa: E501
        # taxonomy "`__import__` with computed module name" row.
        from frob.vet._capability_scan import _opaque_indirection_findings

        pkg = tmp_path / "pkg.py"
        pkg.write_text("__import__(mod_name).run(x)\n")
        findings = _opaque_indirection_findings(pkg)
        assert any(f.construct_name == "__import__" for f in findings)

    def test_python_setattr_monkeypatch_fires(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::_opaque_indirection_findings kind="unit"  # noqa: E501
        # taxonomy "monkeypatch / module attribute mutation" row.
        from frob.vet._capability_scan import _opaque_indirection_findings

        pkg = tmp_path / "pkg.py"
        pkg.write_text("setattr(subprocess, name, real_run)\n")
        findings = _opaque_indirection_findings(pkg)
        assert any(f.construct_name == "setattr" for f in findings)

    def test_python_container_dynamic_key_not_addressed(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::_opaque_indirection_findings kind="unit"  # noqa: E501
        # taxonomy "callable in a container, dynamic key" row (also covers
        # the sibling "computed member access, non-constant key" row --
        # identical `container[expr](...)` shape): `handlers[key](x)`.
        # Closed by T-1051's `RUNTIME_OPAQUE_STRUCTURAL_CONSTRUCTS`
        # generalized `subscript_call` detector (`_structural_opaque_
        # findings`) -- T-1047 left this unaddressed since the fixed-
        # needle+literal-arg architecture cannot express a non-constant
        # SUBSCRIPT shape, only a fixed call-name substring.
        from frob.vet._capability_scan import _opaque_indirection_findings

        pkg = tmp_path / "pkg.py"
        pkg.write_text('handlers = {"a": subprocess.run}\nhandlers[key](x)\n')
        findings = _opaque_indirection_findings(pkg)
        assert any(f.construct_name == "container dynamic-key call" for f in findings)

    def test_python_container_literal_key_call_not_addressed_by_structural_gate(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::_subscript_key_looks_literal kind="unit"  # noqa: E501
        # No-regression guard for the new structural detector: a LITERAL-
        # keyed subscript call (`handlers["a"](x)`) is the ORDINARY
        # resolver's job per T-0665's literal/non-literal split, not this
        # fail-closed obligation -- must not double-fire.
        from frob.vet._capability_scan import _opaque_indirection_findings

        pkg = tmp_path / "pkg.py"
        pkg.write_text('handlers = {"a": subprocess.run}\nhandlers["a"](x)\n')
        findings = _opaque_indirection_findings(pkg)
        assert findings == ()

    def test_opaque_structural_construct_is_frozen(self) -> None:
        # frob:waive COV006 reason="confirmed exercised: the test mutates \
        # RUNTIME_OPAQUE_STRUCTURAL_CONSTRUCTS[0], an instance of the bound class -- \
        # the best-effort callgraph only sees name( call tokens, not indexed-constant \
        # attribute mutation; same disposition as the evasion-taxonomy meta-test \
        # COV006 waivers"
        # frob:tests src/frob/vet/_capability_registry/_schemas.py::_OpaqueStructuralConstruct kind="unit"  # noqa: E501
        # T-1051: `_OpaqueStructuralConstruct.model_config = ConfigDict(
        # frozen=True)` (same immutability posture as `_OpaqueConstruct`
        # above it) must actually reject a post-construction mutation --
        # kills the `frozen=True` -> `frozen=False` mutant TEST016 flagged
        # with zero coverage.
        import pydantic

        from frob.vet._capability_registry import RUNTIME_OPAQUE_STRUCTURAL_CONSTRUCTS

        entry = RUNTIME_OPAQUE_STRUCTURAL_CONSTRUCTS[0]
        with pytest.raises(pydantic.ValidationError):
            entry.construct_name = "mutated"

    def test_python_functools_partial_dynamic_target_fires(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::_opaque_indirection_findings kind="unit"  # noqa: E501
        # taxonomy "`functools.partial`/decorator indirection with dynamic
        # target" row -- closed by T-1047 (RUNTIME_OPAQUE_CONSTRUCTS now
        # registers a `functools.partial(` needle).
        from frob.vet._capability_scan import _opaque_indirection_findings

        pkg = tmp_path / "pkg.py"
        pkg.write_text("functools.partial(resolve_target())(x)\n")
        findings = _opaque_indirection_findings(pkg)
        assert any(f.construct_name == "functools.partial" for f in findings)

    def test_python_dunder_getattr_class_interception_fires(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::_opaque_indirection_findings kind="unit"  # noqa: E501
        # taxonomy "class `__getattr__`/`__getattribute__` interception"
        # row -- closed by T-1047 (a `def __getattr__(` needle).
        from frob.vet._capability_scan import _opaque_indirection_findings

        pkg = tmp_path / "pkg.py"
        pkg.write_text(
            "class Proxy:\n"
            "    def __getattr__(self, name):\n"
            "        return subprocess.run\nobj = Proxy()\nobj.run(x)\n"
        )
        findings = _opaque_indirection_findings(pkg)
        assert any(f.construct_name == "__getattr__ interception" for f in findings)

    def test_python_sys_modules_replacement_fires(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::_opaque_indirection_findings kind="unit"  # noqa: E501
        # taxonomy "direct `sys.modules` replacement" row (added in the
        # taxonomy doc's Phase 2 pass) -- closed by T-1047 (a
        # `sys.modules[` needle).
        from frob.vet._capability_scan import _opaque_indirection_findings

        pkg = tmp_path / "pkg.py"
        pkg.write_text(
            'sys.modules["subprocess"] = fake_module\n'
            "import subprocess\nsubprocess.run(x)\n"
        )
        findings = _opaque_indirection_findings(pkg)
        assert any(f.construct_name == "sys.modules replacement" for f in findings)

    def test_typescript_computed_member_non_constant_key_not_addressed(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::_opaque_indirection_findings kind="unit"  # noqa: E501
        # taxonomy "computed member access, non-constant key" row -- closed
        # by T-1051's generalized `subscript_call` structural detector
        # (`_structural_opaque_findings`), the same shape T-1047 could not
        # express with a fixed needle.
        from frob.vet._capability_scan import _opaque_indirection_findings

        pkg = tmp_path / "pkg.ts"
        pkg.write_text("cp[key](x);\n")
        findings = _opaque_indirection_findings(pkg)
        assert any(f.construct_name == "container dynamic-key call" for f in findings)

    def test_typescript_global_this_bracket_fires(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::_opaque_indirection_findings kind="unit"  # noqa: E501
        # taxonomy "`globalThis[name]`" row -- closed by T-1047 (a
        # `globalThis[` needle).
        from frob.vet._capability_scan import _opaque_indirection_findings

        pkg = tmp_path / "pkg.ts"
        pkg.write_text("globalThis[name](x);\n")
        findings = _opaque_indirection_findings(pkg)
        assert any(f.construct_name == "globalThis[name]" for f in findings)

    def test_typescript_reflect_apply_dynamic_target_fires(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::_opaque_indirection_findings kind="unit"  # noqa: E501
        # taxonomy "`Reflect.get`/`Reflect.apply` with dynamic target" row
        # -- closed by T-1047 (`Reflect.get(`/`Reflect.apply(` needles).
        from frob.vet._capability_scan import _opaque_indirection_findings

        pkg = tmp_path / "pkg.ts"
        pkg.write_text("Reflect.apply(Reflect.get(cp, key), null, [x]);\n")
        findings = _opaque_indirection_findings(pkg)
        names = {f.construct_name for f in findings}
        assert "Reflect.get" in names
        assert "Reflect.apply" in names

    def test_typescript_proxy_interception_fires(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::_opaque_indirection_findings kind="unit"  # noqa: E501
        # taxonomy "`Proxy` interception (`get`/`apply` traps)" row --
        # closed by T-1047 (a `new Proxy(` needle).
        from frob.vet._capability_scan import _opaque_indirection_findings

        pkg = tmp_path / "pkg.ts"
        pkg.write_text("new Proxy(cp, { get(){ return cp.exec; } }).run(x);\n")
        findings = _opaque_indirection_findings(pkg)
        assert any(f.construct_name == "Proxy interception" for f in findings)

    def test_typescript_container_dynamic_key_not_addressed(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::_opaque_indirection_findings kind="unit"  # noqa: E501
        # taxonomy "callable in container, dynamic key" row -- closed by
        # T-1051's generalized `subscript_call` structural detector.
        from frob.vet._capability_scan import _opaque_indirection_findings

        pkg = tmp_path / "pkg.ts"
        pkg.write_text("handlers[key](x);\n")
        findings = _opaque_indirection_findings(pkg)
        assert any(f.construct_name == "container dynamic-key call" for f in findings)

    def test_typescript_monkeypatch_module_namespace_fires(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::_opaque_indirection_findings kind="unit"  # noqa: E501
        # taxonomy "monkeypatch / property mutation on module namespace
        # object" row -- closed by T-1047 (a `require.cache[` needle).
        from frob.vet._capability_scan import _opaque_indirection_findings

        pkg = tmp_path / "pkg.ts"
        pkg.write_text("require.cache[id].exports.exec = realExec;\n")
        findings = _opaque_indirection_findings(pkg)
        assert any(f.construct_name == "monkeypatch module namespace" for f in findings)

    def test_c_array_nonconstant_index_not_addressed(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::_opaque_indirection_findings kind="unit"  # noqa: E501
        # taxonomy "function pointer read via array/struct with non-
        # constant index/selector" row. The ORDINARY resolver still proves
        # this stays UNDETECTED as a resolution
        # (`test_array_fn_ptr_nonconstant_index_not_detected`, unchanged --
        # that is a SEPARATE, still-open gap in the ordinary resolver's own
        # points-to); this fixture proves the fail-closed OBLIGATION gate
        # now catches it via T-1051's generalized `subscript_call`
        # structural detector, closing THIS row.
        from frob.vet._capability_scan import _opaque_indirection_findings

        pkg = tmp_path / "pkg.c"
        pkg.write_text(
            "void (*tbl[])(const char*) = { system };\n"
            'void g(int user_selected_index) { tbl[user_selected_index]("sh"); }\n'
        )
        findings = _opaque_indirection_findings(pkg)
        assert any(
            f.construct_name == "array-index function-pointer dispatch"
            for f in findings
        )

    def test_c_integer_cast_to_function_pointer_not_addressed(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::_opaque_indirection_findings kind="unit"  # noqa: E501
        # taxonomy "function pointer cast from an integer/opaque value" row
        # -- closed by T-1051's `explicit_fnptr_cast_call` structural
        # detector (`((RET(*)(ARGS))expr)(...)`).
        from frob.vet._capability_scan import _opaque_indirection_findings

        pkg = tmp_path / "pkg.c"
        pkg.write_text('void g(long addr) { ((void(*)(const char*))addr)("sh"); }\n')
        findings = _opaque_indirection_findings(pkg)
        assert any(
            f.construct_name == "integer-cast to function pointer" for f in findings
        )

    def test_c_void_star_backcast_not_addressed(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::_opaque_indirection_findings kind="unit"  # noqa: E501
        # taxonomy "function pointer through `void*` indirection and
        # back-cast" row -- closed by T-1051's `named_type_cast_call`
        # structural detector (`((TypeName)expr)(...)`).
        from frob.vet._capability_scan import _opaque_indirection_findings

        pkg = tmp_path / "pkg.c"
        pkg.write_text(
            "typedef void (*Handler)(const char*);\n"
            'void g() { void *p = get_handler(); ((Handler)p)("sh"); }\n'
        )
        findings = _opaque_indirection_findings(pkg)
        assert any(
            f.construct_name == "void* back-cast to function pointer" for f in findings
        )

    def test_cpp_array_runtime_index_not_addressed(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::_opaque_indirection_findings kind="unit"  # noqa: E501
        # taxonomy "function pointer through array/vector with runtime
        # index" row -- closed by T-1051's `subscript_call` structural
        # detector (same shape as the sibling C row above, `.cpp`
        # extension exercises the identical `language="c-cpp"` bucket).
        from frob.vet._capability_scan import _opaque_indirection_findings

        pkg = tmp_path / "pkg.cpp"
        pkg.write_text(
            "void g(int user_idx) {\n"
            "    void (*handlers[])(const char*) = { system };\n"
            '    handlers[user_idx]("sh");\n'
            "}\n"
        )
        findings = _opaque_indirection_findings(pkg)
        assert any(
            f.construct_name == "array-index function-pointer dispatch"
            for f in findings
        )

    def test_cpp_reinterpret_cast_to_function_pointer_fires(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::_opaque_indirection_findings kind="unit"  # noqa: E501
        # taxonomy "`reinterpret_cast` from an integer/opaque handle" row
        # -- closed by T-1047 (a `reinterpret_cast<` needle).
        from frob.vet._capability_scan import _opaque_indirection_findings

        pkg = tmp_path / "pkg.cpp"
        pkg.write_text(
            "typedef void (*Handler)(const char*);\n"
            'void g(long addr) { reinterpret_cast<Handler>(addr)("sh"); }\n'
        )
        findings = _opaque_indirection_findings(pkg)
        assert any(
            f.construct_name == "reinterpret_cast to function pointer" for f in findings
        )

    def test_cpp_rtti_driven_dispatch_fires(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::_opaque_indirection_findings kind="unit"  # noqa: E501
        # taxonomy "RTTI-driven dispatch (`typeid`/`dynamic_cast`)" row --
        # closed by T-1047 (a `typeid(` needle).
        from frob.vet._capability_scan import _opaque_indirection_findings

        pkg = tmp_path / "pkg.cpp"
        pkg.write_text(
            "void g(Base *obj) {\n"
            '    if (typeid(*obj) == typeid(Derived)) { system("sh"); }\n'
            "}\n"
        )
        findings = _opaque_indirection_findings(pkg)
        assert any(f.construct_name == "RTTI-driven dispatch" for f in findings)

    def test_rust_trait_object_dynamic_dispatch_not_addressed(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::_opaque_indirection_findings kind="unit"  # noqa: E501
        # taxonomy "trait-object dynamic dispatch" row. Bounded-polymorphism
        # dispatch through a statically-enumerable impl set is explicitly
        # OUT of this gate's scope by design (`_opaque.py`'s own module
        # docstring) -- but no `frob:enforces`/registry cross-check
        # currently distinguishes "bounded, in-repo impl set" from "open,
        # plugin-arriving" trait objects for Rust specifically the way the
        # gate's docstring claims is handled; this fixture records the
        # current as-built behavior (silent) rather than asserting the
        # nuanced claim is fully implemented -- see T-1047.
        from frob.vet._capability_scan import _opaque_indirection_findings

        pkg = tmp_path / "pkg.rs"
        pkg.write_text(
            "trait Spawn { fn spawn(&self, x: &str); }\n"
            "fn g(s: &dyn Spawn, x: &str) { s.spawn(x); }\n"
        )
        findings = _opaque_indirection_findings(pkg)
        assert findings == ()

    def test_rust_extern_ffi_symbol_excused_source_invisible(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability_registry/_opaque.py::OPAQUE_SOURCE_INVISIBLE kind="unit"  # noqa: E501
        # taxonomy "`extern` block FFI symbol binding resolved by the
        # dynamic linker" row. Same source-invisible shape as the C
        # weak-symbol row `OPAQUE_SOURCE_INVISIBLE` already excuses (T-0665)
        # -- closed by T-1047: a dedicated rust `extern`-block excuse entry
        # now exists (distinct from the vtable-patch entry). No finding
        # fires (source-invisible, category-3 per T-0665 doctrine) but the
        # accountability record is asserted, not silent non-detection.
        from frob.vet._capability_scan import _opaque_indirection_findings
        from frob.vet._capability_registry import OPAQUE_SOURCE_INVISIBLE

        pkg = tmp_path / "pkg.rs"
        pkg.write_text(
            'extern "C" { fn run_cmd(s: *const i8); }\n'
            "fn g(x: *const i8) { unsafe { run_cmd(x); } }\n"
        )
        findings = _opaque_indirection_findings(pkg)
        assert findings == ()
        rust_excuses = [e for e in OPAQUE_SOURCE_INVISIBLE if e.language == "rust"]
        assert any("extern" in e.reason for e in rust_excuses)

    def test_rust_function_pointer_in_container_fires(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::_opaque_indirection_findings kind="unit"  # noqa: E501
        # taxonomy "function pointer stored in and read from a container"
        # row -- closed by T-1047 (a `Vec<fn(` needle).
        from frob.vet._capability_scan import _opaque_indirection_findings

        pkg = tmp_path / "pkg.rs"
        pkg.write_text(
            "use std::process::Command as C;\n"
            'fn g(i: usize, v: Vec<fn(&str)>) { v[i]("sh"); }\n'
        )
        findings = _opaque_indirection_findings(pkg)
        assert any(
            f.construct_name == "function pointer in container" for f in findings
        )

    def test_rust_boxed_dyn_fn_runtime_selected_fires(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::_opaque_indirection_findings kind="unit"  # noqa: E501
        # taxonomy "`Box<dyn Fn>` built from a runtime-selected source" row
        # -- closed by T-1047 (a `Box<dyn Fn` needle).
        from frob.vet._capability_scan import _opaque_indirection_findings

        pkg = tmp_path / "pkg.rs"
        pkg.write_text(
            "fn g(cond: bool, a: fn(&str), b: fn(&str), x: &str) {\n"
            "    let f: Box<dyn Fn(&str)> = if cond { Box::new(a) } else { Box::new(b) };\n"
            "    f(x);\n"
            "}\n"
        )
        findings = _opaque_indirection_findings(pkg)
        assert any(f.construct_name == "Box<dyn Fn> runtime-selected" for f in findings)

    def test_rust_proc_macro_synthesized_call_excused_source_invisible(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability_registry/_opaque.py::OPAQUE_SOURCE_INVISIBLE kind="unit"  # noqa: E501
        # taxonomy "procedural / derive macros synthesizing a call from
        # external input" row -- mirrors the `macro_rules!` resolver gap
        # `test_macro_rules_expansion_emitting_fixed_call_not_detected`
        # already locks for the ordinary resolver (that resolver-level
        # gap remains open, tracked separately). This is the fail-closed-
        # obligation-gate sibling: closed by T-1047 with a dedicated rust
        # proc-macro excuse entry (category-3, source-invisible -- the
        # expansion never appears in this file's text at all).
        from frob.vet._capability_scan import _opaque_indirection_findings
        from frob.vet._capability_registry import OPAQUE_SOURCE_INVISIBLE

        pkg = tmp_path / "pkg.rs"
        pkg.write_text("#[derive(RunFromAttribute)]\nstruct Job;\n")
        findings = _opaque_indirection_findings(pkg)
        assert findings == ()
        rust_excuses = [e for e in OPAQUE_SOURCE_INVISIBLE if e.language == "rust"]
        assert any("proc" in e.reason or "macro" in e.reason for e in rust_excuses)

    def test_kotlin_function_value_in_container_fires(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::_opaque_indirection_findings kind="unit"  # noqa: E501
        # taxonomy "function value stored in and read from a container" row
        # -- closed by T-1047 (a `]!!(` needle).
        from frob.vet._capability_scan import _opaque_indirection_findings

        pkg = tmp_path / "pkg.kt"
        pkg.write_text(
            'val handlers: Map<String, (String) -> Unit> = mapOf("a" to ::ProcessBuilder)\n'
            'fun g(key: String) { handlers[key]!!("sh") }\n'
        )
        findings = _opaque_indirection_findings(pkg)
        assert any(f.construct_name == "function value in container" for f in findings)

    def test_kotlin_delegated_property_by_fires(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::_opaque_indirection_findings kind="unit"  # noqa: E501
        # taxonomy "delegated property / `by` indirection resolving at
        # runtime" row -- closed by T-1047 (a `by lazy {` needle).
        from frob.vet._capability_scan import _opaque_indirection_findings

        pkg = tmp_path / "pkg.kt"
        pkg.write_text(
            "val f: (String) -> Unit by lazy { ::ProcessBuilder }\n"
            'fun g() { f("sh") }\n'
        )
        findings = _opaque_indirection_findings(pkg)
        assert any(f.construct_name == "delegated property by" for f in findings)

    def test_kotlin_dynamic_classloading_fires(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::_opaque_indirection_findings kind="unit"  # noqa: E501
        # taxonomy "dynamic classloading (`URLClassLoader` etc.)" row --
        # closed by T-1047 (a `URLClassLoader(` needle).
        from frob.vet._capability_scan import _opaque_indirection_findings

        pkg = tmp_path / "pkg.kt"
        pkg.write_text(
            "fun g(clsName: String) {\n"
            "    val cls = URLClassLoader(arrayOf()).loadClass(clsName)\n"
            "}\n"
        )
        findings = _opaque_indirection_findings(pkg)
        assert any(f.construct_name == "dynamic classloading" for f in findings)

    def test_kotlin_kcallable_call_always_fires(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::_opaque_indirection_findings kind="unit"  # noqa: E501
        # taxonomy "`KFunction`/`KCallable.call` obtained dynamically" row
        # -- RUNTIME_OPAQUE_CONSTRUCTS registers a separate "KCallable.call"
        # entry (deliberately broad `.call(` needle, literal_arg_index=
        # None) from the "Class.forName" entry above.
        from frob.vet._capability_scan import _opaque_indirection_findings

        pkg = tmp_path / "pkg.kt"
        pkg.write_text(
            "fun g(methodName: String, target: Any, x: String) {\n"
            "    val f = target::class.members.first { it.name == methodName }\n"
            "    f.call(x)\n"
            "}\n"
        )
        findings = _opaque_indirection_findings(pkg)
        assert any(f.construct_name == "KCallable.call" for f in findings)

    def test_typescript_eval_always_fires_regardless_of_argument(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::_opaque_indirection_findings kind="unit"  # noqa: E501
        # taxonomy "`eval`" row (TS/JS's own copy of the construct Python's
        # `eval` row above already locks a sibling fixture for) --
        # RUNTIME_OPAQUE_CONSTRUCTS registers a separate `language=
        # "typescript"` "eval" entry (literal_arg_index=None), so this row
        # needs its own litmus rather than reusing Python's.
        from frob.vet._capability_scan import _opaque_indirection_findings

        pkg = tmp_path / "pkg.ts"
        pkg.write_text("eval(\"require('child_process').exec(x)\");\n")
        findings = _opaque_indirection_findings(pkg)
        assert any(f.construct_name == "eval" for f in findings)

    def test_typescript_function_constructor_always_fires(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::_opaque_indirection_findings kind="unit"  # noqa: E501
        # taxonomy "`new Function(...)`" row.
        from frob.vet._capability_scan import _opaque_indirection_findings

        pkg = tmp_path / "pkg.ts"
        pkg.write_text(
            'new Function("x", "return require(\'child_process\').exec(x)")(x);\n'
        )
        findings = _opaque_indirection_findings(pkg)
        assert any(f.construct_name == "Function constructor" for f in findings)

    def test_c_weak_symbol_override_excused_source_invisible(self) -> None:
        # frob:tests src/frob/vet/_capability_registry/_opaque.py::OPAQUE_SOURCE_INVISIBLE kind="unit"  # noqa: E501
        # taxonomy "weak-symbol override resolved by the linker/loader" row
        # (C). Unlike the other C runtime rows, this one is DELIBERATELY
        # not a fixture-with-a-finding: the T-0665 sign-off excuses it via
        # a REG011-compliant "none -- <explanation>" disposition in
        # `OPAQUE_SOURCE_INVISIBLE` rather than a detector, since no
        # per-source-file scan can see linker-level symbol interposition.
        # This litmus locks that the excuse entry itself still exists
        # (a REG011 accountability record, not silence).
        from frob.vet._capability_registry import OPAQUE_SOURCE_INVISIBLE

        c_cpp_excuses = [e for e in OPAQUE_SOURCE_INVISIBLE if e.language == "c-cpp"]
        assert len(c_cpp_excuses) == 1
        assert "weak-symbol" in c_cpp_excuses[0].reason

    def test_rust_runtime_vtable_patch_excused_source_invisible(self) -> None:
        # frob:tests src/frob/vet/_capability_registry/_opaque.py::OPAQUE_SOURCE_INVISIBLE kind="unit"  # noqa: E501
        # Rust's own `OPAQUE_SOURCE_INVISIBLE` entries: a runtime vtable
        # patch (unsafe raw-pointer rewrite of a trait object's vtable
        # slot), plus, as of T-1047, a dedicated `extern` FFI symbol
        # excuse and a proc-macro-expansion excuse (each its own entry,
        # each its own reason -- REG011 per-entry accountability, not a
        # shared blanket rust exemption). This litmus locks that the
        # vtable-patch excuse specifically still exists among however
        # many rust entries there are, so a future edit cannot silently
        # drop it.
        from frob.vet._capability_registry import OPAQUE_SOURCE_INVISIBLE

        rust_excuses = [e for e in OPAQUE_SOURCE_INVISIBLE if e.language == "rust"]
        assert len(rust_excuses) == 3
        vtable_excuses = [e for e in rust_excuses if "vtable" in e.reason]
        assert len(vtable_excuses) == 1
        assert "vtable" in rust_excuses[0].reason

    def test_cpp_virtual_dispatch_bounded_polymorphism_no_finding(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::_opaque_indirection_findings kind="unit"  # noqa: E501
        # taxonomy "virtual dispatch through a base pointer" row.
        # `_opaque.py`'s own module docstring carves BOUNDED POLYMORPHISM
        # (ordinary virtual dispatch whose implementation set is statically
        # enumerable in-repo) OUT of this gate's scope by design -- not a
        # gap, a deliberate exclusion, since the may-analysis is sound over
        # the statically-visible override set. This litmus locks that
        # design intent: an ordinary virtual call produces no
        # opaque-indirection finding.
        from frob.vet._capability_scan import _opaque_indirection_findings

        pkg = tmp_path / "pkg.cpp"
        pkg.write_text(
            "struct Base { virtual void run(const char*) = 0; };\n"
            "struct Derived : Base { void run(const char* x) override { system(x); } };\n"
            "void g(Base *base, const char *x) { base->run(x); }\n"
        )
        findings = _opaque_indirection_findings(pkg)
        assert findings == ()


class TestEvasionTaxonomyExhaustiveness:
    """T-0666: cross-language exhaustiveness meta-test. Parses
    `docs/design/capability-evasion-taxonomy.md`'s per-language tables AT
    TEST TIME (not a hardcoded copy of the row counts) and asserts every
    row maps to >=1 registered litmus fixture via
    `frob.vet._evasion_coverage._EVASION_LITMUS_MAP` -- the explicit,
    greppable, statically-checkable registration T-0666's own acceptance
    criteria require. Validates BOTH directions (the "dangling test refs"
    check): (1) the doc's row COUNT per (language, category) never exceeds
    the map's registered litmus COUNT for that pair (a new taxonomy row
    added with no matching new fixture fails the build, acceptance [1]);
    (2) every dotted `Class.method` path the map lists actually resolves
    to a real test defined in this file (a stale/renamed reference fails
    the build too, not silently passes)."""

    _TAXONOMY_DOC = (
        Path(__file__).resolve().parent.parent
        / "docs"
        / "design"
        / "capability-evasion-taxonomy.md"
    )

    @staticmethod
    def _doc_row_counts() -> dict[tuple[str, str], int]:
        # frob:tests tests/test_vet.py::TestEvasionTaxonomyExhaustiveness kind="unit"
        """Parse the taxonomy doc's `## <Language>` sections at call time,
        counting `| static |...` and `| runtime |...` table rows under
        each heading -- the doc IS the denominator, never a hardcoded
        number in this test module."""
        from frob.vet._evasion_coverage import _DOC_HEADING_TO_LANGUAGE_KEY

        text = TestEvasionTaxonomyExhaustiveness._TAXONOMY_DOC.read_text()
        counts: dict[tuple[str, str], int] = {}
        current_key: str | None = None
        for line in text.splitlines():
            if line.startswith("## "):
                heading = line[3:].strip()
                current_key = _DOC_HEADING_TO_LANGUAGE_KEY.get(heading)
                continue
            if current_key is None:
                continue
            if line.startswith("| static |"):
                counts[(current_key, "static")] = (
                    counts.get((current_key, "static"), 0) + 1
                )
            elif line.startswith("| runtime |"):
                counts[(current_key, "runtime")] = (
                    counts.get((current_key, "runtime"), 0) + 1
                )
        return counts

    def test_every_doc_heading_recognized(self) -> None:
        # frob:tests src/frob/vet/_evasion_coverage.py::_DOC_HEADING_TO_LANGUAGE_KEY kind="unit"  # noqa: E501
        # frob:waive COV006 reason="T-1024: genuinely read directly by this test (dict subscript/iteration/membership, not a call), which frob.graph.callgraph's best-effort reachability heuristic cannot see"  # noqa: E501
        # Dangling-heading check: every `## <Language>` heading actually
        # present in the taxonomy doc must be a key
        # `_DOC_HEADING_TO_LANGUAGE_KEY` recognizes -- a renamed heading
        # (e.g. "TypeScript / JavaScript" -> "TypeScript/JavaScript") would
        # otherwise silently drop that language's rows from the count
        # entirely rather than failing loudly.
        from frob.vet._evasion_coverage import _DOC_HEADING_TO_LANGUAGE_KEY

        text = self._TAXONOMY_DOC.read_text()
        doc_headings = {
            line[3:].strip() for line in text.splitlines() if line.startswith("## ")
        }
        # The doc also carries non-language headings (Purpose, Combined
        # coverage table, Honesty and sourcing) -- only assert every
        # KNOWN-LANGUAGE heading this map claims to cover is genuinely
        # present verbatim (the reverse of "every doc heading is mapped").
        for heading in _DOC_HEADING_TO_LANGUAGE_KEY:
            assert heading in doc_headings, (
                f"_DOC_HEADING_TO_LANGUAGE_KEY claims heading {heading!r} "
                "but it is not present verbatim in "
                "capability-evasion-taxonomy.md -- stale mapping"
            )

    def test_every_litmus_path_resolves_to_a_real_test(self) -> None:
        # frob:tests src/frob/vet/_evasion_coverage.py::_EVASION_LITMUS_MAP kind="unit"
        # frob:waive COV006 reason="T-1024: genuinely read directly by this test (dict subscript/iteration/membership, not a call), which frob.graph.callgraph's best-effort reachability heuristic cannot see"  # noqa: E501
        # Dangling-ref check (direction 2): every "Class.method" string in
        # _EVASION_LITMUS_MAP must be a REAL class+method actually defined
        # in this file -- a typo'd or renamed-but-not-updated reference
        # fails loudly rather than silently claiming coverage that does
        # not exist. Uses `ast` (static, no pytest-collect dependency) so
        # this check has no test-runner-ordering hazard.
        import ast

        from frob.vet._evasion_coverage import _EVASION_LITMUS_MAP

        source = Path(__file__).read_text()
        tree = ast.parse(source)
        real: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for child in node.body:
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        real.add(f"{node.name}.{child.name}")

        missing: list[str] = []
        for (language, category), paths in _EVASION_LITMUS_MAP.items():
            for path in paths:
                if path not in real:
                    missing.append(f"{language}/{category}: {path}")
        assert not missing, (
            "_EVASION_LITMUS_MAP references test(s) that do not exist in "
            f"tests/test_vet.py: {missing}"
        )

    def test_every_taxonomy_row_has_sufficient_registered_litmus_coverage(
        self,
    ) -> None:
        # frob:tests src/frob/vet/_evasion_coverage.py::_EVASION_LITMUS_MAP kind="unit"
        # frob:waive COV006 reason="T-1024: genuinely read directly by this test (dict subscript/iteration/membership, not a call), which frob.graph.callgraph's best-effort reachability heuristic cannot see"  # noqa: E501
        # Acceptance [0]: "given the full evasion taxonomy denominator,
        # when the meta-test runs, then every entry maps to >=1 registered
        # litmus fixture." Acceptance [1]: "given a new taxonomy entry
        # added with no fixture, when the meta-test runs, then it fails
        # the build" -- this is the count-floor check that makes that
        # true: the doc's own row count per (language, category), parsed
        # fresh every run, must never exceed the number of litmus paths
        # registered for that pair.
        from frob.vet._evasion_coverage import _EVASION_LITMUS_MAP

        doc_counts = self._doc_row_counts()
        shortfalls: list[str] = []
        for key, doc_count in doc_counts.items():
            registered = len(_EVASION_LITMUS_MAP.get(key, ()))
            if registered < doc_count:
                shortfalls.append(
                    f"{key[0]}/{key[1]}: doc has {doc_count} row(s), only "
                    f"{registered} litmus path(s) registered in "
                    "_EVASION_LITMUS_MAP -- add the missing fixture(s)"
                )
        assert not shortfalls, "\n".join(shortfalls)

    def test_map_has_no_orphaned_language_category_pairs(self) -> None:
        # frob:tests src/frob/vet/_evasion_coverage.py::_EVASION_LITMUS_MAP kind="unit"
        # frob:waive COV006 reason="T-1024: genuinely read directly by this test (dict subscript/iteration/membership, not a call), which frob.graph.callgraph's best-effort reachability heuristic cannot see"  # noqa: E501
        # Reverse sanity: every (language, category) key in
        # _EVASION_LITMUS_MAP must correspond to a pair the doc actually has
        # at least one row for -- catches a typo'd language/category key
        # in the map itself (e.g. "kotln" or "statc") that would otherwise
        # silently register litmus paths nothing ever cross-checks.
        from frob.vet._evasion_coverage import _EVASION_LITMUS_MAP

        doc_counts = self._doc_row_counts()
        orphaned = [key for key in _EVASION_LITMUS_MAP if key not in doc_counts]
        assert not orphaned, (
            f"_EVASION_LITMUS_MAP has key(s) with no matching doc rows: {orphaned}"
        )

    def test_combined_registered_total_matches_112_entry_denominator(self) -> None:
        # frob:tests src/frob/vet/_evasion_coverage.py::_EVASION_LITMUS_MAP kind="unit"
        # frob:waive COV006 reason="T-1024: genuinely read directly by this test (dict subscript/iteration/membership, not a call), which frob.graph.callgraph's best-effort reachability heuristic cannot see"  # noqa: E501
        # T-0339's own framing (and `docs/design/registry/evasion.yaml`'s
        # 112 EVA-<LANG>-<S|R><NN> ids, reconciled in
        # `docs/design/registry/RECONCILIATION.md`) name 112 as the
        # working denominator. This locks that _EVASION_LITMUS_MAP's total
        # registered litmus count is >= 112 -- never fewer than the
        # reconciled registry total, even though (per this test class's
        # own module docstring) the taxonomy doc's OWN raw table-row count
        # is higher for python's two extra rows found this pass (see this
        # ticket's Done report for the doc-vs-registry count-mismatch
        # finding, filed as a documentation-accuracy follow-up rather than
        # resolved here since docs/design/capability-evasion-taxonomy.md
        # is outside T-0666's declared scope).
        from frob.vet._evasion_coverage import _EVASION_LITMUS_MAP

        total = sum(len(v) for v in _EVASION_LITMUS_MAP.values())
        assert total >= 112, (
            f"_EVASION_LITMUS_MAP total registered litmus paths ({total}) is "
            "below the 112-entry reconciled denominator"
        )


class TestSupplyChainUnpinnedDependencies:
    """T-1088: VET007, SC-ATTACK-UNPINNED-DEPENDENCIES."""

    def test_pyproject_caret_range_flagged(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_supplychain.py::_unpinned_dependency_violations \
        # kind="unit"
        from frob.vet._supplychain import _unpinned_dependency_violations

        (tmp_path / "pyproject.toml").write_text(
            'dependencies = [\n  "requests>=2.0",\n  "typani==0.0.3",\n]\n'
        )
        violations = _unpinned_dependency_violations(tmp_path)
        rules = {v.rule for v in violations}
        assert "VET007" in rules
        messages = " ".join(v.message for v in violations)
        assert "requests" in messages
        assert "typani" not in messages

    def test_pyproject_exact_pin_not_flagged(self, tmp_path: Path) -> None:
        from frob.vet._supplychain import _unpinned_dependency_violations

        (tmp_path / "pyproject.toml").write_text(
            'dependencies = [\n  "typani==0.0.3",\n]\n'
        )
        violations = _unpinned_dependency_violations(tmp_path)
        assert violations == []

    def test_package_json_wildcard_flagged(self, tmp_path: Path) -> None:
        from frob.vet._supplychain import _unpinned_dependency_violations

        (tmp_path / "package.json").write_text(
            '{"dependencies": {"lodash": "*", "left-pad": "1.3.0"}}\n'
        )
        violations = _unpinned_dependency_violations(tmp_path)
        rules = {v.rule for v in violations}
        assert "VET007" in rules
        messages = " ".join(v.message for v in violations)
        assert "lodash" in messages
        assert "left-pad" not in messages

    def test_cargo_toml_caret_flagged(self, tmp_path: Path) -> None:
        from frob.vet._supplychain import _unpinned_dependency_violations

        (tmp_path / "Cargo.toml").write_text(
            '[dependencies]\nserde = "^1.0"\nlibc = "0.2.150"\n'
        )
        violations = _unpinned_dependency_violations(tmp_path)
        rules = {v.rule for v in violations}
        assert "VET007" in rules
        messages = " ".join(v.message for v in violations)
        assert "serde" in messages
        assert "libc" not in messages


class TestSupplyChainInstallArtifacts:
    """T-1088: VET008, SC-DETECTION-PYTHON-INSTALL-ARTIFACTS."""

    def test_setup_py_absolute_data_files_flagged(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_supplychain.py::_python_install_artifact_violations \
        # kind="unit"
        from frob.vet._supplychain import _python_install_artifact_violations

        (tmp_path / "setup.py").write_text(
            "from setuptools import setup\n"
            "setup(data_files=[('/etc/cron.d', ['evil.cron'])])\n"
        )
        violations = _python_install_artifact_violations(tmp_path)
        assert any(v.rule == "VET008" for v in violations)

    def test_setup_py_traversal_data_files_flagged(self, tmp_path: Path) -> None:
        from frob.vet._supplychain import _python_install_artifact_violations

        (tmp_path / "setup.py").write_text(
            "from setuptools import setup\n"
            "setup(data_files=[('../../etc', ['evil'])])\n"
        )
        violations = _python_install_artifact_violations(tmp_path)
        assert any(v.rule == "VET008" for v in violations)

    def test_setup_py_package_relative_data_files_not_flagged(
        self, tmp_path: Path
    ) -> None:
        from frob.vet._supplychain import _python_install_artifact_violations

        (tmp_path / "setup.py").write_text(
            "from setuptools import setup\n"
            "setup(data_files=[('share/pkg', ['data.json'])])\n"
        )
        violations = _python_install_artifact_violations(tmp_path)
        assert violations == []

    def test_no_setup_py_not_flagged(self, tmp_path: Path) -> None:
        from frob.vet._supplychain import _python_install_artifact_violations

        assert _python_install_artifact_violations(tmp_path) == []


class TestSupplyChainCiActionPin:
    """T-1088: VET009, SC-DETECTION-UNPINNED-CI-ACTION."""

    def test_workflow_branch_ref_flagged(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_supplychain.py::_unpinned_ci_action_violations \
        # kind="unit"
        from frob.vet._supplychain import _unpinned_ci_action_violations

        workflows = tmp_path / ".github" / "workflows"
        workflows.mkdir(parents=True)
        (workflows / "ci.yaml").write_text(
            "jobs:\n  build:\n    steps:\n      - uses: actions/checkout@main\n"
        )
        violations = _unpinned_ci_action_violations(tmp_path)
        assert any(v.rule == "VET009" for v in violations)

    def test_workflow_full_sha_ref_not_flagged(self, tmp_path: Path) -> None:
        from frob.vet._supplychain import _unpinned_ci_action_violations

        workflows = tmp_path / ".github" / "workflows"
        workflows.mkdir(parents=True)
        (workflows / "ci.yaml").write_text(
            "jobs:\n  build:\n    steps:\n"
            "      - uses: actions/checkout@"
            "8f4b7f84864484a7bde6ce6dbe0021e11a91c0f4\n"
        )
        violations = _unpinned_ci_action_violations(tmp_path)
        assert violations == []

    def test_no_workflows_dir_not_flagged(self, tmp_path: Path) -> None:
        from frob.vet._supplychain import _unpinned_ci_action_violations

        assert _unpinned_ci_action_violations(tmp_path) == []


class TestSupplyChainOpaqueBinaryArtifact:
    """T-1088: VET010, SC-DETECTION-OPAQUE-BINARY-ARTIFACT."""

    def test_tracked_so_without_recipe_flagged(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_supplychain.py::_opaque_binary_artifact_violations \
        # kind="unit"
        from frob.vet._supplychain import _opaque_binary_artifact_violations

        blob_dir = tmp_path / "vendor"
        blob_dir.mkdir()
        (blob_dir / "mystery.so").write_bytes(b"\x7fELF")
        violations = _opaque_binary_artifact_violations(tmp_path)
        assert any(v.rule == "VET010" for v in violations)

    def test_so_with_nearby_cargo_toml_not_flagged(self, tmp_path: Path) -> None:
        from frob.vet._supplychain import _opaque_binary_artifact_violations

        crate_dir = tmp_path / "native"
        crate_dir.mkdir()
        (crate_dir / "Cargo.toml").write_text('[package]\nname = "native"\n')
        (crate_dir / "built.so").write_bytes(b"\x7fELF")
        violations = _opaque_binary_artifact_violations(tmp_path)
        assert violations == []

    def test_no_binary_files_not_flagged(self, tmp_path: Path) -> None:
        from frob.vet._supplychain import _opaque_binary_artifact_violations

        (tmp_path / "readme.txt").write_text("hello\n")
        assert _opaque_binary_artifact_violations(tmp_path) == []


# frob:ticket T-1433
class TestOperationEntryMatchesFallthrough:
    """T-1465: `_operation_entry_matches` must return `False`
    (not implicitly `None`, ty's invalid-return-type finding) for an
    entry with no `needles` whose `function_or_pattern` is not a
    Python bare-`compile(` special case -- the fallthrough branch."""

    # frob:ticket T-1433
    def test_no_needles_and_not_bare_compile_returns_false(self) -> None:
        # frob:tests src/frob/vet/_capability_core.py::_operation_entry_matches \
        # kind="unit"
        from frob.vet._capability_core import _operation_entry_matches
        from frob.vet._capability_registry._schemas import _DangerousOperation

        entry = _DangerousOperation(
            language="python",
            library="os",
            function_or_pattern="os.system(",
            capability_kind="exec",
            rationale="test fixture",
            safer_alternative="subprocess.run",
            severity="high",
            needles=(),
        )
        result = _operation_entry_matches(entry, b"nothing relevant here", ())
        assert result is False

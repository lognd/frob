"""Tests for `frob.vet._capability_registry` (T-0158): the single-source
capability-kind enumeration, the structured `DangerousOperation` registry,
and the (kind x language) coverage matrix -- plus per-cell fire fixtures
proving representative patterned entries actually fire through
`frob.vet._capability.scan_file_capabilities`/`scan_file_operations`
(T-0145 drift-lock style: a pattern with zero firing evidence is as good
as absent)."""

from __future__ import annotations

from pathlib import Path

import pytest

from frob.vet._capability import scan_file_capabilities, scan_file_operations
from frob.vet._capability_registry import (
    CAPABILITY_KINDS,
    CAPABILITY_MATRIX_EXCUSES,
    DANGEROUS_OPERATIONS,
    LANGUAGES,
    DangerousOperation,
    capability_matrix,
    unexcused_empty_cells,
    validate_registry_kinds,
)


class TestMatrixExhaustiveness:
    # frob:tests src/frob/vet/_capability_registry.py::unexcused_empty_cells kind="unit"
    def test_no_unexcused_empty_cells(self) -> None:
        """T-0158's core exhaustiveness claim: every (kind, language) cell is
        either patterned or excused. Any unexcused empty cell fails loudly
        here -- the blanket C/C++ exemption is retired."""
        assert unexcused_empty_cells() == ()

    # frob:tests src/frob/vet/_capability_registry.py::capability_matrix kind="unit"
    def test_matrix_covers_every_kind_and_language(self) -> None:
        cells = capability_matrix()
        assert len(cells) == len(CAPABILITY_KINDS) * len(LANGUAGES)
        seen = {(c.capability_kind, c.language) for c in cells}
        # frob:waive PERF003 reason="13x4 fixed small cross product asserting matrix completeness, not a data-scale join"
        for kind in CAPABILITY_KINDS:
            for language in LANGUAGES:
                assert (kind, language) in seen

    # frob:tests src/frob/vet/_capability_registry.py::DANGEROUS_OPERATIONS kind="unit"
    def test_every_operation_kind_and_language_registered(self) -> None:
        """Every `DangerousOperation` names a registered kind/language --
        the T-0158 drift-lock: the registry cannot silently grow a kind or
        language its own vocabulary tuples do not know about."""
        for entry in DANGEROUS_OPERATIONS:
            assert entry.capability_kind in CAPABILITY_KINDS
            assert entry.language in LANGUAGES

    # frob:tests src/frob/vet/_capability_registry.py::CAPABILITY_MATRIX_EXCUSES kind="unit"
    def test_every_excuse_kind_and_language_registered(self) -> None:
        for excuse in CAPABILITY_MATRIX_EXCUSES:
            assert excuse.capability_kind in CAPABILITY_KINDS
            assert excuse.language in LANGUAGES

    # frob:tests src/frob/vet/_capability_registry.py::capability_matrix kind="unit"
    def test_no_cell_is_both_patterned_and_excused(self) -> None:
        """An excused cell exists BECAUSE it has no pattern -- a cell that
        is both patterned and carries a stale excuse entry is a drift bug
        (the excuse should have been removed when the pattern landed)."""
        for cell in capability_matrix():
            assert not (cell.patterned and cell.excused)


class TestValidateRegistryKinds:
    # frob:tests src/frob/vet/_capability_registry.py::validate_registry_kinds kind="unit"
    def test_known_kinds_pass(self) -> None:
        assert validate_registry_kinds(frozenset({"exec", "eval"})) == ()

    # frob:tests src/frob/vet/_capability_registry.py::validate_registry_kinds kind="unit"
    def test_unknown_kind_reported(self) -> None:
        offenders = validate_registry_kinds(frozenset({"exec", "bogus-kind"}))
        assert offenders == ("bogus-kind",)

    # frob:tests src/frob/vet/_capability_registry.py::validate_registry_kinds kind="unit"
    def test_every_threat_catalog_kind_is_registered(self) -> None:
        """Cross-check (T-0158 deliverable 4): every `capability_kind`
        `CWE_CATALOG`/`CWE_TOP_25_CATALOG`/`DEFAULT_BENIGN_CAPABILITIES`
        names must be a registry kind."""
        from frob.strata._threat import (
            CWE_CATALOG,
            CWE_TOP_25_CATALOG,
            DEFAULT_BENIGN_CAPABILITIES,
        )

        used = {e.capability_kind for e in CWE_CATALOG if e.capability_kind}
        used |= {e.capability_kind for e in CWE_TOP_25_CATALOG if e.capability_kind}
        used |= {b.kind for b in DEFAULT_BENIGN_CAPABILITIES}
        assert validate_registry_kinds(frozenset(used)) == ()


# ---------------------------------------------------------------------------
# per-cell fire fixtures (T-0145 drift-lock style): a representative,
# minimal snippet per patterned language that MUST be flagged. Not every
# single one of the ~70 DANGEROUS_OPERATIONS entries gets its own fixture
# here (see T-0158 Done report for the follow-up ticket covering full
# per-operation fixture parametrization); these cover at least one entry
# per (kind, language) cell that IS patterned, proving the compiled
# `_PATTERNS` table (T-0158: derived from this registry) actually fires.
# ---------------------------------------------------------------------------


_FIRE_FIXTURES: tuple[tuple[str, str, str, str], ...] = (
    # (language, capability_kind, filename, source snippet)
    ("python", "exec", "m.py", "import subprocess\nsubprocess.run(['ls'])\n"),
    ("python", "eval", "m.py", "eval(user_input)\n"),
    ("python", "net", "m.py", "import socket\nsocket.socket()\n"),
    ("python", "fs-write", "m.py", "open('x', 'w').write('y')\n"),
    ("python", "env", "m.py", "import os\nos.environ.get('X')\n"),
    ("python", "ffi", "m.py", "import ctypes\nctypes.CDLL('x')\n"),
    ("python", "install-hook", "m.py", "setup(cmdclass={'build': X})\n"),
    ("python", "sql", "m.py", 'cur.execute(f"SELECT {x}")\n'),
    (
        "python",
        "fetch_url",
        "m.py",
        "import urllib.request\nurllib.request.urlopen(u)\n",
    ),
    ("python", "deserialize", "m.py", "import pickle\npickle.loads(b)\n"),
    ("typescript", "exec", "m.ts", "child_process.execSync('ls')\n"),
    ("typescript", "eval", "m.ts", "eval(userInput)\n"),
    ("typescript", "html_render", "m.ts", "el.innerHTML = raw\n"),
    ("typescript", "client_storage", "m.ts", "localStorage.setItem('k', v)\n"),
    ("typescript", "fetch_url", "m.ts", "fetch(url)\n"),
    ("typescript", "net", "m.ts", "const ws = new WebSocket(url)\n"),
    ("typescript", "env", "m.ts", "process.env.SECRET\n"),
    ("typescript", "fs-write", "m.ts", "fs.writeFile(p, d)\n"),
    ("typescript", "ffi", "m.ts", "require('ffi-napi')\n"),
    ("rust", "exec", "m.rs", 'fn f() { std::process::Command::new("sh"); }\n'),
    ("rust", "ffi", "m.rs", 'extern "C" { fn f(); }\n'),
    ("rust", "eval", "m.rs", "unsafe { mem::transmute(x) }\n"),
    ("rust", "net", "m.rs", "TcpStream::connect(addr)\n"),
    ("rust", "fs-write", "m.rs", "File::create(p)\n"),
    ("rust", "env", "m.rs", 'std::env::var("X")\n'),
    ("c-cpp", "exec", "m.c", 'int f() { system("ls"); }\n'),
    ("c-cpp", "ffi", "m.c", 'void *h = dlopen("lib.so", 0);\n'),
    ("c-cpp", "fs-write", "m.c", "strcpy(buf, src);\n"),
    ("c-cpp", "net", "m.c", "socket(AF_INET, SOCK_STREAM, 0);\n"),
)


@pytest.mark.parametrize("language,kind,filename,source", _FIRE_FIXTURES)
# frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
def test_fire_fixture_flags_capability(
    tmp_path: Path, language: str, kind: str, filename: str, source: str
) -> None:
    """Every fixture here MUST cause `scan_file_capabilities` to observe
    `kind` for `language` -- a pattern without a firing fixture is as good
    as absent (T-0145 precedent)."""
    path = tmp_path / filename
    path.write_text(source)
    observed = scan_file_capabilities(path)
    assert kind in observed, f"{language}/{kind} fixture did not fire: {source!r}"


@pytest.mark.parametrize("language,kind,filename,source", _FIRE_FIXTURES)
# frob:tests src/frob/vet/_capability.py::scan_file_operations kind="unit"
def test_fire_fixture_names_a_registry_entry(
    tmp_path: Path, language: str, kind: str, filename: str, source: str
) -> None:
    """T-0158 addendum 1: the richer `scan_file_operations` must name at
    least one matching `DangerousOperation` for the same fixture, so an
    audit finding can cite library/function/rationale/safer_alternative."""
    path = tmp_path / filename
    path.write_text(source)
    ops = scan_file_operations(path)
    assert any(op.capability_kind == kind for op in ops), (
        f"{language}/{kind} fixture matched no registry entry: {source!r}"
    )
    matching = next(op for op in ops if op.capability_kind == kind)
    assert isinstance(matching, DangerousOperation)
    assert matching.rationale
    assert matching.safer_alternative


#: Snapshot of `_capability.py::_PATTERNS` as it existed IMMEDIATELY before
#: T-0158 replaced hand-written needle tuples with the compiled registry
#: (merge-base 734355174018f73d0aee1e4e1d16b6df963048df, `git show
#: <sha>:src/frob/vet/_capability.py`). A reviewer caught a real silent
#: regression during T-0158 review: the pre-change table's bare `"Popen("`
#: needle (catching `from subprocess import Popen; Popen(cmd)` with no
#: `subprocess.` prefix at the call site) was absent from the registry-
#: compiled table entirely -- no needle, no excuse, no written reason. This
#: snapshot plus `_RECLASSIFIED_NEEDLES` below is the drift-lock that
#: catches the NEXT silent drop as a test failure instead of a manual
#: reviewer catch.
_PRE_REGISTRY_PATTERNS_SNAPSHOT: dict[str, dict[str, tuple[str, ...]]] = {
    "python": {
        "exec": ("subprocess.", "os.system(", "os.popen(", "os.exec", "Popen("),
        "eval": ("eval(", "exec(", "__import__(", "importlib.import_module("),
        "net": ("socket.", "urllib.", "http.client", "requests.", "aiohttp.", "httpx."),
        "fs-write": ("os.remove(", "shutil.rmtree(", "os.rename(", "open(", ".write("),
        "env": ("os.environ", "os.getenv("),
        "ffi": ("ctypes.", "import ctypes", "cffi"),
        "install-hook": ("cmdclass",),
    },
    "typescript": {
        "exec": ("child_process", "execSync(", "spawn(", "execFile("),
        "eval": ("eval(", "new Function(", "vm.runInContext(", "vm.runInNewContext("),
        "net": (
            'require("http")',
            "require('http')",
            "fetch(",
            "axios.",
            "net.connect(",
            "http.request(",
            "https.request(",
        ),
        "fs-write": ("fs.writeFile", "fs.appendFile", "fs.unlink", "fs.rm("),
        "env": ("process.env",),
        "ffi": ("ffi-napi", "node-gyp", "napi"),
        "install-hook": ("cmdclass",),
    },
    "rust": {
        "exec": ("Command::new(",),
        "eval": (),
        "net": ("TcpStream", "reqwest::", "hyper::", "std::net::"),
        "fs-write": ("File::create(", "fs::write(", "fs::remove_file("),
        "env": ("std::env::var(", "std::env::vars("),
        "ffi": ('extern "C"', "libc::"),
        "install-hook": (),
    },
}

#: Every pre-registry needle that no longer appears under the SAME
#: (language, kind) cell in the compiled table, with the written reason it
#: moved or was dropped (T-0158 Done report has the full reasoning; this is
#: the machine-checked summary). Reclassifying a needle to a MORE PRECISE
#: kind is not a regression -- `frob.vet._capability_registry`'s
#: `urllib.request.urlopen`/`fetch()` entries carry the same needles under
#: `fetch_url` instead of the old generic `net` bucket. `cmdclass` under
#: typescript/install-hook is a genuine drop: no JS/TS packaging-hook
#: idiom exists (see `CAPABILITY_MATRIX_EXCUSES`'s
#: `install-hook`/`typescript` entry).
_RECLASSIFIED_NEEDLES: tuple[tuple[str, str, str, str], ...] = (
    # (language, old_kind, needle, reason)
    (
        "python",
        "net",
        "urllib.",
        "moved to fetch_url -- urlopen's actual danger is SSRF (CWE-918), "
        "a more precise kind than generic net",
    ),
    (
        "typescript",
        "net",
        "fetch(",
        "moved to fetch_url -- fetch()'s actual danger is SSRF (CWE-918), "
        "a more precise kind than generic net",
    ),
    (
        "typescript",
        "install-hook",
        "cmdclass",
        "genuinely dropped -- no JS/TS packaging-install-hook idiom exists "
        "analogous to setuptools cmdclass (npm lifecycle scripts are "
        "package.json DATA, not source text this scanner reads); see "
        "CAPABILITY_MATRIX_EXCUSES install-hook/typescript",
    ),
)


class TestNoSilentNeedleRegression:
    """T-0158 regression-lock (reviewer-mandated): every needle the pre-
    registry hand-written `_PATTERNS` table matched must still fire
    SOMEWHERE in the registry-compiled table, unless explicitly
    reclassified/excused in `_RECLASSIFIED_NEEDLES` with a written reason.
    Catches the next silent detection drop as a test failure, not a
    reviewer catch."""

    # frob:tests src/frob/vet/_capability_registry.py::DANGEROUS_OPERATIONS kind="unit"
    def test_every_pre_registry_needle_still_fires_somewhere(self) -> None:
        from frob.vet._capability import _PATTERNS

        reclassified = {
            (lang, kind, needle) for lang, kind, needle, _ in _RECLASSIFIED_NEEDLES
        }
        new_needles_flat: set[str] = set()
        for by_kind in _PATTERNS.values():
            for needles in by_kind.values():
                new_needles_flat.update(needles)

        missing: list[tuple[str, str, str]] = []
        for lang, by_kind in _PRE_REGISTRY_PATTERNS_SNAPSHOT.items():
            for kind, needles in by_kind.items():
                for needle in needles:
                    if needle in new_needles_flat:
                        continue
                    if (lang, kind, needle) in reclassified:
                        continue
                    missing.append((lang, kind, needle))
        assert missing == [], (
            f"needle(s) silently dropped from the registry with no "
            f"replacement and no _RECLASSIFIED_NEEDLES entry: {missing}"
        )

    # frob:tests src/frob/vet/_capability_registry.py::DANGEROUS_OPERATIONS kind="unit"
    def test_every_reclassified_needle_actually_still_fires_under_its_new_kind(
        self,
    ) -> None:
        """A `_RECLASSIFIED_NEEDLES` entry must be TRUE, not just claimed --
        the needle really does still appear in the compiled table
        (just not necessarily under its old kind)."""
        from frob.vet._capability import _PATTERNS

        new_needles_flat: set[str] = set()
        for by_kind in _PATTERNS.values():
            for needles in by_kind.values():
                new_needles_flat.update(needles)
        for lang, _old_kind, needle, reason in _RECLASSIFIED_NEEDLES:
            if needle == "cmdclass" and lang == "typescript":
                # the one genuine drop -- no replacement needle to check.
                continue
            assert needle in new_needles_flat, (
                f"{lang}/{needle} claimed reclassified ({reason}) but is "
                f"absent from the compiled table entirely"
            )

    # frob:tests src/frob/vet/_capability_registry.py::DANGEROUS_OPERATIONS kind="unit"
    def test_popen_bare_call_still_flags_exec(self, tmp_path: Path) -> None:
        """The specific reviewer-caught regression: `from subprocess import
        Popen; Popen(cmd)` with no `subprocess.` prefix at the call site
        must still flag as `exec`."""
        path = tmp_path / "m.py"
        path.write_text("from subprocess import Popen\nPopen(['ls'], shell=True)\n")
        assert "exec" in scan_file_capabilities(path)


class TestNegativeFixtures:
    """T-0151 lessons: dotted-call exclusions and self-match boundaries
    must stay locked, not just the positive fire side."""

    # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
    def test_re_compile_is_not_eval(self, tmp_path: Path) -> None:
        path = tmp_path / "m.py"
        path.write_text("import re\n_RE = re.compile(r'^x$')\n")
        assert "eval" not in scan_file_capabilities(path)

    # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
    def test_c_socket_header_alone_is_not_net(self, tmp_path: Path) -> None:
        path = tmp_path / "m.c"
        path.write_text("#include <sys/socket.h>\n")
        assert "net" not in scan_file_capabilities(path)

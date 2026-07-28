"""Tests for `frob.vet._capability_registry` (T-0158): the single-source
capability-kind enumeration, the structured `_DangerousOperation` registry,
and the (kind x language) coverage matrix -- plus per-cell fire fixtures
proving representative patterned entries actually fire through
`frob.vet._capability.scan_file_capabilities`/`_scan_file_operations`
(T-0145 drift-lock style: a pattern with zero firing evidence is as good
as absent)."""

from __future__ import annotations

from pathlib import Path

import pytest

from frob.vet._capability import (
    _scan_file_operations,
    is_self_pattern_path,
    scan_file_capabilities,
)
from frob.vet._capability_registry import (
    CAPABILITY_KINDS,
    CAPABILITY_MATRIX_EXCUSES,
    DANGEROUS_OPERATIONS,
    LANGUAGES,
    _DangerousOperation,
    _unexcused_empty_cells,
    _validate_registry_kinds,
    capability_matrix,
)


class TestMatrixExhaustiveness:
    # frob:tests src/frob/vet/_capability_registry.py::_unexcused_empty_cells \
    # kind="unit"
    def test_no_unexcused_empty_cells(self) -> None:
        """T-0158's core exhaustiveness claim: every (kind, language) cell is
        either patterned or excused. Any unexcused empty cell fails loudly
        here -- the blanket C/C++ exemption is retired."""
        assert _unexcused_empty_cells() == ()

    # frob:tests src/frob/vet/_capability_registry.py::capability_matrix kind="unit"
    def test_matrix_covers_every_kind_and_language(self) -> None:
        cells = capability_matrix()
        assert len(cells) == len(CAPABILITY_KINDS) * len(LANGUAGES)
        seen = {(c.capability_kind, c.language) for c in cells}
        for kind in CAPABILITY_KINDS:
            for language in LANGUAGES:
                assert (kind, language) in seen

    # frob:tests src/frob/vet/_capability_registry.py::DANGEROUS_OPERATIONS kind="unit"
    def test_every_operation_kind_and_language_registered(self) -> None:
        """Every `_DangerousOperation` names a registered kind/language --
        the T-0158 drift-lock: the registry cannot silently grow a kind or
        language its own vocabulary tuples do not know about."""
        for entry in DANGEROUS_OPERATIONS:
            assert entry.capability_kind in CAPABILITY_KINDS
            assert entry.language in LANGUAGES

    # frob:tests src/frob/vet/_capability_registry.py::CAPABILITY_MATRIX_EXCUSES \
    # kind="unit"
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
    # frob:tests src/frob/vet/_capability_registry.py::_validate_registry_kinds \
    # kind="unit"
    def test_known_kinds_pass(self) -> None:
        assert _validate_registry_kinds(frozenset({"exec", "eval"})) == ()

    # frob:tests src/frob/vet/_capability_registry.py::_validate_registry_kinds \
    # kind="unit"
    def test_unknown_kind_reported(self) -> None:
        offenders = _validate_registry_kinds(frozenset({"exec", "bogus-kind"}))
        assert offenders == ("bogus-kind",)

    # frob:tests src/frob/vet/_capability_registry.py::_validate_registry_kinds \
    # kind="unit"
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
        assert _validate_registry_kinds(frozenset(used)) == ()


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
# frob:tests src/frob/vet/_capability.py::_scan_file_operations kind="unit"
def test_fire_fixture_names_a_registry_entry(
    tmp_path: Path, language: str, kind: str, filename: str, source: str
) -> None:
    """T-0158 addendum 1: the richer `_scan_file_operations` must name at
    least one matching `_DangerousOperation` for the same fixture, so an
    audit finding can cite library/function/rationale/safer_alternative."""
    path = tmp_path / filename
    path.write_text(source)
    ops = _scan_file_operations(path)
    assert any(op.capability_kind == kind for op in ops), (
        f"{language}/{kind} fixture matched no registry entry: {source!r}"
    )
    matching = next(op for op in ops if op.capability_kind == kind)
    assert isinstance(matching, _DangerousOperation)
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
    (
        "typescript",
        "ffi",
        "napi",
        "T-0019 (graphite adoption): not dropped, moved to a special check -- "
        "bare 'napi' is a substring of the ordinary word 'openapi' "
        "(openapi-typescript codegen false-positived on it); still detected, "
        "but only via frob.vet._capability._has_word_boundary_napi's "
        "identifier-boundary match, registered in _SPECIAL_CHECKS rather "
        "than the plain-needle table this snapshot compares against",
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
        from frob.vet._capability import _PATTERNS, _SPECIAL_CHECKS

        new_needles_flat: set[str] = set()
        for by_kind in _PATTERNS.values():
            for needles in by_kind.values():
                new_needles_flat.update(needles)
        for lang, _old_kind, needle, reason in _RECLASSIFIED_NEEDLES:
            if needle == "cmdclass" and lang == "typescript":
                # the one genuine drop -- no replacement needle to check.
                continue
            if needle == "napi" and lang == "typescript":
                # T-0019: not a plain needle any more -- moved to the
                # identifier-boundary special check instead (still
                # detected, just not via the substring table this loop
                # inspects).
                assert "ffi" in _SPECIAL_CHECKS.get("typescript", {}), (
                    f"{lang}/{needle} claimed reclassified to a special "
                    f"check ({reason}) but no typescript/ffi special check "
                    f"is registered"
                )
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


# ---------------------------------------------------------------------------
# per-operation fire+negative parametrization (T-0182, T-0158 deliverable 3
# remainder): the `_FIRE_FIXTURES` tuple above is one representative
# fixture per patterned (kind, language) cell (29 cells) -- it does NOT
# give each of the ~70 individual `DANGEROUS_OPERATIONS` entries its own
# dedicated proof. The tests below parametrize DIRECTLY over
# `DANGEROUS_OPERATIONS` itself (not a hand-maintained fixture tuple), so a
# new entry appended to the registry automatically gets its own fire
# fixture generated from its own needle -- no fixture written means no
# proof, and `frob check`'s coverage gate has nothing to bind, but the test
# itself cannot silently "ride" on a sibling entry's cell-level fixture the
# way `_FIRE_FIXTURES` can (T-0145 drift-lock style: a pattern with zero
# entry-level firing evidence is as good as absent).
# ---------------------------------------------------------------------------

#: registry language -> the file extension `frob.vet._capability.language_for`
#: buckets it under, so each generated fixture lands in the right pattern
#: table.
_LANG_EXT: dict[str, str] = {
    "python": ".py",
    "typescript": ".ts",
    "rust": ".rs",
    "c-cpp": ".c",
    "kotlin": ".kt",
}

#: benign source per language guaranteed to contain none of this registry's
#: needles -- the negative-fixture baseline every entry is checked against.
_BENIGN_SOURCE: dict[str, str] = {
    "python": "x = 1\n",
    "typescript": "const x = 1;\n",
    "rust": "let x: i32 = 1;\n",
    "c-cpp": "int x = 1;\n",
    "kotlin": "val x: Int = 1\n",
}


def _fire_snippet(entry: _DangerousOperation) -> str:
    """Minimal source text that must fire `entry`: its own first needle
    verbatim, or -- for the one no-needle registry entry (python bare
    `compile()`, matched only via `_has_bare_compile_call`) -- a literal
    bare builtin call. Raises if a future no-needle entry has no known
    generation strategy, so a silently un-provable entry fails loudly
    instead of being skipped."""
    if entry.needles:
        return entry.needles[0] + "\n"
    if entry.language == "python" and entry.function_or_pattern.startswith("compile("):
        return "compile(src, '<string>', 'eval')\n"
    raise AssertionError(
        f"no fire-snippet generation strategy for no-needle entry "
        f"{entry.language}/{entry.library}/{entry.function_or_pattern!r} "
        f"-- T-0182 fixture generator needs a case for it"
    )


_PER_OPERATION_IDS = tuple(
    f"{i:03d}-{entry.language}-{entry.library}-{entry.function_or_pattern}"
    for i, entry in enumerate(DANGEROUS_OPERATIONS)
)


class TestPerOperationFireFixtures:
    """One needle-based fire fixture per `DANGEROUS_OPERATIONS` entry
    (T-0182), generated from the entry itself rather than hand-maintained,
    so an entry added to the registry without review gets proof for free
    and a broken needle fails loudly instead of riding on a sibling
    entry's cell-level fixture."""

    @pytest.mark.parametrize("entry", DANGEROUS_OPERATIONS, ids=_PER_OPERATION_IDS)
    # frob:tests src/frob/vet/_capability.py::_scan_file_operations kind="unit"
    def test_entry_fires_scan_file_operations(
        self, tmp_path: Path, entry: _DangerousOperation
    ) -> None:
        """`_scan_file_operations` must name THIS exact registry entry (not
        merely some entry sharing its kind) for a minimal snippet built
        from the entry's own needle."""
        path = tmp_path / ("m" + _LANG_EXT[entry.language])
        path.write_text(_fire_snippet(entry))
        ops = _scan_file_operations(path)
        assert entry in ops, (
            f"{entry.language}/{entry.library}/{entry.function_or_pattern} "
            f"did not fire via its own needle(s) {entry.needles!r}"
        )

    @pytest.mark.parametrize("entry", DANGEROUS_OPERATIONS, ids=_PER_OPERATION_IDS)
    # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
    def test_entry_fires_scan_file_capabilities(
        self, tmp_path: Path, entry: _DangerousOperation
    ) -> None:
        """The bare-kind sibling entry point must also observe `entry`'s
        `capability_kind` for the same minimal snippet."""
        path = tmp_path / ("m" + _LANG_EXT[entry.language])
        path.write_text(_fire_snippet(entry))
        observed = scan_file_capabilities(path)
        assert entry.capability_kind in observed, (
            f"{entry.language}/{entry.library}/{entry.function_or_pattern} "
            f"fired no capability via its own needle(s) {entry.needles!r}"
        )

    @pytest.mark.parametrize("entry", DANGEROUS_OPERATIONS, ids=_PER_OPERATION_IDS)
    # frob:tests src/frob/vet/_capability.py::_scan_file_operations kind="unit"
    def test_entry_absent_from_benign_source(
        self, tmp_path: Path, entry: _DangerousOperation
    ) -> None:
        """Negative fixture: this entry must NOT fire against benign source
        containing none of its needles -- proves the needle match is
        discriminating, not vacuously true (T-0145 lesson applied per
        entry, not just per cell)."""
        path = tmp_path / ("m" + _LANG_EXT[entry.language])
        path.write_text(_BENIGN_SOURCE[entry.language])
        ops = _scan_file_operations(path)
        assert entry not in ops, (
            f"{entry.language}/{entry.library}/{entry.function_or_pattern} "
            f"fired against benign source with none of its needles present"
        )


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

    # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
    def test_openapi_generated_ts_is_not_ffi(self, tmp_path: Path) -> None:
        """T-0019 (graphite adoption): SYS100 fired for graphite's `node
        browser` on capability `ffi`, sourced from `frontend/src/api/
        api.generated.ts`/`client.ts` -- both openapi-typescript codegen/
        consumers with zero real node-ffi/ffi-napi usage. The needle
        `"napi"` is a substring of `"openapi"`/`"OpenAPI"`
        (`o-p-e-n-[napi]`); this fixture reproduces the shape of that
        false positive verbatim (an OpenAPI-generated client, no FFI
        anywhere) and locks it fixed."""
        path = tmp_path / "api.generated.ts"
        path.write_text(
            "/* eslint-disable */\n"
            "/* tslint:disable */\n"
            "/*\n"
            " * ---------------------------------------------------------------\n"
            " * ## THIS FILE WAS GENERATED BY openapi-typescript-codegen ##\n"
            " * ## ##\n"
            " * ## AUTHOR: OpenAPI Generator ##\n"
            " * ---------------------------------------------------------------\n"
            " */\n"
            "export type OpenAPI = {\n"
            "  BASE: string;\n"
            "  TOKEN?: string;\n"
            "};\n"
            "export class ApiClient {\n"
            "  constructor(public readonly openapi: OpenAPI) {}\n"
            "}\n"
        )
        observed = scan_file_capabilities(path)
        assert "ffi" not in observed

    # frob:tests src/frob/vet/_capability.py::scan_file_capabilities kind="unit"
    def test_real_napi_import_still_fires_ffi(self, tmp_path: Path) -> None:
        """The positive counterpart to the openapi fixture above: a real
        `napi`-based native addon import must still be caught (T-0019 is a
        precision fix, not a recall regression)."""
        path = tmp_path / "native.ts"
        path.write_text("import napi from 'napi';\nconst addon = napi.load('x');\n")
        observed = scan_file_capabilities(path)
        assert "ffi" in observed


def _make_frob_repo_root(root: Path) -> None:
    """Build a directory tree that `_is_frob_repo_root` accepts: a
    `pyproject.toml` declaring `name = "frob"` plus the `frob-core`/
    `strata-core` crate directories the real monorepo ships alongside it."""
    (root / "pyproject.toml").write_text('[project]\nname = "frob"\n')
    (root / "frob-core").mkdir()
    (root / "strata-core").mkdir()


class TestIsSelfPatternPath:
    """T-0253: `is_self_pattern_path`'s foreign-vs-self discriminator --
    the suffix match only fires when `root` is frob's OWN repo checkout,
    never based on `path` alone."""

    # frob:tests src/frob/vet/_capability.py::is_self_pattern_path kind="unit"
    def test_root_none_always_returns_false(self, tmp_path: Path) -> None:
        # Fail-closed default: omitting `root` means "never exclude,
        # always scan", even for a path that would otherwise match a
        # self-pattern suffix.
        _make_frob_repo_root(tmp_path)
        path = tmp_path / "frob" / "vet" / "_capability.py"
        path.parent.mkdir(parents=True)
        path.write_text("")
        assert is_self_pattern_path(path) is False

    # frob:tests src/frob/vet/_capability.py::is_self_pattern_path kind="unit"
    def test_root_not_frob_repo_returns_false(self, tmp_path: Path) -> None:
        # `root` lacks pyproject.toml / crate dirs -- a foreign dependency
        # root that happens to mimic frob's package layout must still be
        # scanned, not silently excluded (the T-0253 round-1 evasion hole).
        foreign_root = tmp_path / "foreign"
        path = foreign_root / "frob" / "vet" / "_capability.py"
        path.parent.mkdir(parents=True)
        path.write_text("")
        assert is_self_pattern_path(path, foreign_root) is False

    # frob:tests src/frob/vet/_capability.py::is_self_pattern_path kind="unit"
    def test_frob_repo_root_with_matching_suffix_returns_true(
        self, tmp_path: Path
    ) -> None:
        _make_frob_repo_root(tmp_path)
        path = tmp_path / "frob" / "vet" / "_capability.py"
        path.parent.mkdir(parents=True)
        path.write_text("")
        assert is_self_pattern_path(path, tmp_path) is True

    # frob:tests src/frob/vet/_capability.py::is_self_pattern_path kind="unit"
    def test_frob_repo_root_with_non_matching_path_returns_false(
        self, tmp_path: Path
    ) -> None:
        # Same (valid) root, but a path that isn't one of the three
        # self-pattern-catalog files -- must not be excluded.
        _make_frob_repo_root(tmp_path)
        path = tmp_path / "frob" / "vet" / "_source.py"
        path.parent.mkdir(parents=True)
        path.write_text("")
        assert is_self_pattern_path(path, tmp_path) is False

    # frob:tests src/frob/vet/_capability.py::is_self_pattern_path kind="unit"
    def test_short_path_shorter_than_suffix_returns_false(self, tmp_path: Path) -> None:
        # `len(parts) >= len(suffix)` guard: a resolved path with fewer
        # path components than the longest self-pattern suffix must not
        # raise or false-positive via a negative slice.
        _make_frob_repo_root(tmp_path)
        path = tmp_path / "_capability.py"
        path.write_text("")
        assert is_self_pattern_path(path, tmp_path) is False

    # frob:tests src/frob/vet/_capability.py::is_self_pattern_path kind="unit"
    def test_path_resolve_oserror_returns_false(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # `path.resolve()` failing (e.g. a filesystem-level error walking
        # a broken symlink) must fail closed rather than propagate.
        _make_frob_repo_root(tmp_path)
        path = tmp_path / "frob" / "vet" / "_capability.py"
        real_resolve = Path.resolve

        # Only the scanned FILE's resolve() should fail here -- `root`'s
        # own resolve() (inside `_is_frob_repo_root`) must still succeed
        # so this exercises `is_self_pattern_path`'s own try/except rather
        # than an unrelated failure in the discriminator it calls first.
        def _selective_oserror(self: Path, strict: bool = False) -> Path:
            if self == path:
                raise OSError("simulated resolve failure")
            return real_resolve(self, strict)

        monkeypatch.setattr(Path, "resolve", _selective_oserror)
        assert is_self_pattern_path(path, tmp_path) is False

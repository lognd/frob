"""T-3247: enforcement for the "whole-repo-scan test needs its own
`@pytest.mark.timeout(N)` override" rule.

BACKGROUND: `pyproject.toml`'s `addopts` sets a global `--timeout=120
--timeout-method=thread`. A test that legitimately scans this repo's whole
real tree (a `build_graph`/`check_self_conformance`/`scan_file_
capabilities` call, or a real `frob check` subprocess spawn) can exceed
that on a slow CI runner; `--timeout-method=thread` then kills the xdist
WORKER (not just the test), and xdist's `loadscope` scheduler crashes on
the dead worker (`KeyError: <WorkerController gwN>`), aborting the WHOLE
suite -- this is what happened in the 2026-08-28 CI run this ticket traces.

The fix for an individual test is `@pytest.mark.timeout(N)` with a
measured N (docs/guides/testing.md#per-test-timeout-ci-hardening,
precedent: T-0742). That mechanism already existed and was applied to only
4 files before this ticket. THE POINT OF THIS TICKET IS THE GATE, NOT THE
3 FIXES: this file enumerates every test that performs a whole-repo scan,
by parsing (never by substring/regex, per this repo's standing directive)
each test file's AST and resolving each call's target through that file's
own `import`/`from ... import` statements, and asserts every one of them
carries an explicit timeout override -- so the NEXT such test cannot be
added silently.

`tests/conftest.py::_SELF_SCAN_HEAVY_NAME_SUBSTRINGS` is a DIFFERENT,
pre-existing, deliberately-hardcoded-name mechanism (T-1433) for xdist
GROUPING (keeping heavy scans off concurrent workers, not bounding their
wall-clock). It is not reused here: T-3247 explicitly asks for an
enumeration method that "will not rot", and a hand-maintained name list is
the thing that rots."""

from __future__ import annotations

import ast
import textwrap
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_TESTS_ROOT = _REPO_ROOT / "tests"

#: (module, original-name) pairs for the entry points a call resolving to
#: any of them (via the calling file's own imports, not a source-text
#: guess) marks a test as a whole-repo scan. Each is a REAL, unbounded,
#: whole-repo-tree traversal in this codebase today -- not a heuristic
#: name pattern:
#:   - `frob.graph.build_graph`: parses every language-supported file
#:     under its `root` argument (T-3247's `test_sys_gate_zero_violations`
#:     case).
#:   - `frob.strata._selfconform.check_self_conformance`: walks
#:     `scan_file_capabilities` over the whole tree (T-3247's
#:     `test_repo_design_and_declarations_are_self_conformant` case).
#:   - `frob.vet._capability_core.scan_file_capabilities`: the capability
#:     sweep itself, in case a future test calls it directly rather than
#:     through `check_self_conformance`.
#:   - `tests.system.conftest.run`: spawns a real `frob check`/`frob`
#:     subprocess against this repo's live tree (T-3247's
#:     `test_ticket_readiness_is_not_an_arch001_finding` case) -- this
#:     repo's own canonical "full frob check spawn" helper.
_WHOLE_REPO_SCAN_ENTRYPOINTS: frozenset[tuple[str, str]] = frozenset(
    {
        ("frob.graph", "build_graph"),
        ("frob.strata._selfconform", "check_self_conformance"),
        ("frob.vet._capability_core", "scan_file_capabilities"),
        ("tests.system.conftest", "run"),
    }
)

#: Files that are themselves entry-point definitions/synthetic-repo
#: fixtures, exempted so the detector never flags an entry point's OWN
#: unit tests (which legitimately call it against a `tmp_path` synthetic
#: tree, not the real repo, and are fast by construction) -- the
#: entrypoint set above only exists to be resolved through THESE files'
#: exports, not to blanket-flag every caller of a same-named local helper.
#: Kept narrow and explicit rather than inferred, since an inferred
#: exemption is exactly the kind of silent escape hatch this ticket's
#: sibling findings (WAIVE004) warn against.
_ENTRYPOINT_DEFINITION_FILES: frozenset[str] = frozenset(
    {
        "src/frob/graph/_core.py",
        "src/frob/strata/_selfconform.py",
        "src/frob/vet/_capability_core.py",
        "tests/system/conftest.py",
    }
)


# frob:waive WIRE001 follow_up="T-3267" reason="lives entirely within its own test \
# module by design -- src/frob/gates/__init__.py was under a live T-3196 scope lease \
# at land time, so this detector is a self-verifying pytest test \
# (TestRepoIsScanTimeoutClean) rather than a wired gate rule; \
# find_scan_timeout_violations IS its real caller, just from within this same file. \
# Migrate into a proper gate module once T-3196 releases the lease."
def _imported_origins(tree: ast.Module) -> dict[str, tuple[str, str]]:
    """Map each locally-bound name in `tree` to the `(module, original-
    name)` it was imported from -- `from module import name [as local]`
    only (the shape every entry point in `_WHOLE_REPO_SCAN_ENTRYPOINTS` is
    actually imported by in this repo); a bare `import module` binds
    `module` itself, which a later `module.name(...)` attribute-call
    lookup handles separately in `_scan_function_for_entrypoint_calls`."""
    origins: dict[str, tuple[str, str]] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            for alias in node.names:
                local = alias.asname or alias.name
                origins[local] = (node.module, alias.name)
    return origins


# frob:waive WIRE001 follow_up="T-3267" reason="lives entirely within its own test \
# module by design -- src/frob/gates/__init__.py was under a live T-3196 scope lease \
# at land time, so this detector is a self-verifying pytest test \
# (TestRepoIsScanTimeoutClean) rather than a wired gate rule; \
# find_scan_timeout_violations IS its real caller, just from within this same file. \
# Migrate into a proper gate module once T-3196 releases the lease."
def _has_timeout_override(node: ast.AST) -> bool:
    """Whether `node` (a function/class def) carries a
    `@pytest.mark.timeout(...)` decorator -- parsed structurally (the
    decorator must be a `Call` whose `func` is an `Attribute` named
    `timeout`), never a text search for the substring "timeout"."""
    decorator_list = getattr(node, "decorator_list", [])
    for dec in decorator_list:
        if (
            isinstance(dec, ast.Call)
            and isinstance(dec.func, ast.Attribute)
            and dec.func.attr == "timeout"
        ):
            return True
    return False


# frob:waive WIRE001 follow_up="T-3267" reason="lives entirely within its own test \
# module by design -- src/frob/gates/__init__.py was under a live T-3196 scope lease \
# at land time, so this detector is a self-verifying pytest test \
# (TestRepoIsScanTimeoutClean) rather than a wired gate rule; \
# find_scan_timeout_violations IS its real caller, just from within this same file. \
# Migrate into a proper gate module once T-3196 releases the lease."
def _class_level_timeout_override(class_node: ast.ClassDef) -> bool:
    """Whether `class_node` sets a class-level `pytestmark =
    [pytest.mark.timeout(...)]` (or a bare `pytestmark =
    pytest.mark.timeout(...)`) applying the override to every test method
    in the class -- pytest's own documented class-scoping mechanism, so a
    method-level miss here must still check this before it is a real
    violation."""
    for stmt in class_node.body:
        if not isinstance(stmt, ast.Assign):
            continue
        if not any(
            isinstance(t, ast.Name) and t.id == "pytestmark" for t in stmt.targets
        ):
            continue
        candidates = (
            stmt.value.elts if isinstance(stmt.value, ast.List) else [stmt.value]
        )
        for cand in candidates:
            if (
                isinstance(cand, ast.Call)
                and isinstance(cand.func, ast.Attribute)
                and cand.func.attr == "timeout"
            ):
                return True
    return False


# frob:waive WIRE001 follow_up="T-3267" reason="lives entirely within its own test \
# module by design -- src/frob/gates/__init__.py was under a live T-3196 scope lease \
# at land time, so this detector is a self-verifying pytest test \
# (TestRepoIsScanTimeoutClean) rather than a wired gate rule; \
# find_scan_timeout_violations IS its real caller, just from within this same file. \
# Migrate into a proper gate module once T-3196 releases the lease."
def _module_level_assigns(tree: ast.Module) -> dict[str, ast.expr]:
    """Map each module-level simple-assignment target name to its RHS
    expression (`_REPO_ROOT = Path(__file__).resolve().parent.parent`-
    shaped statements) -- lets `_derives_from_dunder_file` resolve a
    `Name` argument (`build_graph(_REPO_ROOT, ...)`) back to the
    expression that actually defines it, one hop, without a full
    dataflow analysis (every real case in this repo's test suite assigns
    the root constant exactly once at module scope)."""
    assigns: dict[str, ast.expr] = {}
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    assigns[target.id] = node.value
    return assigns


# frob:waive WIRE001 follow_up="T-3267" reason="lives entirely within its own test \
# module by design -- src/frob/gates/__init__.py was under a live T-3196 scope lease \
# at land time, so this detector is a self-verifying pytest test \
# (TestRepoIsScanTimeoutClean) rather than a wired gate rule; \
# find_scan_timeout_violations IS its real caller, just from within this same file. \
# Migrate into a proper gate module once T-3196 releases the lease."
# frob:invariant terminates reason="recurses only through _module_level_assigns, a \
# FINITE dict built once per file from that file's own module-level assignment \
# statements (never mutated during recursion); each recursive step consumes one entry \
# from _seen's complement and _seen is never reset mid-call, so the same name can \
# never be visited twice in one call chain" measure="len(module_assigns) - len(_seen), \
# which strictly decreases (or the call returns) every recursive step since _seen \
# strictly grows by one name it was not already in"
def _derives_from_dunder_file(
    expr: ast.expr,
    module_assigns: dict[str, ast.expr],
    _seen: frozenset[str] = frozenset(),
) -> bool:
    """Whether `expr` is structurally derived from `__file__` -- the
    idiom this repo's own test suite already uses everywhere for "this
    test's own real, checked-out location" (`Path(__file__).resolve()
    .parent...` / `.parents[N]`), as opposed to a `tmp_path`-family
    pytest fixture (a `Name` with no module-level assignment at all, so
    resolution below simply fails to find one and returns `False`).
    Recurses through ONE level of module-level `Name` indirection
    (`_derives_from_dunder_file` on `_module_level_assigns[expr.id]`) to
    cover the `_REPO_ROOT = Path(__file__)...` constant-then-reference
    shape, guarded by `_seen` against a self-referential assignment."""
    for node in ast.walk(expr):
        if isinstance(node, ast.Name) and node.id == "__file__":
            return True
    if isinstance(expr, ast.Name) and expr.id not in _seen:
        target = module_assigns.get(expr.id)
        if target is not None:
            return _derives_from_dunder_file(target, module_assigns, _seen | {expr.id})
    return False


#: `run(subcommand, ...)` subcommands that walk the WHOLE repo tree by
#: default when given no explicit target path -- narrower than "any `run`
#: call with only string-literal args", because most `frob` subcommands
#: (`parse`, `sys-audit`, `ticket ...`) either take no directory concept
#: at all or REQUIRE an explicit positional path (`tests/system/test_cli_
#: arch.py` always passes one), so "no path argument" alone does not mean
#: "scans the real repo" for them the way it does for `check`. Extend this
#: set only when a NEW subcommand is verified (like `check` was for this
#: ticket, via `test_ticket_readiness_is_not_an_arch001_finding`) to
#: default to a real, unbounded repo-tree walk with no path argument.
_RUN_SUBCOMMANDS_DEFAULTING_TO_REPO_SCAN: frozenset[str] = frozenset({"check"})


# frob:waive WIRE001 follow_up="T-3267" reason="lives entirely within its own test \
# module by design -- src/frob/gates/__init__.py was under a live T-3196 scope lease \
# at land time, so this detector is a self-verifying pytest test \
# (TestRepoIsScanTimeoutClean) rather than a wired gate rule; \
# find_scan_timeout_violations IS its real caller, just from within this same file. \
# Migrate into a proper gate module once T-3196 releases the lease."
def _run_call_has_no_path_argument(call: ast.Call) -> bool:
    """Whether `call` is a `tests.system.conftest.run` invocation of one
    of `_RUN_SUBCOMMANDS_DEFAULTING_TO_REPO_SCAN` (its first positional
    argument, a string literal) with every OTHER positional argument also
    a plain string literal (flags, e.g. `run("check", "--only", "arch")`)
    -- `run` has no explicit `root`/target parameter at all, so a
    known-whole-repo-scanning subcommand invoked with no non-literal
    (path-shaped) argument defaults to spawning `frob` against the
    CURRENT process's cwd, the real repo for every system test. A call
    passing any non-literal argument (`str(tmp_path)`,
    `str(ARCH_PYTHON_DIR)`, ...) targets that explicit -- in every real
    case in this suite, synthetic -- directory instead."""
    if not call.args:
        return False
    first = call.args[0]
    if not (isinstance(first, ast.Constant) and isinstance(first.value, str)):
        return False
    if first.value not in _RUN_SUBCOMMANDS_DEFAULTING_TO_REPO_SCAN:
        return False
    return all(
        isinstance(arg, ast.Constant) and isinstance(arg.value, str)
        for arg in call.args
    )


# frob:waive WIRE001 follow_up="T-3267" reason="lives entirely within its own test \
# module by design -- src/frob/gates/__init__.py was under a live T-3196 scope lease \
# at land time, so this detector is a self-verifying pytest test \
# (TestRepoIsScanTimeoutClean) rather than a wired gate rule; \
# find_scan_timeout_violations IS its real caller, just from within this same file. \
# Migrate into a proper gate module once T-3196 releases the lease."
def _calls_whole_repo_scan_entrypoint(
    func_node: ast.AST,
    origins: dict[str, tuple[str, str]],
    module_assigns: dict[str, ast.expr],
) -> bool:
    """Whether any direct `Call` inside `func_node` resolves, through
    `origins` (this file's own `from ... import` statements), to a member
    of `_WHOLE_REPO_SCAN_ENTRYPOINTS`, AND actually targets the real repo
    tree rather than a synthetic `tmp_path` fixture -- `build_graph`/
    `check_self_conformance`/`scan_file_capabilities` are called
    constantly across this suite against `tmp_path`-rooted throwaway
    trees (fast, correctly NOT a whole-repo scan), so matching the call
    target alone would flag most of the test suite; `run` (see
    `_run_call_has_no_path_argument`) is checked by argument shape
    instead, since it has no `root` PARAMETER at all to inspect. A `Name`
    call (`build_graph(...)`) resolves via `origins[name]`; an
    `Attribute` call (`conftest.run(...)`) resolves via the attribute's
    own name against any entrypoint's original-name (module-qualified
    calls are rare in this suite; the fallback still requires the SHORT
    name to match a real entry point, never an arbitrary substring)."""
    for sub in ast.walk(func_node):
        if not isinstance(sub, ast.Call):
            continue
        func = sub.func
        origin: tuple[str, str] | None = None
        if isinstance(func, ast.Name):
            origin = origins.get(func.id)
        elif isinstance(func, ast.Attribute):
            for mod, name in _WHOLE_REPO_SCAN_ENTRYPOINTS:
                if func.attr == name:
                    origin = (mod, name)
                    break
        if origin is None or origin not in _WHOLE_REPO_SCAN_ENTRYPOINTS:
            continue
        if origin == ("tests.system.conftest", "run"):
            if _run_call_has_no_path_argument(sub):
                return True
            continue
        if any(_derives_from_dunder_file(arg, module_assigns) for arg in sub.args):
            return True
    return False


# frob:waive WIRE001 follow_up="T-3267" reason="lives entirely within its own test \
# module by design -- src/frob/gates/__init__.py was under a live T-3196 scope lease \
# at land time, so this detector is a self-verifying pytest test \
# (TestRepoIsScanTimeoutClean) rather than a wired gate rule; \
# find_scan_timeout_violations IS its real caller, just from within this same file. \
# Migrate into a proper gate module once T-3196 releases the lease."
class ScanTimeoutViolation:
    """One test found calling a whole-repo-scan entry point with no
    `@pytest.mark.timeout(...)` override in effect (method-level or
    class-level `pytestmark`)."""

    def __init__(self, path: Path, qualname: str, lineno: int) -> None:
        """Record the violation's file-relative `path`, dotted
        `qualname` (`ClassName.method_name` or bare function name), and
        1-based `lineno` for a readable assertion failure."""
        self.path = path
        self.qualname = qualname
        self.lineno = lineno

    def __repr__(self) -> str:  # pragma: no cover - debug/assertion display only
        """`path:lineno qualname` -- the shape a reader acts on directly."""
        return f"{self.path}:{self.lineno} {self.qualname}"


def find_scan_timeout_violations(tests_root: Path) -> tuple[ScanTimeoutViolation, ...]:
    """Walk every `test_*.py` file under `tests_root`, parse it with
    `ast`, and return one `ScanTimeoutViolation` per test function/method
    that calls a whole-repo-scan entry point (`_calls_whole_repo_scan_
    entrypoint`) without an effective `@pytest.mark.timeout(...)`
    override (method decorator OR class-level `pytestmark`). This is the
    enumeration method T-3247 asks for: no hand-maintained name list --
    a renamed or newly-added whole-repo-scan test is caught automatically
    because the call target, not the test's name, is what is matched."""
    violations: list[ScanTimeoutViolation] = []
    for path in sorted(tests_root.rglob("test_*.py")):
        rel = path.relative_to(tests_root.parent).as_posix()
        if rel in _ENTRYPOINT_DEFINITION_FILES:
            continue
        try:
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(path))
        except (SyntaxError, UnicodeDecodeError):  # pragma: no cover - defensive
            continue
        origins = _imported_origins(tree)
        module_assigns = _module_level_assigns(tree)

        def _walk_classes_and_functions(
            body: list[ast.stmt], class_override: bool, class_prefix: str
        ) -> None:
            for node in body:
                if isinstance(node, ast.ClassDef):
                    override = class_override or _class_level_timeout_override(node)
                    _walk_classes_and_functions(
                        node.body, override, f"{class_prefix}{node.name}."
                    )
                elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if not node.name.startswith("test_"):
                        continue
                    if not _calls_whole_repo_scan_entrypoint(
                        node, origins, module_assigns
                    ):
                        continue
                    if class_override or _has_timeout_override(node):
                        continue
                    violations.append(
                        ScanTimeoutViolation(
                            path=Path(rel),
                            qualname=f"{class_prefix}{node.name}",
                            lineno=node.lineno,
                        )
                    )

        _walk_classes_and_functions(tree.body, class_override=False, class_prefix="")
    return tuple(violations)


class TestFindScanTimeoutViolations:
    """Unit fixtures for `find_scan_timeout_violations` itself, isolated
    from the real repo tree via `tmp_path` so they exercise the detector's
    logic (not this repo's current compliance state, which is
    `TestRepoIsScanTimeoutClean` below)."""

    @staticmethod
    def _write(tmp_path: Path, rel: str, content: str) -> None:
        """Write `content` (auto-dedented) to `tmp_path/rel`, creating
        parent directories -- shared setup for every fixture below."""
        target = tmp_path / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(textwrap.dedent(content), encoding="utf-8")

    # frob:tests tests/gates/test_scan_timeout_enforcement.py::TestFindScanTimeoutViolations.test_must_fire_on_unmarked_whole_repo_scan_call  # noqa: E501
    # frob:waive FMT001 reason="single-line frob:tests directive naming a long test \
    # node id -- already at frob fmt's own canonical form (verified: `frob fmt` \
    # reports it unchanged), same unwrappable shape as src/frob/app/_json_guard.py's \
    # existing FMT001 waivers"
    def test_must_fire_on_unmarked_whole_repo_scan_call(self, tmp_path: Path) -> None:
        """MUST-FIRE: a test that calls `build_graph` with no timeout
        override is flagged."""
        self._write(
            tmp_path,
            "tests/test_planted_violation.py",
            """
            from pathlib import Path
            from frob.graph import build_graph

            _REPO_ROOT = Path(__file__).resolve().parent.parent

            def test_scans_everything():
                build_graph(_REPO_ROOT, cache)
            """,
        )
        violations = find_scan_timeout_violations(tmp_path / "tests")
        assert [v.qualname for v in violations] == ["test_scans_everything"]

    # frob:tests tests/gates/test_scan_timeout_enforcement.py::TestFindScanTimeoutViolations.test_must_stay_quiet_on_synthetic_tmp_path_target  # noqa: E501
    # frob:waive FMT001 reason="single-line frob:tests directive naming a long test \
    # node id -- already at frob fmt's own canonical form (verified: `frob fmt` \
    # reports it unchanged), same unwrappable shape as src/frob/app/_json_guard.py's \
    # existing FMT001 waivers"
    def test_must_stay_quiet_on_synthetic_tmp_path_target(self, tmp_path: Path) -> None:
        """MUST-STAY-QUIET: `build_graph` called against a `tmp_path`
        fixture (no module-level `__file__`-derived assignment to resolve
        it to) is NOT flagged -- this is the common shape across most of
        the real suite (`build_graph(tmp_path, ...)` in dozens of files),
        and flagging it would make the gate impossibly noisy."""
        self._write(
            tmp_path,
            "tests/test_synthetic.py",
            """
            from frob.graph import build_graph

            def test_builds_synthetic_graph(tmp_path):
                build_graph(tmp_path, tmp_path / "cache.db")
            """,
        )
        assert find_scan_timeout_violations(tmp_path / "tests") == ()

    # frob:tests tests/gates/test_scan_timeout_enforcement.py::TestFindScanTimeoutViolations.test_must_stay_quiet_on_run_call_with_explicit_path_argument  # noqa: E501
    # frob:waive FMT001 reason="single-line frob:tests directive naming a long test \
    # node id -- already at frob fmt's own canonical form (verified: `frob fmt` \
    # reports it unchanged), same unwrappable shape as src/frob/app/_json_guard.py's \
    # existing FMT001 waivers"
    def test_must_stay_quiet_on_run_call_with_explicit_path_argument(
        self, tmp_path: Path
    ) -> None:
        """MUST-STAY-QUIET: `tests.system.conftest.run` called with an
        explicit (non-literal) path argument -- e.g. `run("arch",
        str(tmp_path))`, the dominant shape across `tests/system/` -- is
        NOT flagged, since it targets that explicit directory rather than
        the real repo `run`'s own default cwd would scan."""
        self._write(
            tmp_path,
            "tests/test_explicit_target.py",
            """
            from tests.system.conftest import run

            def test_arch_on_explicit_dir(tmp_path):
                r = run("arch", str(tmp_path))
                assert r.returncode == 0
            """,
        )
        assert find_scan_timeout_violations(tmp_path / "tests") == ()

    # frob:tests tests/gates/test_scan_timeout_enforcement.py::TestFindScanTimeoutViolations.test_must_stay_quiet_on_ordinary_fast_test  # noqa: E501
    # frob:waive FMT001 reason="single-line frob:tests directive naming a long test \
    # node id -- already at frob fmt's own canonical form (verified: `frob fmt` \
    # reports it unchanged), same unwrappable shape as src/frob/app/_json_guard.py's \
    # existing FMT001 waivers"
    def test_must_stay_quiet_on_ordinary_fast_test(self, tmp_path: Path) -> None:
        """MUST-STAY-QUIET: an ordinary test with no whole-repo-scan call
        is never flagged."""
        self._write(
            tmp_path,
            "tests/test_ordinary.py",
            """
            def test_addition():
                assert 1 + 1 == 2
            """,
        )
        assert find_scan_timeout_violations(tmp_path / "tests") == ()

    # frob:tests tests/gates/test_scan_timeout_enforcement.py::TestFindScanTimeoutViolations.test_must_stay_quiet_when_method_level_override_present  # noqa: E501
    # frob:waive FMT001 reason="single-line frob:tests directive naming a long test \
    # node id -- already at frob fmt's own canonical form (verified: `frob fmt` \
    # reports it unchanged), same unwrappable shape as src/frob/app/_json_guard.py's \
    # existing FMT001 waivers"
    def test_must_stay_quiet_when_method_level_override_present(
        self, tmp_path: Path
    ) -> None:
        """MUST-STAY-QUIET: a whole-repo-scan test carrying its own
        `@pytest.mark.timeout(N)` is not flagged."""
        self._write(
            tmp_path,
            "tests/test_covered.py",
            """
            from pathlib import Path
            import pytest
            from frob.graph import build_graph

            _REPO_ROOT = Path(__file__).resolve().parent.parent

            @pytest.mark.timeout(300)
            def test_scans_everything():
                build_graph(_REPO_ROOT, cache)
            """,
        )
        assert find_scan_timeout_violations(tmp_path / "tests") == ()

    # frob:tests tests/gates/test_scan_timeout_enforcement.py::TestFindScanTimeoutViolations.test_must_stay_quiet_when_class_level_pytestmark_present  # noqa: E501
    # frob:waive FMT001 reason="single-line frob:tests directive naming a long test \
    # node id -- already at frob fmt's own canonical form (verified: `frob fmt` \
    # reports it unchanged), same unwrappable shape as src/frob/app/_json_guard.py's \
    # existing FMT001 waivers"
    def test_must_stay_quiet_when_class_level_pytestmark_present(
        self, tmp_path: Path
    ) -> None:
        """MUST-STAY-QUIET: a class-level `pytestmark =
        [pytest.mark.timeout(N)]` covers every method in the class."""
        self._write(
            tmp_path,
            "tests/test_class_covered.py",
            """
            from pathlib import Path
            import pytest
            from frob.strata._selfconform import check_self_conformance

            _REPO_ROOT = Path(__file__).resolve().parent.parent

            class TestWholeRepo:
                pytestmark = [pytest.mark.timeout(300)]

                def test_conforms(self):
                    check_self_conformance(model, _REPO_ROOT)
            """,
        )
        assert find_scan_timeout_violations(tmp_path / "tests") == ()

    # frob:tests tests/gates/test_scan_timeout_enforcement.py::TestFindScanTimeoutViolations.test_must_stay_quiet_on_synthetic_repo_fixture_test  # noqa: E501
    # frob:waive FMT001 reason="single-line frob:tests directive naming a long test \
    # node id -- already at frob fmt's own canonical form (verified: `frob fmt` \
    # reports it unchanged), same unwrappable shape as src/frob/app/_json_guard.py's \
    # existing FMT001 waivers"
    def test_must_stay_quiet_on_synthetic_repo_fixture_test(
        self, tmp_path: Path
    ) -> None:
        """MUST-STAY-QUIET: `build_graph` called against a `tmp_path`-
        rooted synthetic tree is still, deliberately, flagged the same as
        a real-repo call -- the detector matches the CALL TARGET, not the
        argument, so a genuinely fast synthetic-tree test must carry the
        override too (or be added to `_ENTRYPOINT_DEFINITION_FILES` if it
        IS the entry point's own definition file). This fixture instead
        demonstrates the file-exemption path: a file listed in
        `_ENTRYPOINT_DEFINITION_FILES` is skipped outright."""
        self._write(
            tmp_path,
            "tests/system/conftest.py",
            """
            def run(*args):
                pass
            """,
        )
        assert find_scan_timeout_violations(tmp_path / "tests") == ()


class TestRepoIsScanTimeoutClean:
    """T-3247's actual GATE: every whole-repo-scan test in THIS repo's
    real `tests/` tree carries an explicit timeout override. This is what
    makes the next unmarked whole-repo-scan test a CI failure instead of a
    silent addition -- the difference between fixing the three named
    tests and closing the class, per the ticket."""

    # frob:tests tests/gates/test_scan_timeout_enforcement.py::TestRepoIsScanTimeoutClean.test_no_unmarked_whole_repo_scan_tests_in_repo  # noqa: E501
    # frob:waive FMT001 reason="single-line frob:tests directive naming a long test \
    # node id -- already at frob fmt's own canonical form (verified: `frob fmt` \
    # reports it unchanged), same unwrappable shape as src/frob/app/_json_guard.py's \
    # existing FMT001 waivers"
    def test_no_unmarked_whole_repo_scan_tests_in_repo(self) -> None:
        """Zero `ScanTimeoutViolation`s over this repo's real `tests/`
        tree -- fails loudly, naming file/line/qualname, the moment a new
        whole-repo-scan test lands without `@pytest.mark.timeout(...)`."""
        violations = find_scan_timeout_violations(_TESTS_ROOT)
        assert violations == (), (
            "whole-repo-scan test(s) with no @pytest.mark.timeout(...) override "
            f"(T-3247): {list(violations)}"
        )

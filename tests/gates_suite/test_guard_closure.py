"""Tests for `frob.gates._guard_closure` (GUARD001, T-4111).

F-307 H3-1: a guard that reads a lockout primitive but has no
route-reachable writer of the matching write primitive in the same class
is a control that fires on nothing. This ticket's own fixture note says a
must-fire/must-stay-quiet fixture cannot be drawn from frob's real tree
(frob has no route/guard/lockout shape of its own) -- every fixture here is
therefore a small SYNTHETIC package written under a tmp git repo, never
wired into frob's own runtime, per that note.
"""

from pathlib import Path

from frob.gates._guard_closure import (
    GuardClosurePair,
    guard_closure_gate,
    load_guard_closure_pairs,
)
from tests.conftest import _by_rule, _git_init, _write


# frob:tests src/frob/gates/_guard_closure.py::guard_closure_gate  # noqa: E501
def test_guard001_fires_when_no_writer_reachable(tmp_path: Path) -> None:
    """Must-fire case (a): a route-reachable method reads the lockout,
    and NOTHING in the class calls the write primitive at all -- the
    plain total-absence shape."""
    _write(
        tmp_path,
        "pkg/login.py",
        (
            "class LoginRoute:\n"
            "    @app.route('/login')\n"
            "    def handle(self, request):\n"
            "        wait = retry_after_seconds(self.__class__, request.user)\n"
            "        return wait\n"
        ),
    )
    _git_init(tmp_path)

    violations = _by_rule(guard_closure_gate(tmp_path), "GUARD001")

    assert len(violations) == 1
    assert violations[0].symref == "pkg/login.py::LoginRoute"


# frob:tests src/frob/gates/_guard_closure.py::guard_closure_gate  # noqa: E501
def test_guard001_quiet_when_writer_reachable_from_same_class_route(
    tmp_path: Path,
) -> None:
    """Must-stay-quiet case (b): a real, non-test caller reaches the
    write primitive from a route entry point in the SAME class -- the
    guard's writer is genuinely wired, closure is satisfied."""
    _write(
        tmp_path,
        "pkg/login.py",
        (
            "class LoginRoute:\n"
            "    @app.route('/login')\n"
            "    def handle(self, request):\n"
            "        wait = retry_after_seconds(self.__class__, request.user)\n"
            "        if request.failed:\n"
            "            self._on_failure(request)\n"
            "        return wait\n"
            "\n"
            "    def _on_failure(self, request):\n"
            "        record_failure(self.__class__, request.user)\n"
        ),
    )
    _git_init(tmp_path)

    violations = _by_rule(guard_closure_gate(tmp_path), "GUARD001")

    assert violations == []


# frob:tests src/frob/gates/_guard_closure.py::guard_closure_gate  # noqa: E501
def test_guard001_fires_when_writer_reachable_only_from_a_different_class(
    tmp_path: Path,
) -> None:
    """Must-fire case (c): a caller of the write primitive DOES exist in
    the tree and IS route-reachable, but only from a route in a
    DIFFERENT class -- a class-scoping bug, the closest-to-real false-
    negative shape a naive tree-wide "is record_failure called anywhere"
    scan would miss."""
    _write(
        tmp_path,
        "pkg/login.py",
        (
            "class LoginRoute:\n"
            "    @app.route('/login')\n"
            "    def handle(self, request):\n"
            "        wait = retry_after_seconds(self.__class__, request.user)\n"
            "        return wait\n"
            "\n"
            "\n"
            "class SignupRoute:\n"
            "    @app.route('/signup')\n"
            "    def handle(self, request):\n"
            "        self._on_failure(request)\n"
            "\n"
            "    def _on_failure(self, request):\n"
            "        record_failure(self.__class__, request.user)\n"
        ),
    )
    _git_init(tmp_path)

    violations = _by_rule(guard_closure_gate(tmp_path), "GUARD001")

    assert len(violations) == 1
    assert violations[0].symref == "pkg/login.py::LoginRoute"


def test_guard001_quiet_when_read_only_reachable_from_class_with_no_route(
    tmp_path: Path,
) -> None:
    """A class with no configured route entry point at all has nothing
    for closure to BFS from -- this check has no opinion on it (a
    different gate's job to flag a wholly unreached class)."""
    _write(
        tmp_path,
        "pkg/login.py",
        (
            "class Helper:\n"
            "    def handle(self, request):\n"
            "        return retry_after_seconds(self.__class__, request.user)\n"
        ),
    )
    _git_init(tmp_path)

    violations = _by_rule(guard_closure_gate(tmp_path), "GUARD001")

    assert violations == []


# frob:tests src/frob/gates/_guard_closure.py::load_guard_closure_pairs  # noqa: E501
def test_load_guard_closure_pairs_defaults_when_unconfigured(tmp_path: Path) -> None:
    """No `frob.toml` at all falls back to the one pair this ticket's own
    motivating report named."""
    pairs, markers = load_guard_closure_pairs(tmp_path)

    assert pairs == (
        GuardClosurePair(read="retry_after_seconds", write="record_failure"),
    )
    assert "route" in markers


# frob:tests src/frob/gates/_guard_closure.py::GuardClosurePair  # noqa: E501
# frob:tests src/frob/gates/_guard_closure.py::load_guard_closure_pairs  # noqa: E501
def test_load_guard_closure_pairs_reads_frob_toml(tmp_path: Path) -> None:
    """A configured `[[guard_closure.pairs]]`/`route_decorator_markers`
    fully replaces the defaults, proving this check is naming-convention-
    generic rather than hardcoded to the consumer's own symbol names."""
    _write(
        tmp_path,
        "frob.toml",
        (
            "[[guard_closure.pairs]]\n"
            'read = "is_locked_out"\n'
            'write = "mark_locked_out"\n'
            "\n"
            "[guard_closure]\n"
            'route_decorator_markers = ["endpoint"]\n'
        ),
    )

    pairs, markers = load_guard_closure_pairs(tmp_path)

    assert pairs == (GuardClosurePair(read="is_locked_out", write="mark_locked_out"),)
    assert markers == frozenset({"endpoint"})


# frob:tests src/frob/gates/_guard_closure.py::GuardClosurePair  # noqa: E501
def test_guard001_honors_configured_pair_and_route_marker(tmp_path: Path) -> None:
    """End-to-end: a project-specific pair/marker pair (not frob's
    defaults) still drives GUARD001 correctly, proving the closure logic
    itself is generic, not merely its config loader."""
    _write(
        tmp_path,
        "frob.toml",
        (
            "[[guard_closure.pairs]]\n"
            'read = "is_locked_out"\n'
            'write = "mark_locked_out"\n'
            "\n"
            "[guard_closure]\n"
            'route_decorator_markers = ["endpoint"]\n'
        ),
    )
    _write(
        tmp_path,
        "pkg/login.py",
        (
            "class LoginRoute:\n"
            "    @app.endpoint('/login')\n"
            "    def handle(self, request):\n"
            "        return is_locked_out(self.__class__, request.user)\n"
        ),
    )
    _git_init(tmp_path)

    violations = _by_rule(guard_closure_gate(tmp_path), "GUARD001")

    assert len(violations) == 1


def test_guard001_ignores_tests_directory(tmp_path: Path) -> None:
    """A write call reachable only from a route inside a `tests/`
    directory does not satisfy closure -- production route reachability,
    not any file in the tree, is what this check requires."""
    _write(
        tmp_path,
        "pkg/login.py",
        (
            "class LoginRoute:\n"
            "    @app.route('/login')\n"
            "    def handle(self, request):\n"
            "        return retry_after_seconds(self.__class__, request.user)\n"
        ),
    )
    _write(
        tmp_path,
        "tests/test_login.py",
        (
            "class LoginRoute:\n"
            "    @app.route('/login')\n"
            "    def handle(self, request):\n"
            "        record_failure(self.__class__, request.user)\n"
        ),
    )
    _git_init(tmp_path)

    violations = _by_rule(guard_closure_gate(tmp_path), "GUARD001")

    assert len(violations) == 1
    assert violations[0].file == "pkg/login.py"

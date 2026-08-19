"""T-2614: T-2450's own scope was recorded as a single ticket-frontmatter
entry containing a literal semicolon joining two globs
(`'src/frob/verify/**;src/frob/app/ticket_runner/**'`) instead of two
separate scope entries. `PurePath.match` treats `**` as an "entire path
component" wildcard and raises `ValueError` when it is not the whole
component (as happens once a semicolon glues a second pattern onto it),
so the joined string was not evaluable as "either glob" -- it matched
nothing at all, voiding T-2450's declared write lease and evidence
coverage. This test asserts T-2450's actual on-disk scope is free of
that shape and that every entry is independently usable as a glob.
"""

from pathlib import Path, PurePosixPath

import pytest

# frob:ticket T-2614
# frob:tests \
# tests/unit/test_t2450_scope_repair.py::TestT2450ScopeRepair.test_no_scope_entry_conta\
# ins_a_semicolon
# frob:tests \
# tests/unit/test_t2450_scope_repair.py::TestT2450ScopeRepair.test_every_scope_entry_is\
# _independently_matchable
class TestT2450ScopeRepair:
    """T-2614's own repro: T-2450's declared scope must be two proper
    glob entries, not one semicolon-joined string."""

    def _t2450_scope(self) -> list[str]:
        """Load T-2450's currently-declared scope list from this repo's
        own ticket store -- the exact data this test's subject is about,
        not a synthetic fixture."""
        from frob.tickets import load_queue

        root = Path(__file__).resolve().parents[2]
        queue = load_queue(root)
        assert queue.is_ok, queue.err
        ticket = queue.danger_ok.tickets.get("T-2450")
        assert ticket is not None, "T-2450 must exist in this repo's ticket store"
        return list(ticket.scope)

    def test_no_scope_entry_contains_a_semicolon(self) -> None:
        # frob:tests tests/unit/test_t2450_scope_repair.py::TestT2450ScopeRepair.test_no_scope_entry_contains_a_semicolon  # noqa: E501
        scope = self._t2450_scope()
        offenders = [entry for entry in scope if ";" in entry]
        assert offenders == [], (
            f"T-2450 scope still carries a semicolon-joined entry: {offenders!r} "
            "-- this is not a valid single glob and matches nothing"
        )

    def test_every_scope_entry_is_independently_matchable(self) -> None:
        # frob:tests tests/unit/test_t2450_scope_repair.py::TestT2450ScopeRepair.test_every_scope_entry_is_independently_matchable  # noqa: E501
        scope = self._t2450_scope()
        assert scope, "T-2450 must still declare a non-empty scope"
        probe = PurePosixPath("src/frob/verify/example.py")
        # Every entry must be independently usable as a glob against
        # PurePath.match -- a semicolon-joined string raises ValueError
        # here ("'**' can only be an entire path component") instead of
        # returning a bool, which is exactly the failure this ticket
        # fixes.
        for entry in scope:
            try:
                probe.match(entry)
            except ValueError as exc:  # pragma: no cover -- the pre-fix path
                pytest.fail(f"scope entry {entry!r} is not a valid glob: {exc}")
        assert {"src/frob/verify/**", "src/frob/app/ticket_runner/**"} <= set(scope)

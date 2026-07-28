"""T-0700 access-mode grammar read-back + SYS204 contention-proof unit
coverage (`frob.strata._access`) -- mirrors `test_host.py`'s "construct a
`Node`/`Module` directly, test the read-back function" convention: the
grammar->attr desugar itself is covered by `strata-core/src/parse.rs`'s
own unit tests (`parses_node_access_clause` et al.), this file covers the
attr->model read-back and the compatibility-matrix/contention-proof logic
built on top of it.
"""

from __future__ import annotations

from frob.strata import KernelModel, Node
from frob.strata._access import (
    SYS_UNARBITRATED_MODE_CONFLICT,
    AccessMode,
    NodeAccess,
    mode_conflict,
    node_access_declarations,
    resource_contention_violations,
)
from frob.strata._ast import Module, ResourceDecl


class TestNodeAccessDeclarations:
    # frob:tests \
    # tests/unit/strata/test_access.py::TestNodeAccessDeclarations.test_reads_access_at\
    # trs
    def test_reads_access_attrs(self):
        """`access=<resource>:<mode>` attrs read back as typed `NodeAccess`
        pairs, in declaration order."""
        node = Node(
            id="writer",
            trust="trusted",
            attrs=("access=ledger_db:write", "access=cache_db:read"),
        )
        assert node_access_declarations(node) == (
            NodeAccess(resource="ledger_db", mode=AccessMode.WRITE),
            NodeAccess(resource="cache_db", mode=AccessMode.READ),
        )

    # frob:tests \
    # tests/unit/strata/test_access.py::TestNodeAccessDeclarations.test_no_access_attrs\
    # _is_empty
    def test_no_access_attrs_is_empty(self):
        """A node with no `access` clause at all reads back an empty
        tuple, not `None` -- mirrors `_pii.py::node_pii_tags`'s
        "absent means empty, not missing" shape."""
        node = Node(id="plain", trust="trusted")
        assert node_access_declarations(node) == ()

    # frob:tests \
    # tests/unit/strata/test_access.py::TestNodeAccessDeclarations.test_unrecognized_mo\
    # de_fails_closed
    def test_unrecognized_mode_fails_closed(self):
        """A hand-built `access=` attr with a mode outside the closed
        vocabulary raises `ValueError` -- fail-closed, not silently
        skipped (module docstring: `parse_access_attr` already validates
        this at parse time, so a mismatch here means the attr did not
        come from the grammar)."""
        node = Node(id="odd", trust="trusted", attrs=("access=ledger_db:bogus",))
        try:
            node_access_declarations(node)
        except ValueError as exc:
            assert "bogus" in str(exc)
        else:
            raise AssertionError("expected ValueError for unrecognized mode")


class TestModeConflict:
    # frob:tests \
    # tests/unit/strata/test_access.py::TestModeConflict.test_read_read_is_safe
    def test_read_read_is_safe(self):
        """Any number of readers coexist -- read+read never conflicts."""
        assert mode_conflict(AccessMode.READ, AccessMode.READ) is False

    # frob:tests \
    # tests/unit/strata/test_access.py::TestModeConflict.test_read_alpha_is_safe
    def test_read_alpha_is_safe(self):
        """`alpha` never conflicts with a reader (user-specified 2026-07-22
        semantics: alpha is an upgrade-INTENT marker, not a writer yet)."""
        assert mode_conflict(AccessMode.READ, AccessMode.ALPHA) is False
        assert mode_conflict(AccessMode.ALPHA, AccessMode.READ) is False

    # frob:tests \
    # tests/unit/strata/test_access.py::TestModeConflict.test_alpha_alpha_conflicts
    def test_alpha_alpha_conflicts(self):
        """Two distinct alpha declarants conflict -- exactly one
        writer-intender per resource (prevents the two-readers-both-
        upgrading deadlock)."""
        assert mode_conflict(AccessMode.ALPHA, AccessMode.ALPHA) is True

    # frob:tests \
    # tests/unit/strata/test_access.py::TestModeConflict.test_write_conflicts_with_anyt\
    # hing
    def test_write_conflicts_with_anything(self):
        """`write+anything CONFLICT`, including read, alpha, itself, and
        the `append`/`exclusive` write-like modes (documented judgment
        call, module docstring)."""
        for other in AccessMode:
            assert mode_conflict(AccessMode.WRITE, other) is True

    # frob:tests \
    # tests/unit/strata/test_access.py::TestModeConflict.test_exclusive_conflicts_with_\
    # everything_including_itself
    def test_exclusive_conflicts_with_everything_including_itself(self):
        """`exclusive` is stricter than plain `write`: it must not coexist
        with ANY other accessor at all, including another `exclusive`."""
        for other in AccessMode:
            assert mode_conflict(AccessMode.EXCLUSIVE, other) is True

    # frob:tests \
    # tests/unit/strata/test_access.py::TestModeConflict.test_append_conflicts_with_any\
    # thing
    def test_append_conflicts_with_anything(self):
        """`append` is folded in as write-like -- it still mutates the
        resource, so `write+anything` applies to it too."""
        for other in AccessMode:
            assert mode_conflict(AccessMode.APPEND, other) is True


class TestResourceContentionViolations:
    # frob:tests \
    # tests/unit/strata/test_access.py::TestResourceContentionViolations.test_two_write\
    # rs_no_arbiter_fires
    def test_two_writers_no_arbiter_fires(self):
        """Two nodes with write-mode access to the same resource and no
        declared arbiter -- SYS204 fires (T-0700 acceptance criterion)."""
        model = KernelModel(
            nodes=(
                Node(id="a", trust="trusted", attrs=("access=ledger_db:write",)),
                Node(id="b", trust="trusted", attrs=("access=ledger_db:write",)),
            ),
        )
        module = Module(name="m")
        report = resource_contention_violations(model, module)
        assert [v.rule for v in report.violations] == [SYS_UNARBITRATED_MODE_CONFLICT]
        assert {report.violations[0].node, report.violations[0].peer} == {"a", "b"}

    # frob:tests \
    # tests/unit/strata/test_access.py::TestResourceContentionViolations.test_arbitrate\
    # d_by_discharges
    def test_arbitrated_by_discharges(self):
        """The same two write-mode accessors with a declared
        `arbitrated_by` arbiter discharge cleanly (T-0700 acceptance
        criterion)."""
        model = KernelModel(
            nodes=(
                Node(id="a", trust="trusted", attrs=("access=ledger_db:write",)),
                Node(id="b", trust="trusted", attrs=("access=ledger_db:write",)),
            ),
        )
        module = Module(
            name="m",
            resources=(ResourceDecl(id="ledger_db", arbitrated_by="a"),),
        )
        report = resource_contention_violations(model, module)
        assert report.violations == ()

    # frob:tests \
    # tests/unit/strata/test_access.py::TestResourceContentionViolations.test_lock_disc\
    # harges
    def test_lock_discharges(self):
        """A declared `lock` (lease name, no node arbiter) discharges the
        same way `arbitrated_by` does."""
        model = KernelModel(
            nodes=(
                Node(id="a", trust="trusted", attrs=("access=ledger_db:write",)),
                Node(id="b", trust="trusted", attrs=("access=ledger_db:write",)),
            ),
        )
        module = Module(
            name="m",
            resources=(ResourceDecl(id="ledger_db", lock="ledger-lease"),),
        )
        report = resource_contention_violations(model, module)
        assert report.violations == ()

    # frob:tests \
    # tests/unit/strata/test_access.py::TestResourceContentionViolations.test_read_only\
    # _modes_discharge_without_arbiter
    def test_read_only_modes_discharge_without_arbiter(self):
        """Two read-mode accessors of the same resource, no arbiter --
        clean (T-0700 acceptance criterion: read-only modes discharge)."""
        model = KernelModel(
            nodes=(
                Node(id="a", trust="trusted", attrs=("access=cache_db:read",)),
                Node(id="b", trust="trusted", attrs=("access=cache_db:read",)),
            ),
        )
        module = Module(name="m")
        report = resource_contention_violations(model, module)
        assert report.violations == ()

    # frob:tests \
    # tests/unit/strata/test_access.py::TestResourceContentionViolations.test_bare_reso\
    # urce_declaration_with_no_arbiter_still_fires
    def test_bare_resource_declaration_with_no_arbiter_still_fires(self):
        """A `resource` block that names the resource but declares
        neither `arbitrated_by` nor `lock` does NOT discharge -- a bare
        declaration is not itself an arbiter."""
        model = KernelModel(
            nodes=(
                Node(id="a", trust="trusted", attrs=("access=ledger_db:write",)),
                Node(id="b", trust="trusted", attrs=("access=ledger_db:write",)),
            ),
        )
        module = Module(name="m", resources=(ResourceDecl(id="ledger_db"),))
        report = resource_contention_violations(model, module)
        assert [v.rule for v in report.violations] == [SYS_UNARBITRATED_MODE_CONFLICT]

    # frob:tests \
    # tests/unit/strata/test_access.py::TestResourceContentionViolations.test_single_ac\
    # cessor_never_fires
    def test_single_accessor_never_fires(self):
        """A resource with exactly one declared accessor has no peer to
        conflict with -- SYS204 is single-instance-silent by construction
        (no pairwise combination exists)."""
        model = KernelModel(
            nodes=(Node(id="a", trust="trusted", attrs=("access=ledger_db:write",)),),
        )
        module = Module(name="m")
        report = resource_contention_violations(model, module)
        assert report.violations == ()

    # frob:tests \
    # tests/unit/strata/test_access.py::TestResourceContentionViolations.test_unrelated\
    # _resources_do_not_cross_conflict
    def test_unrelated_resources_do_not_cross_conflict(self):
        """Two nodes writing DIFFERENT resources never conflict -- the
        proof is per-resource, not global."""
        model = KernelModel(
            nodes=(
                Node(id="a", trust="trusted", attrs=("access=ledger_db:write",)),
                Node(id="b", trust="trusted", attrs=("access=cache_db:write",)),
            ),
        )
        module = Module(name="m")
        report = resource_contention_violations(model, module)
        assert report.violations == ()

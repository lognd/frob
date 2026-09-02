import subprocess
from pathlib import Path

from frob.gates import (
    Severity,
    drift_gate,
)
from frob.gates._docblocks import doc004_gate, doc012_gate
from frob.graph import build_graph
from frob.graph._models import LockEntry, LockFile
from tests.conftest import (
    _DOC012_FAKE_CONFIG,
    _WIDGET_PY,
    _by_rule,
    _files,
    _first_rule,
    _git_init,
    _rules,
    _snapshot,
    _write,
)


# frob:ticket T-2230
class TestMutationEvidencePackageReexports:
    """T-2230: `frob.gates`'s package `__init__` re-exports five names
    from the private `frob.gates._mutation_evidence` submodule
    (BugReproOutcome, bug_repro_outcome_at_ref, bug_repro_violations,
    designated_repro_test, mutation_evidence_violations) -- BUG002's own
    gate family. `must_still_pass_violations` (BUG003, T-2193, wired
    into land/close by T-2215) was an asymmetric omission: nothing
    distinguishes it from its siblings, and its absence forced a landed
    call site (`frob.tickets._land`) to deep-import the private
    submodule instead of the package surface."""

    def test_must_still_pass_violations_importable_from_package(self) -> None:
        # frob:tests tests/gates_suite/test_doc.py::TestMutationEvidencePackageReexports.test_must_still_pass_violations_importable_from_package  # noqa: E501
        """MUST FAIL FIRST: raises ImportError against pre-fix
        `frob.gates.__init__`, which re-exports its four siblings but
        not this one."""
        from frob.gates import must_still_pass_violations

        assert callable(must_still_pass_violations)

    def test_existing_sibling_reexports_still_resolve(self) -> None:
        # frob:tests tests/gates_suite/test_doc.py::TestMutationEvidencePackageReexports.test_existing_sibling_reexports_still_resolve  # noqa: E501
        """MUST-STILL-PASS control: the five pre-existing re-exports must
        keep resolving unchanged -- a rewritten/reordered import block
        that silently dropped one would satisfy the criterion above
        while breaking real consumers of this package surface."""
        from frob.gates import (
            BugReproOutcome,
            bug_repro_outcome_at_ref,
            bug_repro_violations,
            designated_repro_test,
            mutation_evidence_violations,
        )

        assert BugReproOutcome is not None
        for obj in (
            bug_repro_outcome_at_ref,
            bug_repro_violations,
            designated_repro_test,
            mutation_evidence_violations,
        ):
            assert callable(obj)

    def test_no_private_helper_becomes_importable(self) -> None:
        # frob:tests tests/gates_suite/test_doc.py::TestMutationEvidencePackageReexports.test_no_private_helper_becomes_importable  # noqa: E501
        """Criterion 4: adding the ONE missing re-export must not widen
        the public surface beyond it -- `_mutation_evidence`'s own
        private regexes/helpers (including the ones T-2218 touched) stay
        unreachable from the `frob.gates` package."""
        import frob.gates as gates_pkg

        for private_name in (
            "_bug002_waiver_reason",
            "_no_behavior_change_reason",
            "_must_still_pass_controls",
            "_quoted_char_ranges",
            "_BUG002_WAIVER_RE",
            "_NO_BEHAVIOR_CHANGE_RE",
            "_MUST_STILL_PASS_RE",
        ):
            assert not hasattr(gates_pkg, private_name)


class TestDriftGate:
    def test_drift001_stale_ack_has_remedy(self, tmp_path: Path) -> None:
        _write(tmp_path, "src/a.py", _WIDGET_PY)
        snap = _snapshot(tmp_path)
        ref = "src/a.py::Widget.render"
        record = snap.symbols[ref]
        lock = LockFile(entries=(LockEntry(ref=ref, facet="sig", digest="deadbeef"),))
        assert record.digests.sig != "deadbeef"

        violations = drift_gate(snap, lock)
        v = _first_rule(violations, "DRIFT001")
        assert v is not None
        assert v.severity == Severity.ERROR
        assert "frob ack" in v.message
        assert v.file == "src/a.py"

    def test_drift002_dangling_has_candidates(self, tmp_path: Path) -> None:
        _write(tmp_path, "src/a.py", _WIDGET_PY)
        _write(
            tmp_path,
            "docs/x.md",
            "# Widget\n\n<!-- frob:describes src/a.py::Widget.gone -->\n",
        )
        snap = _snapshot(tmp_path)
        lock = LockFile()
        violations = drift_gate(snap, lock)
        v = _first_rule(violations, "DRIFT002")
        assert v is not None
        assert "run: frob ack" in v.message or "candidates" in v.message

    def test_no_drift_when_clean(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/__init__.py::drift_gate
        _write(tmp_path, "src/a.py", _WIDGET_PY)
        snap = _snapshot(tmp_path)
        violations = drift_gate(snap, LockFile())
        assert violations == ()


class TestDoclinkGate:
    def test_orphan_doc_is_error_and_linked_docs_pass(self, tmp_path):
        # frob:tests src/frob/gates/_doclink_docanchor.py::doclink_gate kind="unit"
        from frob.gates import doclink_gate

        root = tmp_path / "repo"
        (root / "docs").mkdir(parents=True)
        (root / "src").mkdir()
        (root / "docs" / "index.md").write_text(
            "# Docs\n\n[linked](linked.md)\n", encoding="utf-8"
        )
        (root / "docs" / "linked.md").write_text("# Linked\n", encoding="utf-8")
        (root / "docs" / "orphan.md").write_text("# Orphan\n", encoding="utf-8")
        (root / "docs" / "described.md").write_text(
            "<!-- frob:describes src/m.py::f -->\n# Described\n", encoding="utf-8"
        )
        (root / "src" / "m.py").write_text("def f():\n    return 1\n")

        snap = build_graph(root, root / ".frob" / "cache.db").danger_ok
        violations = doclink_gate(root, snap)
        assert _files(violations) == {"docs/orphan.md"}
        assert set(_rules(violations)) <= {"DOC001"}

    def test_new_file_is_auto_obligated_by_glob(self, tmp_path):
        from frob.gates import doclink_gate

        root = tmp_path / "repo"
        (root / "docs").mkdir(parents=True)
        (root / "docs" / "index.md").write_text("# Docs\n", encoding="utf-8")
        cache = root / ".frob" / "cache.db"
        snap = build_graph(root, cache).danger_ok
        assert doclink_gate(root, snap) == ()

        (root / "docs" / "brand_new.md").write_text("# New\n", encoding="utf-8")
        violations = doclink_gate(root, build_graph(root, cache).danger_ok)
        assert {v.file for v in violations} == {"docs/brand_new.md"}

    def test_orphan_hint_does_not_point_at_missing_docs_root(self, tmp_path):
        # frob:tests src/frob/gates/_doclink_docanchor.py::doclink_gate kind="unit"
        # T-0231: default roots=["docs/index.md", "README.md"] but neither
        # exists in this repo (sibling-repo "lithos" precedent, 256 hits) --
        # the hint must not blindly name docs/index.md as if it were there.
        from frob.gates import doclink_gate

        root = tmp_path / "repo"
        (root / "docs").mkdir(parents=True)
        (root / "docs" / "orphan.md").write_text("# Orphan\n", encoding="utf-8")

        snap = build_graph(root, root / ".frob" / "cache.db").danger_ok
        violations = doclink_gate(root, snap)
        assert len(violations) == 1
        message = violations[0].message
        assert "docs/index.md" not in message or "create it" in message
        assert "no configured docs root exists" in message or "create it" in message

    def test_broken_relative_link_target_fires_doc008(self, tmp_path):
        # frob:tests src/frob/gates/_doclink_docanchor.py::doclink_gate kind="unit"
        # T-1231: an inline markdown link to a file that does not exist.
        from frob.gates import doclink_gate

        root = tmp_path / "repo"
        (root / "docs").mkdir(parents=True)
        (root / "docs" / "index.md").write_text(
            "# Docs\n\n[broken](missing.md)\n", encoding="utf-8"
        )

        snap = build_graph(root, root / ".frob" / "cache.db").danger_ok
        violations = doclink_gate(root, snap)
        assert set(_rules(violations)) == {"DOC008"}
        assert any("missing.md" in v.message for v in violations)

    def test_broken_fragment_on_existing_target_fires_doc008(self, tmp_path):
        # frob:tests src/frob/gates/_doclink_docanchor.py::doclink_gate kind="unit"
        # T-1231: the target file exists but the #fragment does not resolve.
        from frob.gates import doclink_gate

        root = tmp_path / "repo"
        (root / "docs").mkdir(parents=True)
        (root / "docs" / "index.md").write_text(
            "# Docs\n\n[bad anchor](target.md#nope)\n", encoding="utf-8"
        )
        (root / "docs" / "target.md").write_text(
            "# Target\n\n## Real Heading\n", encoding="utf-8"
        )

        snap = build_graph(root, root / ".frob" / "cache.db").danger_ok
        violations = doclink_gate(root, snap)
        assert set(_rules(violations)) == {"DOC008"}
        assert any("nope" in v.message for v in violations)

    def test_resolvable_relative_link_and_fragment_pass(self, tmp_path):
        # frob:tests src/frob/gates/_doclink_docanchor.py::doclink_gate kind="unit"
        from frob.gates import doclink_gate

        root = tmp_path / "repo"
        (root / "docs").mkdir(parents=True)
        (root / "docs" / "index.md").write_text(
            "# Docs\n\n[good](target.md#real-heading)\n"
            "[abs](https://example.com/x.md#nope)\n",
            encoding="utf-8",
        )
        (root / "docs" / "target.md").write_text(
            "# Target\n\n## Real Heading\n", encoding="utf-8"
        )

        snap = build_graph(root, root / ".frob" / "cache.db").danger_ok
        violations = doclink_gate(root, snap)
        assert set(_rules(violations)) == set()

    def test_valid_parent_relative_link_with_two_dotdots_resolves(self, tmp_path):
        # frob:tests src/frob/gates/_doclink_docanchor.py::doclink_gate kind="unit"
        # T-2704: `.replace("../", "")` deleted the `../` TEXT instead of
        # popping a directory, so `../../design/x.md` from `docs/architecture`
        # kept BOTH segments (`docs/architecture/design/x.md`, which does not
        # exist) instead of resolving to `design/x.md` (which does).
        from frob.gates import doclink_gate

        root = tmp_path / "repo"
        (root / "docs" / "architecture").mkdir(parents=True)
        (root / "design").mkdir(parents=True)
        (root / "docs" / "index.md").write_text(
            "# Docs\n\n[config](architecture/config.md)\n", encoding="utf-8"
        )
        (root / "docs" / "architecture" / "config.md").write_text(
            "# Config\n\n[quiz](../../design/mini-quizzes.md)\n", encoding="utf-8"
        )
        (root / "design" / "mini-quizzes.md").write_text(
            "# Quizzes\n", encoding="utf-8"
        )

        snap = build_graph(root, root / ".frob" / "cache.db").danger_ok
        violations = doclink_gate(root, snap)
        assert set(_rules(violations)) == set(), violations

    def test_genuinely_missing_target_still_fires_doc008_after_dotdot_fix(
        self, tmp_path
    ):
        # frob:tests src/frob/gates/_doclink_docanchor.py::doclink_gate kind="unit"
        # T-2704 control: the ../ resolution fix must not turn DOC008 into a
        # no-op -- a link that genuinely does not resolve, even with a
        # correctly-walked `../`, must still fire.
        from frob.gates import doclink_gate

        root = tmp_path / "repo"
        (root / "docs" / "architecture").mkdir(parents=True)
        (root / "docs" / "index.md").write_text(
            "# Docs\n\n[config](architecture/config.md)\n", encoding="utf-8"
        )
        (root / "docs" / "architecture" / "config.md").write_text(
            "# Config\n\n[nope](../../design/does-not-exist.md)\n", encoding="utf-8"
        )

        snap = build_graph(root, root / ".frob" / "cache.db").danger_ok
        violations = doclink_gate(root, snap)
        assert set(_rules(violations)) == {"DOC008"}
        assert any("does-not-exist.md" in v.message for v in violations)

    def test_dotdot_link_escaping_above_repo_root_is_refused(self, tmp_path):
        # frob:tests src/frob/gates/_doclink_docanchor.py::doclink_gate kind="unit"
        # T-2704 control: a link with more `../` segments than there are
        # directories to pop must be refused, not silently resolved to a
        # path outside the repo root.
        from frob.gates import doclink_gate

        root = tmp_path / "repo"
        (root / "docs").mkdir(parents=True)
        (root / "docs" / "index.md").write_text(
            "# Docs\n\n[escape](../../../etc/passwd.md)\n", encoding="utf-8"
        )

        snap = build_graph(root, root / ".frob" / "cache.db").danger_ok
        violations = doclink_gate(root, snap)
        assert set(_rules(violations)) == {"DOC008"}
        assert any("escapes above the repo root" in v.message for v in violations)


class TestDocstatusGate:
    def test_missing_status_header_fires_doc009(self, tmp_path):
        # frob:tests src/frob/gates/_docstatus.py::docstatus_gate kind="unit"
        from frob.gates import docstatus_gate

        root = tmp_path / "repo"
        (root / "docs" / "audits").mkdir(parents=True)
        (root / "docs" / "audits" / "no_header.md").write_text(
            "# An Audit\n\nSome prose with no status header at all.\n",
            encoding="utf-8",
        )
        violations = docstatus_gate(root)
        assert set(_rules(violations)) == {"DOC009"}
        assert any("no_header.md" in v.file for v in violations)

    def test_dated_status_header_passes(self, tmp_path):
        # frob:tests src/frob/gates/_docstatus.py::docstatus_gate kind="unit"
        from frob.gates import docstatus_gate

        root = tmp_path / "repo"
        (root / "docs" / "audits").mkdir(parents=True)
        (root / "docs" / "audits" / "dated.md").write_text(
            "# An Audit\n\nStatus: 2026-08-01\n\nSome prose.\n", encoding="utf-8"
        )
        assert docstatus_gate(root) == ()

    def test_superseded_header_with_missing_target_fires_doc009(self, tmp_path):
        # frob:tests src/frob/gates/_docstatus.py::docstatus_gate kind="unit"
        from frob.gates import docstatus_gate

        root = tmp_path / "repo"
        (root / "docs" / "audits").mkdir(parents=True)
        (root / "docs" / "audits" / "stale.md").write_text(
            "# An Audit\n\nStatus: SUPERSEDED (see docs/audits/missing.md)\n",
            encoding="utf-8",
        )
        violations = docstatus_gate(root)
        assert set(_rules(violations)) == {"DOC009"}
        assert any("missing.md" in v.message for v in violations)

    def test_superseded_header_with_real_target_passes(self, tmp_path):
        # frob:tests src/frob/gates/_docstatus.py::docstatus_gate kind="unit"
        from frob.gates import docstatus_gate

        root = tmp_path / "repo"
        (root / "docs" / "audits").mkdir(parents=True)
        (root / "docs" / "audits" / "stale.md").write_text(
            "# An Audit\n\nStatus: SUPERSEDED (see docs/audits/current.md)\n",
            encoding="utf-8",
        )
        (root / "docs" / "audits" / "current.md").write_text(
            "# Current\n\nStatus: 2026-08-01\n", encoding="utf-8"
        )
        assert docstatus_gate(root) == ()

    # frob:ticket T-1641
    def test_unresolvable_ticket_mention_fires_doc011(self, tmp_path):
        # frob:tests src/frob/gates/_docstatus.py::docstatus_gate kind="unit"
        # T-draft-8c110736: a prose T-####/T-draft-<hex> mention that resolves against
        # neither tickets.md nor tickets-archive.md (no ledger present at
        # all here, so nothing is known) fires DOC011.
        from frob.gates import docstatus_gate

        root = tmp_path / "repo"
        (root / "docs").mkdir(parents=True)
        (root / "docs" / "page.md").write_text(
            "# Page\n\nSee T-9999 for context.\n", encoding="utf-8"
        )
        violations = docstatus_gate(root)
        assert set(_rules(violations)) == {"DOC011"}
        assert any("T-9999" in v.message for v in violations)

    # frob:ticket T-1641
    def test_ticket_mention_inside_line_wrapped_inline_code_does_not_fire_doc011(
        self, tmp_path
    ):
        # frob:tests src/frob/gates/_docstatus.py::docstatus_gate kind="unit"
        # T-draft-8c110736: an inline `` `code` `` span that an editor hard-wrapped
        # across a line break (a single embedded newline, no blank line) is
        # still ONE token under commonmark -- the T-1228 precedent
        # `_docptr.py::_prose_tokens` already established for DOC006's own
        # scan. The previous `_INLINE_CODE_RE` (`` `[^`\n]+` ``) rejected any
        # embedded newline outright, so the second physical line of a
        # wrapped span was left un-blanked and its ticket-id-shaped content
        # (e.g. an illustrative `T-9999` inside example CLI prose) was
        # misread as an unresolvable real-prose citation. Regression for the
        # docs/modules/strata.md false positive this ticket fixed.
        from frob.gates import docstatus_gate

        root = tmp_path / "repo"
        (root / "docs").mkdir(parents=True)
        (root / "docs" / "page.md").write_text(
            '# Page\n\nExample: `waive "X" reason "r" ticket\n"T-9999";`\n',
            encoding="utf-8",
        )
        assert docstatus_gate(root) == ()

    # frob:ticket T-1641
    def test_ticket_mention_across_blank_line_still_fires_doc011(self, tmp_path):
        # frob:tests src/frob/gates/_docstatus.py::docstatus_gate kind="unit"
        # T-draft-8c110736: a genuine PARAGRAPH break (blank line) between two stray
        # backticks is NOT a wrapped code span -- it must still be treated
        # as ordinary prose and fire DOC011, matching the T-1228 precedent's
        # own blank-line rejection.
        from frob.gates import docstatus_gate

        root = tmp_path / "repo"
        (root / "docs").mkdir(parents=True)
        (root / "docs" / "page.md").write_text(
            "# Page\n\nStray `backtick.\n\nSee T-9999 here, then a `close.\n",
            encoding="utf-8",
        )
        violations = docstatus_gate(root)
        assert set(_rules(violations)) == {"DOC011"}
        assert any("T-9999" in v.message for v in violations)


class TestDocmakeGate:
    def test_bogus_make_target_fires_doc010(self, tmp_path):
        # frob:tests src/frob/gates/_docstatus.py::docmake_gate kind="unit"
        from frob.gates import docmake_gate

        root = tmp_path / "repo"
        (root / "docs").mkdir(parents=True)
        (root / "Makefile").write_text("build:\n\techo hi\n", encoding="utf-8")
        (root / "docs" / "index.md").write_text(
            "# Docs\n\nRun `make nonexistent-target` first.\n", encoding="utf-8"
        )
        snap = build_graph(root, root / ".frob" / "cache.db").danger_ok
        violations = docmake_gate(root, snap)
        assert set(_rules(violations)) == {"DOC010"}
        assert any("nonexistent-target" in v.message for v in violations)

    def test_real_make_target_passes(self, tmp_path):
        # frob:tests src/frob/gates/_docstatus.py::docmake_gate kind="unit"
        from frob.gates import docmake_gate

        root = tmp_path / "repo"
        (root / "docs").mkdir(parents=True)
        (root / "Makefile").write_text(
            "build:\n\techo hi\ninstall-tool:\n\techo installing\n", encoding="utf-8"
        )
        (root / "docs" / "index.md").write_text(
            "# Docs\n\nRun `make install-tool` first.\n", encoding="utf-8"
        )
        snap = build_graph(root, root / ".frob" / "cache.db").danger_ok
        assert docmake_gate(root, snap) == ()

    def test_no_makefile_is_a_noop(self, tmp_path):
        # frob:tests src/frob/gates/_docstatus.py::docmake_gate kind="unit"
        from frob.gates import docmake_gate

        root = tmp_path / "repo"
        (root / "docs").mkdir(parents=True)
        (root / "docs" / "index.md").write_text(
            "# Docs\n\nRun `make anything` first.\n", encoding="utf-8"
        )
        snap = build_graph(root, root / ".frob" / "cache.db").danger_ok
        assert docmake_gate(root, snap) == ()

    def test_nested_project_target_resolves_against_nested_makefile(self, tmp_path):
        # frob:tests src/frob/gates/_docstatus.py::docmake_gate kind="unit"
        # T-2705: a nested sub-project's own docs citing ITS OWN Makefile's
        # target (not present in the root Makefile) must resolve, not fire.
        from frob.gates import docmake_gate

        root = tmp_path / "repo"
        (root / "docs").mkdir(parents=True)
        (root / "slidegen" / "docs").mkdir(parents=True)
        (root / "frob.toml").write_text(
            '[gates.docs]\ninclude = ["**/*.md"]\n', encoding="utf-8"
        )
        (root / "Makefile").write_text("build:\n\techo hi\n", encoding="utf-8")
        (root / "slidegen" / "Makefile").write_text(
            "preview:\n\techo previewing\n", encoding="utf-8"
        )
        (root / "slidegen" / "docs" / "scripts.md").write_text(
            "# Scripts\n\nRun `make preview` to preview a deck.\n", encoding="utf-8"
        )
        snap = build_graph(root, root / ".frob" / "cache.db").danger_ok
        violations = docmake_gate(root, snap)
        assert violations == (), violations

    def test_nested_project_bogus_target_still_fires(self, tmp_path):
        # frob:tests src/frob/gates/_docstatus.py::docmake_gate kind="unit"
        # T-2705 control: a target absent from BOTH the nearest and the
        # root Makefile must still fire, even inside a nested project.
        from frob.gates import docmake_gate

        root = tmp_path / "repo"
        (root / "docs").mkdir(parents=True)
        (root / "slidegen" / "docs").mkdir(parents=True)
        (root / "frob.toml").write_text(
            '[gates.docs]\ninclude = ["**/*.md"]\n', encoding="utf-8"
        )
        (root / "Makefile").write_text("build:\n\techo hi\n", encoding="utf-8")
        (root / "slidegen" / "Makefile").write_text(
            "preview:\n\techo previewing\n", encoding="utf-8"
        )
        (root / "slidegen" / "docs" / "scripts.md").write_text(
            "# Scripts\n\nRun `make nonexistent-nested-target` first.\n",
            encoding="utf-8",
        )
        snap = build_graph(root, root / ".frob" / "cache.db").danger_ok
        violations = docmake_gate(root, snap)
        assert set(_rules(violations)) == {"DOC010"}
        assert any("nonexistent-nested-target" in v.message for v in violations)

    def test_root_level_doc_still_resolves_against_root_makefile(self, tmp_path):
        # frob:tests src/frob/gates/_docstatus.py::docmake_gate kind="unit"
        # T-2705 control: no regression for the single-Makefile case -- a
        # doc at repo root still resolves against the root Makefile.
        from frob.gates import docmake_gate

        root = tmp_path / "repo"
        (root / "docs").mkdir(parents=True)
        (root / "Makefile").write_text(
            "build:\n\techo hi\ninstall-tool:\n\techo installing\n", encoding="utf-8"
        )
        (root / "docs" / "index.md").write_text(
            "# Docs\n\nRun `make install-tool` first.\n", encoding="utf-8"
        )
        snap = build_graph(root, root / ".frob" / "cache.db").danger_ok
        assert docmake_gate(root, snap) == ()

    def test_nested_doc_falls_back_to_root_target_when_absent_nested(self, tmp_path):
        # frob:tests src/frob/gates/_docstatus.py::docmake_gate kind="unit"
        # T-2705 control: a nested Makefile EXISTS but does not contain the
        # cited target, while the root Makefile does -- must resolve via
        # the root fallback rather than firing.
        from frob.gates import docmake_gate

        root = tmp_path / "repo"
        (root / "docs").mkdir(parents=True)
        (root / "slidegen" / "docs").mkdir(parents=True)
        (root / "frob.toml").write_text(
            '[gates.docs]\ninclude = ["**/*.md"]\n', encoding="utf-8"
        )
        (root / "Makefile").write_text(
            "build:\n\techo hi\ninstall-tool:\n\techo installing\n", encoding="utf-8"
        )
        (root / "slidegen" / "Makefile").write_text(
            "preview:\n\techo previewing\n", encoding="utf-8"
        )
        (root / "slidegen" / "docs" / "scripts.md").write_text(
            "# Scripts\n\nSee `make install-tool` for the root install path.\n",
            encoding="utf-8",
        )
        snap = build_graph(root, root / ".frob" / "cache.db").danger_ok
        violations = docmake_gate(root, snap)
        assert violations == (), violations


class TestDocseverityGate:
    def test_mismatched_severity_row_fires_doc013(self, tmp_path):
        # frob:tests src/frob/gates/_docstatus.py::docseverity_gate kind="unit"
        from frob.gates import docseverity_gate

        root = tmp_path / "repo"
        (root / "docs").mkdir(parents=True)
        (root / "frob.toml").write_text(
            '[gates.severity]\nARCH101 = "error"\n', encoding="utf-8"
        )
        (root / "docs" / "index.md").write_text(
            "# Docs\n\n"
            "| name | detail | severity |\n"
            "| --- | --- | --- |\n"
            "| `low-cohesion-class` (ARCH101, T-0616) | LCOM4 | warning |\n",
            encoding="utf-8",
        )
        snap = build_graph(root, root / ".frob" / "cache.db").danger_ok
        violations = docseverity_gate(root, snap)
        assert set(_rules(violations)) == {"DOC013"}
        assert any("ARCH101" in v.message for v in violations)

    def test_matching_severity_row_passes(self, tmp_path):
        # frob:tests src/frob/gates/_docstatus.py::docseverity_gate kind="unit"
        from frob.gates import docseverity_gate

        root = tmp_path / "repo"
        (root / "docs").mkdir(parents=True)
        (root / "frob.toml").write_text(
            '[gates.severity]\nARCH101 = "error"\n', encoding="utf-8"
        )
        (root / "docs" / "index.md").write_text(
            "# Docs\n\n"
            "| name | detail | severity |\n"
            "| --- | --- | --- |\n"
            "| `low-cohesion-class` (ARCH101, T-0616) | LCOM4 | error |\n",
            encoding="utf-8",
        )
        snap = build_graph(root, root / ".frob" / "cache.db").danger_ok
        assert docseverity_gate(root, snap) == ()

    def test_no_override_is_a_noop(self, tmp_path):
        # frob:tests src/frob/gates/_docstatus.py::docseverity_gate kind="unit"
        # A code with no [gates.severity] override cannot be checked (no
        # independent default-severity registry exists), so a doc word
        # this repo also uses for a class default (`suggestion`) never
        # fires even though it looks similar to the mismatch shape above.
        from frob.gates import docseverity_gate

        root = tmp_path / "repo"
        (root / "docs").mkdir(parents=True)
        (root / "frob.toml").write_text("", encoding="utf-8")
        (root / "docs" / "index.md").write_text(
            "# Docs\n\n"
            "| name | detail | severity |\n"
            "| --- | --- | --- |\n"
            "| `mixed-concern-function` (ARCH103, T-0616) | mixed | suggestion |\n",
            encoding="utf-8",
        )
        snap = build_graph(root, root / ".frob" / "cache.db").danger_ok
        assert docseverity_gate(root, snap) == ()

    def test_ambiguous_doc_word_is_never_flagged(self, tmp_path):
        # frob:tests src/frob/gates/_docstatus.py::docseverity_gate kind="unit"
        # T-2080's own closed-set hardening: `suggestion`/`report` are this
        # repo's class-default vocabulary, not one of the two words this
        # gate can verify against a real [gates.severity] override value
        # -- even WITH a live override present, an ambiguous word must not
        # fire (no default-severity registry to compare it against).
        from frob.gates import docseverity_gate

        root = tmp_path / "repo"
        (root / "docs").mkdir(parents=True)
        (root / "frob.toml").write_text(
            '[gates.severity]\nARCH103 = "error"\n', encoding="utf-8"
        )
        (root / "docs" / "index.md").write_text(
            "# Docs\n\n"
            "| name | detail | severity |\n"
            "| --- | --- | --- |\n"
            "| `mixed-concern-function` (ARCH103, T-0616) | mixed | suggestion |\n",
            encoding="utf-8",
        )
        snap = build_graph(root, root / ".frob" / "cache.db").danger_ok
        assert docseverity_gate(root, snap) == ()


class TestDocanchorGate:
    def _snap(self, root: Path):

        return build_graph(root, root / ".frob" / "cache.db").danger_ok

    def test_resolvable_heading_and_explicit_anchor_pass(self, tmp_path):
        # frob:tests src/frob/gates/_doclink_docanchor.py::docanchor_gate kind="unit"
        from frob.gates import docanchor_gate

        root = tmp_path / "repo"
        (root / "docs").mkdir(parents=True)
        (root / "src").mkdir()
        (root / "docs" / "m.md").write_text(
            '# Title\n\n## Public API\n\n<a id="widget"></a>\n', encoding="utf-8"
        )
        (root / "src" / "m.py").write_text(
            "# frob:doc docs/m.md#public-api\ndef f():\n    return 1\n\n\n"
            "# frob:doc docs/m.md#widget\ndef g():\n    return 2\n",
            encoding="utf-8",
        )
        violations = docanchor_gate(root, self._snap(root))
        assert violations == ()

    def test_unresolvable_anchor_fires(self, tmp_path):
        from frob.gates import docanchor_gate

        root = tmp_path / "repo"
        (root / "docs").mkdir(parents=True)
        (root / "src").mkdir()
        (root / "docs" / "m.md").write_text(
            "# Title\n\n## Real Heading\n", encoding="utf-8"
        )
        (root / "src" / "m.py").write_text(
            "# frob:doc docs/m.md#nonexistent-slug\ndef f():\n    return 1\n",
            encoding="utf-8",
        )
        violations = docanchor_gate(root, self._snap(root))
        assert set(_rules(violations)) == {"DOC002"}
        assert any("nonexistent-slug" in v.message for v in violations)

    def test_unresolvable_anchor_reports_slug_and_nearest_match(self, tmp_path):
        # frob:tests src/frob/gates/_doclink_docanchor.py::_anchor_mismatch_message \
        # kind="unit"
        from frob.gates import docanchor_gate

        root = tmp_path / "repo"
        (root / "docs").mkdir(parents=True)
        (root / "src").mkdir()
        (root / "docs" / "m.md").write_text(
            "# Title\n\n## Real Heading\n", encoding="utf-8"
        )
        (root / "src" / "m.py").write_text(
            "# frob:doc docs/m.md#real-headin\ndef f():\n    return 1\n",
            encoding="utf-8",
        )
        violations = docanchor_gate(root, self._snap(root))
        assert set(_rules(violations)) == {"DOC002"}
        (message,) = [v.message for v in violations]
        assert "computed slug #real-headin" in message
        assert "found: real-heading" in message
        assert "did you mean #real-heading?" in message

    def test_missing_file_fires(self, tmp_path):
        from frob.gates import docanchor_gate

        root = tmp_path / "repo"
        (root / "docs").mkdir(parents=True)
        (root / "src").mkdir()
        (root / "src" / "m.py").write_text(
            "# frob:doc docs/does_not_exist.md#anything\ndef f():\n    return 1\n",
            encoding="utf-8",
        )
        violations = docanchor_gate(root, self._snap(root))
        assert set(_rules(violations)) == {"DOC002"}
        assert any("does not exist" in v.message for v in violations)

    def test_malformed_target_missing_fragment_fires(self, tmp_path):
        from frob.gates import docanchor_gate

        root = tmp_path / "repo"
        (root / "docs").mkdir(parents=True)
        (root / "src").mkdir()
        (root / "docs" / "m.md").write_text("# Title\n", encoding="utf-8")
        (root / "src" / "m.py").write_text(
            "# frob:doc docs/m.md\ndef f():\n    return 1\n", encoding="utf-8"
        )
        violations = docanchor_gate(root, self._snap(root))
        assert set(_rules(violations)) == {"DOC002"}
        assert any("no #anchor" in v.message for v in violations)


class TestDoc004CsharpUsingDrift:
    """T-2906: `csharp` fenced blocks -- `_csharp_using_violations` has no
    manifest namespace to resolve against (unlike python's package, rust's
    crate, ts's package.json name), so it mirrors `_c_include_violations`'s
    tracked-file-existence posture: a `using X.Y` naming a dotted prefix of
    a tracked `.cs` file's path is treated as project-internal."""

    def test_using_of_tracked_namespace_unanchored_warns(self, tmp_path: Path) -> None:
        _git_init(tmp_path)
        _write(
            tmp_path,
            "Sample/Missing/Real.cs",
            "namespace Sample.Missing {\n    public class Real {}\n}\n",
        )
        _write(
            tmp_path,
            "docs/guide.md",
            "```csharp\nusing Sample.Missing;\n```\n",
        )

        subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
        snapshot = _snapshot(tmp_path)
        violations = doc004_gate(tmp_path, snapshot)

        unbound = _by_rule(violations, "DOC004")
        assert unbound
        assert all(v.severity == Severity.ERROR for v in unbound)

    def test_using_of_tracked_namespace_anchored_passes(self, tmp_path: Path) -> None:
        _git_init(tmp_path)
        _write(
            tmp_path,
            "Sample/Missing/Real.cs",
            "namespace Sample.Missing {\n    public class Real {}\n}\n",
        )
        _write(
            tmp_path,
            "docs/guide.md",
            "<!-- frob:doc docs/guide.md -->\n\n"
            "```csharp\nusing Sample.Missing;\n```\n",
        )

        subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
        snapshot = _snapshot(tmp_path)
        violations = doc004_gate(tmp_path, snapshot)

        assert _by_rule(violations, "DOC004") == []


class TestDoc004JavaImportDrift:
    """T-3492: `java` fenced blocks -- `_java_import_violations` mirrors
    `_csharp_using_violations` exactly (no manifest package to resolve
    against, same tracked-file-existence posture): an `import a.b` naming
    a dotted prefix of a tracked `.java` file's path is treated as
    project-internal."""

    def test_import_of_tracked_package_unanchored_warns(self, tmp_path: Path) -> None:
        _git_init(tmp_path)
        _write(
            tmp_path,
            "sample/missing/Real.java",
            "package sample.missing;\npublic class Real {}\n",
        )
        _write(
            tmp_path,
            "docs/guide.md",
            "```java\nimport sample.missing.Real;\n```\n",
        )

        subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
        snapshot = _snapshot(tmp_path)
        violations = doc004_gate(tmp_path, snapshot)

        unbound = _by_rule(violations, "DOC004")
        assert unbound
        assert all(v.severity == Severity.ERROR for v in unbound)

    def test_import_of_tracked_package_anchored_passes(self, tmp_path: Path) -> None:
        _git_init(tmp_path)
        _write(
            tmp_path,
            "sample/missing/Real.java",
            "package sample.missing;\npublic class Real {}\n",
        )
        _write(
            tmp_path,
            "docs/guide.md",
            "<!-- frob:doc docs/guide.md -->\n\n"
            "```java\nimport sample.missing.Real;\n```\n",
        )

        subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
        snapshot = _snapshot(tmp_path)
        violations = doc004_gate(tmp_path, snapshot)

        assert _by_rule(violations, "DOC004") == []

    def test_import_of_jdk_package_is_not_project_internal(
        self, tmp_path: Path
    ) -> None:
        """`java.*`/`javax.*` imports never resolve to a tracked file, so
        they never trip DOC004 even unanchored -- same posture as
        csharp's `System.*`/`Microsoft.*` skip."""
        _git_init(tmp_path)
        _write(
            tmp_path,
            "docs/guide.md",
            "```java\nimport java.util.List;\n```\n",
        )

        subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
        snapshot = _snapshot(tmp_path)
        violations = doc004_gate(tmp_path, snapshot)

        assert _by_rule(violations, "DOC004") == []


class TestDoc004ConsoleCommandDrift:
    """T-0443: DOC004's console/bash `<prog> <subcommand>` tier is driven
    entirely by `frob.toml`'s `[[docblocks.commands]]` array -- `prog` plus
    a `module:callable` dotted path to an `argparse.ArgumentParser` factory
    this gate imports and walks at check time. No frob-specific subcommand
    list is hardcoded anywhere in `frob.gates._docblocks`; these tests use
    frob's OWN real CLI factory (`frob.__main__:_build_parser`) as the
    configured source, proving the tier derives from the live registry
    rather than a second, hand-maintained copy of it."""

    _CONFIG = (
        '[[docblocks.commands]]\nprog = "frob"\n'
        'parser = "frob.__main__:_build_parser"\n'
    )

    def test_nonexistent_subcommand_is_stale(self, tmp_path: Path) -> None:
        _git_init(tmp_path)
        _write(tmp_path, "frob.toml", self._CONFIG)
        _write(
            tmp_path,
            "docs/guide.md",
            "```console\n$ frob nonexistent-subcommand --flag\n```\n",
        )

        subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
        snapshot = _snapshot(tmp_path)
        violations = doc004_gate(tmp_path, snapshot)

        stale = _by_rule(violations, "DOC004")
        assert stale
        assert any(
            v.severity == Severity.ERROR and "nonexistent-subcommand" in v.message
            for v in stale
        )

    def test_real_subcommand_anchored_passes(self, tmp_path: Path) -> None:
        _git_init(tmp_path)
        _write(tmp_path, "frob.toml", self._CONFIG)
        _write(
            tmp_path,
            "docs/guide.md",
            "<!-- frob:doc docs/guide.md -->\n\n"
            "```console\n$ frob check --delta\n```\n",
        )

        subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
        snapshot = _snapshot(tmp_path)
        violations = doc004_gate(tmp_path, snapshot)

        assert all(v.severity != Severity.ERROR for v in _by_rule(violations, "DOC004"))

    def test_real_subcommand_unanchored_warns_unbound(self, tmp_path: Path) -> None:
        # T-3140: T-2374 (the v1.0.0 severity freeze, src/frob/gates/
        # _docblocks_shared.py::_doc004_violation) deliberately promoted
        # BOTH DOC004 tiers ("stale" and "unbound") to ERROR -- "unbound"
        # shipped at WARN and was burned to zero alongside DOC006 before
        # promotion. An unanchored-but-real console command example is
        # therefore ERROR now, not WARN; this test's name/expectation
        # predates that freeze and never got updated to match it.
        _git_init(tmp_path)
        _write(tmp_path, "frob.toml", self._CONFIG)
        _write(
            tmp_path,
            "docs/guide.md",
            "```console\n$ frob check --delta\n```\n",
        )

        subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
        snapshot = _snapshot(tmp_path)
        violations = doc004_gate(tmp_path, snapshot)

        unbound = _by_rule(violations, "DOC004")
        assert unbound
        assert all(v.severity == Severity.ERROR for v in unbound)

    def test_waive_suppresses_console_stale(self, tmp_path: Path) -> None:
        _git_init(tmp_path)
        _write(tmp_path, "frob.toml", self._CONFIG)
        _write(
            tmp_path,
            "docs/guide.md",
            '<!-- frob:waive DOC004 reason="illustrative, not real" -->\n\n'
            "```console\n$ frob nonexistent-subcommand\n```\n",
        )

        subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
        snapshot = _snapshot(tmp_path)
        violations = doc004_gate(tmp_path, snapshot)

        assert _by_rule(violations, "DOC004") == []

    def test_no_config_means_no_console_checking(self, tmp_path: Path) -> None:
        """No `[[docblocks.commands]]` entries at all -- fail-open, same
        posture as every other namespace source in this module: a project
        that has not opted in gets zero console/bash checking, never a
        crash on a plain shell example."""
        _git_init(tmp_path)
        _write(
            tmp_path,
            "docs/guide.md",
            "```console\n$ frob nonexistent-subcommand\n```\n",
        )

        subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
        snapshot = _snapshot(tmp_path)
        violations = doc004_gate(tmp_path, snapshot)

        assert _by_rule(violations, "DOC004") == []


# frob:ticket T-1783
class TestDoc012CommandSectionGate:
    """T-1783: DOC012 requires a dedicated `## `-level (or deeper) doc
    section for every live top-level subcommand, not just a DOC005
    command-table row -- driven by the same `[[docblocks.commands]]`
    config DOC004/DOC005 already read, walked via a synthetic two-command
    CLI so these tests never depend on frob's own live command count."""

    def test_undocumented_subcommand_fails(self, tmp_path: Path) -> None:
        # T-2299: promoted WARN -> ERROR once the disclosed T-1783 backlog
        # measured zero (children T-2315/T-2316) -- see
        # tests/test_doc012_promotion.py::TestDoc012PromotedToError for
        # the must-fail fixture that originally proved this severity
        # change, added there instead of here because this class carried
        # a live cross-worktree lease (T-2314) at promotion time.
        _git_init(tmp_path)
        _write(tmp_path, "frob.toml", _DOC012_FAKE_CONFIG)
        _write(
            tmp_path,
            "docs/commands/widget.md",
            "# acme widget\n\nDoes widget things.\n",
        )
        subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)

        violations = doc012_gate(tmp_path)

        stale = _by_rule(violations, "DOC012")
        assert any(
            v.severity == Severity.ERROR and "gadget" in v.message for v in stale
        )
        assert not any("widget" in v.message for v in stale)

    def test_documented_subcommand_passes(self, tmp_path: Path) -> None:
        _git_init(tmp_path)
        _write(tmp_path, "frob.toml", _DOC012_FAKE_CONFIG)
        _write(
            tmp_path,
            "docs/commands/widget.md",
            "# acme widget\n\nDoes widget things.\n",
        )
        _write(
            tmp_path,
            "docs/modules/gadget.md",
            "## `acme gadget` (CLI verb, T-9999)\n\nDoes gadget things.\n",
        )
        subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)

        violations = doc012_gate(tmp_path)

        assert _by_rule(violations, "DOC012") == []

    def test_table_row_alone_does_not_satisfy(self, tmp_path: Path) -> None:
        """A DOC005-satisfying README table row is not a dedicated
        section -- DOC012 still fires (the whole point of the rule)."""
        _git_init(tmp_path)
        _write(tmp_path, "frob.toml", _DOC012_FAKE_CONFIG)
        _write(
            tmp_path,
            "README.md",
            "## Commands\n\n| Command | Description |\n"
            "|---|---|\n"
            "| `acme widget` | does widget things |\n"
            "| `acme gadget` | does gadget things |\n",
        )
        subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)

        violations = doc012_gate(tmp_path)

        stale = _by_rule(violations, "DOC012")
        assert any("widget" in v.message for v in stale)
        assert any("gadget" in v.message for v in stale)

    def test_no_config_means_no_checking(self, tmp_path: Path) -> None:
        """No `[[docblocks.commands]]` entries at all -- fail-open, same
        posture as DOC004/DOC005: a project that has not opted in gets
        zero DOC012 checking, never a crash."""
        _git_init(tmp_path)
        subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)

        violations = doc012_gate(tmp_path)

        assert _by_rule(violations, "DOC012") == []

"""Tests for `frob.refactor`'s resolve/plan/apply/verify pipeline
(T-1197, docs/design/refactor-verb.md)."""

from __future__ import annotations

import subprocess
from pathlib import Path

from frob.refactor import (
    RefactorError,
    RefactorKind,
    SymbolRef,
    apply_plan,
    build_plan,
    carry_lock_acks,
    extend_span_for_attached_directives,
    resolve_rename_dest_collision,
    resolve_symbol,
    run_refactor,
    scan_directive_carriers,
    scan_doc_anchor_carriers,
    scan_docs_prose_mentions,
    scan_evidence_citations,
    scan_pii_allowlist_carrier,
    scan_python_prose_mentions,
    scan_references,
    scan_registry_citations,
)
from frob.refactor._resolve import module_to_path


# frob:waive DUP001 reason="the git-init/config trio is the established test-repo-fixture \
# shape shared by tests/test_stats.py::_repo and several other test modules \
# (tests/test_decisions.py, tests/test_prework_parity.py) -- each test module owns its own \
# tiny fixture builder by convention rather than importing a cross-file shared helper; \
# extracting one would be a cross-file refactor out of T-1197's declared scope \
# (tests/test_refactor.py only)"  # noqa: E501
def _repo(tmp_path: Path) -> Path:
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=tmp_path, check=True)
    return tmp_path


def _commit_all(root: Path, subject: str) -> None:
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    subprocess.run(["git", "commit", "-q", "-m", subject], cwd=root, check=True)


def _write(root: Path, rel: str, text: str) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


class TestResolveSymbol:
    def test_resolves_top_level_function(self, tmp_path):
        # frob:tests \
        # tests/test_refactor.py::TestResolveSymbol.test_resolves_top_level_function
        root = _repo(tmp_path)
        _write(root, "src/pkg/mod.py", "def greet():\n    return 'hi'\n")
        result = resolve_symbol(root, SymbolRef(module="pkg.mod", qualname="greet"))
        assert result.is_ok
        resolved = result.danger_ok
        assert resolved.start_line == 1
        assert resolved.end_line == 2
        assert resolved.is_class is False

    def test_missing_module_is_target_not_found(self, tmp_path):
        # frob:tests \
        # tests/test_refactor.py::TestResolveSymbol.test_missing_module_is_target_not_f\
        # ound
        root = _repo(tmp_path)
        result = resolve_symbol(root, SymbolRef(module="pkg.absent", qualname="x"))
        assert result.is_err
        assert result.danger_err == RefactorError.TargetNotFound

    def test_missing_qualname_is_target_not_found(self, tmp_path):
        # frob:tests \
        # tests/test_refactor.py::TestResolveSymbol.test_missing_qualname_is_target_not\
        # _found
        root = _repo(tmp_path)
        _write(root, "src/pkg/mod.py", "def other():\n    pass\n")
        result = resolve_symbol(root, SymbolRef(module="pkg.mod", qualname="greet"))
        assert result.is_err
        assert result.danger_err == RefactorError.TargetNotFound

    def test_resolves_class_method(self, tmp_path):
        # frob:tests \
        # tests/test_refactor.py::TestResolveSymbol.test_resolves_class_method
        root = _repo(tmp_path)
        _write(
            root,
            "src/pkg/mod.py",
            "class Widget:\n    def build(self):\n        return 1\n",
        )
        result = resolve_symbol(
            root, SymbolRef(module="pkg.mod", qualname="Widget.build")
        )
        assert result.is_ok
        assert result.danger_ok.is_class is False


class TestScanReferences:
    def test_finds_from_import_call_site(self, tmp_path):
        # frob:tests \
        # tests/test_refactor.py::TestScanReferences.test_finds_from_import_call_site
        root = _repo(tmp_path)
        _write(root, "src/pkg/mod.py", "def greet():\n    return 'hi'\n")
        _write(
            root,
            "src/pkg/caller.py",
            "from pkg.mod import greet\n\ndef use():\n    return greet()\n",
        )
        resolved = resolve_symbol(
            root, SymbolRef(module="pkg.mod", qualname="greet")
        ).danger_ok
        dest = SymbolRef(module="pkg.newmod", qualname="greet")
        ops, aliases, unresolved = scan_references(root, resolved, dest)
        assert len(ops) == 1
        assert "pkg.newmod import greet" in ops[0].new_text
        assert aliases == []
        assert unresolved == []

    def test_auto_alias_on_call_site_name_collision(self, tmp_path):
        # frob:tests \
        # tests/test_refactor.py::TestScanReferences.test_auto_alias_on_call_site_name_\
        # collision
        root = _repo(tmp_path)
        _write(root, "src/pkg/mod.py", "def greet():\n    return 'hi'\n")
        _write(
            root,
            "src/pkg/caller.py",
            "import shadow_target\n"
            "from pkg.mod import greet\n\n"
            "def use():\n    return greet()\n",
        )
        resolved = resolve_symbol(
            root, SymbolRef(module="pkg.mod", qualname="greet")
        ).danger_ok
        # Rename destination's leaf name to something already bound in
        # caller.py's scope (`shadow_target`) -- forces the alias branch:
        # the call site gets an auto-generated alias rather than a bare
        # rewrite that would silently rebind `shadow_target`.
        dest = SymbolRef(module="pkg.newmod", qualname="shadow_target")
        ops, aliases, unresolved = scan_references(root, resolved, dest)
        assert len(aliases) == 1
        assert aliases[0].original_name == "shadow_target"
        assert aliases[0].alias_name.endswith("_refactored")
        assert unresolved == []

    def test_semicolon_joined_from_import_refuses_rewrite(self, tmp_path):
        # frob:tests \
        # tests/test_refactor.py::TestScanReferences.test_semicolon_joined_from_import_\
        # refuses_rewrite
        root = _repo(tmp_path)
        _write(root, "src/pkg/mod.py", "def greet():\n    return 'hi'\n")
        _write(
            root,
            "src/pkg/caller.py",
            "from pkg.mod import greet; other_marker = 1\n\n"
            "def use():\n    return greet()\n",
        )
        resolved = resolve_symbol(
            root, SymbolRef(module="pkg.mod", qualname="greet")
        ).danger_ok
        dest = SymbolRef(module="pkg.newmod", qualname="greet")
        ops, aliases, unresolved = scan_references(root, resolved, dest)
        # No mechanical rewrite op for the shared-line import -- rewriting
        # the whole `[lineno, end_lineno]` span would silently delete
        # `other_marker = 1`, which lives on the same physical line.
        assert ops == []
        assert len(unresolved) == 1
        assert "semicolon-joined" in unresolved[0]

    def test_unresolved_attribute_style_reference_surfaces(self, tmp_path):
        # frob:tests \
        # tests/test_refactor.py::TestScanReferences.test_unresolved_attribute_style_re\
        # ference_surfaces
        root = _repo(tmp_path)
        _write(root, "src/pkg/mod.py", "def greet():\n    return 'hi'\n")
        _write(
            root,
            "src/pkg/caller.py",
            "import pkg.mod\n\ndef use():\n    return pkg.mod.greet()\n",
        )
        resolved = resolve_symbol(
            root, SymbolRef(module="pkg.mod", qualname="greet")
        ).danger_ok
        dest = SymbolRef(module="pkg.newmod", qualname="greet")
        ops, aliases, unresolved = scan_references(root, resolved, dest)
        # `import pkg.mod` + `pkg.mod.greet(...)` attribute-style usage is
        # not mechanically rewritten (v1 scans `from ... import` call
        # sites only) -- it must surface in `unresolved`, never silently
        # drop.
        assert ops == []
        assert len(unresolved) == 1
        assert "pkg.mod.greet" in unresolved[0]
        assert "caller.py" in unresolved[0]


class TestApplyPlan:
    def test_apply_then_rollback_restores_tree(self, tmp_path):
        # frob:tests \
        # tests/test_refactor.py::TestApplyPlan.test_apply_then_rollback_restores_tree
        root = _repo(tmp_path)
        _write(root, "src/pkg/mod.py", "def greet():\n    return 'hi'\n")
        _write(
            root,
            "src/pkg/caller.py",
            "from pkg.mod import greet\n\ndef use():\n    return greet()\n",
        )
        _commit_all(root, "initial")

        plan_result = build_plan(
            root,
            RefactorKind.MOVE,
            SymbolRef(module="pkg.mod", qualname="greet"),
            SymbolRef(module="pkg.newmod", qualname="greet"),
        )
        assert plan_result.is_ok
        plan = plan_result.danger_ok

        pre_sha = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

        apply_result = apply_plan(root, plan)
        assert apply_result.is_ok

        new_module_path = module_to_path(root, "pkg.newmod")
        assert new_module_path.is_file()
        assert "def greet" in new_module_path.read_text(encoding="utf-8")

        old_text = (root / "src/pkg/mod.py").read_text(encoding="utf-8")
        assert "def greet" not in old_text

        caller_text = (root / "src/pkg/caller.py").read_text(encoding="utf-8")
        assert "from pkg.newmod import greet" in caller_text

        # Rollback: git reset --hard to the pre-transaction sha restores
        # the tree exactly, never touching refs/stash.
        subprocess.run(["git", "add", "-A"], cwd=root, check=True, capture_output=True)
        subprocess.run(
            ["git", "reset", "--hard", pre_sha],
            cwd=root,
            check=True,
            capture_output=True,
        )
        restored = (root / "src/pkg/mod.py").read_text(encoding="utf-8")
        assert "def greet" in restored
        assert not new_module_path.exists()

    def test_overlapping_ops_refuse_before_write(self, tmp_path):
        # frob:tests \
        # tests/test_refactor.py::TestApplyPlan.test_overlapping_ops_refuse_before_write
        from frob.refactor._models import RefactorKind, RefactorPlan, RewriteOp

        root = _repo(tmp_path)
        target = _write(root, "src/pkg/mod.py", "x = 1\ny = 2\nz = 3\n")
        _commit_all(root, "initial")
        original = target.read_text(encoding="utf-8")

        # Two ops both computed against the ORIGINAL source, targeting
        # overlapping line ranges in the same file -- applying either
        # order would silently clobber the other's rewrite.
        op_a = RewriteOp(
            file_path=str(target),
            start_line=1,
            end_line=2,
            old_text="x = 1\ny = 2",
            new_text="x = 100\ny = 200",
            reason="op-a",
        )
        op_b = RewriteOp(
            file_path=str(target),
            start_line=2,
            end_line=2,
            old_text="y = 2",
            new_text="y = 999",
            reason="op-b",
        )
        plan = RefactorPlan(
            kind=RefactorKind.MOVE,
            source=_fake_resolved(str(target)),
            destination=SymbolRef(module="pkg.mod", qualname="x"),
            move_ops=(op_a,),
            reference_ops=(op_b,),
            aliases=(),
        )
        result = apply_plan(root, plan)
        assert result.is_err
        assert result.danger_err == RefactorError.OverlappingRewrites
        # No write happened -- the file is untouched.
        assert target.read_text(encoding="utf-8") == original

    def test_apply_failed_on_write_error_reports_apply_failed(
        self, tmp_path, monkeypatch
    ):
        # frob:tests \
        # tests/test_refactor.py::TestApplyPlan.test_apply_failed_on_write_error_report\
        # s_apply_failed
        from frob.refactor._models import RefactorKind, RefactorPlan, RewriteOp

        root = _repo(tmp_path)
        target = _write(root, "src/pkg/mod.py", "x = 1\n")
        _commit_all(root, "initial")

        op = RewriteOp(
            file_path=str(target),
            start_line=1,
            end_line=1,
            old_text="x = 1",
            new_text="x = 2",
            reason="op",
        )
        plan = RefactorPlan(
            kind=RefactorKind.MOVE,
            source=_fake_resolved(str(target)),
            destination=SymbolRef(module="pkg.mod", qualname="x"),
            move_ops=(op,),
            reference_ops=(),
            aliases=(),
        )

        import frob.refactor._apply as apply_mod

        def _boom(*_a, **_kw):
            raise OSError("disk full (simulated)")

        monkeypatch.setattr(apply_mod.Path, "write_text", _boom)

        result = apply_plan(root, plan)
        assert result.is_err
        assert result.danger_err == RefactorError.ApplyFailed


def _fake_resolved(file_path: str):
    """A minimal `ResolvedSymbol` for tests that only need `apply_plan`'s
    own machinery, not a real Resolve-phase result."""
    from frob.refactor._models import ResolvedSymbol

    return ResolvedSymbol(
        ref=SymbolRef(module="pkg.mod", qualname="x"),
        file_path=file_path,
        start_line=1,
        end_line=1,
        is_class=False,
    )


class TestBuildPlan:
    def test_plan_includes_move_and_reference_ops(self, tmp_path):
        # frob:tests \
        # tests/test_refactor.py::TestBuildPlan.test_plan_includes_move_and_reference_o\
        # ps
        root = _repo(tmp_path)
        _write(root, "src/pkg/mod.py", "def greet():\n    return 'hi'\n")
        _write(
            root,
            "src/pkg/caller.py",
            "from pkg.mod import greet\n\ndef use():\n    return greet()\n",
        )
        result = build_plan(
            root,
            RefactorKind.RENAME,
            SymbolRef(module="pkg.mod", qualname="greet"),
            SymbolRef(module="pkg.mod", qualname="hello"),
        )
        assert result.is_ok
        plan = result.danger_ok
        assert len(plan.move_ops) == 2
        # One op rewrites the `from pkg.mod import greet` line itself,
        # one renames the `greet()` call-site usage -- both are needed
        # since the imported name changes from `greet` to `hello`.
        assert len(plan.reference_ops) == 2
        assert len(plan.all_ops) == 4

    def test_destination_collision_refuses(self, tmp_path):
        # frob:tests \
        # tests/test_refactor.py::TestBuildPlan.test_destination_collision_refuses
        root = _repo(tmp_path)
        _write(
            root,
            "src/pkg/mod.py",
            "def greet():\n    return 'hi'\n\n\ndef hello():\n    return 'yo'\n",
        )
        result = build_plan(
            root,
            RefactorKind.RENAME,
            SymbolRef(module="pkg.mod", qualname="greet"),
            SymbolRef(module="pkg.mod", qualname="hello"),
        )
        assert result.is_err
        assert result.danger_err == RefactorError.DestinationCollision

    def test_missing_target_refuses(self, tmp_path):
        # frob:tests tests/test_refactor.py::TestBuildPlan.test_missing_target_refuses
        root = _repo(tmp_path)
        result = build_plan(
            root,
            RefactorKind.MOVE,
            SymbolRef(module="pkg.absent", qualname="x"),
            SymbolRef(module="pkg.newmod", qualname="x"),
        )
        assert result.is_err
        assert result.danger_err == RefactorError.TargetNotFound


class TestRunRefactor:
    def test_dirty_working_tree_refuses(self, tmp_path):
        # frob:tests \
        # tests/test_refactor.py::TestRunRefactor.test_dirty_working_tree_refuses
        root = _repo(tmp_path)
        _write(root, "src/pkg/mod.py", "def greet():\n    return 'hi'\n")
        _commit_all(root, "initial")
        _write(root, "src/pkg/mod.py", "def greet():\n    return 'changed'\n")

        result = run_refactor(
            root,
            RefactorKind.RENAME,
            SymbolRef(module="pkg.mod", qualname="greet"),
            SymbolRef(module="pkg.mod", qualname="hello"),
        )
        assert result.is_err
        assert result.danger_err == RefactorError.DirtyWorkingTree

    def test_rename_succeeds_and_commits(self, tmp_path):
        # frob:tests \
        # tests/test_refactor.py::TestRunRefactor.test_rename_succeeds_and_commits
        root = _repo(tmp_path)
        _write(root, "src/pkg/mod.py", "def greet():\n    return 'hi'\n")
        _write(
            root,
            "src/pkg/caller.py",
            "from pkg.mod import greet\n\ndef use():\n    return greet()\n",
        )
        _commit_all(root, "initial")

        result = run_refactor(
            root,
            RefactorKind.RENAME,
            SymbolRef(module="pkg.mod", qualname="greet"),
            SymbolRef(module="pkg.mod", qualname="hello"),
            run_pytest_collect=False,
            run_check_delta=False,
        )
        assert result.is_ok
        report = result.danger_ok
        assert report.success is True
        assert report.rolled_back is False
        assert report.commit_sha is not None

        caller_text = (root / "src/pkg/caller.py").read_text(encoding="utf-8")
        assert "hello" in caller_text
        mod_text = (root / "src/pkg/mod.py").read_text(encoding="utf-8")
        assert "def hello" in mod_text

    def test_target_not_found_refuses_with_no_writes(self, tmp_path):
        # frob:tests \
        # tests/test_refactor.py::TestRunRefactor.test_target_not_found_refuses_with_no\
        # _writes
        root = _repo(tmp_path)
        _write(root, "src/pkg/mod.py", "def greet():\n    return 'hi'\n")
        _commit_all(root, "initial")

        result = run_refactor(
            root,
            RefactorKind.RENAME,
            SymbolRef(module="pkg.mod", qualname="absent"),
            SymbolRef(module="pkg.mod", qualname="hello"),
        )
        assert result.is_err
        assert result.danger_err == RefactorError.TargetNotFound
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        assert status.strip() == ""

    def test_verify_failure_rolls_back(self, tmp_path):
        # frob:tests \
        # tests/test_refactor.py::TestRunRefactor.test_verify_failure_rolls_back
        root = _repo(tmp_path)
        # A source file whose body, once the definition is spliced out,
        # leaves behind syntactically invalid Python (an orphaned
        # decorator) so verify_import_resolution fails and forces a
        # rollback.
        _write(
            root,
            "src/pkg/mod.py",
            "@some_decorator\ndef greet():\n    return 'hi'\n",
        )
        _commit_all(root, "initial")
        pre_sha = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

        result = run_refactor(
            root,
            RefactorKind.MOVE,
            SymbolRef(module="pkg.mod", qualname="greet"),
            SymbolRef(module="pkg.newmod", qualname="greet"),
            run_pytest_collect=False,
            run_check_delta=False,
        )
        assert result.is_ok
        report = result.danger_ok
        assert report.success is False
        assert report.rolled_back is True

        head_sha = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        assert head_sha == pre_sha
        restored = (root / "src/pkg/mod.py").read_text(encoding="utf-8")
        assert "def greet" in restored

    def test_apply_failure_recovers_clean_precommit_tree(self, tmp_path, monkeypatch):
        # frob:tests \
        # tests/test_refactor.py::TestRunRefactor.test_apply_failure_recovers_clean_pre\
        # commit_tree
        root = _repo(tmp_path)
        _write(root, "src/pkg/mod.py", "def greet():\n    return 'hi'\n")
        _write(
            root,
            "src/pkg/caller.py",
            "from pkg.mod import greet\n\ndef use():\n    return greet()\n",
        )
        _commit_all(root, "initial")
        pre_sha = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

        import frob.refactor._apply as apply_mod

        real_write_text = Path.write_text
        calls = {"n": 0}

        def _fail_second_write(self, *a, **kw):
            calls["n"] += 1
            if calls["n"] >= 2:
                raise OSError("disk full (simulated) mid-file-set")
            return real_write_text(self, *a, **kw)

        monkeypatch.setattr(apply_mod.Path, "write_text", _fail_second_write)

        result = run_refactor(
            root,
            RefactorKind.RENAME,
            SymbolRef(module="pkg.mod", qualname="greet"),
            SymbolRef(module="pkg.mod", qualname="hello"),
            run_pytest_collect=False,
            run_check_delta=False,
        )
        assert result.is_err
        assert result.danger_err == RefactorError.ApplyFailed

        # The pre-commit reset-and-clean recovery (_transaction.py's
        # `git checkout -- .` + `git clean -fd`) must leave a genuinely
        # clean, unchanged tree -- no commit was ever made, so nothing
        # should differ from the pre-transaction sha.
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        assert status.strip() == ""
        head_sha = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        assert head_sha == pre_sha
        mod_text = (root / "src/pkg/mod.py").read_text(encoding="utf-8")
        assert "def greet" in mod_text


class TestVerify:
    def test_import_resolution_catches_syntax_error(self, tmp_path):
        # frob:tests \
        # tests/test_refactor.py::TestVerify.test_import_resolution_catches_syntax_error
        from frob.refactor import verify_import_resolution

        bad = _write(tmp_path, "broken.py", "def f(:\n    pass\n")
        outcome = verify_import_resolution([bad])
        assert outcome.passed is False
        assert outcome.name == "import_resolution"

    def test_import_resolution_passes_clean_files(self, tmp_path):
        # frob:tests \
        # tests/test_refactor.py::TestVerify.test_import_resolution_passes_clean_files
        from frob.refactor import verify_import_resolution

        good = _write(tmp_path, "ok.py", "def f():\n    return 1\n")
        outcome = verify_import_resolution([good])
        assert outcome.passed is True

    def test_pytest_collect_reports_failure(self, tmp_path):
        # frob:tests \
        # tests/test_refactor.py::TestVerify.test_pytest_collect_reports_failure
        from frob.refactor._verify import verify_pytest_collect

        _write(tmp_path, "test_broken.py", "def test_x(:\n    pass\n")
        outcome = verify_pytest_collect(tmp_path, targets=[tmp_path / "test_broken.py"])
        assert outcome.passed is False
        assert outcome.name == "pytest_collect"

    def test_check_delta_reports_command_failure(self, tmp_path):
        # frob:tests \
        # tests/test_refactor.py::TestVerify.test_check_delta_reports_command_failure
        from frob.refactor._verify import verify_check_delta

        # An empty, non-frob directory: `frob check --delta` run there
        # fails (not a frob repo) -- proves the outcome carries a
        # non-zero-exit failure through as `passed=False`, not a crash.
        outcome = verify_check_delta(tmp_path, timeout=30)
        assert outcome.name == "check_delta"
        assert outcome.passed is False

    def test_check_delta_uses_current_interpreter(self, tmp_path, monkeypatch):
        # frob:tests \
        # tests/test_refactor.py::TestVerify.test_check_delta_uses_current_interpreter
        import sys

        import frob.refactor._verify as verify_mod

        captured = {}

        def _fake_run(args, **kw):
            captured["args"] = args
            from typani import Ok

            return Ok(
                subprocess.CompletedProcess(
                    args=args, returncode=0, stdout="", stderr=""
                )
            )

        monkeypatch.setattr(verify_mod, "guarded_subprocess_run", _fake_run)
        verify_mod.verify_check_delta(tmp_path, timeout=30)
        # Must invoke `sys.executable -m frob`, version-consistent with the
        # running interpreter -- never a bare `frob` on PATH, which could
        # resolve to a stale globally-installed binary (agent-playbook.md
        # sec 2).
        assert captured["args"][:3] == [sys.executable, "-m", "frob"]

    def test_import_resolution_catches_dangling_reference(self, tmp_path):
        # frob:tests \
        # tests/test_refactor.py::TestVerify.test_import_resolution_catches_dangling_re\
        # ference
        from frob.refactor import verify_import_resolution

        root = _repo(tmp_path)
        _write(root, "src/pkg/mod.py", "def other():\n    return 1\n")
        caller = _write(
            root,
            "src/pkg/caller.py",
            "from pkg.mod import greet\n\ndef use():\n    return greet()\n",
        )
        # `caller.py` still imports `greet` from `pkg.mod`, but `pkg.mod`
        # no longer defines it (e.g. a botched move left the import
        # unrewritten) -- a real import-graph resolution check must catch
        # this even though the file parses as syntactically valid Python.
        outcome = verify_import_resolution([caller], repo_root=root)
        assert outcome.passed is False
        assert "greet" in outcome.detail

    def test_import_resolution_local_import_resolves(self, tmp_path):
        # frob:tests \
        # tests/test_refactor.py::TestVerify.test_import_resolution_local_import_resolv\
        # es
        from frob.refactor import verify_import_resolution

        root = _repo(tmp_path)
        _write(root, "src/pkg/mod.py", "def greet():\n    return 1\n")
        caller = _write(
            root,
            "src/pkg/caller.py",
            "from pkg.mod import greet\n\ndef use():\n    return greet()\n",
        )
        outcome = verify_import_resolution([caller], repo_root=root)
        assert outcome.passed is True


class TestFindPythonFiles:
    def test_finds_py_files_and_skips_venv(self, tmp_path):
        # frob:tests tests/test_refactor.py::TestFindPythonFiles.test_finds_py_files_and_skips_venv  # noqa: E501
        from frob.refactor import find_python_files

        _write(tmp_path, "src/pkg/mod.py", "x = 1\n")
        _write(tmp_path, ".venv/lib/ignored.py", "x = 1\n")
        found = find_python_files(tmp_path)
        rels = {p.relative_to(tmp_path) for p in found}
        assert Path("src/pkg/mod.py") in rels
        assert not any(".venv" in p.parts for p in found)


class TestModuleToPath:
    def test_maps_dotted_module_under_src(self, tmp_path):
        # frob:tests tests/test_refactor.py::TestModuleToPath.test_maps_dotted_module_under_src  # noqa: E501
        (tmp_path / "src").mkdir()
        path = module_to_path(tmp_path, "pkg.sub.mod")
        assert path == tmp_path / "src" / "pkg" / "sub" / "mod.py"


class TestPlanProperties:
    def test_plan_and_report_touched_files_dedupe(self, tmp_path):
        # frob:tests tests/test_refactor.py::TestPlanProperties.test_plan_and_report_touched_files_dedupe  # noqa: E501
        root = _repo(tmp_path)
        _write(root, "src/pkg/mod.py", "def greet():\n    return 'hi'\n")
        _write(
            root,
            "src/pkg/caller.py",
            "from pkg.mod import greet\n\ndef use():\n    return greet()\n",
        )
        _commit_all(root, "initial")

        plan = build_plan(
            root,
            RefactorKind.RENAME,
            SymbolRef(module="pkg.mod", qualname="greet"),
            SymbolRef(module="pkg.mod", qualname="hello"),
        ).danger_ok
        assert len(plan.all_ops) == len(plan.move_ops) + len(plan.reference_ops)
        touched = plan.touched_files
        assert len(touched) == len(set(touched))

        report = run_refactor(
            root,
            RefactorKind.RENAME,
            SymbolRef(module="pkg.mod", qualname="greet"),
            SymbolRef(module="pkg.mod", qualname="hello"),
            run_pytest_collect=False,
            run_check_delta=False,
        ).danger_ok
        assert report.touched_files == report.plan.touched_files


class TestBuildMoveOps:
    def test_build_move_ops_deletes_and_appends(self, tmp_path):
        # frob:tests tests/test_refactor.py::TestBuildMoveOps.test_build_move_ops_deletes_and_appends  # noqa: E501
        from frob.refactor._apply import build_move_ops

        root = _repo(tmp_path)
        source = _write(root, "src/pkg/mod.py", "def greet():\n    return 'hi'\n")
        delete_op, append_op = build_move_ops(
            root, str(source), 1, 2, "pkg.newmod", "hello", "greet"
        )
        assert delete_op.new_text == ""
        assert "def hello" in append_op.new_text


class TestCli:
    def test_add_refactor_parser_registers_move_and_rename(self):
        # frob:tests tests/test_refactor.py::TestCli.test_add_refactor_parser_registers_move_and_rename  # noqa: E501
        import argparse

        from frob.refactor._cli import add_refactor_parser

        parser = argparse.ArgumentParser()
        sub = parser.add_subparsers(dest="subcommand")
        add_refactor_parser(sub)
        args = parser.parse_args(["refactor", "move", "pkg.mod:x", "pkg.new:x"])
        assert args.source == SymbolRef(module="pkg.mod", qualname="x")
        assert args.destination == SymbolRef(module="pkg.new", qualname="x")

    def test_run_refactor_command_reports_refusal_exit_code(self, tmp_path, capsys):
        # frob:tests tests/test_refactor.py::TestCli.test_run_refactor_command_reports_refusal_exit_code  # noqa: E501
        import argparse
        import os

        from frob.refactor._cli import run_refactor_command

        root = _repo(tmp_path)
        _write(root, "placeholder.txt", "x\n")
        _commit_all(root, "initial")
        cwd = os.getcwd()
        os.chdir(root)
        try:
            args = argparse.Namespace(
                _refactor_kind=RefactorKind.RENAME,
                source=SymbolRef(module="pkg.absent", qualname="x"),
                destination=SymbolRef(module="pkg.absent", qualname="y"),
                alias_conflict="error",
                skip_check_delta=True,
                full_repo_collect=False,
            )
            code = run_refactor_command(args)
        finally:
            os.chdir(cwd)
        assert code == 1


class TestDirectiveCarrier:
    """T-1199: `frob:*` directives and `frob.lock` acks move/repoint with
    a moved symbol."""

    def test_attached_waiver_moves_with_symbol(self, tmp_path):
        # frob:tests \
        # tests/test_refactor.py::TestDirectiveCarrier.test_attached_waiver_moves_with_\
        # symbol
        source = "# frob:waive ARCH101 reason=\"test\"\ndef greet():\n    return 'hi'\n"
        lines = source.splitlines()
        # `greet`'s own def line is line 2 (1-indexed); the waiver directly
        # above it should extend the move span back to line 1.
        assert extend_span_for_attached_directives(lines, 2) == 1

    def test_unrelated_comment_not_extended(self, tmp_path):
        # frob:tests \
        # tests/test_refactor.py::TestDirectiveCarrier.test_unrelated_comment_not_exten\
        # ded
        source = "# just a regular comment\ndef greet():\n    return 'hi'\n"
        lines = source.splitlines()
        assert extend_span_for_attached_directives(lines, 2) == 2

    def test_directive_target_elsewhere_rewritten(self, tmp_path):
        # frob:tests \
        # tests/test_refactor.py::TestDirectiveCarrier.test_directive_target_elsewhere_\
        # rewritten
        import os

        root = _repo(tmp_path)
        _write(root, "src/pkg/mod.py", "def greet():\n    return 'hi'\n")
        old_symref = "src/pkg/mod.py::greet"
        _write(
            root,
            "src/pkg/other.py",
            f"def use():\n    pass\n\n\n# frob:tests {old_symref}\ndef test_use():\n"
            "    use()\n",
        )
        cwd = os.getcwd()
        os.chdir(root)
        try:
            resolved = resolve_symbol(
                root, SymbolRef(module="pkg.mod", qualname="greet")
            ).danger_ok
            destination = SymbolRef(module="pkg.mod", qualname="hello")
            ops, unresolved = scan_directive_carriers(root, resolved, destination)
        finally:
            os.chdir(cwd)
        assert unresolved == []
        assert len(ops) == 1
        assert "src/pkg/mod.py::hello" in ops[0].new_text
        assert old_symref not in ops[0].new_text

    def test_lock_ack_carried_to_new_symref(self, tmp_path):
        # frob:tests \
        # tests/test_refactor.py::TestDirectiveCarrier.test_lock_ack_carried_to_new_sym\
        # ref
        import json
        import os

        root = _repo(tmp_path)
        _write(root, "src/pkg/mod.py", "def greet():\n    return 'hi'\n")
        old_symref = "src/pkg/mod.py::greet"
        lock_doc = {
            "version": 1,
            "entries": [{"ref": old_symref, "facet": "sig", "digest": "abc123"}],
        }
        _write(root, "frob.lock", json.dumps(lock_doc))
        cwd = os.getcwd()
        os.chdir(root)
        try:
            resolved = resolve_symbol(
                root, SymbolRef(module="pkg.mod", qualname="greet")
            ).danger_ok
            destination = SymbolRef(module="pkg.mod", qualname="hello")
            carried = carry_lock_acks(root, resolved, destination)
        finally:
            os.chdir(cwd)
        assert carried == 1
        new_lock = json.loads((root / "frob.lock").read_text(encoding="utf-8"))
        refs = [e["ref"] for e in new_lock["entries"]]
        assert "src/pkg/mod.py::hello" in refs
        assert old_symref not in refs

    def test_move_carries_attached_waiver_end_to_end(self, tmp_path):
        # frob:tests \
        # tests/test_refactor.py::TestDirectiveCarrier.test_move_carries_attached_waive\
        # r_end_to_end
        import os

        root = _repo(tmp_path)
        _write(
            root,
            "src/pkg/mod.py",
            "# frob:waive ARCH101 reason=\"test\"\ndef greet():\n    return 'hi'\n",
        )
        _commit_all(root, "initial")
        cwd = os.getcwd()
        os.chdir(root)
        try:
            plan = build_plan(
                root,
                RefactorKind.MOVE,
                SymbolRef(module="pkg.mod", qualname="greet"),
                SymbolRef(module="pkg.new", qualname="greet"),
            ).danger_ok
        finally:
            os.chdir(cwd)
        result = apply_plan(root, plan)
        assert result.is_ok
        new_text = (root / "src/pkg/new.py").read_text(encoding="utf-8")
        assert "frob:waive ARCH101" in new_text
        old_text = (root / "src/pkg/mod.py").read_text(encoding="utf-8")
        assert "frob:waive ARCH101" not in old_text


class TestRepointer:
    """T-1200: the three non-DSL reference kinds the directive carrier
    cannot reach -- PII012 allowlist, registry citations, ticket evidence."""

    def test_pii_allowlist_entry_rekeyed_on_move(self, tmp_path):
        # frob:tests \
        # tests/test_refactor.py::TestRepointer.test_pii_allowlist_entry_rekeyed_on_move
        root = _repo(tmp_path)
        _write(root, "src/pkg/mod.py", "def greet():\n    return 'hi'\n")
        _write(
            root,
            "src/frob/gates/_pii_structural/_keywords.py",
            "_TABLE = frozenset(\n"
            "    {\n"
            '        ("src/pkg/mod.py", "greet"),\n'
            "    }\n"
            ")\n",
        )
        resolved = resolve_symbol(
            root, SymbolRef(module="pkg.mod", qualname="greet")
        ).danger_ok
        destination = SymbolRef(module="pkg.new", qualname="greet")
        ops, unresolved = scan_pii_allowlist_carrier(root, resolved, destination)
        assert unresolved == []
        assert len(ops) == 1
        assert '("src/pkg/new.py", "greet")' in ops[0].new_text
        assert "src/pkg/mod.py" not in ops[0].new_text

    def test_registry_cross_ref_rewritten(self, tmp_path):
        # frob:tests \
        # tests/test_refactor.py::TestRepointer.test_registry_cross_ref_rewritten
        root = _repo(tmp_path)
        _write(root, "src/pkg/mod.py", "def greet():\n    return 'hi'\n")
        old_symref = "src/pkg/mod.py::greet"
        _write(
            root,
            "docs/design/registry/foo.yaml",
            f'    cross_refs: ["{old_symref}"]\n',
        )
        resolved = resolve_symbol(
            root, SymbolRef(module="pkg.mod", qualname="greet")
        ).danger_ok
        destination = SymbolRef(module="pkg.new", qualname="greet")
        ops, unresolved = scan_registry_citations(root, resolved, destination)
        assert unresolved == []
        assert len(ops) == 1
        assert "src/pkg/new.py::greet" in ops[0].new_text
        assert old_symref not in ops[0].new_text

    def test_ticket_evidence_symref_rewritten(self, tmp_path):
        # frob:tests \
        # tests/test_refactor.py::TestRepointer.test_ticket_evidence_symref_rewritten
        root = _repo(tmp_path)
        _write(root, "src/pkg/mod.py", "def greet():\n    return 'hi'\n")
        old_symref = "src/pkg/mod.py::greet"
        _write(root, "tickets.md", f"Evidence: {old_symref} passes.\n")
        _write(root, "tickets-archive.md", f"Evidence: {old_symref} passes.\n")
        resolved = resolve_symbol(
            root, SymbolRef(module="pkg.mod", qualname="greet")
        ).danger_ok
        destination = SymbolRef(module="pkg.new", qualname="greet")
        ops, unresolved = scan_evidence_citations(root, resolved, destination)
        assert unresolved == []
        assert len(ops) == 2
        touched = {op.file_path for op in ops}
        assert str(root / "tickets.md") in touched
        assert str(root / "tickets-archive.md") in touched
        for op in ops:
            assert "src/pkg/new.py::greet" in op.new_text
            assert old_symref not in op.new_text

    def test_no_matching_citation_yields_no_ops(self, tmp_path):
        # frob:tests \
        # tests/test_refactor.py::TestRepointer.test_no_matching_citation_yields_no_ops
        root = _repo(tmp_path)
        _write(root, "src/pkg/mod.py", "def greet():\n    return 'hi'\n")
        resolved = resolve_symbol(
            root, SymbolRef(module="pkg.mod", qualname="greet")
        ).danger_ok
        destination = SymbolRef(module="pkg.new", qualname="greet")
        ops, unresolved = scan_registry_citations(root, resolved, destination)
        assert ops == []
        assert unresolved == []
        ops, unresolved = scan_evidence_citations(root, resolved, destination)
        assert ops == []
        assert unresolved == []


class TestProseCarrier:
    """T-1267: docstring/comment prose, docs/** prose, and doc heading/
    anchor slug carriers -- the free-text reference kinds no structured
    (`frob:*` DSL, registry yaml, ticket evidence) carrier reaches."""

    def test_docstring_mention_elsewhere_rewritten(self, tmp_path):
        # frob:tests \
        # tests/test_refactor.py::TestProseCarrier.test_docstring_mention_elsewhere_rew\
        # ritten
        root = _repo(tmp_path)
        _write(root, "src/pkg/mod.py", "def greet():\n    return 'hi'\n")
        _write(
            root,
            "src/pkg/other.py",
            "def use():\n"
            '    """See `pkg.mod.greet` for the shared greeting logic."""\n'
            "    pass\n",
        )
        resolved = resolve_symbol(
            root, SymbolRef(module="pkg.mod", qualname="greet")
        ).danger_ok
        destination = SymbolRef(module="pkg.mod", qualname="hello")
        ops, unresolved = scan_python_prose_mentions(root, resolved, destination)
        assert unresolved == []
        assert len(ops) == 1
        assert "pkg.mod.hello" in ops[0].new_text
        assert "pkg.mod.greet" not in ops[0].new_text

    def test_directive_line_skipped_by_prose_scan(self, tmp_path):
        # frob:tests \
        # tests/test_refactor.py::TestProseCarrier.test_directive_line_skipped_by_prose\
        # _scan
        root = _repo(tmp_path)
        _write(root, "src/pkg/mod.py", "def greet():\n    return 'hi'\n")
        old_symref = "src/pkg/mod.py::greet"
        _write(
            root,
            "src/pkg/other.py",
            f"def use():\n    pass\n\n\n# frob:tests {old_symref}\ndef test_use():\n"
            "    use()\n",
        )
        resolved = resolve_symbol(
            root, SymbolRef(module="pkg.mod", qualname="greet")
        ).danger_ok
        destination = SymbolRef(module="pkg.mod", qualname="hello")
        ops, unresolved = scan_python_prose_mentions(root, resolved, destination)
        # Owned by scan_directive_carriers instead -- the prose scan must
        # not double-rewrite the same directive comment.
        assert ops == []
        assert unresolved == []

    def test_docs_prose_and_code_block_rewritten(self, tmp_path):
        # frob:tests \
        # tests/test_refactor.py::TestProseCarrier.test_docs_prose_and_code_block_rewri\
        # tten
        root = _repo(tmp_path)
        _write(root, "src/pkg/mod.py", "def greet():\n    return 'hi'\n")
        _write(
            root,
            "docs/guide.md",
            "Call `pkg.mod.greet` to say hello.\n\n"
            "```python\nfrom pkg.mod import greet\n```\n",
        )
        resolved = resolve_symbol(
            root, SymbolRef(module="pkg.mod", qualname="greet")
        ).danger_ok
        destination = SymbolRef(module="pkg.mod", qualname="hello")
        ops, unresolved = scan_docs_prose_mentions(root, resolved, destination)
        assert unresolved == []
        assert len(ops) == 1
        assert "pkg.mod.hello" in ops[0].new_text
        assert "pkg.mod.greet" not in ops[0].new_text

    def test_heading_and_anchor_rewritten_together(self, tmp_path):
        # frob:tests \
        # tests/test_refactor.py::TestProseCarrier.test_heading_and_anchor_rewritten_to\
        # gether
        root = _repo(tmp_path)
        _write(root, "src/pkg/mod.py", "def greet():\n    return 'hi'\n")
        _write(root, "docs/guide.md", "# greet\n\nSome text.\n")
        _write(
            root,
            "src/pkg/other.py",
            "# frob:doc docs/guide.md#greet\ndef use():\n    pass\n",
        )
        resolved = resolve_symbol(
            root, SymbolRef(module="pkg.mod", qualname="greet")
        ).danger_ok
        destination = SymbolRef(module="pkg.mod", qualname="hello")
        ops, unresolved = scan_doc_anchor_carriers(root, resolved, destination)
        assert unresolved == []
        heading_ops = [op for op in ops if str(root / "docs/guide.md") == op.file_path]
        assert any("# hello" in op.new_text for op in heading_ops)
        anchor_ops = [op for op in ops if str(root / "src/pkg/other.py") == op.file_path]
        assert any("docs/guide.md#hello" in op.new_text for op in anchor_ops)

    def test_unrelated_heading_not_touched(self, tmp_path):
        # frob:tests \
        # tests/test_refactor.py::TestProseCarrier.test_unrelated_heading_not_touched
        root = _repo(tmp_path)
        _write(root, "src/pkg/mod.py", "def greet():\n    return 'hi'\n")
        _write(root, "docs/guide.md", "# unrelated topic\n\nSome text.\n")
        resolved = resolve_symbol(
            root, SymbolRef(module="pkg.mod", qualname="greet")
        ).danger_ok
        destination = SymbolRef(module="pkg.mod", qualname="hello")
        ops, unresolved = scan_doc_anchor_carriers(root, resolved, destination)
        assert ops == []
        assert unresolved == []

    def test_unreadable_doc_file_disclosed_in_unresolved(self, tmp_path):
        # frob:tests \
        # tests/test_refactor.py::TestProseCarrier.test_unreadable_doc_file_disclosed_i\
        # n_unresolved
        import os
        import stat

        root = _repo(tmp_path)
        _write(root, "src/pkg/mod.py", "def greet():\n    return 'hi'\n")
        bad_doc = _write(root, "docs/guide.md", "Call `pkg.mod.greet` please.\n")
        bad_doc.chmod(0)
        resolved = resolve_symbol(
            root, SymbolRef(module="pkg.mod", qualname="greet")
        ).danger_ok
        destination = SymbolRef(module="pkg.mod", qualname="hello")
        try:
            ops, unresolved = scan_docs_prose_mentions(root, resolved, destination)
        finally:
            bad_doc.chmod(stat.S_IRUSR | stat.S_IWUSR)
        if os.name == "nt" or os.geteuid() == 0:
            # chmod(0) does not deny a root/administrator reader -- the
            # unresolved-disclosure path is unreachable in that
            # environment, not a test failure.
            return
        assert ops == []
        assert len(unresolved) == 1
        assert "review by hand" in unresolved[0]


class TestAliasPolicy:
    """T-1202: the alias-conflict policy layer for a DESTINATION-namespace
    collision (two symbols landing with the same name in the same
    module) -- distinct from the import-site name collision `scan_
    references` already resolves on its own."""

    def test_rename_dest_renames_existing_symbol_and_its_callers(self, tmp_path):
        # frob:tests \
        # tests/test_refactor.py::TestAliasPolicy.test_rename_dest_renames_existing_sym\
        # bol_and_its_callers
        root = _repo(tmp_path)
        _write(
            root,
            "src/pkg/mod.py",
            "def hello():\n    return 'yo'\n",
        )
        _write(
            root,
            "src/pkg/caller.py",
            "from pkg.mod import hello\n\ndef use():\n    return hello()\n",
        )
        existing = resolve_symbol(
            root, SymbolRef(module="pkg.mod", qualname="hello")
        ).danger_ok
        own_op, caller_ops, alias = resolve_rename_dest_collision(
            root, existing, "hello"
        )
        assert "def hello_existing" in own_op.new_text
        assert alias.original_name == "hello"
        assert alias.alias_name == "hello_existing"
        assert len(caller_ops) == 2
        assert all("hello_existing" in op.new_text for op in caller_ops)

    def test_build_plan_error_policy_still_refuses(self, tmp_path):
        # frob:tests \
        # tests/test_refactor.py::TestAliasPolicy.test_build_plan_error_policy_still_re\
        # fuses
        root = _repo(tmp_path)
        _write(
            root,
            "src/pkg/mod.py",
            "def greet():\n    return 'hi'\n\n\ndef hello():\n    return 'yo'\n",
        )
        result = build_plan(
            root,
            RefactorKind.RENAME,
            SymbolRef(module="pkg.mod", qualname="greet"),
            SymbolRef(module="pkg.mod", qualname="hello"),
            alias_conflict="error",
        )
        assert result.is_err
        assert result.danger_err == RefactorError.DestinationCollision

    def test_build_plan_rename_dest_policy_proceeds(self, tmp_path):
        # frob:tests \
        # tests/test_refactor.py::TestAliasPolicy.test_build_plan_rename_dest_policy_pr\
        # oceeds
        root = _repo(tmp_path)
        _write(
            root,
            "src/pkg/mod.py",
            "def greet():\n    return 'hi'\n\n\ndef hello():\n    return 'yo'\n",
        )
        result = build_plan(
            root,
            RefactorKind.RENAME,
            SymbolRef(module="pkg.mod", qualname="greet"),
            SymbolRef(module="pkg.mod", qualname="hello"),
            alias_conflict="rename-dest",
        )
        assert result.is_ok
        plan = result.danger_ok
        assert len(plan.aliases) == 1
        assert plan.aliases[0].original_name == "hello"
        assert plan.aliases[0].alias_name == "hello_existing"
        assert any("def hello_existing" in op.new_text for op in plan.reference_ops)

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
    resolve_symbol,
    run_refactor,
    scan_references,
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

    def test_apply_failed_on_write_error_reports_apply_failed(self, tmp_path, monkeypatch):
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
                subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")
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

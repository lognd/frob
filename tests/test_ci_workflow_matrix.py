"""T-2917: CI ran ubuntu-latest only, so no platform regression (Windows or
macOS) could ever be detected -- locks that the `build` job's matrix
includes windows-latest and macos-latest alongside ubuntu-latest.
"""

from pathlib import Path

import yaml


def _load_ci_workflow() -> dict:
    """Parse .github/workflows/ci.yml (frob:tests target) into a dict."""
    text = (
        Path(__file__).resolve().parents[1] / ".github" / "workflows" / "ci.yml"
    ).read_text(encoding="utf-8")
    return yaml.safe_load(text)


class TestCiBuildMatrixCoversAllThreePlatforms:
    """T-2917: a single-OS CI matrix cannot detect a platform regression."""

    def test_build_job_declares_a_matrix_strategy(self) -> None:
        # frob:tests .github/workflows/ci.yml
        workflow = _load_ci_workflow()
        build_job = workflow["jobs"]["build"]
        assert "strategy" in build_job, (
            "build job has no matrix strategy -- it can only ever run on "
            "one OS, so a Windows- or macOS-only regression is undetectable"
        )
        assert build_job["runs-on"] == "${{ matrix.os }}"

    def test_build_matrix_includes_windows_and_macos(self) -> None:
        # frob:tests .github/workflows/ci.yml
        workflow = _load_ci_workflow()
        matrix_os = workflow["jobs"]["build"]["strategy"]["matrix"]["os"]
        assert "ubuntu-latest" in matrix_os
        assert "windows-latest" in matrix_os
        assert "macos-latest" in matrix_os

    def test_build_matrix_is_fail_fast_false(self) -> None:
        """A single early platform failure must not hide the others' results."""
        # frob:tests .github/workflows/ci.yml
        workflow = _load_ci_workflow()
        strategy = workflow["jobs"]["build"]["strategy"]
        assert strategy.get("fail-fast") is False


class TestWindowsDiagStepResolvesFrobCheckoutEnv:
    """T-3597: the "Diagnose frob check hang on windows (T-3589)" step
    `Push-Location`s into a throwaway fixture directory before invoking
    `uv run python <diag script>` -- with no `--project`, `uv` resolves
    the venv/dependencies from the CURRENT DIRECTORY, which is the
    fixture (no pyproject.toml, no `frob` installed), not the frob
    checkout. The diag process dies with `ModuleNotFoundError: No module
    named 'frob'` before the faulthandler watchdog it exists to arm ever
    runs, silently voiding the whole Windows-hang diagnostic (run
    33412543005). `--project $env:GITHUB_WORKSPACE` pins dependency
    resolution to the checkout while leaving cwd (and so `frob check`'s
    scan target) at the fixture."""

    def test_windows_diag_step_uv_run_pins_project_to_checkout(self) -> None:
        # frob:tests .github/workflows/ci.yml
        text = (
            Path(__file__).resolve().parents[1] / ".github" / "workflows" / "ci.yml"
        ).read_text(encoding="utf-8")
        idx = text.find("Diagnose frob check hang on windows")
        assert idx != -1, "windows diag step (T-3589) was removed/renamed"
        step_text = text[idx : idx + 8000]
        assert '"--project", "$env:GITHUB_WORKSPACE",' in step_text, (
            "the diag step's `uv run python <script>` has no --project "
            "pin -- uv resolves the venv from cwd, which has no "
            "pyproject.toml/frob installed unless pinned, so the diag "
            "process dies with ModuleNotFoundError before its "
            "faulthandler watchdog ever arms (T-3597). T-3624 round 12 "
            "moved the invocation to Start-Process -ArgumentList, so "
            "each argument (including --project's value) is now its own "
            "array element rather than one shell-quoted string."
        )

    def test_windows_diag_step_still_scans_the_fixture_not_the_repo(self) -> None:
        """The --project pin must resolve DEPENDENCIES only -- cwd (and so
        frob check's scan target, since the diag script's own sys.argv
        carries no explicit path) must stay at the fixture, not flip to
        scanning this whole repo."""
        # frob:tests .github/workflows/ci.yml
        step = _windows_diag_step()
        assert "-WorkingDirectory $fixture" in step["run"], (
            "expected the diag child's Start-Process invocation to pass "
            "-WorkingDirectory $fixture -- --project must pin DEPENDENCY "
            "resolution only, not also move frob check's scan target off "
            "the fixture and onto the real repo"
        )


class TestCoverageStepUsesFrobNotMake:
    """T-3077 (T-1382 epic: decouple frob from the Makefile): the T-1366
    "coverage stamp + delta baseline" step used to shell out to `make
    coverage`, which depends on a `make` binary that windows-latest never
    installs -- so the one job that would prove the make-free path works
    never actually exercised it. The step must call `uv run frob coverage
    --full` directly instead."""

    # frob:tests .github/workflows/ci.yml
    def test_coverage_step_does_not_shell_to_make(self) -> None:
        """No CI step may spell `make coverage`/`make <target>` -- T-1382's
        whole point is that workflows never depend on a Makefile."""
        workflow = _load_ci_workflow()
        raw = yaml.safe_dump(workflow)
        assert "make coverage" not in raw, (
            "a CI step still shells to `make coverage`, which depends on a "
            "`make` binary no step installs on windows-latest (T-3077)"
        )

    # frob:tests .github/workflows/ci.yml
    def test_coverage_step_calls_frob_coverage_full(self) -> None:
        """The T-1366 coverage-stamp step's `run:` block must invoke the
        frob subcommand `make coverage` used to alias, not the make target
        itself."""
        workflow = _load_ci_workflow()
        steps = workflow["jobs"]["build"]["steps"]
        coverage_step = next(
            step for step in steps if "coverage stamp" in step.get("name", "")
        )
        assert "uv run frob coverage --full" in coverage_step["run"], (
            "the T-1366 coverage-stamp step must call `uv run frob "
            "coverage --full` directly (T-3077)"
        )


def _windows_diag_step() -> dict:
    """The "Diagnose frob check hang on windows (T-3589)" step's own
    dict from the parsed workflow -- shared by every test below."""
    workflow = _load_ci_workflow()
    steps = workflow["jobs"]["build"]["steps"]
    return next(
        step
        for step in steps
        if "Diagnose frob check hang on windows" in step.get("name", "")
    )


class TestWindowsDiagStepFixtureIsAClassifiableProject:
    """T-3604 (T-3589 round 7): run 33439890956 measured `frob check`
    COMPLETING in 547ms on the diag fixture and still aborting the
    windows job, because a bare src/demo/__init__.py with no
    pyproject.toml makes project-type detection legitimately yield
    'unknown' (CHECK001) -- a real gate ERROR, not a hang. The fixture
    must be a classifiable Python project."""

    # frob:tests .github/workflows/ci.yml
    def test_fixture_gets_a_pyproject_toml(self) -> None:
        step = _windows_diag_step()
        assert "pyproject.toml" in step["run"], (
            "the diag fixture has no pyproject.toml -- frob's project-"
            "type detection yields 'unknown' (CHECK001) and the step "
            "fast-fails before ever exercising a real language stage "
            "(T-3604, run 33439890956)"
        )


class TestWindowsDiagStepDoesNotGateTheJob:
    """T-3609 (T-3604 round 8 correction): a step-level continue-on-
    error is redundant AND wrong -- T-3604's own script-side elapsed-
    time discriminator already exits 0 for every no-hang outcome (a
    clean run or an ordinary gate finding like CHECK001), so the only
    nonzero left IS a genuine watchdog-fired hang, which SHOULD fail
    the (job-level-advisory) windows job loudly. A step-level continue-
    on-error also tripped tests/unit/test_release_workflow_gate.py::
    TestCiWindowsLegAdvisoryOnly::
    test_no_step_level_continue_on_error_smuggled_onto_other_legs on
    BOTH posix legs (run 33451274911) -- that guard is correct and
    stays; this diag step must not carry step-level continue-on-error
    at all."""

    # frob:tests .github/workflows/ci.yml
    def test_step_has_no_continue_on_error(self) -> None:
        step = _windows_diag_step()
        assert "continue-on-error" not in step, (
            "the windows diag step must NOT set its own continue-on-"
            "error -- T-3604's script-side elapsed-time discriminator "
            "already exits 0 for every no-hang outcome, so a step-level "
            "continue-on-error is both redundant and trips the repo's "
            "windows-only advisory-boundary guard test (T-3609)"
        )

    # frob:tests .github/workflows/ci.yml
    def test_diag_invocation_uses_start_process_not_a_native_pwsh_command(
        self,
    ) -> None:
        """T-3609's original concern (a native pwsh command's stderr
        redirect turning under Stop into a terminating NativeCommand
        Error) applies to whatever pwsh invokes NATIVELY as a bare
        command. T-3624 round 10's `cmd /c` wrapper was ITSELF invoked as
        a native pwsh command and died silently at that exact boundary
        (round 11, run 33480116817) -- round 12 replaces both the `uv`
        invocation and the `cmd /c` wrapper around it with `Start-
        Process`, which pwsh never treats as a native command at all, so
        neither stream-redirect promotion nor a silent kill at the
        invocation line can recur."""
        step = _windows_diag_step()
        assert "Start-Process" in step["run"]
        code_lines = [
            line
            for line in step["run"].splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]
        assert not any("cmd /c" in line for line in code_lines), (
            "the cmd /c wrapper (T-3624 round 10) died silently at its "
            "own invocation line (round 11, run 33480116817) -- round 12 "
            "removes it entirely in favor of Start-Process (a historical "
            "mention of 'cmd /c' in an explanatory comment is fine, only "
            "actual CODE using it is not)"
        )

    def test_diag_invocation_redirects_uv_streams_to_files(self) -> None:
        """The uv/python invocation, run through Start-Process rather
        than a native pwsh/cmd command, still captures both streams to
        files so breadcrumb output survives even a killed/terminated
        child (T-3624 round 12)."""
        step = _windows_diag_step()
        assert "-RedirectStandardOutput $diagOut" in step["run"]
        assert "-RedirectStandardError $diagErr" in step["run"]

    # frob:tests .github/workflows/ci.yml
    def test_diag_invocation_is_wrapped_in_try_catch(self) -> None:
        """T-3624 round 12: the whole Start-Process/Wait-Process region is
        wrapped in try/catch printing 'invoke threw: $_' -- round 11's
        failure mode was a silent kill with zero diagnostic output, so no
        exception path through this invocation may ever go unreported
        again."""
        run_text = _windows_diag_step()["run"]
        assert "invoke threw: $_" in run_text, (
            "expected the diag step's Start-Process invocation to be "
            "wrapped in a try/catch that prints 'invoke threw: $_' on "
            "any exception -- otherwise a failure mode this step has not "
            "yet seen could die as silently as round 11's cmd /c did"
        )

    # frob:tests .github/workflows/ci.yml
    def test_diag_invocation_output_capture_is_unconditional(self) -> None:
        """T-3624 round 12: Get-Content of both redirect files and the
        exit-code print must run in a `finally` block, not only on the
        happy path -- round 11 died with NO output at all because
        everything after the invocation line was unreachable once it
        threw."""
        run_text = _windows_diag_step()["run"]
        finally_idx = run_text.find("} finally {")
        assert finally_idx != -1, (
            "expected a `finally` block around the diag invocation's "
            "output-capture/exit-code reporting"
        )
        finally_block = run_text[finally_idx:]
        assert "Get-Content $diagOut" in finally_block
        assert "Get-Content $diagErr" in finally_block
        assert "frob check diag exit code:" in finally_block

    # frob:tests .github/workflows/ci.yml
    def test_diag_step_sets_error_action_preference_continue_first(self) -> None:
        """T-3619 (round 9): pwsh steps default to
        $ErrorActionPreference='Stop', which promotes a native command's
        FIRST stderr line into a terminating error -- this is the actual
        mechanism that killed rounds 7 (uv resolver chatter) and 8/9
        (frob's own gitio WARNING), independent of the T-3609 stderr-
        redirect fix, since Stop kills the step on interleaved stderr
        too. The step script must flip to Continue before any command
        that can write to stderr runs."""
        step = _windows_diag_step()
        code_lines = [
            line
            for line in step["run"].splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]
        assert code_lines, "diag step has no run lines"
        assert (
            code_lines[0].strip().startswith("$ErrorActionPreference = 'Continue'")
        ), (
            "the diag step's first non-blank run line must set "
            "$ErrorActionPreference = 'Continue' -- otherwise the "
            "default Stop preference turns the first stderr line any "
            "native command prints (uv chatter, frob's gitio warnings) "
            "into a terminating NativeCommandError before the script's "
            "own elapsed-time/exit-code handling ever runs (T-3619)"
        )

    # frob:tests .github/workflows/ci.yml
    def test_diag_fixture_repo_has_an_initial_commit(self) -> None:
        """T-3619 (round 9): the fixture repo is `git init` with zero
        commits, so frob's gitio helper (`git rev-parse --abbrev-ref
        HEAD`) fails rc=128 with "ambiguous argument 'HEAD'" and frob
        aborts with "frob: interrupted" before the diagnostic's own
        watchdog/exit-code logic ever gets a signal to read. The step
        must create one empty commit right after `git init`."""
        step = _windows_diag_step()
        run_lines = step["run"].splitlines()
        init_idx = next(i for i, line in enumerate(run_lines) if "git init" in line)
        following = "\n".join(run_lines[init_idx + 1 : init_idx + 4])
        assert "commit" in following and "--allow-empty" in following, (
            "expected a `git commit --allow-empty` shortly after `git "
            "init` in the diag step -- a commitless fixture repo makes "
            "frob's own git rev-parse HEAD fail rc=128 and frob abort "
            "with 'frob: interrupted' (T-3619)"
        )

    # frob:tests .github/workflows/ci.yml
    def test_diag_python_prints_liveness_marker_before_anything_else(self) -> None:
        """T-3624 round 10: the diag python script's FIRST statement
        prints a liveness marker (flushed) before even `import
        faulthandler` -- if diag.out ever comes back empty, that proves
        the interpreter itself never ran a single statement, ruling out
        the whole python process as the kill point."""
        step = _windows_diag_step()
        code_line_idx = next(
            i
            for i, line in enumerate(step["run"].splitlines())
            if "$codeLines = @(" in line
        )
        first_code_line = step["run"].splitlines()[code_line_idx + 1]
        assert "diag-python-alive" in first_code_line, (
            "the diag script's first $codeLines entry must print a "
            "liveness marker -- otherwise an empty diag.out cannot "
            "distinguish 'python never started' from 'python started and "
            "then died silently'"
        )

    # frob:tests .github/workflows/ci.yml
    def test_diag_python_wraps_main_call_in_baseexception_handler(self) -> None:
        """T-3624 round 10: main() is called inside try/except
        BaseException that prints the exception's repr and a full
        traceback before re-raising -- so whatever "frob: interrupted"
        actually is gets a stack instead of dying with no diagnostic
        information at all."""
        run_text = _windows_diag_step()["run"]
        assert "except BaseException as exc:" in run_text
        assert "traceback.print_exc()" in run_text

    # frob:tests .github/workflows/ci.yml
    def test_diag_step_has_breadcrumbs_around_every_major_block(self) -> None:
        """T-3624 round 10: Write-Host markers before/after fixture
        setup, diag-file writing, and the child invocation -- whichever
        marker is the LAST to print in a real run localizes the kill
        point, since the step previously died with zero output of its
        own at all."""
        run_text = _windows_diag_step()["run"]
        for marker in (
            "fixture dir + pyproject.toml written",
            "fixture git init + initial commit done",
            "diag python file written",
            "about to invoke uv via Start-Process",
            "Start-Process invocation returned",
        ):
            assert marker in run_text, f"expected a breadcrumb containing {marker!r}"

    # frob:tests .github/workflows/ci.yml
    def test_test_step_is_untouched_and_still_windows_only(self) -> None:
        """Neither T-3604 nor T-3609 may touch the Test step itself --
        only the diagnostic step ahead of it."""
        workflow = _load_ci_workflow()
        steps = workflow["jobs"]["build"]["steps"]
        test_step = next(
            step for step in steps if step.get("name", "").startswith("Test (windows")
        )
        assert test_step["if"] == "matrix.os == 'windows-latest'"
        assert "continue-on-error" not in test_step, (
            "T-3604 must not add continue-on-error to the Test step "
            "itself -- only to the diagnostic step ahead of it"
        )


class TestWindowsDiagStepRunsUnbudgeted:
    """T-3604: a `--budget 180` diag run defers gates-security/lint/
    static to a later, unmeasured pass -- a real hang living in one of
    those deferred stage groups would never reach the fixture at all.
    The diag invocation must run unbudgeted so all 5 stage groups are
    exercised against the fixture."""

    # frob:tests .github/workflows/ci.yml
    def test_diag_invocation_has_no_budget_flag(self) -> None:
        step = _windows_diag_step()
        assert "--budget" not in step["run"], (
            "the diag invocation still passes --budget, which defers "
            "gates-security/lint/static -- a hang in one of those stage "
            "groups would never reach this diagnostic (T-3604)"
        )


def _code_lines_array_lines() -> list[str]:
    """The raw lines of the diag step's `$codeLines = @( ... )` pwsh
    array literal, from the line after `@(` up to (excluding) the
    closing `)` line -- shared by the syntactic-balance tests below."""
    run_lines = _windows_diag_step()["run"].splitlines()
    start = next(i for i, line in enumerate(run_lines) if "$codeLines = @(" in line)
    end = next(
        i for i in range(start + 1, len(run_lines)) if run_lines[i].strip() == ")"
    )
    return run_lines[start + 1 : end]


def _strip_inline_comment(line: str) -> str:
    """Strip a trailing pwsh `# ...` comment from an element line, if the
    `#` appears AFTER the last quote character (i.e. genuinely outside
    the string literal) -- a naive `line.split('#')[0]` would wrongly
    truncate a quoted string that happens to contain a literal `#`."""
    last_quote = max(line.rfind("'"), line.rfind('"'))
    hash_idx = line.find("#", last_quote + 1) if last_quote != -1 else line.find("#")
    return line if hash_idx == -1 else line[:hash_idx]


class TestCodeLinesArrayLiteralIsSyntacticallyBalanced:
    """T-3633 (round 11): pwsh is not available on this (WSL) CI host, so
    a ParserError in the $codeLines array literal can only ever be
    caught by a human reading a failed job log after the fact. This
    statically re-derives pwsh's own array-literal balance rule so a
    future round's edit gets caught before it ever reaches a runner:
    round 10 shipped exactly this defect -- a trailing comma after the
    last element ("    raise",) right before the closing `)` -- and
    NONE of that round's instrumentation ever ran (run 33472403980,
    ParserError at ~0.5s, before even the liveness-marker print)."""

    # frob:tests .github/workflows/ci.yml
    def test_last_array_element_has_no_trailing_comma(self) -> None:
        """pwsh's `@()` array grammar treats a bare trailing `,` as an
        operator expecting a following expression -- a comma right
        before the closing `)` is a hard ParserError ("Missing
        expression after ','"), unlike Python/JS where it is tolerated.
        The LAST non-blank, non-comment line inside the array must NOT
        end with a comma once any trailing inline `# ...` comment is
        stripped."""
        content_lines = [
            line
            for line in _code_lines_array_lines()
            if line.strip() and not line.strip().startswith("#")
        ]
        assert content_lines, "expected at least one element in $codeLines"
        last = _strip_inline_comment(content_lines[-1]).rstrip()
        assert not last.endswith(","), (
            f"the last $codeLines element {last!r} ends with a trailing "
            "comma -- pwsh's array grammar parses that as 'expecting "
            "another expression', a hard ParserError right before the "
            "closing ')' (T-3633, exactly what run 33472403980 hit)"
        )

    # frob:tests .github/workflows/ci.yml
    def test_every_non_last_element_line_ends_with_a_comma(self) -> None:
        """Every element EXCEPT the last must end with a comma (ignoring
        any trailing inline `# ...` comment) -- a missing comma between
        two adjacent element strings would make pwsh parse them as one
        juxtaposed expression instead of two separate array entries,
        silently corrupting the emitted python source instead of raising
        a ParserError."""
        content_lines = [
            line
            for line in _code_lines_array_lines()
            if line.strip() and not line.strip().startswith("#")
        ]
        for line in content_lines[:-1]:
            stripped = _strip_inline_comment(line).rstrip()
            assert stripped.endswith(","), (
                f"$codeLines element {stripped!r} does not end with a "
                "comma but is not the last element -- pwsh would parse "
                "it and the next element as one juxtaposed expression "
                "instead of two separate array entries"
            )

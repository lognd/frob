"""Tests for frob.gates._secrets -- SEC001/SEC002/SEC003 (docs/modules/gates.md).

Fixture tokens below are all realistic-SHAPED but pattern-invalid or
explicitly fake-marked (T-0157's self-match lesson, T-0151 precedent): every
literal string in this file that looks like a credential is either (a) too
short/wrong-charset to match its provider's regex, (b) built from an
`XXXX`/`****` placeholder run, or (c) annotated with `frob:secret-fake` on
the line above. `TestGateIsGreenOnItself` locks that this file (and the
whole repo) stays clean under the real gate.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from frob.gates._models import Severity
from frob.gates._secrets import _PATTERNS, ALL_PROVIDERS, redact, secrets_gate


def _git(root: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
    )


def _init_repo(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "test@example.com")
    _git(root, "config", "user.name", "Test")
    _git(root, "checkout", "-q", "-b", "main")


def _commit(root: Path, message: str = "commit") -> None:
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", message)


class TestRedact:
    def test_never_returns_the_token(self) -> None:
        # frob:tests src/frob/gates/_secrets.py::redact
        # frob:secret-fake -- fixture literal for the redact() unit test
        token = "sk_live_abcdefghijklmnopqrstuvwxyz"
        out = redact(token, "sk_live_")
        assert token not in out
        assert out == f"sk_live_... ({len(token)} chars)"


class TestFindsTokens:
    def test_stripe_live_key_sec003(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_secrets.py::secrets_gate
        repo = tmp_path / "repo"
        _init_repo(repo)
        # Runtime-constructed (prefix and filler concatenated, never a
        # contiguous literal in THIS file's own source) so this test file
        # never self-matches; written unmarked into the throwaway tmp_path
        # repo below, where it is exactly the shape SEC003 must catch.
        (repo / "config.py").write_text('STRIPE_KEY = "sk_live_' + "a" * 24 + '"\n')
        _commit(repo)

        violations = secrets_gate(repo)
        sec003 = [v for v in violations if v.rule == "SEC003"]
        assert len(sec003) == 1
        assert "sk_live_" in sec003[0].message
        assert "a" * 24 not in sec003[0].message
        assert sec003[0].severity == Severity.ERROR

    def test_pem_private_key_header_flagged_sec003(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        _init_repo(repo)
        pem_fixture = (
            # frob:secret-fake -- fixture PEM header for the SEC003 pem test
            "-----BEGIN RSA PRIVATE KEY-----\nMIIfakebodyxxxx\n-----END RSA PRIVATE KEY-----\n"
        )
        (repo / "id_rsa").write_text(pem_fixture)
        _commit(repo)

        violations = secrets_gate(repo)
        sec003 = [v for v in violations if v.rule == "SEC003"]
        assert len(sec003) == 1

    def test_anthropic_key_flagged_sec001(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        _init_repo(repo)
        (repo / "notes.txt").write_text("sk-ant-" + "b" * 30 + "\n")
        _commit(repo)

        violations = secrets_gate(repo)
        assert any(v.rule == "SEC001" for v in violations)

    def test_sec003_waiver_is_inert(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/__init__.py::_match_waiver
        # SEC003 is unwaivable BY CONSTRUCTION (frob.gates._UNWAIVABLE_RULES),
        # not merely because nobody has tried to waive it. TEST008 already
        # locks the mechanism generically (test_gates.py::
        # test_test008_cannot_be_waived); this is SEC003's own dedicated
        # lock so a future refactor of _UNWAIVABLE_RULES cannot silently
        # drop SEC003 (live Stripe / PEM keys) without a test noticing.
        from frob.gates import _apply_waivers
        from frob.graph import build_graph

        repo = tmp_path / "repo"
        _init_repo(repo)
        # Runtime-constructed, same discipline as test_stripe_live_key_sec003
        # above: never a contiguous literal in this file's own source, so
        # TestGateIsGreenOnItself's self-scan of this file stays clean.
        (repo / "config.py").write_text(
            '# frob:waive SEC003 reason="pretend this is fine"\n'
            'STRIPE_KEY = "sk_live_' + "a" * 24 + '"\n'
        )
        _commit(repo)

        violations = secrets_gate(repo)
        sec003 = [v for v in violations if v.rule == "SEC003"]
        assert len(sec003) == 1

        cache = repo / ".frob" / "cache.db"
        snap = build_graph(repo, cache).danger_ok
        kept, waived = _apply_waivers(tuple(violations), snap)
        assert any(v.rule == "SEC003" for v in kept)
        assert not any(v.rule == "SEC003" for v in waived)

    def test_generic_live_key_adjacent_to_other_content_sec001(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_secrets.py::secrets_gate
        # T-0219: a hyphenated `sk-live-...` token immediately abutted by
        # other characters (quote + trailing prose, no whitespace boundary)
        # was silently missed pre-fix -- `openai-legacy`'s `sk-[A-Za-z0-9]{
        # 20,}` breaks at the first hyphen in "live-", so no pattern in the
        # table ever claimed the span. Runtime-constructed (never a
        # contiguous literal in this file's own source), same discipline as
        # `test_stripe_live_key_sec003` above.
        repo = tmp_path / "repo"
        _init_repo(repo)
        token = "sk-live-" + "d" * 24
        (repo / "config.py").write_text(f'X = "{token}" # trailing note\n')
        _commit(repo)

        violations = secrets_gate(repo)
        matches = [v for v in violations if "generic-live-key" in v.message]
        assert len(matches) == 1
        assert matches[0].rule == "SEC001"
        assert "d" * 24 not in matches[0].message

    def test_stripe_test_key_is_low_severity_warn(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        _init_repo(repo)
        (repo / "notes.txt").write_text("sk_test_" + "c" * 20 + "\n")
        _commit(repo)

        violations = secrets_gate(repo)
        matches = [v for v in violations if "stripe-secret-test" in v.message]
        assert len(matches) == 1
        assert matches[0].severity == Severity.WARN


class TestFakeMarking:
    def test_placeholder_xxxx_tail_is_not_flagged(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_secrets.py::secrets_gate
        repo = tmp_path / "repo"
        _init_repo(repo)
        (repo / "notes.txt").write_text("sk-ant-" + "X" * 30 + "\n")
        _commit(repo)

        violations = secrets_gate(repo)
        assert violations == ()

    def test_literal_fake_word_in_token_is_not_flagged(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        _init_repo(repo)
        (repo / "notes.txt").write_text("sk-ant-fake" + "d" * 25 + "\n")
        _commit(repo)

        violations = secrets_gate(repo)
        assert violations == ()

    def test_fake_marker_same_line(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        _init_repo(repo)
        (repo / "notes.py").write_text(
            'KEY = "sk-ant-' + "e" * 30 + '"  # frob:secret-fake\n'
        )
        _commit(repo)

        violations = secrets_gate(repo)
        assert violations == ()

    def test_frob_secret_fake_marker_on_line_above(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        _init_repo(repo)
        (repo / "notes.py").write_text(
            "# frob:secret-fake\n" + 'KEY = "sk-ant-' + "f" * 30 + '"\n'
        )
        _commit(repo)

        violations = secrets_gate(repo)
        assert violations == ()

    def test_placeholder_phrase_your_dash_here_is_not_flagged(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_secrets.py::secrets_gate
        # T-0219: a doc-example token like `xoxb-your-slack-token-here`
        # reads as an obvious template to a human but contains none of the
        # single-word `_PLACEHOLDER_WORDS` (fake/changeme/example/
        # placeholder) -- pre-fix, this fired a false-positive SEC001.
        repo = tmp_path / "repo"
        _init_repo(repo)
        (repo / "README.md").write_text("SLACK_TOKEN=xoxb-your-slack-token-here\n")
        _commit(repo)

        violations = secrets_gate(repo)
        assert violations == ()

    def test_placeholder_phrase_insert_dash_is_not_flagged(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_secrets.py::secrets_gate
        # Same T-0219 phrase-recognition fix, `insert-` variant.
        repo = tmp_path / "repo"
        _init_repo(repo)
        (repo / "README.md").write_text("SLACK_TOKEN=xoxb-insert-your-real-token\n")
        _commit(repo)

        violations = secrets_gate(repo)
        assert violations == ()

    def test_placeholder_phrase_does_not_suppress_real_looking_token(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_secrets.py::secrets_gate
        # Regression guard: the new phrase heuristic must stay scoped to
        # `-here`/`your-`/`insert-` fragments -- a real-shaped slack token
        # with none of those fragments must still fire (T-0157's original
        # "the miss matters more than any false positive" posture).
        repo = tmp_path / "repo"
        _init_repo(repo)
        # Runtime-constructed (never a contiguous literal in this file's own
        # source), same discipline as `test_stripe_live_key_sec003` above.
        token = "xoxb-" + "".join(str(n % 10) for n in range(20))
        (repo / "notes.txt").write_text(token + "\n")
        _commit(repo)

        violations = secrets_gate(repo)
        assert len(violations) == 1
        assert violations[0].rule == "SEC001"


class TestTrackedEnvFile:
    def test_env_file_sec002(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_secrets.py::secrets_gate
        repo = tmp_path / "repo"
        _init_repo(repo)
        (repo / ".env").write_text("SOME_VAR=1\n")
        _commit(repo)

        violations = secrets_gate(repo)
        sec002 = [v for v in violations if v.rule == "SEC002"]
        assert len(sec002) == 1
        assert sec002[0].severity == Severity.ERROR
        assert sec002[0].file == ".env"

    def test_env_example_is_not_flagged(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        _init_repo(repo)
        (repo / ".env.example").write_text("SOME_VAR=changeme\n")
        _commit(repo)

        violations = secrets_gate(repo)
        assert violations == ()

    def test_untracked_env_file_is_never_scanned(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        _init_repo(repo)
        (repo / "a.txt").write_text("hello\n")
        _commit(repo)
        # Untracked -- git ls-files never sees it.
        (repo / ".env").write_text("REAL_SECRET=sk_live_" + "z" * 24 + "\n")

        violations = secrets_gate(repo)
        assert violations == ()

    def test_tracked_binary_file_is_skipped_not_crashed(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_secrets.py::secrets_gate
        # `secrets_gate` reads every tracked file as strict UTF-8 text; a
        # tracked binary (invalid UTF-8 bytes -- e.g. a committed image or
        # compiled artifact) must be skipped via the `except (OSError,
        # UnicodeDecodeError)` branch, not raise or silently mis-scan.
        repo = tmp_path / "repo"
        _init_repo(repo)
        (repo / "blob.bin").write_bytes(b"\xff\xfe\x00\xff not valid utf-8 \xd8")
        _commit(repo)

        violations = secrets_gate(repo)
        assert violations == ()


class TestOverlapClaim:
    """T-0157 span-claim discipline (`_scan_line`'s `claimed` list): a later,
    less-specific pattern must not double-report a span an earlier, more-
    specific pattern already claimed on the same line."""

    def test_embedded_overlapping_match_is_not_double_claimed(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_secrets.py::secrets_gate
        # Anthropic's pattern ("sk-ant-" + 20+ [A-Za-z0-9_-]) is tried before
        # OpenAI's legacy pattern ("sk-" + 20+ [A-Za-z0-9]) in `_PATTERNS`.
        # Embedding a second literal "sk-" inside Anthropic's own suffix
        # makes the legacy pattern also match, at a span nested entirely
        # inside the span Anthropic already claimed and reported -- this is
        # the overlap branch in `_scan_line`'s
        # `any(... for start, end in claimed)` check: the legacy match must
        # be dropped as already-claimed, not double-reported as its own
        # SEC001 finding. Runtime-constructed (never a contiguous 20+ char
        # literal in this file's own source), same discipline as
        # `test_anthropic_key_flagged_sec001` above.
        repo = tmp_path / "repo"
        _init_repo(repo)
        token = "sk-ant-" + "sk-" + "q" * 23
        (repo / "overlap.txt").write_text(f"token = {token}\n")
        _commit(repo)

        violations = secrets_gate(repo)
        assert len(violations) == 1
        assert violations[0].rule == "SEC001"
        assert "anthropic" in violations[0].message
        assert "openai" not in violations[0].message


class TestDriftLock:
    """T-0157 drift-lock: a provider in the pattern table with no fixture
    exercising it must fail the suite, so a new pattern can never land
    silently untested."""

    # frob:tests src/frob/gates/_secrets.py::ALL_PROVIDERS
    def test_every_provider_has_a_fixture(self, tmp_path: Path) -> None:
        # The actual drift lock: every provider name in the live pattern
        # table must have a matching entry below, or this fails immediately
        # -- a new pattern landing without a fixture is a build failure.
        assert set(_FIXTURES_BY_PROVIDER) == ALL_PROVIDERS, (
            "every entry in frob.gates._secrets._PATTERNS must have a "
            "matching entry in _FIXTURES_BY_PROVIDER below (T-0157 "
            "drift-lock) -- a provider was added without a test fixture"
        )

        # Each fixture must actually satisfy its own provider's regex...
        for pattern in _PATTERNS:
            fixture_text = _FIXTURES_BY_PROVIDER[pattern.provider]
            assert pattern.regex.search(fixture_text) is not None, (
                f"{pattern.provider}'s fixture in _FIXTURES_BY_PROVIDER does "
                f"not actually match its own regex"
            )

        # ...and a real end-to-end pass: every fixture, committed unmarked
        # into a throwaway repo, is caught by the real secrets_gate.
        repo = tmp_path / "repo"
        _init_repo(repo)
        for name, text in _FIXTURES_BY_PROVIDER.items():
            (repo / f"fixture_{name.replace('/', '_')}.txt").write_text(text + "\n")
        _commit(repo)
        violations = secrets_gate(repo)
        assert len(violations) >= len(_PATTERNS)


# One hand-built, pattern-invalid-but-shape-matching accepting fixture per
# provider (T-0157 drift-lock source of truth). Every value here is
# constructed to satisfy its provider's regex while being obviously not a
# real, currently-valid credential (repeated filler characters, never a
# value that could plausibly be copy-pasted from a live account).
_FIXTURES_BY_PROVIDER: dict[str, str] = {
    "anthropic": "sk-ant-" + "a" * 30,
    "stripe-secret-live": "sk_live_" + "a" * 24,
    "stripe-restricted-live": "rk_live_" + "a" * 24,
    "stripe-webhook": "whsec_" + "a" * 24,
    "stripe-publishable-live": "pk_live_" + "a" * 24,
    "stripe-secret-test": "sk_test_" + "a" * 24,
    "stripe-publishable-test": "pk_test_" + "a" * 24,
    "openai-project": "sk-proj-" + "a" * 24,
    "generic-live-key": "sk-live-" + "a" * 24,
    "openai-legacy": "sk-" + "a" * 24,
    "aws-access-key-id": "AKIA" + "A" * 16,
    "github": "ghp_" + "a" * 36,
    "github-fine-grained": "github_pat_" + "a" * 24,
    "gitlab": "glpat-" + "a" * 24,
    "slack": "xoxb-" + "1" * 12,
    "google": "AIza" + "a" * 35,
    "twilio-api-key": "SK" + "a" * 32,
    "twilio-account-sid": "AC" + "a" * 32,
    "sendgrid": "SG." + "a" * 22 + "." + "b" * 22,
    "square": "sq0atp-" + "a" * 24,
    "braintree": "access_token$production$" + "a" * 16 + "$" + "b" * 32,
    "npm": "npm_" + "a" * 36,
    "pypi": "pypi-" + "a" * 52,
    "huggingface": "hf_" + "a" * 34,
    "plaid": "plaid_secret = " + "a" * 30,
    # Literal PEM header below -- self-scan would otherwise match this dict
    # entry's own source text (unlike every other entry above, there is no
    # way to build this fixture out of concatenated pieces without changing
    # what regex it needs to satisfy), hence the fake marker on its line.
    # frob:secret-fake
    "private-key-pem": "-----BEGIN RSA PRIVATE KEY-----",
    "jwt": "eyJ" + "a" * 12 + "." + "b" * 12 + "." + "c" * 12,
}


class TestTrackedFilesGitFailure:
    """T-0157 degrade-don't-crash posture (`_tracked_files`): a spawn-level
    `run_argv` failure (`Err(GitError...)`, e.g. `git` missing or the
    subprocess timing out) is treated as "no tracked files" -- gate returns
    clean rather than raising -- and is handled separately from a completed
    spawn that merely exits non-zero."""

    def test_spawn_error_yields_no_tracked_files(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/gates/_secrets.py::secrets_gate
        from typani import Err

        from frob.gates import _secrets
        from frob.gitio import GitError

        repo = tmp_path / "repo"
        _init_repo(repo)
        (repo / "a.txt").write_text("hello\n")
        _commit(repo)

        def _fake_run_argv(argv: object, **kwargs: object) -> object:
            return Err(GitError.GitFailed)

        monkeypatch.setattr(_secrets, "run_argv", _fake_run_argv)

        violations = secrets_gate(repo)
        assert violations == ()

    def test_nonzero_exit_yields_no_tracked_files(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/gates/_secrets.py::secrets_gate
        from typani import Ok

        from frob.gates import _secrets
        from frob.gitio import ProcResult

        repo = tmp_path / "repo"
        _init_repo(repo)
        (repo / "a.txt").write_text("hello\n")
        _commit(repo)

        def _fake_run_argv(argv: object, **kwargs: object) -> object:
            return Ok(
                ProcResult(
                    argv=("git", "-C", str(repo), "ls-files"),
                    returncode=128,
                    stdout="",
                    stderr="fatal: not a git repository\n",
                )
            )

        monkeypatch.setattr(_secrets, "run_argv", _fake_run_argv)

        violations = secrets_gate(repo)
        assert violations == ()


class TestGateIsGreenOnItself:
    """T-0151 self-match lesson, locked: the secrets gate must not flag its
    own source module or this test file's fixtures when run for real."""

    def test_secrets_module_source_is_clean(self) -> None:
        # frob:tests src/frob/gates/_secrets.py::secrets_gate
        root = Path(__file__).resolve().parents[1]
        module = root / "src" / "frob" / "gates" / "_secrets.py"
        text = module.read_text(encoding="utf-8")
        from frob.gates._secrets import _scan_text

        violations = _scan_text("src/frob/gates/_secrets.py", text)
        assert violations == [], violations

    def test_this_test_file_is_clean(self) -> None:
        root = Path(__file__).resolve().parents[1]
        this_file = Path(__file__)
        text = this_file.read_text(encoding="utf-8")
        from frob.gates._secrets import _scan_text

        rel = str(this_file.relative_to(root))
        violations = _scan_text(rel, text)
        assert violations == [], violations

    def test_repo_is_clean(self) -> None:
        # frob:tests src/frob/gates/_secrets.py::secrets_gate
        root = Path(__file__).resolve().parents[1]
        violations = secrets_gate(root)
        assert violations == [] or violations == (), (
            "secrets_gate found real-looking credentials in the live repo: "
            + "; ".join(f"{v.rule} {v.file}:{v.line}" for v in violations)
        )


@pytest.mark.parametrize("provider", sorted(ALL_PROVIDERS))
def test_provider_has_a_registered_fixture(provider: str) -> None:
    """Redundant, cheaper drift-lock check: one parametrized case per
    provider currently in the pattern table (T-0157) -- a new provider with
    no `_FIXTURES_BY_PROVIDER` entry fails immediately with the provider
    name in the test id, rather than a single aggregate assertion."""
    # frob:tests src/frob/gates/_secrets.py::ALL_PROVIDERS
    assert provider in _FIXTURES_BY_PROVIDER

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

import re
import subprocess
from pathlib import Path

import pytest

from frob.gates._models import Severity
from frob.gates._secrets import (
    _PATTERNS,
    ALL_PROVIDERS,
    _redact,
    fake_marker_staleness_gate,
    secrets_gate,
)


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
    # invariant spec: [INV-039](invariants/INV-039.md)
    def test_never_returns_the_token(self) -> None:
        # frob:tests src/frob/gates/_secrets.py::_redact
        # Runtime-constructed (never a contiguous literal in this file's
        # own source), T-0190 GitHub-unflaggable discipline: a bare literal
        # "sk_live_" + 20+ contiguous alnum chars is exactly the shape
        # GitHub's push protection matches.
        token = "sk_live_" + "abcdefghijklmnopqrstuvwxyz"
        out = _redact(token, "sk_live_")
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
            # frob:secret-fake reason="fixture PEM header for the SEC003 pem test"
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


class TestProviderParityT0427:
    """T-0427: new providers added toward `docs/design/secrets-pii-corpus.md`
    A.4 parity -- one end-to-end fire test per new pattern, beyond the
    drift-lock's own generic coverage."""

    def test_aws_bedrock_key_flagged_sec001(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_secrets.py::secrets_gate
        repo = tmp_path / "repo"
        _init_repo(repo)
        token = "ABSK" + "d" * 109
        (repo / "config.py").write_text(f'BEDROCK_KEY = "{token}"\n')
        _commit(repo)

        violations = secrets_gate(repo)
        matches = [v for v in violations if "aws-bedrock-api-key" in v.message]
        assert len(matches) == 1
        assert matches[0].severity == Severity.ERROR
        assert "d" * 109 not in matches[0].message

    def test_discord_bot_token_flagged_sec001(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_secrets.py::secrets_gate
        repo = tmp_path / "repo"
        _init_repo(repo)
        token = "N" + "d" * 24 + "." + "e" * 6 + "." + "f" * 27
        (repo / "bot.py").write_text(f'DISCORD_TOKEN = "{token}"\n')
        _commit(repo)

        violations = secrets_gate(repo)
        matches = [v for v in violations if "discord-bot-token" in v.message]
        assert len(matches) == 1
        assert matches[0].severity == Severity.ERROR

    def test_mongodb_atlas_uri_flagged_sec001(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_secrets.py::secrets_gate
        repo = tmp_path / "repo"
        _init_repo(repo)
        # Runtime-constructed (never a contiguous literal in this file's own
        # source), same discipline as test_stripe_live_key_sec003 above.
        uri = "mongodb+srv://" + "dbuser:s3cretpw@cluster0.mongo-prod.net/db"
        (repo / "settings.py").write_text(f'MONGO_URI = "{uri}"\n')
        _commit(repo)

        violations = secrets_gate(repo)
        matches = [v for v in violations if "mongodb-atlas-uri" in v.message]
        assert len(matches) == 1
        assert "s3cretpw" not in matches[0].message
        # The generic basic-auth-url pattern must NOT double-claim the same
        # span -- mongodb-atlas-uri is ordered first as the more specific
        # pattern (table ordering discipline).
        assert not any("basic-auth-url" in v.message for v in violations)

    def test_hashicorp_vault_service_token_flagged_sec001(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_secrets.py::secrets_gate
        repo = tmp_path / "repo"
        _init_repo(repo)
        token = "hvs." + "d" * 24
        (repo / "config.py").write_text(f'VAULT_TOKEN = "{token}"\n')
        _commit(repo)

        violations = secrets_gate(repo)
        matches = [v for v in violations if "hashicorp-vault-service" in v.message]
        assert len(matches) == 1

    def test_hashicorp_vault_batch_token_flagged_sec001(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_secrets.py::secrets_gate
        repo = tmp_path / "repo"
        _init_repo(repo)
        token = "hvb." + "d" * 24
        (repo / "config.py").write_text(f'VAULT_TOKEN = "{token}"\n')
        _commit(repo)

        violations = secrets_gate(repo)
        matches = [v for v in violations if "hashicorp-vault-batch" in v.message]
        assert len(matches) == 1

    def test_basic_auth_url_flagged_sec001_warn(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_secrets.py::secrets_gate
        repo = tmp_path / "repo"
        _init_repo(repo)
        # Runtime-constructed, same discipline as above.
        url = "https://" + "dbuser:s3cretpw@svc.internal/path"
        (repo / "notes.txt").write_text(f"connect to {url}\n")
        _commit(repo)

        violations = secrets_gate(repo)
        matches = [v for v in violations if "basic-auth-url" in v.message]
        assert len(matches) == 1
        assert matches[0].severity == Severity.WARN
        assert "s3cretpw" not in matches[0].message


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
        """T-0968 (gates-quality audit finding 3) INVERTS this case's
        original pre-T-0968 assertion -- name kept as-is (an already-closed
        ticket, T-0157, cites this exact test id as evidence; renaming it
        would only break that historical evidence resolution, not the
        finding this docstring documents). A token merely CONTAINING the
        substring "fake" is no longer suppressed for free -- that
        bare-substring escape (the AWS canonical placeholder access key id
        class of false negative) is dropped from `_PLACEHOLDER_WORDS`. This
        real-shaped Anthropic token happens to contain "fake" but matches
        none of the remaining anchored template-shape/low-entropy-phrase
        checks, so it now fires like any other real-looking token would."""
        repo = tmp_path / "repo"
        _init_repo(repo)
        (repo / "notes.txt").write_text("sk-ant-fake" + "d" * 25 + "\n")
        _commit(repo)

        violations = secrets_gate(repo)
        assert any(v.rule == "SEC001" for v in violations)

    def test_fake_marker_same_line(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        _init_repo(repo)
        (repo / "notes.py").write_text(
            'KEY = "sk-ant-'
            + "e" * 30
            + '"  # frob:secret-fake reason="fabricated fixture token"\n'
        )
        _commit(repo)

        violations = secrets_gate(repo)
        assert violations == ()

    def test_frob_secret_fake_marker_on_line_above(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        _init_repo(repo)
        (repo / "notes.py").write_text(
            '# frob:secret-fake reason="fabricated fixture token"\n'
            + 'KEY = "sk-ant-'
            + "f" * 30
            + '"\n'
        )
        _commit(repo)

        violations = secrets_gate(repo)
        assert violations == ()

    def test_frob_secret_fake_marker_without_reason_still_fires(
        self, tmp_path: Path
    ) -> None:
        """T-0968: a bare `frob:secret-fake` (no `reason="..."`) no longer
        discharges anything -- mirrors WAIVE001's `frob:waive` contract --
        and is itself flagged as SEC004."""
        repo = tmp_path / "repo"
        _init_repo(repo)
        # T-0190 discipline: the bare marker itself is split across two
        # concatenated literals so this test file's own raw source never
        # contains the contiguous, un-reasoned `# frob:secret-fake` text
        # this case deliberately writes into the fixture repo.
        (repo / "notes.py").write_text(
            "# frob:secret" + "-fake\n" + 'KEY = "sk-ant-' + "g" * 30 + '"\n'
        )
        _commit(repo)

        violations = secrets_gate(repo)
        assert any(v.rule == "SEC001" for v in violations)
        assert any(v.rule == "SEC004" for v in violations)

    def test_placeholder_phrase_your_dash_here_is_not_flagged(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_secrets.py::secrets_gate
        # T-0219: a doc-example token like `xoxb-your-...-here`
        # reads as an obvious template to a human but contains none of the
        # single-word `_PLACEHOLDER_WORDS` (fake/changeme/example/
        # placeholder) -- pre-fix, this fired a false-positive SEC001.
        # Runtime-constructed (T-0190: never a contiguous literal in this
        # file's own source, same discipline as the real-shaped-token
        # fixtures above).
        repo = tmp_path / "repo"
        _init_repo(repo)
        token = "xoxb-your-" + "slack-token-here"
        (repo / "README.md").write_text(f"SLACK_TOKEN={token}\n")
        _commit(repo)

        violations = secrets_gate(repo)
        assert violations == ()

    def test_placeholder_phrase_insert_dash_is_not_flagged(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_secrets.py::secrets_gate
        # Same T-0219 phrase-recognition fix, `insert-` variant.
        # Runtime-constructed, same T-0190 discipline as above.
        repo = tmp_path / "repo"
        _init_repo(repo)
        token = "xoxb-insert-" + "your-real-token"
        (repo / "README.md").write_text(f"SLACK_TOKEN={token}\n")
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

    def test_placeholder_phrase_your_does_not_suppress_high_entropy_token(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_secrets.py::secrets_gate
        # T-0219 round 2 (reviewer-reproduced bypass): a real-shaped,
        # high-entropy `sk-live-` token that merely CONTAINS `your-` as a
        # substring (e.g. naming a tenant "your-company") must still fire
        # SEC001 -- the old bare `.search()` phrase check silently dropped
        # this. Runtime-constructed, same discipline as the other
        # real-shaped-token tests above.
        repo = tmp_path / "repo"
        _init_repo(repo)
        token = "sk-live-your-company" + "".join(str(n % 10) for n in range(16))
        (repo / "config.py").write_text(f'X = "{token}"\n')
        _commit(repo)

        violations = secrets_gate(repo)
        matches = [v for v in violations if v.rule == "SEC001"]
        assert len(matches) == 1

    def test_placeholder_phrase_insert_does_not_suppress_high_entropy_token(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_secrets.py::secrets_gate
        # Same bypass class, `insert-` fragment embedded in a real-shaped,
        # digit-bearing token.
        repo = tmp_path / "repo"
        _init_repo(repo)
        token = "sk-live-insert" + "".join(str(n % 10) for n in range(20))
        (repo / "config.py").write_text(f'X = "{token}"\n')
        _commit(repo)

        violations = secrets_gate(repo)
        matches = [v for v in violations if v.rule == "SEC001"]
        assert len(matches) == 1

    def test_placeholder_phrase_here_does_not_suppress_high_entropy_token(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_secrets.py::secrets_gate
        # Same bypass class, `-here` fragment embedded in a real-shaped,
        # digit-bearing token (not the exact `-here` template tail, just a
        # substring appearing mid-token).
        repo = tmp_path / "repo"
        _init_repo(repo)
        token = "sk-live-here" + "".join(str(n % 10) for n in range(20)) + "abcd"
        (repo / "config.py").write_text(f'X = "{token}"\n')
        _commit(repo)

        violations = secrets_gate(repo)
        matches = [v for v in violations if v.rule == "SEC001"]
        assert len(matches) == 1

    def test_digit_free_mixed_case_your_token_still_fires(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_secrets.py::secrets_gate
        # T-0219 round 3 (reviewer-reproduced live bypass): round 2's
        # `_looks_low_entropy` was `not any(c.isdigit() for c in token)` --
        # a binary "has no digits" check, not a real entropy measure. A
        # digit-free, high-entropy, real-shaped token containing `your-`
        # was silently suppressed regardless of how random it looked.
        # Runtime-constructed (mixed-case run glued on, never a contiguous
        # literal in this file's own source) so this file's own self-scan
        # stays clean while still exercising the exact bypass shape.
        repo = tmp_path / "repo"
        _init_repo(repo)
        tail = "XKCDplmqrstuvwxyz" + "ABCD"
        token = "sk-live-your-" + tail
        (repo / "config.py").write_text(f'X = "{token}"\n')
        _commit(repo)

        violations = secrets_gate(repo)
        matches = [v for v in violations if v.rule == "SEC001"]
        assert len(matches) == 1

    def test_digit_free_insert_alphabet_run_still_fires(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_secrets.py::secrets_gate
        # Same round-3 bypass class: digit-free, single-case, but a wide
        # near-unique-letter run -- real Shannon entropy reads this as
        # high, unlike the round-2 binary digit check which suppressed it
        # outright just for containing `insert-`.
        repo = tmp_path / "repo"
        _init_repo(repo)
        tail = "abcdefgh" + "qrstuvwxyz"
        token = "sk-live-insert-" + tail
        (repo / "config.py").write_text(f'X = "{token}"\n')
        _commit(repo)

        violations = secrets_gate(repo)
        matches = [v for v in violations if v.rule == "SEC001"]
        assert len(matches) == 1

    def test_digit_free_mixed_case_here_tail_still_fires(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_secrets.py::secrets_gate
        # Same round-3 bypass class, `-here` tail variant: mixed-case,
        # digit-free, and structurally close to `_KNOWN_TEMPLATE_SHAPE_RE`
        # (ends in `-here`) but does NOT fullmatch it (second segment is
        # `live`, not `your`/`insert`), so this token can only be wrongly
        # suppressed via `_looks_low_entropy` -- which the mixed-case gate
        # and entropy floor must both refuse.
        repo = tmp_path / "repo"
        _init_repo(repo)
        tail = "abcd" + "XYZQRSTUVW"
        token = "sk-live-" + tail + "-here"
        (repo / "config.py").write_text(f'X = "{token}"\n')
        _commit(repo)

        violations = secrets_gate(repo)
        matches = [v for v in violations if v.rule == "SEC001"]
        assert len(matches) == 1


class TestFakeMarkerStaleness:
    """T-0978: `fake_marker_staleness_gate` -- WAIVE004 zero-findings
    staleness for the reserved `frob:secret-fake` marker family, wired in
    at the gate level (T-0157's reserved-verb constraint stands: this
    marker never becomes a real `frob:waive` graph `Edge`)."""

    def test_stale_marker_fires_waive004(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_secrets.py::fake_marker_staleness_gate
        """A marker discharging a site with no real secret-shaped token
        left behind (the underlying token was fixed/removed but the marker
        comment was never cleaned up) is stale."""
        repo = tmp_path / "repo"
        _init_repo(repo)
        (repo / "notes.py").write_text(
            'KEY = "not-a-secret-anymore"'
            '  # frob:secret-fake reason="fabricated fixture token"\n'
        )
        _commit(repo)

        violations = fake_marker_staleness_gate(repo)
        assert any(v.rule == "WAIVE004" for v in violations)
        hit = next(v for v in violations if v.rule == "WAIVE004")
        assert hit.file == "notes.py"
        assert hit.line == 1

    def test_stale_marker_on_line_above_fires_waive004(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_secrets.py::fake_marker_staleness_gate
        repo = tmp_path / "repo"
        _init_repo(repo)
        (repo / "notes.py").write_text(
            '# frob:secret-fake reason="fabricated fixture token"\n'
            'KEY = "not-a-secret-anymore"\n'
        )
        _commit(repo)

        violations = fake_marker_staleness_gate(repo)
        assert any(v.rule == "WAIVE004" for v in violations)

    def test_live_marker_does_not_fire(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_secrets.py::fake_marker_staleness_gate
        """A marker still discharging a genuinely real-looking token is not
        stale -- the mirror-image case of the fire tests above."""
        repo = tmp_path / "repo"
        _init_repo(repo)
        (repo / "notes.py").write_text(
            'KEY = "sk-ant-'
            + "e" * 30
            + '"  # frob:secret-fake reason="fabricated fixture token"\n'
        )
        _commit(repo)

        violations = fake_marker_staleness_gate(repo)
        assert violations == ()

    def test_marker_discharging_email_shaped_pii_does_not_fire(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_secrets.py::fake_marker_staleness_gate
        """T-0968: this marker family is shared with PII011 (email-shaped
        literals) -- a marker whose site is email-shaped, not SEC00x-
        shaped, must not be misread as stale just because no SEC00x
        pattern matches there (`_plausibly_still_needed`)."""
        repo = tmp_path / "repo"
        _init_repo(repo)
        (repo / "notes.py").write_text(
            '# frob:secret-fake reason="fabricated fixture email"\n'
            'EMAIL = "ci@fake.example.com"\n'
        )
        _commit(repo)

        violations = fake_marker_staleness_gate(repo)
        assert violations == ()

    def test_bare_marker_without_reason_is_not_a_staleness_site(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_secrets.py::fake_marker_staleness_gate
        """A bare marker (no `reason=`) is SEC004's territory, not
        WAIVE004's -- `fake_marker_staleness_gate` only ever enumerates
        reason-bearing sites."""
        repo = tmp_path / "repo"
        _init_repo(repo)
        # T-0190 discipline: split so this test file's own raw source
        # never contains the contiguous, un-reasoned marker text.
        (repo / "notes.py").write_text(
            "# frob:secret" + "-fake\n" + 'KEY = "not-a-secret-anymore"\n'
        )
        _commit(repo)

        violations = fake_marker_staleness_gate(repo)
        assert violations == ()

    def test_docstring_style_mention_is_not_a_staleness_site(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_secrets.py::fake_marker_staleness_gate
        """A prose/docstring MENTION of the marker (backtick-quoted, or
        embedded inside a Python string literal) is never mistaken for a
        real directive -- mirrors `_BARE_FAKE_DIRECTIVE_RE`'s own backtick
        exclusion, extended here to the quote-adjacent case a
        multi-line-literal test-authoring pattern produces."""
        repo = tmp_path / "repo"
        _init_repo(repo)
        (repo / "notes.py").write_text(
            'DOC = "see the `frob:secret-fake reason=\\"...\\"` marker"\n'
        )
        _commit(repo)

        violations = fake_marker_staleness_gate(repo)
        assert violations == ()


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
    "aws-bedrock-api-key": "ABSK" + "a" * 109,
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
    "discord-bot-token": "M" + "a" * 24 + "." + "b" * 6 + "." + "c" * 27,
    "mongodb-atlas-uri": "mongodb+srv://" + "user:pass@cluster0.mongo-prod.net/db",
    "hashicorp-vault-service": "hvs." + "a" * 24,
    "hashicorp-vault-batch": "hvb." + "a" * 24,
    "basic-auth-url": "https://" + "user:pass@svc.internal/path",
    "plaid": "plaid_secret = " + "a" * 30,
    # Literal PEM header below -- self-scan would otherwise match this dict
    # entry's own source text (unlike every other entry above, there is no
    # way to build this fixture out of concatenated pieces without changing
    # what regex it needs to satisfy), hence the fake marker on its line.
    # frob:secret-fake reason="literal PEM header fixture, not a real key"
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

    #: T-0968: `tickets.md`/`tickets-archive.md` are the git-tracked ticket
    #: LEDGER, out of this ticket's declared scope to hand-edit (playbook
    #: ledger-splice discipline) -- both files quote the audit's own
    #: AWS canonical placeholder access key id (`AKIA` + `IOSFODNN7EXAMPLE`)
    #: repro text verbatim as narrative/planning
    #: prose describing this exact finding, not a real leaked credential.
    #: Dropping the bare-substring `example`/`fake` suppression
    #: (`_PLACEHOLDER_WORDS`, T-0968 finding 3 fix) makes that quoted prose
    #: newly real-looking to the tightened scanner; excluded here by file,
    #: not by loosening the scanner itself.
    _LEDGER_NARRATIVE_FILES = frozenset({"tickets.md", "tickets-archive.md"})

    def test_repo_is_clean(self) -> None:
        # frob:tests src/frob/gates/_secrets.py::secrets_gate
        root = Path(__file__).resolve().parents[1]
        violations = [
            v
            for v in secrets_gate(root)
            if v.file not in TestGateIsGreenOnItself._LEDGER_NARRATIVE_FILES
        ]
        assert violations == [] or violations == (), (
            "secrets_gate found real-looking credentials in the live repo: "
            + "; ".join(f"{v.rule} {v.file}:{v.line}" for v in violations)
        )


class TestGitHubPushProtectionUnflaggable:
    """T-0190: GH013 push protection rejected main because a fixture in an
    earlier revision of this file (the Stripe key at 48aeed1, T-0157) was a
    contiguous literal that matched GitHub's own secret-scanning patterns
    closely enough to be blocked as a real credential, even though it was
    already pattern-invalid/fake-marked for frob's own gate. This class is
    the meta-test the ticket calls for: a coarse re-encoding of GitHub's
    published detector shapes (github.com/advanced-security/secret-
    scanning-patterns) for the providers this repo's fixtures are most
    likely to collide with, checked directly against THIS FILE'S OWN
    on-disk source text -- so a future fixture that reintroduces a
    contiguous, GitHub-flaggable literal fails locally before it can ever
    reach a push and retrip GH013.

    Deliberately narrower than `frob`'s own `_PATTERNS` table: GitHub's
    scanner requires an unbroken literal run in the raw file bytes, so a
    fixture built by concatenating string pieces at runtime (this file's
    house style throughout, e.g. `"sk-ant-" + "a" * 30`) can satisfy
    frob's own regex when evaluated while never appearing as one
    contiguous span in the source -- that is precisely the property this
    class locks in.
    """

    #: Coarse re-encodings of a handful of GitHub's published secret-
    #: scanning patterns, chosen to match the providers T-0157's fixture
    #: table covers and that are most likely to be mistaken for a real,
    #: partner-verified credential. These are intentionally looser than
    #: frob's own per-provider regexes (no anchoring, generous charset) --
    #: the goal is "would GitHub plausibly flag a contiguous literal like
    #: this", not an exact reproduction of GitHub's private matching logic.
    _GITHUB_FLAGGABLE_RES: tuple[re.Pattern[str], ...] = (
        re.compile(r"sk_live_[0-9a-zA-Z]{20,}"),  # Stripe live secret key
        re.compile(r"AKIA[0-9A-Z]{16}"),  # AWS access key id
        re.compile(r"ghp_[0-9a-zA-Z]{30,}"),  # GitHub personal access token
        re.compile(r"xox[baprs]-[0-9a-zA-Z-]{10,}"),  # Slack token
    )

    def test_this_file_contains_no_github_flaggable_literal(self) -> None:
        # frob:tests src/frob/gates/_secrets.py::secrets_gate
        text = Path(__file__).read_text(encoding="utf-8")
        hits: list[str] = []
        for pattern in self._GITHUB_FLAGGABLE_RES:
            for m in pattern.finditer(text):
                hits.append(f"{pattern.pattern} -> {m.group(0)[:8]}...")
        assert hits == [], (
            "this file contains a contiguous literal shaped like a "
            "GitHub-flaggable credential (GH013 push-protection risk, "
            "T-0190): " + "; ".join(hits)
        )

    def test_pattern_source_module_contains_no_github_flaggable_literal(
        self,
    ) -> None:
        # frob:tests src/frob/gates/_secrets.py::secrets_gate
        root = Path(__file__).resolve().parents[1]
        module = root / "src" / "frob" / "gates" / "_secrets.py"
        text = module.read_text(encoding="utf-8")
        hits: list[str] = []
        for pattern in self._GITHUB_FLAGGABLE_RES:
            for m in pattern.finditer(text):
                hits.append(f"{pattern.pattern} -> {m.group(0)[:8]}...")
        assert hits == [], (
            "the pattern-table source itself contains a contiguous "
            "GitHub-flaggable literal (GH013 push-protection risk, "
            "T-0190): " + "; ".join(hits)
        )


@pytest.mark.parametrize("provider", sorted(ALL_PROVIDERS))
def test_provider_has_a_registered_fixture(provider: str) -> None:
    """Redundant, cheaper drift-lock check: one parametrized case per
    provider currently in the pattern table (T-0157) -- a new provider with
    no `_FIXTURES_BY_PROVIDER` entry fails immediately with the provider
    name in the test id, rather than a single aggregate assertion."""
    # frob:tests src/frob/gates/_secrets.py::ALL_PROVIDERS
    assert provider in _FIXTURES_BY_PROVIDER

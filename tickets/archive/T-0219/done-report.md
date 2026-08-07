## Done report

**Root cause, miss 1 (sk-live- adjacent):** confirmed both misses reproduce
on main (6164712) before any fix -- `_scan_text` returned `[]` for a
`sk-live-<24 hex>` token embedded in `X = "sk-live-...." # trailing note`
and for `xoxb-your-slack-token-here`. Miss 1's root cause is a FORMAT
CONSTRAINT, not a missing prefix-table entry per se: the existing
`openai-legacy` pattern `sk-[A-Za-z0-9]{20,}` requires 20+ contiguous
alnum-ONLY chars right after `sk-`; `sk-live-...` has a hyphen 4 chars in
(`live-`), which breaks that run before it reaches the 20-char floor, so
NO pattern in `_PATTERNS` ever claimed the span (this is also why
"adjacency" mattered in the ticket title -- the token never matched
regardless of what surrounds it). Fix: added a new, more-specific
`generic-live-key` pattern (`sk-live-[A-Za-z0-9-]{16,}`, `SEC001`,
critical) ordered before `openai-legacy` per the file's most-specific-
prefix-first discipline (`src/frob/gates/_secrets.py` `_PATTERNS`).

**Root cause, miss 2 (placeholder phrase):** `_looks_fake` only checked
single WORDS (`fake`/`changeme`/`example`/`placeholder`) and an
XXXX/**** run; a phrase like `xoxb-your-slack-token-here` matches the real
Slack regex and contains none of those words, so it fired a false-
positive SEC001 despite being an obvious template. Fix: added
`_PLACEHOLDER_PHRASE_RE` (`-here`, `your-`, `insert-`, case-insensitive)
checked in `_looks_fake` alongside the existing word list.

**Litmus tests added** (`tests/test_secrets_gate.py`):
- `TestFindsTokens.test_generic_live_key_adjacent_to_other_content_sec001`
  -- miss 1, now caught.
- `TestFakeMarking.test_placeholder_phrase_your_dash_here_is_not_flagged`
  -- miss 2 (`-here`/`your-` phrase), now correctly ignored.
- `TestFakeMarking.test_placeholder_phrase_insert_dash_is_not_flagged` --
  miss 2, `insert-` variant.
- `TestFakeMarking.test_placeholder_phrase_does_not_suppress_real_looking_token`
  -- regression guard: a real-shaped Slack token with none of the new
  phrase fragments still fires (the phrase heuristic must stay scoped, not
  swallow real detections).
- `generic-live-key` added to `_FIXTURES_BY_PROVIDER` (drift-lock
  requirement, `TestDriftLock.test_every_provider_has_a_fixture` and the
  parametrized `test_provider_has_a_registered_fixture`).

**No false positives introduced:** `tests/test_secrets_gate.py` full
suite, 52 passed (`uv run pytest tests/test_secrets_gate.py -q`), including
`TestGateIsGreenOnItself.test_repo_is_clean`,
`test_this_test_file_is_clean`, and `test_secrets_module_source_is_clean`
(the module's own source and this test file, self-scanned by the real
gate, stay clean) and all existing `frob:secret-fake`-marked fixtures
(T-0157/T-0294) still discharge correctly -- unchanged, still passing.

**Evidence:**
- `tests/test_secrets_gate.py::TestFindsTokens::test_generic_live_key_adjacent_to_other_content_sec001`
- `tests/test_secrets_gate.py::TestFakeMarking::test_placeholder_phrase_your_dash_here_is_not_flagged`
- `tests/test_secrets_gate.py::TestFakeMarking::test_placeholder_phrase_insert_dash_is_not_flagged`
- `tests/test_secrets_gate.py::TestFakeMarking::test_placeholder_phrase_does_not_suppress_real_looking_token`
- `tests/test_secrets_gate.py::TestDriftLock::test_every_provider_has_a_fixture`
- `tests/test_secrets_gate.py::TestGateIsGreenOnItself::test_repo_is_clean`

**Gates:** `uv run frob check --ticket T-0219` clean: 0 errors, 1 warning
(pre-existing `TEST006` "no coverage stamp found", unrelated to this
change), 24 waived (all pre-existing). `uv run ruff check` and
`uv run ruff format --check` clean on both touched files; `uv run ty
check` clean. `uv run frob test --base main` selected and ran
`tests/test_gates.py::test_gates_run_gates_integration` +
`tests/test_secrets_gate.py`, exit=0. Full-repo `uv run frob check`
(unscoped): `gates 0 errors, 1 warning, 24 waived` -- same pre-existing
`TEST006` warning, no new secrets-gate or other violations. Deletion-
filter (`git diff main --diff-filter=D --stat`) empty.

Filed: none -- both misses were fully addressable within this ticket's
declared scope (`src/frob/gates/_secrets.py`, `tests/**`, `tickets.md`).

Not closing per dispatch instructions -- leaving for reviewer.

## Done report (round 2 -- security bypass fix)

**Reviewer-found bypass:** round 1's `_PLACEHOLDER_PHRASE_RE` was
`.search()`'d as a bare SUBSTRING test against the whole token, and
`_looks_fake` gated the entire SEC001 detection path unconditionally. A
real-shaped, high-entropy `sk-live-` token that merely CONTAINS `your-`,
`insert-`, or `-here` anywhere -- e.g. a live key naming a tenant
"your-company" -- was silently suppressed: zero violations, debug log
"generic-live-key match ... placeholder, skipping". An attacker (or a
tenant genuinely named `your...`) could evade SEC001 entirely by choosing
a credential name that happens to contain one of those three fragments.
Reproduced against the pre-round-2 worktree code before fixing (see
verification below).

**Fix -- anchored-or-entropy-gated phrase suppression**
(`src/frob/gates/_secrets.py`): a phrase match now suppresses ONLY when
one of two guards holds, never on the bare substring alone:
1. `_KNOWN_TEMPLATE_SHAPE_RE` -- a whole-token structural anchor,
   `^[a-z0-9]{2,10}-(your|insert)-[a-z-]+-here$`, matched with
   `fullmatch` against the ENTIRE token (not `.search()`). Catches
   `xoxb-your-slack-token-here`, `sk-insert-api-key-here`, etc.
2. `_looks_low_entropy(token)` AND `_PLACEHOLDER_PHRASE_RE.search(token)`
   -- the phrase must also be sitting inside token text with NO digits
   anywhere (`_looks_low_entropy` returns `not any(c.isdigit() for c in
   token)`). A real secret's non-prefix portion is machine-generated
   noise and virtually always mixes in digits; a human template
   (`insert-your-real-token`) is plain lowercase words and hyphens, no
   digits at all.

Net rule: a token is placeholder-fake via the phrase path only if it is a
known whole-token template shape, OR it is digit-free AND contains the
phrase. A high-entropy, digit-bearing, real-shaped token is NEVER
suppressed by phrase content alone, regardless of what substrings it
happens to contain. `_looks_fake`'s docstring and the `_PLACEHOLDER_PHRASE_RE`
comment block now document this explicitly so the substring trap cannot
be silently reintroduced.

Out of scope, left alone per dispatch instructions: the single-word
`_PLACEHOLDER_WORDS` check (`fake`/`changeme`/`example`/`placeholder`)
still does a bare substring `in` test and has the same theoretical
substring-embedding weakness (e.g. a live key named "...fakecompany...").
The dispatch explicitly named only the phrase-regex bypass for this
round; the word-list's own approved detection behavior (T-0157) was not
touched. Not filing a new ticket for it -- noting here for the reviewer's
awareness since it is the same class of gap.

**Mandatory adversarial regression tests added**
(`tests/test_secrets_gate.py::TestFakeMarking`):
- `test_placeholder_phrase_your_does_not_suppress_high_entropy_token` --
  `sk-live-your-company` + 16 digits fires SEC001.
- `test_placeholder_phrase_insert_does_not_suppress_high_entropy_token` --
  `sk-live-insert` + 20 digits fires SEC001.
- `test_placeholder_phrase_here_does_not_suppress_high_entropy_token` --
  `sk-live-here` + 20 digits + `abcd` fires SEC001.

**Confirmed bypass-then-fix:** stashed only `src/frob/gates/_secrets.py`
(keeping the new tests), reran the three new tests against the
pre-round-2 source -- `test_placeholder_phrase_your_does_not_suppress_high_entropy_token`
FAILED (`assert 0 == 1`, log line `generic-live-key match ...
placeholder, skipping`), confirming the bypass reproduces exactly as the
reviewer described. Restored the round-2 fix and reran: all three pass,
along with the full `tests/test_secrets_gate.py` suite (58 passed,
including `TestGateIsGreenOnItself::test_repo_is_clean` and
`test_secrets_module_source_is_clean`, and the pre-existing round-1
whole-token placeholder tests `test_placeholder_phrase_your_dash_here_is_not_flagged`
/ `test_placeholder_phrase_insert_dash_is_not_flagged`, still suppressed
correctly via the `_KNOWN_TEMPLATE_SHAPE_RE`/low-entropy paths).

**Gates:** `uv run pytest tests/test_secrets_gate.py -q` -- 58 passed.
`uv run ruff check .`, `uv run ruff format --check .`, `uv run ty check`
all clean. `uv run frob check` (full repo, unscoped): `gates 0 errors, 1
warning, 24 waived` -- same single pre-existing `TEST006` warning as
round 1, no new secrets-gate violations, no new waivers added.

Evidence stays node-level (see the three new test node ids above, plus
round 1's evidence list, unchanged).

Filed: none -- fix fully addressable within this ticket's declared scope.

Not closing -- reviewer.

## Done report (round 3 -- entropy-proxy bypass fix)

**Reviewer-found bypass (live-reproduced):** round 2's
`_looks_low_entropy(token)` was `return not any(char.isdigit() for char in
token)` -- a binary "has no digits" check, not a real entropy measure. A
digit-free, high-entropy, real-shaped token containing a placeholder-
phrase fragment (`your-`/`insert-`/`-here`) was still silently suppressed
regardless of how random the rest of it looked: 0 violations confirmed for
an `sk-live-your-` prefix glued to a mixed-case run, an `sk-live-insert-`
prefix glued to a near-unique-letter alphabet run, and an `sk-live-`
prefix glued to a mixed-case run ending in `-here` (see the three new
adversarial test cases below for the exact fragments).

**Fix -- real entropy/diversity measure, security-safe by construction**
(`src/frob/gates/_secrets.py`): replaced `_looks_low_entropy` with three
independent, conservative gates, ALL of which must hold before a token is
ever classified low-entropy -- failing any single one keeps it
high/unsuppressed, the security-safe default when uncertain:
1. No digit anywhere (unchanged from round 2, still decisive on its own
   for "not low").
2. Single case only (all-lowercase or all-uppercase letters). Mixed case
   is rejected outright before entropy is even computed -- a real
   generated token frequently mixes case, a hand-typed template phrase
   never does.
3. Real Shannon entropy over the token's alnum characters, bits/char,
   below a calibrated `_LOW_ENTROPY_BITS_PER_CHAR = 3.7` floor.

Calibration against this repo's own fixtures: the existing legit-
suppressed placeholder `xoxb-insert-your-real-token` sits at ~3.64
bits/char (below the floor, still correctly suppressed, no regression);
the reviewer's adversarial `sk-live-insert-` token (a near-unique-letter
run, essentially no character repeats) sits at ~4.32
bits/char (above the floor, correctly now fires); any mixed-case token
never reaches the entropy calculation at all. `_KNOWN_TEMPLATE_SHAPE_RE`
(the whole-token `fullmatch` anchor from round 2, confirmed sound by the
reviewer) is unchanged and remains the primary path for the canonical
`prefix-your/insert-words-here` shape; the entropy gate now only matters
for phrase fragments that don't fullmatch that anchor (no `-here` tail, or
a non-`your`/`insert` middle segment, as in all three of the reviewer's
adversarial tokens).

**Mandatory adversarial regression tests added**
(`tests/test_secrets_gate.py::TestFakeMarking`), all digit-free and
runtime-constructed (concatenated fragments, never a contiguous literal in
this file's own source) so the addition itself stays clean under
`TestGateIsGreenOnItself`:
- `test_digit_free_mixed_case_your_token_still_fires` -- `sk-live-your-` +
  `XKCDplmqrstuvwxyzABCD` (mixed case) fires SEC001.
- `test_digit_free_insert_alphabet_run_still_fires` -- `sk-live-insert-` +
  `abcdefghqrstuvwxyz` (near-unique-letter run, all-lowercase) fires
  SEC001.
- `test_digit_free_mixed_case_here_tail_still_fires` -- `sk-live-` +
  `abcdXYZQRSTUVW` + `-here` (mixed case, structurally close to but does
  NOT fullmatch `_KNOWN_TEMPLATE_SHAPE_RE` since the middle segment is
  `live` not `your`/`insert`) fires SEC001.

**Confirmed bypass-then-fix:** stashed only `src/frob/gates/_secrets.py`
(keeping the new tests), reran the three new tests against the
pre-round-3 source -- all three FAILED (`assert 0 == 1`, log line
`generic-live-key match ... placeholder, skipping`), confirming each of
the reviewer's three tokens reproduces the exact live bypass described.
Restored the round-3 fix and reran: all three pass, along with the full
`tests/test_secrets_gate.py` suite (61 passed), including
`TestGateIsGreenOnItself::test_repo_is_clean` and
`test_secrets_module_source_is_clean`, and every prior round 1/2
adversarial and legit-suppression test unchanged and still green (no
regressions).

Also reworded the module docstring's `_looks_low_entropy`-adjacent example
tokens (previously literal, self-scan-tripping strings) into non-
contiguous doc phrasing, since the new fix's own commentary needed to
reference example token shapes without becoming a false positive against
this module's own self-scan.

**Gates:** `uv run pytest tests/test_secrets_gate.py -q` -- 61 passed.
`uv run ruff check .`, `uv run ruff format --check .` (after `ruff
format`), `uv run ty check src/frob/gates/_secrets.py` all clean. `make
coverage` then `uv run frob check` (full repo, unscoped): `gates 0 errors,
1 warning, 204 waived` -- same single pre-existing warning, no new
violations, no new secrets-gate waivers.

Committed in worktree `.claude/worktrees/agent-aaa45dc8342d35cc0`
(branch `worktree-agent-aaa45dc8342d35cc0`), sha `6cea368`.

Filed: none -- fix fully addressable within this ticket's declared scope.

Not closing -- reviewer.

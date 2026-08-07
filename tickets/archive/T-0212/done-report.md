## Done report

Changed:
- src/frob/graph/dsl.py :: slugify -- rewritten to GitHub's real algorithm
  (lowercase, strip everything that is not `\w`/hyphen/space via
  unicode-aware `\w`, then replace each space with its own hyphen -- no
  more collapsing punctuation+space runs into a single `-`)
- src/frob/graph/dsl.py :: dedupe_slug (new) -- applies GitHub's repeated-
  heading `-1`/`-2` suffixing, given a per-document `seen` counter
- src/frob/graph/dsl.py :: markdown_anchors -- now threads a `seen` dict
  through the heading walk and calls dedupe_slug so `frob:describes`
  anchors get the same suffixing GitHub would apply
- src/frob/graph/__init__.py -- exports dedupe_slug alongside slugify
- src/frob/gates/__init__.py :: _doc_anchor_slugs -- now applies
  dedupe_slug over the ordered heading walk before building the resolvable
  slug set, so DOC002 (and its T-0165 did-you-mean suggestion, which reuses
  this same slug set via difflib in _anchor_mismatch_message) reflect
  GitHub's real duplicate-heading anchors, not just first-occurrence ones
- src/frob/docs/__init__.py -- 7 frob:doc anchors targeting
  docs/modules/app.md updated from the stale slug `#frob-docs-library` to
  the corrected `#frobdocs-library` (heading is "## frob.docs library";
  the `.` is deleted outright under the new algorithm instead of
  collapsing with the following space into one `-`)
- tests/test_graph.py :: TestSlugify -- rewrote the punctuation-collapse
  assertion, added a table-driven `test_github_slug_table` covering the
  ticket's own tricky-heading examples plus '.', '&', '/', ',', '!', '_',
  existing '-', leading/trailing spaces, '%', '+', and an all-hyphens
  heading; added test_unicode_letters_survive_emoji_are_stripped (unicode
  letters survive via chr()-built strings to stay ASCII-in-file per repo
  rule, emoji do not since they are not \w) and
  test_dedupe_slug_suffixes_repeats
- tests/unit/test_research_assets.py -- the local `_slugify`/`_heading_slugs`
  mirror of frob.graph.dsl (kept separate on purpose so this drift-lock
  test doesn't import gate internals) updated to match the new algorithm
  plus its own `_dedupe_slug` mirror
- src/frob/strata/_ast.py, _compliance.py, _deploy.py, _infra.py,
  _lint.py, _models.py, _pii.py, src/frob/policy/_models.py -- the
  remaining 46 frob:doc anchors broken by the corrected slugify, fixed
  with the exact did-you-mean slugs the docanchor gate itself computed:
  `docs/strata/surface.md#std-deploy` -> `#stddeploy` (_ast.py x2,
  _models.py x2, _deploy.py x2), `docs/strata/surface.md#std-infra` ->
  `#stdinfra` (_ast.py x5, _infra.py x2),
  `docs/strata/threat.md#operational-design-lints-std-lint-t-0155` ->
  `#operational-design-lints-stdlint-t-0155` (_lint.py x9),
  `docs/strata/threat.md#compliance-regulatory-obligations-std-compliance`
  -> `#compliance-regulatory-obligations-stdcompliance` (_compliance.py
  x10), `docs/strata/threat.md#pii-declarations-std-pii-t-0154` ->
  `#pii-declarations-stdpii-t-0154` (_pii.py x10),
  `docs/modules/gates.md#policy-rules-frob-toml-policy` ->
  `#policy-rules-frobtoml-policy` (_models.py x2)
- pyproject.toml -- version 0.2.0 -> 0.3.0 (RELEASE001: adding the new
  public `dedupe_slug` symbol to frob.graph's exports is a minor public
  API change); `.frob-release.json` re-stamped via `frob release stamp`

Scope note: T-0212 was widened per coordinator directive after initial
review -- the 46 anchors above were originally not filed as a separate ticket
(T-draft-2327479e (never refiled)) on the theory that they were outside T-0212's declared
scope. On review it was correctly identified that those 46 breaks are a
direct, inseparable mechanical consequence of THIS branch's slugify
rewrite (they only resolve, or fail to resolve, against this exact
slugger), so landing them as a follow-up would leave main red between the
two landings. T-0212's scope was widened to include the 8 affected files
(src/frob/strata/_ast.py, _compliance.py, _deploy.py, _infra.py, _lint.py,
_models.py, _pii.py, src/frob/policy/_models.py), T-draft-2327479e (never refiled)'s
content was folded into this ticket and the draft entry was dropped
entirely from tickets.md (it never had a landed T-#### id -- it was a
provisional id minted off-default-branch and never merged, so there was
no dangling reference to clean up elsewhere).

Migration decision (disclosed, not silent): clean cutover, no
old-slug-acceptance compatibility window. All 53 DOC002 violations the
corrected slugify produced (7 in the original scope + 46 in the widened
scope) are fixed in this single branch. A dual-form-acceptance shim in
slugify/docanchor_gate was considered and rejected: 53 total anchor edits
is cheap and mechanical (six distinct old->new slug mappings, applied via
targeted sed across the 9 affected files), and a compatibility shim would
be permanent complexity for a one-time migration.

Evidence:
- `uv run pytest tests/test_graph.py -k TestSlugify` -- 15 passed
  (test_lowercases_and_strips_disallowed_punctuation,
  test_empty_falls_back_to_top, test_github_slug_table[11 cases],
  test_unicode_letters_survive_emoji_are_stripped,
  test_dedupe_slug_suffixes_repeats)
- `uv run pytest tests/test_graph.py tests/test_gates.py
  tests/unit/test_research_assets.py
  tests/unit/test_extending_guides_complete.py tests/unit/test_ticket_store.py
  tests/unit/strata` -- all passed (full run after the scope-widening fix)
- `uv run ruff check` + `uv run ruff format --check` on every changed
  file, including the 8 widened-scope files -- all clean
- `uv run frob check --only docanchor --json` -- 0 DOC002 violations
  repo-wide (was 53 before any fix)
- `uv run frob check --only doclink --json` -- 0 DOC001 violations
- `uv run frob check --only release --json` -- 0 REL001 violations after
  the 0.3.0 version bump + `frob release stamp`
- `uv run frob check` (full run) -- exit code 0. Remaining diagnostics
  (30, all warning/note severity: PERF001-004, TEST006) are pre-existing
  and unrelated to this ticket, confirmed by running the same `--only`
  gates on the pre-widen commit via `git stash`; none are DOC002 or
  DOC001 and none were introduced by this diff
- `git diff main --diff-filter=D --stat` -- empty (no unintended
  deletions), re-checked after merging main (T-0192/T-0229, fast-forward
  99ec64c -> 289f2c6) and after the scope-widening fix
- `git merge origin/main` -- fast-forward, no conflicts against source;
  the only conflict was in tickets.md itself (T-0261 vs the now-dropped
  T-draft-2327479e (never refiled) block), resolved by keeping T-0261 intact and removing
  the draft ticket entirely

Not Filed: none (T-draft-2327479e (never refiled) folded into this ticket and removed from
the ledger, per the coordinator's directive; no other out-of-scope work
discovered)

Gates: `uv run frob check` clean (exit 0). `docanchor` and `doclink`
gates both 0 violations repo-wide. No waivers added.

Second main merge (land-rule catch, worked as designed): after finishing
the scope-widening fix above, `git diff main --diff-filter=D --stat`
showed `tests/unit/strata/litmus/waive_lint_store.strata` and
`tests/unit/strata/test_litmus_waive_store.py` as deletions -- files this
branch never touched. Cause: `origin/main` moved again mid-session (from
289f2c6 to 423c299, landing T-0250 "extend waive clause to stores", which
added those two files plus new lines in src/frob/strata/_ast.py and
src/frob/strata/_infra.py -- both files this ticket's widened scope also
touches). Per agent-playbook.md section 9, merged main again
(fast-forward, no conflicts against source; the tickets.md ledger
auto-merged cleanly this time) instead of committing through the stale
deletion-filter result. T-0250 also changed strata-core/src/parse.rs, so
`make core` was re-run to rebuild the native extension (stale
strata_core rejected the new store-property grammar with "unknown store
property" parse errors on design/frob.strata and the new litmus fixture
until rebuilt). After the rebuild: `docanchor` and `doclink` gates still
0 repo-wide, `release` gate still 0 (re-verified against the new merge),
`frob check --diff-filter=D --stat` against the now-current main is
empty, and `pytest tests/test_graph.py tests/test_gates.py
tests/unit/test_research_assets.py tests/unit/test_extending_guides_complete.py
tests/unit/test_ticket_store.py tests/unit/strata` all pass. No conflict
or interaction between this ticket's anchor-slug edits and T-0250's new
_ast.py/_infra.py lines (T-0250 added new frob:doc-anchored code below
the lines this ticket edited; git auto-merged both cleanly and the
did-you-mean-derived slugs still apply verbatim to the pre-existing
anchors).

NOT closing this ticket per the review-gated flow (agent-playbook.md
section 11.4).

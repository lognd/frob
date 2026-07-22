# Changelog

All notable changes to `frob` are recorded here. Format is loosely
Keep-a-Changelog; entries reference the ticket id (`T-####`) that shipped
them so the full rationale is always one `frob ticket show` away.

There has never been a tagged release of this project before. `0.2.0` is
the first. Everything below landed on `main` between the initial commit
(`ad79fd6`, tree-sitter/jinja2 scaffold) and the tip at the time of this
release (393 commits). The version was bumped from the placeholder
`0.1.0a0` because the alpha tag no longer describes the project: 161
tickets closed across five strata phases, a threat/CWE/CVE/compliance
obligation catalog, a capability exhaustiveness matrix, a design lint
family, smart-dup (frob-core), the extending-frob guide series, and a
release gate of its own are all live and gated by `frob check`. This
list is derived mechanically from every `state: done` ticket in
`tickets.md` + `tickets-archive.md` at merge time; the claimed count
matches `grep -oE 'T-[0-9]{4}' CHANGELOG.md | sort -u | wc -l` exactly.

## [0.65.0] - unreleased

T-0461/T-0459/T-0562: `RENDER001` (bare stdout `print()` outside
`frob.render`) landed on `main` between this branch's fork point and its
merge back in; bumped here to cover that surface alongside T-0550's own
change (below) since both are unreleased public-API deltas the release
gate had not yet been stamped against.

## [0.64.0] - unreleased

T-0549/T-0550: two more gates-accounting audit fixes (T-0403 B7/B8).
`_case_count` caps a parametrized python test's counted variants to 1
unless its body actually contains an assertion-shaped construct, closing
the `@pytest.mark.parametrize(range(N))`-with-no-assertions escape from
`TEST002`/`TEST003`/`TEST009`'s minimum-case floors. `coverage_gate`
gained an optional `diff_load_failed: bool = False` kwarg: a genuinely
FAILED `working_diff` (bad `--base`, no merge-base, git error) now fires
a loud `COV002`/`SCOPE001`/`TODO001` violation instead of silently
degrading to an empty, clean-looking diff.

## [0.63.0] - unreleased

T-0541/T-0542: two gates-accounting audit fixes (T-0403 B9/B10).
`coverage_gate` gained an optional `active_ticket: str | None = None`
kwarg (COV002 now prefers the active ticket's own scope, and treats two
open tickets whose scopes ambiguously, equally cover the same file as
NOT covering it rather than picking the first match found). `run_gates`
no longer silently skips `SCOPE001`/`PRE001` when no active ticket is
derivable and the diff touches real source (only a `tickets.md`-only or
empty diff still skips cleanly) -- it now emits a blocking violation
instead, closing an off-convention-branch/`main`-commit escape from
scope and pre-work enforcement.

## [0.62.0] - unreleased

T-0555: `frob.lang` gained `partial_parse_files()`, a `reset_parse_cache`-
scoped accessor (mirroring `parse_cache_stats`'s shape) returning the
display paths of every file whose tree-sitter parse was salvaged around a
syntax error since the last reset (T-0404 finding 9) -- previously only a
scattered `_warn_if_partial_tree` (T-0434) `WARNING` log line, invisible
below `-v` and with no structured consumer, especially for Rust/C++/TS
repos with no gates stage at all (T-0546/T-0554) to notice it. Wiring a
blocking `frob check` violation off this list is a `frob.gates`-family
change tracked separately.

## [0.61.0] - unreleased

T-0424: reflexive check-coverage registry -- `docs/design/registry/
check-coverage.yaml` is a tenth `docs/design/registry/*.yaml` instance
(added to `frob.gates._registry_exhaustiveness.REGISTRY_FILES`, the same
unified gate T-0407 built, no second mechanism), seeded honestly from the
live `frob.gates.known_gate_rule_ids()` inventory (82 entries, each
self-referentially `handled_by` its own rule id) plus the `docs/audits/`
7-auditor pessimistic-pass concern families (5 cross-cutting themes + 8
per-subsystem verdicts, 13 entries, each `deferred:T-0397`, the real open
audit-remediation epic). An un-dispositioned concern reds the same
REG001-REG007 exhaustiveness gate every other registry instance is bound
to -- frob's own check-coverage is now a first-class, exhaustible,
gate-enforced registry rather than something only the user's eyeballs
audit (see docs/design/registry/README.md#check-coverageyaml-t-0424-frobs-own-reflexive-check-coverage-registry).

## [0.60.0] - unreleased

T-0407: unified registry capability -- new `frob.registry` module
(`RegistryEntry`/`Disposition`/`DispositionKind`/`RegistryFile`/
`RegistryAudit`, `load_registry_dir`, `audit_registry_file`,
`parse_disposition`) is now the single source of truth for the
`docs/design/registry/*.yaml` entry shape and disposition grammar;
`frob.gates._registry_exhaustiveness.registry_gate` (T-0343) was
refactored onto it rather than carrying a second, duplicated inline
parser. Two early-exit/partial-coverage holes the pre-unification gate
silently allowed are now closed: **REG006** (a malformed list item --
not a mapping, or missing a string `id` -- previously vanished from every
count with no trace) and **REG007** (the same `id` defined by two or
more entries anywhere in the registry, a real collision distinct from an
intentional `duplicate_of:` reference). New CLI subcommand `frob
registry audit` reports the per-file `handled`/`deferred`/`duplicate`/
`out_of_scope`/`unaccounted`/`malformed` accounting against `total`, so
"is this registry exhausted" is a one-line honest read (see
docs/design/registry/EXHAUSTIVENESS-GATE.md#unified-model-t-0407).

## [0.58.0] - unreleased

T-0454: professional ticket organization -- `Ticket`/`TicketSpec` gained
`component: str | None` (freeform module/area) and `labels: tuple[str,
...]` (freeform tags orthogonal to component), both additive/optional so
every pre-existing ticket stays valid on load. New public
`set_component`/`mutate_labels` mutation functions (same single-writer,
ledger-locked pattern as `set_priority`/`mutate_scope`), `board_view`/
`BoardColumn`/`BOARD_STATES` (a fixed-column, priority-ordered board over
the whole active queue), and `epic_rollup`/`EpicRollup` (the `parent`
chain's full descendant subtree, a done/total rollup, and any BLOCKED
leaf). New CLI subcommands `frob ticket component <id> <name>`, `frob
ticket label <id> --add/--remove TAG...`, `frob ticket board
[--component/--label]`, `frob ticket epic <id>`; `frob ticket new` gained
`--component`/`--label`. Sprints/milestones and a doable/list component-
label filter were deliberately deferred as follow-ups (see
docs/modules/tickets.md#organization-components-labels-board-epics-t-0454).

## [0.57.0] - unreleased

T-0510: `frob.strata._threat` gained five `WeaknessEntry` rows in
`QUALITY_CATALOG` (CWE-916 weak-hash password storage, CWE-1321
prototype pollution, CWE-1333 ReDoS, CWE-601 open redirect, CWE-1336
SSTI), each catalog-only (`capability_kind=None`, discharged by the
`std.cve` fingerprint layer, mirroring CWE-295's precedent) -- previously
disclosed gaps `_cve_fingerprint.py`'s own docstring named as blocked on
a missing `WeaknessEntry`. `frob.strata._cve_fingerprint.CVE_FINGERPRINTS`
gained a matching real-CVE-cited needle per CWE (FP-WEAKHASH-PASSWORD-001,
FP-PROTO-POLLUTION-001, FP-REDOS-REGEX-001, FP-OPEN-REDIRECT-001,
FP-SSTI-TEMPLATE-001), 13 -> 18 entries. `docs/design/registry/
weaknesses.yaml`'s five matching `SEC-CVE-FINGERPRINT-CWE-*` rows flipped
from `disposition: deferred:T-0510` to `handled_by:SEC-CVE-FINGERPRINT-001`
with the new fingerprint ids cross-referenced.

T-0511: `frob.strata._threat.BenignCapability` gained an optional
`family: str | None` field ("security" | "quality", `None` for the
built-in `DEFAULT_BENIGN_CAPABILITIES` tuple) -- mandatory for every
`load_repo_benign_capabilities` (`[[strata.benign_capabilities]]`
frob.toml) entry, verified at load time against that family's own
catalog: an entry whose `kind` is already classified in the family it
names is rejected (`Err(StrataError.MalformedBenignConfig)`) rather than
accepted as a blanket, unverified excuse (strata audit G12).

T-0512: `frob.strata._audit.AuditReport` gained
`narrower_than_baseline: tuple[str, ...]` -- every security-family
baseline view (`VIEWS` union `CWE_TOP_25_VIEWS`) a `frob sys audit` run's
configured `security_views` did not include (empty for a genuinely
exhaustive run); `frob sys audit`'s CLI printer now discloses this
unconditionally instead of a PROVED report silently meaning "narrower
than the full catalog baseline" (strata audit G6).

## [0.56.0] - unreleased

T-0358: `frob.app.config.stale_install_warning` -- a loud stderr warning,
printed by `main()` before every subcommand dispatches, when the running
`frob` is a globally installed binary whose version differs from the
current checkout's `pyproject.toml`-declared version (the stale-global-
binary phantom-numbers trap: an old installed gate implementation silently
running against a newer working tree, producing wrong violation counts).

T-0433: `frob.graph.cache._FINGERPRINT_PACKAGES` (G6, T-0402 residual) is
now derived from `frob.lang.GRAMMAR_FINGERPRINT_PACKAGES` (a new public
constant -- the tree-sitter grammar packages every non-`.strata` language
in `frob.lang` loads through) instead of a hand-copied tuple, so a future
grammar-loading package change updates the cache-invalidation fingerprint
automatically. Also fixed G7 (T-0402 residual): `_parse_source_file_fresh`
now stores `parsed.content_hash` -- the hash `frob.lang` computed from the
exact bytes it read and parsed -- rather than a hash the caller read
separately beforehand, closing the hash/parse TOCTOU window where a write
between the two reads could store fresh symbols under a stale hash.

## [0.55.0] - unreleased (tickets chain 3: frob:debt)

T-0412: `frob:debt` vs `frob:waive` -- a TEMPORARY, ticket-bound, tracked
exception distinct from `frob:waive`'s PERMANENT one. New public API:
`EdgeKind.DEBT`, `frob.gates.debt_gate`/`list_debt`/`DebtEntry`, and the
`DEBT001`/`DEBT002`/`DEBT003` rule ids (malformed directive / non-open
ticket / expired `until`). `frob.gates.release_gate` (REL001) now
additionally fails while ANY `frob:debt` is open, expired or not -- debt
is collected and re-raised before a release, never silently carried
forward. New `frob debt [--json]` CLI (`frob.app.debt_runner`) lists every
outstanding entry (rule, site, ticket, until, expired). Migration of the
~143 existing debt-shaped `frob:waive` directives to `frob:debt` is
deliberately NOT done in this release -- see docs/guides/extending/
comment-dsl-directives.md's migration-guidance note; it is a follow-up
burndown ticket.

## [0.54.0] - unreleased (tickets chain 3: intent journal)

T-0456: crash/interrupt recovery, the remaining delta after T-0473
(cross-worktree lease registry)/T-0476 (reconcile)/T-0479 (own-block ledger
splice) had already landed the rest. Added `frob.tickets._journal` (new
public `write_intent`/`clear_intent`/`read_all_intents`/`LandIntent`/
`JournalError`/`journal_dir`): `frob ticket land` now records a small
`.frob/journal/<ticket-id>.json` marker before it starts mutating anything
and clears it in a `finally` block on every exit, so a marker outliving the
process means it crashed mid-land. `frob ticket reconcile` gained a third
anomaly class, orphaned land intents, reported every run and cleared
(never auto-resumed) under `--apply`. `frob.tickets._store.atomic_write`
now `fsync`s the temp file before the `os.replace` that makes it visible,
closing the "rename completed but data unflushed" crash window for every
`tickets.md`/`.frob-release.json`/lease/journal write.

T-0507: extended the T-0431 `FROB_WORKTREE` lease guard to `frob release
stamp` (`frob.release.stamp`, new `ReleaseError.WorktreeLeaseViolation`
member) and `frob ack` (`frob.app.ack_runner.run`) -- the two remaining
mutating entry points T-0431 had not yet covered.

## [0.53.0] - unreleased

T-0517: `frob.dup._cache`'s `dup.db` gained a version fingerprint (reusing
`frob.graph.cache._compute_fingerprint`, the T-0243 pattern) -- a
`dup.db` written under an older frob/tree-sitter grammar version now has
its `fingerprints`/`verdicts` rows invalidated on reconnect instead of
silently serving stale content-addressed rows under an algorithm change.
`tests/test_dup_cross_lang.py` also no longer leaks an untracked
`.frob/dup.db` into the tracked fixture directory it runs against.

T-0518: `frob.dup._exhaustiveness.DUP_CLAIMS` gained the r5/typescript
cell (`compute_total`/`computeTotal`, T-0494's fixture), mirroring the
r5/rust entry T-0487 already added -- the cross-language R5 capability
this repo actually has is now reflected in the exhaustiveness matrix
instead of falling through the generic non-python language-gap excuse.

## [0.52.0] - unreleased (tickets-bugs chain)

T-0446: `frob.tickets.scope_matches` gained an optional `kind` keyword --
when `kind=TicketKind.FEATURE`, the three well-known CLI-wiring files
(`src/frob/__main__.py`, `src/frob/app/config.py`,
`src/frob/app/ticket_runner.py`, `frob.tickets._models.CLI_WIRING_FILES`)
are implicitly in scope, mirroring `LEDGER_PATH`'s always-in-scope rule
(T-0241). The SCOPE001 gate (`scope_gate`) now passes `ticket.kind`
through, so a feature ticket adding a new `frob ticket <subcommand>` no
longer needs a `frob ticket scope --add` per wiring file just to avoid
SCOPE001 -- the exact "scope-expansion ceremony" T-0323 (adding `frob
ticket merge-driver`) hit and T-0446 was filed to close. `kind=None` (the
default, and every pre-T-0446 call site) preserves prior behavior exactly;
non-FEATURE tickets still trip SCOPE001 on these files as before.

## [0.51.0] - unreleased (gates-calibration chain)

- T-0506: COV006's disclosed T-0483 false-positive shape (a test reaching
  its bound private target only via a same-file public wrapper) is now
  rescued by a gate-local one-hop lookahead
  (`_cov006_public_wrapper_reachable`), reducing COV006 from 98 to 89
  findings on this repo without weakening `frob.graph.callgraph`'s
  public-boundary-stop guarantee (still load-bearing for frob.dup/arch).
  Residual burndown filed as a follow-up ticket per its count.
- T-0509: INV003/INV004 calibrated -- claim-shape scanning now strips
  fenced/inline code, link targets, and table rows before matching, and
  requires a claim-verb in the same sentence as the trigger word
  (`frob.gates.invariants._is_claim_shaped`); INV003 is scoped to
  `INV003_SPEC_DIRS` (docs/modules, docs/strata) rather than all of
  docs/**.md; markdown-side `<!-- frob:waive INV003|INV004
  reason="..." -->` support lets a genuine-but-unprovable claim be
  dispositioned honestly. INV003+INV004 combined warnings: 765 -> 604.

## [0.50.0] - unreleased

T-0411: queue health + priority model. Tickets carry a `priority`
(low/medium/high/critical, default medium) field; `frob ticket doable`
orders by priority first, then age (previously age-only); a new TICK004
gate warns (escalating to error) when a queued/planned ticket sits past
its priority-specific rot-day threshold (default 3/7/30/90 days for
critical/high/medium/low, configurable via `frob.toml`'s `[tickets]`
table); `frob ticket priority <id> <level>` reprioritizes an existing
ticket through the single-writer ledger path.

## [0.49.0] - unreleased (reconciliation)

Another parallel landing chain (T-0335/T-0462/T-0452/T-0465, gates-area
tickets worked sequentially in one worktree) independently claimed
version numbers 0.44.0-0.46.0, colliding with the land-machinery/strata
chains reconciled at 0.47.0/0.48.0 below. Final reconciled version is
0.49.0; that chain's own three sections follow immediately below under
the numbers they were authored with, same reconciliation pattern as
0.47.0.

## [0.46.0] - unreleased (gates-area chain)

Public-API surface change since 0.45.0 (mechanical semver via REL001): an
additive (minor) bump -- new hazard-guard gate rule.

- T-0465: EXCL001, a new (ERROR-severity, unwaivable) gate rule flagging
  `.git/info/exclude` entries that shadow git-tracked source. `.git/
  info/exclude` is the SHARED common-dir file across every worktree of a
  clone -- an agent once added `src/frob/render/` to it to hide its own
  scratch files, silently blinding `git status`/`git add -A` to every
  NEW file added under that real source directory afterward, in every
  worktree, until the T-0448 foundation went missing. New public
  `frob.gates.exclude_hazard_gate` (`src/frob/gates/_exclude_hazard.py`).
  Added the same hazard as a hard rule in
  docs/guides/agent-playbook.md (section 1c).

## [0.45.0] - unreleased (gates-area chain)

Public-API surface change since 0.44.0 (mechanical semver via REL001): an
additive (minor) bump -- new advisory invariant density lint.

- T-0452: INV004, a new advisory (warn-severity, never fails `frob
  check`) invariant gate rule complementing INV003's per-claim check
  with the section-level inverse: a `docs/**.md` section using ANY
  normative language ("must", "must not", "never", "always", "shall",
  "guarantees", "ensures", "requires", plus INV003's exclusivity
  vocabulary) but anchoring ZERO `frob:invariant` markers at all is
  flagged as likely under-specified -- the "silence" a per-claim lint
  can't see. New public `frob.gates.invariants.find_normative_claims` /
  `NORMATIVE_CLAIM_PATTERNS` and `frob.gates.inv004_gate`.

## [0.44.0] - unreleased (gates-area chain)

Public-API surface change since 0.43.0 (mechanical semver via REL001): an
additive (minor) bump -- new invariant-language lint.

- T-0462: INV003, a new (warn-severity) invariant gate rule: a
  `docs/**.md` file making an exclusivity/normative claim ("only",
  "sole"/"solely", "exclusively", "nothing else", "never...except", "at
  most/exactly one") needs a `<!-- frob:invariant INV-### -->` marker in
  the same file naming a real, loaded invariant. New public
  `frob.gates.invariants.find_exclusivity_claims` /
  `EXCLUSIVITY_CLAIM_PATTERNS` (the exclusivity-word corpus) and
  `frob.gates.inv003_gate`. WARN, not ERROR: the vocabulary's bare "only"
  surfaces ~90 findings across this repo's own pre-existing docs;
  hardening specific docs to ERROR (or building markdown-side
  `frob:waive` support) is follow-up work, not done in this pass.

## [0.48.0] - unreleased (strata round 2, part 2)

Public-API surface change since 0.44.0 (mechanical semver via REL001): an
additive (minor) bump -- new `frob.strata.scan_text_for_fingerprints`/
`FingerprintHit` and `frob.gates.cve_fingerprint_scan_gate`.

- T-0439: added SEC-CVE-FINGERPRINT-001, a `frob check` gate scanning
  first-party repo source for the `CVE_FINGERPRINTS` needle corpus
  (`frob.strata._cve_fingerprint`) -- the missing first-party-source-lint
  sibling of CVEFP001 (catalog-drift only, no source scan) and `frob vet`'s
  `_scan_file_fingerprints` (third-party dependency source, no file:line).
  New `frob.strata.scan_text_for_fingerprints`/`FingerprintHit` do the
  line-level needle scan; `frob.gates.cve_fingerprint_scan_gate`
  (`src/frob/gates/_cve_fingerprint_scan.py`) walks every git-tracked,
  language-bucketed file and wires it into `frob check` as WARN-severity
  `SEC-CVE-FINGERPRINT-001` (registered in `_KNOWN_GATE_RULES`). Litmus
  pair: `tests/unit/strata/test_cve_fingerprint_scan.py` -- a "smelly" fixture
  (`shell=True`) fires, a "clean" one (`shell=False`) and an out-of-language
  file do not.

## [0.48.0] - unreleased (strata round 2, part 1)

Public-API surface change since 0.43.0 (mechanical semver via REL001): an
additive (minor) bump -- new `frob.strata.COMPLIANCE_OUT_OF_SCOPE` catalog.

- T-0503: COMPLIANCE004 (`caught_by` integrity for compliance out-of-scope
  exclusions) was vacuous in production -- `_audit.py` never threaded an
  `out_of_scope` catalog into `evaluate_compliance` (unlike the security/
  quality families' `CWE_TOP_25_OUT_OF_SCOPE`/`QUALITY_OUT_OF_SCOPE`), so
  it always defaulted to `()` and the check trivially passed regardless of
  a fabricated `caught_by`. Added `COMPLIANCE_OUT_OF_SCOPE` (a real,
  production `OutOfScopeRegulation` catalog, `frob.strata._compliance`) and
  threaded it into `_compliance_pii_lint_fingerprint_gaps`'s
  `evaluate_compliance` call. Non-vacuous proof: `tests/unit/strata/
  test_audit.py::TestExhaustiveness.
  test_compliance_out_of_scope_bad_caught_by_fails_real_audit_path` shows a
  fabricated `caught_by` failing through the real production entrypoint
  (`evaluate_exhaustiveness`, exactly what `frob sys audit` calls), not
  just the unit-level `check_regulation_caught_by_integrity` evaluator.

## [0.47.0] - unreleased

Reconciliation section: two parallel landing chains independently claimed
overlapping version numbers. The check-output UX chain (T-0419/T-0420/
T-0421: TTY progress task-list, per-family gate stages + gate-summary,
skip_unchanged per-language reporting; new RenderWriter-driven check
runner surface) stamped 0.44.0 without a section, colliding with the
land-machinery chain's sections below. Final reconciled version is
0.47.0; the sections below document the land-machinery surface under the
numbers they were authored with.

## [0.46.0] - unreleased

Public-API surface change since 0.45.0 (mechanical semver via REL001): an
additive (minor) bump -- new `frob.tickets.enforce_worktree_lease` and
`frob.scaffold.install_worktree_lease_hook`.

- T-0431: worktree-lease guard. New `FROB_WORKTREE=<abs path>` env var
  names the one worktree an agent's shell is authorized to mutate frob's
  tracked ticket state in; `frob.tickets.enforce_worktree_lease(root)`
  refuses (`Err(WorktreeLeaseViolation)`) when it is set and `root`'s
  actual git top-level does not match it -- wired as the first statement
  of every mutating `frob.tickets` entry point (`new_ticket`,
  `transition`, `add_evidence`, `add_cmd_evidence`, `set_done_report`,
  `record_failure`, `attach`, `archive`, `renumber`/`renumber_one`) and
  into `frob.gates`' `stamp_baseline`/`stamp_coverage`. Unset (the
  coordinator's own commands) is unrestricted, matching prior behavior.
  New `frob.scaffold.install_worktree_lease_hook` installs `pre-commit`/
  `pre-merge-commit` git hooks that abort loudly when `FROB_AGENT` is set
  non-empty, catching a raw `git commit`/`git merge` an agent shell ran
  directly against the wrong checkout, independent of `frob.tickets`.

## [0.45.0] - unreleased

Public-API surface change since 0.44.0 (mechanical semver via REL001): an
additive (minor) bump -- new `frob.tickets.closed_ticket_ids`.

- T-0409: ledger-hygiene gate (TICK003). WARN (escalating to ERROR past a
  hard cap) when the active `tickets.md` ledger holds more than a
  configurable threshold (`frob.toml` `[tickets]` `stale_archive_warn`/
  `stale_archive_error`, default 20/60) of closed (done/dropped) tickets
  sitting un-archived -- the repeated "we got away with not running `frob
  ticket archive`" gap this ticket exists to close. New public
  `frob.tickets.closed_ticket_ids(queue)` is the shared "which tickets are
  closed" predicate the gate counts over. Resurrection-safe by
  construction: the gate only counts and recommends `frob ticket archive`,
  never writes anything itself, so it can never interact with the land/
  splice path's archive-resurrection guards (`_drop_resurrected_ids`,
  `splice_ledger`).

## [0.44.0] - unreleased

Public-API surface change since 0.43.0 (mechanical semver via REL001): a
signature change to an existing public symbol (`frob.tickets.land`), so
REL001 computes it as MAJOR-class -- under the "0.x is initial
development" semver rule this bumps the MINOR, not to 1.0.0.

- T-0338: `frob ticket land` now owns the two remaining coordinator-
  plumbing steps the T-0479 own-block-only splice did not cover: a
  REL001 version-bump/stamp step and a native-rebuild trigger. New
  optional `land()` parameters `bump_version` and `rebuild_natives`
  (both default `None`, matching the T-0398/D-05 `collected`/`passed`/
  `covers_scope` pattern): `bump_version(root, ticket, final_id)` is
  invoked right after the squash-apply is staged, computing whatever
  `frob.release` says the just-squashed public API demands and, if
  needed, rewriting `pyproject.toml`'s version, prepending a minimal
  CHANGELOG.md entry, and `frob release stamp`-ing the manifest, all
  staged into the same landing commit; `rebuild_natives(root)` runs only
  when the landed changeset touches `frob-core/`/`strata-core/` and
  triggers a rebuild (best-effort, non-blocking on failure). `LandReport`
  grew `release_bumped_to`/`natives_rebuilt` fields. The `frob ticket
  land` CLI supplies both by default
  (`frob.app.ticket_runner._apply_release_bump_for_land`/
  `_land_rebuild_natives_fn`).

## [0.43.0] - unreleased

Public-API surface change since 0.42.0 (mechanical semver via REL001): an
additive (minor) bump -- new `frob.tickets.replay_evidence_from_done_report`.

- T-0357: coordinator-land evidence-loss recovery. A ticket closed straight
  from a hand-merged worktree (`git merge --no-ff`, bypassing `frob ticket
  land`'s ledger splice) could arrive at `transition(..., DONE)` with an
  empty structured `evidence:` field even though its Done report prose
  still carried the rendered ids -- failing MissingEvidence and forcing a
  manual `frob ticket evidence` re-record on main (the T-0248/T-0266
  incidents). New `frob.tickets.replay_evidence_from_done_report` parses a
  ticket's own rendered `### Evidence` Done-report section (the inverse of
  `render_evidence_block`) and recovers those ids into the structured
  field; `transition(..., DONE)` now attempts this automatically,
  best-effort, before falling through to the ordinary MissingEvidence
  rejection.

## [0.42.0] - unreleased

Public-API surface change since 0.41.0 (mechanical semver via REL001): an
additive (minor) bump -- new `frob.tickets._reconcile` module and `frob
ticket reconcile` CLI command.

- T-0476: ticket<->worktree binding + liveness reconcile. New `frob.
  tickets.reconcile`/`ReconcileReport` (`src/frob/tickets/_reconcile.py`),
  reusing the T-0473 lease registry to judge two anomaly classes
  structurally: a stale `IN_PROGRESS` hold (a checkout's own ledger shows
  it, but no live lease backs it -- requeued to `QUEUED` via the same edge
  `frob ticket requeue` uses) and an orphan live worktree (a real `git
  worktree` entry with no lease naming it -- flagged, and only removed with
  `--remove-orphans`, a strictly more destructive opt-in gated separately
  from `--apply`). New `frob ticket reconcile [--apply] [--remove-orphans]`
  CLI command.

## [0.41.0] - unreleased

Public-API surface change since 0.40.0 (mechanical semver via REL001):
additive minor bump -- DOC004 console/bash command-drift tier driven by
[[docblocks.commands]] (T-0443) and PERF007 cross-stage redundant-
recomputation detection in frob.perf._redundancy (T-0413).

## [0.40.0] - unreleased

Public-API surface change since 0.39.0 (mechanical semver via REL001):
strata caught_by integrity -- new COMPLIANCE004 check, shared public
`caught_by_unresolved_tokens` helper in frob.strata._threat (T-0382),
and the eval/CWE-94 threat join with self-conformance updates (T-0401
G3).

## [0.39.0] - unreleased

Public-API surface change since 0.38.0 (mechanical semver via REL001): an
additive (minor) bump -- new `frob.testing.python_coverage_targets`
(touched-set incremental coverage, T-0484) plus file-/directory-level
COV003 evidence resolution and parametrized-node-id fixes (T-0298,
T-0324). The 0.38.0 bump (cross-worktree lease registry
`frob.tickets._leases`, T-0473) landed without its own section; both are
reconciled here.

## [0.37.0] - unreleased

Public-API surface change since 0.36.0 (mechanical semver via REL001): an
additive (minor) bump -- new `frob.check._memo` run-scoped memoization
module.

- T-0423: compute-once contract for the heavy pure analyses. New
  `frob.check._memo` module: `run_memo_scope` (context manager activating
  memoization for one `frob check` invocation), `reset_run_memo` (test/
  convenience entry into an unconditionally-active scope), `run_memo_stats`
  (hit/miss instrumentation, mirroring `frob.lang.parse_cache_stats`), and
  `memoize_per_run` (the decorator itself). Applied to `frob.graph.
  build_graph` and `frob.arch.analyze_project` at their definition site --
  a second call with identical arguments while a scope is active is a
  cache hit, not a recompute, regardless of which `frob check` stage calls
  it. Generalizes the T-0414 parse-cache pattern one level up; closes the
  T-0418 arch-double-run class of bug. `frob.dup.find_duplicates` was
  deliberately NOT touched (out of this ticket's scope; `src/frob/dup/` is
  concurrently under active rework) -- filed as a follow-up.

## [0.36.0] - unreleased

Public-API surface change since 0.35.0 (mechanical semver via REL001): an
additive (minor) bump -- new render vocabulary on `frob.render`.

- T-0460: render vocabulary follow-on to the T-0448 foundation -- `table`,
  `tree`, and `count_deltas` elements (each total: plain-mode shape and
  color-mode painting are identical once ANSI is stripped), plus `Progress`
  (TTY-only, cursor-controlling, clears on completion per the T-0419
  contract; a no-op on any non-TTY stream). New `RenderWriter` methods:
  `table`, `tree`, `count_deltas`, `progress`. See
  `docs/modules/render.md`.

## [0.34.0] - unreleased

Public-API surface change since 0.33.0 (mechanical semver via REL001): an
additive (minor) bump -- new `frob.render` package.

- T-0448: FOUNDATION for the unified TTY-aware CLI output layer EPIC. New
  `frob.render` package -- `Renderer` (the only object a command runner
  should print through), `RenderWriter` (the standardized element
  vocabulary, namespaced off `Renderer.write`: heading, subhead, kv,
  status, count_summary, path, ticket_id, good, warn, critical, muted),
  `resolve_color` (single TTY/color decision honoring `NO_COLOR`,
  `FROB_NO_COLOR`, `--no-color`, `--color=auto|always|never`, `TERM=dumb`,
  `CLICOLOR_FORCE`), the five-name colorblind-safe semantic palette
  (`good`/`warn`/`critical`/`muted`/`accent`), and `RenderError`. `frob
  doctor` and `frob map` are migrated as the two FOUNDATION exemplars
  (`--json` paths unchanged). See `docs/modules/render.md`.

## [0.33.0] - unreleased

Public-API surface change since 0.32.0 (mechanical semver via REL001): an
additive (minor) bump -- one new public function and five new public
constants, no removal or signature-breaking change to any existing caller.

- T-0373: the arch gate (`frob.gates._arch.arch_gate`, the ARCH stage of
  `frob check`) used to always call `frob.arch.analyze_project` with the
  library's own conservative keyword defaults (30-line functions, 500-line
  files), silently ignoring the calibrated 60-line/800-line thresholds the
  user had already decided on -- that calibration only ever reached the
  standalone `frob arch` CLI, never the gate `frob check` actually runs.
  New `frob.app.config.load_arch_config(root)` reads a `[arch]` table from
  `frob.toml` (`max_function_lines`, `max_class_methods`,
  `max_local_imports`, `max_nesting_depth`, `max_file_lines`), defaulting
  every unset key to the calibrated values (new `ARCH_DEFAULT_MAX_*`
  constants), and `arch_gate` now threads it through. This repo's own
  `frob.toml` now carries an explicit `[arch]` table disclosing the
  calibration.
- T-0319: new `frob doctor` subcommand -- verifies the native extensions
  (`frob_core`, `strata_core`) are importable, reports availability and
  version for each, and exits nonzero with the remediation command
  (`make core` / `make install-tool`) when either is missing, so a
  natives-less install gets a clear diagnosis instead of silently degraded
  gates. `frob doctor --json` emits the same report machine-readably. New
  public `frob.doctor` module (`run_diagnosis`, `DoctorReport`,
  `NativeExtensionStatus`, `NATIVE_EXTENSIONS`, `REMEDIATION_HINT`).

## [0.32.0] - unreleased

No public-API change recorded for this version.

## [0.31.0] - unreleased

Public-API surface changes since 0.29.0 (mechanical semver via REL001): an
additive (minor) bump -- new optional parameters and new public functions,
no removal or signature-breaking change to any existing caller.

- T-0398: evidence-integrity fix for the audit's central North-Star hole
  (docs/audits/tickets-testing.md D-01..D-12) -- close/land previously
  meant only "a test with this name exists in collection," not "the work
  was actually tested, covers the ticket, and passed." `add_evidence`
  gained `passed` (D-01: a collected-but-currently-failing test is
  rejected, `EvidenceNotPassing`), `transition`/`land` gained
  `covers_scope` (D-02: evidence that binds to none of the ticket's
  touched/scope symbols is rejected, `EvidenceScopeUnbound`, via new
  `frob.gates.evidence_covers_scope`), `land` gained `collected`/`passed`/
  `covers_scope` callables for post-merge re-verification (D-05), a Done
  report must carry real content under its heading (D-03), an unknown-
  language file change no longer silently selects zero tests (D-04), a
  module-level edit forces selection even under `fallback="warn"` (D-06),
  the `uses-contract` ripple horizon widened from one hop to a bounded
  BFS (D-07), a splice union's evidence instead of dropping one side's
  (D-09), and a new `reverify_cmd_evidence` re-checks a `cmd:` evidence
  entry's reproducibility on demand (D-10). The real `frob ticket
  evidence`/`close`/`land` CLI commands (`ticket_runner.py`) now compute
  and supply these by default -- the library functions themselves keep a
  permissive `None` default for backward compatibility, but the CLI's
  default path is the strict one.

## [0.29.0] - unreleased

Public-API surface changes since 0.28.0 (mechanical semver via REL001): a
minor bump -- the public surface SHRANK (a compatible reduction of
internal-only names, not a breaking change to any documented API).

- T-0369: 73 genuinely package-internal helpers (0-1 intra-package
  consumer, never imported cross-package) were demoted to private
  (`name` -> `_name`) across `dup`, `gates`, `graph`, `lang`, `logging`,
  `strata`, `tickets`, and `vet`, with every in-repo reference and
  `frob:doc`/`frob:describes` anchor updated in lockstep. This completes
  the T-0362 export-or-demote pass: the public surface of each package is
  now exactly its intended API, and `frob-exports` reports zero
  unaccounted-for public symbols outside test packages.
- T-0359/0360/0370/0372: the arch analyzer's advisory categories are now
  materially more precise (test-file/data-file exemption, dispatch-family
  recognition, abstraction-opportunity gated on body-similarity or
  signature-specificity) -- no public API change, noted here for the
  release narrative.

## [0.28.0] - unreleased

Public-API surface changes since 0.27.0 (mechanical semver via REL001): an
additive (minor) bump.

- T-0362: export-or-demote pass over every package `__init__.py`. Error
  classes callers catch are now re-exported from their package roots
  (`frob.gitio.GitError`, `frob.gates.decisions.DecisionError`,
  `frob.graph.lock.LockError`, `frob.scaffold.project.ScaffoldError`),
  alongside the `app.*_runner.run` entry points and `app._style` helpers.
  The `frob-exports` checker no longer flags pytest symbols in `tests/`
  packages (they were never meant to be package exports). 74 true-internal
  helpers deferred to T-0369; two console-script entrypoints reason-noted.
- T-0359: `frob.excludes.is_test_file` -- the single shared test-file
  predicate -- is now public; three drifted private copies (in `gates`,
  `arch`, `testing`) were collapsed into it, and it recognizes TS/JS
  `*.test.*` naming the Python-only copies missed. Test files are now
  exempt from the arch advisory categories (long-function, god-class,
  abstraction-opportunity).
- T-0360: the arch abstraction-opportunity detector recognizes intentional
  dispatch/validator families (via tree-sitter structural references) and
  no longer flags them; internal `_collect_file_dispatch_refs` is private.

## [0.27.0] - unreleased

Public-API surface changes since 0.26.0 (mechanical semver via REL001): an
additive (minor) bump.

- T-0353: disposition of frob's own PII010/SEC110 findings. The over-broad
  `fingerprint` biometric field signature is narrowed to genuine biometric
  field names (`fingerprint_scan`/`fingerprint_template`); SEC110 gains a
  known-non-secret env-var allowlist (DISPLAY/TERM/PATH/PYO3_PYTHON/...) that
  does not fire; the true residue (passwd-audit metadata, tooling env reads)
  carries honest per-site `frob:waive` reasons. `frob check --only
  pii_structural` on frob's own tree is now 0/0.

## [0.26.0] - unreleased

Public-API surface changes since 0.25.0 (mechanical semver via REL001): an
additive (minor) bump.

- T-0207: structural PII/secrets detection. New `frob.gates._pii_structural`
  gate with `PII010` (a data-structure/schema FIELD whose name matches a
  PII/credential signature -- drawn from the secrets+PII corpus's
  `FIELD_SIGNATURES`) and `SEC110` (an `os.environ` read is a secret-source
  observation to map to a declared std.secrets node or waive). Both waivable
  with a reason, per the anti-evasion bounded-escape-hatch rule.

## [0.25.0] - unreleased

Public-API surface changes since 0.24.0 (mechanical semver via REL001): an
additive (minor) bump.

- T-0248: stale native-extension detection. New `frob.strata._native_staleness`
  (`stale_natives`, `stale_native_warning`, `check_native_staleness_or_exit`,
  `StaleNative`, `NATIVE_SOURCE_DIRS`) compares each `[[native]]`'s source dir
  mtime against its built artifact (reusing the T-0333 fingerprint), so a
  grammar-affecting change that left the native unrebuilt is caught: `make
  check` fails loudly, and `frob ticket land` warns pre-commit.

## [0.24.0] - unreleased

Public-API surface changes since 0.23.0 (mechanical semver via REL001): an
additive (minor) bump.

- T-0232: per-gate timing attribution corrected (measured via
  `time.thread_time()` per job instead of wall-clock, so GIL contention no
  longer smears every gate's cost toward the slowest), and `.frob` db read
  contention removed -- new `frob.graph.cache.connect_readonly` lets pure
  readers (`load_graph`) open the cache without taking sqlite's write lock,
  and `_apply_schema` no-ops when the schema is already current.

## [0.23.0] - unreleased

Public-API surface changes since 0.22.0 (mechanical semver via REL001): an
additive (minor) bump.

- T-0241: ticket scope parsing fixed. New `frob.tickets.scope_matches` is the
  single shared scope matcher -- splits comma-joined scope entries, expands a
  bare `dir/` prefix to `dir/**`, and always treats `tickets.md` as implicitly
  in scope; every fnmatch call site (land + the scope gates) now delegates to
  it, and `Ticket`/`TicketSpec` normalize comma-joined scope at construction.

## [0.22.0] - unreleased

Public-API surface changes since 0.21.0 (mechanical semver via REL001): an
additive (minor) bump.

- T-0244: embedded-code blind spot closed. The capability scanner now
  detects HTML/JS embedded in python string literals (`_embedded_code_regions`)
  and, per the anti-evasion fail-closed rule, always emits a new
  `embedded_code` capability kind for a detected region (best-effort
  needle re-scan on top), so dangerous embedded code can no longer hide
  from the scan. `embedded_code` added to `CAPABILITY_KINDS` with per-language
  matrix excuses.

## [0.21.0] - unreleased

Public-API surface changes since 0.20.0 (mechanical semver via REL001): an
additive (minor) bump.

- T-0247: the strata store grammar gains four `node_prop` productions --
  `on-deploy`, `observe`, `errors_total`, `panics_contained_by` -- so a
  `store` node can carry the same deploy/observability obligations other
  nodes already do. `StoreDecl` gains the four fields; elaboration and the
  observability validators now walk `module.stores`.

## [0.20.0] - unreleased

Public-API surface changes since 0.19.0 (mechanical semver via REL001): an
additive (minor) bump.

- T-0180: closed-world unknown-import accounting (T-0158 addendum 2
  remainder). New `frob.vet` module `_closedworld` with `ImportResolution`
  / `ClosedWorldAccounting` models: walks a project's absolute imports,
  resolves each against the capability registry / vetted-library cache /
  local-source scan, and reports the residue of genuinely-unknown imports
  as a closed-world accounting.

## [0.19.0] - unreleased

Public-API surface changes since 0.18.0 (mechanical semver via REL001): an
additive (minor) bump.

- T-0236: `frob ticket land` now refreshes the pre-work sweep post-merge,
  pre-close, so PRE001 stops re-firing stale sweep findings after a land in
  the multi-agent loop. New `frob.gates.sweep_ticket(root, ticket)` (the
  single dup+xref+digest sweep-computation function).

## [0.18.0] - unreleased

Public-API surface changes since 0.17.0 (mechanical semver via REL001).

- T-0171: THREAT002 no longer fires in quality views for a capability that
  IS classified, just in a different family's catalog (e.g. a security-only
  `exec`/`html_render`). New `frob.strata.ALL_CATALOG` (the union sink
  taxonomy across every family catalog) and a `taxonomy=` parameter on
  `check_capability_completeness` (defaults to the per-family `catalog`, so
  single-family callers are unchanged); the exhaustiveness sweep classifies
  against the union while still scoping obligations per family.

## [0.17.0] - unreleased

Public-API surface changes since 0.16.0 (mechanical semver via REL001): an
additive (minor) bump.

- T-0234: generated-file marker respected by the coverage gate.
  `frob.graph._generated.is_generated_source` + `GENERATED_MARKER_RE`
  detect a generated-by/`@generated`/`DO NOT EDIT` header in a file's first
  lines; COV001 then exempts such files from the frob:doc obligation
  (nobody hand-documents generated code). The file stays fully in the graph
  (xref/dup/arch still see it) -- only the documentation obligation is
  waived, deliberately distinct from `[graph] exclude`.

## [0.16.0] - unreleased

Public-API surface changes since 0.15.0 (mechanical semver via REL001): in
0.x a breaking change bumps the minor (semver section 4).

- T-0233: a broken `frob:doc` target no longer suppresses other coverage
  findings on the same file. `_cov001` now counts a symbol documented only
  when its `frob:doc` edge actually RESOLVES (reusing DOC002's resolution
  logic), so a dangling doc anchor is reported as its own DOC002 error
  without masking the real COV001 gap. `coverage_gate`/`_cov001` gained a
  `root: Path` parameter (the breaking change driving this bump).

## [0.15.0] - unreleased

Public-API surface changes since 0.14.0 (mechanical semver via REL001): an
additive (minor) bump.

- T-0170: `kotlin` capability-scanner column for Android nodes. Added as a
  fully registry-backed language (`_capability_registry.LANGUAGES` +
  `DANGEROUS_OPERATIONS` net/exec/client_storage rows + `MatrixExcuse`
  entries for its unpatterned cells), so the T-0169 language-coverage
  drift-lock stays strict equality with no carve-out. `.kt`/`.kts` files
  now scan for net/exec/client-storage capabilities.

## [0.14.0] - unreleased

Public-API surface changes since 0.13.0 (mechanical semver via REL001): an
additive (minor) bump.

- T-0188: `CWE-295` (Improper Certificate Validation) `WeaknessEntry` added
  to `QUALITY_CATALOG`, plus three `std.cve` fingerprints (FP-TLS-VERIFY-001/
  002/003) for TLS certificate-verification bypass across Python
  (`verify=False`), TypeScript/Node (`rejectUnauthorized: false`), and Rust
  (`danger_accept_invalid_certs(true)`), each cited by a real CVE.
- T-0189: `CWE-611` (XML External Entity) `WeaknessEntry` added to
  `CWE_CATALOG`, plus the `FP-XXE-PARSE-001` fingerprint (Python
  `resolve_entities=True` / `xml.sax.make_parser`), cited by CVE-2013-1665.

## [0.13.0] - unreleased

Public-API surface changes since 0.12.0 (mechanical semver via REL001): an
additive (minor) bump.

- T-0333: native-extension-aware test collection. `frob.testing.NativeSpec`
  + `load_natives` parse a new `frob.toml` `[[native]]` table; the pytest
  collection cache key now folds in a fingerprint over each declared
  native's compiled artifacts (`.so`/`.pyd`/`.dylib`), so building or
  rebuilding a native (`make core`) invalidates the cache automatically
  instead of leaving a stale set that reds COV003. COV003 now names an
  unbuilt native and its build command (via `CollectedTests.missing_natives`)
  instead of pointing at a nonexistent flag; `frob test --collect`
  (`drop_collection_cache`) is the explicit cache-refresh escape hatch.
  Toolchain/platform-agnostic (maturin/pyo3 and setuptools/pybind11 alike;
  Linux/macOS/Windows, x86/arm).

## [0.11.0] - unreleased

Public-API surface changes since 0.10.0 (mechanical semver via REL001). Per
semver section 4, breaking changes while in 0.x bump the MINOR (0.10 -> 0.11),
not to 1.0.0 -- REL001 now enforces this (a breaking change no longer forces
a premature 1.0.0).

- T-0288: `frob.graph.callgraph` (`CallGraph`, `build_call_graph`,
  `closure`) -- a shared interprocedural call-graph substrate; dup's
  `find_clones` now inlines bounded PRIVATE-helper call closures before
  fingerprinting (`DupConfig.inline_calls`/`inline_max_depth`/
  `inline_max_nodes`), plus a dedicated `find_helper_clones` population
  pass (`DupConfig.helper_min_tokens`) for over-split tiny-helper families.
- T-0222: `ffi` capability needle for compiled-extension imports
  (`importlib.machinery.ExtensionFileLoader`).
- T-0289: complexity-aware long-function arch rule + `arch_gate`/ARCH001
  reasoned per-function override.
- T-0195: dup template report (`build_group_template`, `CloneTemplate`,
  `CloneBinding`, `CloneMatchGroup`); `CloneReport.groups` retyped.
- T-0179: `frob.app._style` CLI-presentation helpers (private module).
- release: `required_version` -- a breaking change in 0.x bumps the minor,
  not the major (semver section 4).

## [0.10.0] - unreleased

Public-API surface changes since 0.9.0 (mechanical semver via REL001):

- T-0194: anti-unification kernel (Plotkin least-general-generalization)
  over the `(labels, parents)` node-array representation
  `apted_similarity` already consumes -- the foundation of the dup-engine
  reverse-templating chain (T-0195 template report, T-0287
  type-generalization). New `frob-core/src/lib.rs::anti_unify`: a
  lockstep top-down walk emitting shared nodes where two trees agree and
  a fresh `$hole_N` at each divergence (label mismatch or arity
  mismatch), never recursing into a hole's diverging subtrees.
  Deterministic left-to-right/top-down hole numbering. HOLE-CEILING
  sanity: a template that is >50% holes carries no real generalization
  value, so the kernel returns a false-ok sentinel (never raises across
  the PyO3 boundary) that the Python shim turns into
  `Err(DupError.HoleCeilingExceeded)`, letting the caller fall back to a
  plain (non-generalized) clone pair. New Python surface:
  `frob.dup._core.anti_unify`, `frob.dup.AntiUnifyTemplate` (frozen
  pydantic model: `labels`, `parents`, `bindings_a`, `bindings_b`), and
  `DupError.HoleCeilingExceeded`, all re-exported from `frob.dup`.

## [0.9.0] - unreleased

Public-API surface changes since 0.8.0 (mechanical semver via REL001):

- T-0262: `std.krb` -- Kerberos/AD domain trust, SPNs, and delegation as
  first-class strata (deploy epic T-0254's auth pillar, built on T-0255's
  `HostManifest`/`runs_as`). New grammar (`strata-core/src/parse.rs`):
  node clauses `realm "NAME"`, `kdc`, `spn "SPN"`+, `delegation
  none|constrained|rbcd|unconstrained [target "SPN"]*`, `trusts IDENT
  [direction "one-way"|"two-way"] [transitive]`+, and a flow clause
  `authenticates_via tgt|st`. New `frob.strata._krb` (pure, fully unit-
  and litmus-tested): `KrbManifest`, `KrbDelegationKind`, `KrbTrust`,
  `krb_attrs`, `krb_manifest_for`, `krb_trust_flows`,
  `flow_authenticates_via`. New `frob.strata._ast.KrbTrustDecl`. Domain
  trusts desugar to a synthesized `Flow` at elaboration time
  (`_elaborate.py::_elaborate_module`) so the existing reach/noflow
  closure model-checks cross-realm reachability with no new kernel
  primitive (charter law 1). MODEL + VOCABULARY ONLY: delegation-abuse
  obligations are T-0263, out of scope here. tmLanguage grammar synced
  (`editors/vscode-strata/syntaxes/strata.tmLanguage.json`);
  `docs/strata/krb.md` documents the vocabulary and its scope cuts (no
  store-level clauses, no generator).

## [0.8.0] - unreleased

Public-API surface changes since 0.7.0 (mechanical semver via REL001):

- T-0259: `frob deploy audit --vm <name>` -- VirtualBox snapshot-diff
  harness proving artifact-free install/uninstall against a live guest
  (deploy epic T-0254 child 5, NOT run by `frob check`/`make check`).
  New `frob.deploy._audit` (pure, fully unit-tested): `StateCapture`,
  `FileFact`, `StateDiff`, `diff_states`, `idempotence_holds`,
  `artifact_freeness_holds`, `install_exactness_holds`,
  `assert_not_installed`, `assert_healthy`, `CheckpointResult`,
  `AuditAttestation`, `build_attestation`, `ALLOWLIST_PATTERNS` -- the
  four proofs (idempotence, artifact-freeness, install-exactness, and
  the per-checkpoint `status.sh` health assertions) plus attestation
  JSON. New `frob.deploy._vm_runner` (the one VM-gated, untested-in-CI
  sliver, deliberately kept thin): `VmAuditConfig`, `AuditRunResult`,
  `run_vm_audit`, `vboxmanage_available` -- drives restore-snapshot ->
  CHECK C0 -> install -> CHECK C1 -> install again -> CHECK C1' ->
  uninstall -> CHECK C2, and degrades to a clear `status="skipped"`
  (never a fabricated pass) when `VBoxManage` is not on `PATH`. New
  `frob deploy audit` CLI verb (`src/frob/app/deploy_runner.py`,
  `src/frob/__main__.py`) and `make deploy-audit` Makefile target.

## [0.7.0] - unreleased

Public-API surface changes since 0.6.0 (mechanical semver via REL001):

- T-0258: `frob deploy`'s bidirectional conformance check -- new
  `frob.deploy.deploy_conformance_violations`, `ConformanceViolation`,
  `extract_mutation_surface`, `expected_mutation_surface`,
  `MutationTarget` (`_conform.py`): structured extraction of committed
  `deploy/install.sh`/`uninstall.sh`'s actual mutation surface
  (`useradd`/`groupadd`/`userdel`/`groupdel`/`mkdir`/`install`/`cp`/
  `chown`/`chmod`/`rm -f`/`rm -rf`/`systemctl enable|disable|start|
  stop`/unit-heredoc writes), compared bidirectionally against the
  current `HostManifest` set as `DEPLOY002` (script mutation not
  declared in the manifest) and `DEPLOY003` (manifest entry no
  mutation implements), wired into `frob check` as an extra
  `deploy-conformance` stage alongside `DEPLOY001`.

## [0.6.0] - unreleased

Public-API surface changes since 0.5.0 (mechanical semver via REL001):

- T-0257: `frob deploy generate` -- new `frob.deploy` package
  (`generate_all`, `generate_install_script`, `generate_status_script`,
  `generate_uninstall_script`, `manifest_digest`,
  `sorted_manifest_entries`, `deploy_drift_violations`,
  `DeployDriftViolation`, `ManifestEntry`) compiling `std.host`
  `HostManifest` facts (T-0255) into idempotent Linux/systemd
  install/status/uninstall bash, plus the `DEPLOY001` drift check
  (wired into `frob check` as an extra `deploy-drift` stage) and the
  `frob deploy generate [--check] [--out-dir]` CLI verb. Also adds
  `frob.strata.node_allowed_syscalls`/`node_may_kinds` (public exports
  of previously-private `_export.py`/`_effects.py` helpers, reused by
  the new generator for `SystemCallFilter=`/`CapabilityBoundingSet=` so
  neither mapping is duplicated).

## [0.5.0] - unreleased

Public-API surface changes since 0.4.0 (mechanical semver via REL001):

- T-0193: R1.5 exact-region dup kernel -- new public `frob_core.exact_regions`
  (generalized suffix array + LCP over a normalized token corpus) and
  `frob.dup._core.exact_regions`; `DupConfig` gained `region_kernel_enabled`
  and `region_min_tokens` fields (`[dup].region_kernel`/`region_min_tokens`
  in frob.toml). Off by default, independent of `[dup].enforce`.

## [0.4.0] - unreleased

Public-API surface changes since 0.2.0 (mechanical semver via REL001):

- T-0212: new public `frob.graph.dedupe_slug`; GitHub-compatible anchor slugger.
- T-0253: `frob.vet.is_self_pattern_path` gained a `root` param (scan-target
  discriminator closing a capability-scan evasion hole).
- T-0209: `frob.lang.COMMENT_TYPES` made public (capability scanner drops
  needle hits inside comment spans).
- T-0231: `frob --version` prints the installed package version instead of
  an argparse error; `frob sys plan` (no `--apply`) labels its output
  "DRY RUN (no tickets created; pass --apply to compile)"; DOC001's orphan
  hint resolves an actually-existing configured docs root instead of
  blindly naming `docs/index.md` in repos that never created one.
- T-0255: new public `frob.strata` std.host manifest symbols
  (`HostManifest`/`HostOwns`/`HostPlatform`/`host_manifest_for`/`OwnsDecl`).
- T-0256: new public `frob.strata` movement-impossibility symbols --
  `HostIsolationViolation`, `evaluate_lateral_isolation` (HOST001),
  `evaluate_vertical_isolation` (HOST002), `evaluate_host_isolation_waived`,
  `HOST_MULTI_INSTANCE_WAIVER_FAMILIES`, `COMPROMISED_OWNER_CATALOG`,
  `COMPROMISED_OWNER_OUT_OF_SCOPE`, `COMPROMISED_OWNER_VIEWS`,
  `host_movement_flows`, `AddFlow` (new `Rewrite` variant), and
  `build_compromised_user_scenario` (the compromised-service-owner
  red-team scenario builder; its blast-radius `NoFlow` claims are proved
  over the declared-flow graph PLUS `host_movement_flows`'s
  HostManifest-derived filesystem/socket sharing edges, closing a
  review-round vacuity gap where a shared writable path with no declared
  app `Flow` would otherwise vacuously prove the claim).

## [0.2.0] - unreleased

Ticket list frozen at the T-0156 landing commit; T-0174 (sys-audit waiver
channel) and T-0208 (vet obfuscation-scan performance) closed during the
final review rounds and are included below. Tickets closed after this
landing appear in the next release's section.

### strata (design-language kernel, prover, policy, self-conformance)

- T-0174: waive clause for sys-audit findings: RULE:SUBTARGET specificity,
  mandatory reasons, stale-waiver drift-lock, PROVED-(N-waived) reporting

- T-0047: strata: provable system-design language (epic)
- T-0048: strata charter + design doc tree under docs/strata/
- T-0049: strata phase 0: kernel + prover core
- T-0050: strata phase 1: surface language v0 + std.trust + refinement
- T-0051: strata phase 2: std.infra + bounds + policy forms + boundaries
- T-0052: strata phase 3: scenarios, crash contracts, atomicity
- T-0053: strata phase 4: code binding (tier 2) + self-hosting
- T-0054: strata phase 5: std.secrets, std.deploy, work-order compiler, exporters
- T-0055: strata kernel data model: Node/Flow/Boundary/Bound/Claim/Scenario
- T-0056: strata fact base + semi-naive Datalog closure engine
- T-0057: strata claim evaluation: noflow/bound/reach with counterexample traces
- T-0058: strata payments litmus as kernel facts + golden findings
- T-0059: strata lexer + recursive-descent parser (pydantic AST, Result diagnostics)
- T-0060: strata elaborator framework + std.trust vocabulary
- T-0061: strata assert/assume: owner, expiry, verdict report
- T-0062: strata refinement: abstract components, refine blocks, faithfulness
- T-0063: strata payments litmus in surface syntax + CI goldens
- T-0064: strata std.infra: store/cache/queue/cdn/balancer elaboration
- T-0065: strata age/staleness propagation (TTL = rotation = RPO = expiry)
- T-0066: strata capacity arithmetic: utilization, fanout, skew, growth horizons
- T-0067: strata policy sublanguage: 5 forms, semantic scoping, tree-sitter compilation
- T-0068: strata std.policy.analyzable base pack + enables soundness cascade
- T-0069: strata six-phase boundaries + outcome-conditioned frames
- T-0070: strata errors-total, panics-contained, observe blocks (ERR/OBS gates)
- T-0071: strata-core: independent Rust/PyO3 kernel crate (closure + propagation)
- T-0072: strata tube + chirp litmus models + goldens
- T-0073: strata scenario engine: node loss, rate surge, trust downgrade
- T-0074: strata crash contracts: on-crash, no-hang check, crash-retry-idempotency join
- T-0075: strata atomic/saga: cross-store refusal + fault-injection generation
- T-0076: strata breach scenarios: blast radius + recovery-path independence
- T-0077: strata as 6th frob.lang grammar: design constructs become graph symbols
- T-0078: strata code binding: code globs + import-level conformance
- T-0079: strata effect extraction: net/fs/exec facts vs may-capabilities
- T-0080: strata directives (frob:channel/boundary/secret) + SYS gates in run_gates
- T-0081: strata self-hosting: design/frob.strata models frob itself
- T-0082: strata std.secrets: credentials as cache-of-authority
- T-0083: strata std.deploy: endorsement pipeline, canary schedules, rollback budgets
- T-0084: strata frob sys plan: obligation -> ticket compiler
- T-0085: strata frob sys doc + DOC002 claims audit
- T-0086: strata exporters: k8s netpol / seccomp / IAM from the model
- T-0093: strata grammar: explicit trust clause for queue/balancer
- T-0099: document demand() behavior shift for unresolvable rates (propagates vs drops)
- T-0103: std.infra drops declared store capacity (UTILIZATION can never target a store)
- T-0109: strata obligation catalog: CWE/CVE + quality anti-pattern auditing (epic)
- T-0110: threat D: NVD CVE->CWE ingestion into vet + containment report
- T-0111: threat A: std.cwe catalog + weakness/capability grammar + THREAT001/003
- T-0112: threat B: capability->obligation instantiation + THREAT002 precondition completeness
- T-0113: threat C: CWE-sink effect extraction + mitigation chokepoint verification
- T-0114: threat E: std.perf/reliability/compat anti-pattern families
- T-0115: threat F: frob sys audit exhaustiveness matrix + DOC002 + vuln litmus
- T-0116: threat G: std.compliance -- COPPA/GDPR/HIPAA + privacy-policy-as-claims
- T-0132: strata surface grammar: code=<glob>/may <capability> unreachable from .strata source text
- T-0134: frob.strata._facts hard 'import strata_core' crashes standalone installs with a design/ dir (found while working T-0133)
- T-0136: strata surface grammar: on deploy / secret constructs unreachable from .strata source text
- T-0138: strata claim ids cannot carry ':' or '-' -- discharge claims unauthorable from .strata source
- T-0139: editor syntax highlighting for .strata (VSCode + JetBrains via one TextMate grammar)
- T-0144: pytest --collect-only hard-fails repo-wide when strata_core native ext is absent, blocking frob ticket evidence for any ticket
- T-0145: per-CWE litmus fixtures: every catalog weakness fires from real .strata source
- T-0148: drive frob check gates to zero violations
- T-0150: self-conformance: vet capability scan of our own source must match design/frob.strata interfaces
- T-0151: vet capability scanner self-matches its own pattern-table literals
- T-0153: std.cve fingerprints: pattern catalog for known vulnerable-usage classes
- T-0154: PII declarations: first-class personal-data modeling and flow proofs in strata
- T-0155: design lint family: caching, resource bounds, rate-limiting, kill-switch rules over the kernel model
- T-0158: capability exhaustiveness matrix: every reserved kind provably detected in every supported language
- T-0164: COV002 demands per-declaration frob:ticket edges inside .strata files -- boilerplate x28
- T-0166: store grammar rejects code/may despite surface.md implying support
- T-0168: TEST001 fires on flow declarations in .strata files -- undefined semantics
- T-0169: capability conformance did not scan TS/JS in the logand.app pilot -- verify per-language wiring
- T-0172: managed marker for config-only infra nodes promised in surface.md but unimplemented
- T-0201: selfconform self-match: pattern-catalog data files observed as live capabilities -- main red

### check / gates

- T-0015: Implement per-rule severity overrides in frob.toml (gates currently hardcodes severity in code)
- T-0021: frob.perf: profiling, heat-maps, PERF linear-scan rules (docs/modules/perf.md)
- T-0022: Polyglot monorepo check: per-subtree stage detection, frob.toml [check] scoping, TypeScript stage (tsc/eslint)
- T-0031: Single-file tickets.md ledger + scope-based COV002 (reduce ticket/annotation spam)
- T-0035: REL001 release gate: mechanical semver from public-API digests
- T-0037: Smart-dup: frob-core Rust kernels + DUP gate + build wiring
- T-0038: ADR decision records: frob:decision edges + DEC gates
- T-0039: Convention-based unit-test binding inference (reduce frob:tests burden)
- T-0042: TEST007: pair-level integration obligations from uses-contract edges
- T-0090: TEST002 misses frob:tests directives bound cross-file to rust symbols
- T-0092: rust test integration: [[test.runner]] for cargo + COV003 evidence resolution
- T-0095: frob check --delta: report only violations new since a stamped baseline
- T-0101: extend frob:waive to arch/perf tool channels or document the boundary
- T-0102: frob check must FAIL, not silently pass, when the ticket queue fails to load
- T-0106: Wire frob ticket new/close --evidence to tickets.add_evidence
- T-0107: Wire frob check --stamp-baseline/--delta CLI flags and docs
- T-0108: SCOPE001 flags files already committed by earlier tickets on the same branch
- T-0122: frob check races concurrent build_graph calls against shared .frob/cache.db
- T-0124: frob check --ticket exits 1 with no diagnostic output (repro on closed T-0075)
- T-0125: frob.logging.quiet_stdout_logs is not thread-safe; races across concurrent frob.arch/frob.dup calls
- T-0135: sys_gate imports frob.strata (and its unguarded strata_core dep) before the design/ opt-in check -- crashes frob check on ANY repo in a standalone install (supersedes/extends T-0134)
- T-0142: standalone frob check crashes FileNotFoundError when ruff/ty binaries absent -- wheel declares no tool deps
- T-0157: secrets-scan gate: real-looking API tokens in tracked files fail check unless marked fake
- T-0162: make ticket-id collision structurally impossible across checkouts and worktrees
- T-0165: DOC002 anchor errors: report the computed slug and suggest nearest valid anchor
- T-0202: frob check default output: stats summary, gate chatter to DEBUG, standardized log format
- T-0203: perf_gate: silence UnsupportedLanguage skips for non-code files
- T-0205: pytest collects Test*-prefixed product classes -- set __test__ = False
- T-0215: non-pytest evidence channel for docs/design tickets + close-from-queued hint

### tickets (queue, evidence, worktree/ledger safety)

- T-0032: Ticket schema: incident kind, acceptance, STRIDE threat, renumber
- T-0043: Migrate arch + dup/_legacy off frob.ast, then delete frob.ast
- T-0088: reorganize flat docs/ into guides/ modules/ commands/ hierarchy
- T-0094: frob ticket evidence subcommand: append structured evidence ids from the CLI
- T-0096: frob ticket archive: rotate done tickets out of the active ledger
- T-0097: README banner with goblin mascot (aviator cap, crystal ball of rune-code)
- T-0098: frob ticket attach without path should error usefully outside a TTY
- T-0117: fresh frob_core rebuild fails TestR5Dataflow::test_no_false_positive_against_unrelated_function
- T-0126: annotate newly-extracted module constants with frob:doc edges (COV001 x21)
- T-0128: extend rust [[test.runner]] coverage to frob-core (second PyO3 crate)
- T-0130: design/litmus strata symbols: exclude from doc/test obligations
- T-0137: frob test --base main mixes touched non-test source symbols into pytest argv
- T-0140: ticket id allocator ignores tickets-archive.md -- new ids collide with archived tickets
- T-0141: cache corrupt-recovery crashes on Python 3.12 sqlite: DROP TABLE raises before rebuild
- T-0149: frob test: no [[test.runner]] for language=strata blocks touched-set selection on .strata fixtures
- T-0152: packaging is an undeclared runtime dependency -- bare frob install crashes on import
- T-0159: extending frob: developer guides for every registry and extension point
- T-0163: frob sys audit <file> appends bogus path segment instead of erroring
- T-0167: frob sys --help: add example invocations and directory-root convention
- T-0175: agent playbook in-repo: kill per-dispatch retreading
- T-0176: frob ticket land: one-command landing (merge-check-splice-close-commit)
- T-0184: frob ticket close prints ERROR MissingEvidence but exits 0
- T-0185: exhaustive-research agent: frontier-loop with external graph-knowledge store
- T-0186: link docs/guides/exhaustive-research.md from docs/index.md
- T-0227: gitio treats untracked gitlink/directory as file (Errno 21 warning spam)

### dup (clone detection, frob-core)

- T-0001: frob-core PyO3/maturin crate + smart dup (Phase 7)
- T-0016: Re-platform map/outline/xref/cycle/dup onto frob.lang; delete frob.ast
- T-0026: Unify exclude surface: dup/arch/cycle scanners must respect [graph] exclude
- T-0041: dup follow-on: --probe CLI, full APTED, real CFG/DFG

### vet (dependency vetting)

- T-0034: Wire fuzz+vet: FUZZ gate, frob test --fuzz, capability scan merge, gates degrade without diff
- T-0208: obfuscation scan rewritten single-pass (~100x on pathological files),
  per-package progress, honest per-package timeout verdicts
- T-0181: survey-prioritized third-party python/npm/cargo dangerous-surface registry entries (T-0158 addendum 2 remainder)

### threat / CVE / compliance

- T-0146: cvelistV5 record parser: pydantic models for CVE Record Format v5
- T-0147: frob vet: match dependencies against a local cvelistV5 mirror, link CVEs to the threat catalog

### docs

- T-0010: frob serve: MCP adapter over stale_docs/doable_tickets/check_scope/pre_work
- T-0025: Colors, frob.toml check config, DOC001, overload fix, log dedup
- T-0028: frob check red at HEAD: 16 orphan docs (DOC001) and ruff-format drift in 9 files
- T-0036: frob stats: DORA-ish delivery measurement (queue health + commit cadence)
- T-0040: frob mutate: mutation testing quality oracle
- T-0161: PERF001-004 lexical heuristic: false-positive classes need real fixes, not permanent waivers

### other

- T-0019: cache.connect does not recover from a non-sqlite-file corrupt cache.db
- T-0020: Gate convergence: collection oracle, evidence matching, fixture excludes
- T-0024: graph: @overload chains crash build_graph (UNIQUE symref); dedupe last-def-wins
- T-0027: perf: cProfile masks workload exit code; profile_command cannot detect failed runs
- T-0029: graph: concurrent build_graph on shared cache.db raises disk I/O error; add busy_timeout
- T-0030: ticket new --origin flag
- T-0044: Comment binder: directive above nested method binds to enclosing class
- T-0045: perf: split heat/profile long functions and clear PERF-rule self-flags
- T-0046: Refactor: clear perf/arch/test warnings in app,process,serve,testing,map,outline,xref,cycle,gitlog,policy
- T-0087: python CONST extraction misses call-expression assignments (X = Foo(...))
- T-0089: test_scaffold_dx flaky under full-suite run, passes in isolation
- T-0091: make core creates a stray venv under strata-core/, contaminating the editable install
- T-0100: frob:tests directives silently degrade when stacked 3+ or separated from def
- T-0119: perf: split long functions in app/perf_runner.py (_heat_body, _annotate)
- T-0120: perf: split long test in tests/system/test_cli_perf.py
- T-0123: register pytest 'slow' marker in pyproject.toml
- T-0127: DOC002-style gate: validate frob:doc anchors resolve to real doc slugs
- T-0129: wire .strata into frob.graph/outline/xref/testing/policy/cycle scanners
- T-0131: frob ticket resolves repo root to main checkout from inside a linked worktree (first invocation)
- T-0133: standalone tool install crashes: strata_core hard import in frob.lang (hotfixed); bundle or degrade natives properly
- T-0143: std.cwe catalog: transcribe the cwe-top-25 view (and stub-free ASVS decision)
- T-0182: per-operation fire+negative fixture parametrization for the full DANGEROUS_OPERATIONS table (T-0158 deliverable 3 remainder)

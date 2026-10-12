# frob v1 ticket subsystem -- inventory for the Rust redesign

Source of truth: <frob-v1> (read-only). ASCII only. No code pastes; names are
quoted only where load-bearing. T-#### cites are v1 ticket ids that carry the incident or decision
(look them up in <frob-v1>/tickets/T-####/ticket.md).

## 0. Honest scope statement (denominator and what was NOT read)

| Item | Count / status |
|---|---|
| Python files in src/frob/tickets/ | 56 files, 52,466 lines (largest: _land.py 8.6k, _leases.py 4.7k, _models.py 3.7k, _evidence.py 2.8k, _land_git_ops.py 2.5k, _land_squash.py 2.6k, _store.py 2.5k) |
| CLI package src/frob/app/ticket_runner/ | 27,751 lines (verb handlers, land CLI, ledger mirror) |
| `frob ticket` verbs (argparse) | 53 top-level + 3 `admin` subverbs; dispatch table audited at 48 keys (T-2603) |
| Tickets on disk in v1 repo | 1,245 active dirs under tickets/ (953 queued, 236 done-not-yet-archived, 37 dropped, 11 in-progress, 6 planned) + 3,906 dirs in tickets/archive/ |
| Docs read fully or section-sampled | tickets.md, tickets-data-storage.md, tickets-lifecycle.md, tickets-landing.md, tickets-merge-driver.md, tickets-verify-sweep.md, ledger-v2.md, ledger-mirror-batching.md, land-checkpoint-durability.md, land-splice-test-then-impl.md, agent-playbook.md, worktree-pool.md, coordinator-scripts.md (headings + intro), fleet.md |
| Code read directly | _models.py (all enums + Ticket + sub-records + error sets), __init__.py (state machine), _leases.py (record shape, TTL, staleness), _ledger_mirror.py (verb strategy table), _registry_files.py, _lifecycle.py (start guard chain), all `--help` output |
| NOT read in depth | _land.py / _land_squash.py / _land_git_ops.py bodies (relied on docs), _reporting.py, _token_usage.py internals, _worktree_sweep.py, _mutation_*.py, clipboard.py, agent-playbook-appendix.md, docs/guides/landing.md, docs/modules/release.md |
| Not run | `frob ticket doable` was attempted on the live repo and exceeded a 120s timeout (observed perf datapoint, not diagnosed) |

Phase-2 verdict is in section 10. Short form: data model, verbs, lease semantics, land pipeline,
mirror strategy and verify/quarantine coupling are covered at design level; land internals are
covered from docs, not from code reading.

## 1. One-paragraph model

A ticket is a markdown file with YAML frontmatter in the repo (tickets/T-####/ticket.md, plus
done-report.md, attachments/). All mutations go through `frob ticket <verb>`; hand-editing is
explicitly forbidden and policed. A ticket owns a SCOPE (file globs) which is a WRITE LEASE:
two in-progress tickets may not overlap. Work happens in a git worktree per ticket (or per
series); closing requires bound test evidence and a Done report; `frob ticket land` merges the
worktree's branch onto the primary checkout through a long chain of gates, CAS-publishes the
commit, and cleans up. The design is hostile to concurrency accidents because dozens of agents
write the ledger at once; most of the 52k lines are incident defenses.

## 2. Data model

### 2.1 Identity

| Item | Rule |
|---|---|
| Final id | `T-####` (zero-padded to 4+ digits; v1 repo is at T-6611). Allocated sequentially as max(active, archive)+1 under a lock; only on the default branch |
| Draft id | `T-draft-<8 hex>` minted by `ticket new` whenever the checkout is NOT on the default branch (every linked worktree is by definition off default). Ambiguous git state (no repo, detached HEAD) is treated as default-branch |
| Validity | `is_valid_ticket_ref` accepts exactly those two shapes; enforced for blocked_by/parent at `new` (TicketSpec) and at `block`; NOT enforced on ledger load (load stays lenient, a doctor scan flags bad edges) |
| Directory name | the id only (no slug); title lives in frontmatter so retitling never renames paths |
| Collision history | T-0157/T-0144/T-0001 reissue, T-1090 (two finalizers computing the same id), T-1179 (id claimed on main in the window a land was finalizing against a stale worktree view); drove the draft mechanism and land-time finalize |

### 2.2 Ticket fields (pydantic `Ticket`, frozen, `extra="allow"`)

Unknown keys are tolerated and preserved on rewrite (forward compat, T-0838); TICK008 WARNs on them.
Empty collection fields are omitted from the dump (T-0838) but the scalar `null` fields are written
(so a freshly written ticket.md lists ~30 keys).

| Field | Type / default | Meaning and rules |
|---|---|---|
| id | str | see 2.1 |
| title | str | free text; duplicate-title / near-duplicate refusal at filing (T-1744, `--ack-related`) |
| state | enum | 6 states, see 2.5 |
| kind | enum | feature, bug, security, ux, docs, invariant, incident. Drives evidence rules (BUG002 repro for bug/security; cmd evidence for docs/ux), land commit type (feature->feat; bug/security/ux/incident->fix; docs->docs; invariant->test) |
| origin | enum | human, agent, auditor (who filed) |
| created | date | day granularity only; the sole timestamp the model carries (state-change times are mined from git history) |
| priority | enum low/medium/high/critical, default medium | rank 0..3; first sort key within milestone; staleness alarm for critical (4h) / high (24h) via frob.toml |
| blocked_by | tuple of ids | open blockers make a ticket not doable; close refuses with open blockers (BlockerOpenAtClose) |
| parent | id or null | hierarchy edge; cycle / self / tier-inversion refused by `set-parent` |
| tier | milestone, epic, story, ticket (default ticket) | `milestone` tier added by T-5749 (model only; CLI `--tier` still lists epic/story/ticket). Only tier=ticket is ever doable; epic/story/milestone cannot close while any descendant is open |
| flavour | user_story or quality_objective or null | only legal on tier=story (validator); planned V-model binding of closers (T-5751+) |
| sprint | free string or null | a TIME BOX / overarching goal in kebab-case (T-5133); semver-shaped values REFUSED at write (`--semver-sprint-ack` overrides); `YYYY-Www` / `sprint-N` only WARN |
| milestone | semver string or null | "what ships together"; totally ordered via packaging.Version; validated at write sites, lenient on load; effective value = own, else nearest ancestor, else frob.toml [tickets].default_milestone (DECLARED / INHERITED / DEFAULTED, rendered distinctly) |
| due | date or null | calendar target; not tier-restricted; model only, setter verb not present in 53-verb list |
| rank | int or null | sibling ordering hint under one parent; non-unique by design (ties tolerated); setter verb not present |
| points | int or null | Fibonacci 1,2,3,5,8,13 only; `new` WARNs when omitted; `start` refuses unsized when `ticket_points_required` (pyproject key, on in the v1 repo) unless `--unsized-ack REASON` |
| unsized_ack, unsized_ack_reason | bool, str | override record for the points refusal |
| runs_last | bool | structurally undoable while ANY other non-runs-last ticket is non-terminal (dynamic, unlike blocked_by); siblings order among themselves via blocked_by |
| runs_last_parallel_safe (+_reason) | bool, str | MILE004 escape: BOTH tickets of an unordered runs-last pair in one milestone must declare it |
| tokens_in/out/cache_read | int or null | manual measured spend (`frob ticket tokens`); null means unmeasured, never 0 |
| usage | TicketUsage or null | automatic token accounting mined from agent transcript JSONL (T-5137): input/output/cache_creation/cache_read tokens, sessions, transcripts_seen, window_start/end, collected_at, complete flag |
| worktree, branch | str or null | stamped at first in-progress transition (durable lease record, T-5120/T-5464); TICK015 flags dead ones |
| scope | tuple of globs | the write lease; see 2.7 |
| evidence_scope | tuple of globs | paths covering only PRE-EXISTING cited evidence; counts for "evidence binds to scope" but takes no lease (T-1944); auto-populated by `evidence` |
| findings | tuple of (rule_id, file) | gate finding(s) this ticket exists to resolve; second open ticket with the same pair refused at filing, warned at start (T-2760); auto-filled by sweep-filed regression tickets |
| scope_breadth_ack (+_reason) | bool, str | acknowledges deliberately mega-glob scope (TICK009 exemption, bypasses start refusal) |
| no_scope_declared (+_reason) | bool, str | explicit "this ticket legitimately has no file scope"; `start` refuses empty scope otherwise (T-2394) |
| scope_changes | tuple of ScopeChangeEntry | append-only audit (see 2.4) |
| triage_changes | tuple of TriageChangeEntry | append-only audit of priority/kind/component/tier/milestone/sprint/parent changes |
| body_changes | tuple of BodyChangeEntry | append-only audit of `body --append/--set` |
| lease_force_releases | tuple of LeaseForceReleaseEntry | operator forced lease releases (reason, matched staleness shape, actor, date) |
| evidence | tuple of str | see 2.8 |
| kind_history | tuple of str | audit of post-hoc kind changes made after evidence/Done report existed (dodging BUG002, T-1616) |
| designated_repro_test | str or null | which evidence node BUG002 re-runs at the parent commit (T-1670); redesignation audit in designated_repro_changes |
| reviews | tuple of ReviewEntry | structured adversarial-review verdicts |
| attachments | tuple of Attachment | path, caption, sha256 |
| acceptance | tuple of AcceptanceCriterion | text + bound evidence ids; legacy plain-string lists load as unbound |
| acceptance_amendments | tuple | audit of `accept --amend/--remove` |
| evidence_changes | tuple | audit of `evidence --replace/--remove` |
| threat | STRIDE enum or null | spoofing, tampering, repudiation, info-disclosure, denial-of-service, elevation-of-privilege (kind=security) |
| component | str or null | freeform module/area (not an enum); null = uncategorized |
| labels | tuple of str | freeform tags orthogonal to component |
| anchor (+_reason) | bool, str | ticket that must NEVER reach done/dropped (permanent waiver target, e.g. WIRE001 follow_up); excluded from doable by default; land refuses (AnchorTerminalLand) |
| land_commit | sha or null | recorded for old lands and `--plan` lands; since T-3543 per-ticket lands derive it by `git log --grep "land <id> "` instead of a follow-up commit |
| body | markdown | description/plan/log sections; Done report is spliced in on read from done-report.md |

### 2.3 Enumerations (complete)

| Enum | Values |
|---|---|
| TicketState | queued, planned, in-progress, blocked, done, dropped |
| TicketKind | feature, bug, security, ux, docs, invariant, incident |
| TicketTier | milestone, epic, story, ticket |
| StoryFlavour | user_story, quality_objective |
| Priority | low, medium, high, critical |
| Origin | human, agent, auditor |
| Stride | spoofing, tampering, repudiation, info-disclosure, denial-of-service, elevation-of-privilege |
| ScopeChangeOp / AcceptanceAmendmentOp | add,remove / replace,remove |
| ReviewVerdict | approve, reject |
| ProfileName | rapid, standard, fortress (fortress parses, no behavior) |
| MilestoneSource | DECLARED, INHERITED, DEFAULTED |
| LedgerWriteStrategy | OWN_TRANSACTION, OWN_TRANSACTION_LEDGER_MIRROR, GENERIC_COMMIT_MIRRORED, GENERIC_COMMIT_UNMIRRORED, NOT_TICKET_SCOPED |
| VerifyStatus (evidence re-run) | PASSED, FAILED, UNMEASURED (T-2569; infra failure must never read as FAILED) |

### 2.4 Sub-records (all append-only, never edited)

| Record | Fields |
|---|---|
| ScopeChangeEntry | op, glob, reason, actor, at |
| TriageChangeEntry | field, old_value, new_value, reason, actor, at |
| BodyChangeEntry | mode (append/set), reason, actor, at |
| LeaseForceReleaseEntry | reason, staleness shape, actor, date |
| AcceptanceAmendmentEntry | op (replace/remove), index, old_text, new_text, reason, actor, at |
| EvidenceChangeEntry | old id, new id (or removal), reason, actor, at |
| DesignatedReproChangeEntry | old, new, reason, actor, at |
| ReviewEntry | verdict, reviewer, findings (text), commit sha, at |
| FailureEntry | date, attempt number, summary (rendered as dated lines under "## Failure log") |
| Attachment | path (relative to tickets/), caption, sha256 |
| AcceptanceCriterion | text, evidence tuple (comma-joined hand input is split) |
| DoneReportClaims | test_count, evidence_count, gate_errors/warnings/waived (int or null = unmeasured, never -1), error_findings set of (rule,file) |

Free-text body sections appended by verbs (heading text is load-bearing, scanned by gates):
"## Failure log", "## Drop reason" (dated line, optional "(absorbed by T-####)"), "## Reopen log",
"## Unblock log" (mandatory reason, T-3113), "## Restore log", "## Done report". 'Filed:' lines in the
Done report name follow-up tickets (checked by TICK006/TICK011/close guard T-1648).

### 2.5 State machine

Transition table (from -> allowed to), enforced in `transition()`; anything else is Err(InvalidTransition):

| From | To |
|---|---|
| queued | planned, dropped |
| planned | in-progress, dropped |
| in-progress | done, blocked, queued, dropped |
| blocked | in-progress, dropped |
| done | (terminal) |
| dropped | (terminal) |

Observations an implementer must know:
- `start` auto-plans a queued ticket (queued->planned->in-progress); there is no direct queued->in-progress edge.
- `blocked` is declared but has NO CLI verb that reaches it; `block --by` edits blocked_by and does not change state. It is reachable only programmatically. Effectively a dead state in v1.
- done->queued is NOT an edge. `reopen` bypasses the table on purpose (own gate: must be DONE, dated reason mandatory, direct write) so the generic transition can never silently un-close. Reopen warns about live worktrees that forked while the ticket was terminal (T-4287).
- Terminal states: done and dropped. Both release leases. Archive only accepts terminal tickets (ArchiveNonTerminalTicket defense in depth). `restore` moves archived tickets back without touching state.
- `fail` appends a failure-log entry and (CLI layer) requeues in-progress->queued, releasing the lease (T-1131). `record_failure` itself is a pure append.
- Display overlay (T-0716 display_state): a queued/planned ticket with a live cross-worktree lease displays as in-flight even though the local ledger copy still says queued, because ledgers are per-branch.
- Merge precedence for same-id divergence (old splice): state rank done=dropped(3) > in-progress=blocked(2) > planned(1) > queued(0), then Done-report richness, then incoming side.
- Close (-> done) guard stack (`_done_transition_guard`): evidence non-empty; substantive Done report (a bare heading does not count); no disallowed cmd: evidence for the kind; epic/story/milestone refuses with open descendants; every acceptance criterion bound to resolving evidence; optional injected checks (evidence covers touched/scope symbols, approved review naming current commit when --strict + require_review_for_close, no unwaived TEST016 confirmatory-only evidence, fresh re-run of evidence passes, own new-symbol doc/test/REL001 obligations clean, gate-claim criteria "0 RULE findings under glob" actually established, no stale Captured-claims count); always-run: live-tracker citation (no registry/waiver still cites this id as follow_up, T-0854), new-gate-rule acceptance, blockers closed, runs-last precondition, disclosed-remainder-names-a-Filed-ticket (T-1648). Cmd evidence is also re-validated at land.
- Content-loss guard on every write (T-1637/T-1679): replacing non-empty evidence and/or a Done report with empty is REFUSED by default (DoneReportOrEvidenceDiscarded); only test fixtures bypass.

### 2.6 Hierarchy, epics, milestones, sprints, ordering

| Concept | v1 behavior |
|---|---|
| parent/child | single `parent` pointer; children computed by scan. `epic <id>` = full descendant BFS, done/total rollup, ids of blocked LEAF descendants. `set-parent` (T-2770) with mandatory reason, `--clear` to root; archived tickets re-parent via archive-aware write path |
| epic/story rule | tier=ticket only is doable; epic/story cannot close with open descendant (OpenDescendant). MILE002 projects the same rule onto milestones statically |
| sprint | label commitment; `sprint assign`, `sprint show LABEL` (state rollup, closed count, total/done points, sized_count, naive points ETA), `sprint migrate` (move semver-shaped sprints onto milestone). Velocity/burndown mined from ledger git history (full walk, slow; sprint reassignment history is lost) |
| milestone | semver; sort axis FIRST in doable; orders but never hides; `doable --milestone` is an opt-in filter. Gates: MILE001 (open ticket blocked by open ticket in a LATER milestone), MILE002 (open parent with later-milestone open descendant), MILE003 (open ticket with no resolvable effective milestone), MILE004 (ambiguous runs-last pairs). milestone is a plain string; there is no milestone object (no due date, state, or release record) |
| ordering | `_doable_sort_key` = (milestone_rank, milestone_version, -priority_rank, created, id); unresolved milestone sorts after all scheduled ones |
| board | `board [--component C] [--label L]`: columns queued, planned, in-progress, blocked, done, dropped (always all present), each priority-then-age sorted. Text/JSON only |
| flow | `flow`: per-day filed vs landed vs net from git history, trailing-3-day net rate, naive burn-down ETA (null unless net shrinking), median cycle days created->first done, points_per_hour and tokens_per_point derived from history |
| list --stats | same velocity mining appended; slow on large histories |

### 2.7 Scope = write lease

| Aspect | Semantics |
|---|---|
| Declaration | list of glob strings (comma-split at input); changed only through `scope --add/--remove/--demote-to-evidence-only/--declare-no-scope` with ONE mandatory reason per invocation, audited in scope_changes |
| Overlap test | sound glob-set intersection (two-pattern wildcard DP: `*`, `?`, bracket classes), not a prefix heuristic. tickets.md/ticket-ledger paths implicitly leased by everyone and ignored |
| Registry-file carve-out (T-4650) | frob.toml [tickets].registry_files (default 4 append-shared paths: design/frob.strata, capability-via-ratchet lock json, docs/modules/gates.md, check-coverage.yaml): implicitly in every ticket's scope, exempt from lease and from CrossTicketLeakage while this branch's diff to them is additive-only |
| Managed side-effect paths (T-3296) | frob-coverage.lock.json etc. skipped by lease conflict check |
| Where checked | `doable` (default lease-filtered; `--ignore-lease`, `--show-blocked` explains `held: scope 'glob' leased by in-progress T-x (worktree or "local ledger row")`), `start` (refuses collision at grant time T-1880, refuses foreign live lease unless `--steal`), `scope --add` (checks live cross-worktree leases, T-1868), land (cross-ticket leakage) |
| Same-worktree exemption | a worktree cannot conflict with itself (T-1356/T-1883), so grouped/cluster dispatch in one worktree works |
| Over-broad demotion | holder's over-broad entries (> `large_glob_max_files`, default 25, or chronic literals like tests/**, docs/**, package prefix) are dropped before the overlap check so one repo-wide lease does not zero the queue; precise entries on the same holder still block. Package prefixes derive from pyproject (T-2771) |
| Mega-glob refusal | `start` refuses a scope whose match set exceeds the threshold unless scope_breadth_ack (T-1866); filing-time check stays WARN (24 of 68 open would fail, T-2302); TICK009 nudge once per ledger scan |
| Empty scope | `start` refuses empty scope unless no_scope_declared (T-2394); TICK013 error for in-progress/planned empty scope |
| Cross-worktree lease side channel | one JSON file per in-progress ticket at <git-common-dir>/frob-leases/<id>.json with ticket_id, scope, worktree, branch, recorded_at (ISO UTC). Written on entering in-progress, rewritten by scope changes (delta-reconciled against the lease's own current scope, T-1993), released on ANY transition not entering in-progress (keyed on file existence, T-4684), renamed on renumber (T-1173) |
| TTL / staleness | LEASE_TTL = 6h; a lease is orphaned by shapes: path-gone, ticket-gone (draft only in a retired worktree), ticket-terminal (authoritative, never TTL gated), holder-dead (TTL expired + no live process cwd'd in worktree + no land in flight for it). `read_all_leases` prunes stale ones and reconciles terminal tickets (T-4172) except during archive (T-4388) |
| Release verbs | `worktree release-lease ID` (only if confirmed orphaned), `--force --reason` (ledger-audited), `ticket reconcile`, `ticket requeue`, `ticket fail` |
| Env guard | FROB_WORKTREE=<abs path> makes every mutating entry point refuse when the git top-level differs (WorktreeLeaseViolation); coordinator has it unset. `unleased_root_env()` strips it for one write when a worker legitimately writes the shared root (T-3379). FROB_AGENT marks a dispatched agent shell |
| Lease-file TICK gates | TICK010 (lease whose worktree is gone), TICK012 (lease scope diverges from ledger scope), TICK015 (ledger-stamped worktree/branch dead) |

### 2.8 Evidence

| Aspect | v1 behavior |
|---|---|
| Kinds | (a) pytest node ids `path::Class::method` (frob:tests directives use dotted `Class.method`); (b) `cmd:<command> exit=0 sha256=<12hex>` entries produced by `--evidence-cmd` |
| Validation at bind | every node id must resolve against a fresh collection (UnknownEvidence rejects the whole batch) and must have been observed passing (EvidenceNotPassing); atomic batch semantics |
| cmd gating | allowed for kind docs and ux always (CMD_EVIDENCE_ALLOWED_KINDS), and for ANY kind whose declared scope has no Python file (scope_has_python_surface, filesystem check, T-3156); empty-output command refused as silent (EvidenceCmdSilent); `--evidence-cmd` is single-command per call; `--cwd DIR` runs under root |
| `--accepts N` | 1-based index of acceptance criterion to bind (was 0-based until T-3837, caused silent off-by-one binds) |
| evidence_scope | auto-populated for cited pre-existing tests so lease is not claimed |
| Mutation | `--replace OLD NEW --reason` (rebinds flat list and every criterion in one write, audited), `--remove ID --reason`, `--archived` (target archived ticket), `--designate-repro NODE-ID` (validates it FAILS at parent commit unless `--designate-repro-force`; reason required on redesignation), `--check-repro [NODE]` (read-only BUG002 classification: FAILED_AT_PARENT ok; PASSED_AT_PARENT, NO_VERDICT, TIMEOUT, SAME_AS_HEAD, TEST_ABSENT_AT_PARENT) |
| Gates around evidence | COV003 (resolution after close), TEST001/TEST016 (mutation evidence: confirmatory-only evidence refused for security synchronously, other kinds via batch sweep; rapid profile skips), BUG002 (bug/security repro must fail at parent) + BUG003 positive control, D-02 evidence-covers-scope, post-merge re-verification at land, orphaned-evidence-deletion guard (T-1946) |
| Recovery | `replay_evidence_from_done_report` rebuilds the evidence field from rendered '### Evidence' prose when a hand merge dropped it (T-0357) |

### 2.9 Acceptance criteria

Stored as list of {text, evidence[]}. Convention: given/when/then text. `new --acceptance` (repeatable),
`--acceptance-file` (blank-line separated blocks). `accept` verb: append (`--criterion`),
`--amend N --text --reason`, `--remove N --reason`; amend/remove of a terminal ticket refused
(AcceptanceAmendTerminalState). A criterion with empty evidence blocks done; a bound id later removed
from evidence reads unbound again. Criteria shaped "0 RULE findings under <glob>" are re-measured by a
real gate run at close/land (T-1399/T-1410). `ticket show` prints `[N]` numbers.

### 2.10 Done report

| Aspect | Rule |
|---|---|
| Home | tickets/T-####/done-report.md (v2 layout); spliced into Ticket.body on load, split out on write |
| Writer | `done-report` verb is the SINGLE write path; caller supplies only the narrative `--why`/`--why-file`/stdin; Changed and Evidence are always auto-composed |
| Sections | "## Done report" narrative; "### Changed" (fenced `git diff --stat base...HEAD`, base default main; "(no changed files detected)" if empty); "### Evidence" (renders the recorded evidence tuple, no re-run); "### Captured claims" (test count passed from a real run, gate error/warning/waived counts from a fresh `frob check --ticket`, error-findings list); optional "### Acceptance amendments" |
| Validation | base ref must resolve (BaseRefUnresolvable); narrative sanitized so a line cannot forge a `<!-- ticket:T-#### -->` marker (T-1536); `--no-check` skips the gate spawn (claims unmeasured, <5s) |
| Concurrency | the slow claims capture runs BEFORE taking the ledger lock; only the final load-compose-write is locked |
| Re-verification | land re-captures claims against the post-merge tree and refuses on test-claim or gate_errors divergence (ClaimDivergence); warnings/waived are informational. Under rapid profile the inline re-check is skipped (144-209s measured) and run in the deferred sweep (T-2938). Unmeasurable claims refuse unless `--force --reason` (ClaimsReverifyUnmeasured) |
| Quality checks | substantive-ness, hollow-report (HollowDoneReport), stale claims (T-3266), TICK006 phantom "Filed:" ids, TICK011 disclosure with no ticket, TICK014 feature/bug closed with ledger-only diff |
| reverify | `reverify` re-runs close checks on a DONE ticket with no state change and refreshes the recap (recovering the narrative verbatim) |

### 2.11 Reviews

`ticket review --verdict approve|reject --reviewer NAME --findings-file PATH [--commit SHA]` appends a
ReviewEntry (commit defaults to HEAD). `close --strict` plus frob.toml [tickets].require_review_for_close=true
requires an approve entry naming the CURRENT commit. Off by default; reject entries are advisory records.

### 2.12 Attachments

`attach ID PATH [--caption]` or clipboard image (platform backends in clipboard.py, first working one wins, PNG bytes; backend list not verified)
stores under tickets/T-####/attachments/NN-name.ext with sha256 in frontmatter; `--remove PATH`/`--remove-all`
(refused when the done report quotes the path, T-5151); `--backfill-drafts [--apply]` repairs paths left
dangling by draft promotion. On archive the attachment path field is rewritten to archive/<id>/attachments/...
(T-2986); COV004 resolves attachments as tickets/<path>.

### 2.13 Drafts, renumber, promote, finalize

| Verb / mechanism | Behavior |
|---|---|
| draft filing | off default branch `new` mints T-draft-<hex>; a draft is a fully usable id (show/start/close, blocked_by, directives) |
| `renumber OLD NEW [--dry-run]` | rewrites the ticket dir (git mv), id field, every blocked_by/parent in active AND archive, every `frob:ticket/waive/todo/tests/invariant/doc` directive in the tracked tree, registry yaml dispositions (deferred:/duplicate_of:), prose citations in other tickets' bodies (T-1125), and migrates the lease file; whole-ledger no-arg form reassigns EVERYTHING contiguous (destructive) |
| `promote DRAFT` | thin wrapper over finalize_draft: allocates next real id against the merged view under the ledger lock and renames; no-op if already final. Replaces the lossy hand-refile recipe (T-1636: 12 evidence ids and a 12KB Done report lost). Committed in the worktree; reaches main only on land (dedicated mirror, T-2587) |
| land-time finalize | `land` finalizes the landing draft plus every sibling draft in the worktree, using main's FRESH ledger as the id ceiling (finalize_draft_for_land, T-1179); `land --plan` finalizes all drafts in one atomic pass |
| Gates | TICK001 duplicate ids anywhere (unwaivable), TICK002 draft id surviving onto default branch (unwaivable), detect_duplicate_ticket_id_collisions at land |
| Rejected alternative | worktree allocating real ids from a shared counter (T-1622): re-introduces cross-checkout coordination |

### 2.14 On-disk layout and storage modes

| Path | Role |
|---|---|
| tickets/T-####/ticket.md | frontmatter (YAML) + body; v2 layout, the current default for fresh repos (T-1553) |
| tickets/T-####/done-report.md | Done report |
| tickets/T-####/attachments/ | files |
| tickets/archive/T-####/ | archived done/dropped tickets, moved with `git mv` (no content rewrite except the attachment path field) |
| tickets.md + tickets-archive.md | legacy v1 monofile ledger (marker comment + yaml fence per ticket); still supported in source for other repos; `migrate --to v2 [--fill-gaps]` converts; `migrate` alone collapses legacy tickets/*.md dir mode into the monofile |
| tickets/T-####-slug.md | legacy dir mode |
| .frob/tickets.lock | repo-wide ledger flock (ledger_lock); `ticket_lock(id)` and `allocator_lock` primitives exist but v1 call sites still mostly use the global lock; `--wait [SECONDS]` on some verbs blocks on land-in-progress/lock instead of refusing |
| .frob/tickets-index.json | derived mtime/size cache for fast load; rebuildable, never authoritative |
| .frob/land.lock, land-queue.json, land-queue/<id>.json, land-status.json, journal/<id>.json, land-repair/ | land runtime state (see section 4) |
| .frob/verify-queue.json, verify-watermark.json, quarantine.json, profile-ratchet.json | verification state (section 6) |
| <git-common-dir>/frob-leases/<id>.json | cross-worktree leases |
| <git-common-dir>/frob-pool/manifest.json | warm worktree pool |
| force-overrides.jsonl (tracked, merge=union) | append-only record of every `--force` override with reason |
| rapid-debt.jsonl | debt record for deferred verification (moved out of git, T-2997) |
| changelog.d/T-####.md | per-ticket changelog fragments written at land |
| fleet.toml | cross-repo manifest |

Archive: `archive` moves every done/dropped ticket; refuses if any live cross-worktree lease exists
(`--force --reason` records in force-overrides.jsonl); an id present in both active and archive collapses to
the archive copy (self-healing, T-1437). `load_queue` reads active+archive (so blockers/parents of archived
tickets resolve); `list`/`doable` read active only. TICK003 warns when too many closed tickets sit
un-archived (v1 repo today: 236 done, 37 dropped un-archived). `restore ID --reason` is the inverse.
Wholesale writes carry an optimistic-concurrency digest map (LedgerChangedSinceLoad, T-0680/T-1588).
`_store_api` (T-4657) is the intended single seam (get/list/put for live and archive); direct ticket.md
opens are grandfathered via an allowlist test that may only shrink.

### 2.15 Error taxonomy (TicketError ~88 variants, LandError 28)

Useful as a v2 error-enum seed. TicketError groups: lookup (NotFound, DuplicateId, DuplicateTicket,
DuplicateFinding, MalformedFrontmatter); transition/close (InvalidTransition, MissingEvidence, MissingDoneReport,
HollowDoneReport, StaleClaimsInDoneReport, BlockerOpen, BlockerOpenAtClose, RunsLastBlocked, OpenDescendant,
MissingApprovedReview, EvidenceConfirmatoryOnly, EvidenceNotPassing, EvidenceScopeUnbound, AcceptanceUnbound,
LiveTrackerCited, NewGateRuleUnaccepted, OwnObligationsUnclean, GateClaimUnverified); evidence (Unknown/Malformed/
KindNotAllowed/CmdFailed/CmdSilent/ReplaceNotFound/ReplaceReasonMissing); scope (ScopeLeaseConflict, ScopeChangeEmpty,
ScopeChangeReasonMissing, ScopeRemoveNotDeclared, ScopeRemoveOrphansEvidence, EmptyScopeAtStart, ScopeGlobInvalid);
validation (InvalidMilestone, InvalidPoints, SprintIsSemverShaped, UnsizedTicketAtStart); parent (ParentNotFound/
SelfReference/Cycle/TierInversion/AlreadyRoot/ReasonMissing); archive/restore (ArchiveLiveLeaseExists,
ArchiveNonTerminalTicket, Restore*); integrity (LedgerIntegrityViolation, SiblingLedgerEditConflict, IdTitleMismatch,
DoneReportOrEvidenceDiscarded, LedgerChangedSinceLoad, WriteFailed, TicketVanishedDuringScan);
ownership (WorktreeLeaseViolation, TicketOwnershipViolation, ReconcileLandInProgress).
LandError: DirtyMain, NotCloseable, GitFailed, MergeConflict, UnownedDeletions, CloseFailed, SquashConflict,
CommitFailed, IncompleteLand, ReleaseBumpFailed, BranchDrift, ClaimDivergence, EvidenceConfirmatoryOnly,
LiveTrackerCited, TerminalStateRegression, OutOfScopeWaiveDeletion, CrossTicketLeakage, PlanTickGateDirty,
LandLockTimeout, Pre/PostLandUnscopedSweepFailed, PassengerTickets, AlreadyLandedOnMain, SiblingLedgerEditConflict,
AnchorTerminalLand, OrphanedEvidenceDeletion, TargetBranchInvalid, ClaimsReverifyUnmeasured.

## 3. Verbs and what they mutate

Commit strategy key (LEDGER_VERB_STRATEGY, T-2603): OWN = verb commits a complete multi-file transaction itself;
OWN+M = own transaction plus dedicated ledger-only mirror to primary; GEN-M = generic commit of ledger residue
THEN mirror the ticket's ledger paths to the PRIMARY checkout immediately (so fleet sees scope/lease changes);
GEN-U = commits its own ledger change (via commit_ticket_ledger_change) but is NOT mirrored (progress that land
carries atomically); RO = read-only / not ticket scoped. Most mutating verbs accept `--no-commit`, which WARNs
that a dirty ledger will DirtyMain-block lands. Several accept `--wait [SECONDS]`.

| Verb | Mutates | Strategy | Notes |
|---|---|---|---|
| new | creates ticket dir; id (draft off default); optional --evidence, scope-breadth-ack, runs-last-parallel-safe at filing | GEN-U (self-commits, T-1758: the write boundary commits) | flags: --title --kind --acceptance --threat --priority --origin --scope --blocked-by --parent --tier --sprint --milestone --points --component --label --finding RULE:FILE --body/--body-file --acceptance-file --json --evidence --no-commit --ack-related --wait; refuses exact-duplicate title and duplicate finding; WARNs on omitted points, overlapping scope, over-broad scope |
| list | none | RO | --state/--status filter, --json, --stats |
| show | none | RO | full ticket incl. [N] acceptance |
| doable | none (may auto-DROP sweep-filed tickets whose findings vanished, T-2006) | RO | --json --show-blocked --ignore-lease --sprint --milestone --by-parent --show-anchors; splits in-flight rows from dispatchable rows; UNDISPATCHED alarm |
| wave | none | RO | --agents N --json --ignore-lease |
| contention | none | RO | files declared by 2+ open tickets, ranked, suggested single-agent batching |
| board / epic / flow | none | RO | see 2.6 |
| brief | none | RO | `[id]` or `--cluster EPIC-OR-STORY` |
| plan | state queued->planned | GEN-U | |
| start | state ->in-progress, stamps worktree/branch, writes lease file, may set scope_breadth_ack / unsized_ack; spawns detached background pre-work sweep (dup+xref) | GEN-U (auto-commit T-1054) | guard chain: terminal refused; foreign live lease refused (`--steal` overrides and invalidates theirs); unsized (opt-in); mega-glob; empty scope; scope collision with live lease; flags --foreground --steal --scope-breadth-ack(+reason) --unsized-ack REASON --require-points |
| work | creates/reuses worktree (default .claude/worktrees/<id-lowercase>), merges main, builds natives, then start; `--cluster` leases every dispatchable descendant into ONE worktree with union scope | GEN-U | --worktree --cluster --foreground --steal |
| sweep | re-records pre-work sweep (in-progress only; terminal = no-op) | GEN-U | |
| requeue | in-progress->queued, releases lease | GEN-M (T-2840) | --reason (logged only) |
| fail | appends Failure log; requeues if in-progress | GEN-U | --summary required |
| block / unblock | blocked_by add / remove | GEN-M | unblock requires dated --reason (Unblock log) |
| close | ->done after guard stack; may bind --evidence/--evidence-cmd/--accepts; may write frob:no-behavior-change directive into body | GEN-U | --strict --skip-mutation-evidence --no-behavior-change(+reason/-file) |
| drop | ->dropped; Drop reason line; releases lease | GEN-U | --reason required, --absorbed-by (unvalidated note) |
| reopen | done->queued directly, Reopen log | GEN-M | reason required; DONE only |
| reverify | refreshes Done report recap on done ticket | GEN-U | close's evidence flags + --base-ref |
| done-report | writes done-report.md (+ claims capture) | GEN-U | --why/--why-file/stdin --base-ref --no-check |
| evidence | evidence list, evidence_scope, acceptance binding, designated repro, audit trails | GEN-U | see 2.8; direct mirror path for --replace/--remove (T-4267) |
| accept | acceptance list + amendments audit | GEN-M | |
| review | reviews list | GEN-M | |
| scope | scope, evidence_scope, no_scope_declared, scope_changes, lease file | GEN-M | one reason per call; refuses overlap with another live lease |
| scope-ack | scope_breadth_ack(+reason) | GEN-M | |
| anchor | anchor(+reason) --set/--clear | GEN-M | |
| set ID FIELD VALUE | priority, kind, component, tier, milestone, sprint (folds standalone spellings) | GEN-M | --reason required, triage_changes audit |
| priority / kind / component / tier | same single-field setters | GEN-M | kind change after evidence appends kind_history |
| milestone, points, tokens, sprint assign | single-field setters (milestone/points/tokens/sprint do not require reason) | GEN-M | |
| label | labels add/remove | GEN-M | no audit trail |
| set-parent | parent | GEN-M | reason required, --clear |
| runs-last on|off ; runs-last-parallel-safe | flags | GEN-M | |
| body | body append/set + body_changes | GEN-M | --append/--append-file/--set/--set-file, reason required |
| attach | attachments + files | GEN-M | see 2.12 |
| renumber | whole-tree id rewrite | OWN | --dry-run |
| promote | draft finalize | OWN+M | |
| migrate | store mode conversion | RO-class (caller commits) | --to v2, --fill-gaps |
| archive | moves terminal tickets | GEN-U | --force --reason, --no-commit |
| restore | un-archive | GEN-M | --reason |
| reconcile / admin reconcile | requeues stale in-progress holds, reports orphan worktrees, orphaned land intents, unlanded branch work (report only), stray extra fields | GEN-U | --apply --remove-orphans --strip-stale-fields --no-commit --wait |
| land | whole land transaction | OWN | section 4 |
| merge-driver %O %A %B | git merge driver for monofile ledger | OWN | retired for v2 repos |
| sweep-async --commit SHA | detached post-land sweep under rapid | OWN | |
| waive-audit scan/complete | watermark of frob:waive honesty audit | RO-class | |
| debt / deprecated | lists frob:debt and frob:deprecated entries | RO | |
| (other CLI families touching tickets) | `frob worktree sweep|remove|release-lease`, `frob agent env|brief`, `frob verify status|now|explain|dispose|drain-async`, `frob fleet status|route`, `frob scaffold pool warm|lease|status` | | |

Atomicity facts: ledger writes are temp-file + rename; verbs hold ledger_lock; ledger-writing verbs refuse
while a land holds land.lock (`refuse_if_land_in_progress`, T-1619) because a commit during a land moved the
tip under it; every verb auto-commits so root never sits dirty (T-1054/T-1130/T-1615); the dispatch wrapper
raises KeyError for a verb absent from the strategy table (cure for the T-2197 silent default).

## 4. Landing

### 4.1 Worktree-per-ticket flow (the happy path)

1. `frob ticket work T-X` (or EnterWorktree / `git worktree add` for a series): create or reuse the worktree,
   merge main for freshness (a stale-cut warning exists, T-1059; the harness has cut worktrees from stale
   origin/main), build native extensions, then `start` (lease, in-progress, stamps worktree/branch).
2. Implement inside scope; commit WIP (never `git stash`: refs/stash is shared across worktrees; a
   reference-transaction hook refuses stash when more than one worktree exists).
3. Bind evidence, `done-report`, run `frob check --land-parity` and exactly one `land --dry-run` from root.
4. `frob ticket land T-X --worktree PATH [--push] [--finish|--retire-on-proof]`.
5. LAND-PROOF line: commit sha, is_ancestor_of_main, state_on_main, verified. verified=True is the definition
   of landed. `--finish` removes the worktree only if proven; `--retire-on-proof` also deletes the branch;
   `--force --reason` overrides a live-process or lease pin.

### 4.2 Land pipeline (documented order; v1 numbering)

| Step | What |
|---|---|
| 0 | resolve root from worktree via git common dir (no manual cd) |
| pre | CLI absorbs `frob fmt` and Tier-A deterministic auto-fixes in the worktree first; pre-land lint gate; crash recovery of stale land-repair / post-land-verify markers; reclaim orphaned squash residue only when a repair marker exists AND land.lock is free (T-2286: dirt alone is NOT evidence) |
| 1 | refuse dirty root (DirtyMain); refuse root==worktree |
| 2 | validate close preconditions in the worktree BEFORE any git mutation (NotCloseable) |
| 2.5 | refuse uncommitted out-of-scope frob:waive deletions |
| 3 | wip-commit worktree changes ("wip: pre-land snapshot for <id>"); auto-restore uv.lock version-only flap |
| 4 | merge main into worktree (no-ff, staged); conflicts outside ledger abort; ledger conflicts historically spliced by ticket-id, per-file native git in v2 |
| 5 | deletion-filter (stale-base guard): every deleted path must be within scope; whole-tree/bare-top-level globs never authorize deletion (UnownedDeletions) |
| 5.5 | re-verify evidence against POST-MERGE tree (resolution, pass, scope binding, gate claims); runs before dry-run exit so a clean dry run is a real guarantee |
| 6 | `--dry-run` stops and unwinds. Dry run does NOT measure every refusal class (post-squash self-conformance, DOC006 pointers at unlanded siblings, parametrized frob:tests ids, native freshness, stale uv sync) |
| 7-8 | finalize draft id; close (->done) in worktree |
| 9 | squash. Since T-3121 the whole squash-apply is built in a DISPOSABLE detached `git worktree` cut at pre_land_tip, never in root; fold into a commit object; `publish_ref_cas` = `git update-ref` compare-and-swap on refs/heads/<target>; lost CAS reports DirtyMain (a sibling landed first); then `read-tree -m -u old new` resyncs root's index/tree (a blocked resync is NOT a land failure: Ok with root_resync_failed=True and a recovery command). Root is never dirty during a land |
| 9.5 | completeness assertion: worktree's full changeset (tracked, untracked, deletions) must all appear in the staged result (IncompleteLand; T-0448 dropped an untracked file when a manual patch-apply was used) |
| 9.6 | release bookkeeping, DEFERRED (T-2462): writes a changelog.d/T-####.md fragment and regenerates the unreleased CHANGELOG section; pyproject version and .frob-release.json are NOT touched at land (they serialized every land on two files); `frob release` cuts once per release. Version/CHANGELOG/uv.lock are land-owned: agents never edit them (pre-commit hook refuses). Version-monotonicity and quartet-coherence checks (T-0992/T-1078/T-1358/T-1760) remain in code for non-deferred callbacks; recompute-not-carry resets release artifacts to pre-land state first |
| 9.7 | best-effort native rebuild when native source trees changed |
| 9.75 | TICK005 regression sweep: any ticket terminal pre-splice but neither terminal nor archived after splice refuses (TerminalStateRegression) |
| 9.8 | stacked-sibling absorption: an empty squash is accepted ONLY if the id is already done on root and every scope file matches content-for-content |
| 10 | commit "<type>(tickets): land <final-id> <title>" (ASCII, no Co-Authored-By); this is the last commit of a per-ticket land (T-3543 dropped the follow-up land_commit commit) |
| 11 | `--push` pushes root's branch to upstream after success only; push failure exits nonzero but does not unwind |
| tail | post-land unscoped error sweep (standard: synchronous, reverts on new unscoped errors; rapid: detached, files a ticket, appends rapid-debt line first), baseline thread, LAND-PROOF print, `--finish` |

Error handling on failure: close/commit failure leaves the merge commit only in the WORKTREE branch; the log names
the exact undo (`git -C <worktree> reset --hard HEAD~1`). The worktree/branch is always the recovery path; never
remove it after a failed land. A land that dies silently may have succeeded: check git log before retrying.

### 4.3 Land modes, queue, deferred pieces

| Mechanism | Detail |
|---|---|
| Land lock | flock on .frob/land.lock (kernel frees on death, no TTL); holder metadata names ticket id; declared FROB_LAND_DEADLINE_S bounds lock wait; in-land wait defaults near zero (queueing belongs to the caller, T-2816); `wait_for_land_slot.py --max-in-flight N --timeout S` exit 0 free / 1 retry / 2 unmeasured |
| Exclusivity | any ledger-commit verb refuses (LandInProgress) while a land holds the lock |
| Merge queue (T-1345/T-1444/T-3613) | .frob/land-queue.json (own flock land-queue.lock), FIFO, never auto-retry; `land --queue` enqueues and returns; `land --drain` is one process, one invocation, serial, not a daemon; ENQUEUE is the DEFAULT when FROB_AGENT is set or [tool.frob] land_default="queue"; per-intent poll file .frob/land-queue/<id>.json (queued/landing/landed/failed, verbatim refusal, sha) read via `land --status ID`; drainer records pid and reclaims entries stuck in "landing" only if pid CONFIRMED dead; drain re-execs itself between lands if frob's own source/natives changed (T-5814) |
| Pollable status | .frob/land-status.json phases acquiring-lock, waiting-for-lock, lock-acquired, running, done/failed with pid and timestamps; never deleted (stale updated_at = died mid-flight) |
| Intent journal | .frob/journal/<id>.json written at land start, cleared in finally; orphaned marker reported by reconcile and only cleared (never resumed) with --apply |
| Checkpoint durability design (T-1554) | two durable windows exist (pre-commit staging repair marker T-0907, post-land verify marker T-1523); recommended Option A: a land-finish-pending marker around worktree removal / branch delete; Option B (`--verify-only SHA`) deferred. Design only |
| Target branch | `--branch/--onto NAME` or [tool.frob] ticket_land_branch; must exist and be root's current checkout (TargetBranchInvalid); landing onto a branch root is not on is deferred. The v1 repo lands on "dev", keeping main frozen at a release |
| `--plan` | design-phase worktree with docs + draft tickets and no closeable ticket: no-ff merge, finalize every incoming draft atomically, optional TICK gate re-check, all failures hard-reset root |
| Profiles (frob.toml [profile]) | rapid / standard (default) / fortress(no-op). rapid: no TEST016 on land path, no pre-commit sweep, no sync post-land sweep, deferred sweep + rolling baseline, inline claims re-verify skipped; one-way auto-ratchet to standard when repo files > 300, tickets > 200 or concurrent leases > 5. Never relaxed: ledger integrity, LAND-PROOF. Scaffolded repos default to rapid |
| Deferred mutation sweep | TEST016 for non-security kinds is enqueued to .frob/mutation-sweep-queue.json and processed by `land --run-mutation-sweep` (also run after --drain) |
| Splice test-then-impl (T-3546, design + unwired primitives) | would publish two commits (test first, then impl) with ONE CAS; trailer Land-Splice-Role; makes `--check-repro` verifiable post-land (a single squash can never show the test failing at any ref); falls back to single squash when either side is empty |

### 4.4 Ledger conflict handling (v1 monofile vs v2)

| Concern | Resolution |
|---|---|
| Monofile era | `splice_ledger`: parse both sides to id->Ticket, newest per id wins (state rank, richness, incoming), evidence UNIONed (T-0398 D-09), 3-way aware via true merge-base (T-1154), sibling edits carried forward when only the worktree changed, REFUSED when both changed differently (SiblingLedgerEditConflict, T-1721); tickets-archive.md spliced the same way; git merge driver `merge.frob-ledger` registered per clone via `git config` (uv run frob, never bare frob, T-1443); force-overrides.jsonl uses git built-in merge=union (no registration) |
| v2 | disjoint ticket dirs = disjoint git objects; the custom driver is deliberately retired for v2 repos (.gitattributes documents it) and must not be registered; native 3-way handles different-key edits; real conflicts are same-key edits and add/add of done-report.md; resolve by reading both sides, never blind --ours/--theirs; audit with `ticket show` afterwards |
| Main is a second writer | ledger mirror (T-2563) copies a ticket's ledger paths from a worktree to the primary and commits there, pathspec-limited, skipped loudly if a land is in progress, no-op when run in the primary; done-report.md is excluded from the mirror (T-2570: a metadata mirror silently overwrote main's fresh done-report) |
| Mirror batching (T-3550, design only) | 109 of last 300 main commits were mirror commits; proposed .frob/mirror-queue/ one file per event, flush as one "chore(tickets): sync ledger (...)" commit on land completion, sweep completion, or bounded timer; block/unblock and land stay per-commit as coordination signals; unresolved owner question: do cross-ticket flush commits break the one-commit-one-ticket assumption of CrossTicketLeakage checks. Re-measurement showed the 41 "file" commits are genuine individual decisions, not a batching target |

### 4.5 Passenger tickets, leakage, already-landed

| Guard | Behavior |
|---|---|
| CrossTicketLeakage | refuses when a sibling IN_PROGRESS ticket's scope + ledger diff shows up in the branch; terminal siblings exempt; registry-file additive-only diffs exempt; `--allow-cross-ticket` is the shared escape hatch |
| Passenger tickets (T-1618) | scans the branch's FULL diff for `frob:ticket <other-id>` directive lines (net + occurrences vs - occurrences; exact relocation multiset exempt, T-2082) so a dropped sibling's code riding along is caught regardless of ledger state. Incident: a reverted-in-ledger ticket's code still landed and deleted 55 live waiver directives |
| AlreadyLandedOnMain | clean worktree + empty scope diff + ticket's own record on base_ref already `done`; refuses with the manual recipe (verify, then `close`) |
| Anchors | land refuses to move an anchor ticket terminal |
| Sibling ledger edits | carried forward or refused as above |
| Orphaned evidence deletion | deleting a test that bound evidence refuses unless rebound (T-1946) |
| Live-tracker citation | cannot close/land a ticket still cited as follow_up by a waiver/registry disposition (T-0854; incident: 41 orphaned rows) |

## 5. Agent coordination

| Piece | Behavior |
|---|---|
| doable | state in queued/planned, tier=ticket, no open blockers, not anchor (unless `--show-anchors`), runs-last precondition satisfied, scope not overlapping any live lease (local in-progress rows UNION cross-worktree lease files), sorted by key in 2.6. Doable-time revalidation drops sweep-filed tickets whose findings vanished (one scoped re-check, unmeasurable drops nothing) |
| wave --agents N | greedy partition of doable into up to N mutually scope-DISJOINT groups; same-group tickets may share scope (one agent, in order); a candidate colliding with 2+ already-separate groups goes to `remainder` with the blocking group, colliding ticket and glob; N is a hint, never padded; deterministic |
| contention | files declared by 2+ open tickets with holder counts, ranked, with suggested batching; the number that caps parallel dispatch |
| brief ID / --cluster | composed mission text: body+acceptance, scope + collisions, CONCURRENT leases (do-not-touch list), concurrency hazards, playbook hard rules parsed from the playbook's numbered headings, inferred verify commands (always `frob check --ticket`), gate baseline status, REL/land rules with current version. `--cluster` = topologically sorted dispatchable descendants of an epic/story, union scope lease, shared rules once, one worktree (`work --cluster`) |
| agent env | `frob agent env WORKTREE` prints FROB_WORKTREE / FROB_AGENT exports plus PYTEST_XDIST_AUTO_NUM_WORKERS = max(1, cpu // (other_live_leases + 1)) under a fleet; frob-orchestrated pytest applies the bound in-process because harness shell state is reset between calls; `frob agent brief ID` renders the dispatch contract |
| Dispatch contract (playbook section 0) | one named worktree per series; build natives first; long verbs foreground with explicit timeout; stay in scope, narrow broad scope; evidence via node ids + --accepts; no stash; no remove after failed land; file residue as drafts and verify real ids exist before citing; read LAND-PROOF; check the land slot with the script not ps; ASCII; report per ticket land hash, evidence, residue ids. FROB_AGENT set makes bare `frob check` refuse (needs --only/--budget); agents never run coverage-full, baseline stamps, version bumps |
| scope-ack / mega-glob rules | see 2.7; ack is per ticket with mandatory reason; `start --scope-breadth-ack` acks and starts in one call |
| Coordinator scripts | scripts/fleet_status.py (root dirt, leases, worktree idle age and content classification, land processes/lock holders, host load/swap pressure, forkserver counts, ticket rot buckets, readiness, scope intersections), verify_lands.py (resolve ticket->landing commit, ancestry, subject), wait_for_land_slot.py, check_summary.py. All plain stdlib, run via `uv run python` (bare python3 broke on 3.10). fleet_status resolves repo root via git common dir (a worktree-relative guess reported "0 live leases") |
| Worktree lifecycle | `worktree sweep [--dry-run] [--min-age H]` lease-aware (verdict kept:dirty, kept:unlanded ranks ABOVE dirty so clean finished work is never swept, T-1934); `worktree remove` with liveness check; `release-lease`; warm pool (frob scaffold pool warm/lease/status) pre-builds N worktrees with natives under <git-common-dir>/frob-pool |
| Fleet routing (fleet.toml) | `[[repo]] name,path` (relative to manifest dir); `frob fleet status [--json --skip-gates --manifest]` probes branch/dirty, `uv run --project <repo> frob check --json` gate counts (120s cap, failures degrade to zero), doable count; sorted reddest-first; `frob fleet route --repo NAME --title ... [--kind --priority --scope --body]` files a ticket (origin=agent) directly into a sibling's ledger via new_ticket, refusing (RouteFailed) when the sibling has no ledger rather than bootstrapping one. Manifest lists 9 repos. Routing creates tickets only; no cross-repo links or states |
| Staleness alarms | critical 4h / high 24h undispatched (TICK007); rot buckets in fleet_status |
| Auto-filed tickets | sweep regression tickets and claim-divergence tickets filed by machinery with findings=(rule,file) pairs and titles of a machine-generated shape; at most one per sweep run |

## 6. Verify sweep, watermark, quarantine and tickets

| Piece | Interaction with tickets |
|---|---|
| Epic T-1686 principle | a check stays on the land critical path only if its failure damages someone OTHER than the author (ledger integrity, LAND-PROOF, lease/lock discipline); everything else defers to batch verification |
| Watermark | .frob/verify-queue.json (append-only intent per land, with touched-symbol set) and verify-watermark.json (single current watermark); coalescing worker (daemon) reads queue to tip, verifies once, advances watermark only on green; in-flight marker so a killed worker cannot advance past an unconfirmed batch |
| Attribution | red findings map to the specific land commit via graph reachability (symbolic), with bisect fallback; `frob verify explain` prints the path |
| Backpressure | land blocks until watermark advances when queue depth/age exceeds profile ceilings (ceilings_for_profile) |
| Quarantine circuit breaker | red batch raises .frob/quarantine.json (via the regression-ticket seam both drivers share); while raised, deferred landing is OFF (ceilings forced to depth 0 age 0 = fully synchronous) regardless of profile; unreadable quarantine file is treated as raised; clears ONLY by `frob verify dispose` giving EVERY finding a disposition (filed ticket id or dismissed with reason), never by a green run; trivial unattributed ruff I001/F401 findings are exempt (T-3025); native-extension noise from cold worktrees filtered by warm re-check (T-1847) |
| Tickets filed by sweep | `_file_regression_ticket` (rapid sweep) files a bug ticket with findings pairs; also auto-DROPS a sweep ticket when its identities no longer reproduce (T-1983, T-2006 at doable time); never drops on an unmeasurable re-check (T-2521: 7 tickets dropped against truncated output, 66 findings lost) |
| rapid-debt | every deferral appends a machine-readable debt line BEFORE spawning the child; `ticket debt` lists them; ratchet override (T-1681) |
| Claim divergence | Done-report captured claims re-checked in the deferred sweep (T-2938) against the same unscoped measurement |
| Truncation honesty | budget-truncated or resumed sweeps must not present as clean (T-2456, T-2713, T-2793) |
| Stale worktree reclaim | automatic (T-2261) via lease/liveness predicates |
| Ticket-state coupling | a quarantine disposition may name a ticket id; WIRE002-style gates require a follow_up id that is non-terminal, which is why anchors exist |

## 7. Known pain points and gotchas (collected from docs and code comments)

| Area | Incident / gotcha | Cite |
|---|---|---|
| Monofile era | every ticket write was a diff over everyone's state; archive clobber, churn rewrites, id collisions, draft deaths via the "restore main's file" recipe, DirtyMain from write-then-commit split, lock starvation | T-0577 T-0959 T-1036 T-1090 T-1115..1128 T-1054 T-0933/0982 (all collected in ledger-v2.md section 0) |
| Narrative corruption | a Done-report line byte-identical to a ledger marker forged a section boundary and corrupted a neighbor | T-1536 |
| Stale-snapshot wholesale writes | silent revert of three DONE tickets to QUEUED by a stale in-memory map | T-0680/T-0889/T-1588 |
| Hand edits | agents hand-edit ledgers, bypass verbs; every verb exists to replace a hand-edit recipe (priority, scope, body, drop, reopen, restore, done-report, renumber, promote). Hand-refile of a draft lost 12 evidence ids | T-1636 T-0579 T-2392 |
| Falsely closed tickets | ticket reached done while blocked and with a land touching zero source files; reopen verb and TICK014 are the answer | T-3064 T-3087 T-3092 |
| Silent zero / invisible effect | mirror: verb success message true, effect unreachable from main; missing verb-table entry crashed after write; `points` validated but never persisted; dropped-field class | T-2563 T-2197 T-2681 T-3081 T-5815 |
| Lease leaks | fail left ticket in-progress holding lease forever; drop from another checkout left lease file; lease of a terminal ticket blocked the queue; deleting worktree by hand was only recovery | T-1050/T-1131 T-3259/T-4659/T-4684 T-2031/T-2048/T-4172 |
| Cross-worktree blindness | per-branch ledgers mean doable/scope --add could not see siblings' starts until merged; fixed by the side channel; show-blocked once named the wrong holder | T-0473 T-1868 T-1743 T-1880 |
| Evidence | collected-but-failing test bound as evidence; 0-based --accepts silently bound wrong criterion; bind-order picked the wrong repro test for BUG002; runner timeout under load reported all evidence as FAILED | T-0398 T-3837 T-1670 T-2569 |
| Gate gaming | kind change bug->feature to dodge BUG002; weakening acceptance to close; rebind evidence silently; hence audited changes with mandatory reasons | T-1616 T-1422 T-1733 |
| Land hazards | squash from stale base silently reverts landed features (deletion filter); manual patch-apply dropped an untracked file; two lands computing the same version; version/uv.lock regression oscillating 0.366<->0.365; passenger code of a "reverted" sibling; ledger write during a land moved tip and stranded staged files | T-0167 T-0448 T-0976/T-0989/T-1760 T-1618 T-1619 |
| Land cost | full-repo check on every land 2-8 min; inline claims re-verify 144-209s; dozens of fixed-cost steps; five-minute land is itself a correctness risk (queue stops draining) | T-1684 T-2913 |
| Process hygiene | hand-rolled ps/pgrep land probes never reach zero (their own command text matches); backgrounded long verbs lose notifications; bare frob vs uv run frob version skew (stale global registered as merge driver reintroduced a fixed bug); git stash and .git/info/exclude are repo-global; inline shell prose with backticks executed by bash (use --*-file) | T-2742 T-1004 T-1443 T-0574 |
| Commit churn | ~109 of last 300 main commits were mirror commits; "82 percent of main is chore churn" | T-3542 T-3544 T-3550 |
| Scope ergonomics | whole-file exclusive leases on hot shared files serialized 5-8 agents (registry-file carve-out); mega-globs: 39 of 72 queued tickets carried one; chronically over-broad literals | T-4650 T-1866 T-2302 |
| Sprint/milestone conflation | 592 of 691 open tickets carried semver in sprint | T-5133 |
| Archive | archive-time lease zeroing defeated its own guard; non-terminal ticket found under archive (T-0450, cause never found) | T-4388 T-2954 |
| Dead surface | `blocked` state unreachable from CLI; `fortress` profile unwired; `due`, `rank`, `flavour` have fields but no setter verbs; tickets.md in frontmatter fence for older archived tickets; `ticket_runner` verb table must be kept in sync by hand | this inventory |
| Perf | `doable` on 1,245 active tickets exceeded 120s in one run; velocity/flow mining walks all ledger git history; full ledger scan per verb under a global lock | observed; T-0938 T-1100 |
| Repo-name leakage | milestone values like 0.534.0 mirror the package release; v1 had no release object so sprint/milestone semantics drifted | T-5133 |
| Test-rooted closure | closing requires a Python test collector; Rust-only or docs-only repos need the cmd: escape (scope without any .py file) | T-0215 T-3045 T-3156 |
| Environment fragility | harness resets shell state per call; cwd must be the worktree; natives must be built (mass phantom findings otherwise); frob outputs scale with 1,245 tickets | playbook sections 1-3 |

## 8. Jira-superset gap list

### 8.1 What Jira has that v1 lacks or does poorly

| Jira capability | v1 status | Gap detail / what v2 needs |
|---|---|---|
| Issue types (Epic/Story/Task/Bug/Subtask, custom) | kind (7) x tier (4) fixed enums | no custom types, no per-type workflow or fields, no Subtask-as-distinct-type (parent+tier approximates); kind and tier conflated into evidence behavior |
| Workflows (custom statuses, transitions, conditions, validators, post-functions) | one hardcoded 6-state machine, `blocked` unreachable | no per-project/per-type workflows, no named transitions, no status categories (to-do/in-progress/done), no resolution field (done vs dropped only, no "won't fix/duplicate/cannot reproduce") |
| Assignee / reporter / owner | NONE (origin enum = human/agent/auditor; worktree/branch stamp is the only owner trace; actor strings in audit entries) | needs first-class assignee, reporter, owner, mentions, team membership; ticket ownership currently implied by a lease |
| Boards (Kanban/Scrum, swimlanes, WIP limits, quick filters) | text/JSON `board` with fixed columns and 2 filters (component, label) | no interactive board, no swimlanes, no WIP limits, no saved filters, no per-board column mapping, no card layout |
| Backlog ranking | `rank` field (sibling hint, no setter) + priority/age sort | no drag-order backlog, no per-sprint backlog lanes, no rank collision resolution |
| Sprints | free label, show/assign/migrate, mined velocity | no sprint objects (start/end dates, goal, state active/closed, capacity), no carry-over on close, no burndown chart, no sprint report, no scope-change tracking, single sprint per ticket only |
| Epics / roadmaps / timeline | parent + epic rollup (done/total, blocked leaves), milestone tier | no roadmap/timeline view, no epic progress by points, dependencies not shown, milestone has no date or object |
| Components (with lead, default assignee) | freeform string | no component registry, owner, or auto-assignment |
| Versions / releases (fix version, affects version, release notes) | `milestone` semver string; changelog fragments written at land; REL gates | no release object (state, date, notes), no affects-version, no multiple fix versions, no release burndown; release is cut outside tickets |
| Custom fields | none; unknown keys tolerated but WARNed (TICK008) | no typed, schema-declared custom fields, contexts, screens; field set is code |
| Issue links (blocks, is blocked by, relates, duplicates, clones, caused by) | blocked_by only; `absorbed_by` free-text note; parent | no typed link taxonomy, no inverse display, no duplicate resolution semantics, no cross-repo links (fleet route files into one repo, no linkage) |
| Subtasks / checklists | acceptance criteria list with evidence binding | no checklist toggling, no subtask rollup separate from tiers |
| Comments / discussion / @mentions | none; narrative goes in body sections and Done report | no threaded comments, no author/time per comment (body_changes records append events only), no reactions, no mention notifications |
| Watchers / voters / subscriptions / notifications | none | no watch lists, no notification schemes, no email/Slack/webhook out; only logs and stdout |
| Time tracking (estimates, remaining, worklog) | story points (Fibonacci) + derived hours-per-point and tokens-per-point; explicitly NO manual hours (owner directive) | no original/remaining estimate, no worklogs, no due-date reminders (due field has no verb); cycle time derived only from git history at day granularity of `created` |
| Query language (JQL) | `list --state`, `board --component/--label`, `doable` flags, `--json` | no query language, no saved filters, no subscriptions, no sorting spec, no cross-field boolean queries, no full-text search |
| Dashboards / gadgets / reports | `flow`, `sprint show`, `contention`, `fleet status`, fleet_status.py script | no dashboards, no control chart, created-vs-resolved chart (flow approximates), cumulative flow, cycle-time histogram, workload report |
| Automation rules (triggers/conditions/actions) | git hooks, gates (TICK/MILE families), auto-drop and auto-file in sweeps, Claude hooks; no user-defined rules | no declarative automation, no scheduled rules, no "when transition then" |
| Permissions / roles / issue security / audit | none; single-user trust; FROB_WORKTREE guard prevents wrong-checkout mutation only; git history is the audit log | no permission schemes, roles, issue-level security, field-level edit rights; audit is per-field append-only entries for a subset of fields (not title, kind change only partly, state transitions not recorded in-ticket) |
| Attachments | images/files with sha256, clipboard | no previews, no size policy, no embedding in comments |
| Search / indexing | grep and a derived mtime cache | no index with ranking; load is a full directory parse |
| Import / export / REST / webhooks | `--json` on reads; no server in this subsystem (a daemon exists elsewhere) | no REST API, webhooks, CSV/Jira import-export |
| Multi-project / cross-project | fleet.toml status rollup and route-create | no cross-project backlog, shared sprints, or portfolio view |
| Service-desk features (SLA, queues, customer portal) | UNDISPATCHED staleness alarm for critical/high only | out of scope unless desired |
| Concurrency model | git-merge based; global ledger lock; incident-driven mirror and splice layers | the main architectural debt: per-branch ledgers make "current truth" ambiguous (display overlay, lease side channel, mirror commits, landing-time splice all exist to patch that) |

### 8.2 What v1 has that Jira lacks (keep as differentiators)

| v1 capability | Why it matters |
|---|---|
| In-repo, git-native, offline, diffable, greppable, no server | ticket history is code history; branches carry ticket state |
| Evidence-bound closure | done requires resolvable, passing, scope-covering test evidence, acceptance-criterion binding, mutation-evidence (TEST016), BUG002 repro that fails at parent, re-verification at close and land |
| Scope as an enforced write lease | glob-overlap proof, cross-worktree leases with TTL and staleness shapes, `wave` partitioning, `contention` report, mega-glob refusal; Jira has nothing equivalent |
| Worktree-per-ticket and land transaction | squash compose in a disposable worktree, CAS publish, completeness assertion, deletion filter, passenger detection, LAND-PROOF; merge queue with pollable per-intent records |
| Append-only audited changes with mandatory reasons | scope, triage, body, acceptance, evidence, kind, repro, lease overrides; force-overrides.jsonl; no silent weakening |
| Auto-composed Done report | Changed from git, Evidence from record, Captured claims from a real run; narrative-only human input |
| Anchors and live-tracker citation | tickets that must never close as waiver targets; close refuses while cited |
| Failure memory | Failure log so a dead end is not retried |
| Runs-last and milestone gating gates | dynamic ordering; MILE001..004 static deadlock checks |
| Fleet/agent ergonomics | brief generation (concurrent-lease do-not-touch list), cluster dispatch, agent env, wave, quarantine circuit breaker, deferred verification with debt records, token accounting per ticket |
| Draft ids and land-time finalize | collision-free concurrent filing from any worktree |
| Integrity machinery | content-loss guard, post-splice integrity check, TICK gates over the ledger itself (TICK001..TICK015), doctor scans |
| Cost accounting | per-ticket token usage mined from transcripts; points-per-hour and tokens-per-point |

### 8.3 Redesign hints distilled from the above (non-binding)

- Keep the per-ticket-directory unit of storage; decide ONE writer story for "the primary" instead of ledger + mirror + lease side channel + display overlay (these are four patches for one cause: branch-local state).
- Make state transitions first-class events (who, when, from, to, reason) in the ticket instead of mining git history; this also gives Jira-style resolution, comments and watchers a home.
- Replace freeform strings that drifted (sprint vs milestone; component; labels) with declared registries (sprint and release objects with dates and state) while keeping the bool+reason acknowledgement idiom.
- Lease model is the crown jewel: keep glob-overlap proof, TTL, staleness shapes, same-worktree exemption, additive-only registry carve-out; consider range/symbol-level leases for hot shared files.
- Treat `blocked` as derived from open blockers instead of a manually reachable state.
- Add typed links, assignee, comments and a query language early; they are the highest-frequency Jira features missing here.
- Evidence and gates are language-coupled (pytest node ids, ty, ruff); define an evidence-provider interface (cmd: entries are the seed) for a Rust tool that must also close Rust-only and docs-only tickets.
- Reduce land to: validate, compose out-of-tree, CAS publish, resync, record; make every other check a pluggable gate with a profile-controlled placement (critical path vs deferred watermark).
- Index (derived, rebuildable) from day one; v1 doable took >120s at 1.2k tickets.

## 9. Landmarks to read first when implementing

| Need | File |
|---|---|
| Field list and validators | <frob-v1>/src/frob/tickets/_models.py |
| State machine, doable, wave | <frob-v1>/src/frob/tickets/__init__.py, _doable.py |
| Leases | <frob-v1>/src/frob/tickets/_leases.py, _scope.py |
| Close guards | <frob-v1>/src/frob/tickets/_evidence.py |
| Land | <frob-v1>/src/frob/tickets/_land.py, _land_squash.py, _land_compose.py, _land_queue.py |
| Verb strategy table | <frob-v1>/src/frob/app/ticket_runner/_ledger_mirror.py |
| Start guard chain | <frob-v1>/src/frob/app/ticket_runner/_lifecycle.py |
| Design records | <frob-v1>/docs/design/ledger-v2.md, ledger-mirror-batching.md, land-*.md |
| Sample tickets | <frob-v1>/tickets/T-2451 (anchor + done report), T-6528 (scope audit), T-2371 (acceptance), archive/T-0001 |

## 10. Phase-2 coverage verdict

- Universe: 56 python modules + 27 runner files + 13 doc files + 4 sample tickets + CLI help for all 56 verbs.
- Covered with direct source or CLI evidence: data model, enums, state machine, lease record and TTL, verb table and
  mirror strategies, all verb flags, registry-file carve-out, start guard chain names.
- Covered from docs only (not verified in code): land step internals, queue internals, verify watermark/quarantine
  internals, profile ratchet thresholds, token accounting mechanics, flow/velocity mining, TICK/MILE gate details.
- Not covered: agent-playbook-appendix.md, docs/guides/landing.md, docs/modules/release.md, _worktree_sweep.py,
  _mutation_*.py, _reporting.py internals, clipboard backends, frob.gates ticket gates source.
- Pending: 0 enumerated nodes pending; the not-covered list above is a deliberate cut, not a blocked item.

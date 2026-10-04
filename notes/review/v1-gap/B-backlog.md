# v1 gap analysis, slice B: the v1 ticket backlog

Scope: v1/tickets/ (1243 ticket directories), with the 970 open tickets
(953 queued, 11 in-progress, 6 planned) clustered, classified against v2
and mined for failure modes that could recur. The 37 dropped tickets are
reviewed separately. Status vocabulary is the brief's (BUILT, TICKETED,
DESIGNED, DROPPED-ON-PURPOSE, MISSING) plus one label used only where it
is honest: V1-INTERNAL, meaning the ticket is about a Python-v1
implementation detail that has no v2 counterpart (no decision removes it;
the thing it fixes simply does not exist in a Rust rewrite).

Honesty statement, first: this is a cluster-level classification. I did
not read 970 ticket bodies. I read every open ticket title (970 of 970),
read the bodies of about 40 tickets chosen as the structurally
significant ones (critical audits, scope, land, evidence, hooks), and
verified each v2 claim below against v2/docs/design, the 477-ticket v2
ledger, or v2/crates. Cluster membership comes from title keyword rules
plus a manual override pass (roughly 150 ids reassigned by hand), so cluster counts are
good to a few tickets, not exact. Every ticket id is accounted for in the
Appendix. Where I say MISSING I searched at least two terms; the terms
are given.

## Headline

- Universe: 1243 v1 ticket directories (v1/tickets/T-*/; v1/tickets/archive/
  holds 3906 older archived ids and is out of the slice). Open: 970.
  Dropped: 37. Done: 236 (not in the slice).
- 421 of 970 open tickets need no v2 work: 192 are DROPPED-ON-PURPOSE
  (v1's sweep, queue, draft-id, scaffold and web-lint machinery, removed by
  D2, D7, D8, D25, boundaries.md 2.6) and 229 are V1-INTERNAL (Python gate,
  registry, strata-monolith and test-suite detail).
- 219 are already BUILT by redesign: v2's storage, land, lease and PM model
  removes the failure the ticket describes (real gaps remain, see Proposed
  tickets).
- 158 are DESIGNED in v2 but have no v2 ticket (language adapters, test
  runners, the hook binary, serve, docs/narrative rules, strata expressiveness),
  170 are MISSING (102 system-design/STORE lint tickets and 68 consumer-audit
  rule requests, both needing an owner decision about packs), 2 are TICKETED.
- The most valuable output is the recurrence list: of 34 failure modes the
  v1 tickets describe, v2's design already prevents 13, prevents 12 only
  partly and does not prevent 9. 17 proposed tickets close the 9 and the
  partial ones. The v2 repo's own history already shows the class recurring
  (~XGAS05X "closed as done with no evidence", ~NTKAXC1 "SCOPE001 blocks
  every land", ~CTKE1J4 lockfiles serialise tickets, all fixed).

## 1. Inventory

### 1.1 v1 ticket format (read first)

One directory per ticket: v1/tickets/T-####/ticket.md (YAML frontmatter,
then a markdown body whose first block is the problem statement and whose
later blocks are dated log sections, for example "## Drop reason - date"
or "## Unblock log - date") and, for 250 closed tickets, done-report.md.
Frontmatter keys seen across 1243 files: id, title, state (queued,
in-progress, planned, done, dropped), kind (bug, feature, docs, security,
ux, invariant, incident), origin (human, agent, auditor), priority (low,
medium, high, critical), tier (ticket, story, epic), parent, milestone,
sprint, scope (write-lease globs) with scope_changes audit log, acceptance,
evidence, blocked_by, points, tokens_*, runs_last, plus many ack/reason
fields. Ids are sequential T-#### plus T-draft-* drafts (the draft machinery
is itself the subject of about 24 open tickets). One file, T-6571, has the
literal text "---" inside its title, which breaks naive frontmatter
splitting; I handled it explicitly (it is queued, bug, medium).

### 1.2 Enumeration commands and counts

    ls v1/tickets | wc -l                      # 1245 = 1243 tickets + archive/ + attachments/
    ls v1/tickets/T-*/ticket.md | wc -l        # 1243
    # parse every ticket.md frontmatter (python yaml), group by state/kind/priority/tier

| State | Count |
|---|---|
| queued | 953 |
| in-progress | 11 |
| planned | 6 |
| done | 236 |
| dropped | 37 |
| total | 1243 |

Open set (970) by kind: bug 467, feature 372, docs 58, security 50, ux 15,
invariant 7, incident 1. By priority: critical 72, high 224, medium 632,
low 42. By origin: human 596, agent 366, auditor 7 (the auditor tickets are
the consumer-audit epics). By tier: ticket 878, story 47, epic 44.

Backlog hygiene facts that matter for import: 19 open tickets are exact
title duplicates of another open ticket (for example T-4161/T-4162,
T-6518/T-6519, ten pairs of "migration: split module X"); 11 of the 37
dropped tickets are duplicates of each other, and several were created by
the draft-adoption helper re-promoting a stale copy (T-5172..T-5175).

### 1.3 v2 reference set used

v2/docs/design/*.md (decision log D1-D87 in v2/docs/design/README.md), the
v2 ledger (477 tickets: 226 done, 9 in-progress, 242 todo; read with
`frob ticket list --json`), v2/crates/*, and v2/notes/v1/*.md (earlier v1
inventories, which already carry keep/merge/drop verdicts per verb and rule).

## 2. Clusters (open tickets, 970)

Disposition is the status of the capability the cluster asks for, judged
against v2. "Sub" rows split a cluster where its parts differ.


| Code | Cluster | n | kinds | hi/crit | Status | Why and v2 evidence |
|---|---|---|---|---|---|---|
| A1 | Auto-filed sweep residue, regressions, phantom-citation recoveries, fixture drift | 68 | b65,f3 | 30 | DROPPED-ON-PURPOSE | v1 files one ticket per post-land sweep residue and regression. v2 has no deferred sweep (tickets.md s10: no merge queue daemon, no deferred sweep, no mirror, no rapid debt; D8) and its land refuses only findings the ticket introduces (~QAFRXM3, done). The six 'Recovered from phantom TICK006 citation' tickets cannot occur: ULID ids, no drafts (D2, D24). |
| B1 | STORE / SYSDESIGN / GRAMMAR system-design lint family | 102 | f102 | 0 | MISSING | Searched v2/docs/design and v2/notes for STORE, SYSDESIGN, Redis, Mongo, Kubernetes, Terraform: only cicd.md binds kube-linter, tflint, checkov (D60) and packs.md has a sample pack. 102 feature tickets, none high priority, all filed 2026-09-25 from research docs; 12 siblings were already dropped as 'dynamic-only'. The carrying mechanism exists (packs D76, GRL D80). Needs an owner decision (PT-15), not 102 tickets. |
| B2 | Web-app lint families (WEBSEC, A11Y, SEO, COMPLY, SQL) | 27 | b5,f16,s5,u1 | 12 | DROPPED-ON-PURPOSE | Note-level, not a D-number: v2/notes/v1/gates-and-rules.md s11 recommends DROP from v2 core for all 249 web ids (half-built, product scope creep, delegates to axe/semgrep/lighthouse) and ship, if wanted, as an out-of-tree pack. The decision is not in the decision log; PT-15 records it. |
| B3a | Strata monolith split into modules (design/frob.strata) | 28 | f28 | 28 | V1-INTERNAL | Splits v1's single design/frob.strata file into per-module files. v2's .grmb is modular by construction (D65 includes, module / part of; D77 declared roots; grmb-spec.md). Ten of the 28 are exact duplicate titles of another. |
| B3b | Strata ratchet lock, kernel DECISION tickets, Story A-D, SF-nn | 27 | b6,d12,f8,s1 | 11 | V1-INTERNAL | SYS111 via-ratchet races, three shadow lock writers, 'six primitives vs 139 keywords' decisions. v2 has no one-way ratchet (rules.md s7), typed lock entries (D64), and the kernel questions are settled by D56-D58, D65, D75. |
| B3c | SYS rule bugs and design-quality rules | 25 | b21,f4 | 3 | BUILT | grimble-bind carries SYS001-012 (~EG1XSWC, ~T9R1B70 done; crates/grimble-bind/src/rules.rs). The v1 tickets are bugs in v1's Python SYS gates (false 'unbound', waivers inert under cache, 4x duplicate output); the failure classes are in Structural bugs 13-14. |
| B3d | V-model closure, TIER closers on strata, strata expressiveness asks | 35 | b11,d4,f18,s2 | 8 | DESIGNED | grmb-spec.md vmodel entity, binding.md, D75 capabilities; G16 (~QNDWNDM, todo) ports CLAIM and VMOD. Expressiveness asks (client-persisted storage capability, volatility=external, flow participation, CSP link) are not individually ticketed. |
| B4 | Consumer-audit rule and feature requests (security-kind asks, H3-, M-, L- items) | 77 | b8,d2,f24,i5,s37,u1 | 29 | MISSING (68) / BUILT (2) / DESIGNED (5) / TICKETED (2) | Rule content is MISSING. Carriers exist: GRL (D80), packs (D76), tool stages, exceptions budgets (D21). Mapped: BUILT T-3988 (TOOL001 tool-failed) and T-3965 (shellcheck as a tool stage); DESIGNED T-3992 (CI001, cicd.md), T-3969 (waiver budgets, exceptions.md s4), T-3959 (EXC008 on INV), T-4033 (milestone-2 claim directives, code-model.md s4), T-3955 (bash adapter, code-model.md s3); TICKETED T-3994 (~XV7331Q GATE001 policy-weakened), T-3973 (~YTQ622S, GRL error goldens). |
| C1a | Land machinery: queue, drain, coord drain/freeze, verify watermark, quarantine, saga, kernel decoupling, splice, curated landing | 70 | b27,d3,f39,u1 | 34 | DROPPED-ON-PURPOSE | v2 land is one synchronous transaction with CAS publish (D7, D8, D23, D25; tickets.md s10) and cli.md lists 'Removed from frob relative to v1: promote, renumber, sweep-async, job, land --status, ci, claude'. The coord PM items (velocity, plan, status) are covered by frob-pm: cycle velocity (~0AN408B), board (~4XZVMNC), forecast (pm-enforcement.md s5). |
| C1b | Land contract and state-sync bugs (preconditions, stale base, dry-run parity, mirror lag, Tier-A scope) | 37 | b30,d2,f5 | 17 | BUILT | crates/frob-land/src/land.rs: preconditions, dry-run, detached compose, CAS publish. v1's failure modes mostly vanish with the storage redesign; the ones that do not are Structural bugs 8, 12, 19, 22 and PT-1, PT-5, PT-6. |
| C2 | Ledger store, ticket verbs, draft ids, leases, merge driver, archive | 93 | b59,d3,f24,s1,u6 | 32 | BUILT | Redesigned: ULIDs (D2, D24), ledger commits by CAS onto a ref (D23), append-only events, merge driver (crates/frob/src/ticket/merge_cmd.rs), leases in the git common dir (D26, D47), reopen accepts dropped tickets (crates/frob-ledger/src/ops.rs reopen, since drop is category done). Structural bugs 2-4, 24-26 are prevented. Gap: PT-1. |
| C3 | Scope and lease semantics, SCOPE001/002 closure | 29 | b21,d4,f4 | 9 | BUILT | crates/frob-lease (overlap.rs, rule.rs SCOPE001), diff-based and per worktree; no import-closure rule exists so SCOPE002 explosions cannot recur. Gaps: bare-name, whitespace and zero-match globs (PT-2). |
| C4a | Per-language test runners and collectors (vitest, jest, cargo ids, kotlin, dotnet, Playwright) | 38 | b31,d1,f5,u1 | 12 | DESIGNED | tickets.md s9 lists pytest, cargo test, ctest, vitest, junit, command providers; milestone 1 ships nextest, command, file (crates/frob-evidence/src/provider.rs). code-model.md s3 gives each adapter a `runner` member. Not ticketed (PT-16). |
| C4b | Python test gates, coverage floors, xdist flakes, TEST0xx/COV0xx burn-downs | 31 | b22,f7,u2 | 9 | V1-INTERNAL | About v1's own test suite and Python-specific gates. v2 `coverage` is designed (cli.md row, M2) and unticketed. |
| C4c | Evidence semantics (frozen evidence, doc-anchor evidence, import-as-done, bare id resolution) | 7 | b4,f3 | 2 | BUILT | T-4119 prevented (evidence is an immutable event with its commit, tickets.md s2; Unmeasured on a terminal ticket is not a finding, s9). T-6585 import-as-done is `ticket close --no-evidence --reason` (audited evidence-bypass, tickets.md s9). T-4009 is PT-4. |
| D1 | Scaffold, project types, facets, templates | 27 | b10,d1,f16 | 11 | DROPPED-ON-PURPOSE | boundaries.md 2.6: 'scaffold templates | dropped for the product'; code-model.md: scaffold managed-block markers dropped with the feature. `frob init` (adoption, merge driver, knobs) is BUILT (crates/frob/src/init.rs). |
| D2 | Language support (C#/Unity, Zig, CSS/JS/Vue, tree-sitter walkers, per-language scanners) | 18 | b9,d1,f7,i1 | 2 | DESIGNED | code-model.md s3 lists adapters python, ts, c-family, jvm, dotnet, misc (zig bash css scss html vue); plugins.md s8 tier-4 adapter packs; binding.md B11 turns the Unity asmdef generator (T-4512) into a pack inference rule. Only rust, markdown, toml exist (milestone 1, D36); no ticket for any other adapter. |
| E1 | Hooks, frob-suggest, protect-secrets, MCP/serve, agent guards | 21 | b18,f3 | 5 | DESIGNED | architecture.md s7 and git-io.md s5: one `frob hook <event>` replaces v1's eight python processes per Bash call; cli.md rows `hook` and `serve`. No crate (no frob-hook, frob-serve) and no ticket. v1's measured hook quality (10.4 percent precision, 97.3 percent blind acks, T-5101) is the design input. PT-3. |
| E2 | Windows/macOS portability and CI infrastructure | 16 | b12,d1,f2,s1 | 4 | V1-INTERNAL | Mostly Python POSIX-primitive failures (fcntl, subprocess, path shape). v2's analogue is the D86 path discipline epic (~ATR5EP7, todo; ~EDPHHFS in progress) plus Windows CI jobs already hit and fixed (~G5RJY40, ~M4WWW00, ~0G8QF7V). |
| E3 | Release, versioning, vet, dependencies, doctor, typani/ruff tooling | 24 | b15,d4,f5 | 5 | V1-INTERNAL | Python packaging and tooling. v2 has release cut, lockstep bump, changelog, tag (frob-release crate; ~BZ9EG10, ~WSY4VA5, ~REL001/REL002 done); vet is grimble-vet (~RPQKHAV, todo). T-4001 (build identity) is the one live item (PT-9). |
| F1 | Docs, narrative placement, comment placement, docstring archaeology | 35 | b15,d12,f7,u1 | 5 | DESIGNED | documentation.md NARR rules, doc-consistency.md SYNC family (D20, D84); v2 has DOC001/DOC002 only (crates/frob-obligations). The 11 burn-down tickets are V1-INTERNAL; v2's repo starts clean. |
| F2 | PM model: tiers, velocity, due/rank, WIP, epics, milestones | 26 | b2,d3,f21 | 0 | BUILT | frob-pm (milestone, cycle, board, WIP, classes of service; ~YR8CA0D, ~ZERXHAH, ~ZQRNCXY done), pm-enforcement.md (D17, D19), releases.md (D83). T-5149 (v1.0.0 definition of done) is superseded by D83 and ~C28ECPV. T-4272 (cross-clone epic claims) is MISSING by an explicit design limit (tickets.md s3, leases invisible to other clones): PT-14. |
| G1 | Gate engine: false positives, wiring, registry, burn-downs, waivers, formatter | 98 | b68,d5,f18,i2,s3,u2 | 24 | V1-INTERNAL | The Python gate registry, WIRE/OPAQUE/REF text scans, burn-down campaigns, rapid-debt. Gone with the registry (rules derive, inventory registration, D3) and EXC (D21, D32). The failure modes they record are in Structural bugs 1, 13, 14, 15. |
| G2 | CLI surface and UX | 6 | b3,f3 | 4 | DESIGNED | cli.md (about 35 verbs, JSON envelope, exit codes, D13); T-4687 (52 verbs to a dozen) is superseded by it. |
| H1 | Refactor and architecture tooling (refactor split/move, frob-arch) | 5 | b5 | 0 | V1-INTERNAL | `refactor` is removed (cli.md 'Removed from frob relative to v1'); v2 architecture metrics live in grimble-arch. |
| | Total | 970 | | 296 | | |

Kind letters: b bug, f feature, d docs, s security, u ux, i invariant or incident. hi/crit counts priority high or critical.

Status tally by dominant label (cluster level, so approximate; B4 split by the mapped ids):

| Status | Tickets |
|---|---|
| DROPPED-ON-PURPOSE | 192 |
| V1-INTERNAL | 229 |
| BUILT | 219 |
| DESIGNED | 158 |
| MISSING | 170 |
| TICKETED | 2 |
| total | 970 |

## 3. Findings table (individually significant tickets)

Significant means critical priority, high-priority bug, in-progress or
planned, or an owner request. Every critical ticket (72) is in a row below
or in a row group by id range. The 130 high-priority bugs are covered at
cluster level (section 2), by the Structural bugs table (section 6), and are
starred in the Appendix; I did not write one row per high bug. Ticket ids
are v1 ids (v1/tickets/T-####/ticket.md); ~xxxxxxx are v2 handles.

| Item | v1 evidence | Status | v2 evidence |
|---|---|---|---|
| Consumer-audit epics: T-3919, 4109, 4113, 4117, 4135, 4157, 4166, 4175, 4182 (critical; the auditor-origin epics plus H3-3 outbound-flow destination and H3-9 module-docstring-versus-code), T-3920, 3928, 3942, 3984, 4025, 4036, 4089 (high) | Seven audit lists from consumer repos (logand.app-v2, apollo): "every HIGH sat behind green gates"; first-audit asks never built so defects recurred (T-3942) | Split: silent-zero primitive BUILT; rule-shaped remediation closable by fixing instances MISSING (PT-7); the per-rule asks MISSING (68 in B4) | must_measure and subjects_examined: v2/crates/frob-check/src/lib.rs, v2/crates/gob-ir/src/eval/program.rs, cli.md s2 (c). No finding kind whose done-condition is "a rule exists and is loaded": searched "rule is loaded", "rule exists", "closable" in v2/docs/design |
| Kernel decoupling epics: T-4651-4656, 4735-4741, 4598, 4662, 4664 | Ledger, lease, land, gate kernels, layering ARCH10x, trunk-assigned numbers | DROPPED-ON-PURPOSE | v2 is the decoupling: layered crates (D1, boundaries.md s6 dependency rules), ledger on a ref (D23), one synchronous land, ULIDs (D2). Nothing to carry |
| Module-split migrations T-4848-4874, 5086-5115 and Strata module system T-5081, 5102, 5104, 5116 (critical) | Split v1 design/frob.strata; per-module leases and locks | V1-INTERNAL | .grmb is modular (D65, D77); per-file lease plus symbol-level scope exists (tickets.md s3, D47) |
| WEBSEC T-5141-5144 (critical), T-5140, 5145-5148 | 249 reserved ids, 17k lines half built | DROPPED-ON-PURPOSE (note-level) | v2/notes/v1/gates-and-rules.md s11. PT-15 records it |
| T-5149 v1.0.0 definition of done (critical) | 72 tickets on milestone 1.0.0 across ten sprints, no definition | BUILT (superseded) | D83 releases.md (milestone is a release object with goal and exit criteria), ~C28ECPV version scheme, ~K0YKGNK milestone exit criteria bound to evidence |
| T-5153 sys stage took 1268 s of a 1900 s check (critical) | Per-file scoping did not skip the stage; N+1 shape | Prevented by design, watch | rules.md s4 targets (warm scoped under 1 s, warm full under 2 s); v2 already measured the same class: ~RS10WX7 (grimble check 17 s), ~A8AMNGF, ~AKMV3C3 (cold check 20 s of 29 s in file rules, todo) |
| T-5285 announce_shim logs INFO to stdout, breaking --json (critical); T-6571, 6536, 3809 | Log lines on stdout/stderr corrupting machine output | BUILT (by design) | architecture.md s5 (tracing to stderr, `-v`), cli.md s2 (envelope on stdout); no shims exist (cli.md "all deprecated aliases" removed) |
| T-5358 TICK015 requeues tickets waiting in the land queue (critical) | Liveness heuristic fought the queue | V1-INTERNAL | No queue, no liveness reaper; leases carry TTL and heartbeat (tickets.md s3) |
| T-6496, 6516, 6517 land critical (dir/id mismatch after promotion; stacked successor hunks silently dropped; non-landable state accepted) | 15 stacked worktrees lost a feature commit that stayed an ancestor | 6496: DROPPED-ON-PURPOSE (no promotion). 6517: BUILT in part (E-LAND-NOT-LEASED etc.). 6516: MISSING | Structural bugs 22, PT-6, PT-10. Searched "stack", "successor", "series" in v2/docs/design: no stacking concept |
| T-6518, 6519 verify OOM; T-6604 concurrent checks (critical, high) | Four 2 GB checks plus drain on a 23 GB host | MISSING (cross-process admission) | architecture.md s9: memory admission per process, "never a refusal". PT-8 |
| T-6535, 6543, 6589 fixer and read-only-verb corruption (critical) | `done-report` wrote 60 directive lines; land applied Tier-A fixes to the whole tree and squashed them under the ticket | DESIGNED (partial) | D78 and diagnostics.md: fixes only with --fix and within ticket scope; ~R5QDX7H (todo). No invariant test that read-only verbs leave the tree unchanged (searched "porcelain", "read_only" in v2/crates tests). PT-5 |
| T-6537 land evidence collected through tool venv python (critical) | Wrong interpreter produced wrong verdicts | V1-INTERNAL | v2 evidence runs `[evidence] allowed_tools` argv templates (tickets.md s9) |
| T-6545, 6549 runner aliasing, exit-code-only PASS (critical) | PASS recorded when the filter selected nothing | BUILT for nextest, DESIGNED for the rest | v2/crates/frob-evidence/src/provider.rs `matched_no_tests`, E-EVIDENCE-NO-TESTS (error.rs). Other runners PT-16; skipped tests PT-13 |
| T-6590, 4513 C#/Unity project type (critical, owner directive 2026-09-16) | Unity detection by asmdef | DESIGNED | binding.md B11; code-model.md s3 dotnet adapter. Not ticketed (PT-16) |
| T-3004 strata as the language of software development (high epic) | V-model spec graph | DESIGNED | grimble-model.md, grmb-spec.md, binding.md (D58, D65, D66) |
| T-3542 82 percent of main is ledger chore churn (high, owner) | History dominated by `tickets(update)` commits | BUILT by redesign | D79 orphan ticket branch; D23 ledger ref |
| T-3053 land is a hand-compensated saga across four stores (high) | Four stores, compensation code | BUILT by redesign | tickets.md s10: one transaction, detached compose, CAS publish |
| T-3611 write-path latency, LandInProgress starvation (high epic) | One drop refused for about 3 hours behind back-to-back lands | PREVENTED, one residual | Ledger commits are CAS retries, not blocked by land (tickets.md s2); land lock waits poll without FIFO (crates/frob-land/src/lock.rs POLL 25 ms): PT-17 |
| T-4001 two builds both report 0.530.0 (high) | Consumer bug unverifiable against main | MISSING | `frob --version` prints 0.0.0 with no commit; releases.md names dev assets by sha but the binary does not report it. Searched "build id", "--version", "sha" in v2/docs/design. PT-9 |
| T-4007 one-way profile auto-ratchet with no record (high) | Strictness changed silently | DROPPED-ON-PURPOSE | rules.md s7: "There is no one-way ratchet" |
| T-4036, 4069 rule-shaped remediation closed by fixing instances; gates satisfied by making code worse (high) | LARGE001 cleared by deleting comments; 13 waivers in prod source for a styling diff | MISSING | PT-7 |
| T-3927 scope conflates write lease with evidence coverage; stale leases (high, 9 consumer findings) | Four reports of stale leases blocking, requeue detonating a guard | BUILT | `evidence_scope` is a separate field (tickets.md s3 data model row "scope"); lease TTL, heartbeat, steal with reason, release on terminal transition (tickets.md s3) |
| T-4050 scope denominator (high epic) | Five defects: zero-match glob, import closure, subtractive mirroring, ledger writes counted, whole-branch diff | BUILT for 4 of 5; gap on glob quality | frob-lease SCOPE001 over the ticket diff (~470ARGM, ~NTKAXC1 done); no mirror, no closure rule. Gap: PT-2 |
| T-3984 subject-count primitive (high) | "0 findings over 0 subjects" indistinguishable | BUILT | Same as row 1 |
| T-4119 evidence re-resolved against current tree (high) | A later rename broke a closed ticket | PREVENTED | Evidence is an append-only event with commit (tickets.md s2, s9) |
| T-5101, 3924, 3284, 3817, 3831, 5085, 5098, 5099 hooks (high) | frob-suggest precision 10.4 percent; blanket ack used 97.3 percent; secrets hook blocks commands that mention a file | DESIGNED | architecture.md s7; git-io.md s5. No crate, no ticket. PT-3 |
| T-4272 cross-clone epic claims (owner request, medium) | Remote collaborator claims an epic; offline-safe; expiry observable | MISSING (explicit design limit) | tickets.md s3: leases are "invisible to other clones and machines". PT-14 |
| T-3849, 3894 typani discarded-Result lint, 649 propagate sites (high) | Python typani adoption | V1-INTERNAL | Rust has `#[must_use]`; clippy discarded-result lints are the analogue |
| T-4687 CLI surface 52 verbs to a dozen (high story) | Debloat | DESIGNED (superseded) | cli.md: about 35 verbs; notes/v1/cli-surface.md keep/merge/drop table |
| T-4691, 3022, 2994 narrative migration (high) | 447 comment blocks over 15 lines | DESIGNED | documentation.md NARR rules (D20); v2 repo starts clean |
| T-3068 TDD commit protocol xfail(strict=True) (in progress, high) | Test-first commit protocol | DESIGNED | tickets.md s3: bug needs a repro that fails at parent; not built: PT-4 |
| In-progress set (11): T-3068, 5444, 5633, 5642, 5784, 5785, 6391, 6531, 6538, 6589, 6590 | land, coord, ci, LAYOUT wiring, C# project type | Covered by C1a, C1b, G1, D2 rows | none individually |
| Planned set (6): T-5758, 5766, 5770, 5774, 5776, 5817 | TIER lint, reclassification, promote verbs, milestone closer | BUILT/DESIGNED | frob-pm and pm-enforcement.md s1 (hierarchy), D83 |

## 4. Dropped tickets (37)

Method: read the "Drop reason" block of each of the 37. Result: none was
dropped for a reason that makes it worth porting as is.

| Reason class | Count | Ids | Worth in v2 |
|---|---|---|---|
| Duplicate or re-filed (same title, draft re-promoted by the adoption helper, crashed rerun) | 11 | 5172-5175, 5238, 5269, 5272, 5278, 5298, 5769, 6586 | No. The cause (draft ids re-promoted from stale worktree copies) cannot occur with ULIDs (D2, D24). T-6586 (`--points` silently dropped) is a live failure mode: prevented by the TicketField derive (~A7J9FD5, done) |
| Landed inside a sibling ticket ("absorbed by") | 11 | 4581, 5202, 5203, 5267, 5268, 5283, 5288, 5293, 5430, 5759, 3049 | No. Two (5267, 5293) show a land that lands content but loses its ledger record, after which an empty re-land refuses: v2 land returns `already` for a landed ticket (cli.md verb table), so no residue |
| Dynamic-only STORE rules ("becomes a frob:tests / EXPLAIN-style obligation, never a static rule") | 12 | 6389, 6409, 6428, 6431, 6443, 6452, 6464, 6466, 6468, 6473, 6494, 6497 | Principle worth keeping, no ticket: runtime-only claims are discharged by bound evidence of a declared kind (v2 already does this for `frob:idempotent`, code-model.md s4). Record it in PT-15 |
| Resolved without a fix | 3 | 5192 (blocker cleared), 5231 (tests pass), 5460 (already implemented) | No |

Nothing in the dropped set was dropped only for a v1 reason that v2
would want back. T-3049 (one canonical schema for decisions, invariants and
review records, folded into T-3048 "no monofiles") is covered: v2 validates
invariant frontmatter (migration.md s1) and binds MADR ADRs (D20).

## 5. Proposed tickets

Priorities are v2 priorities. Each cites the v1 evidence. Given/When/Then
is the acceptance.

### PT-1 close must refuse done on a ticket with unlanded scope changes (bug, high)

Why: v1 T-4052: `ticket close` succeeded with the ticket's code still
uncommitted, so a ticket read done on main with no code. tickets.md s3 states
the rule ("a ticket whose scope changed files reaches done only through
land") but the guards that exist are E-CLOSE-OUTCOME (crates/frob-ledger/src/guards.rs)
and E-EVIDENCE-MISSING (crates/frob-evidence/src/guard.rs); I found no guard
implementing it (searched "only through", "NeedsLand", "through land").
v2 already hit this class: ~XGAS05X (closed as done with no evidence).
- Given a ticket in-progress whose worktree has changes inside its scope or whose branch has commits not on the ledger ref, When `frob ticket close <id>` runs with outcome done or fixed, Then it exits 3 with E-CLOSE-NEEDS-LAND naming `frob land <id>`, and with outcome wont-fix, duplicate or invalid it still succeeds on a reason alone.
- Given a ticket with an empty diff (evidence-only work), When closed with measured evidence, Then it closes.

### PT-2 scope entries are linted when written (feature, high)

Why: v1 T-3841 (bare filename `admin.py` matched only the root, agents had to widen), T-3978 (a glob matching zero tracked files accepted silently, six instances), T-4174 (an entry containing a space matches nothing), epic T-4050. v2 `normalize` (crates/frob-lease/src/overlap.rs) and `matcher` use literal-separator globs, so a bare name matches only the root, and a space is accepted. tickets.md s3 deliberately allows globs for files that do not exist yet (`src/newmod/**`), so the lint must be advisory for those.
- Given `ticket update --scope admin.py` where only `src/app/admin.py` exists, When applied, Then the envelope carries a warning LEASE-BARE-NAME with the suggested `**/admin.py`.
- Given an entry with whitespace, When applied, Then it is refused (E-LEASE-BAD-GLOB) naming the entry.
- Given an entry matching no tracked file and no path declared new, When applied, Then a warning LEASE-MATCHES-NOTHING is returned; it is not an error.

### PT-3 frob hook <event>: guard rules with measured precision and a decision log (feature, high)

Why: designed (architecture.md s7, git-io.md s5, cli.md rows `hook`, `grimble vet --hook`) but no crate and no ticket. v1 T-5101 measured frob-suggest at 10.4 percent precision, FROB_SUGGEST_ACK used blindly in 97.3 percent of uses, double registration doubling the attempt counter, no logging; T-3924: the secrets hook blocked commands that merely named a protected file; T-3284, 3817, 3831: false positives on `find -name`, any `sed -i`, one-file `ruff check`. v1's five hook classes: raw commands bypassing accounting, long backgrounded commands, agents dirtying the shared root, unwatched pollers, lost telemetry (notes/v1/ops-and-integrations.md s6.5).
- Given a hook corpus of recorded agent commands with expected verdicts, When `frob hook pre-tool` is run over it, Then precision is at least 90 percent on the block verdicts and the corpus test fails below that.
- Given a command that names `.env` without reading it, When evaluated, Then it is allowed; a command that reads it is denied.
- Given any block, allow or ignored-override decision, When it happens, Then one line is written to the telemetry log with rule id, verdict and override token; overrides are per-rule tokens, never a blanket variable.
- Given the hook is registered twice, When invoked, Then the attempt counter increments once.

### PT-4 bug repro guard: fails at the parent commit, with an explicit tri-state (feature, high)

Why: tickets.md s3 and s9 say a bug needs a repro that fails at the parent commit; no code does (searched "parent commit", "repro" in v2/crates/frob-evidence and frob-ledger). v1 T-4008 (score zero over an empty subject set, skip flag does not lift it), T-4009 (a brand-new test is NO_VERDICT at the parent, `--designate-repro-force` needed every time), T-4168 (file absent at parent), T-6549 (PASS when nothing ran).
- Given a bug ticket whose repro test does not exist at the parent commit, When evidence is recorded with `--test-first`, Then the record carries verdict `fails-by-absence` and satisfies the guard only when the ticket declares test-first.
- Given a repro that passes at the parent, When closing, Then it is refused with the measured parent verdict shown.
- Given zero subjects examined at the parent run, When evaluated, Then the outcome is Unmeasured, never Passed.

### PT-5 standing invariant: read-only verbs leave tree and index unchanged (test, high)

Why: v1 T-6543 (`done-report` without --fix wrote 60 directive lines), T-6589 (land applied Tier-A fixes to the whole tree and squashed them under the landing ticket), T-6535 (fixer corrupted Python). v2 design (D78) allows fixes only with `--fix` and in scope, but nothing asserts it across verbs.
- Given the verb table in cli.md, When a test runs every verb marked read-only, or run without --fix, against a fixture repository with a fixable finding, Then `git status --porcelain` and the index tree hash are identical before and after.
- Given `frob check --fix`, When it applies a machine fix, Then only files inside the current ticket scope change and each skipped out-of-scope fix is listed with the `lease widen` command.

### PT-6 land content proof: every ticket-owned hunk is present in the published tree (feature, medium)

Why: v1 T-6516 (critical): after the base squash-landed, a merge resolved away successor hunks while the commit stayed an ancestor ("ancestry says the work is there, the tree says it is not"); T-3194 (land-proof pointed at a code-empty commit); T-3896 (post-merge re-verification missed tests the merge broke). v2 land prints LAND-PROOF (tickets.md s10) but nothing in crates/frob-land checks content.
- Given a branch whose change to path P is resolved away by the compose merge, When land runs, Then it refuses with E-LAND-HUNK-LOST naming P, before the CAS publish.
- Given a normal land, When it publishes, Then LAND-PROOF includes the count of ticket-changed paths verified against the published tree.

### PT-7 rule-kind finding closure and the cheapest-clearing-action audit (feature, medium)

Why: v1 T-4036: "an audit finding whose remediation is a policy rule must not be closable by fixing the instances" (the checked_mul rule was hand-fixed at the listed sites and the gap recurred); T-3942: three first-audit asks were never built; T-4069: three gates satisfied by making code worse (LARGE001 cleared by deleting comments, AFFECT001 by 13 waivers in production source, PARSE002 by adding casts). Searched "rule is loaded", "closable", "cheapest" in v2/docs/design and v2/notes: nothing.
- Given a ticket with `closes = rule:<id>`, When closed, Then the guard requires that `frob check --only <id>` lists the rule as loaded and that its example corpus (fire and clean cases) exists.
- Given a new rule proposal, When a rule is registered, Then the rule page records its cheapest clearing action and the registry refuses a rule whose cheapest action is deleting documentation, adding a waiver, or adding an exception.

### PT-8 cross-process admission for full checks, and stage progress (feature, medium)

Why: v1 T-6518 (four concurrent 2 GB checks plus a drain on a 23 GB host, harness reaping loops), T-5153 (one stage took 21 minutes with no visible progress, agents gave up), T-6604 (refuse a second concurrent full check per worktree). v2 reduces pool size per process but "never a refusal" (architecture.md s9) and has no cross-process coordination; N agents each running a full check multiply memory.
- Given one full check running in a worktree, When a second starts, Then it exits 3 retryable E-CHECK-BUSY naming the pid and elapsed time, or joins with `--wait`.
- Given available memory below the per-check estimate measured from recent runs, When a full check starts, Then it defers or refuses with the numbers.
- Given a TTY, When a check runs longer than 10 s, Then per-stage elapsed lines appear on stderr.

### PT-9 build identity in `--version`, the envelope and doctor (feature, medium)

Why: v1 T-4001: two different builds reported 0.530.0 so a consumer's report could not be checked against main. v2 `frob --version` prints `frob 0.0.0`; dev assets carry the sha in file names (releases.md) but the binary does not.
- Given a build from commit C with a dirty tree, When `frob --version --json` runs, Then it reports version, commit, dirty flag and channel (release, dev, local).
- Given `frob doctor`, When a sibling binary or the merge driver differs in commit from the running frob, Then it reports the skew with both ids.

### PT-10 decide stacked (series) tickets: support or refuse with a remedy (design, medium)

Why: v1 shows demand and pain: T-3842 (a series worktree of three sibling leaf tickets cannot land), T-3839, T-4049 (sibling tickets sharing a worktree), T-6516 and T-6517 (critical: 15 stacked successor worktrees lost content; auto-start a queued stacked leaf). v2 has one worktree per ticket and blocked-by links but no stacking concept (searched "stack", "series", "successor" in v2/docs/design).
- Given a ticket B blocked-by A where A has not landed, When `frob work B` runs, Then the outcome is documented and tested: either B branches from A's tip and lands only after A (with PT-6 proof) or `work` refuses with E-WORK-BLOCKED and the command to wait.
- Decision recorded as a D-number.

### PT-11 a directive in a file with no scanned language is reported (feature, medium)

Why: v1 T-3858 (`frob:waive` silently inert in files with no registered grammar), T-6532 (a waiver applies on one run and not the next, cache), T-5344 (directive-shaped text in string literals rewritten). v2 scans by language (crates/gob-directives/src/scan.rs takes a Language) and binds only comment lines (D44); EXC013 and EXC002 report stale or unmatched exceptions, but a directive in an unscanned file is never seen (searched "inert", "no grammar", "not scanned", "unsupported" in v2/docs/design and crates/gob-directives).
- Given `frob:accept RULE because="x"` in a `.sh` file with no adapter, When `frob check` runs, Then DSL004 (Warn, required) reports the directive as inert with the language it would need.
- Given the same directive in a recognised file, Then no DSL004.

### PT-12 code-changing tickets with zero acceptance criteria (decision then rule, medium)

Why: v1 T-4031: a ticket with zero criteria passes the acceptance check vacuously and lands. v2 tickets.md s9 states the opposite on purpose: "a ticket without criteria passes with a warning"; PM005 requires criteria only for stories. v2's own history shows the cost (~XGAS05X).
- Given `[pm] done_requires` default and a task or bug with no criteria, When closed, Then it refuses with E-CLOSE-NO-CRITERIA unless `--no-evidence --reason` is used; docs and chore types keep the warning.

### PT-13 skipped, ignored and xfail tests never satisfy evidence (feature, medium)

Why: v1 T-3975 (satisfaction must exclude xfail/xpass/skip by default), T-4247 (a bound test that skipped must be reported with its reason). v2's nextest provider rejects "no tests to run" (provider.rs) but I found no handling of skipped or `#[ignore]` bound tests (searched "skipped", "ignored" in crates/frob-evidence/src).
- Given a bound test marked `#[ignore]`, When evidence is recorded for it, Then the record lists it as skipped and does not satisfy that criterion.

### PT-14 advisory cross-clone epic claims (feature, medium, owner request T-4272)

Why: owner request in v1, scheduled after the alpha. Constraints from the v1 ticket: never on the checking path, offline-safe with a displayed cache age, one ref per claim (mutual exclusion by CAS push, not one shared file), liveness defined by evidence of work not heartbeat alone, observable expiry, audited stealing, and an unreachable network must never look like an empty claim set. v2 leases are local by design (tickets.md s3); the ticket branch (D79) is the natural carrier.
- Given two clones, When clone A claims epic E, Then clone B's `frob ticket doable` shows E as claimed by A with the age of the view.
- Given the remote is unreachable, When `doable` runs, Then it answers from the cache and says "claims as of <time>, remote unreachable", never an empty set.
- Given a claim with no commit, land or transition for `claim_ttl_days`, When another user takes it, Then a `steal` event records who, when and the previous last evidence.

### PT-15 record the disposition of web-app and STORE/SYSDESIGN families (decision, low)

Why: 129 open v1 tickets (B1 102, B2 27) plus 12 dropped ones. The only verdict is a note (v2/notes/v1/gates-and-rules.md s11). The research that backs B1 lives in v1 docs and is not in v2.
- Given the decision log, When PT-15 closes, Then a D-number states: these families are out-of-tree packs on the D76 mechanism, not core; the v1 research docs and rule lists are preserved under v2/notes/; the dynamic-only principle (runtime claims are bound evidence, never static rules) is stated.

### PT-16 ticket the designed-but-unticketed surfaces the v1 backlog proves are wanted (chore, medium)

Why: v1 demand for these is 158 tickets. Designed in v2, no ticket: language adapters python, ts, c-family, jvm, dotnet, misc (code-model.md s3); test providers pytest, vitest, jest, junit, ctest (tickets.md s9); `frob hook` and `frob serve` (PT-3); `fleet`, `coverage`, `stats` verbs (cli.md); NARR and SYNC rule families (documentation.md, doc-consistency.md); token and cost capture (tickets.md s8, v1 T-5132, 5279).
- Given the design docs, When PT-16 closes, Then each listed surface has a milestone-2 ticket with an acceptance and a v1 evidence link.

### PT-17 FIFO fairness for land.lock waiters (feature, low)

Why: v1 T-3611 (window starvation under a five-agent fleet) and T-3270 (wall-clock timeout racing contention). v2 land waits by polling a flock every 25 ms (crates/frob-land/src/lock.rs), unfair under contention; ~3WMXBBJ covers lease waits only.
- Given three waiting lands, When the holder releases, Then the oldest waiter acquires; `--wait` timeouts report queue position.

### PT-18 ticket-id alias scanning needs a token boundary (bug, low)

Why: v1 T-4015 and T-4209: `UT-2207` read as a citation of `T-2207`, the sweep auto-filed phantom citations. v2 persists full ULIDs (D24) but keeps v1 `T-0042` aliases resolving (migration.md s3).
- Given text `UT-0042` or `SIT-0042`, When TICK rules or alias resolution scan it, Then no alias match is produced.

### PT-19 must_measure is declared explicitly on every rule (chore, low)

Why: v1 T-3984 and T-4008 (silent zero over empty subject sets). The mechanism is built, but rules.md s2 shows `must_measure = false` as a default a rule author can leave in place.
- Given a rule derive without an explicit `must_measure`, When compiled, Then compilation fails like a missing `polarity`.

## 6. Structural bugs

Failure modes the v1 backlog records, with whether v2's current design
prevents them. PREVENTED = prevented by design or built code (cited);
PARTIAL = mechanism exists but a gap remains; NOT = not prevented.

| # | Failure mode | v1 evidence | v2 verdict | Cite / ticket |
|---|---|---|---|---|
| 1 | Silent-zero gate: green because it examined nothing | T-3984, 4008, 3202-3205 | PARTIAL | must_measure BUILT (frob-check lib.rs, gob-ir program.rs); opt-in default false: PT-19 |
| 2 | Draft ids, promotion renames, dangling citations, phantom TICK006 | T-3359, 3929, 4101, 5415, 6496, 6605, 5127-5129 | PREVENTED | D2, D24: full ULID only, no drafts or promote |
| 3 | Ledger writes captured by a stale worktree or cwd; mirror divergence | T-3983, 4002, 4261, 3958, 3340, 6608, 4164 | PREVENTED | tickets.md s2 (repository from the git common dir, never cwd); D23 ledger on a ref by CAS; no mirror to root |
| 4 | Killed or hung ledger verb leaves a partial write or duplicates | T-4022, 4048, 4134, 6579, 3710, 5290, 3639, 4200 | PREVENTED | Events are append-only files committed atomically by ref CAS (D23, D46); `--idempotency-key` (D34); `new` runs no unbounded post-analysis |
| 5 | Scope computed over the wrong denominator | T-4050, 4004, 4032, 4049 | PREVENTED | SCOPE001 over the ticket diff (frob-lease rule.rs; ~470ARGM, ~NTKAXC1 done); one worktree per ticket; no closure rule |
| 6 | Scope globs that match nothing, bare names, spaces | T-3841, 3978, 4174 | NOT | overlap.rs normalize accepts them: PT-2 |
| 7 | Vacuous acceptance: zero criteria passes | T-4031 | NOT (by explicit design) | tickets.md s9 "passes with a warning": PT-12 |
| 8 | Ticket closed done with its code unlanded | T-4052 | NOT (designed guard unbuilt) | tickets.md s3 vs guards.rs: PT-1 |
| 9 | Runner records PASS when nothing ran | T-6549, 6607, 4042, 6550 | PARTIAL | nextest BUILT (E-EVIDENCE-NO-TESTS, provider.rs); other runners unbuilt: PT-16 |
| 10 | Skipped, ignored or xfail tests satisfy evidence | T-3975, 4247 | NOT | PT-13 |
| 11 | Bug repro for a new test is NO_VERDICT at the parent; empty subject set scores zero | T-4008, 4009, 4168 | NOT (designed, unbuilt) | tickets.md s3, s9: PT-4 |
| 12 | Read-only verbs mutate the tree; fixers rewrite the whole tree and squash under one ticket; fixer corrupts files | T-6543, 6589, 6535, 6521, 6573, 6578 | PARTIAL | D78 design, ~R5QDX7H todo; no cross-verb invariant: PT-5 |
| 13 | Text or regex scan where AST or call graph is needed | T-4151, 4160, 3405, 5462, 6596 | PARTIAL | v2 rules run over tree-sitter and U with Unresolved (D57, D62); doc rules scan markdown text; no dev lint against source-text regex in rules. Watch item, no ticket |
| 14 | Waivers inert, nondeterministic or deleted while live | T-3858, 6532, 3888, 4005 | PARTIAL | EXC013 stale, EXC002 never-matches (exceptions.md s6), cache keyed by engine (D85, ~1EZ3QHP done); unscanned file gap: PT-11 |
| 15 | Closed rule registry; wiring a rule needs edits in four places | T-3854, 4990, 5375, 3239, 4575, 4580, 4736, 6600 | PREVENTED | D3: derive plus inventory registration; docs and schemas generated; GEN001 (D50) |
| 16 | Remedy text names commands or anchors that do not exist | T-3859, 4020, 4061, 4141 | PARTIAL | ~992AN0Q done (test every remedy against the CLI registry); ~S4GVE49 todo (structured remedies) |
| 17 | Path and glob platform shape (normcase, separators, verbatim paths) | T-4099, 4124, 4011, 4357, 3076 | PARTIAL | paths.md D86; epic ~ATR5EP7 todo, ~EDPHHFS in progress |
| 18 | Stale caches, stale graph snapshot, diff base is stale local main | T-4484, 6597, 6611, 5152, 5162 | PREVENTED | D30, D85 (~1EZ3QHP done); base is the configured ledger ref (D8STDJR done) |
| 19 | Land lock timeouts and starvation under a fleet | T-3270, 3611, 5358 | PARTIAL | land synchronous, bounded `--wait`; no FIFO: PT-17; ~3WMXBBJ (lease waits) todo |
| 20 | Full-check memory blowup from concurrent processes | T-6518, 5153, 6604 | PARTIAL | per-process admission only: PT-8 |
| 21 | Two builds report one version | T-4001 | NOT | PT-9 |
| 22 | Content lost in a merge of stacked or aligned branches while ancestry looks fine | T-6516, 3194, 3896 | PARTIAL | no stacking, but also no content proof: PT-6, PT-10 |
| 23 | Ticket-id matching without a token boundary | T-4015, 4209 | PARTIAL | ULIDs fix new ids; aliases remain: PT-18 |
| 24 | A flag is accepted and silently dropped | T-5283, 6586, 3898, 4017 | PREVENTED | TicketField derive (~A7J9FD5 done), clap-typed verbs (cli.md) |
| 25 | Automatic strictness change with no durable record | T-4007 | PREVENTED | rules.md s7: no one-way ratchet |
| 26 | Closed ticket's evidence re-resolved against the current tree | T-4119 | PREVENTED | Evidence is an immutable event with commit; Unmeasured on a terminal ticket is not a finding (tickets.md s9) |
| 27 | A gate is cleared by making the code worse | T-4069, 4036 | NOT | PT-7 |
| 28 | Hooks: low precision, blanket bypass, no decision log, double registration | T-5101, 3924, 3284 | NOT (designed, unbuilt) | PT-3 |
| 29 | Log output on stdout corrupts --json | T-5285, 6536, 6571, 3809 | PREVENTED | architecture.md s5: tracing on stderr; envelope on stdout |
| 30 | Duplicate filings from retries and helpers | T-5172-5175, 4161/4162, 19 open duplicate pairs | PARTIAL | ULIDs remove collisions; dedupe only with `--idempotency-key` or an identical request (D34) |
| 31 | A tool stage that cannot run reports nothing | T-6601, 3202 | PREVENTED | TOOL001 tool-failed Unresolved (rules.md s4); ~APQCEPT done |
| 32 | Stale leases from parked branches block live work | T-3927 (F-127, F-133, F-142, F-118) | PREVENTED | TTL, heartbeat, steal with reason, release on terminal and requeue (tickets.md s3) |
| 33 | Shared registry and lock files serialise parallel tickets | T-4120, 4598 | PREVENTED | `scope_mode = append` and `[lease] shared_files` (tickets.md s3; ~CTKE1J4 done). Seen once in v2 already |
| 34 | Cross-clone claim state; unreachable network looks like an empty set | T-4272 | NOT (explicit limit) | tickets.md s3: leases invisible to other clones: PT-14 |

Tally: PREVENTED 13 (2, 3, 4, 5, 15, 18, 24, 25, 26, 29, 31, 32, 33),
PARTIAL 12 (1, 9, 12, 13, 14, 16, 17, 19, 20, 22, 23, 30), NOT 9
(6, 7, 8, 10, 11, 21, 27, 28, 34).

## 7. Open questions

1. Do the 970 open v1 tickets get imported at all? migration.md s1 imports
   every ticket. This analysis says 421 would arrive as noise (192 dropped
   on purpose plus 229 v1-internal) and 170 are MISSING-by-scope. Proposal:
   import done and dropped as history, import queued tickets only for
   clusters marked BUILT/DESIGNED/MISSING with a requirement, and bulk-close
   the rest as wont-fix with a pointer to this file. Owner decision.
2. B1 and B2 (129 tickets): out-of-tree packs, dropped, or core later (PT-15)?
3. Stacked tickets (PT-10): is a stack a supported workflow or a documented non-goal?
4. Zero acceptance criteria (PT-12): v2 chose warn on purpose. Is that
   still right for task and bug types given ~XGAS05X and v1 T-4031?
5. Hook scope (PT-3): is `frob hook` Claude-Code-specific or harness-neutral,
   and who owns the guard rules (frob or the harness config)?
6. T-4272 cross-clone claims (PT-14): in M1 scope or after the mirror?
7. Is the v1 notes-level verdict (v2/notes/v1/gates-and-rules.md) binding?
   Several DROPs I relied on (web families, `run`/`build` task runner
   T-4759, `[commands]`) are notes, not D-numbers.
8. T-4759 and T-1382 (a `[commands]` table and a `run` verb, "decouple from
   the Makefile"): v2 has `[[check.tool]]` stages but no task runner; I
   treated it as out of scope. Confirm.
9. Cluster counts are keyword-based. If the owner wants exact per-ticket
   dispositions for import, that is a second pass over 970 bodies and
   should be a scripted triage (`frob migrate tickets` plus a cluster map),
   not hand classification.

## 8. Appendix: every open ticket id, by cluster

Completeness proof for the open set: the 25 cluster rows below partition
the 970 open ids (checked: sum of cluster sizes = 970, no id repeated,
every id from the enumeration is present). A trailing * marks critical
or high priority. Ids are v1 ids without the T- prefix.

### A1 (68): Auto-filed sweep residue, regressions, phantom-citation recoveries, fixture drift

3503 4126 4400* 4497* 4500* 4567 4573 4600* 4601* 4606* 4610* 4617* 4992
5089 5100 5127* 5128* 5129* 5158 5159* 5163* 5165* 5168* 5213 5229 5248*
5252* 5260 5262 5263 5264 5265* 5266 5271 5273 5276 5277 5282 5310 5312*
5314 5318 5327 5328 5330* 5336 5338* 5340 5342* 5343 5348 5355 5367* 5368*
5385 5387 5422 5442* 5444(ip) 5447 5449* 5455* 5457* 5458* 5459 5527 5629
5742*

### B1 (102): STORE / SYSDESIGN / GRAMMAR system-design lint family

6388 6390 6392 6393 6394 6395 6396 6397 6398 6399 6400 6401 6402 6403 6404
6406 6407 6408 6410 6411 6412 6413 6414 6415 6416 6417 6418 6420 6421 6422
6423 6424 6425 6426 6427 6429 6430 6432 6433 6434 6435 6436 6437 6438 6439
6440 6441 6442 6444 6445 6446 6447 6449 6450 6451 6453 6454 6455 6456 6457
6458 6459 6460 6461 6462 6463 6465 6467 6469 6470 6471 6472 6474 6475 6476
6477 6478 6479 6480 6481 6482 6483 6484 6485 6486 6487 6489 6490 6491 6492
6493 6495 6500 6501 6502 6503 6504 6505 6506 6508 6509 6510

### B2 (27): Web-app lint families (WEBSEC, A11Y, SEO, COMPLY, SQL)

3814 4034 4077 5140* 5141* 5142* 5143* 5144* 5145* 5146* 5147* 5148* 5365*
5402 5443 5445 5446 5488 5490 5496 5500 5508 6526 6534* 6536 6540* 6610

### B3a (28): Strata monolith split into modules (design/frob.strata)

4848* 4853* 4855* 4856* 4857* 4863* 4869* 4870* 4871* 4874* 5081* 5086*
5087* 5091* 5093* 5094* 5097* 5102* 5103* 5104* 5109* 5110* 5111* 5112*
5113* 5114* 5115* 5116*

### B3b (27): Strata ratchet lock, kernel DECISION tickets, Story A-D, SF-nn

3833 3862* 3990 4242 4598* 4662* 4664* 4665* 4666* 4667* 4668* 4670 4671*
4672* 4674 4676 4681 4804* 4996 5033 5037 5074 5076 5077 5078 5079 5080

### B3c (25): SYS rule bugs and design-quality rules

2676 2837 3213 3821 3824 3825 3826 3827 3828 3832 4063 4296 4330 4994 4995
4997 5214 5425 5427 5462 5483 6532* 6533* 6584* 6592

### B3d (35): V-model closure, TIER closers on strata, strata expressiveness asks

3004* 3239 3504 3815 3822 3823 3853* 3915 3916* 3920* 4071* 4109* 4127 4157*
4189 4202 4209 4216 4218 4222 4232 4245 4250 4253 4530 5155 5180 5182 5345
5768 5771 5797 6511* 6514 6600

### B4 (77): Consumer-audit rule and feature requests (security-kind asks, H3-, M-, L- items)

3919* 3928* 3942* 3952* 3954* 3955* 3959* 3960* 3963 3965 3966* 3967 3968
3969* 3970* 3971 3972 3973 3974 3975* 3976 3977 3981 3984* 3987 3988* 3991
3992 3994 3996 4025* 4033 4035* 4038* 4039 4072* 4074 4075 4076 4078 4079
4080 4081 4089* 4090* 4091 4092 4093 4094 4095 4096 4113* 4117* 4135* 4166*
4175* 4182* 4188 4190 4192 4211 4215 4217* 4220 4223 4225 4226 4227* 4228
4229 4231 4233 4237 4238 4239 4249 4252*

### C1a (70): Land machinery: queue, drain, coord drain/freeze, verify watermark, quarantine, saga, kernel decoupling, splice, curated landing

1686 3053* 3102 3193 3221 3459 3505 3564 3611* 3728 4051* 4062* 4357 4410*
4504 4575* 4580* 4603 4609 4651* 4652* 4653* 4654* 4655* 4656* 4738* 4739*
4740* 4741* 4772 4810 5106* 5156* 5178 5249* 5250* 5251* 5253* 5255* 5281*
5358* 5438 5489 5492 5520 5532 5630 5631 5632 5633(ip) 5637 5638 5639 5708
5784(ip) 5785(ip) 5816 6512 6513 6515* 6516* 6517* 6518* 6519* 6537* 6572
6595 6605 6607* 6608*

### C1b (37): Land contract and state-sync bugs (preconditions, stale base, dry-run parity, mirror lag, Tier-A scope)

2886 3194 3270 3319 3340 3882 3883 3896* 3939 4029 4152* 4164* 4194 4206
4261* 4300 4571* 5162* 5256* 5424 5461 5636 5642(ip) 6496* 6507 6529*
6538*(ip) 6539* 6544* 6548* 6573* 6582 6589*(ip) 6593 6597* 6604* 6611

### C2 (93): Ledger store, ticket verbs, draft ids, leases, merge driver, archive

0969* 2856 2889 3226 3282 3313 3329 3337 3357 3359 3377 3542* 3559 3620 3639
3710 3789 3800 3835 3836 3838 3873 3898 3902 3929* 3946 3957 3958* 3978*
3983* 3998* 4002* 4006 4010 4017 4021 4022* 4031 4048* 4052* 4061 4066 4068*
4086* 4097 4098 4101 4120* 4134* 4140* 4141* 4180* 4198 4199 4200 4247 4364
4383 4422 4640 4648* 4685 4721 4724 4735* 4737* 4743* 4766* 4910 5085* 5149*
5154 5157 5160 5176 5204 5290* 5415 5757 5770(pl) 5791 5819 6498* 6542*
6543* 6575 6577 6579* 6580 6581 6594* 6602* 6609

### C3 (29): Scope and lease semantics, SCOPE001/002 closure

3127 3299 3300 3304 3775 3839 3841 3842 3918 3926 3927* 3944 3949* 4004*
4032 4049 4050* 4100* 4123 4128 4129 4144* 4156 4174* 4283 4311 5152* 5756
6499*

### C4a (38): Per-language test runners and collectors (vitest, jest, cargo ids, kotlin, dotnet, Playwright)

2835 3351 3723 3834 3921 3932 3933 3945 3999 4040 4042* 4045* 4053* 4058
4059 4070* 4149 4203 4541 4558 4608* 4643 4644 5270 5297 5423 5480 5487 5523
6521* 6535* 6545* 6549* 6587* 6590*(ip) 6591 6603 6606*

### C4b (31): Python test gates, coverage floors, xdist flakes, TEST0xx/COV0xx burn-downs

1273* 1661 1953 3068*(ip) 3278 3331 3352 3729 3864 3869 3950 3951 4007*
4008* 4014 4161 4162 4168* 4176* 4363 4389 4484* 4720 5171 5179* 5388 5426
5468 5519 6541* 6596

### C4c (7): Evidence semantics (frozen evidence, doc-anchor evidence, import-as-done, bare id resolution)

3063 3234 4009 4119* 6547 6550* 6585

### D1 (27): Scaffold, project types, facets, templates

3262 3307 3330 3335 3415 3513 3719 3804 3805 3806 3807 3808 4084 4757* 4759*
4762* 4765* 4768* 4769* 4771* 4773* 4774* 4809* 4989 5090* 5107 6588

### D2 (18): Language support (C#/Unity, Zig, CSS/JS/Vue, tree-sitter walkers, per-language scanners)

1597 1598 1607 1608 2799 2894 3231 3321 3872 3917 4003 4016* 4067* 4513 4679
5386 5390 5391

### E1 (21): Hooks, frob-suggest, protect-secrets, MCP/serve, agent guards

2963 3229 3284 3306 3334 3714 3803 3817 3831 3904 3924* 3938 4082 4574 5098*
5099* 5101* 5254* 5437 6571 6576

### E2 (16): Windows/macOS portability and CI infrastructure

1382 2939 2982* 3076 3267 3274 3659* 3783 3811 3923 3936* 4011 4124 4268
5812 6601*

### E3 (24): Release, versioning, vet, dependencies, doctor, typani/ruff tooling

2802 3073 3083 3327 3602 3716 3717 3718 3809 3849* 3850 3894* 4001* 4169
4181 4213* 4259 4332 4717* 5092 5096 5205 6530 6546

### F1 (35): Docs, narrative placement, comment placement, docstring archaeology

1609 1778 2752 2803 2987 2994* 3022 3248 3309 3317 3318 3323 3355 3418 3860
3866 3867 3874 3876 3877 3897 4187 4193 4204 4418 4423 4466 4605 4691* 4716*
4807* 4808 5095 5375 6448*

### F2 (26): PM model: tiers, velocity, due/rank, WIP, epics, milestones

2964 3002 3241 4272 5279 5284 5706 5715 5717 5718 5748 5755 5758(pl) 5760
5761 5763 5765 5766(pl) 5772 5774(pl) 5775 5776(pl) 5780 5817(pl) 6405 6419

### G1 (98): Gate engine: false positives, wiring, registry, burn-downs, waivers, formatter

1820 1831 2202 2371 2377 2451 2819 2962 2998 3048* 3091 3202 3203 3204 3205
3269 3310 3312 3332 3333 3338 3343 3381 3405 3663 3703 3739 3758 3812 3813
3816 3829 3830 3854* 3855* 3858* 3859 3863 3868 3870 3871 3875 3878 3880
3881 3888* 3889 3911 3982 3989 4005* 4012* 4015* 4020 4036* 4043 4044 4054
4064 4069* 4083 4087 4099 4133 4151* 4158 4160* 4165 4196 4205* 4224* 4235
4248 4370 4371 4385 4533 4647* 4686 4703* 4736* 4742* 4950 4990 5153* 5177
5344* 5470 5526 5747 5798 6391(ip) 6524* 6531*(ip) 6574 6578* 6583 6599*

### G2 (6): CLI surface and UX

3840 3879* 4687* 4811* 5088 5285*

### H1 (5): Refactor and architecture tooling (refactor split/move, frob-arch)

3573 3646 3660 3677 5181

### Dropped (37), reviewed in section 4

3049 4581 5172 5173 5174 5175 5192 5202 5203 5231 5238 5267 5268 5269 5272
5278 5283 5288 5293 5298 5430 5460 5759 5769 6389 6409 6428 6431 6443 6452
6464 6466 6468 6473 6494 6497 6586

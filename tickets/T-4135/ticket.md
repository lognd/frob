---
id: T-4135
title: 'consumer backlog F-315 through F-338: 24 untriaged findings including four
  whole verbatim audits'
state: queued
kind: bug
origin: auditor
created: '2026-09-07'
priority: critical
parent: null
tier: epic
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: given the 24 findings in this epic, when it is decomposed, then each has either
    its own leaf ticket or recorded evidence attached to an existing open ticket,
    with the choice stated per finding
  evidence: []
- text: given the four verbatim audits, when they are decomposed, then each produces
    one leaf per finding with a note saying whether its rule can be fixture-tested
    in frob's own tree
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
TWENTY-FOUR UNTRIAGED CONSUMER FINDINGS, F-315 THROUGH F-338, accumulated in
logand.app-v2 while the fleet was working other tickets. Filed as one epic rather
than twenty-four separate tickets deliberately: filing is currently expensive
(T-4134 -- every filing runs three unbounded analyses after announcing success,
and under fleet load they contend on a shared cache lock), so twenty-four
filings would cost hours and add to the very load that makes them slow. One
epic, decomposed once by a planner, is the cheaper and more accurate path.

F-337 IS ALREADY FILED as T-4134, with our own first-party reproduction attached.
Do not re-file it. Everything else below is untriaged.

FOUR OF THE TWENTY-FOUR ARE WHOLE VERBATIM AUDITS, not single findings, and each
will decompose into several leaves of its own -- the same shape as T-4109, which
came from this consumer's backend audit and produced nine leaves:

    F-317   shell round-3 audit
    F-325   edge/ops round-2 audit
    F-326   process round-2 audit
    F-327   API contract audit

Treat those four as sub-epics. The remaining twenty are individual findings.

CLUSTERS I CAN SEE FROM THE TITLES ALONE, offered as a starting point and NOT as
a substitute for reading each one:

  COST AND CONCURRENCY UNDER FLEET LOAD -- F-329 (a ticket verb exceeding even a
  600s foreground budget under load, and recording a partial result when re-run),
  F-332 (filing exceeding a 120s harness budget twice for one ticket, with no
  obvious safe retry). These are the same family as T-4134 and may share its fix;
  check before filing separate work. The re-run-records-a-partial-result half of
  F-329 is the more dangerous claim and should not be folded away.

  LEASE AND SCOPE CONTENTION ON SHARED FILES -- F-321 (an in-progress ticket's
  lease on a shared design file blocking every other ticket), F-323 (findings
  attributed to whichever ticket touched a shared doc), F-331 (mirrored ticket
  files conflicting on merge because transitions are mirrored to the main branch
  mid-ticket). F-323 is closely related to T-4127, already open; read that first.

  DIRECTIVES ACCEPTED SILENTLY WHEN MALFORMED -- F-318 (a free-text symref in a
  test-binding directive accepted silently while breaking collection counting),
  F-333 (a multi-line waiver whose continuation lines lack the comment prefix
  silently failing to attach). Both are the silent-zero class applied to our own
  comment DSL: the directive is present, looks right, and does nothing. These two
  deserve priority above their apparent severity.

  CALL-GRAPH BLIND SPOTS -- F-330 (the wiring gate unable to see callers through
  a tuple-of-callables dispatch table, plus a size rule firing on the resolver
  that works around it), F-335 (no call edge recorded for a direct call to a new
  helper). Note the shape: in F-330 the gate's blindness forced a workaround, and
  a second gate then fired on the workaround. That is the wrong-incentive class.

  WRONG TOOL, WRONG CONFIG, WRONG TREE -- F-328 (the land's type stage running a
  PATH-resolved checker at one version instead of the project venv's at another,
  and refusing a ticket on that basis), F-338 (a nested project config shadowing
  the root test configuration so a test passes in one invocation and fails in
  another). F-328 is close to a defect already in the queue about gates executing
  a target project's code in frob's own interpreter; check for overlap.

  MESSAGES THAT MISLEAD -- F-315 (a stale-lock reclaim message that reads as an
  active lock), F-319 (a behind-main warning giving wrong advice on a parked
  branch), F-322 (a V-model test id parsed as a ticket id).

  NO-EXIT AND CANNOT-CLOSE -- F-316 (filing a follow-up ticket makes the scope
  gate fire on the new ticket's own files), F-324 (a docs-only correction hitting
  a confirmatory-evidence rule and needing a waiver to close), F-336 (a
  strata-only ticket unable to close because no touched code symbol exists).
  Every one of these is a rule demanding something the subject structurally
  cannot provide. The class already has thirteen recorded instances; these are
  candidates fourteen through sixteen.

  CITATION AND ID ROT -- F-334 (draft ids promoted only inside the ticket tree,
  leaving citations in code comments and baseline files pointing at dead ids).
  This is the same mechanism as T-4101, already open; attach rather than re-file.

DECOMPOSITION GUIDANCE
- Read every finding's own text before trusting the clustering above. The titles
  compress badly and I have not read all twenty-four bodies.
- Check the existing queue before filing each leaf. At least four of these name
  mechanisms that already have open tickets (T-4101, T-4127, T-4134, and the
  interpreter-isolation defect). Attaching evidence to an open ticket is worth
  more than a duplicate.
- The four verbatim audits get the T-4109 treatment: one leaf per finding, real
  scope per leaf, and an explicit note per leaf saying whether its rule can be
  fixture-tested in frob's own tree at all.
- Say per leaf which are consumer-blocking now versus latent.

VERBATIM REPORT FOLLOWS, F-315 THROUGH F-338.

## F-315 -- a stale-orphan land.lock reclaim message reads like an active lock

T-0279's agent retried the dry-run ten times because each run printed
"reclaiming orphaned land.lock -- prior holder pid ... confirmed NOT
running" (left by my killed T-0274 land, X-045) and its retry condition
matched the word lock. The reclaim is informational and should be
worded as such ("stale lock removed"), and the orphaned lock should be
cleaned up once, not re-reported on every invocation.

## F-316 -- T-0285 agent friction: filing a follow-up ticket makes gate:SCOPE report SCOPE001 on the new tickets/T-xxxx files

Every agent that files a follow-up sees SCOPE001 for the new ticket
directory and has to either scope-add it or explain it away (T-0285,
T-0271, T-0274). Files under tickets/ created by frob ticket new
should be exempt from the filing ticket's scope check.

## F-317 -- shell round-3 audit 2026-09-06: what frob or strata should have caught (verbatim)


- H-1 -- Nothing checks that a --check script exists in the build
  chain. frob check has no notion of "this module exports a check*
  gate that no entry point calls". A rule that flags an exported
  check*/*Check symbol in frontend/scripts/ with no reference
  from package.json scripts would have caught both halves. The
  allowlist desync specifically would be caught by an invariant of the
  form frob:invariant PUBLIC_ALLOWLIST == git ls-files frontend/public
  -- the comment already states it in prose, which is the tell.
- M-1 -- SYS100 scanned main, where frontend/scripts/github-metadata.ts
  does not exist; the file lives only on the parked branch. This is
  FROBLEMS F-039's shape again: the strata ceiling is evaluated against
  main while the code that needs the grant sits on a branch that cannot
  land. The gate is structurally blind to every capability this branch
  introduces. Nothing short of running frob sys audit against the
  worktree fixes that.
- M-2 -- No gate models "a check that exits 0 for two different
  reasons". A frob:invariant on checkGithubMetadata asserting that a
  "degraded" outcome still compares the "ok" subset would be the
  testable form; UT-1616 covers the degrade path but asserts only exit
  code, so it passes on the broken semantics.
- M-3 -- The frob:todo T-0225 at media-manifest.ts:149 is doing
  its job (the gap is recorded, not silent). What is missing is that
  TODO001 does not escalate when a frob:todo describes an *unwired
  gate* rather than unwritten code. A severity bump for frob:todo on a
  file exporting a check* symbol would surface it.
- M-4 -- A doc-drift check over ALLOWLIST.txt would need it to be a
  frob-acked doc; it is a plain text file with no frob:doc edge, so
  DRIFT001 cannot see it. The stronger rule: DEC-003 is a decision record
  with concrete assertions ("four files"), and nothing binds a decision
  record to a verifiable predicate. frob:invariant on
  projectVideo call count vs. the deleted-file count would have caught
  it.
- M-5 -- The V-model has no row for the 404 status, so vmodel closure
  is satisfied. This is a genuine spec hole rather than a gate miss:
  L3/L5 describe every route's *content* and nothing describes the
  origin's *status* for a non-route. An L3 SIT row asserting
  GET /nonexistent -> 404 would close it and give frob check --only
  vmodel something to bind.
- M-6 -- The strata carries "contact.email" annotation
  (logand-app.strata:58) exists precisely to let a taint rule check
  PII-source -> client_storage sink on the browser node, and the
  comment says so ("Declaring it here gives a future taint rule ... a PII
  source to check the client_storage grant below against"). That rule was
  never written. ForgotPassword.tsx:212 -> logging.ts ->
  localStorage is a two-hop flow a taint rule would flag directly.
  This is the single highest-value rule to add from this audit.
- M-7 -- formErrors.ts documents its consumers in prose
  ("COMP-1801/1802/1803/1804") and Portal (COMP-1805) is simply absent
  from that list. A REF002-style rule inverted -- "every page under
  src/pages/auth/ that catches an error must import
  mapErrorToDisplay" -- is an eslint rule, not a frob one, and would
  have caught it in one line.
- M-8 -- The eslint rule T-0247 added is scoped to src/api/ and
  matches on identifier *suffix*. Me in src/app/hooks/useMe.ts evades
  both. A rule that instead bans the & intersection of an
  ApiResponseBody<...> with an object literal type -- anywhere -- would
  target the actual anti-pattern rather than a naming convention. The
  deeper miss is that no gate checks whether backend/openapi.json
  matches the live FastAPI app; SIT-014 asserts it
  (docs/spec/L3-system-integration-test-plan.md:32) but that test lives
  on the backend and the frontend's types:check compares the frontend
  to the snapshot, not the snapshot to the app.
- L-2 -- SYS101 (unobserved capability) is the right gate and it is
  waived wholesale for the browser node
  (logand-app.strata:59-62, waive "SYS101:fetch_url" ... ticket "T-0002").
  The waiver is honest -- the code is on a branch -- but it means a
  *stale* grant and a *not-yet-landed* grant are indistinguishable. When
  T-0002 clears, re-check this specific via entry.

---


## 2026-09-06 frob (T-0297)

### F-039-b SYS100 cannot observe either T-0297 file (parked branch)
- command: frob check --only sys /home/logan/projects/logand.app-v2/.claude/worktrees/t-0297
- observed: T-0297 adds via-list grants for frontend/scripts/github-metadata.ts
  (process_tooling::fetch_url, process_tooling::net.connect) and removes
  frontend/src/pages/public/GithubRepoCard.tsx from browser::fetch_url. Neither
  file exists on main -- both live on the parked sub-15-web-shell branch -- so
  SYS100 (declared-but-unobserved / observed-but-undeclared) cannot see either
  side of this change on main at all; gate:SYS reads clean only because it has
  nothing to check the new grant or the dropped grant against.
- expected: same shape as F-039 -- SELFAUDIT/SYS100 has no cross-branch
  visibility, so a via-list edit for code that lives only on a parked branch is
  unverifiable by the gate until that branch lands. The lock's via_sha256 test
  (test_capability_via_globs_match_lock) is what actually caught drift here,
  not SYS100.
- severity: friction (known limitation, same class as F-039)
- ticket: none yet (bound to the existing T-0002 planned-capability waiver
  umbrella on process_tooling; no new waiver needed since this is a via-list
  edit, not a new SYS101 finding)

## F-318 -- a free-text symref in a frob:tests directive is accepted silently and breaks collection counting for the file (T-0295)

The agent wrote frob:tests <test description> (prose instead of
file::Symbol) in three source files; the parser did not reject it, but
TEST002/collection counts for those files went to zero until the
directives were rewritten in the test files with the correct form. A
DSL001-style syntax error at parse time would have named the lines.

## F-319 -- frob ticket start's "N commits behind main, merge main" warning is wrong advice on a parked branch

T-0298's agent followed the start-time suggestion to git merge main
into a worktree cut from sub-15-web-shell; it pulled in main-only files
and produced spurious SCOPE001s because the gate runs with
--base sub-15-web-shell. The warning should name the ticket's declared
base (or the branch the worktree was cut from), not main.

## F-320 -- evidence runs on a worktree with symlinked node_modules quarantine TS1005/TS1490 findings from node_modules/typescript/lib/lib.dom.d.ts

A T-0290 evidence run quarantined two TypeScript findings whose file is
inside node_modules (the symlinked sub-15 toolchain). node_modules is
never repo code; the verify queue should exclude it (or honor the
tsconfig exclude) instead of asking a human to dispose findings about
the compiler's own lib files. Disposed to T-0168 with the parked batch.

## F-321 -- an in-progress ticket holding a lease on design/vmodel.strata blocks every other ticket's spec-table regen

T-0293 edited an L3 table and could not commit the regenerated
vmodel.strata because T-0295 held the file lease; it reverted the regen
and filed T-0303 just to regenerate later. The generated file is an
artifact of any spec edit, so its lease should be shared (or the regen
should be a land-time step frob performs), not an exclusive per-ticket
scope item. Same family as F-292/F-309.

## F-322 -- TICK006 reads the V-model test id "UT-1516" as a ticket filing "T-1516"

T-0250's done report lists the spec rows it edited, COMP-1514, UT-1516.
TICK006 now reports "T-0250's Done report claims T-1516 was filed ... a
phantom filing trail". The ticket-id regex is matching inside UT-1516
(no word boundary before T-), so every done report that names a UT-/
SUBT-/SIT-/CT- row with a four-digit number becomes a phantom filing.
The match should require a word boundary, and "filed" claims should be
read from the Filed: line only, not anywhere in the report.

## F-323 -- SCOPE002 attributes every component anchored in a shared L5 doc to whichever ticket touches that doc

T-0290 edited one row (COMP-1605) of SUB-16-public-pages.md and SCOPE002
demanded frontend/scripts/licenses.ts and prerender.ts be in scope, because
the same doc anchors COMP-1608/1610/1613/1616. Row-level closure (only the
COMP rows the diff touched) would stop this; the agent did not widen scope.
(Reported by the agent into the worktree's gitignored FROBLEMS.md, which
vanished with the worktree: F-041 class. Re-logged here.)

## F-324 -- bug-kind docs-only correction hits BUG002/TEST016 "EvidenceConfirmatoryOnly" and needs a waive to close

T-0304 corrected stale L5 rows (kind=bug, because the doc was wrong) and
bound the existing e2e test as evidence. close refused with
EvidenceConfirmatoryOnly because the test passes before and after -- true
for every doc-only bug. The agent waived BUG002 with an honest reason. A
kind: docs bug-of-documentation, or exempting tickets whose diff is
docs/spec-only, would avoid the routine waive. Also: frob ticket evidence
--accepts N is rejected when placed before the positional node id but
accepted after it (argparse ordering, F-253 family).

## F-325 -- edge/ops round-2 audit: what frob/strata should learn (verbatim from docs/security/audit-2026-09-06-edge-ops-round2.md; tickets T-0306..T-0311)


H2-1 (config file not mounted). design/logand-app.strata:84 declares
node edge : trusted with the comment at :88 deferring everything to
SUB-01-edge.md -- there is no capability, flow, or policy that says the edge
node *reads files*, let alone which ones. The ops node (:203-210) grants
may "fs.read" via "ops/" but a may describes what code is allowed to do,
not what a deployment actually provides. The missing rule is a *provisioning*
edge: strata needs the notion "node N's runtime artifact set" and frob needs to
be able to compare the files a config artifact references (here, import
targets in ops/caddy/*.caddy -- a two-line regex, no Caddyfile grammar
required) against the container-side paths a compose service mounts. Even
without a grammar, a shipped rule "every relative import/include target
inside a file under a code glob must be reachable from the mounts declared for
the node that runs it" would have caught this the moment T-0113 landed. Note
this is *not* the "frob has no Caddyfile grammar" excuse from round 1 (M-1's
learning line): the check is a path-set comparison between two files frob
already reads as text.

H2-2 (URL credential parse). design/logand-app.strata:215-216 waives
REL201:f_ops_backup / f_ops_postgres because "the REL201 proof reads Python
only (FROBLEMS F-059); permanent until frob scans shell", and :206 waives
SYS101:exec over the whole node. The blanket waiver is doing far too much
work: it now covers timeouts, argv-secret hygiene *and* parsing correctness in
the one script that stands between the business and total data loss. The rule
that would have caught it is not a scanner but an invariant: a
frob:invariant on COMP-2105 phrased "the postgres credential parsed from
DATABASE_URL round-trips for any legal userinfo" would have had no evidence to
bind to and surfaced as INV001, because the existing UT-2105d only ever tests a
password with no reserved characters. Generalisable lesson, same as round 1's
H-3: when a component's only tests use the happy-path fixture value, frob
should be able to say so -- "no bound test varies input X" is checkable from
the test source for parameter-shaped inputs.

M2-1 (restore runbook). tests/unit/test_ops_runbooks.py::test_runbook_structure_and_refs
(UT-2109) is the bound evidence and it checks structure plus *file/service
existence*. It cannot distinguish "this path exists in the repo" from "this
path exists in the namespace the command runs in", which is the entire defect.
frob-side rule: for a documented command, classify each path argument by the
execution context the command establishes (docker compose exec / run =
container namespace; bare shell = host) and check it against that context's
declared mounts. That is a real feature, not a config tweak -- the cheap
bounded version is a lint that flags any host-side path under a mount point
that compose declares as a *named volume*, which is a literal string comparison
against docker-compose.yml's volumes: map.

M2-2 (SITE_DOMAIN unset). The test asserting the override's behaviour
(test_override_minimal_diff) supplies SITE_DOMAIN itself as extra_env, so
the config's required-input contract is satisfied by the test harness and never
by the deployment. This is a general anti-pattern frob can name: a config
artifact declares required environment inputs ({$VAR} placeholders without a
usable default), and every consumer of that artifact -- compose service, CI job
-- must supply them. Rule: "extract {$VAR} placeholders from files under a
code glob; every service that mounts the file must define each VAR, or the
file must supply a default that the test does not override." strata could carry
this as a per-node requires "env" names ... clause, the environment mirror of
the existing may "env" capability -- which today says only that the node may
*read* env, never which names it needs.

M2-3 (no Cache-Control). Pure V-model closure failure, and one
vmodel_gen.py could catch today: SIT-010's runnable column names
tests/e2e/test_edge.py::test_routing_and_caching, which does not exist in the
repository, and SIT-040/041/043 name test_edge.py/test_ops.py node ids that
do not exist either. The V-model gate is at 0 findings, so it is evidently
accepting non-existent pytest node ids as closure. Rule: frob check --only
vmodel must resolve every runnable cell to a collectable pytest node id
(pytest --collect-only -q once per run, set-compare) and report an unresolved
one as a closure violation. That single rule turns four silently-unverified SIT
rows into findings.

M2-4 (deploy smoke check / unbuilt image). frob.toml declares
.github/workflows/*.yml a refs.entrypoint, exempting it from REF001/REF002,
and design/logand-app.strata:205 folds .github/ into ops. Round 1's H-4
taught the repo to check *pinning* inside workflow YAML
(test_ops_workflows.py), which proves the file is machine-checkable -- the
missing checks are semantic rather than structural: (a) every image name a
deploy script pulls is an image some job pushes (a within-file string-set
comparison), and (b) a smoke-check URL must not name a route whose handler
declares require_admin (a cross-file check frob is well placed to do, since it
already resolves route symbols for the SIT-011 guard inventory). Frame (b) as
the general rule: "an unauthenticated caller asserts success against a guarded
route" is a contract violation frob can see, because both halves -- the curl and
the Depends(require_admin) -- are in its index.

M2-5 (no backup alert). COMP-2105's spec row asserts a control ("failure ->
admin alert via the backend's alert endpoint") that no line of the component
implements, and UT-2105..2105e bind five real tests to the component without any
of them touching alerting. This is the round-1 H-3 lesson recurring in a
different component: frob counts bound cases but cannot tell that a *clause* of
a design row has no test. Rule: treat each comma-separated responsibility clause
in an L5 component row as a claim requiring at least one bound test whose
name/docstring references it, and report an unbacked clause -- a coverage gate
over prose, which is what the frob:invariant mechanism is nearly already for.
The cheapest immediate version: require every L5 component row to declare which
UT covers each clause, so an uncovered clause is a table-shaped, mechanically
checkable hole.

M2-6 (busybox vs GNU head). No gate anywhere knows which shell/userland a
script executes under: ops/backup.sh's shebang says #!/bin/sh, the strata
ops node grants may "exec", and UT-2105e runs shellcheck -- but shellcheck
with the default sh dialect does not flag head -n -N as a non-POSIX
extension. Rule: bind each shell component to its *runtime image* (the backup
script's is ops/backup.Dockerfile's alpine:3.20) and run its shellcheck with
the matching dialect plus a busybox-compatibility list -- or, cheaper and
stronger, run the script's own dry-run unit tests inside that image. strata
could express this as an attribute on the node (runtime "alpine:3.20")
alongside the existing code/may clauses; today nothing connects a script to
the userland it will actually run on, which is the same class of gap as H2-1
(nothing connects a config file to the container that must contain it).


## F-326 -- process round-2 audit: what frob/strata should learn (verbatim from docs/security/audit-2026-09-06-process-round2.md; tickets T-0312..T-0317)


For each HIGH/MEDIUM: why no gate caught it, and the rule that would have.

H2-1 (path-only branch resolution) and H2-2 (:: splitting). This lives entirely in
repo-side python because frob does not resolve runnable at all (FROBLEMS F-004, F-013
item 4) -- round 1 already asked for VMOD002. Round 2 adds a sharper requirement: a
resolver that frob owns would resolve against the union of the configured
(( test.runner )) collectors, which know their own id grammar (pytest's ::, cargo's
::-qualified module path, vitest's title), so no repo would ever hand-write a splitter
per language and get Rust wrong. The rule: VMOD002 must resolve a runnable via the
runner that owns its file extension, never a generic string split. Secondary rule, the
one that would have caught H2-1 specifically: a resolution result must record WHICH
predicate it satisfied, and a gate must report the count per predicate -- "46 of 212
resolved by filename alone" is a number no one could have seen without instrumenting the
resolver by hand, which is how it hid.

H2-3 (red ratchet on main). frob has no concept of "this repo's own test suite is
currently failing on the default branch". frob check --ticket does not run pytest here at
all (round-1 M-7, still true), so nothing in the ticket loop observes it. Rule:
TESTRUN001 (a configured (( test.runner )) that produced no tool result is a finding),
already asked for in round 1, plus BASE001: a ratchet/baseline file tracked in the repo
whose current violation count exceeds its baseline is a check failure reported by name at
land time, so a red ratchet blocks the next land rather than accumulating.

H2-4 (lock entry deletion). SYS111's ratchet is frob's, but the via_sha256 layer is a
repo-side test invented to patch it (round-1 M-5). A repo-side test guarding a repo-side
lock file is inherently circular: the agent can edit both. Rule: frob must own the
capability-ceiling lock -- the via digest belongs in frob's own SYS111 state, with
SYS111 failing on a declared grant that has no lock entry ("unlocked ceiling") as loudly
as on a changed one. Until then the general rule: a lock file must enumerate a closed set
-- every subject present in the source must appear in the lock, or the lock must name the
exemption explicitly. "Missing entry means not my concern" is never a safe default for a
ratchet.

H2-5 (build-step ordering). No gate anywhere models the build as a pipeline with inputs
and outputs, so "this generator writes a file that an earlier step consumed" is invisible.
Rule: a (( generated )) declaration (round-1 M-2's GEN001) should carry produces and
consumed_by, and frob should fail a build script whose declared producer runs after its
declared consumer. Cheaper repo-side approximation available today: a unit test over
package.json's build string asserting that every generator writing under src/ or
public/ appears before vite build.

M2-1 (no fetch timeout). strata has the vocabulary -- the backend's health probe carries
an explicit REL200/REL201 timeout obligation at design/logand-app.strata:105-113 -- but a
may "net.connect" via <file> grant carries no obligation of its own, so T-0297 could add
the capability without the timeout. Rule: SYS/REL should require every net.connect /
fetch_url grant to declare a timeout attr, and flag a grant that declares none. That is
a one-line model change with repo-wide reach.

M2-2, M2-6 (checks that cannot fail). Both are round 1's cross-cutting theme recurring
in a new subsystem: a gate green because it examined nothing (all-degraded) or examined
what it just wrote (tautological). Rule, restated and now twice-earned: every check must
report its subject count, and a zero (or self-produced) subject count on an enforcing check
is itself a finding. For build scripts specifically: a --check step whose inputs were
written by an earlier step of the same command is a configuration error.

M2-3, M2-4, M2-5 (generated-file content loss). GEN001 as proposed in round 1 checks
freshness only. Rule: a generated file's check must be bidirectional (nothing in the
output that the input no longer justifies) and monotonic where the generator's inputs are
environment-dependent (a run that can resolve less than the committed file must refuse to
write, not silently shrink). frob could express this as (( generated )) with
allow_shrink = false.

M2-7 (shell-quote false positives). A repo-side resolver re-implementing shell
tokenisation is the symptom; round 1 named the cure (frob should re-execute cmd: evidence
rather than have the repo parse it). Adding to that: frob should refuse to RECORD a
cmd: evidence string it cannot itself tokenise and resolve at bind time. Every bad
entry in H2-3 was accepted by frob ticket evidence at bind time and only rejected weeks
later by a repo test -- the check is on the wrong side of the transaction.

M2-8 (env-var skip hatch). Round 1's rule ("a test bound as evidence that SKIPPED in the
measured run is reported, not counted") covers this exactly and is still unimplemented; M2-8
is its second sighting. Strengthen slightly: the skip reason must be recorded with the
evidence, so ALLOW_STRATA_SKIP=1 is visible in the ledger rather than only in a scrolled
-past pytest summary.

M2-9 (unratcheted PLANNED set). frob has ratchet machinery (SYS111, the repo's two
baseline files) but no general "declare a tolerated set that may only shrink" primitive, so
each one is hand-rolled with different semantics -- and the PLANNED set simply never got
one. Rule: a first-class (( ratchet )) declaration (path to a baseline, the command that
produces the current set, subset-only semantics, and a required ticket to grow it), so the
three baselines in this repo (TDD ordering, ledger hygiene, PLANNED runnables) share one
implementation and one contract instead of three.

Cross-cutting, round 2. Round 1's theme was "a gate is green because it examined
nothing". Round 2's is narrower and more actionable: every repair in round 1 that took the
form of a repo-side test guarding a repo-side data file has a hole where the data file is
missing an entry -- H2-1 (a branch tree with no content check), H2-4 (a lock with no
entry), M2-9 (a set with no baseline), M2-2 (a comparison with no comparable subject). The
single rule that covers all four: a check must enumerate its subject set from the SOURCE,
not from its own records, and must fail on a source subject its records do not cover.


## F-327 -- API contract audit: what frob/strata should learn (verbatim from docs/security/audit-2026-09-06-api-contract.md; tickets T-0318..T-0322)


### H-1 (no Retry-After)
design/logand-app.strata models capability edges (who may call net.connect, who may
touch PII), not response envelopes, so a missing response *header* is invisible to
SYS100. frob's gates saw nothing either because the only artifact that names the
requirement is a prose cell in docs/spec/L3-system-integration-test-plan.md:30, and no
frob:tests directive anywhere binds that cell to a test id -- the SIT row is a doc row
with no obligation edge.
Rule that would have caught it: every SIT-nnn row in L3 must resolve to an existing test
node id, and frob check --only vmodel should fail with a distinct code (e.g. VMODEL:
SIT row names a nonexistent test) rather than counting the row as closed because the
markdown cell is non-empty. That single rule catches H-1, H-2, and the four other missing
SIT files at once.

### H-2 (openapi.json has no producer and no gate)
backend/openapi.json is a *generated artifact with a cross-stack consumer*, and frob has
no concept for that: frob:doc binds code to docs, frob:tests binds code to tests, but
nothing binds backend/src/logand_backend/api/*.py to
backend/openapi.json to frontend/src/types/api.generated.ts. So the file could be
absent from main entirely while every gate stayed green.
Rule that would have caught it: a frob:generated <artifact> from <glob> via <command>
directive, with frob check running the command in --check mode and failing on a diff
(the same shape as scripts/api_inventory.py --check, which already exists and is the
proven pattern here -- it just was never applied to openapi.json). A weaker but still
sufficient rule: a REF/COV code that fires when a path referenced by a workspace member's
package.json script does not exist in the repo -- frontend/package.json:26 points at
../backend/openapi.json, which is not on main, and no gate noticed.

### M-1 / M-5 (error codes the client cannot act on)
The {detail, code} envelope is declared in SPEC-034/SYS-013 prose and mapped in
api/errors.py:_MAPPING, which has a genuine totality check
(_assert_total_coverage) -- but only in the backend direction. Nothing checks the
*consumer* side: that every code the backend can emit is either handled or deliberately
ignored by client.ts/formErrors.ts.
Rule that would have caught it: export _MAPPING's code set into the generated contract
artifact from H-2, and add a frontend unit test (bindable via frob:tests) that
enumerates it and asserts each code is present in a client-side handled/ignored
allowlist -- the mirror image of _assert_total_coverage. A new code added to
_MAPPING then fails the frontend test until someone decides what the UI does with it.
That one rule covers M-1 (no csrf_failed code exists to handle), M-5 (account_locked
vs rate_limited collapsed), and L-1 (the internal code the client structurally cannot
read).

### M-2 (docstring guarantee stronger than the code)
ensureCsrfCookie's "fails closed" is exactly the class of claim
frob check --only invariant exists for, but the claim is in a / */ docstring with no
frob:invariant directive, so it is prose, not an obligation.
Rule: a lint that flags absolute guarantee words -- "fails closed", "always", "never",
"idempotent", "guaranteed" -- appearing in a docstring on a symbol that carries no
frob:invariant, in TypeScript as well as Python. client.ts alone has several
("Always returns a positive, finite number", "only one /api/auth/csrf call ever goes
out", "Fails closed") and only the first has a test behind it
(tests/unit/api-client.test.ts:258).

### M-3 / M-4 (validation bounds duplicated across the boundary)
api/auth.py:44-49 documents itself as "the single home for every password field's length
bound in this backend" -- and the qualifier "in this backend" is doing load-bearing work
that no gate reads. The three frontend copies of MIN_PASSWORD_LENGTH = 8 are literal
duplicates of a backend constant with no link between them.
Rule that would have caught it: extend frob's duplication check across stack boundaries
for *declared constants* -- a numeric literal bound to a SCREAMING_CASE name that appears
identically in more than one workspace member is a DUP finding unless one side is marked
as generated from the other. Alternatively, and more in the grain of this repo: since the
bounds already reach the frontend through api.generated.ts, a rule that a zod schema
validating a field which exists in paths must be derived from the generated schema
rather than hand-written.

### M-6 (two redirect-to-login paths with different contracts)
design/logand-app.strata's browser node grants fetch_url via client.ts, so the
capability edge is satisfied; nothing in the model says "navigation to a protected-route
boundary is a single flow with a single return-path contract". RequireAuth.tsx and
client.ts each implement half of it, and the L5 rows (SUB-15 COMP-1503 and COMP-1506)
describe them in separate anchors that never cross-reference.
Rule that would have caught it: a strata flow node for "unauthenticated redirect" that
both COMP-1503 and COMP-1506 must declare participation in, so frob sys audit reports
two participants implementing the same flow with divergent behaviour -- or, cheaper, a
lint that window.location.assign("/login") may appear in exactly one module.

### M-7 (three verbs exempt from the typing guarantee)
T-0296 tightened apiGet/apiPost and its done-report is closed, yet apiPatch,
apiPut and apiDelete kept the old <T>(path: string) shape in the same file, under a
docstring that describes the new guarantee. frob check has no notion of "this
improvement should have applied to every sibling with the same shape."
Rule that would have caught it: on ticket close, an AFFECT-style check that flags
sibling symbols in the same module with a signature matching the *pre-change* shape of the
symbol the ticket changed. Failing that, an eslint rule (this repo already has custom
eslint rules -- tests/unit/eslint-rules.test.ts) banning a bare path: string parameter
in src/api/client.ts.


## 2026-09-06 T-0306

### F-XXX frob ticket land --dry-run refuses on a phantom "1 NEW ty error" that no
scoped ty check reproduces, and logs a self-referential doubled path
- command: frob ticket land T-0306 --dry-run --worktree /home/logan/projects/logand.app-v2/.claude/worktrees/t-0306
- observed: land refuses with "ty check found 1 NEW error(s) in this ticket's own
  touched file(s) (tests/unit/test_ops_compose.py)" on every retry (3x, across
  different commits, tree_hash changing each time). uv run ty check (whole repo
  and file-scoped) and frob check --only ty (with and without --ticket T-0306),
  run directly in the worktree, both report "no issues" / 0 diagnostics. The same
  land invocation also logs ~40 SUPPRESS001: could not read
  .claude/worktrees/t-0306/<path> for mypy diagnostic correlation warnings whose
  attempted path is doubled:
  /home/logan/projects/logand.app-v2/.claude/worktrees/t-0306/.claude/worktrees/t-0306/backend/...
  -- the worktree prefix is prepended twice, so the read always 404s.
- expected: land's "new error" ty diff should reproduce under a direct scoped
  frob check --only ty --ticket T-0306 run (the error message says as much), or
  name the line; the SUPPRESS001 path should not double the worktree segment.
- severity: blocker for a real frob ticket land from this worktree (dry-run only
  requested here, so not fixed further); the doubled-path warning is friction
  (it may be *why* the ty diagnostic-correlation step spuriously reports a new
  error -- it cannot read the compared file at all).
- ticket: none yet

## F-328 -- land's ty stage runs the PATH ty (0.0.58), not the project's venv ty (0.0.78); it refused T-0306 on a diagnostic no frob check --only ty or uv run ty shows, and named no line

T-0306 was refused three times with "ty check found 1 NEW error(s) in
this ticket's own touched file(s)" while frob's own ty gate on the
worktree said "no issues" and uv run ty check passed. Reproducing
_ty_check_files by hand (ty check <file> --python .venv, cwd
worktree, bare ty from PATH) showed the real cause: the globally
installed ty 0.0.58 reports set(raw.keys()) as set[object] for a
set[str] return; the venv's ty 0.0.78 does not. Two asks: (1) the
land stage must run the same ty binary the gate runs (or uv run ty),
and (2) the refusal must print the diagnostic (file:line, code,
message) instead of telling the agent to re-run a check that uses a
different binary and finds nothing. Also: the first two retries were
after merging main and after creating a worktree .venv, both no-ops;
F-311 was the same bug misdiagnosed. Every land on a worktree also
prints ~40 SUPPRESS001 warnings with a doubled path
(.../t-0306/.claude/worktrees/t-0306/...).

## F-329 -- frob ticket accept under load exceeds even a 600 s foreground budget and, when re-run, records the criterion twice

T-0312's first accept call was backgrounded by the harness; it completed
anyway, and the agent's retry added a duplicate criterion (#1 == #2).
accept should be idempotent on identical criterion text.

## F-330 -- WIRE001 cannot see callers through a tuple-of-callables dispatch table; LARGE001 fires on the resolver growth

T-0312's per-extension predicate table (_PREDICATES, a tuple of
(suffix, callable)) makes the four predicates look uncalled; four WIRE001
waivers with a follow-up ticket were needed. A call-graph edge from a
name referenced inside a container literal to the function would remove
this class of waiver (same family as T-0077/T-0086/T-0087).

## F-331 -- every mirrored ticket file conflicts on merge with main because frob mirrors accept/scope transitions to main mid-ticket

Three lands in a row (T-0306, T-0312, T-0318, T-0309) needed git merge
main before landing (F-328's ty stage, or simply to be current), and
every merge conflicted on exactly one file: tickets/T-xxxx/ticket.md,
because frob had mirrored the worktree's accept/scope transitions onto
main as separate commits while the worktree's copy moved on to close.
The mirror commits and the worktree's ticket file describe the same
ticket; land handles it, but a plain merge cannot. Either mirror the
whole ticket file byte-for-byte (so both sides are identical at merge
time) or give the ticket file a merge driver that takes the worktree
side.

## F-332 -- frob ticket new exceeds the 120 s harness budget under load (twice for T-0307), and is not obviously safe to retry

The agent polled tickets/ to learn whether the ticket had been filed.
new should either be fast (it is a file write plus a commit) or print the
allocated id before it starts its sweep so a retry can be avoided.

## F-333 -- a multi-line frob:waive whose continuation lines lack the # prefix silently fails to attach

T-0313's agent wrote a wrapped waive with continuation lines that were
not comment lines; frob neither attached the waiver nor reported a
malformed directive (DSL gate silent). A wrapped directive that does not
parse should be a DSL finding at the line, not a silent no-op.

## F-334 -- frob ticket close promotes T-draft-* ids only inside tickets/; citations in code comments and baseline files keep the draft id

T-0313 cited follow-up drafts from tests/e2e/ledger_hygiene_baseline.txt
and a waive reason; after promotion those still read T-draft-xxxx and
needed a manual rewrite commit. Promotion should rewrite every tracked
text file (or at least the ticket's own scope) or refuse to close with
stale draft citations.

## F-335 -- WIRE001 records no calls edge for a direct call from resolve_cmd_entry to a new helper (_tokenize_cmd); waived, follow-up T-0334

Same class as F-330 (call-graph blind spots); here the call is a plain
direct call in the same module, so the resolver miss is unexplained.

## F-336 -- a strata-only ticket cannot close: EvidenceScopeUnbound because no "touched/scope symbol" exists in a .strata file

T-0327 changed design/logand-app.strata and the ratchet lock only. close
refused with "No evidence id covers a touched/scope symbol" even though
the bound test (test_capability_via_globs_match_lock) is exactly the
proof of the change. Workaround: add the test file and the lock json to
scope. A ticket whose scope is entirely non-code (strata, json, docs)
should accept a bound test or cmd evidence without a symbol match.

## F-337 -- frob ticket new processes linger for 30-45 minutes after the ticket is filed and committed

Two frob ticket new processes (one from the T-0307 agent filing
T-0327, one from the coordinator filing T-0338) were still alive 26 and
45 minutes after their tickets existed on disk and in git, while the
frob developer's own checks (T-4130/T-4131) were running on the machine.
Other ticket verbs kept working, so no lock was held, but the harness
treated each filing as a backgrounded task. Whatever new runs after
the commit (the scope-plausibility sweep?) should be bounded, or
detached, or skippable with a flag.

## F-338 -- nested pyproject pytest config shadows the root pythonpath, so a system test that imports scripts/ fails when run alone

backend/pyproject.toml's [tool.pytest.ini_options] wins when pytest is
invoked with only backend paths, and the root's pythonpath (which makes
scripts importable) is not applied. T-0319 worked around it with a
sys.path insert in the test file. A frob-side check that the configured
(( test.runner )) invocation resolves the same rootdir for every path it
may be given would catch this class (the agent-playbook's "run from the
repo root" rule is not enough when the runner selects files).

---
id: T-4166
title: 'consumer round-4 shell audit: nine findings, including outcomes that depend
  on wall-clock time and a suite that mutates tracked files'
state: queued
kind: bug
origin: auditor
created: '2026-09-07'
priority: critical
parent: null
tier: epic
sprint: v0.544.0
runs_last: false
milestone: v0.544.0
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: true
no_scope_declared_reason: 'tier=epic: a decomposition container for nine consumer
  audit findings spanning time-dependent gate outcomes, call reachability, and test-suite
  side effects; scope belongs on the leaves where it can be disjoint enough to dispatch
  in parallel'
designated_repro_test: null
acceptance:
- text: given the findings in this epic, when it is decomposed, then each has its
    own leaf ticket or recorded evidence on an existing open ticket, with the choice
    stated per finding
  evidence: []
- text: given a check whose outcome depends on wall-clock time, when its bound test
    runs, then the test exercises the predicate at more than one instant
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
A CONSUMER'S FOURTH-ROUND SHELL AUDIT, verbatim: nine findings, each with why the
existing gates missed it and the rule that would have caught it. Same instrument
as the round-3 backend audit filed as T-4109 (nine leaves) and the round-4 engine
audit filed as T-4157.

DECOMPOSE ONE LEAF PER FINDING, with real scope per leaf and an explicit note
saying whether the rule can be fixture-tested in frob's own tree. Read every
finding's own text; the summary below is orientation, not a substitute.

TWO THAT DESERVE ATTENTION AHEAD OF THE REST, because they name gaps in how frob
decides things rather than gaps in what it checks:

  H4-1, TIME-DEPENDENT OUTCOMES ARE STRUCTURALLY INVISIBLE. Their check passes
  today and fails tomorrow, and every test that exercises it supplies the current
  time and the build time FROM THE SAME INSTANT -- so the entire class of
  wall-clock-dependent failure cannot be observed by any test they have. That is
  a silent-zero with a clock attached: the measurement is taken in the one
  condition where the bug cannot appear. Their proposed rule is an invariant kind
  for time-dependent predicates, discharged by re-running the bound test with the
  clock advanced across a declared horizon. Note we have the same blind spot: ask
  what in THIS repo is a function of wall-clock time and is only ever tested at a
  single instant.

  M4-7, THE TEST SUITE MUTATES TRACKED FILES and no gate asserts otherwise. That
  is worth checking against ourselves immediately and cheaply -- a suite that
  writes to tracked files makes every "clean tree" measurement conditional on
  whether the suite ran, and this session has already been bitten twice by tree
  state contaminating a measurement.

THREE ARE ONE MECHANISM SEEN TWICE, WHICH THEY SPOTTED THEMSELVES: M4-2 and M4-3
are both a parameter or field that nothing consumes, and they note the identical
mechanism one file over. That is the same call-reachability question already open
as T-4151, where our wiring gate answers a reachability question with a text scan
and misses real callers. Check T-4151 before filing these two separately -- they
may be evidence for it rather than new work.

DOGFOODING NOTE, unchanged from the sibling epics: this is a web shell with
routes, CSRF bootstrapping, rate-limit copy and a return-path stash. frob has none
of that. Our own green is evidence of nothing for most of these leaves, and a
fixture built from our tree will not exercise the rule. Say so per leaf rather
than discovering it during implementation.

CHECK THE OPEN QUEUE BEFORE FILING EACH LEAF. Several of these name mechanisms
already tracked; attaching evidence to an open ticket is worth more than a
duplicate, and this queue has already absorbed five separate tickets against one
mechanism this session before they were consolidated.

VERBATIM REPORT FOLLOWS.

## F-362 -- shell round-4 audit: what frob/strata should learn (verbatim from docs/security/audit-2026-09-07-shell-round4.md; tickets T-0370..T-0373)


Per HIGH/MEDIUM finding, why the existing gates did not catch it, and the
rule that would have.

H4-1 (security.txt 24h staleness). frob check has no notion of a gate
whose outcome is a function of wall-clock time. Every test that exercises
securityTxtMatches supplies now and buildTime from the same instant, so
the whole class of "passes today, fails tomorrow" is invisible.
*Rule:* a frob:invariant kind for time-dependent predicates -- a directive
such as frob:invariant time-stable fn="securityTxtMatches" horizon="180d"
that gate:INV discharges by re-running the bound test with the clock advanced
across the declared horizon. Failing that, a narrower lint: a comparison
between a value derived from a *committed artifact* and a value derived from
new Date() must be accompanied by a test that varies now.

H4-2 (github-metadata drift on live GitHub state).
design/logand-app.strata grants the build node network reach for this
generator but does not classify what it reaches. Nothing in the model says
"this data is owned by a third party and is volatile", so no gate can object
to it being compared for byte equality against a committed file.
*Rule:* a strata capability attribute on outbound fetches -- may "fetch_url"
... volatility=external -- plus a SYS rule that a volatility=external
source may not be the basis of a build-failing equality check. A cheaper
frob-side rule: gate:BUILD flags any package.json script chain containing
an X:check step with no corresponding X write step in the same chain
(build-chain.test.ts already encodes the write-before-check pairing for
three generators and simply omits github-metadata from the list -- the gate
should derive the pairs from the script names, not from a hand-maintained
array).

M4-1 (Shell renders a raw .message). The L-6 rule is real and was
applied to six auth pages; it lives only as prose in formErrors.ts's module
comment, so the one consumer outside pages/auth/ never picked it up.
*Rule:* a frob:invariant on formErrors.ts of the form "no JSX in
frontend/src/ renders .message off a value that is not ErrorDisplay",
enforceable as an eslint rule in the existing custom-rule harness
(tests/unit/eslint-rules.test.ts already exists) -- ban error.message in
JSX expression position outside formErrors.ts. This is the same shape as
the existing rule banning the hand-written Me intersection.

M4-2 (rateLimitedCopy(code) never passed). gate:TEST saw the parameter
covered because the unit test calls the function directly; nothing checks
that a documented parameter is ever supplied by production code.
*Rule:* a DEAD-PARAM finding in gate:REF -- an exported function's optional
parameter that no non-test call site ever passes, where the symbol's own
docstring describes behaviour conditioned on it, is unproven. The docstring
at formErrors.ts:58-65 makes a behavioural claim ("a shared-NAT visitor
should not read...") that no production path can satisfy; gate:INV's
"docstring claims a behaviour" check should treat a claim gated on an
never-supplied argument as unverified.

M4-3 (fieldErrors consumed by nobody). Identical mechanism to M4-2 one
level up: a whole exported field, populated and typed through three modules,
with zero readers. gate:REF's reference counting evidently attributes the
ErrorDisplay type's usage to the pages, masking that the *field* is unread.
*Rule:* per-field reachability for exported interface members, not just
per-symbol -- a member written but never read outside its own module is a
REF finding. This would also have caught the T-0320 done-report claiming 422
field errors were delivered.

M4-4 (licences host coupling). The project's own test file documents the
coupling in 20 lines of comment and responds by skipping itself; nothing
propagates that knowledge to the build script the same coupling breaks.
*Rule:* frob should treat a describe.skipIf/it.skip whose reason names a
*production* command as an obligation, not a resolution --
gate:TEST finding "skipped test names npm run build as the affected
surface; no ticket accounts for it". More generally: a skipIf guard needs a
frob:todo T-#### next to it, the same way a bare # TODO is a TODO001.

M4-5 (no CSRF re-bootstrap). csrf_failed sits in
IGNORED_ERROR_CODES, whose docstring (formErrors.ts:99-112) explicitly
defines that list as "codes that need no branch because ApiError.message
is safe to render". That is a display-layer statement being used to
discharge a *recovery* question. The totality test only checks that every
backend code appears in one of the two lists.
*Rule:* split the list by concern. IGNORED_ERROR_CODES should be
DISPLAY_ONLY_ERROR_CODES, and a second axis -- "does this code require a
client-side recovery action?" -- should be declared per code, with the
totality test asserting both axes are answered. csrf_failed,
session_expired and token_expired are all codes where "render it and
stop" is a design decision that deserves an explicit, reviewed entry rather
than falling into a bucket named "ignored".

M4-6 (return-path stash lifecycle). The stash has three lifecycle events
-- write, consume, invalidate-on-logout -- and only two are implemented. The
docstrings assert the third ("cleared on read so a stale destination never
resurfaces") without qualification. strata models /login as a route but
models no client-side session-scoped state at all, so there is nothing for a
SYS rule to attach to.
*Rule:* declare browser-persisted state in design/logand-app.strata the way
capabilities are declared -- browser stores "logand:return-path" scope=session
cleared_on="logout,consume" -- and have gate:SYS require a code path for
each declared cleared_on trigger. The same rule would cover
logand.client-log (which *does* clear on logout, via clearLogs) and would
have made the asymmetry between the two obvious.

M4-7 (test suite mutates tracked files). No gate asserts that running
the test suite is side-effect-free on the working tree.
*Rule:* a frob test post-condition -- after the bound test run, git status
--porcelain must be unchanged from before; any modified tracked file is a
finding naming the test file that spawned the writer. This is cheap, exact,
and would also have caught the licences document being rewritten.

---

## Notes

Checked and found correct (do not re-verify):

- isSafeReturnPath / matchesKnownRoutePrefix
  (redirectToLogin.ts:33-49) against open-redirect input. Traced
  //evil.example/x (rejected by the explicit !startsWith("//")),
  /\evil.example (the "/" prefix in PUBLIC_ROUTE_PATHS only matches
  path === "/" or startsWith("//"), so it is rejected),
  javascript: and absolute https:// URLs (no leading single slash),
  and nested /portal/invoices (correctly accepted). The allowlist itself
  is sound; the finding against this area (M4-6) is about lifecycle, not
  validation.
- isSameOriginPath (client.ts:171-177) -- protocol-relative and
  cross-origin paths correctly receive neither the CSRF header nor
  credentials.
- parseRetryAfterSeconds (client.ts:182-192) -- delta-seconds,
  HTTP-date, missing header and unparseable values all floor at 1; no
  NaN path.
- parseErrorBody (client.ts:209-254) -- all three body shapes
  (nested envelope, 422 array, legacy flat) parse as documented, and the
  res.clone() means the body is not consumed for the caller.
- ensureCsrfCookie's in-flight memoization and unconditional finally
  reset (client.ts:136-164) -- a non-2xx bootstrap correctly rejects
  rather than resolving, and concurrent first mutations share exactly one
  GET. (The gap is a *stale* cookie, M4-5, not this mechanism.)
- The 401 exemptions for /api/me and /api/auth/* (client.ts:287-296)
  match useMe.ts:2-4's stated contract.
- engineModules.ts's glob keys vs the real engine file names. Confirmed
  against the demo checkout: frontend/src/engine/footerHeight.ts and
  frontend/src/engine/MotionToggle.tsx both exist and match
  FOOTER_HEIGHT_MODULE/MOTION_TOGGLE_MODULE exactly. No T-0356-class
  drift. The import.meta.glob form correctly resolves to {} on this
  branch with no build error, and emits no runtime
  import("/src/engine/...") -- the T-0363/H4-1 fix holds.
- FooterHeightPublisher/MotionControl mount sites: both are mounted
  only from Landing.tsx (:420, :423, :443), never from Shell.tsx
  or any non-landing route, so there is no non-landing-route mount to
  report. The rules-of-hooks split into FooterHeightPublisherActive is
  correct. The engine's own useFooterHeightPublisher does
  removeProperty on unmount (demo checkout
  frontend/src/engine/footerHeight.ts:173-177), so a Landing -> other
  route -> Landing round trip does not leave a stale value that would
  permanently disable the guard.
- resolveCliOutDir (cli.ts:26-48) -- confinement to frontend/ or the
  OS temp dir, including the + path.sep prefix check that prevents
  /tmpfoo matching /tmp.
- canonicalGitRelPath (cli.ts:76-85) -- the T-0358 rebase onto the
  canonical public dir is correct; a LOGAND_CLI_OUT_DIR-redirected
  --check really does compare against frontend/public/<relPath> at HEAD.
- The NODE_OPTIONS preload in cli-runner.test.ts:203-248. It is
  inherited by every node child the build spawns (that is the intent), but
  it only intercepts URLs containing api.github.com and delegates
  everything else to the original fetch, so it does not corrupt the real
  build; it is written under tmpdir() and removed in afterAll; and it
  is confined to the env object handed to that one execFileAsync call,
  never exported into the ambient environment. The separate problem with
  that block is M4-7 (it writes to the real tree), not the preload.
- GITHUB_METADATA_ALLOW_OFFLINE is set in exactly one place --
  cli-runner.test.ts:244, scoped to that test's spawned build. It is not
  set in any committed CI config, ops/ file, or shell profile in this
  checkout (git grep over the whole tree). The "offline flag permanently
  on in CI, drift gate off" hypothesis does not hold today; H4-2 is a
  problem with the gate's own comparison, not with the flag.
- checkGithubMetadata's per-repo ok/ok comparison and the T-0316
  allDegraded exit-2 path are logically correct as written -- the
  vacuous-pass hole M2-2 named is genuinely closed. The remaining issue
  (H4-2) is the field set being compared.
- writeGithubMetadata's preserve-on-degrade and stale-entry-drop
  (github-metadata.ts:349-398) behave as documented.
- build-chain.test.ts -- the write-before-vite build and
  check-after-vite build assertions are real (they parse the actual
  script string) and not vacuous. The gap is coverage, not soundness:
  github-metadata has no write/check pair to assert.
- parseSpdxExpression / looksLikeSpdxExpression / distInfoStem
  (licenses.ts:152-175, :344-361) -- the legacy-PyPI free-text guard
  and the WITH <exception> skip are correct.
- PUBLIC_ALLOWLIST / findStrayPublicFiles (static-assets.ts:274-298)
  -- the M-7 mockServiceWorker backstop works in the real (non-redirected)
  build. Verified git ls-files frontend/public top-level entries are all
  on the list.
- logging.ts redaction and lifecycle -- clearLogs() is wired to logout
  (Shell.tsx:32), the ring buffer is bounded by count and age, and the
  L-4 correction about not mirroring the backend's redaction list is
  honestly stated rather than overclaimed.
- RequireAuth / AdminGuard -- the UnauthenticatedError-vs-other-error
  split is correct in both, and neither bounces an authenticated session to
  /login on a 500. Portal's role dispatch matches DEC-004.
- Test run: api-client.test.ts, tests/unit/auth/,
  tests/unit/guards/ -- 110 tests, all green. The two
  Not implemented: navigation jsdom warnings come from
  Login.tsx:99's window.location.assign and are expected noise, but see
  "skipped" below.

Deliberately skipped or only skimmed:

- The engine glue itself (frontend/src/engine/ on the demo checkout)
  beyond footerHeight.ts and the two glob-matched filenames -- covered by
  docs/security/audit-2026-09-07-engine-round4.md. I read
  footerHeight.ts only to confirm the unmount-cleanup contract
  FooterHeightPublisher depends on.
- prerender.ts and media-manifest.ts were skimmed for CLI-entry and
  --check shape only (both follow the isCliRunEntry +
  resolveCliOutDir convention correctly). Their output correctness
  against SPEC-012 was covered in round 3 and I did not re-derive it.
- Public content modules (content/projects.ts, content/site.ts,
  content/policies/) and the presentational public-page components
  (ImageCarousel, TerminalWindow, LetterboxFrame, VideoPoster,
  Throbber, Icons, GlitchText, Reveal, useBrightnessWave) --
  no auth, money, or data-integrity surface; round 3 covered them.
- Styling/token machinery (styles/tokens.css, tailwind.css,
  a11y.ts) and the apollo design-check integration -- out of this audit's
  stated focus.
- mocks/handlers.ts / mocks/browser.ts -- dev-only, gated behind
  --mode mock, and the M-7 publicDir override that kept the service
  worker out of dist/ is verified by PUBLIC_ALLOWLIST above.
- I did not run npm run build, frob check, or any full suite, per
  the task's constraints. H4-1, H4-2 and M4-4 are therefore reasoned from
  the code plus (for H4-1) a direct function-level probe, not from an
  observed failing build. H4-1's probe is exact; H4-2 and M4-4 follow
  deterministically from the code paths cited and from
  cli-runner.test.ts's own documentation of the same couplings.
- Browser automation was not used and the Vite dev server on :5173 was
  left untouched.
- login.test.tsx asserts login success but cannot assert the redirect
  *destination*, because jsdom throws Not implemented: navigation on
  window.location.assign and the rejection is swallowed. That means the
  M4-6 stash-lifecycle behaviour has no end-to-end test today; a fixer
  should mock window.location (or extract the navigation into an
  injectable seam) rather than assume the existing green suite covers it.

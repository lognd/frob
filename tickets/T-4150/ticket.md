---
id: T-4150
title: 'frob exports a public Python API no consumer can import: installed as an isolated
  tool, with no published release carrying the current API'
state: in-progress
kind: bug
origin: agent
created: '2026-09-07'
priority: critical
parent: null
tier: ticket
sprint: alpha-gate
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/__init__.py
- tests/system/test_public_api_from_wheel.py
- src/frob/tickets/__init__.py
- docs/guides/python-api.md
- docs/index.md
- design/frob.strata
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/__init__.py
  reason: 'makes the ticket startable: the advertised surface lives in the package
    init, and the must-fire fixture needs a home that does not yet exist; CLI wiring
    for the path-reporting verb and any workflow change are expected to be added with
    their own recorded reason once the implementer has measured what the verb actually
    needs'
  actor: logan
  at: '2026-09-08'
- op: add
  glob: tests/system/test_public_api_from_wheel.py
  reason: 'makes the ticket startable: the advertised surface lives in the package
    init, and the must-fire fixture needs a home that does not yet exist; CLI wiring
    for the path-reporting verb and any workflow change are expected to be added with
    their own recorded reason once the implementer has measured what the verb actually
    needs'
  actor: logan
  at: '2026-09-08'
- op: add
  glob: src/frob/tickets/__init__.py
  reason: 'wheel-import probe found a genuine pre-existing bug on-topic for this ticket''s
    own subject: frob.tickets.__all__ advertises ClipboardError but __init__.py never
    imports it, so AttributeError fires on access -- exactly the class of defect T-4150
    exists to catch (an advertised name that does not actually import), so fixing
    it belongs in this ticket rather than a separate one'
  actor: logan
  at: '2026-09-08'
- op: add
  glob: docs/guides/python-api.md
  reason: acceptance criterion requires the advertised public API surface to be written
    down somewhere a consumer can find it; adding a dedicated guide and one index
    link
  actor: logan
  at: '2026-09-08'
- op: add
  glob: docs/index.md
  reason: acceptance criterion requires the advertised public API surface to be written
    down somewhere a consumer can find it; adding a dedicated guide and one index
    link
  actor: logan
  at: '2026-09-08'
- op: add
  glob: design/frob.strata
  reason: new system test's fs.read/fs.write/exec capabilities (building wheels, installing
    into a venv, running the probe script) need declaring against the testsuite node
    per SELFAUDIT001
  actor: logan
  at: '2026-09-08'
body_changes:
- mode: append
  reason: scoped for dispatch; records why the verb wiring and the workflow are deliberately
    left out of the initial scope, and names the exports-policy closure hint the scope
    change reported
  actor: logan
  at: '2026-09-08'
  old_length: 4715
  new_length: 6483
designated_repro_test: null
acceptance:
- text: given a wheel built from this repository installed alone in an environment,
    when the advertised public names are imported, then the import succeeds
  evidence: []
- text: given a private module path, when a consumer attempts to import it as public
    API, then the advertised-surface fixture does not cover it
  evidence: []
- text: given two different frob installs, when the path-reporting verb runs under
    each, then each reports the environment of the frob actually executing
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
FROB EXPORTS A PUBLIC PYTHON API THAT NO CONSUMER CAN IMPORT. Reported as
logand.app-v2 F-351, and it arrived one message after I advised that consumer to
replace their hand-written scope matcher with `from frob.tickets import
scope_matches`. They tried. It does not work, and they had to shim their path by
locating frob's uv-tool venv through `shutil.which`.

THE MECHANISM: frob is installed as a uv TOOL, which by design lives in its own
isolated environment that a consumer project's interpreter cannot see. The normal
remedy -- declare frob as a dev dependency and let the resolver put it on the
path -- is unavailable, because there is no published release carrying the
current API.

ONE CORRECTION TO THE REPORT, verified against the index: the consumer describes
the PyPI entry as "an unrelated 0.0.x frob". IT IS NOT UNRELATED, IT IS OURS. The
published metadata carries this project's own author address and its project URLs
point at this repository. What it is, is ANCIENT -- version 0.0.6, uploaded
2026-06-28, licensed MIT, requiring Python 3.10. This tree is 0.530.0, GPL-2.0-
only, requiring 3.11. The distinction matters: this is not a name squatted by a
stranger, it is our own abandoned release, which means publishing is available to
us and is the straightforward fix.

WHY THIS IS A RELEASE-BLOCKING GAP RATHER THAN AN INCONVENIENCE:

  1. WE ADVERTISE THE API AND CANNOT DELIVER IT. `scope_matches` is deliberately
     exported and its docstring calls it "THE one implementation every
     scope-consulting site must call". T-4124 records that consumers writing
     their own matcher is a defect. But the recommended fix is unreachable, so
     the advice is unfollowable and every consumer will keep writing a second
     matcher that desyncs from ours. A published function nobody can import is
     not published.
  2. THE WORKAROUND IS WORSE THAN THE PROBLEM. Locating another tool's virtual
     environment through the resolved path of its console script and splicing it
     onto the interpreter path is exactly the kind of fragile coupling frob
     exists to prevent. It breaks on any install-layout change, it is invisible
     to dependency tooling, and the consumer had to add a loud warning to it
     because they know it is unsound.
  3. IT COMPOUNDS THE VERSION-SKEW SURFACE. With no pinnable release, every
     consumer runs whatever local path they installed from. There is then no
     answer to "which frob produced this finding", which has already cost this
     queue wrong conclusions about consumer reports.

TWO FIXES, AND THEY ARE NOT ALTERNATIVES -- DO BOTH:

  A. PUBLISH. This is the real fix and it is the owner's decision, not an
     implementer's -- do NOT publish from this ticket. What this ticket SHOULD
     do is make publishing correct when it happens: confirm the API surface a
     consumer needs is actually importable from the built wheel (not merely
     present in the tree), and add a test that imports the advertised public
     names FROM A BUILT ARTIFACT rather than from the source tree. The py.typed
     defect this repo just fixed is the cautionary precedent -- a packaging claim
     that was true in config and false in the wheel, invisible for months.
  B. ADD A PATH-REPORTING VERB. Their second suggestion stands on its own merit
     even after publishing, because a tool install remains a legitimate way to
     run frob. A verb that prints the interpreter or site-packages path of the
     running frob turns their fragile shim into a supported one-liner, and it
     costs almost nothing. Note it must report the path of the frob that is
     ACTUALLY RUNNING, since this repo already warns that the invoked binary's
     source identity may not match a given checkout.

MUST-FIRE FIXTURE:   the advertised public names import successfully from a wheel
                     built by this repository, in an environment that has only
                     that wheel installed.
MUST-STAY-QUIET:     private module paths are NOT importable as public API -- the
                     fixture must pin the advertised surface, not everything that
                     happens to be reachable.
THIRD FIXTURE:       the path-reporting verb names the environment of the frob
                     actually executing, verified by running it from two
                     different installs.

ACCEPTANCE
- A test imports the advertised public API from a BUILT ARTIFACT, not the tree.
- The advertised surface is written down somewhere a consumer can find it.
- A path-reporting verb exists and reports the running frob's environment.
- No publish performed from this ticket; the owner decides that separately.
- All three fixtures committed.



COORDINATOR NOTE ADDED WHILE SCOPING THIS FOR DISPATCH.

This ticket was unstartable because it had no scope; it now names the package
init and a test file that does not yet exist, which is the home the must-fire
fixture needs. That scope is deliberately minimal rather than complete.

The wiring for the path-reporting verb is NOT in scope yet, because the number of
places a new verb must be registered is not obvious from outside: this repository
has already had a defect where a verb was added and missed several of the lists
that enumerate verbs, so guessing the file set here would either over-claim leases
or under-claim them. Measure what the verb actually needs, then widen with a
recorded reason.

The integration workflow is also NOT in scope, and is contended by other in-flight
tickets. Note that a job already exists there which builds a bare wheel, installs
it into a clean environment, and asserts the tool starts without native
extensions. That job is the natural home for the from-a-wheel import check, and
extending it is likely cheaper and more honest than building a wheel inside the
test suite. Coordinate rather than racing for that file.

A CLOSURE HINT THE SCOPE CHANGE ITSELF REPORTED: the package init is already
covered by an exports-policy test elsewhere in the tree, which is not in scope.
Decide deliberately whether that test needs to move or widen, rather than
discovering it at land time.

ONE THING TO CHECK BEFORE BUILDING ANYTHING: the owner has decided the imminent
publish is a plain final release. Publishing is what actually closes this
ticket's first cause, and it is not yours to do. What IS yours is making sure
that when it happens, the advertised names import from the artifact rather than
merely existing in the tree.

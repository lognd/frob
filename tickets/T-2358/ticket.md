---
id: T-2358
title: Three live import cycles in src/frob (deploy, vet, serve/stats), invisible
  to accounting because the cycle gate emits identity-less findings
state: queued
kind: bug
origin: agent
created: '2026-08-17'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
acceptance:
- text: given src/frob, when frob cycle runs, then it reports zero import cycles
  evidence: []
- text: given a deliberately planted 2-node cycle, when the detector runs, then it
    is still reported (fix did not blind the detector)
  evidence: []
- text: given the touched packages, when their test suites run, then they pass
  evidence: []
threat: null
component: gates
anchor: false
anchor_reason: null
land_commit: null
---
MEASURED 2026-08-17. `uv run frob cycle src/frob` reports three genuine
import cycles in this package:

  1. src/frob/deploy/_generate_windows.py <-> src/frob/deploy/_generate.py
  2. src/frob/vet/_capability_scan.py    <-> src/frob/vet/_capability.py
  3. src/frob/serve/_socketd.py -> src/frob/serve/_events.py
       -> src/frob/stats/__init__.py -> src/frob/serve/_to... (multi-node)

The third is reported by `frob check --only cycle` as a hard ERROR.

WHY THESE WENT UNNOTICED, WHICH IS THE INTERESTING PART: the cycle gate emits
its finding as

    frob-cycle:None None:None | import cycle: ...

-- `code=None`, `file=None`, the whole description in free text. So the
finding has NO IDENTITY. It cannot be attributed to a commit, owned by a
ticket, waived, counted in a floor comparison, or filed by the sweep. It has
presumably been sitting in the error floor unowned for a long time, visible
only to someone reading raw gate output rather than the accounting layer.

That identity-less shape is also the exact record that pinned the verify
quarantine and deadlocked the fleet for two hours today: `_verify.py::
_parse_error_findings_from_json` turned `(code or "", file or "")` into a
real `("", "")` identity. T-2313 patched the downstream choke point and
T-2345 fixed the parse boundary -- and T-2345's investigation is how this
producer was finally identified. The identity bug was MASKING a real
architectural defect.

REQUIRED: break all three cycles. These are structural, not cosmetic --
a cycle means two modules cannot be reasoned about, tested, or imported
independently, and it is the kind of thing that turns into an import-order
heisenbug later.
 - The two 2-node cycles are likely a shared helper wanting its own module,
   or a type-only import that belongs under `TYPE_CHECKING`.
 - The serve/stats cycle spans package boundaries and needs a real look at
   which direction the dependency SHOULD run; do not break it by moving an
   import inside a function just to silence the detector. That hides the
   cycle from the tool while leaving the coupling in place.

POSITIVE CONTROLS: (1) `frob cycle src/frob` reports zero cycles afterward;
(2) must-still-pass -- a deliberately planted 2-node cycle IS still detected,
so the fix did not simply blind the detector (this repo has already been
burned once by a "clean" cycle verdict that came from a detector that could
not see the planted case); (3) the full test suite for the touched packages
passes, since breaking a cycle usually means moving symbols.

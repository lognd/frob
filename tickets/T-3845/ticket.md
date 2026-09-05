---
id: T-3845
title: ship frob-core and strata-core with frob by default now that the release workflow
  publishes both
state: in-progress
kind: feature
origin: human
created: '2026-09-05'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- pyproject.toml
- docs/guides/install.md
- tests/system/test_cli_native_missing.py
- tests/fixtures/fake_no_native/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: pyproject.toml
  reason: ship cores as default deps, update install docs, verify degrade path fixture
  actor: logan
  at: '2026-09-05'
- op: add
  glob: docs/guides/install.md
  reason: ship cores as default deps, update install docs, verify degrade path fixture
  actor: logan
  at: '2026-09-05'
- op: add
  glob: tests/system/test_cli_native_missing.py
  reason: ship cores as default deps, update install docs, verify degrade path fixture
  actor: logan
  at: '2026-09-05'
- op: add
  glob: tests/fixtures/fake_no_native/**
  reason: ship cores as default deps, update install docs, verify degrade path fixture
  actor: logan
  at: '2026-09-05'
- op: add
  glob: uv.lock
  reason: uv sync regenerates the lock now that cores are default deps
  actor: logan
  at: '2026-09-05'
- op: remove
  glob: uv.lock
  reason: uv.lock is land-owned (T-0731), never hand-committed
  actor: logan
  at: '2026-09-05'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
OWNER DIRECTIVE 2026-09-05: "The README says that frob doesn't come with the
core packages. I need frob to come with the core packages."

Today `frob-core` and `strata-core` are an OPTIONAL extra:

    pyproject.toml:68   native = ["frob-core==0.530.0", "strata-core==0.530.0"]
    pyproject.toml:145  # T-3011: `frob-core`/`strata-core` are not published
                        #          to PyPI yet
    pyproject.toml:154  frob-core = { path = "frob-core" }
    pyproject.toml:155  strata-core = { path = "strata-core" }

So `uv tool install frob` gets NO natives, and the user is sent to build them
from source. That was correct while the cores were unpublished. It stops being
correct at the alpha cut.

WHAT CHANGED, MEASURED 2026-09-05: `.github/workflows/release.yml` already
builds and publishes BOTH cores. maturin across five targets (manylinux
x86_64/aarch64, macOS x86_64/arm64, Windows x86_64), abi3-py311; each wheel is
installed into a clean venv on the runner that built it and imported before
upload; the publish job collects them with `pattern: frob-core-*` /
`strata-core-*` and `merge-multiple: true`, then publishes each package. The
premise of the T-3011 comment is therefore about to be false.

THE ORDERING PROBLEM, AND IT IS THE REAL WORK. If frob's `dependencies` name
`frob-core==<v>` and `strata-core==<v>`, those versions must EXIST on PyPI when
frob's own wheel is resolved. Within one release run the publish job does the
cores before frob, so a single run is self-consistent -- but only if each step
truly completes, and a partial publish (cores up, frob fails) leaves an
installable-but-coreless state while a reversed partial (frob up, cores failed)
leaves frob UNINSTALLABLE for everyone. Decide and state how this is handled:
  (a) Hard-pin `==` and rely on publish order. Simplest; a failed core publish
      must then abort before frob is pushed. Verify the workflow actually does
      abort rather than continuing.
  (b) Floor-pin `>=` so a lagging core does not brick frob's install.
  (c) Keep the extra AND add the cores to the default dependency set, so
      `frob[native]` stays valid for anyone pinning it.
Say which and why. Check what the workflow does on a failed publish step BEFORE
choosing -- do not assume it aborts.

THE DEGRADE PATH MUST SURVIVE. T-0133 established that both natives degrade
honestly: a clear `Err`, never a crash, when the extension is absent. Making
them default dependencies must NOT delete that path. A source install on a
platform with no wheel, or a constrained environment that strips them, still
has to work. Keep the degrade branch and keep its tests; this change alters the
DEFAULT, not the requirement.

ALSO REMOVE THE LOCAL-DEV PATH SOURCES FROM THE PUBLISHED METADATA if they leak
into the wheel. `[tool.uv.sources]` path entries are a local-dev convenience;
confirm whether they reach the built artifact and, if so, that a consumer
resolving frob from the index is unaffected.

MUST-FIRE FIXTURE:   a clean-venv install of the built frob wheel imports
                     frob_core and strata_core without a separate install step.
MUST-STAY-QUIET:     frob still starts and `frob check` still runs with the
                     natives forcibly absent, degrading per T-0133 rather than
                     crashing.

ACCEPTANCE
- The (a)/(b)/(c) pin choice stated with reasoning, after checking the
  workflow's real failure behaviour.
- `frob doctor`'s native-extension reporting still accurate afterwards.
- Both fixtures committed.
- docs/guides/install.md updated in the same change; it currently explains why
  the natives are NOT a plain extra, which becomes wrong.

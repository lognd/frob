---
id: T-3011
title: 'Epic: publish frob-core and strata-core wheels to PyPI -- build now, publish
  only on explicit owner consent'
state: queued
kind: feature
origin: human
created: '2026-08-26'
priority: high
parent: null
tier: ticket
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
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
frob's two Rust/PyO3 extensions are not on PyPI. Adopting frob in another repo
therefore means building Rust from source, which is a poor first run for exactly
the adopter the owner does not want to lose. This is on the critical path for
the standing transferability goal: wheels are what make `uv tool install frob`
work for someone who is not the author.

PUBLISHING REQUIRES EXPLICIT OWNER CONSENT. This is not advisory and it is not
satisfied by "the ticket said it was ready". Build the machinery; do NOT publish
any artifact to PyPI (or TestPyPI) without the owner saying so for that specific
release. Make that STRUCTURAL, not a note in a runbook:
  - no publish on tag-push, no publish on merge, no publish on any automatic
    trigger;
  - the publish job runs only via an explicit manual dispatch, and sits behind a
    protected environment with a required reviewer so approval is recorded;
  - building and uploading are SEPARATE jobs -- wheels may be built and retained
    as artifacts freely; only the upload step is consent-gated.
An agent that publishes without that approval has done something unrecoverable:
a version cannot be re-used on PyPI once taken.

--------------------------------------------------------------------
MEASURED STARTING POINT (2026-08-26) -- most of the hard part is done
--------------------------------------------------------------------
- `abi3-py311` is ALREADY configured on both crates (`pyo3 = { version = "0.22",
  features = ["abi3-py311"] }`). This collapses the Python-version axis: ONE
  wheel per platform, not one per (platform x Python version).
- maturin is ALREADY the build backend for both crates (`maturin>=1.7,<2`,
  `build-backend = "maturin"`, `module-name = "frob_core"`).
- The top-level `frob` package builds with setuptools and is pure Python.
- CI's `standalone-install` job ALREADY proves frob installs and runs WITHOUT
  the natives: it builds the bare wheel via `uv build --wheel`, installs into a
  clean venv, and passes in ~15s.

So the natives are an ACCELERATOR, not a hard dependency, and the remaining work
is packaging and release plumbing rather than a build-system change.

TARGET MATRIX (abi3 keeps this small -- roughly 5 targets x 2 crates + sdists):
  manylinux x86_64, manylinux aarch64, macos x86_64, macos arm64, windows x86_64

--------------------------------------------------------------------
DECISIONS TO MAKE DELIBERATELY
--------------------------------------------------------------------
1. VERSION COUPLING. Three separately published artifacts (`frob`, `frob-core`,
   `strata-core`) is three chances to skew. This repo already has the problem in
   miniature: T-2884 had to add a git-SHA check to the daemon BECAUSE VERSION
   STRINGS WERE NOT SUFFICIENT to detect skew. Recommendation: `frob` pins the
   cores with exact `==` versions and all three are cut together. Loose pins on
   an ABI-coupled native extension produce bug reports nobody can reproduce.
   Whatever is chosen, the coupling must be enforced by a gate, not a convention.

2. WHAT HAPPENS WHEN NO WHEEL MATCHES. An sdist fallback makes pip build from
   source, requiring a Rust toolchain -- a miserable first run. Since
   `standalone-install` already proves the natives-free path works, the better
   behaviour is to DEGRADE LOUDLY to pure Python ("native acceleration
   unavailable on this platform/interpreter; install X to enable") rather than
   silently attempting a Rust build. That is the PLATFORM001 doctrine applied to
   distribution: declare the boundary, never degrade silently.

3. TRUSTED PUBLISHING. Prefer PyPI trusted publishing (OIDC) over a long-lived
   API token in repository secrets. If a token is used instead, say why.

--------------------------------------------------------------------
SEQUENCING -- do not publish from a red matrix
--------------------------------------------------------------------
As of 2026-08-26 there is NO verified green CI run on any platform:
  - Windows reaches the Test stage and fails ~19 tests across 7 files (T-3003);
  - macOS has ~144 uncharacterised failures (T-2930, T-2971);
  - Linux has never produced a verified green full-suite baseline (T-2992).

Publishing today would ship artifacts we have no evidence work. Build the release
workflow NOW so it is ready, and gate the FIRST PUBLISH on a green matrix plus
explicit owner consent. Those are two separate gates and both are required.

--------------------------------------------------------------------
ACCEPTANCE
--------------------------------------------------------------------
- A release workflow builds wheels for the full target matrix plus an sdist per
  crate, retained as CI artifacts, on a manual dispatch.
- The upload step is a SEPARATE, consent-gated job behind a protected
  environment with a required reviewer. No automatic trigger publishes anything.
  Prove it: demonstrate that a normal push/tag/merge produces artifacts and does
  NOT upload.
- A built wheel installs into a clean venv on each target platform and the
  natives import successfully. Verified on real runners, not asserted.
- With no matching wheel available, frob still installs and runs, and reports
  the missing native acceleration LOUDLY and by name. Must-fire fixture.
- The version-coupling policy is implemented and enforced by a gate, with the
  reasoning recorded.
- Nothing is published to PyPI or TestPyPI under this ticket without a recorded
  owner approval for that specific release.

---
id: T-4131
title: 'release presentation: frob ships with no contributing guide, security policy,
  code of conduct, issue or PR templates, and no README badges'
state: in-progress
kind: docs
origin: human
created: '2026-09-06'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- CONTRIBUTING.md
- SECURITY.md
- CODE_OF_CONDUCT.md
- README.md
- .github/**
- docs/guides/command-reference.md
- docs/index.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: docs/guides/command-reference.md
  reason: verb-groups and full command table moved out of README to keep it scannable
    per T-4131's own acceptance
  actor: logan
  at: '2026-09-07'
- op: add
  glob: docs/index.md
  reason: add a docs/index.md link entry for the moved command-reference page (DOC001
    fix)
  actor: logan
  at: '2026-09-07'
designated_repro_test: null
acceptance:
- text: given a first-time visitor, when they open the repository root, then a contributing
    guide, a security policy and a code of conduct are present and non-empty
  evidence: []
- text: given the README, when it is rendered, then it carries badges for PyPI version,
    Python versions, license, CI status and the uv/ty/ruff/pytest toolchain, each
    linking to a real target
  evidence: []
- text: given the repository, when a contributor opens a pull request or an issue,
    then a template is offered
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
FROB'S PUBLIC PRESENTATION IS INCOMPLETE FOR A PROJECT ABOUT TO PUBLISH. Owner
request ahead of the alpha. Measured against the sibling repo whose presentation
is the house standard (typani), frob is missing every community-facing document
and every status badge:

    PRESENT      README.md (with banner), LICENSE, CHANGELOG.md
    MISSING      CONTRIBUTING.md, SECURITY.md, CODE_OF_CONDUCT.md
    MISSING      .github/PULL_REQUEST_TEMPLATE.md
    MISSING      .github/ISSUE_TEMPLATE/ (bug_report, feature_request, config)
    MISSING      every README badge -- PyPI version, supported Python versions,
                 license, CI status, typed marker, and the toolchain badges the
                 owner asked for (uv, ty, ruff, pytest)

WHY THIS IS RELEASE WORK AND NOT COSMETICS. A first-time visitor to a repo with
no contributing guide, no security policy and no issue templates cannot tell
whether the project accepts contributions, how to report a vulnerability without
disclosing it publicly, or what a good bug report looks like. For a tool whose
entire premise is that unaccounted-for work should be impossible, shipping
without a stated process is the wrong first impression -- the same argument the
scaffold-noise ticket in this queue makes about a fresh scaffold not being
gate-clean.

FOLLOW THE SIBLING REPO'S SHAPE RATHER THAN INVENTING ONE. Read its versions of
all three documents first. Specifics worth carrying over deliberately:

  - Its contributing guide has TWO PATHS: a terse summary for experienced
    contributors and a full step-by-step walkthrough for a first-ever pull
    request, both pointing at the same commands. Keep that structure. frob's
    version must document frob's OWN workflow -- the ticket queue, the comment
    directives, evidence binding and the close/land dance -- which is
    substantially more than the sibling needs to explain.
  - Its security policy names a supported-version table, private vulnerability
    reporting as the preferred channel, what to include in a report, and a
    stated acknowledgement window. frob's scope section must differ from the
    sibling's: frob executes tooling, spawns subprocesses, reads and writes the
    repository, and runs policy queries over source, so its threat surface is
    genuinely larger than an in-memory value-type library's. Write that section
    from frob's actual behaviour, not by adapting the sibling's paragraph.
  - Its code of conduct is the Contributor Covenant. Use the same, with frob's
    contact address.

BADGES. The owner named the toolchain explicitly: uv, ty, ruff, pytest. Add
those alongside the standard set (PyPI version, Python versions, license, CI,
typed). Every badge must link somewhere useful and must reflect something TRUE
about this repo -- a badge asserting a property we do not actually enforce is
exactly the "catalogued is not enforced" failure this project exists to prevent.
Verify each claim before adding its badge.

ONE THING TO CHECK, NOT ASSUME: there is a Makefile at the repo root, and this
project carries a standing directive that workflows belong in frob subcommands
rather than GNU-make recipes, because make is not available everywhere frob has
to run and a second name for the same operation is a desync waiting to happen.
Read the Makefile. If its targets are one-line wrappers around frob or uv
commands, say so and propose removing it as a separate ticket -- do NOT delete
it inside this one. If it carries real logic, leave it and note why. Either way
the contributing guide must document the frob commands as the interface, never
make targets.

MUST-FIRE FIXTURE:   the three community documents and the GitHub templates
                     exist and are non-empty.
MUST-STAY-QUIET:     the README's existing content and banner survive -- this
                     adds badges and documents, it does not rewrite the prose
                     that is already there.
THIRD FIXTURE:       every badge URL resolves and every in-repo link target
                     exists (no dead links shipped to a first-time visitor).

ACCEPTANCE
- CONTRIBUTING.md, SECURITY.md and CODE_OF_CONDUCT.md written, following the
  sibling repo's structure and frob's own workflow.
- Pull-request and issue templates added.
- Badges added, each one verified true before inclusion.
- The Makefile question answered in writing, with a follow-up ticket filed if
  removal is warranted.
- ASCII only, no emoji, in every file added.
- All three fixtures committed.

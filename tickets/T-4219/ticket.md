---
id: T-4219
title: 'relative image and link targets in the declared long-description file break
  on the package index: fix this README and add a cross-project gate'
state: in-progress
kind: bug
origin: human
created: '2026-09-07'
priority: high
parent: null
tier: ticket
sprint: alpha-gate
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- README.md
- src/frob/gates/_pkg_resources.py
- src/frob/gates/__init__.py
- src/frob/gates/_waive.py
- tests/unit/gates/test_pkg_resources.py
- docs/modules/gates.md
- docs/design/registry/check-coverage.yaml
- src/frob/gates/_doclink_docanchor.py
- design/frob.strata
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/_pkg_resources.py
  reason: 'T-4219: the general reusable gate the ticket asks for requires a new gate
    module, wiring into run_gates/_KNOWN_GATE_RULES, its unit tests, and the rule-catalog
    doc row -- README.md alone was too narrow'
  actor: logan
  at: '2026-09-07'
- op: add
  glob: src/frob/gates/__init__.py
  reason: 'T-4219: the general reusable gate the ticket asks for requires a new gate
    module, wiring into run_gates/_KNOWN_GATE_RULES, its unit tests, and the rule-catalog
    doc row -- README.md alone was too narrow'
  actor: logan
  at: '2026-09-07'
- op: add
  glob: src/frob/gates/_waive.py
  reason: 'T-4219: the general reusable gate the ticket asks for requires a new gate
    module, wiring into run_gates/_KNOWN_GATE_RULES, its unit tests, and the rule-catalog
    doc row -- README.md alone was too narrow'
  actor: logan
  at: '2026-09-07'
- op: add
  glob: tests/unit/gates/test_pkg_resources.py
  reason: 'T-4219: the general reusable gate the ticket asks for requires a new gate
    module, wiring into run_gates/_KNOWN_GATE_RULES, its unit tests, and the rule-catalog
    doc row -- README.md alone was too narrow'
  actor: logan
  at: '2026-09-07'
- op: add
  glob: docs/modules/gates.md
  reason: 'T-4219: the general reusable gate the ticket asks for requires a new gate
    module, wiring into run_gates/_KNOWN_GATE_RULES, its unit tests, and the rule-catalog
    doc row -- README.md alone was too narrow'
  actor: logan
  at: '2026-09-07'
- op: add
  glob: docs/design/registry/check-coverage.yaml
  reason: 'T-4219: frob registry audit --sync-gate-rules wrote the required CHK-GATE-PKG00x
    entries for the new gate rules here'
  actor: logan
  at: '2026-09-07'
- op: add
  glob: design/frob.strata
  reason: 'T-4219: SELFAUDIT001/SYS100 requires the new gate module and its test file
    declared in the fs.read/fs.write capability lists'
  actor: logan
  at: '2026-09-07'
- op: add
  glob: src/frob/gates/_doclink_docanchor.py
  reason: 'T-4219: pkg_resources_gate reuses _doclink_docanchor._line_index for offset->line
    resolution rather than duplicating PERF002''s fix'
  actor: logan
  at: '2026-09-07'
- op: remove
  glob: design/frob.strata
  reason: 'T-4219: reverted -- using code-level frob:waive SELFAUDIT001 instead of
    expanding the design capability lists, to avoid design/frob.strata''s huge doc-closure
    fan-out'
  actor: logan
  at: '2026-09-07'
- op: add
  glob: design/frob.strata
  reason: 'T-4219: SELFAUDIT001/SYS100 matches its waiver against design/frob.strata''s
    own via-list, not code-level frob:waive comments -- declaring the new module/test
    file''s fs.read/fs.write here is the real fix, same as T-2492''s precedent'
  actor: logan
  at: '2026-09-07'
body_changes:
- mode: set
  reason: 'owner narrowed the scope: relative links are fine and must not be flagged,
    only embedded resources that mis-render. Supersedes the license-link finding I
    reported, and removes the need for a fragment carve-out since fragments are links'
  actor: logan
  at: '2026-09-07'
  old_length: 6137
  new_length: 6137
designated_repro_test: null
acceptance:
- text: given a project whose declared long-description file contains a relative image
    source, when the gate runs, then it reports an error
  evidence: []
- text: given the same relative reference in a markdown file that is not the declared
    long description, when the gate runs, then it reports a warning rather than an
    error
  evidence: []
- text: given a project that declares no long-description file, when the gate runs,
    then that case is handled explicitly without crashing or silently passing
  evidence: []
- text: given a relative link target in any markdown file including the declared long
    description, when the gate runs, then it reports nothing
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
THE README'S BANNER AND LICENSE LINK ARE RELATIVE, SO BOTH BREAK ON THE PACKAGE
INDEX. Owner request, and it has bitten them on more than one project.

MEASURED HERE:

    pyproject declares   readme = "README.md"
    relative references in that file:
        src="docs/assets/frob-banner.svg"     the banner image
        href="LICENSE"                         the license badge target

The index renders a project's long description with NO REPOSITORY CONTEXT. A
relative path has nothing to resolve against there, so the banner renders as a
broken image and the license badge links nowhere. On the repository host both
resolve fine, which is exactly why this survives review: the file looks correct
everywhere the author looks at it.

THE FIX FOR THIS REPOSITORY: point the banner at the raw host URL on the default
branch, matching what the sibling project already does -- its README uses an
absolute raw URL for its own banner, which is why it renders on the index and
ours will not. Decide the license link separately: an absolute link to the
repository's license file is the obvious counterpart, and it should be settled
rather than left relative by omission.

THE GENERAL FIX THE OWNER ASKED FOR, AND IT IS THE MORE VALUABLE HALF: make this
a gate, for every project frob checks rather than for this one.

  ERROR, on the file the manifest DECLARES as the long description. Do not
  hardcode a filename. A consumer may declare a different file, or none at all,
  and a gate that assumes the conventional name would silently pass the very
  projects most likely to get this wrong. Read the declared value, and if none is
  declared, say so rather than guessing.

  WARNING, on every other markdown file. Relative links there resolve on the
  repository host and are usually correct; they are only a problem when the
  document is rendered somewhere without repository context. A warning states the
  risk without forcing a fix that would often be wrong.

WHAT COUNTS AS A FINDING, and this needs deciding rather than assuming: image
sources are the visible bite, but relative LINK targets break the same way. Cover
both, and treat a fragment-only reference (a link to an anchor within the same
document) as fine, because it resolves wherever the document is rendered.

DECIDE THE HOST-URL QUESTION EXPLICITLY. The remedy is an absolute URL naming a
host, an owner, a repository and a branch. That is four facts the gate cannot
invent, and a naive auto-fix would guess them. Prefer reporting the finding with
the remedy's SHAPE over generating the URL, unless the manifest already declares
a repository URL the gate can derive it from -- in which case say so and use it.
Note also that pinning a branch name in the URL means the asset moves if the
branch is renamed; that tradeoff belongs in the message, not in a silent choice.

THIS IS THE SAME CLASS AS TWO FINDINGS ALREADY IN THIS QUEUE, which is the
argument for making it a gate rather than a one-off edit: a packaging claim that
is true in the configuration and false in the built artifact, invisible until a
consumer hits it. The typed-marker defect fixed today was exactly that shape --
declared in package data, absent from the wheel, unnoticed for months. A relative
banner is the same failure with a visual symptom instead of a silent one.

MUST-FIRE FIXTURE:   a project whose declared long-description file contains a
                     relative image source reports an error.
MUST-STAY-QUIET:     the same relative reference in a non-declared markdown file
                     reports a warning, not an error; and a fragment-only link
                     reports nothing anywhere.
THIRD FIXTURE:       a project that declares no long-description file is handled
                     explicitly and does not crash or silently pass.

ACCEPTANCE
- This repository's banner and license references resolve when rendered without
  repository context.
- The gate keys on the manifest's declared long-description file, never a
  hardcoded name.
- Non-declared markdown warns rather than errors.
- The auto-fix question decided: report the remedy shape, or derive the URL from
  a declared repository field, but never guess.
- All three fixtures committed.


SCOPE NARROWED BY THE OWNER: RESOURCES ONLY, NOT LINKS.

Relative LINK targets are fine and must NOT be flagged. A relative link that does
not navigate on the index is a minor inconvenience, links to repository files are
a deliberate and common convention, and flagging them would produce noise on
nearly every project. That includes this README's own license-badge link, which I
reported above as a second finding -- it is NOT one, and the section above is
superseded on that point.

FLAG ONLY EMBEDDED RESOURCES, the things that MIS-RENDER rather than merely fail
to navigate:
  - an image source, in HTML tag form or markdown image syntax
  - the same for any other embedded asset the renderer must fetch to display the
    page correctly

The distinction is what the reader SEES. A relative link looks normal and does
nothing when clicked. A relative image renders as a broken-image box in the
middle of the project's front page, on the one surface where most people meet
the project for the first time. Only the second is worth an error.

SO THE RULE IS:
  ERROR    a relative embedded resource in the file the manifest declares as the
           long description
  WARNING  a relative embedded resource in any other markdown file
  NOTHING  a relative link target, anywhere

That also simplifies the fragment question raised above: fragment-only references
are links, so they fall out of scope entirely rather than needing a carve-out.

REVISED FIXTURES
MUST-FIRE:      a relative image source in the declared long-description file
                reports an error.
MUST-STAY-QUIET: a relative LINK target in that same file reports nothing, and a
                relative image in a non-declared markdown file reports a warning
                rather than an error.
THIRD:          a project that declares no long-description file is handled
                explicitly and does not crash or silently pass.

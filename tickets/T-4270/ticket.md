---
id: T-4270
title: the release version parser truncates pre-release and development suffixes,
  so a pre-release and its final release compare as equal
state: queued
kind: bug
origin: human
created: '2026-09-07'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/release/__init__.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: given a development build, a pre-release, and a final release of the same
    version, when they are sorted, then the order matches what the python packaging
    standard requires
  evidence: []
- text: given a pre-release version, when a minimum-version check is applied, then
    it is not treated as satisfying the corresponding final release
  evidence: []
- text: given a version string the parser cannot interpret, when it is parsed, then
    it produces an inspectable failure rather than a confident value computed from
    a truncation
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
THE VERSION PARSER SILENTLY DISCARDS EVERY PRE-RELEASE AND DEVELOPMENT SUFFIX,
SO TWO DIFFERENT VERSIONS COMPARE AS THE SAME VERSION.

MEASURED, by reading the code rather than inferring from behaviour. The release
module's version pattern anchors at the start of the string and captures exactly
three numeric groups, with no anchor at the end. The parse helper returns those
three integers and nothing else. Any suffix a packaging standard would treat as
significant -- a pre-release marker, a development-build counter, a post-release
marker -- is matched past and thrown away without a warning, an error, or a
result the caller could inspect.

WHAT THAT MEANS IN PRACTICE. A pre-release and its corresponding final release
parse to an identical tuple. So does a development build and the release it
precedes. Anything in this module that compares versions, decides whether a bump
covers an API change, or asks whether one version satisfies a minimum, is
therefore blind to exactly the distinctions those suffixes exist to express. It
will report that a pre-release already satisfies the final version's minimum, and
that a development build needs no bump.

THIS IS A SILENT ZERO, NOT A LIMITATION. A parser that rejected these strings
would be merely restrictive and would say so. This one accepts them and returns a
confident answer computed from a truncation, which is the shape this project
treats as its dominant defect class: an absent measurement rendered as a
measured value.

IT BLOCKS TWO THINGS THE OWNER HAS ASKED FOR.

  The first is publishing a pre-release. An alpha that the index will only serve
  to people who opt into pre-releases requires a pre-release suffix in the
  version. Today that suffix would survive into the published metadata while
  being invisible to every check this module performs, so the release machinery
  would compare and gate against the wrong value.

  The second is automatic per-land development-version bumping, which is a
  separate ticket. That feature's whole mechanism is a counter in the suffix this
  parser discards, so it cannot be built correctly on top of this.

WHAT THE FIX SHOULD DO. Parse the whole version according to the packaging
standard the ecosystem actually uses, and preserve ordering across pre-release,
development, and final builds rather than reducing everything to three integers.
Prefer the standard library or the packaging library the project already depends
on over extending the pattern; hand-rolled version ordering is a well-known
source of subtle wrongness and there is no reason to own it here.

A DETAIL THAT WILL BITE WHOEVER TAKES THIS. A trailing hyphen-number, which reads
like a semantic-versioning pre-release, is parsed by the python packaging
standard as a POST-release and therefore sorts AFTER the release rather than
before it. If a suffix scheme is being chosen as part of this work, choose the
one the ecosystem's own tooling agrees with, not the one that looks right.

VERIFY BY ORDERING, NOT BY PARSING. A test that shows the suffix survives the
parse proves little. Prove it by sorting a list containing a development build, a
pre-release, and the final release, and asserting the order the packaging
standard requires.

OWNER DECISION RECORDED, AND IT CHANGES THIS TICKETS URGENCY BUT NOT ITS
CONTENT. The imminent publish will be a plain final release rather than a
pre-release, so this defect no longer blocks it. What remains blocked is the
automatic per-land development-version bumping the owner asked for as core
functionality, whose counter lives in exactly the suffix this parser discards.
Treat this as a prerequisite for that feature rather than as a release gate, and
do not let the lowered urgency turn into a lowered standard: the parser is still
returning confident answers computed from truncated input, and the day someone
does want a pre-release, this will be silently wrong rather than loudly absent.

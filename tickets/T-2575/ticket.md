---
id: T-2575
title: 'no grammar registered warning is 57 percent of command output: the pre-filter
  obligation is on callers and mostly unmet'
state: in-progress
kind: bug
origin: human
created: '2026-08-18'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
scope:
- src/frob/lang/__init__.py
- src/frob/arch/__init__.py
- src/frob/gates/__init__.py
- src/frob/gates/_coverage_sites.py
- src/frob/tickets/_land.py
- src/frob/xref/__init__.py
- src/frob/outline/__init__.py
- tests/unit/lang/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/lang/__init__.py
  reason: 'T-2575: put unsupported-extension warning guarantee in the primitive with
    an explicit caller declaration; collapse the 6 pre-filter sites + .strata carve-out
    onto it'
  actor: logan
  at: '2026-08-19'
- op: add
  glob: src/frob/arch/__init__.py
  reason: 'T-2575: put unsupported-extension warning guarantee in the primitive with
    an explicit caller declaration; collapse the 6 pre-filter sites + .strata carve-out
    onto it'
  actor: logan
  at: '2026-08-19'
- op: add
  glob: src/frob/gates/__init__.py
  reason: 'T-2575: put unsupported-extension warning guarantee in the primitive with
    an explicit caller declaration; collapse the 6 pre-filter sites + .strata carve-out
    onto it'
  actor: logan
  at: '2026-08-19'
- op: add
  glob: src/frob/gates/_coverage_sites.py
  reason: 'T-2575: put unsupported-extension warning guarantee in the primitive with
    an explicit caller declaration; collapse the 6 pre-filter sites + .strata carve-out
    onto it'
  actor: logan
  at: '2026-08-19'
- op: add
  glob: src/frob/tickets/_land.py
  reason: 'T-2575: put unsupported-extension warning guarantee in the primitive with
    an explicit caller declaration; collapse the 6 pre-filter sites + .strata carve-out
    onto it'
  actor: logan
  at: '2026-08-19'
- op: add
  glob: src/frob/xref/__init__.py
  reason: 'T-2575: put unsupported-extension warning guarantee in the primitive with
    an explicit caller declaration; collapse the 6 pre-filter sites + .strata carve-out
    onto it'
  actor: logan
  at: '2026-08-19'
- op: add
  glob: src/frob/outline/__init__.py
  reason: 'T-2575: put unsupported-extension warning guarantee in the primitive with
    an explicit caller declaration; collapse the 6 pre-filter sites + .strata carve-out
    onto it'
  actor: logan
  at: '2026-08-19'
- op: add
  glob: tests/unit/lang/**
  reason: 'T-2575: put unsupported-extension warning guarantee in the primitive with
    an explicit caller declaration; collapse the 6 pre-filter sites + .strata carve-out
    onto it'
  actor: logan
  at: '2026-08-19'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
## Measured

In one `frob ticket doable` invocation: **24 of 42 output lines (57%) were
`no grammar registered for extension ...`**. Extensions seen: `.md` (19),
`.yaml` (2), `.toml`, `.lock`, `.json`.

Reproduced directly:

    parse_file(Path("docs/audits/README.md"))
    -> src/frob/lang/__init__.py:498 _log.warning("no grammar registered ...")

## Root cause: the obligation is on callers, and it is duplicated

`_parse` (`src/frob/lang/__init__.py:498`) BOTH returns
`Err(LangError.UnsupportedLanguage)` AND logs at WARNING. The caller is
already fully informed by the `Result`, so the log line is double-reporting.

Avoiding it is currently every CALLER's job. Measured: only 6 files
reference `tree_sitter_extensions` (`arch/__init__.py`, `gates/__init__.py`,
`gates/_coverage_sites.py`, `lang/__init__.py`, `tickets/_land.py`,
`xref/__init__.py`) against 25+ files that call
`parse_file`/`extract_imports`/`iter_identifiers`. Two of those six carry
long comments explaining that they pre-filter specifically to dodge this
warning -- `tickets/_land.py:3967` and `outline/__init__.py:161`. That is
the same rule written down in multiple places, which is a bug waiting to
desync, and every NEW caller has to independently rediscover it.

## Do NOT simply demote it to DEBUG

The warning has a real job, stated at `tickets/_land.py:3967`: it is "meant
to flag a genuinely unexpected unsupported path reaching a parse call, not
to fire on every single land's routine ledger diff." Blanket-demoting to
DEBUG converts a genuine signal into silence, which is this repo's dominant
bug class (see the silent-zero doctrine, epic T-2391). A fix that makes the
noise go away by making the detector blind is a regression, not a fix.

## Required shape: put the guarantee in the primitive, with a declaration

The caller knows something `_parse` cannot: whether it is walking a
HETEROGENEOUS tree (where unsupported extensions are expected and routine)
or dispatching a file it BELIEVES is source (where an unsupported extension
is a genuine surprise worth a WARNING).

Make that distinction explicit at the call site instead of implicit in
whether the caller remembered to pre-filter. Sketch, to be refined:

- a way for a caller to declare "heterogeneous input expected" -- e.g. a
  `parse_if_supported()` variant returning an Option/Result with NO warning,
  or an explicit keyword on the existing entry points
- the loud WARNING then fires ONLY for callers that did not declare it,
  which is exactly the "genuinely unexpected" case it was written for
- the six existing pre-filter sites collapse onto the declaration, removing
  the duplicated rule and the two explanatory comments

Additionally, even where the warning IS legitimate, firing once per FILE is
excessive; once per (extension, call site) per run carries the same
information. Deduplicate.

## Positive controls, both directions

- a caller that declares heterogeneous input and hits a `.md` file: NO
  warning, and still gets `Err(UnsupportedLanguage)` so behavior is unchanged
- a caller that did NOT declare it and hits a genuinely unexpected
  unsupported extension: STILL warns. Without this case the fix is
  indistinguishable from demoting to DEBUG.

## Notes

- Verify the 6-vs-25 caller split by measurement before relying on it; those
  numbers are from `git grep` and name FILES, not call sites.
- `.strata` has its own carve-out in `outline/__init__.py` (T-0129) --
  fold it into the same declaration rather than leaving a third mechanism.

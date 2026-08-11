---
id: T-2080
title: 'gate-gap class 4 (non-python doc targets): frob.toml severity + remaining
  config surfaces still unanchored'
state: queued
kind: feature
origin: human
created: '2026-08-10'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/gates/**
- docs/audits/docs-staleness-2026-07-29.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
Split from T-1226 (measured 2026-08-10). Gate-gap class 4 (NON-PYTHON
TARGETS, docs/audits/docs-staleness-2026-07-29.md) is only partially
closed: T-1230 shipped DOC010, which resolves `` `make <target>` ``
citations against real Makefile targets
(`src/frob/gates/_doclink_docanchor.py::docmake_gate`, wired).

Still open, no dedicated mechanism:
- frob.toml severity claims in prose (e.g. "ARCH101 is a report, not a
  gate" when frob.toml declares it error) have no anchor -- DOC006's
  kind 3 (CONFIG REFERENCE) only resolves `[section]`/`[section.key]`
  existence, not a claimed VALUE against the real one.
- pyproject.toml entries, tmLanguage grammar lists, and other non-Rust,
  non-Makefile config surfaces still have no graph node at all.
- Rust file layout/symbol citations are now covered incidentally by
  class 2's T-1228 FILE::SYMBOL kind (`path.rs::name`), not by a
  dedicated class-4 mechanism -- worth confirming that coverage is
  sufficient before scoping new work here, rather than re-deriving it.

Suggested first step: measure how many of the original finding's
non-Makefile NON-PYTHON TARGETS instances (docs/audits/docs-staleness-
2026-07-29.md's own "Non-python targets" section, 3 items) are now
already caught incidentally by T-1228's Rust FILE::SYMBOL kind before
designing new mechanism work -- the denominator may already be smaller
than the original finding implies.

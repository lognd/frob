---
id: T-2187
title: 'walk_strata parses .strata with the strata-core grammar then discards it,
  extracting symbols by line regex instead and downgrading the disagreement to a log
  warning: 16 mismatches in a single run'
state: queued
kind: bug
origin: human
created: '2026-08-16'
priority: high
parent: T-1662
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/lang/_walk_strata.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
acceptance:
- text: 'Symbols MUST come from strata-core''s parse result, not from _HEADER_RE over
    source lines. walk_strata (src/frob/lang/_walk_strata.py) already calls strata_core.parse_source(source)
    and has the authoritative grammar output in parsed[''ok''], then throws it away:
    _extract_symbols(lines) produces the symbols actually returned, and _check_declared_count_drift
    only LOGS when the two disagree. Measured: 16 ''header-regex symbol count != strata-core
    declared count'' warnings in a single frob verify explain run. This test MUST
    fail against current main.'
  evidence: []
- text: Given a .strata source where the grammar and the header regex disagree on
    symbol count, when walk_strata runs, then the returned symbols match the grammar's
    declarations -- not the regex's. Today the regex result is returned and the mismatch
    is a warning the caller never sees.
  evidence: []
- text: 'Do NOT fix this by tightening _HEADER_RE until the counts agree on today''s
    corpus -- that is a lexical fix to a lexical defect and the next construct reopens
    it. Do NOT delete the drift check either: keep it, but it should be a fail-closed
    disagreement between the grammar and any remaining heuristic, never a silent log
    line. Note strata symbols feed capability enforcement, which T-1623 (critical)
    is separately trying to make watertight -- a wrong symbol set undermines that
    gate silently.'
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
---

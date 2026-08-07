---
id: T-1662
title: 'EPIC: every check must decide from semantics, never a lexical match'
state: queued
kind: security
origin: human
created: '2026-08-06'
priority: high
parent: null
tier: epic
sprint: null
runs_last: false
scope:
- src/frob/gates/**
- src/frob/vet/**
- src/frob/strata/**
- docs/**
- tests/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
STANDING PRINCIPLE, set by the repo owner 2026-08-06: every frob and strata check must decide from SEMANTICS -- a resolved symbol, a parsed AST node, a graph edge -- and never from a lexical/textual match. A check that greps is guessing.

This is not a hypothetical concern. Lexical matching has produced a documented incident or false-positive class roughly once per wave in this drive:

- PERF011 counted loop tokens instead of reading nesting structure -- 71% false positives (T-1647), fixed at the rule.
- PERF014 had the identical flaw -- 6 of 9 findings false (T-1649), rewritten as an AST ancestor-depth pass.
- DEAD001 never populated Violation.symref, so waiver matching fell back to FILE SCOPE -- 44 of 62 findings silently mis-waived (T-1652). OPAQUE001 has the same hole with 166 live waived findings (T-1659).
- Four separate detectors read explanatory PROSE as declarations: TICK006 on a marker quoted mid-sentence (T-1541), the live-tracker scan on Done-report narrative (T-1633), INV006 on a waiver reason and again on a module's historical narrative (T-1640).
- The vet capability scanner decides "does this code eval?" by substring search over raw bytes, with per-language binding passes bolted on afterwards to recover aliasing their own comments admit the lexical path "structurally cannot" catch (T-1626).
- An `except json.JSONDecodeError:` clause compared as verbatim TEXT against a bare name never discharged its leak (T-1636).

MEASURED AUDIT of src/frob/gates (60 modules), counting semantic signals (raw_tree/parse_file/GraphSnapshot/callgraph/lang.) against lexical ones (re.search/match/findall/NEEDLE/_PHRASE/startswith/endswith):

Gates with NO semantic signal at all -- pure lexical:
  _refs (22 lexical signals), _tickets_gate (14), _fmt_directives (6),
  _exclude_hazard (5), _secrets (5), _rule_id_scan (4), _render_lint (3),
  _mutation_evidence (2), _ffi_boundary (1), _waive_lease (1), _walk_lint (1)

Gates that are lexical-DOMINANT despite having some semantic access:
  _docptr (7 semantic / 32 lexical), _docblocks_refs (4/23),
  invariants (1/22), _doclink_docanchor (7/14)

Two confirmed concrete cases from that list:
- REF001 (_refs) decides "this file has no inbound references" by looking for its full path or BARE BASENAME mentioned in another file's text. A file reached through a constructed path, a variable, or an import alias is invisible to it; a file merely NAMED in unrelated prose counts as referenced. Both directions are wrong.
- WALK001 (_walk_lint) flags unpruned traversals by matching `os.walk`/`rglob` call TEXT. An aliased or indirectly-bound traversal evades it entirely.

NOT every lexical check is wrong, and this epic must not pretend otherwise. Some are legitimately textual by nature: _fmt_directives is a FORMATTER (it rewrites comment text), _secrets uses entropy/pattern detection which is the industry-standard approach, and a whole-file rule like LARGE001 has no symbol to bind to. The deliverable is a JUDGEMENT per check, not a blanket rewrite.

Children should:
1. Classify every gate rule as (a) genuinely semantic already, (b) lexical but legitimately so -- state why, (c) lexical and WRONG -- raise it to semantics.
2. For each (c), raise it, reusing the substrate that already exists: frob.graph.callgraph for resolution, frob.lang.raw_tree for AST, the snapshot's symbols/edges for the obligation graph. Do NOT build a second parallel analysis layer.
3. Establish the fail-closed rule this drive learned the hard way: when semantic resolution CANNOT determine an answer (genuinely dynamic dispatch, a computed getattr), the check must report UNRESOLVED and demand a declaration -- never silently pass. Every major incident this drive traced to analysis that reported "nothing found" when it could not look.
4. Add a meta-check if feasible: a new gate rule constructed from raw text without a symref or AST node should itself be a finding, so this class cannot silently return.
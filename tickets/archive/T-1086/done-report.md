## Done report

Partial-with-residue land: split the smallest of the four T-1086 monsters,
src/frob/dup/_pipeline.py (2628 lines), into src/frob/dup/_pipeline/ (a
package: __init__.py 200 lines, _shared.py 227, _normalize.py 411,
_callgraph.py 538, _fingerprint.py 798, _probe.py 336, _smt.py 314 -- every
file under the 950-line T-1072/T-1076 convention).

Split by cohesive family, mirroring the module's own rung-ladder structure:
_shared.py (keyword/token tables + the _FpState fingerprint accumulator
used across every submodule), _normalize.py (R1/R2 token normalization +
statement chunking), _callgraph.py (touched_refs + call-substitution/
inlining + the R5 def-use graph builders, both real-subtree and
co-occurrence-proxy paths), _fingerprint.py (R3-R5 fingerprinting,
candidate pairing/verification, find_clones/find_helper_clones), _probe.py
(R6 opt-in observational probing), _smt.py (R7 opt-in bounded-SMT via z3).
__init__.py carries the full original module docstring unchanged and
re-exports the 4 public symbols (find_clones, find_helper_clones,
probe_equivalence, touched_refs) plus every private symbol tests reach
into directly (_r1_hash, _KEYWORDS, _FpState, _normalize_error_channel,
_abstract_if_conditions, _abstract_guard_exit_bodies,
_collapse_duplicate_guard_chains, _is_symref, _callee_name_map,
_find_block, _real_dataflow_graph, _characteristic_vector,
_cosine_similarity, _nicad_size_ratio_ok, _oreo_metric_ratio_ok,
_deckard_vector_ok, _r4_candidate_pair, _probe_smt_equivalence) -- zero
caller edits anywhere outside the split itself.

Directives carried with their symbols: every frob:ticket/frob:doc/
frob:waive/frob:invariant comment moved with the function it annotates
(verified by grep before/after -- same directive count, same symbols).
The two dup/_pipeline.py entries in gates/_pii_structural/_keywords.py's
_PII012_REVIEWED_NON_PII allowlist ("TOKEN"/"token") were replaced with
per-new-file entries covering every file that still contains the
identifier text (__init__.py, _callgraph.py, _fingerprint.py,
_normalize.py, _shared.py). No INV006 file-level waiver or ratchet-lock
entry existed for the old file (checked frob-ratchet.lock.json), so
nothing to carry there.

docs/modules/dup.md's 5 frob:describes anchors (find_clones,
probe_equivalence, _probe_smt_equivalence, touched_refs,
find_helper_clones) were repointed at each symbol's new file; 8 dup test
files' frob:tests directives (test_dup.py, test_dup_smart.py,
test_dup_region.py, test_dup_native_rungs.py, test_dup_cross_lang.py,
test_dup_inline.py, test_dup_r5_multilang.py, test_dup_rungs.py) were
repointed the same way. Two prose mentions in dup.md/the dup-detector-
registry guide were updated for accuracy; tickets-archive.md's historical
log entries were left untouched (archive, never edited).

Root cause of an initial "No such file or directory: .../_pipeline.py"
gate crash: the deletion was unstaged and the new package untracked, so
frob's git-tracked-file walk (xref/exports_consumers via iter_files) still
saw the old path and no longer saw the new one. Fixed by staging
(git add -A) before re-running gates -- not a frob bug, a sequencing
mistake in this pass.

Gates run chunked (lint, static, gates-native, gates-fast, gates-security):
0 errors across all five groups. Full dup test suite green. Deletion-filter
check (git diff main --diff-filter=D --stat) shows only the intended
src/frob/dup/_pipeline.py deletion.

T-1086 residue (NOT done, still queued for a future pass): the other three
monsters -- src/frob/app/ticket_runner.py (3957), src/frob/tickets/__init__.py
(4260), src/frob/tickets/_land.py (4762) -- untouched. T-1074 (800-2000-line
triage) not started; no budget remained after this file's split + gate/test
verification within this dispatch's turn budget.

### Changed
```
 docs/guides/extending/dup-detector-registry.md |    2 +-
 docs/modules/dup.md                            |   12 +-
 src/frob/dup/_pipeline.py                      | 2628 ------------------------
 src/frob/dup/_pipeline/__init__.py             |  200 ++
 src/frob/dup/_pipeline/_callgraph.py           |  538 +++++
 src/frob/dup/_pipeline/_fingerprint.py         |  798 +++++++
 src/frob/dup/_pipeline/_normalize.py           |  411 ++++
 src/frob/dup/_pipeline/_probe.py               |  336 +++
 src/frob/dup/_pipeline/_shared.py              |  227 ++
 src/frob/dup/_pipeline/_smt.py                 |  314 +++
 src/frob/gates/_pii_structural/_keywords.py    |   10 +-
 tests/test_dup.py                              |   26 +-
 tests/test_dup_cross_lang.py                   |    8 +-
 tests/test_dup_inline.py                       |    2 +-
 tests/test_dup_native_rungs.py                 |    8 +-
 tests/test_dup_r5_multilang.py                 |   12 +-
 tests/test_dup_region.py                       |    6 +-
 tests/test_dup_rungs.py                        |   14 +-
 tests/test_dup_smart.py                        |    2 +-
 tickets.md                                     |   55 +-
 20 files changed, 2932 insertions(+), 2677 deletions(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 12 passed (from 12 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)

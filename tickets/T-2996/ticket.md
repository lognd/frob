---
id: T-2996
title: Language-support matrix has 5 facets but 13 packages specialize per-language;
  refactor is silently Python-only and invisible to detection
state: queued
kind: bug
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
frob already has the right machinery for this and it is genuinely good:
`src/frob/lang/_support.py` derives a `LanguageSupport` snapshot per language
from the upstream registries, every `(language, facet)` cell is IMPLEMENTED /
NOT_APPLICABLE(reason) / KNOWN_GAP(reason + tracking ticket), an ABSENT cell is
what `conformance_violations` flags, and LANG003 currently reports 12 tracked
gaps. That module's own docstring states the problem it was built for: "a
half-added language (the PyO3-publicness incident class) shipped silently."

The matrix is not the problem. Its COVERAGE is.

MEASURED 2026-08-26:

    FACETS = (grammar, capability, dup, arch, docblock)   -- 5 facets

Packages containing per-language specialization, by language-literal density:

    321  src/frob/vet          82  src/frob/lang         41  src/frob/gates
     40  src/frob/arch         38  src/frob/app          25  src/frob/perf
     21  src/frob/strata       17  src/frob/dup          10  src/frob/_cli_parsers
      9  src/frob/check         9  src/frob/graph         8  src/frob/testing
      4  src/frob/policy

Thirteen packages branch on language identity. Five facets exist. So
`perf`, `strata`, `graph`, `testing`, `check`, `app`, `policy` and
`_cli_parsers` all carry language-sensitive behaviour that the completeness
matrix never asks about.

THE SHARPEST FINDING, and the reason this cannot be fixed by detection alone:
`src/frob/refactor` does not appear in that list AT ALL, because it contains
ZERO language literals. It does not branch on language -- it simply assumes
Python. `frob refactor --help` says so outright: "move a Python symbol",
"rename a Python symbol".

A silently single-language module is INVISIBLE to a "find the per-language
dispatch" scan. It has nothing to find. That is strictly worse than a declared
gap, and it is exactly the shape the LanguageSupport module was built to
prevent -- just one level up, at the facet axis rather than the language axis.

So a meta-test built purely on detecting language branching would pass while
`refactor` remains Python-only forever. The meta-test must work from a DECLARED
axis and require every language-sensitive module to have a cell, with detection
used only as a cross-check that the declaration has not fallen behind reality.

WHAT IS WANTED -- three parts, in this order:

1. ADD `refactor` AS A FACET. Every supported language then needs a cell:
   IMPLEMENTED, NOT_APPLICABLE with a reason, or KNOWN_GAP with a tracking
   ticket. Expect this to light up LANG003 substantially on first run; that is
   the point, and the findings are honest debt rather than noise. Do not
   pre-emptively mark everything KNOWN_GAP to keep the number small -- judge
   each cell.

2. AUDIT THE FACET AXIS ITSELF for the other twelve packages. For each, decide
   and record: is its language-sensitive behaviour already covered by an
   existing facet, does it need a new facet, or is it genuinely
   language-agnostic? Register or justify every one. This is the meta-question
   the owner asked -- not "are all languages covered by the facets we have" but
   "do the facets we have cover everything that requires per-language
   specialisation".

3. THE META-TEST. Assert that no module with per-language specialisation is
   un-faceted. Since detection alone cannot see a silently single-language
   module, this needs both halves:
   - a declared registry of language-sensitive modules, each mapped to its
     facet (or explicitly justified as agnostic); and
   - a detection cross-check that fails when a package acquires language
     branching without a corresponding facet entry -- so the registry cannot
     silently fall behind.

THE OWNER'S SHARED-MACHINERY POINT, which governs part 1's implementation:
refactoring should use the SAME machinery as vet and the other language-aware
subsystems wherever the work is genuinely shared -- `frob.lang`'s grammars and
`NormalizedModule` already exist and every adapter fills them identically. Do
not build a second per-language abstraction beside them; two copies of a
language registry is a bug waiting to desync, which is the same rule
`_support.py` itself was written to enforce.

But where a module GENUINELY REQUIRES per-language specialisation, that
specialisation must be complete across all supported languages, not present for
Python and absent elsewhere. Reference rewriting is a real example: resolving
what a symbol reference IS differs per language (Python imports vs TypeScript
module specifiers vs Rust `use` paths vs C++ includes), so some specialisation
is unavoidable -- and each language then needs a real cell, not silence.

ACCEPTANCE
- `refactor` is a FACETS member; every supported language has an explicit cell
  with a reason for anything not IMPLEMENTED, and every KNOWN_GAP names a
  tracking ticket.
- All thirteen measured packages are classified: covered by an existing facet,
  assigned a new facet, or justified as language-agnostic -- with the reasoning
  recorded, not merely asserted.
- A meta-test fails when a package gains per-language specialisation without a
  facet entry. Must-fire fixture: a package with language branching and no
  facet. Must-stay-quiet fixture: a genuinely language-agnostic package.
- Report the LANG003 count before and after. A large increase is a SUCCESS
  condition here, not a regression -- it is previously-invisible debt becoming
  visible. Report it plainly rather than suppressing it.

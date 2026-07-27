# Full-repo capability audit (2026-07-20)

Seven read-only `auditor` passes over the whole codebase, one per cohesive
subsystem, under a single North-Star: **if `frob check` / a ticket-close / a
strata proof passes, the thing it claims must actually hold.** The mandate was
to find every way that is *false* -- pessimistically, with concrete repros.

Remediation is tracked under **T-0397** (audit remediation epic); every HIGH
finding gets an actionable child ticket. These findings files are the durable
record (referenced here so they are not themselves orphaned -- the failure mode
that motivated the audit).

## Verdict per subsystem (honest, pessimistic)

| Subsystem | File | HIGH | Total | One-line verdict |
|---|---|---|---|---|
| tickets + testing | [tickets-testing.md](tickets-testing.md) | 5 | 12 | Evidence means "a test EXISTS", never "passed" or "covers this code" -- a red or unrelated test closes any ticket; `land` re-runs nothing. RIGHT about bookkeeping, FAST-but-wrong about proof-of-work. |
| strata (proof engine) | [strata.md](strata.md) | 5 | 12 | Boundaries never bound to code; proofs pass vacuously when the dangerous flow is un-modeled; `eval` globally excused; files loose under `src/frob/` escape all sys rules. The vacuous-proof lineage (T-0256/0193) is not closed. |
| vet | [vet.md](vet.md) | 6 | 14 | Approves code it never read (source-unavailable = empty caps); only the first lockfile scanned; CVE fingerprints + all non-Python needles rename/whitespace-evadable; C/C++ table misses file I/O and most exec/net. Python resolver is the one sound piece. |
| gates: accounting | [gates-accounting.md](gates-accounting.md) | 3 | 15 | Verifies procedural existence (a named test, a doc edge, an ack), not code quality. The one blocking per-symbol test gate clears on a vacuous name-match; DRIFT001's sig facet is blind to body rewrites; TS/C/C++ `frob:tests` need no execution. Coverage/stamp chain is gitignored-local so CI can't trust it. |
| lang + check + docs | [lang-check-docs.md](lang-check-docs.md) | 3 | 12 | Doc/coverage/drift gates run ONLY in the Python pipeline -- a Rust/C++/TS repo gets zero COV/DOC/DRIFT despite the polyglot promise. Parse/IO failure silently erases a file's whole obligation set. COV001 is WARN-only. |
| graph + edges | [graph.md](graph.md) | 2 | 12 | `load_graph` only re-hashes files already cached, so a newly-added file returns Ok on an incomplete snapshot; a non-UTF-8 `.md` hard-crashes `frob check`. Foundation-level "passes on an incomplete graph" holes. |
| performance + caching | [perf.md](perf.md) | 5 | 12 | ~168s CPU is redundant parsing: `frob.lang._parse` uncached so each file parsed 2-6x, the 745k-node tree re-walked ~7x/run, 17 gates GIL-serialized so archgate(91.5s)+sys(77s) never overlap. Shared single-parse + parse-cache + process-pool is the fix (and the warm daemon T-0177). |
| check performance (T-0928, end-to-end profile) | [check-performance.md](check-performance.md) | -- | -- | Discovered `frob.perf`'s own collectors (cProfile, StackSampler, heat) are blind to thread-pool/process-pool gate dispatch -- roughly half a profiled `frob check` run resolves to `heat`'s own "unattributed" bucket. Ranked wall-clock table anchored on `gate-summary` brackets instead: static-bucket, test, archgate, perf, sys top the list. Four follow-up tickets filed. |
- [Coordination churn self-audit](coordination-churn.md) -- 2026-07 zero-drive retrospective: six recurring coordination frictions, each with a design-out (T-0999 epic)
| gates: quality/security | [gates-quality.md](gates-quality.md) | 3 | 15 | The ENTIRE quality surface is non-blocking (WARN): perf smells, undeclared PII, god-classes, deep nesting all exit 0. DUP fails open (default-off + no-op without natives). `frob:secret-fake` suppresses real secrets with no accountability. |

## Convergence protocol

This audit is NOT a one-shot. Standing loop per subsystem: **audit -> fix every
finding the RIGHT way -> re-run the pessimistic auditor (still instructed to find
10+) -> repeat until it comes back empty despite that instruction.** A subsystem
is only "done" when a fresh pessimistic pass finds nothing. Tracked under T-0397.

## Cross-cutting themes

0. **Green makes no claim about code quality.** `frob check` exits nonzero ONLY
   on error-severity findings; the whole quality/security surface (PERF, PII010,
   SEC110, ARCH001, DUP, lower secrets) is WARN. The celebrated "0 warnings" was
   0 *error-tier* -- a repo full of smells still exits 0. The single biggest
   North-Star gap.
1. **Existence != proof.** The single loudest theme: evidence, doc edges,
   `frob:tests` bindings, and registry entries are checked for *existence*, not
   for *truth* (did the test pass? does it cover the code? does the doc match?
   is the entry enforced?). This is the same class as the orphaned-registry
   breach ([[catalogued-is-not-enforced]]).
2. **Python-only enforcement.** COV/DOC/DRIFT/INV and the binding-aware capability
   resolver run for Python and silently no-op for TS/Rust/C/C++ -- the polyglot
   promise is undelivered off Python.
3. **Fail-open on the unknown.** Unparseable file, source-unavailable dependency,
   unknown-language change, missing tool, second lockfile, non-UTF-8 doc --
   again and again the response is silent skip / empty result / neutral pass,
   never a loud fail-closed.
4. **Gitignored-local trust.** The coverage/stamp/baseline/prework signals live
   in `.frob/` (gitignored), so CI cannot verify the one behavioral gate that
   exists.

## Is it good enough?

No -- not yet, measured against its own North-Star. It is a genuinely careful
*bookkeeping and orchestration* system (id allocation, ledger splice, collection
caching, git choreography, the Python capability resolver, missing-tool doctrine
are all sound). But the load-bearing *proof* claims -- "this is tested", "this
is covered", "this proof holds", "this dependency is safe", "docs match" -- are
verified by existence-checks that a lazy or hostile author passes trivially, and
the enforcement is Python-shaped in a tool that promises polyglot. The right-way
fix is to make each green *earned*: tests must pass and cover; proofs must bind
to code and fail-closed on incompleteness; enforcement must span languages;
signals CI needs must be tracked, not gitignored.

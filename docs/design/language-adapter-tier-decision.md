# Next language-adapter tier: decision (T-0691)

<!-- frob:doc docs/design/language-adapter-tier-decision.md#decision -->

## Question

Should frob's language-adapter surface (the per-language `*Adapter` family,
e.g. `frob.arch._python.PythonAdapter`, T-0609) expand beyond the current
Python/TypeScript-JS/Rust/C/C++/Kotlin set (T-0614 shipped
`frob.arch._kotlin.KotlinAdapter`) toward
Go, Java, or C#, per the github.com Innovation Graph global metrics and
the TIOBE index? Both indexes rank Java, Go, C# as the largest
uncovered languages by global usage, then PHP/Ruby/Swift.

## Estate survey (2026-07-23)

Checked the actual language mix of the 9-repo estate this tool is
dogfooded against (per the sibling-repos-rollout record: lithos,
feldspar, graphite, typani, lograder, aprog-public, aprog-private,
logand.app, malmberg), by inspecting each repo's `frob.toml`
`[graph]`/`[check]` configuration and source tree directly:

| Repo | Primary language(s) actually present |
|---|---|
| lithos | Rust (crate + fuzz harness), Python (schema/codegen tooling), firmware examples |
| feldspar | Python + Rust (pyo3-mixed) |
| graphite | Python backend; TypeScript/React frontend (own toolchain, excluded from frob's graph) |
| typani | Python |
| lograder | Python; vendored C++ fixture projects (not real source under obligation) |
| aprog-public | Python; per-assignment C/C++ activity/course content |
| aprog-private | Python; per-assignment C/C++ course content |
| logand.app | TypeScript/React frontend; Rust (wasm-ascii); no Java/Kotlin/C# tree present |
| malmberg | (not present in this checkout; not independently re-surveyed this pass) |

No Go, Java, or C# source tree exists anywhere in the 8 repos actually
checked out and inspected. Kotlin (T-0614, `KotlinAdapter` shipped) is
already the newest addition -- and even that has no real consuming repo in
the estate yet; it was speculative ahead of demand.

## Decision: none for now, stay demand-driven

Do not file implementation tickets for Go, Java, or C# adapters at this
time. This ticket's own recommendation (recorded verbatim in its
Description) already named the reasoning; the estate survey confirms
it rather than overriding it:

- The adapter protocol (T-0609's `LanguageAdapter` + normalized model)
  makes each new language a bounded, roughly one-session ticket once a
  real consumer exists -- there is no compounding cost to waiting.
- An adapter with zero exercising repos is exactly the
  catalogued-but-unenforced dead weight this repo's own doctrine
  forbids (see the Static-quality-vision / catalogued-is-not-enforced
  lineage): it would sit in `frob.arch` unexercised by any real
  `frob check` run, with no fixture repo to prove it correct against
  or keep it honest under drift.
- TIOBE/Innovation Graph rank global popularity, not THIS estate's
  actual composition -- the estate is the only demand signal that
  matters for what frob itself needs to enforce.

## Reopen criterion

Revisit this decision (a fresh ticket, not reopening this one) the
moment either becomes true:
1. A repo in the 9-repo estate (or a user project frob is run against)
   gains a real Go, Java, or C# source tree that needs `frob check`
   coverage, or
2. The user explicitly asks for one of these languages ahead of any
   estate repo adopting it (a deliberate speculative build, called out
   as such rather than inferred from index rankings).

Kotlin (T-0614) is unaffected by this decision -- it was already
in-flight before this ticket and stays on its own track; this decision
covers only the Go/Java/C# question the ticket was opened to answer.

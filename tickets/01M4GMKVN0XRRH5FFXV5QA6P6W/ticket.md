+++
id = "01M4GMKVN0XRRH5FFXV5QA6P6W"
title = "grmb research cycle R2 (early): verification and traceability practice (G); ambient faults and exhaustive error handling (H)"
type = "docs"
category = "in-progress"
priority = "medium"
points = 5
reporter = "lognd"
created = "2026-10-09T15:30:55Z"
updated = "2026-10-09T17:23:54Z"
labels = ["grimble"]
scope = ["notes/research/grmb-r2-*", "changelog.d/**"]

[[acceptance]]
text = "Given topics G and H, when R2-early completes, then notes/research/grmb-r2-verification.md and grmb-r2-faults.md exist with search log, coverage argument, graded findings, ADOPT/ADAPT/REJECT implications and candidate rules, every source looked up or marked [unverified]"
bound = true
+++

Research cycle R2 (early start, owner request 2026-10-09). Same rules as the R1 brief (ticket ~19SEHXJ body): exhaustive with a coverage argument, every source looked up, credibility line per source (venue; authors' practical standing at scale), primary sources over blogs, anonymous blogs excluded, [unverified] never invented, ADOPT/ADAPT/REJECT implications for grmb with candidate rules (predicate, polarity, source).

G verification and traceability practice: how modern teams tie verification to goals: V-model in regulated domains (DO-178C, ISO 26262, IEC 62304, ASPICE; DOORS/Polarion/Jama practice), agile and product teams (acceptance criteria, ATDD, specification by example, BDD at scale, test pyramid/trophy evidence, contract testing such as Pact, consumer-driven contracts), requirements-based testing, empirical studies of traceability in industry; when verification is planned relative to requirements (test-first vs after), and how teams keep goal-to-test links alive. Implication target: the grmb level pairing goal->acceptance, scenario->system/e2e, flow->integration/contract, waypoint->unit, and grimble trace showing the V.

H ambient faults and exhaustive error handling: Java Error vs Exception and the checked-exceptions debate (evidence), Rust panic vs Result, Zig explicit OutOfMemory and error sets, Swift typed throws, Go panic/recover, Erlang/OTP let-it-crash and supervisors, crash-only software (Candea and Fox), C++ noexcept, Python exception analysis tools and studies, empirical studies of exception handling bugs (e.g. Yuan OSDI 2014 follow-ups); per-language error-flow analysis (what can be known statically about raised/thrown sets). Implication target: a pedantic profile where ambient faults (MemoryError, RecursionError, signals, panics, OOM, stack overflow, kill) need one declared policy per scenario or system, and the error-flow facts of ticket ~589WNWE.

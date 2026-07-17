---
id: T-0001
title: frob-core PyO3/maturin crate + smart dup (Phase 7)
state: queued
kind: feature
origin: human
created: '2026-07-17'
blocked_by: []
parent: null
scope:
- src/frob/dup/**,frob-core/**
evidence: []
attachments: []
---
Phase 7 (0.2.0), designed in docs/dup.md: frob-core PyO3/maturin crate (R3 canonicalizer, winnowing, LSH, WL-kernel, APTED; compute-only, no-Python-fallback, lithos as build reference); region-granular matching (function/subsection); content-addressed fingerprint + LRU verdict caches in .frob/dup.db; DUP001/DUP002 gates; R6 observational probing via frob.fuzz generators; pre-work sweep re-platformed onto it.
---
id: T-0008
title: 'frob.vet: dependency capability vetting (docs/vet.md build-out)'
state: queued
kind: security
origin: human
created: '2026-07-17'
blocked_by: []
parent: null
scope:
- src/frob/vet/**
evidence: []
attachments: []
---
Full build-out of frob.vet per docs/vet.md: tree-sitter capability scan of the locked dependency tree, declaration-vs-observation conformance ([vet.allow]), version capability-escalation diffs as primary supply-chain signal, obfuscation unconditionally fatal, content-addressed verdict cache; VET001-VET010 gates; typed adapters over osv-scanner/GuardDog/Scorecard/sigstore-SLSA with skipped-never-silent absence; per-ecosystem rule families (VET-PY/VET-RS/VET-C/VET-JS) plus VET011 slopsquat/cooldown quarantine; first-party anomaly detectors (VET008 artifact/source divergence, VET009 stylometric self-similarity via frob-core WL kernels, VET010 sandboxed capability divergence); absorbs license/pinning checks. Not touched by this ticket's author -- owned by the concurrent vet workstream.
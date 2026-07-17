---
id: T-0016
title: Re-platform map/outline/xref/cycle/dup onto frob.lang; delete frob.ast
state: queued
kind: feature
origin: human
created: '2026-07-17'
blocked_by:
- T-0001
parent: null
scope:
- src/frob/map/**,src/frob/outline/**,src/frob/xref/**,src/frob/cycle/**,src/frob/dup/**,src/frob/ast/**
evidence: []
attachments: []
---
Re-platform map/outline/xref/cycle/dup onto frob.lang's uniform ParsedFile contract, then delete src/frob/ast. Deferred post-0.1.0; blocked_by T-0001 since dup's re-platform is entangled with the frob-core work.
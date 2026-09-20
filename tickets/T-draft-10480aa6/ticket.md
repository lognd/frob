---
id: T-draft-10480aa6
title: 'A11Y: WCAG 2.2 Level A and AA static rules over HTML/JSX/TSX/Vue/templates
  plus accessibility statement page (42 criteria, 40 static)'
state: queued
kind: ux
origin: human
created: '2026-09-20'
priority: high
parent: T-draft-09897a86
tier: story
sprint: v0.534.0
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
component: gates
anchor: false
anchor_reason: null
land_commit: null
---
45 entries, 40 static: alt on img and svg role=img; heading order and single h1 (also SEO); html lang and lang on parts; page title unique; link and button accessible names; form inputs with labels; autocomplete on identity fields (1.3.5); skip link (2.4.1); focus visible not suppressed (outline:none without replacement); tabindex>0; aria-hidden on focusable; invalid ARIA role/attribute pairs; duplicate ids; autoplay media without controls; video without track kind=captions; target size 24px (2.5.8); prefers-reduced-motion respected when animations exist; color-only meaning (dynamic-only -> axe obligation); contrast (static where colors are literal in CSS, else axe). Accessibility statement page required with the W3C WAI statement contents (commitment, standard applied WCAG 2.2 AA, contact, known limitations, measures, technical prerequisites, tested environments). Authorities: WCAG 2.2, ADA Title II rule 28 CFR 35.200, EAA 2019/882, Section 508, EN 301 549. axe-core/pa11y as an optional adapter for dynamic-only criteria, registered in the tool registry.
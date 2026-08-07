---
id: T-0179
title: 'TTY-aware pretty output: colors and formatting across all frob commands'
state: done
kind: ux
origin: human
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/logging/**
- src/frob/app/**
- src/frob/check/**
- tests/**
- docs/**
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_app_style.py::test_ticket_list_json_never_has_ansi_even_with_force_color
- tests/unit/test_app_style.py::test_stats_json_never_has_ansi
designated_repro_test: null
threat: null
component: null
---
Bake consistent pretty formatting and color into frob's terminal output for TTYs, skipped cleanly when non-TTY. Build on the existing src/frob/logging/color.py should_color machinery -- single source of truth, honoring isatty, NO_COLOR, FORCE_COLOR, and a [tool.frob] override. Apply across the surfaces users actually read: frob check tool/gates summary (pass/fail coloring, aligned columns, per-gate timing dimmed), frob sys audit (PROVED green, GAP red, view sections), frob ticket list/doable (state-colored ids), frob vet reports (severity coloring), frob stats. HARD CONSTRAINT: non-TTY output must remain byte-stable plain text -- agents, CI, and this repo's own snapshot tests parse it; add tests locking both modes (force-color golden and plain golden) so pretty mode can never leak ANSI into piped output. No new heavyweight dependency without written justification (prefer hand-rolled ANSI via the existing color module over adding rich).
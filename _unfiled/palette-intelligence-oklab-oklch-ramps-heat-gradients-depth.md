+++
id = "01M1QDTV2BQKS72F3GA3T33TZ5"
title = "palette intelligence: OKLab/OKLCH ramps, heat gradients, depth shading, accessible pairs (A-027 item 4)"
type = "task"
category = "todo"
priority = "low"
points = 5
reporter = "human"
created = "2026-09-05T00:00:00Z"
updated = "2026-10-27T02:57:37Z"
aliases = ["crunk:T-0075"]
labels = ["v1-cluster:C1", "area:crunk", "component:crunk", "source:crunk", "imported:crunk"]
scope = ["src/crunk/**"]
+++

Recorded roadmap item from the adopting project's A-027 wishlist (docs/design/01-customer-requirements.md#roadmap-recorded-from-a-027-unscheduled----queued-tickets-exist). Unscheduled; needs its own design revision before work. Color-derivation items are bound to the OKLab/OKLCH constraint recorded there.

A-052 requirements (2026-09-06, from the engine tokens-JSON adoption): (1) palette completeness against a DECLARED base family (a base key naming a known family with a fixed hue set; missing hues warn at tokens time -- the shell shipped without Gruvbox blue/purple and the three-hue gradient silently could not be built); (2) named ramp exports support an assertable minimum hue-family span in OKLab. Both are OKLab hue-band work for this ticket's design revision.

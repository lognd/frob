+++
id = "01M38BCPEJMFJYSW8TG5YW9FSX"
title = "SEO119/SEO120: split scaled-content vs. doorway-page detectors"
type = "task"
category = "triage"
priority = "low"
reporter = "human"
created = "2026-09-24T00:00:00Z"
updated = "2026-10-04T21:01:23Z"
aliases = ["T-6610"]
labels = ["v1-cluster:B2", "area:crunk", "triage:accepted", "milestone:0.538.0"]
scope = ["src/frob/webapp/_seo_spam.py"]
+++

found while working T-5365: SEO116 implements one combined heuristic (route-generation call + large quoted-string array) covering both the scaled-content and doorway-page halves of the ticket body's single corpus item, leaving SEO119/SEO120 (2 of the reserved SEO113-120 8-id block) unused. Design and implement two distinct detectors: scaled-content (templated pages with near-duplicate body content) and doorway-page (multiple landing pages targeting near-identical search queries with only a location/keyword swap).

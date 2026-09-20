---
id: T-draft-17172ad2
title: 'SEO and WEBPERF: Google spam policies, per-page title/description/canonical/og/structured
  data, robots and sitemap and llms.txt, hreflang, favicon, Core Web Vitals causes,
  bundle budget, image and font loading, caching headers, CDN and compression, API
  payload and pagination, DB pooling and caching'
state: queued
kind: feature
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
38 entries here plus lint-authorities.md sections C and D. Keyword stuffing: the rule is NOT a density threshold; it fires on the Google spam-policy shape (repeated keyword lists, unnatural repetition, hidden text) and a companion advisory checks that the target keyword appears once each in title, slug, h1 and opening sentence, citing Google Search Central spam policies and title-link guidance. Static: framework default titles (Vite, React App, Next.js), duplicate titles/descriptions across routes, missing meta description, missing og:image/og:title, missing canonical, multiple or zero h1, missing lang, missing favicon, no robots.txt or one blocking Google-Extended/GPTBot without a decision record, no sitemap.xml, no llms.txt (advisory, community proposal), staging without noindex, source maps in prod, bundle over the configured budget (default cites web.dev), images without width/height (CLS), no loading=lazy on offscreen images, no srcset, fonts without font-display, render-blocking scripts without defer/async, no Cache-Control/immutable on hashed assets, no compression config, API list endpoints without pagination, DB access without pool config (PgBouncer/SQLAlchemy pool), no server cache layer for repeated expensive queries, undebounced input handlers and unbounded re-renders (React docs as authority). Lighthouse as an optional adapter in the tool registry for dynamic-only entries.
---
id: T-5147
title: 'SEO and WEBPERF: Google spam policies, per-page title/description/canonical/og/structured
  data, robots and sitemap and llms.txt, hreflang, favicon, Core Web Vitals causes,
  bundle budget, image and font loading, caching headers, CDN and compression, API
  payload and pagination, DB pooling and caching'
state: queued
kind: feature
origin: human
created: '2026-09-20'
priority: high
parent: T-5140
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
body_changes:
- mode: append
  reason: 'owner 2026-09-20: carry the research corpus in the ticket body, not only
    as an attachment'
  actor: logan
  at: '2026-09-20'
  old_length: 1408
  new_length: 26911
designated_repro_test: null
threat: null
component: gates
anchor: false
anchor_reason: null
land_commit: null
---
38 entries here plus lint-authorities.md sections C and D. Keyword stuffing: the rule is NOT a density threshold; it fires on the Google spam-policy shape (repeated keyword lists, unnatural repetition, hidden text) and a companion advisory checks that the target keyword appears once each in title, slug, h1 and opening sentence, citing Google Search Central spam policies and title-link guidance. Static: framework default titles (Vite, React App, Next.js), duplicate titles/descriptions across routes, missing meta description, missing og:image/og:title, missing canonical, multiple or zero h1, missing lang, missing favicon, no robots.txt or one blocking Google-Extended/GPTBot without a decision record, no sitemap.xml, no llms.txt (advisory, community proposal), staging without noindex, source maps in prod, bundle over the configured budget (default cites web.dev), images without width/height (CLS), no loading=lazy on offscreen images, no srcset, fonts without font-display, render-blocking scripts without defer/async, no Cache-Control/immutable on hashed assets, no compression config, API list endpoints without pagination, DB access without pool config (PgBouncer/SQLAlchemy pool), no server cache layer for repeated expensive queries, undebounced input handlers and unbounded re-renders (React docs as authority). Lighthouse as an optional adapter in the tool registry for dynamic-only entries.

# Remaining SEO, page-experience, and performance lint authorities

Fills gaps left in lint-authorities.md sections C and D. Sources: Google
Search Central spam-policies page (already fetched, re-grepped for the
remaining categories), Google's mobile-first-indexing page, MDN's <link>
reference, React/Vue performance docs, PgBouncer's own site, PostgreSQL
EXPLAIN/index-types docs, SQLAlchemy relationship-loading docs, and Rails
Active Record Querying guide.

### 1. Google spam policy -- site reputation abuse
Authority: Google Search Central, "Site reputation abuse policy"
URL: https://developers.google.com/search/docs/appearance/site-reputation-abuse
Quote: fetch succeeded (45.6KB) but the targeted grep for the operative definition sentence returned no match against the stripped text in this pass -- flagging as a partial gap; the well-documented policy (summarized on the parent spam-policies page) targets "third-party content published with little to no first-party oversight or involvement" hosted on a reputable domain to exploit its ranking signals (e.g., a coupon-site section hosted on a news domain).
Lint condition: CMS-content lint for a "sponsored content"/"partner content" section published under the main site's own path/subdomain with no `rel="sponsored"` on outbound links and no clear first-party editorial ownership.
Static: dynamic-only

### 2. Google spam policy -- expired domain abuse
Authority: Google Search Central, Spam Policies
URL: https://developers.google.com/search/docs/essentials/spam-policies
Quote: "Expired domain abuse is where an expired domain name is purchased and repurposed primarily to manipulate search rankings by hosting content that provides little to no value to users."
Lint condition: not code-lintable; domain-acquisition process check (not a static code check) for a newly acquired domain whose registration-history shows a prior unrelated owner and content topic.
Static: dynamic-only

### 3. Google spam policy -- link spam
Authority: Google Search Central, Spam Policies
URL: https://developers.google.com/search/docs/essentials/spam-policies
Quote: "Link spam is the practice of creating links to or from a site primarily for the purpose of manipulating search rankings. The following are examples of link spam: Buying or selling links for ranking purposes."
Lint condition: outbound-link content lint for a "partners"/"resources" page consisting of a large list of unrelated external links with commercial anchor text and no `rel="sponsored"`/`rel="nofollow"`.
Static: yes

### 4. Google spam policy -- thin affiliation
Authority: Google Search Central, Spam Policies (page summary confirms "thin affiliation" as a named prohibited category, full definition text not independently isolated this pass -- flagging as a partial gap)
URL: https://developers.google.com/search/docs/essentials/spam-policies
Quote: page's own AI-generated summary: "Additionally, scraping, site reputation abuse, sneaky redirects, thin affiliation, and user-generated spam are prohibited."
Lint condition: content lint for a page consisting mostly of syndicated/manufacturer product descriptions with no original review content, comparison, or editorial value-add.
Static: dynamic-only

### 5. Google spam policy -- sneaky redirects
Authority: Google Search Central, Spam Policies
URL: https://developers.google.com/search/docs/essentials/spam-policies
Quote: "Sneaky redirecting is the practice of doing this maliciously in order to either show users and search engines different content or show users unexpected content that doesn't fulfill their original needs. Examples ... Showing desktop users a normal page while redirecting mobile users to a completely different spam domain."
Lint condition: server-side redirect-logic lint for a `User-Agent`-conditional or device-conditional redirect rule sending crawlers and users to different final destinations.
Static: yes

### 6. Google spam policy -- scraped content
Authority: Google Search Central, Spam Policies
URL: https://developers.google.com/search/docs/essentials/spam-policies
Quote: "Scraping refers to the practice of taking content from other sites, often through automated means, and hosting it with the purpose of manipulating search rankings. Examples ... Republishing content from other sites without adding any original content or value, or even citing the original source."
Lint condition: content-similarity lint (build-time job) comparing new CMS entries against a corpus of known external sources, flagging near-duplicate text with no citation/canonical link back to the source.
Static: dynamic-only

### 7. Google spam policy -- malware
Authority: Google Search Central, Spam Policies
URL: https://developers.google.com/search/docs/essentials/spam-policies
Quote: "Malware is any software ... [that] exhibits malicious behavior that can include installing software without user consent"; the page also references "Prevent a malware infection" and Google Safe Browsing as the enforcement mechanism.
Lint condition: dependency/third-party-script lint for an embedded ad-network or widget script flagged by Google Safe Browsing's Transparency Report API, or for a downloadable file served from the site with no virus/malware scan step in the upload pipeline.
Static: dynamic-only

### 8. Google spam policy -- misleading functionality
Authority: Google Search Central, Spam Policies
URL: https://developers.google.com/search/docs/essentials/spam-policies
Quote: "Misleading functionality refers to the practice of intentionally creating sites that trick users into thinking they would be able to access some content or services but in reality can't. Examples ... A site with a fake generator that claims to provide app store credit but doesn't actually provide the credit."
Lint condition: not code-lintable in general; the closest static proxy is a content lint for marketing copy promising a specific automated function (generator, calculator, converter) with no corresponding backend implementation reachable from that page.
Static: dynamic-only

### 9. E-E-A-T checkable signals -- author, dates, contact page
Authority: Google Search Central's "creating helpful, reliable, people-first content" guidance (cross-referenced from lint-authorities.md item C6; the specific E-E-A-T author/date signals were not re-fetched from a dedicated URL this pass)
URL: https://developers.google.com/search/docs/essentials/spam-policies (parent nav links to the E-E-A-T guidance, not separately re-fetched)
Quote: BLOCKED for a verbatim quote of the E-E-A-T-specific page this pass; Google's well-documented public guidance recommends visible author bylines with credentials, a "last updated"/"published" date, and a reachable contact/about page as trust signals for content quality.
Lint condition: template lint for an article/blog-post template with no author byline field, no `datePublished`/`dateModified` (matching schema.org `Article`), and no site-wide contact page linked in the footer.
Static: yes

### 10. Mobile viewport meta tag
Authority: Google Search Central, mobile-first indexing documentation
URL: https://developers.google.com/search/docs/crawling-indexing/mobile/mobile-sites-mobile-first-indexing
Quote: fetch succeeded (207KB) but the targeted grep for the viewport-meta guidance sentence returned no match in this pass -- flagging as a partial gap; Google's well-documented recommendation is that every page include `<meta name="viewport" content="width=device-width, initial-scale=1">` for correct mobile rendering under mobile-first indexing.
Lint condition: `<head>` lint for a missing `<meta name="viewport">` tag, or one with a fixed `width=` value instead of `device-width`.
Static: yes

### 11. HTTPS as a baseline requirement
Authority: cross-reference lint-authorities.md item A15/D-series TLS requirements; Google has publicly documented HTTPS as a (lightweight) ranking signal since 2014 (not independently re-fetched a dedicated URL this pass)
URL: https://developers.google.com/search/docs/crawling-indexing/mobile/mobile-sites-mobile-first-indexing (adjacent guidance, not the primary HTTPS-signal source)
Quote: BLOCKED for a verbatim quote of the original 2014 HTTPS-signal announcement this pass.
Lint condition: crawl/response lint for any indexable page reachable over plain `http://` with no redirect to `https://`.
Static: yes

### 12. hreflang for internationalized sites
Authority: Google Search Central hreflang documentation (not independently re-fetched a dedicated URL this pass -- BLOCKED for a verbatim quote); cross-reference the canonical-link authority already in lint-authorities.md item C13, same `<link>` mechanism family per MDN's `<link>` reference.
URL: https://developer.mozilla.org/en-US/docs/Web/HTML/Element/link
Quote: MDN's `<link>` reference documents `rel="alternate"` with `hreflang` as the mechanism for "specifying alternate versions of a document in different languages."
Lint condition: `<head>` lint for a site with multiple locale subpaths/subdomains where a page has no `<link rel="alternate" hreflang="...">` set referencing its sibling-locale pages.
Static: yes

### 13. Pagination rel=next/prev (deprecated but still checked by some crawlers)
Authority: MDN `<link>` reference (`rel="next"`/`rel="prev"` historical usage, now officially deprecated by Google for search but still meaningful for accessibility/other crawlers)
URL: https://developer.mozilla.org/en-US/docs/Web/HTML/Element/link
Quote: MDN documents `rel="next"`/`rel="prev"` as link types indicating "the next/previous document in a series."
Lint condition: paginated-listing template lint for a series of `/page/2`, `/page/3` URLs with no `rel="next"`/`rel="prev"` link relations and no canonical strategy (e.g., view-all page) declared.
Static: yes

### 14. noindex accidentally left on/off staging vs production
Authority: general robots meta-tag mechanism (HTML `<meta name="robots" content="noindex">`), cross-referenced from the robots.txt item in lint-authorities.md item C9
URL: not independently re-fetched a dedicated primary-source URL for the `robots` meta tag this pass -- BLOCKED for a verbatim quote; well-documented WHATWG/Google-supported mechanism.
Lint condition: environment-config lint (CI check) that fails the build if a production deploy is missing `<meta name="robots" content="index,follow">` (or has no such tag with server defaults ambiguous), and fails if a staging/preview deploy is missing `<meta name="robots" content="noindex,nofollow">` or a global `X-Robots-Tag: noindex` header.
Static: config

### 15. Redirect chains
Authority: general crawl-efficiency guidance (Google Search Central has publicly documented recommending "avoid chains of redirects" -- not independently re-fetched a dedicated URL this pass, BLOCKED for a verbatim quote)
URL: not independently re-fetched this pass.
Lint condition: link-checker/crawl-audit lint (CI job hitting the sitemap URLs) flagging any URL that resolves through more than one 3xx redirect hop before reaching a 200 response.
Static: config

### 16. 4xx/5xx errors on indexed/linked URLs
Authority: same crawl-efficiency framing as item 15
URL: not independently re-fetched this pass -- BLOCKED for a verbatim quote.
Lint condition: same crawl-audit job as item 15, flagging any URL present in the sitemap or internal link graph that returns a 4xx/5xx status.
Static: config

### 17. Duplicate content without canonical
Authority: cross-reference lint-authorities.md item C13 (RFC 6596 canonical link relation)
URL: https://www.rfc-editor.org/rfc/rfc6596
Quote: same quote as item C13 -- "The canonical link relation are to specify the preferred version of an [IRI]."
Lint condition: same as C13's lint condition, extended here to flag pages with near-identical rendered content (e.g., print view, AMP variant, filtered-list permutations) sharing no `rel="canonical"` back to one preferred URL.
Static: yes

### 18. Image dimensions specified (CLS prevention)
Authority: cross-reference web.dev Core Web Vitals CLS threshold (lint-authorities.md item D1); the specific "always include width/height" guidance is documented on web.dev's own CLS optimization guide, not independently re-fetched a dedicated URL this pass -- BLOCKED for a verbatim quote here.
URL: https://web.dev/articles/vitals (parent CWV page already fetched; the dedicated CLS-optimization sub-page was not separately re-fetched this pass)
Quote: BLOCKED for a verbatim quote this pass; the well-documented recommendation is that every `<img>`/`<video>` element declare explicit `width` and `height` attributes (or an `aspect-ratio` CSS property) so the browser can reserve layout space before the asset loads.
Lint condition: template lint for an `<img>` element with no `width`/`height` attributes and no CSS `aspect-ratio` set on it or its container.
Static: yes

### 19. srcset/sizes for responsive images
Authority: MDN `<link>`/responsive-images documentation family (the specific `srcset` reference was not independently re-fetched this pass -- BLOCKED for a verbatim quote); well-documented HTML feature.
URL: not independently re-fetched a dedicated `srcset` MDN page this pass.
Lint condition: template lint for a large hero/content `<img>` with a single fixed-resolution `src` and no `srcset`/`sizes` attributes, serving desktop-resolution images to mobile viewports.
Static: yes

### 20. font-display for web fonts
Authority: not independently re-fetched a dedicated CSS Fonts Module / web.dev font-display page this pass -- BLOCKED for a verbatim quote; well-documented CSS feature controlling FOIT/FOUT behavior.
URL: not independently re-fetched this pass.
Lint condition: `@font-face` CSS-rule lint for a custom web-font declaration with no `font-display: swap` (or `optional`) property, which risks invisible text during font load (FOIT) and hurts LCP.
Static: yes

### 21. preconnect/preload for critical resources
Authority: MDN `<link>` reference, `rel="preconnect"`/`rel="preload"`
URL: https://developer.mozilla.org/en-US/docs/Web/HTML/Element/link
Quote: MDN documents `rel="preload"` as instructing the browser "to preemptively fetch and cache" a resource, and `rel="preconnect"` as instructing it to establish an early connection to a given origin.
Lint condition: `<head>` lint for a page whose LCP element (hero image, custom font) is loaded from a third-party origin with no matching `<link rel="preconnect">`/`<link rel="preload">` for that resource.
Static: yes

### 22. Third-party script weight budget
Authority: cross-reference Lighthouse's `third-party-summary`/`unused-javascript` audits (lint-authorities.md item D2's audit-catalog citation, same access gap flagged there)
URL: https://web.dev/articles/vitals
Quote: same partial-gap note as item D2 -- the audit categories are well-documented Lighthouse features, not re-extracted verbatim this pass.
Lint condition: CI Lighthouse-budget config asserting a maximum total transferred-byte size (a specific number, e.g., 300KB, must be set by the project and stored in the budget config file, not invented here) attributable to third-party scripts (analytics, ad tech, chat widgets).
Static: config

### 23. HTTP/2 or HTTP/3 and Brotli compression
Authority: cross-reference RFC 9110/9111 (lint-authorities.md items D3-D4); Brotli itself is documented in RFC 7932 (not independently re-fetched this pass -- BLOCKED for a verbatim quote)
URL: https://www.rfc-editor.org/rfc/rfc9110 ; https://www.rfc-editor.org/rfc/rfc9111
Quote: same Accept-Encoding/content-negotiation text already cited in lint-authorities.md item D4.
Lint condition: server/CDN config lint for a listener still serving HTTP/1.1 only (no ALPN `h2`/`h3` negotiated), and for a compression middleware configured with only `gzip` and no `br` (Brotli) encoding offered when the client's `Accept-Encoding` includes it.
Static: config

### 24. ETag / immutable caching for hashed assets
Authority: cross-reference RFC 9111 Cache-Control (lint-authorities.md item D3); RFC 9110 defines the `ETag` validator header (same RFC already fetched, section not independently re-quoted for ETag specifically this pass)
URL: https://www.rfc-editor.org/rfc/rfc9111 ; https://www.rfc-editor.org/rfc/rfc9110
Quote: same Cache-Control directive text cited in lint-authorities.md item D3, extended here to the `immutable` extension directive for content-hashed filenames.
Lint condition: static-asset server config lint for a build-hashed filename (`app.a1b2c3.js`) served without `Cache-Control: max-age=31536000, immutable`, forcing unnecessary revalidation requests.
Static: config

### 25. Service worker / PWA manifest
Authority: not independently re-fetched a dedicated W3C Service Workers / Web App Manifest spec URL this pass -- BLOCKED for a verbatim quote; both are well-documented W3C specifications.
URL: not independently re-fetched this pass.
Lint condition: build-output lint for a project claiming PWA/installable status with no `manifest.json` linked via `<link rel="manifest">` and no registered service worker script.
Static: yes

### 26. JS bundle size budget
Authority: cross-reference Lighthouse performance-budget feature (same access-gap note as item 22); the specific numeric budget is a project-level decision, not a universal standard -- flagging that any specific KB number must come from the project's own `budget.json`, not from this authority list.
URL: https://web.dev/articles/vitals
Quote: same partial-gap note as item 22.
Lint condition: CI bundle-analyzer lint (webpack-bundle-analyzer, source-map-explorer) asserting the initial JS payload stays under the project's own documented budget (this file cannot assert a specific number without a project-level budget doc as its source).
Static: config

### 27. Unused CSS
Authority: cross-reference Lighthouse `unused-css-rules` audit (same access-gap note as item 22)
URL: https://web.dev/articles/vitals
Quote: same partial-gap note as item 22.
Lint condition: CI coverage-tool lint (e.g., Chrome DevTools Coverage API run headlessly, or PurgeCSS in check-mode) flagging a CSS bundle where a large percentage of selectors never match any rendered page.
Static: config

### 28. Render-blocking resources
Authority: cross-reference Lighthouse `render-blocking-resources` audit (lint-authorities.md item D2) and item D7 (defer/async)
URL: https://web.dev/articles/vitals ; https://html.spec.whatwg.org/multipage/scripting.html#attr-script-defer
Quote: same partial-gap note as item D2/D7.
Lint condition: same as lint-authorities.md item D7, plus a `<head>` lint for a synchronous `<link rel="stylesheet">` to a large non-critical CSS file with no `media` attribute or async-loading pattern (`rel="preload" as="style" onload="this.rel='stylesheet'"`).
Static: yes

### 29. Time to First Byte (TTFB) target
Authority: cross-reference web.dev's Core Web Vitals family; TTFB is documented by web.dev as a supporting metric (threshold recommendation ~0.8s "good") on a page not independently re-fetched separately from the Vitals overview this pass -- BLOCKED for a verbatim quote of the TTFB-specific threshold text.
URL: https://web.dev/articles/vitals
Quote: BLOCKED for a verbatim quote this pass.
Lint condition: server-side APM/monitoring config check (not purely static) for no alerting threshold configured on TTFB/server-response-time metrics.
Static: dynamic-only

### 30. INP causes -- long tasks and undebounced handlers (React)
Authority: React documentation, `useTransition`/concurrent-rendering guidance
URL: https://react.dev/reference/react/useTransition
Quote: fetch succeeded (485KB) but the targeted grep for a "debounce" sentence returned no match in this pass -- flagging as a partial gap; React's own docs for `useTransition` document its purpose as marking state updates as "non-blocking" so that "urgent updates like text input" are not delayed by expensive re-renders, directly addressing INP-class long-task jank.
Lint condition: code lint for an `onChange`/`onInput` handler performing expensive synchronous work (unfiltered array re-render, heavy computation) with no `useTransition`/`useDeferredValue` wrapping and no debounce/throttle utility applied.
Static: yes

### 31. INP causes -- unbounded re-renders (Vue)
Authority: Vue.js documentation, "Performance" guide
URL: https://vuejs.org/guide/best-practices/performance.html
Quote: fetch succeeded (117.7KB); Vue's own performance guide documents `v-memo`, computed-property memoization, and virtualization as the standard mitigations for large-list re-render cost (exact sentence not re-quoted verbatim in this pass -- flagging as a partial gap).
Lint condition: template lint for a `v-for` loop rendering a large list with no `:key` binding (forcing full re-render on reorder) and no virtualization library for lists above a documented row-count threshold.
Static: yes

### 32. API payload compression and pagination (cross-ref)
Authority: cross-reference lint-authorities.md item D4 (RFC 9110 Accept-Encoding) and this file's item 14 (API-level pagination, lint-appsec-authz-business-llm.md item 14)
URL: https://www.rfc-editor.org/rfc/rfc9110
Quote: same as lint-authorities.md item D4.
Lint condition: API-response middleware lint for a JSON API with no compression middleware and no page-size cap on collection endpoints (duplicate of lint-appsec-authz-business-llm.md item 14, cross-referenced rather than restated in full).
Static: yes

### 33. Database indexing of FK and WHERE/ORDER columns (cross-ref)
Authority: cross-reference lint-authorities.md item F2 (Postgres FK indexing) and lint-sql-full.md's dedicated index-column entries.
URL: https://www.postgresql.org/docs/current/ddl-constraints.html
Quote: same as lint-authorities.md item F2.
Lint condition: see lint-sql-full.md for the full WHERE/ORDER/JOIN-column indexing entries; cross-referenced here rather than duplicated.
Static: yes

### 34. Connection pooling (PgBouncer)
Authority: PgBouncer project documentation
URL: https://www.pgbouncer.org/
Quote: fetch succeeded (8KB) but the page is primarily a news/download index; PgBouncer's own self-description (site tagline) confirms it as "Lightweight connection pooler for PostgreSQL" -- the specific pooling-mode configuration guidance (`transaction` vs `session` pooling) was not independently re-fetched from a dedicated config-doc URL this pass, flagging as a partial gap.
Lint condition: infra config lint for a web application connecting directly to Postgres with no connection pooler (PgBouncer, RDS Proxy, Supabase's built-in pooler) in front of it, risking connection exhaustion under load, especially from serverless/Lambda-style short-lived-process deployments.
Static: config

### 35. Server-side and CDN caching
Authority: cross-reference RFC 9111 (lint-authorities.md item D3), applied at the origin/application-cache layer rather than only the browser
URL: https://www.rfc-editor.org/rfc/rfc9111
Quote: same Cache-Control directive definitions cited in lint-authorities.md item D3.
Lint condition: infra config lint for a read-heavy, rarely-changing API endpoint (product catalog, published-content list) with no CDN edge-cache rule or application-layer cache (Redis/Memcached) in front of the database query.
Static: config

### 36. N+1 query pattern from ORM lazy loading (SQLAlchemy)
Authority: SQLAlchemy ORM documentation, Relationship Loading Techniques
URL: https://docs.sqlalchemy.org/en/20/orm/queryguide/relationships.html
Quote: "the 'N plus one' problem, which states that for any N objects loaded, iterating through each of their [lazy-loaded relationships] emits an additional 'N+1 SELECT'" -- confirmed via extraction of "N plus one problem" and "N+1 SELECT" strings in the fetched page text.
Lint condition: code lint for an iteration (`for obj in query_result: obj.related_field`) accessing a lazily-loaded relationship attribute inside a loop with no `joinedload`/`selectinload`/`.options()` eager-loading strategy applied to the originating query.
Static: yes

### 37. N+1 query pattern from ORM lazy loading (Rails/ActiveRecord)
Authority: Ruby on Rails Guides, Active Record Query Interface, `includes`
URL: https://guides.rubyonrails.org/active_record_querying.html
Quote: fetch succeeded (336KB) and confirmed the `includes` method as the documented eager-loading mechanism (exact N+1-specific sentence not re-isolated in this pass, flagging as a partial gap); Rails' own guide documents `Model.includes(:association)` as the fix for "referencing an association" in a loop causing "an extra query be executed for each item."
Lint condition: same class of code lint as item 36 -- an ActiveRecord query followed by a view/controller loop calling `.association` on each record with no `.includes(:association)`/`.eager_load(:association)` on the originating `where`/`find` call.
Static: yes

### 38. N+1 query pattern (Django/Prisma, cross-ref by class)
Authority: same ORM-lazy-loading class as items 36-37; Django's `select_related`/`prefetch_related` and Prisma's `include`/`select` serve the identical documented purpose (not independently re-fetched dedicated URLs for these two frameworks this pass -- flagging as a gap).
URL: not independently re-fetched this pass for Django/Prisma specifically.
Lint condition: same lint class as items 36-37, applied to Django (`.select_related()`/`.prefetch_related()` missing before a related-field loop) and Prisma (`findMany()` with no `include`/`select` before a related-record access loop).
Static: yes

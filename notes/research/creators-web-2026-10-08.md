# creators-web: practitioner corpus for lint evidence (front-end engineering: React, TypeScript, CSS architecture, accessibility implementation, performance, state and data, forms, client-side testing, client-side security)

Date 2026-10-08. Agent creators-web, Strand B of lint-evidence-study.md. Research only; no repository modified (the consumer project was read, not changed). ASCII only. Model: creators-systems-2026-10-08.md and creators-games-2026-10-08.md (vetting weights PASS 1.0, PASS-W 0.5 never sole support, FAIL 0, unvetted 0; one voice per person per item; stance relabelled against a rule statement). Visual-design taste and AI-slop tells are out of scope (deslop-research-2026-10-08.md).

## 0. Honesty block

- Candidates vetted: 68 people (55 PASS, 11 PASS-W, 2 FAIL) plus 36 organisational voices that supplied items (team docs, standards bodies, style guides; they count as one voice each, weight 1.0, because the organisation is the maintainer of the software or standard). Every person on the owner's list passed or passed with weight 0.5 once evidence was found; the two FAILs are bylines I could not verify (a co-author and a guest), so the gate again excluded almost nobody famous and works as a weighting device, not a filter. Evidence is GitHub contributor rank and commit counts fetched this session (gh api, top 500 contributors per repository) and the person's own about page where one was reachable. 11 vetted people supplied no item (checked but not used).
- Sources: 1302 written units fetched (1053 prose pages, 249 rule-catalogue pages). Processed: 314 prose pages (305 read by three Sonnet extractor sub-agents, 9 read by me) and 249 rule-catalogue pages handled by a script that takes the rule id, its one-line description and its When-Not-To-Use-It section (no model reading). Extractor status: {'full': 249, 'irrelevant': 12, 'skimmed': 35, 'mismatch': 9}. About 739 fetched prose pages were NOT processed (reserve; mostly further WCAG Understanding pages, MDN reference pages, web.dev and Lighthouse pages and personal-blog archives); none of their content is used. Evidence marked 'via search' was read in a WebSearch result page, not opened (used only to find URLs).
- Talks: none. YouTube was reported as blocking transcript requests from this machine; I made no transcript or video request of any kind and did not try to get round the block. Every claim below rests on a written source: official docs (react.dev incl. You Might Not Need an Effect and the Rules of React lints, TypeScript handbook and wiki, typescript-eslint, MDN, web.dev, WCAG 2.2 Understanding pages, ARIA Authoring Practices, OWASP cheat sheets), maintainers' blogs, framework docs, and rule documentation of ESLint, typescript-eslint, eslint-plugin-react, jsx-a11y, react-hooks, testing-library, jest, import, unicorn, stylelint, tailwindcss and TanStack Query plugins. Conference talks by the named people (Abramov, Florence, Jackson, Harris, Archibald, Surma and others) are therefore NOT represented; where a person's view appears it comes from their blog or docs.
- Items: 1981 raw atomic advice items (1732 extracted from prose pages, 249 derived from rule-catalogue pages). Extraction was done by Sonnet sub-agents under a fixed brief (BRIEF.md in the scratch area), once, with no second extractor; I read 9 pages myself (22 items) and spot-read about 60 item lines in context but did not re-verify items against their sources. 854 free-form slugs were merged into 403 canonical rules by a Sonnet pass (each with a flag-polarity rule statement, tier and lintability); 233 canonical rules have two or more distinct voices and 130 have three or more.
- Stance: extractor stance labels were unreliable (paraphrases mix 'do X' and 'do not X' polarity), so every item in a multi-voice canonical rule (1707 items) was relabelled against the rule statement by a Sonnet pass: F (source says the flagged thing is a mistake) 1084, O (source says it is fine or opposes enforcing it) 19, C (only under a condition) 110, X (does not bear on the statement; excluded) 494. One labeller, no second labeller, so no kappa. Single-voice rules keep F, or C if the extractor said conditional. Opposition (O) is rare, 19 items: the corpus is mostly guidance from maintainers who agree; genuine disagreement is mostly carried by C items and by items that disagree within one source family.
- Weights: PASS 1.0, PASS-W 0.5 (never sole support), unvetted 0. A voice is counted once per rule per label; team documentation of one organisation (React docs, React 18 working group posts, react.dev lint pages, legacy docs; Chrome web.dev and Lighthouse; W3C WAI, WCAG and APG; Remix and React Router; Redux with Mark Erikson) is one voice. Individuals employed by an organisation (Walton, Archibald, Surma, Osmani, Rachel Andrew at Google) are separate voices from that organisation's docs, so agreement between them and web.dev is partly one source cited several times. The HTTP Archive Web Almanac and WebAIM Million count as voices but are descriptive data (what fails on real sites), not advice.
- Coverage bias: tax codes {'WEB.A11Y': 451, 'WEB.CSS': 177, 'WEB.SEC': 162, 'WEB.TEST': 161, 'WEB.PERF': 153, 'WEB.TS': 145, 'WEB.STATE': 128, 'WEB.FORMS': 99}. Accessibility is 23 percent of all items because accessibility implementation has the most written, citable practice and I assigned 105 sources to it. Evidence types: {'authority': 931, 'argument': 498, 'convention': 370, 'data': 100, 'war_story': 82}; only 100 items cite data (mainly HTTP Archive, WebAIM Million, Lighthouse thresholds), so most 'consensus' is shared expert opinion. Vue, Svelte and Solid sources are present but thin; no CSS-in-JS or Angular coverage; no state of the art for React Server Components security beyond the Next.js, React and OWASP pages fetched.
- frob-v2 coverage: by grep of docs/design (crunk.md, language-engines.md, rules.md, neatness.md, boundaries.md), the crunk-design research note (E3 proposed ids), the titles and bodies of the WEBSEC, A11Y, WEBPERF, SEO and LAUNCH tickets, and crates/ for rule ids present as literals. Implemented in crates: COLOR001 (crunk-check); NEAT001, NEAT002, NEAT013, NEAT031, CYCLE001, TODO001, TODO002 as literals. The crunk-spec catalog registers more ids (BP001-003, COLOR002, CONTRAST001, LAYER001, ORG001-005, RADIUS001, SIZE001, SPACE001, TW001-005, TYPE001-003, TOKENS001) but crunk-check holds only the COLOR001 rule file. Every WEBSEC/A11Y/WEBPERF/SEO id is a ticketed design, not code. ESLint coverage is claimed only where I fetched the rule's own doc (the 'verified' rules); rule ids that extractors merely mentioned are marked '?'. 'Verified' means the rule exists with that doc; I did not check that it covers the whole canonical statement (for example jsx-a11y/aria-role is listed against aria-label-misuse only because an extractor tied them, so treat partial overlaps as bind-and-extend, not as full coverage).
- Not done: no detector was built or run; no ESLint run on the consumer (its config and sources were read); no repository mining (Strand A). Tier labels are cheapest-tier judgements by the helper, not measured precision.

## 1. Credibility gate (step 1)

Criteria as in the sibling reports: PASS = shipped or maintained real software of non-trivial size plus depth (widely used libraries, spec editing, books, major team role); PASS-W = one criterion thin or unverifiable here (weight 0.5); FAIL = no verifiable work or identity found by this check. Logan Smith is covered in creators-systems and not re-vetted here (no front-end material).

### 1.1 People

| # | Person | Domain | Verdict | Voice id (items/sources used) | Evidence (fetched this session) | Why |
|---|---|---|---|---|---|---|
| 1 | Dan Abramov | React core, state/effects | PASS | abramov (34/7) | https://github.com/facebook/react (250924 stars, 1688 commits, rank 3); https://github.com/reduxjs/redux (1057, rank 1); https://github.com/facebook/create-react-app (655, rank 1); https://github.com/reactjs/react.dev (934, rank 1) | React core team; Redux and CRA author. |
| 2 | Kent C. Dodds | React testing and patterns | PASS | dodds (60/9) | https://github.com/testing-library/react-testing-library (19663 stars, 29 commits, rank 3; creator); https://github.com/kentcdodds/kentcdodds.com (2513 commits, rank 1); https://github.com/remix-run/remix (123, rank 13) | Created Testing Library; ships a large production site. |
| 3 | Ryan Florence | routing, data, forms (Remix/React Router) | PASS | remix-rr (59/13) | https://github.com/remix-run/react-router (56602 stars, 1284 commits, rank 3); https://github.com/remix-run/remix (547, rank 4); https://github.com/reach/reach-ui (169, rank 2) | Co-creator of React Router and Remix. |
| 4 | Michael Jackson | routing (Remix/React Router) | PASS | remix-rr (59/13) | https://github.com/remix-run/react-router (1955 commits, rank 2); https://github.com/remix-run/remix (33397 stars, 2500, rank 1); https://github.com/unpkg/unpkg (819, rank 1) | Co-creator of React Router, Remix, unpkg. |
| 5 | Sophie Alpert | React core | PASS | alpert (7/4) | https://github.com/facebook/react (1300 commits, rank 5); https://github.com/facebook/react-devtools (58, rank 5) | React core engineer; former Khan Academy. |
| 6 | Andrew Clark | React core (Fiber, concurrent) | PASS | none used | https://github.com/facebook/react (1427 commits, rank 4); https://github.com/acdlite/recompose (14756 stars, 330, rank 1) | React core; Fiber architecture author. |
| 7 | Sebastian Markbage | React architecture | PASS | markbage (3/1) | https://github.com/facebook/react (1939 commits, rank 1) | React architect. |
| 8 | Brian Vaughn | React DevTools, virtualization | PASS | vaughn (12/2) | https://github.com/facebook/react (366 commits, rank 13); https://github.com/bvaughn/react-virtualized (27072 stars, 1105, rank 1); https://github.com/bvaughn/react-window (213, rank 1); https://github.com/bvaughn/react-error-boundary (132, rank 1) | React core; DevTools profiler. |
| 9 | Joe Savona | React Compiler | PASS | react-team (111/33) | https://github.com/facebook/react (1165 commits, rank 6); https://github.com/facebook/relay (556, rank 5) | Compiler lead (no personal items; React team voice). |
| 10 | Lauren Tan | React Compiler | PASS | react-team (111/33) | https://github.com/facebook/react (819 commits, rank 7) | Compiler engineer (no personal items). |
| 11 | Mark Erikson | Redux, React rendering | PASS | erikson (65/9) | https://github.com/reduxjs/redux (835 commits, rank 2); https://github.com/reduxjs/redux-toolkit (1457, rank 1); https://github.com/reduxjs/react-redux (436, rank 1) | Redux maintainer. |
| 12 | Tanner Linsley | data fetching, tables, routing | PASS | tanstack (19/11) | https://github.com/TanStack/query (50407 stars, 1343 commits, rank 1); https://github.com/TanStack/table (1528, rank 1); https://github.com/TanStack/router (3272, rank 1) | TanStack author. |
| 13 | Dominik Dorfmeister | TanStack Query | PASS | dorfmeister (48/9) | https://github.com/TanStack/query (444 commits, rank 3); https://github.com/TanStack/router (25, rank 14) | TanStack Query maintainer. |
| 14 | Matt Pocock | TypeScript | PASS-W | pocock (31/9) | https://github.com/mattpocock/ts-reset (8616 stars, 142 commits, rank 1); https://github.com/statelyai/xstate (30265 stars, 200, rank 4) | Shipped libraries, but his main output is courses and articles; weight 0.5. |
| 15 | Anders Hejlsberg | TypeScript language | PASS | ts-team (43/7) | https://github.com/microsoft/TypeScript (111393 stars, 4120 commits, rank 1) | Language lead; read through the TypeScript team docs. |
| 16 | Daniel Rosenwasser | TypeScript | PASS | ts-team (43/7) | https://github.com/microsoft/TypeScript (2411 commits, rank 3) | TypeScript PM; docs voice. |
| 17 | Josh Goldberg | typescript-eslint | PASS | tseslint (87/65) | https://github.com/typescript-eslint/typescript-eslint (16412 stars, 682 commits, rank 2) | Maintainer; rule docs voice. |
| 18 | Brad Zacher | typescript-eslint | PASS | tseslint (87/65) | https://github.com/typescript-eslint/typescript-eslint (590 commits, rank 3) | Maintainer; rule docs voice. |
| 19 | Nicholas Zakas | ESLint, maintainable JavaScript | PASS | zakas-eslint (33/33) | https://github.com/eslint/eslint (27624 stars, 2552 commits, rank 1); https://github.com/eslint/espree (300, rank 1); https://github.com/CSSLint/csslint (83, rank 2) | Created ESLint and CSS Lint. |
| 20 | Jordan Harband | JS style and lint plugins | PASS | eslint-react-a11y (66/66) | https://github.com/airbnb/javascript (148294 stars, 672 commits, rank 1); https://github.com/jsx-eslint/eslint-plugin-react (953, rank 1); https://github.com/jsx-eslint/eslint-plugin-jsx-a11y (199, rank 2); https://github.com/tc39/ecma262 (208, rank 7) | Maintainer of the rule catalogues used here. |
| 21 | Sindre Sorhus | JS lint, tooling | PASS | sorhus (7/7) | https://github.com/sindresorhus/eslint-plugin-unicorn (1165 commits, rank 1); https://github.com/xojs/xo (483, rank 1) | Maintains unicorn and xo. |
| 22 | Evan You | Vue, Vite | PASS | vue-vite (70/8) | https://github.com/vuejs/core (54587 stars, 3576 commits, rank 1); https://github.com/vitejs/vite (83254 stars, 1922, rank 1); https://github.com/vuejs/vue (212810 stars, 2583, rank 1) | Creator of Vue and Vite. |
| 23 | Anthony Fu | Vite, Vitest, ESLint config | PASS | vitest (13/3) | https://github.com/vitest-dev/vitest (1093 commits, rank 2); https://github.com/antfu/eslint-config (1074, rank 1) | Vitest co-creator (no personal items). |
| 24 | Rich Harris | Svelte, reactivity | PASS | svelte (54/8) | https://github.com/sveltejs/svelte (88358 stars, 5250 commits, rank 1); https://github.com/sveltejs/kit (1577, rank 1); https://github.com/rollup/rollup (1555, rank 2) | Creator of Svelte and Rollup. |
| 25 | Ryan Carniato | fine-grained reactivity | PASS | solid (11/3) | https://github.com/solidjs/solid (36102 stars, 1480 commits, rank 1); https://github.com/solidjs/solid-start (901, rank 1) | Creator of Solid. |
| 26 | Addy Osmani | web performance, patterns | PASS | osmani (45/7) | https://github.com/tastejs/todomvc (28957 stars, 325 commits, rank 3); https://github.com/yeoman/yeoman (299, rank 1); https://github.com/GoogleChrome/lighthouse (8, rank 31) | Yeoman and TodoMVC; Chrome engineering lead (employer unsourced here). |
| 27 | Alex Russell | web performance, platform | PASS | russell (7/2) | https://github.com/w3c/ServiceWorker (188 commits, rank 3); https://github.com/slightlyoff/cassowary.js (510, rank 1) | Service Worker co-author. |
| 28 | Harry Roberts | CSS architecture, performance | PASS | roberts (28/8) | https://github.com/inuitcss/inuitcss (225 commits, rank 1); https://github.com/csswizardry/CSS-Guidelines (68, rank 1) | Framework author; performance consultant. |
| 29 | Jake Archibald | web platform, performance | PASS | archibald (10/3) | https://github.com/jakearchibald/idb (7418 stars, 157 commits, rank 1); https://github.com/GoogleChromeLabs/squoosh (210, rank 2); https://github.com/w3c/ServiceWorker (254, rank 2); https://github.com/jakearchibald/svgomg (258, rank 1) | Library and spec author. |
| 30 | Surma | workers, performance | PASS | surma (15/3) | https://github.com/GoogleChromeLabs/comlink (12802 stars, 602 commits, rank 1); https://github.com/GoogleChromeLabs/squoosh (26001 stars, 594, rank 1); https://github.com/GoogleChromeLabs/proxx (337, rank 1) | Comlink and Squoosh author. |
| 31 | Philip Walton | web vitals, CSS architecture | PASS | walton (13/4) | https://github.com/GoogleChrome/web-vitals (8639 stars, 335 commits, rank 1); https://github.com/philipwalton/solved-by-flexbox (12907 stars); https://github.com/philipwalton/html-inspector (209, rank 1); https://philipwalton.com/about/ (engineer at Google, Chrome and Web Platform) | web-vitals library author. |
| 32 | Josh W. Comeau | CSS, React | PASS | comeau (9/2) | https://github.com/joshwcomeau/react-flip-move (4135 stars, 221 commits, rank 1); https://github.com/joshwcomeau/guppy (233, rank 1); https://github.com/joshwcomeau/use-sound (49, rank 1) | Library author; educator. |
| 33 | Sara Soueidan | inclusive UI, SVG, CSS | PASS-W | soueidan (27/5) | https://www.sarasoueidan.com/about/ (independent inclusive Web UI engineer, in the field since 2012, client list; no public repository matched under the names I tried) | Real client work but no verifiable code; weight 0.5. |
| 34 | Adrian Roselli | accessible patterns | PASS | roselli (35/5) | https://adrianroselli.com/bio (building accessible UIs since 1993; co-founded Algonquin Studios 1998; W3C member in the ARIA, APA and HTML accessibility groups); https://github.com/w3c/aria (1 commit) | Practitioner and standards participant. |
| 35 | Leonie Watson | accessibility, screen readers | PASS | watson (5/2) | https://tink.uk/about/ (TetraLogical co-founder; chair of the W3C Board; co-chair of the W3C Web Applications WG; part of the original GOV.UK team) | Standards leader and long-time practitioner. |
| 36 | Scott O'Hara | accessible widgets, HTML-AAM | PASS | ohara (33/5) | https://github.com/scottaohara/a11y_styled_form_controls (419 commits, rank 1); https://github.com/w3c/html-aria (548, rank 1); https://github.com/w3c/html-aam (202, rank 1) | Spec editor and widget author. |
| 37 | Heydon Pickering | inclusive components, Every Layout | PASS-W | pickering (88/10) | https://github.com/Heydon/inclusive-components (10 commits, rank 1); https://inclusive-components.design and https://every-layout.dev fetched | Widely cited patterns, small public codebase; weight 0.5. |
| 38 | Marcy Sutton | a11y testing, client routing | PASS | sutton (26/5) | https://github.com/dequelabs/axe-core (7612 stars, 41 commits, rank 13); https://github.com/gatsbyjs/gatsby (24, rank 59); https://marcysutton.com/about (Khan Academy senior engineer, frontend infrastructure) | axe-core and Gatsby contributor. |
| 39 | Lea Verou | CSS, web APIs, libraries | PASS | verou (5/2) | https://github.com/PrismJS/prism (13045 stars, 406 commits, rank 3); https://github.com/color-js/color.js; https://github.com/mavoweb/mavo (1397, rank 1); https://github.com/w3c/csswg-drafts (174, rank 18) | Library author; CSSWG member. |
| 40 | Miriam Suzanne | CSS cascade layers, Sass | PASS | suzanne (3/1) | https://github.com/w3c/csswg-drafts (141 commits, rank 23); https://github.com/oddbird/true (238, rank 2); https://github.com/sass/sass (8, rank 9); https://www.miriamsuzanne.com/about (CSSWG invited expert, Sass core team) | Co-wrote the cascade layers spec. |
| 41 | Una Kravets | CSS, web.dev learn | PASS-W | none used | https://github.com/una/CSSgram (5387 stars, 62 commits, rank 1); https://github.com/GoogleChrome/web.dev (45 commits, rank 23) | Chrome DevRel; 0 personal items read, web.dev pages counted as the Chrome docs voice. |
| 42 | Jen Simmons | CSS layout | PASS-W | none used | https://github.com/w3c/csswg-drafts (1 commit, rank 228); https://en.wikipedia.org/wiki/Jen_Simmons (page exists, HTTP 200) | Thin verifiable code; no item read from her; weight 0.5. |
| 43 | Steve Souders | web performance | PASS | souders (9/3) | https://github.com/HTTPArchive/legacy.httparchive.org (301 commits, rank 1) | Founded HTTP Archive; performance rules author (books unsourced here). |
| 44 | Tim Kadlec | performance, responsive | PASS | kadlec (2/1) | https://timkadlec.com/about/ (works on observability and performance at Cloudflare; author of High Performance Images and Implementing Responsive Design) | Practitioner and author. |
| 45 | Rachel Andrew | CSS Grid, docs | PASS | none used | https://github.com/w3c/csswg-drafts (108 commits, rank 27); https://github.com/mdn/content (340, rank 16); https://rachelandrew.co.uk/about/ (Chrome web.dev content lead; edits CSS specs; founded Perch CMS) | Spec editor and CMS founder (no personal items read). |
| 46 | Hidde de Vries | accessibility, standards | PASS-W | devries (28/5) | https://hidde.blog/about-me/ (front-end and accessibility specialist; former W3C WAI staff, Mozilla, Sanity); https://github.com/w3c/wcag (6 commits, rank 37) | Standards and consulting work, thin code; weight 0.5. |
| 47 | Manuel Matuzovic | HTML, CSS, accessibility | PASS-W | matuzovic (24/5) | https://www.matuzo.at/blog/ (articles fetched); no public repository found under the names I tried; about page 404 | Only writing verified; weight 0.5. |
| 48 | Adam Silver | form design, GOV.UK-style patterns | PASS-W | silver (31/5) | https://adamsilver.io/about/ (front-end developer turned UX; GDS-trained design assessor; Just Eat prototyping); https://github.com/alphagov/govuk-frontend (7 commits, rank 28) | Real product work, thin code; weight 0.5. |
| 49 | Stephanie Eckles | modern CSS | PASS-W | eckles (12/2) | https://github.com/5t3ph/stylestage (2229 stars, 281 commits, rank 1) | Educator with one showcase project; weight 0.5. |
| 50 | Ahmad Shadeed | CSS layout | PASS-W | shadeed (8/2) | https://ishadeed.com/about/ (design engineer, Google Developer Expert in Web UI, author of a CSS debugging book); no public code found | Only writing verified; weight 0.5. |
| 51 | Mark Dalgleish | CSS Modules, vanilla-extract | PASS | dalgleish (1/1) | https://github.com/css-modules/css-modules (18039 stars, 11 commits, rank 2); https://github.com/vanilla-extract-css/vanilla-extract (90, rank 5); https://github.com/seek-oss/braid-design-system (289, rank 3); https://github.com/remix-run/remix (299, rank 9) | Co-created CSS Modules (no personal items). |
| 52 | Colin McDonnell | schema validation | PASS | zod (8/2) | https://github.com/colinhacks/zod (44072 stars, 1089 commits, rank 1) | Zod author; docs voice. |
| 53 | Jared Palmer | forms, monorepo tooling | PASS | none used | https://github.com/jaredpalmer/formik (34311 stars, 1174 commits, rank 1); https://github.com/vercel/turborepo (700, rank 4) | Formik author (no items read). |
| 54 | Kitty Giraudel | accessible dialogs, Sass | PASS | none used | https://github.com/KittyGiraudel/a11y-dialog (2488 stars, 1113 commits, rank 1) | a11y-dialog author; one guest post only (guest author weight 0). |
| 55 | Artem Zakharchenko | network mocking | PASS | msw (5/2) | https://github.com/mswjs/msw (18269 stars, 1398 commits, rank 1) | MSW author. |
| 56 | Daishi Kato | client state (Zustand, Jotai) | PASS | none used | https://github.com/pmndrs/zustand (58799 stars, 425 commits, rank 1); https://github.com/pmndrs/jotai (1108, rank 1) | State library author (no items read). |
| 57 | Devon Govett | React Aria, Parcel | PASS | react-aria (12/2) | https://github.com/adobe/react-spectrum (15920 stars, 1836 commits, rank 1); https://github.com/parcel-bundler/parcel (935, rank 1) | React Aria lead; docs voice. |
| 58 | Adam Wathan | Tailwind CSS | PASS | tailwind (31/5) | https://github.com/tailwindlabs/tailwindcss (97798 stars, 2900 commits, rank 1) | Tailwind creator; docs voice. |
| 59 | Vladimir Sheremet | Vitest | PASS | vitest (13/3) | https://github.com/vitest-dev/vitest (2013 commits, rank 1) | Vitest maintainer; docs voice. |
| 60 | Guillermo Rauch | Next.js, Socket.IO | PASS | none used | https://github.com/socketio/socket.io (63219 stars, 3629 commits, rank 1); https://github.com/vercel/next.js (162, rank 37) | Engineering-specific only; no items read. |
| 61 | Tim Neutkens | Next.js | PASS | none used | https://github.com/vercel/next.js (143243 stars, 2867 commits, rank 2) | Next.js core (no items read; Next.js team docs voice). |
| 62 | Sebastian Silbermann | React types and testing | PASS | none used | https://github.com/facebook/react (475 commits, rank 8); https://github.com/DefinitelyTyped/DefinitelyTyped (732, rank 10); https://github.com/mui/material-ui (1327, rank 5) | React core and @types/react (no items read). |
| 63 | Jason Miller | Preact | PASS | none used | https://github.com/preactjs/preact (38916 stars, 1164 commits, rank 3); https://github.com/developit/htm (218, rank 1) | Preact (no items read). |
| 64 | Max Stoiber | styled-components | PASS | none used | https://github.com/styled-components/styled-components (41093 stars, 540 commits, rank 2); https://github.com/mxstbr/react-boilerplate (599, rank 1) | No items read. |
| 65 | Kyle Simpson | JavaScript fundamentals | PASS | none used | https://github.com/getify/You-Dont-Know-JS (185000 stars, 1576 commits, rank 1); https://github.com/getify/LABjs (86, rank 1) | No items read. |
| 66 | Lydia Hallie | patterns.dev, JS education | PASS-W | osmani (45/7) | https://github.com/lydiahallie/javascript-questions (65296 stars; quiz content); https://github.com/lydiahallie/advanced-web-dev-quiz (490) | Content repositories, no shipped-software evidence found; patterns.dev items counted once under Addy Osmani. |
| 67 | Andy Bell | Every Layout co-author | FAIL | none used | https://github.com/hankchizljaw (1 public repo, 13 followers) - the account I could check shows no work; identity of the co-author is not confirmed | Could not verify; item credit given to Heydon Pickering only. |
| 68 | Jesus Ricarte | guest post on kittygiraudel.com | FAIL | none used | byline only; no profile found | Unvetted guest byline, weight 0. |

### 1.2 Organisations used as voices

| Voice | Kind | Verdict | Items | Sources | Canonical rules touched |
|---|---|---|---|---|---|
| React team (docs, WG posts, lints) | org | PASS (weight 1.0) | 111 | 33 | 63 |
| typescript-eslint team | org | PASS (weight 1.0) | 87 | 65 | 40 |
| W3C (WAI, WCAG WG, APG task force) | org | PASS (weight 1.0) | 86 | 16 | 35 |
| Vue / Vite team (Evan You) | org | PASS (weight 1.0) | 70 | 8 | 49 |
| eslint-plugin-react / jsx-a11y maintainers (Jordan Harband et al.) | org | PASS (weight 1.0) | 66 | 66 | 49 |
| WebAIM (Jared Smith) | org | PASS (weight 1.0) | 60 | 7 | 30 |
| Remix / React Router team (Florence, Jackson) | org | PASS (weight 1.0) | 59 | 13 | 32 |
| HTTP Archive Web Almanac (data) | org | PASS (weight 1.0) | 57 | 5 | 41 |
| Svelte team (Rich Harris) | org | PASS (weight 1.0) | 54 | 8 | 42 |
| Google Chrome docs (web.dev, Lighthouse) | org | PASS (weight 1.0) | 50 | 12 | 24 |
| Next.js team (Vercel) | org | PASS (weight 1.0) | 49 | 6 | 27 |
| MDN contributors | org | PASS (weight 1.0) | 45 | 7 | 18 |
| TypeScript team (Hejlsberg et al.) | org | PASS (weight 1.0) | 43 | 7 | 25 |
| Airbnb JavaScript style guide | org | PASS (weight 1.0) | 40 | 3 | 34 |
| GOV.UK Design System team | org | PASS (weight 1.0) | 35 | 5 | 20 |
| ESLint team / Nicholas Zakas | org | PASS (weight 1.0) | 33 | 33 | 17 |
| Tailwind Labs (Adam Wathan) | org | PASS (weight 1.0) | 31 | 5 | 14 |
| Jest team | org | PASS (weight 1.0) | 27 | 17 | 9 |
| Testing Library team and plugin maintainers | org | PASS (weight 1.0) | 26 | 17 | 12 |
| OWASP Cheat Sheet Series | org | PASS (weight 1.0) | 22 | 3 | 10 |
| Playwright team (Microsoft) | org | PASS (weight 1.0) | 20 | 3 | 11 |
| Astro team | org | PASS (weight 1.0) | 20 | 3 | 14 |
| React Hook Form team | org | PASS (weight 1.0) | 20 | 3 | 15 |
| Stylelint team | org | PASS (weight 1.0) | 20 | 20 | 11 |
| TanStack team (Tanner Linsley) | org | PASS (weight 1.0) | 19 | 11 | 11 |
| Vitest team | org | PASS (weight 1.0) | 13 | 3 | 6 |
| Adobe React Aria team (Devon Govett) | org | PASS (weight 1.0) | 12 | 2 | 9 |
| Cypress team | org | PASS (weight 1.0) | 10 | 2 | 3 |
| Storybook team | org | PASS (weight 1.0) | 8 | 1 | 2 |
| Zod (Colin McDonnell) | org | PASS (weight 1.0) | 8 | 2 | 6 |
| eslint-plugin-import maintainers | org | PASS (weight 1.0) | 8 | 8 | 6 |
| Radix UI | org | PASS (weight 1.0) | 6 | 2 | 4 |
| Mock Service Worker (Artem Zakharchenko) | org | PASS (weight 1.0) | 5 | 2 | 2 |
| Sentry | org | PASS (weight 1.0) | 5 | 1 | 1 |
| eslint-plugin-tailwindcss maintainers | org | PASS-W (weight 0.5) | 4 | 4 | 3 |
| GitHub Primer team | org | PASS (weight 1.0) | 3 | 1 | 3 |

People-voices that supplied items:

| Voice | Verdict | Items | Sources | Canonical rules touched |
|---|---|---|---|---|
| Heydon Pickering (with Andy Bell) | PASS-W (weight 0.5) | 88 | 10 | 50 |
| Mark Erikson / Redux maintainers | PASS (weight 1.0) | 65 | 9 | 32 |
| Kent C. Dodds | PASS (weight 1.0) | 60 | 9 | 34 |
| Dominik Dorfmeister | PASS (weight 1.0) | 48 | 9 | 27 |
| Addy Osmani | PASS (weight 1.0) | 45 | 7 | 28 |
| Adrian Roselli | PASS (weight 1.0) | 35 | 5 | 11 |
| Dan Abramov | PASS (weight 1.0) | 34 | 7 | 23 |
| Scott O'Hara | PASS (weight 1.0) | 33 | 5 | 16 |
| Adam Silver | PASS-W (weight 0.5) | 31 | 5 | 17 |
| Matt Pocock | PASS-W (weight 0.5) | 31 | 9 | 14 |
| Hidde de Vries | PASS-W (weight 0.5) | 28 | 5 | 15 |
| Harry Roberts | PASS (weight 1.0) | 28 | 8 | 16 |
| Sara Soueidan | PASS-W (weight 0.5) | 27 | 5 | 21 |
| Marcy Sutton | PASS (weight 1.0) | 26 | 5 | 21 |
| Manuel Matuzovic | PASS-W (weight 0.5) | 24 | 5 | 15 |
| Surma | PASS (weight 1.0) | 15 | 3 | 4 |
| Philip Walton | PASS (weight 1.0) | 13 | 4 | 8 |
| Stephanie Eckles | PASS-W (weight 0.5) | 12 | 2 | 8 |
| Brian Vaughn | PASS (weight 1.0) | 12 | 2 | 10 |
| Solid (Ryan Carniato) | PASS (weight 1.0) | 11 | 3 | 6 |
| Jake Archibald | PASS (weight 1.0) | 10 | 3 | 7 |
| Steve Souders | PASS (weight 1.0) | 9 | 3 | 5 |
| Josh W. Comeau | PASS (weight 1.0) | 9 | 2 | 6 |
| Ahmad Shadeed | PASS-W (weight 0.5) | 8 | 2 | 5 |
| Sophie Alpert | PASS (weight 1.0) | 7 | 4 | 4 |
| Alex Russell | PASS (weight 1.0) | 7 | 2 | 5 |
| Sindre Sorhus | PASS (weight 1.0) | 7 | 7 | 4 |
| Kyle Simpson | PASS (weight 1.0) | 5 | 1 | 2 |
| Leonie Watson | PASS (weight 1.0) | 5 | 2 | 4 |
| Lea Verou | PASS (weight 1.0) | 5 | 2 | 2 |
| Miriam Suzanne | PASS (weight 1.0) | 3 | 1 | 2 |
| Sebastian Markbage | PASS (weight 1.0) | 3 | 1 | 3 |
| Guest author on Giraudel blog (unvetted) | UNVETTED (weight 0.0) | 2 | 1 | 1 |
| Tim Kadlec | PASS (weight 1.0) | 2 | 1 | 1 |
| Mark Dalgleish | PASS (weight 1.0) | 1 | 1 | 1 |

## 2. Sources (step 2)

Full list in section 8 (563 processed units with who, URL, status, item count). Extractor sub-agents: A (React, state, data, TypeScript; 95 sources, 461 items), B (accessibility, forms, security; 105 sources, 699 items), C (performance, CSS, testing, frameworks; 104 sources, 550 items), R (rule catalogue, 249 items by script), M (coordinator, 9 sources, 22 items). A and C shared a scratch helper script once and B's first 26 sources landed in C's files; B moved them back and I checked that every assigned slug has exactly one source record and no duplicate items. Items and relabels are under creators-web/ in the scratchpad: items/*.jsonl, items_all.json, canon.json, stmts.json, relabel_out_*.jsonl, canon_rows.json.

## 3. Taxonomy (step 3)

Base codes follow Mantyla and Lassenius 2009 as extended in the sibling reports; web codes added: WEB.HOOKS, WEB.RENDER, WEB.STATE, WEB.DATA, WEB.TS, WEB.CSS, WEB.A11Y, WEB.PERF, WEB.SEC, WEB.FORMS, WEB.TEST, WEB.ARCH, WEB.BUILD, WEB.ROUTE, WEB.I18N.

| Tax code | Items |
|---|---|
| WEB.A11Y | 451 |
| WEB.CSS | 177 |
| WEB.SEC | 162 |
| WEB.TEST | 161 |
| WEB.PERF | 153 |
| WEB.TS | 145 |
| WEB.STATE | 128 |
| WEB.FORMS | 99 |
| WEB.RENDER | 91 |
| WEB.ARCH | 79 |
| WEB.DATA | 70 |
| WEB.BUILD | 65 |
| WEB.HOOKS | 64 |
| EVO.STR.SOL | 23 |
| FUN.INT | 16 |
| EVO.STR.ORG | 14 |
| FUN.LOG | 13 |
| WEB.ROUTE | 12 |
| EVO.VIS | 10 |
| FUN.CHK | 8 |
| FUN.RES | 7 |
| EVO.DOC.NAME | 7 |
| EVO.DOC.COMMENT | 6 |
| WEB.I18N | 6 |
| FUN.SUP | 4 |
| EVO.STR.ARCH | 4 |
| FUN.TIM | 4 |
| TEST | 1 |
| EVO.DOC.LANG | 1 |

Detection tiers (cheapest tier at which a tool can decide it, helper judgement): syntax = tokens/AST of one file; structural = cross-file model (imports, calls, def-use, component tree, route table) with may/must bounds; types = needs type resolution; effects = needs purity/IO/async effect facts; render = needs rendered DOM/CSS or a browser; human = judgement. Raw items by tier: syntax 1041, human 439, structural 216, types 121, render 92, effects 72. Canonical rules by tier: syntax 243, structural 75, types 28, human 22, render 18, effects 17; by lintability: partial 197, yes 184, no 22.

## 4. Consensus (step 3)

Score = weighted F voices + 0.5 x weighted C voices (one voice per person or organisation per rule). Columns: F/O/C = number of voices, tier, whether an ESLint-family rule is verified (V) or only mentioned (?), frob-v2 coverage (impl = id found in crates; design = ticketed or in design docs; part = partial; none).

### 4.1 Top 30 consensus items

| # | ADV | Canonical rule | Statement | Voices F/O/C | Score | Tier | ESLint-family rule | frob-v2 |
|---|---|---|---|---|---|---|---|---|
| 1 | WADV001 | form-no-label | Flag a form control without a programmatically associated visible label, or a label hidden with display none. | 9/0/2 | 9.0 | syntax | jsx-a11y/label-has-associated-control | designed |
| 2 | WADV002 | effect-for-derived-state | Flag a useEffect whose body only derives state from props or other state and calls a setter. | 8/0/0 | 8.0 | structural | react-hooks/set-state-in-effect | none |
| 3 | WADV003 | alt-text | Flag an img, area, input type image, svg or iframe lacking an alt or accessible name, or a decorative image without empty alt. | 8/0/0 | 7.5 | syntax | jsx-a11y/alt-text, jsx-a11y/iframe-has-title | designed |
| 4 | WADV004 | icon-button-name | Flag a button or link containing only an icon or svg with no accessible name. | 7/0/1 | 7.5 | syntax | jsx-a11y/alt-text, jsx-a11y/anchor-has-content | designed |
| 5 | WADV005 | button-vs-link | Flag navigation implemented as a button with onClick, or an anchor without a real href used as an action. | 7/0/0 | 7.0 | syntax | jsx-a11y/anchor-is-valid, jsx-a11y/no-static-element-interactions | partial |
| 6 | WADV006 | code-splitting-route | Flag a route component, heavy dependency or lazy boundary imported eagerly in the main bundle without dynamic import. | 7/0/0 | 7.0 | structural | - | none |
| 7 | WADV007 | aria-first-rule | Flag a div or span given an ARIA role to imitate a native element that exists, such as button, link, list or heading. | 7/0/1 | 6.5 | syntax | jsx-a11y/aria-role, jsx-a11y/no-interactive-element-to-noninteractive-role | none |
| 8 | WADV008 | stale-closure | Flag a callback or effect reading state captured from an earlier render, such as logging state right after its setter or a stale timer value. | 7/1/0 | 6.5 | structural | react-hooks/exhaustive-deps, react/no-access-state-in-setstate | none |
| 9 | WADV009 | memo-premature | Flag blanket memo, useMemo, useCallback or shouldComponentUpdate with no measured render cost or stable-props justification. | 5/1/2 | 6.0 | structural | react-hooks/preserve-manual-memoization, react-hooks/use-memo | none |
| 10 | WADV013 | effect-fetch-no-cleanup | Flag an effect that starts a request, timer or subscription without returning a cleanup or abort. | 6/0/0 | 6.0 | syntax | - | none |
| 11 | WADV011 | fetch-in-effect-vs-query-lib | Flag hand-written fetch with effect and manual loading state, thunks or reducers where a query library or router loader is available. | 6/0/0 | 6.0 | structural | react-hooks/exhaustive-deps | none |
| 12 | WADV012 | modal-focus-trap | Flag a modal or portal dialog that does not trap focus, restore it on close or lock background scrolling and inertness. | 6/0/0 | 6.0 | effects | - | partial |
| 13 | WADV010 | test-isolation | Flag tests sharing mutable state, leaking mock handlers between tests, or lacking per-test client reset and retry-off configuration. | 6/0/0 | 6.0 | syntax | jest/no-mocks-import, jest/no-standalone-expect | none |
| 14 | WADV014 | live-region | Flag dynamic status, error or result-count updates not announced through a role status or aria-live region, or a live region mounted with its content. | 6/0/1 | 5.75 | syntax | - | partial |
| 15 | WADV015 | aria-redundant-role | Flag a role or aria attribute that duplicates the native semantics of the element, or role none misused, or aria-roledescription. | 4/0/3 | 5.5 | syntax | jsx-a11y/no-interactive-element-to-noninteractive-role, jsx-a11y/no-redundant-roles | partial |
| 16 | WADV016 | role-without-keyboard | Flag an element given an interactive role without matching tabindex and key handlers. | 5/0/1 | 5.5 | syntax | jsx-a11y/click-events-have-key-events, jsx-a11y/interactive-supports-focus | partial |
| 17 | WADV018 | secrets-in-bundle | Flag secrets, source maps, stack traces or sensitive inputs exposed to client bundles, logs or error responses. | 5/0/1 | 5.5 | structural | - | designed |
| 18 | WADV017 | state-derived-in-state | Flag a state variable that stores a value derivable from other state or props, or an unused state definition. | 5/0/1 | 5.5 | structural | react/no-unused-state | none |
| 19 | WADV019 | csp-inline | Flag inline scripts or styles, unsafe-inline, nonce allowlist bypass patterns or meta-delivered CSP where a header is required. | 4/0/2 | 5.0 | render | - | designed |
| 20 | WADV021 | eval-like | Flag eval, new Function, string arguments to setTimeout or setInterval, and dynamic script or worker URLs. | 4/0/2 | 5.0 | syntax | @typescript-eslint/no-implied-eval, no-eval | designed |
| 21 | WADV020 | bundle-size-budget | Flag a build whose shipped JavaScript or CSS bytes exceed the configured budget. | 5/0/0 | 5.0 | render | - | designed |
| 22 | WADV022 | csrf-token | Flag a state-changing operation reachable by GET or a loader, or a mutating request without CSRF protection. | 5/0/0 | 5.0 | structural | - | designed |
| 23 | WADV024 | dead-code | Flag unused exports, unreachable branches and option combinations nothing exercises. | 5/0/0 | 5.0 | structural | @typescript-eslint/no-unused-vars, import/no-unused-modules | partial |
| 24 | WADV023 | tabindex-positive | Flag a tabindex attribute with a value greater than zero. | 5/0/0 | 5.0 | syntax | jsx-a11y/no-noninteractive-tabindex, jsx-a11y/tabindex-no-positive | designed |
| 25 | WADV026 | aria-label-misuse | Flag aria-label on an element that has visible text, or an aria-label used where a visible label element would work. | 5/0/1 | 4.5 | syntax | jsx-a11y/aria-role | none |
| 26 | WADV025 | css-specificity-wars | Flag long descendant or qualified selectors, context overrides or undo declarations used to beat specificity. | 6/0/0 | 4.5 | syntax | stylelint/no-descending-specificity, stylelint/selector-max-compound-selectors | none |
| 27 | WADV027 | progressive-enhancement-baseline | Flag a feature that needs JavaScript for basic function, with no native form, link or select baseline. | 6/0/0 | 4.5 | human | - | none |
| 28 | WADV031 | css-id-selector | Flag an id selector or inline style attribute used for styling. | 5/0/0 | 4.5 | syntax | stylelint/selector-max-id | none |
| 29 | WADV032 | form-native-elements | Flag form logic built on div or custom elements, missing name, novalidate misuse, form.submit instead of requestSubmit, or asterisk-only required. | 4/0/1 | 4.5 | syntax | - | none |
| 30 | WADV029 | heading-order | Flag headings that skip levels or styled text standing in for a real heading element. | 5/0/0 | 4.5 | syntax | - | designed |

Voices behind the top 10 (F side): 
- form-no-label: Adam Silver; HTTP Archive Web Almanac (data); Next.js team (Vercel); React Hook Form team; Sara Soueidan; Svelte team (Rich Harris); W3C (WAI, WCAG WG, APG task force); WebAIM (Jared Smith)
- effect-for-derived-state: Addy Osmani; Brian Vaughn; Dan Abramov; Kent C. Dodds; React team (docs, WG posts, lints); Solid (Ryan Carniato); Svelte team (Rich Harris); Vue / Vite team (Evan You)
- alt-text: Airbnb JavaScript style guide; Heydon Pickering (with Andy Bell); MDN contributors; Scott O'Hara; Svelte team (Rich Harris); W3C (WAI, WCAG WG, APG task force); WebAIM (Jared Smith); eslint-plugin-react / jsx-a11y maintainers (Jordan Harband et al.)
- icon-button-name: Marcy Sutton; Radix UI; Scott O'Hara; Svelte team (Rich Harris); Vue / Vite team (Evan You); WebAIM (Jared Smith); eslint-plugin-react / jsx-a11y maintainers (Jordan Harband et al.)
- button-vs-link: Adrian Roselli; GOV.UK Design System team; Marcy Sutton; Remix / React Router team (Florence, Jackson); Svelte team (Rich Harris); WebAIM (Jared Smith); eslint-plugin-react / jsx-a11y maintainers (Jordan Harband et al.)
- code-splitting-route: Addy Osmani; HTTP Archive Web Almanac (data); React team (docs, WG posts, lints); Remix / React Router team (Florence, Jackson); Svelte team (Rich Harris); TanStack team (Tanner Linsley); Vue / Vite team (Evan You)
- aria-first-rule: Heydon Pickering (with Andy Bell); Hidde de Vries; Leonie Watson; Marcy Sutton; Scott O'Hara; WebAIM (Jared Smith); eslint-plugin-react / jsx-a11y maintainers (Jordan Harband et al.)
- stale-closure: Addy Osmani; Dan Abramov; Heydon Pickering (with Andy Bell); Mark Erikson / Redux maintainers; React team (docs, WG posts, lints); Svelte team (Rich Harris); eslint-plugin-react / jsx-a11y maintainers (Jordan Harband et al.)
- memo-premature: Addy Osmani; Dan Abramov; Dominik Dorfmeister; Kent C. Dodds; React team (docs, WG posts, lints)
- effect-fetch-no-cleanup: Dan Abramov; React team (docs, WG posts, lints); Remix / React Router team (Florence, Jackson); Solid (Ryan Carniato); Svelte team (Rich Harris); Vue / Vite team (Evan You)

### 4.2 Contested items, both sides (top 10)

**form-double-submit** (WADV188): Flag a form submit that has no guard against double submission, or only a disabled button, with no server-side protection.
- For (2): Adam Silver; GOV.UK Design System team
- Against (2): Dominik Dorfmeister; Remix / React Router team (Florence, Jackson)
- Conditional (0): none
- Reading: Real split: disable the submit button while pending (TanStack Query, Remix, Next.js, React docs) versus avoid disabled buttons and guard double submission some other way (GOV.UK, Adam Silver). A lint can require pending feedback and a server-side guard; it should not mandate disabling.

**memo-premature** (WADV009): Flag blanket memo, useMemo, useCallback or shouldComponentUpdate with no measured render cost or stable-props justification.
- For (5): Addy Osmani; Dan Abramov; Dominik Dorfmeister; Kent C. Dodds; React team (docs, WG posts, lints)
- Against (1): eslint-plugin-react / jsx-a11y maintainers (Jordan Harband et al.)
- Conditional (2): Mark Erikson / Redux maintainers [only when measured performance need exists]; Svelte team (Rich Harris) [performance-sensitive trees]
- Reading: React guidance moved from memo-by-default advice to measure first; the plugin rule require-optimization pushes the other way. Flag useCallback/useMemo with no memoized consumer (kcd, React docs) but do not mandate memo; with the React Compiler the question changes again.

**persistent-ui-state-cookie** (WADV349): Flag UI preference state held only in client storage that causes flicker or SSR mismatch, instead of a cookie.
- For (0): none
- Against (1): Lea Verou
- Conditional (1): Remix / React Router team (Florence, Jackson) [mixed positions in same source family]

**god-component** (WADV359): Flag a component or file that mixes data fetching, layout and many responsibilities, or several unrelated components in one file.
- For (0): none
- Against (1): Dominik Dorfmeister
- Conditional (1): eslint-plugin-react / jsx-a11y maintainers (Jordan Harband et al.) [if multiple components per file are acceptable, disable rule]
- Reading: Dorfmeister defends calling the query hook in the component that needs the data over container/presentational splits; eslint-plugin-react no-multi-comp is conditional in its own docs. Size limits are advisory.

**stale-closure** (WADV008): Flag a callback or effect reading state captured from an earlier render, such as logging state right after its setter or a stale timer value.
- For (7): Addy Osmani; Dan Abramov; Heydon Pickering (with Andy Bell); Mark Erikson / Redux maintainers; React team (docs, WG posts, lints); Svelte team (Rich Harris)
- Against (1): Dominik Dorfmeister
- Conditional (0): none
- Reading: Dorfmeister argues a closure is stale only because of memoization, so rule out useCallback rather than lint closures; others want exhaustive-deps style rules. Bind react-hooks/exhaustive-deps and do not invent more.

**aria-redundant-role** (WADV015): Flag a role or aria attribute that duplicates the native semantics of the element, or role none misused, or aria-roledescription.
- For (4): HTTP Archive Web Almanac (data); Kent C. Dodds; Svelte team (Rich Harris); eslint-plugin-react / jsx-a11y maintainers (Jordan Harband et al.)
- Against (0): none
- Conditional (3): W3C (WAI, WCAG WG, APG task force) [mixed positions in same source family]; Adrian Roselli [mixed positions in same source family]; Scott O'Hara [mixed positions in same source family]
- Reading: role=none/presentation and aria-roledescription: Roselli says smell, APG and O'Hara allow them in specific compositions (layout tables, li inside tablist). Flag only redundant roles on native elements; leave presentation roles alone.

**copy-paste-dup** (WADV087): Flag near-identical code blocks duplicated across files or branches.
- For (3): Mock Service Worker (Artem Zakharchenko); Tailwind Labs (Adam Wathan); Vue / Vite team (Evan You)
- Against (1): Dominik Dorfmeister
- Conditional (0): none
- Reading: Dorfmeister argues a little duplication keeps branches free to diverge; others want dedupe. Matches the DUP advice elsewhere in the study: duplicate detection stays advisory.

**test-mock-fetch-network-level** (WADV122): Flag jest.mock of an API client or fetch stub in component tests instead of network-level interception.
- For (2): Dominik Dorfmeister; Kent C. Dodds
- Against (1): Jest team
- Conditional (0): none
- Reading: Jest docs mock the client module; Dodds, MSW and Testing Library prefer network-level interception. Contested between toolkits; lint only the cases the project has chosen.

**naming-convention** (WADV113): Flag identifiers violating naming rules, such as hook state setter mismatch, handler names, I-prefixed interfaces or unclear names.
- For (1): Vue / Vite team (Evan You)
- Against (0): none
- Conditional (3): TypeScript team (Hejlsberg et al.) [TypeScript compiler contributors' own style only]; eslint-plugin-react / jsx-a11y maintainers (Jordan Harband et al.) [mixed positions in same source family]; typescript-eslint team [unless strong naming needs exist]

**test-real-browser** (WADV291): Flag component or e2e tests run in jsdom or a simulated provider where real-browser behaviour matters.
- For (1): Vitest team
- Against (1): Testing Library team and plugin maintainers
- Conditional (0): none

### 4.3 All contested items (opposition or two or more conditional voices)

| ADV | Canonical rule | F | O | C | Against | Conditions |
|---|---|---|---|---|---|---|
| WADV188 | form-double-submit | 2 | 2 | 0 | Dominik Dorfmeister; Remix / React Router team (Florence, Jackson) | - |
| WADV009 | memo-premature | 5 | 1 | 2 | eslint-plugin-react / jsx-a11y maintainers (Jordan Harband et al.) | only when measured performance need exists; performance-sensitive trees |
| WADV349 | persistent-ui-state-cookie | 0 | 1 | 1 | Lea Verou | mixed positions in same source family |
| WADV359 | god-component | 0 | 1 | 1 | Dominik Dorfmeister | if multiple components per file are acceptable, disable rule |
| WADV008 | stale-closure | 7 | 1 | 0 | Dominik Dorfmeister | - |
| WADV015 | aria-redundant-role | 4 | 0 | 3 | - | mixed positions in same source family; mixed positions in same source family; mixed positions in same source family |
| WADV087 | copy-paste-dup | 3 | 1 | 0 | Dominik Dorfmeister | - |
| WADV122 | test-mock-fetch-network-level | 2 | 1 | 0 | Jest team | - |
| WADV113 | naming-convention | 1 | 0 | 3 | - | TypeScript compiler contributors' own style only; mixed positions in same source family; unless strong naming needs exist |
| WADV291 | test-real-browser | 1 | 1 | 0 | Testing Library team and plugin maintainers | - |
| WADV001 | form-no-label | 9 | 0 | 2 | - | mixed positions in same source family; mixed positions in same source family |
| WADV051 | css-important | 3 | 0 | 3 | - | only for single-purpose utility classes; only when no other way to manage specificity; only when the rule must always win by design |
| WADV021 | eval-like | 4 | 0 | 2 | - | mixed positions in same source family; rare projects needing new Function or string timers |
| WADV019 | csp-inline | 4 | 0 | 2 | - | mixed positions in same source family; mixed positions in same source family |
| WADV039 | xss-dangerouslysetinnerhtml | 3 | 0 | 2 | - | mixed positions in same source family; only if content is certainly sanitized |
| WADV077 | state-duplicated-source-of-truth | 2 | 0 | 2 | - | mixed positions in same source family; derived values must be persisted |
| WADV091 | prop-drilling-vs-context | 2 | 0 | 2 | - | only need to avoid prop drilling; mixed positions in same source family |
| WADV143 | form-pending-state | 1 | 0 | 2 | - | React 19 or later; when using React 19 Actions |
| WADV146 | legacy-api-findDOMNode | 1 | 0 | 2 | - | mixed positions in same source family; unless project heavily uses deprecated APIs without migration plan |
| WADV233 | ts-return-type-explicit | 0 | 0 | 2 | - | mixed positions in same source family; mixed positions in same source family |
| WADV224 | csp-trusted-types | 0 | 0 | 2 | - | mixed positions in same source family; mixed positions in same source family |
| WADV033 | form-autocomplete-attr | 4 | 0 | 2 | - | only for inputs rendering their own suggestion popup; mixed positions in same source family |
| WADV069 | skip-link | 3 | 1 | 0 | Manuel Matuzovic | - |
| WADV004 | icon-button-name | 7 | 0 | 1 | - | SVG title naming to avoid verbose output |
| WADV118 | toast-auto-dismiss | 2 | 0 | 2 | - | information also available elsewhere persistently; event discoverable elsewhere in the interface |
| WADV007 | aria-first-rule | 7 | 0 | 1 | - | mixed positions in same source family |
| WADV182 | css-anchor-positioning | 1 | 0 | 2 | - | only for simple light themes, re-invert raster media; only during active press |
| WADV181 | spa-vs-server-rendered | 1 | 0 | 2 | - | content-heavy sites where less JS is valuable; mixed positions in same source family |
| WADV017 | state-derived-in-state | 5 | 0 | 1 | - | for large or collaboratively edited forms |
| WADV018 | secrets-in-bundle | 5 | 0 | 1 | - | only where experimental taint APIs are available |
| WADV016 | role-without-keyboard | 5 | 0 | 1 | - | mixed positions in same source family |
| WADV030 | inline-object-prop-rerender | 4 | 0 | 1 | - | only in tight performance-critical paths |
| WADV032 | form-native-elements | 4 | 0 | 1 | - | when providing custom error summary |
| WADV026 | aria-label-misuse | 5 | 0 | 1 | - | aria-label acceptable for icon-only buttons |
| WADV044 | div-onclick | 4 | 0 | 1 | - | only if unavoidable; add keyboard handler and tabindex |
| WADV052 | render-prop-vs-hook | 3 | 0 | 1 | - | mixed positions in same source family |
| WADV054 | cookie-flags | 3 | 0 | 1 | - | as defense in depth alongside token or fetch-metadata checks |
| WADV061 | key-reset-state | 3 | 0 | 1 | - | mixed positions in same source family |
| WADV065 | js-no-loops | 3 | 0 | 1 | - | as an Airbnb style choice |
| WADV059 | conditional-hook-call | 3 | 0 | 1 | - | mixed positions in same source family |
| WADV060 | dom-order-matches-visual | 3 | 0 | 2 | - | reordered element is not focusable; verify accessibility when using flex-line-count masonry |
| WADV053 | lazy-load-below-fold | 3 | 0 | 1 | - | only with budgets and regression gates |
| WADV057 | js-narrow-scope | 3 | 0 | 1 | - | mixed positions in same source family |
| WADV099 | tabindex-nonnegative-nonfocusable | 3 | 0 | 1 | - | only for inactive controls that should be skipped |
| WADV111 | ts-readonly | 2 | 0 | 1 | - | mixed positions in same source family |
| WADV108 | test-one-assertion-per-test | 2 | 0 | 1 | - | only for independent checks |
| WADV110 | test-act-warning | 2 | 0 | 1 | - | mixed positions in same source family |
| WADV115 | loose-equality | 2 | 0 | 1 | - | mixed positions in same source family |
| WADV107 | invalid-html-nesting | 2 | 0 | 1 | - | mixed positions in same source family |
| WADV106 | long-task-yield | 2 | 0 | 1 | - | mixed positions in same source family |
| WADV133 | ts-generic-needless | 2 | 0 | 1 | - | unless single-use type parameters are intended |
| WADV129 | combobox-aria-contract | 2 | 0 | 1 | - | only for comboboxes using aria-activedescendant |
| WADV189 | query-stale-time | 1 | 0 | 1 | - | mixed positions in same source family |
| WADV210 | react-production-build | 1 | 0 | 1 | - | project targets React 17+ |
| WADV205 | typed-route-links | 1 | 0 | 1 | - | using React Router framework mode |
| WADV213 | ts-optional-vs-undefined | 1 | 0 | 1 | - | TypeScript compiler contributors' own convention |
| WADV216 | context-provider-depth | 1 | 0 | 1 | - | more than two or three state contexts |
| WADV183 | query-key-structure | 1 | 0 | 1 | - | mixed positions in same source family |
| WADV208 | console-log-left | 1 | 0 | 1 | - | only in browser-targeted code, not Node |
| WADV212 | ts-exhaustive-switch | 1 | 0 | 1 | - | mixed positions in same source family |
| WADV187 | dependency-vulnerable | 1 | 0 | 1 | - | mixed positions in same source family |
| WADV202 | todo-untracked | 1 | 0 | 1 | - | mixed positions in same source family |
| WADV198 | state-library-overuse | 1 | 0 | 1 | - | only when synchronization of copies is unavoidable |
| WADV209 | query-spread-result | 1 | 0 | 1 | - | if notifyOnChangeProps is set |
| WADV201 | test-testid-overuse | 1 | 0 | 1 | - | mixed positions in same source family |
| WADV190 | web-component-vs-framework | 1 | 0 | 1 | - | generalizable widgets with many consumers |
| WADV211 | sri | 1 | 0 | 1 | - | only when external hosting is unavoidable |
| WADV219 | target-blank-noopener | 1 | 0 | 1 | - | only needed for old browsers or to suppress referrer |
| WADV185 | aria-hint-text | 1 | 0 | 1 | - | mixed positions in same source family |
| WADV193 | css-vendor-prefix | 1 | 0 | 2 | - | only when old IE support is required; mixed positions in same source family |
| WADV195 | hoc-wrapper-hell | 1 | 0 | 1 | - | large lists |
| WADV217 | mutating-arguments | 1 | 0 | 1 | - | unless parameter reassignment is deliberately allowed |
| WADV194 | fn-length | 1 | 0 | 1 | - | mixed positions in same source family |
| WADV200 | swallowed-error | 1 | 0 | 1 | - | mixed positions in same source family |
| WADV197 | rule-jest-prefer-expect-assertions | 1 | 0 | 1 | - | mixed positions in same source family |
| WADV226 | ts-strict-mode | 1 | 0 | 1 | - | mixed positions in same source family |
| WADV243 | toast-interactive-content | 1 | 0 | 1 | - | mixed positions in same source family |

## 5. Lint candidates and detectability (step 4)

### 5.1 Ranked candidates (consensus, lintable, static tier)

Filter: lintable yes or partial, tier syntax/structural/types/effects, at least two voices, score at least 2.5. Rule = verified ESLint-family rule from a fetched rule doc. Recommendation: bind = run the existing linter through a [[check.tool]] stage with an id map (rules.md s4 pattern used for NEAT001/NEAT002); own = implement in frob/grimble/crunk.

| ADV | Canonical rule | Tier | Score (voices) | Existing rule | frob-v2 | Suggested family | Recommendation | Hullbreach |
|---|---|---|---|---|---|---|---|---|
| WADV001 | form-no-label | syntax | 9.0 (11) | jsx-a11y/label-has-associated-control | designed | FORM (new) over A11Y | bind jsx-a11y/label-has-associated-control | ok: every input has a label with htmlFor |
| WADV002 | effect-for-derived-state | structural | 8.0 (8) | react-hooks/set-state-in-effect | none | REACT (new grimble pack) | bind react-hooks/set-state-in-effect; own only the cross-file/effects extension | - |
| WADV003 | alt-text | syntax | 7.5 (8) | jsx-a11y/alt-text, jsx-a11y/iframe-has-title | designed | A11Y (crunk-web) | bind jsx-a11y/alt-text, jsx-a11y/iframe-has-title | n/a: no images yet |
| WADV004 | icon-button-name | syntax | 7.5 (8) | jsx-a11y/alt-text, jsx-a11y/anchor-has-content | designed | A11Y (crunk-web) | bind jsx-a11y/alt-text, jsx-a11y/anchor-has-content | - |
| WADV005 | button-vs-link | syntax | 7.0 (7) | jsx-a11y/anchor-is-valid, jsx-a11y/no-static-element-interactions | partial | A11Y (crunk-web) | bind jsx-a11y/anchor-is-valid, jsx-a11y/no-static-element-interactions | applies: Header brand is a button that calls window.location.assign("/"); internal <a href> links bypass the router |
| WADV006 | code-splitting-route | structural | 7.0 (7) | none | none | WEBPERF (crunk-web markup/assets; grimble-websec server) | own (heuristic, advisory severity) | n/a: three routes today; becomes relevant with the queued pages (T-0032 onward) |
| WADV007 | aria-first-rule | syntax | 6.5 (8) | jsx-a11y/aria-role, jsx-a11y/no-interactive-element-to-noninteractive-role | none | A11Y (crunk-web) | bind jsx-a11y/aria-role, jsx-a11y/no-interactive-element-to-noninteractive-role | - |
| WADV008 | stale-closure | structural | 6.5 (8) | react-hooks/exhaustive-deps, react/no-access-state-in-setstate | none | REACT (new grimble pack) | bind react-hooks/exhaustive-deps, react/no-access-state-in-setstate; own only the cross-file/effects extension | - |
| WADV009 | memo-premature | structural | 6.0 (8) | react-hooks/preserve-manual-memoization, react-hooks/use-memo | none | REACT (new grimble pack) | bind react-hooks/preserve-manual-memoization, react-hooks/use-memo; own only the cross-file/effects extension | ok: no memo or useCallback anywhere |
| WADV013 | effect-fetch-no-cleanup | syntax | 6.0 (6) | none | none | REACT (new grimble pack) | own | partial: requestJson has no AbortSignal or timeout (frob:todo T-0102 already records it) |
| WADV011 | fetch-in-effect-vs-query-lib | structural | 6.0 (6) | react-hooks/exhaustive-deps | none | REACT/DATA (new grimble pack) | bind react-hooks/exhaustive-deps; own only the cross-file/effects extension | - |
| WADV012 | modal-focus-trap | effects | 6.0 (6) | none | partial | A11Y (crunk-web) | own with the effects capability (advisory heuristic first) | - |
| WADV010 | test-isolation | syntax | 6.0 (6) | jest/no-mocks-import, jest/no-standalone-expect | none | TEST (universal) + WTEST (new) | bind jest/no-mocks-import, jest/no-standalone-expect | - |
| WADV014 | live-region | syntax | 5.75 (7) | none | partial | A11Y (crunk-web) | own (heuristic, advisory severity) | partial: role=alert banner present; success state replaces the page content without a live region |
| WADV015 | aria-redundant-role | syntax | 5.5 (7) | jsx-a11y/no-interactive-element-to-noninteractive-role, jsx-a11y/no-redundant-roles | partial | A11Y (crunk-web) | bind jsx-a11y/no-interactive-element-to-noninteractive-role, jsx-a11y/no-redundant-roles | - |
| WADV016 | role-without-keyboard | syntax | 5.5 (6) | jsx-a11y/click-events-have-key-events, jsx-a11y/interactive-supports-focus | partial | A11Y (crunk-web) | bind jsx-a11y/click-events-have-key-events, jsx-a11y/interactive-supports-focus | - |
| WADV018 | secrets-in-bundle | structural | 5.5 (6) | none | designed | WEBSEC (grimble-websec) | own (heuristic, advisory severity) | - |
| WADV017 | state-derived-in-state | structural | 5.5 (6) | react/no-unused-state | none | REACT (new grimble pack) | bind react/no-unused-state; own only the cross-file/effects extension | - |
| WADV021 | eval-like | syntax | 5.0 (6) | @typescript-eslint/no-implied-eval, no-eval | designed | WEBSEC (grimble-websec) | bind @typescript-eslint/no-implied-eval, no-eval | - |
| WADV022 | csrf-token | structural | 5.0 (5) | none | designed | WEBSEC (grimble-websec) | own (heuristic, advisory severity) | - |
| WADV024 | dead-code | structural | 5.0 (5) | @typescript-eslint/no-unused-vars, import/no-unused-modules | partial | ARCH/NEAT (universal) | bind @typescript-eslint/no-unused-vars, import/no-unused-modules; own only the cross-file/effects extension | - |
| WADV023 | tabindex-positive | syntax | 5.0 (5) | jsx-a11y/no-noninteractive-tabindex, jsx-a11y/tabindex-no-positive | designed | A11Y (crunk-web) | bind jsx-a11y/no-noninteractive-tabindex, jsx-a11y/tabindex-no-positive | - |
| WADV026 | aria-label-misuse | syntax | 4.5 (6) | jsx-a11y/aria-role | none | A11Y (crunk-web) | bind jsx-a11y/aria-role | - |
| WADV025 | css-specificity-wars | syntax | 4.5 (6) | stylelint/no-descending-specificity, stylelint/selector-max-compound-selectors | none | WCSS (new, crunk) + TOKEN/ORG/TW | bind stylelint/no-descending-specificity, stylelint/selector-max-compound-selectors | - |
| WADV031 | css-id-selector | syntax | 4.5 (5) | stylelint/selector-max-id | none | WCSS (new, crunk) + TOKEN/ORG/TW | bind stylelint/selector-max-id | - |
| WADV032 | form-native-elements | syntax | 4.5 (5) | none | none | FORM (new) over A11Y | own (heuristic, advisory severity) | - |
| WADV029 | heading-order | syntax | 4.5 (5) | none | designed | A11Y (crunk-web) | own | ok: one h1 per page |
| WADV030 | inline-object-prop-rerender | syntax | 4.5 (5) | react/jsx-no-bind, react/no-object-type-as-default-prop | none | REACT (new grimble pack) | bind react/jsx-no-bind, react/no-object-type-as-default-prop | - |
| WADV028 | render-blocking-script | syntax | 4.5 (5) | none | designed | WEBPERF (crunk-web markup/assets; grimble-websec server) | own | - |
| WADV033 | form-autocomplete-attr | syntax | 4.25 (6) | jsx-a11y/autocomplete-valid | designed | FORM (new) over A11Y | bind jsx-a11y/autocomplete-valid | applies: Login/Register inputs carry no autocomplete attribute (username, current-password, new-password, email) |
| WADV034 | css-global-leak | structural | 4.25 (5) | none | none | WCSS (new, crunk) + TOKEN/ORG/TW | own (heuristic, advisory severity) | - |
| WADV044 | div-onclick | syntax | 4.0 (5) | jsx-a11y/click-events-have-key-events, jsx-a11y/no-noninteractive-element-interactions | partial | A11Y (crunk-web) | bind jsx-a11y/click-events-have-key-events, jsx-a11y/no-noninteractive-element-interactions | - |
| WADV045 | focus-management-route-change | effects | 4.0 (5) | none | partial | A11Y (crunk-web) | own with the effects capability (advisory heuristic first) | applies: no focus or announcement on client navigation; login and logout use window.location.assign |
| WADV039 | xss-dangerouslysetinnerhtml | syntax | 4.0 (5) | react/no-danger, react/no-danger-with-children | designed | WEBSEC (grimble-websec) | bind react/no-danger, react/no-danger-with-children | ok: not used |
| WADV042 | asset-fingerprint-long-cache | structural | 4.0 (4) | none | designed | WBUILD (new, small) | own (heuristic, advisory severity) | - |
| WADV046 | button-type-attr | syntax | 4.0 (4) | react/button-has-type | none | FORM (new) over A11Y | bind react/button-has-type | - |
| WADV049 | controlled-uncontrolled-switch | structural | 4.0 (4) | react/checked-requires-onchange-or-readonly | none | REACT (new grimble pack) | bind react/checked-requires-onchange-or-readonly; own only the cross-file/effects extension | - |
| WADV038 | effect-missing-deps | syntax | 4.0 (4) | react-hooks/exhaustive-deps | none | REACT (new grimble pack) | bind react-hooks/exhaustive-deps | ok: react-hooks/exhaustive-deps is on (plugin v5) |
| WADV040 | error-boundary-missing | structural | 4.0 (4) | react-hooks/error-boundaries | partial | REACT (new grimble pack) | bind react-hooks/error-boundaries; own only the cross-file/effects extension | applies: createBrowserRouter routes define no errorElement |
| WADV050 | key-index-as-key | syntax | 4.0 (4) | react/no-array-index-key | none | REACT (new grimble pack) | bind react/no-array-index-key | n/a: no lists yet |
| WADV047 | mutable-export | syntax | 4.0 (4) | import/no-default-export, import/no-mutable-exports | none | ARCH/NEAT (universal) | bind import/no-default-export, import/no-mutable-exports | - |
| WADV041 | mutate-state-directly | syntax | 4.0 (4) | react-hooks/immutability, react/no-direct-mutation-state | none | REACT (new grimble pack) | bind react-hooks/immutability, react/no-direct-mutation-state | - |
| WADV048 | render-purity | effects | 4.0 (4) | react-hooks/globals, react-hooks/purity | none | REACT (new grimble pack) | bind react-hooks/globals, react-hooks/purity; own only the cross-file/effects extension | - |
| WADV035 | server-client-boundary | structural | 4.0 (4) | react-hooks/rules-of-hooks | partial | ARCH/NEAT (universal) | bind react-hooks/rules-of-hooks; own only the cross-file/effects extension | - |
| WADV036 | state-colocate | structural | 4.0 (4) | none | none | REACT (new grimble pack) | own (heuristic, advisory severity) | - |
| WADV037 | test-a11y-axe | syntax | 4.0 (4) | none | designed | TEST (universal) + WTEST (new) | own (heuristic, advisory severity) | applies: no axe or jest-axe test; 3 component test files only |
| WADV043 | test-await-async | syntax | 4.0 (4) | jest/no-done-callback, testing-library/await-async-events | none | TEST (universal) + WTEST (new) | bind jest/no-done-callback, testing-library/await-async-events | - |
| WADV051 | css-important | syntax | 3.75 (6) | stylelint/declaration-no-important | none | WCSS (new, crunk) + TOKEN/ORG/TW | bind stylelint/declaration-no-important | - |
| WADV058 | page-title-spa | effects | 3.5 (5) | none | partial | A11Y (crunk-web) | own with the effects capability (advisory heuristic first) | applies: index.html has one static title; routes do not update document.title |
| WADV059 | conditional-hook-call | syntax | 3.5 (4) | react-hooks/rules-of-hooks | none | REACT (new grimble pack) | bind react-hooks/rules-of-hooks | ok: react-hooks/rules-of-hooks is on |
| WADV054 | cookie-flags | syntax | 3.5 (4) | none | designed | WEBSEC (grimble-websec) | own | - |
| WADV056 | focus-outline-removed | syntax | 3.5 (4) | none | designed | A11Y (crunk-web) | own | ok: reset.css does not remove outlines |
| WADV055 | form-error-association | syntax | 3.5 (4) | ?jsx-a11y/aria-proptypes | none | FORM (new) over A11Y | own (extractor mentions jsx-a11y/aria-proptypes? unverified; check before building) | partial: field errors use aria-describedby, but no aria-invalid and the banner role=alert does not receive focus |
| WADV062 | hover-only-interaction | syntax | 3.5 (4) | jsx-a11y/mouse-events-have-key-events | partial | A11Y (crunk-web) | bind jsx-a11y/mouse-events-have-key-events | - |
| WADV057 | js-narrow-scope | syntax | 3.5 (4) | @typescript-eslint/no-shadow, no-shadow | none | NEAT (universal) | bind @typescript-eslint/no-shadow, no-shadow | - |
| WADV065 | js-no-loops | syntax | 3.5 (4) | @typescript-eslint/no-for-in-array, no-await-in-loop | none | NEAT (universal) | bind @typescript-eslint/no-for-in-array, no-await-in-loop | - |
| WADV061 | key-reset-state | structural | 3.5 (4) | ?react/no-unsafe | none | REACT (new grimble pack) | own (extractor mentions react/no-unsafe? unverified; check before building) | - |
| WADV063 | lang-attr | syntax | 3.5 (4) | jsx-a11y/html-has-lang, jsx-a11y/lang | designed | A11Y (crunk-web) | bind jsx-a11y/html-has-lang, jsx-a11y/lang | ok: index.html has lang="en" |
| WADV053 | lazy-load-below-fold | syntax | 3.5 (4) | none | designed | WEBPERF (crunk-web markup/assets; grimble-websec server) | own (heuristic, advisory severity) | - |
| WADV064 | ts-import-type | syntax | 3.5 (4) | @typescript-eslint/consistent-type-imports, @typescript-eslint/no-import-type-side-effects | none | TS (bind typescript-eslint) | bind @typescript-eslint/consistent-type-imports, @typescript-eslint/no-import-type-side-effects | - |
| WADV087 | copy-paste-dup | structural | 3.0 (4) | none | partial | ARCH/NEAT (universal) | own (heuristic, advisory severity) | - |
| WADV067 | css-custom-property-tokens | syntax | 3.0 (4) | stylelint/no-unknown-custom-properties | partial | WCSS (new, crunk) + TOKEN/ORG/TW | bind stylelint/no-unknown-custom-properties | - |
| WADV080 | css-magic-number | syntax | 3.0 (4) | react/forbid-dom-props | partial | WCSS (new, crunk) + TOKEN/ORG/TW | bind react/forbid-dom-props | - |
| WADV088 | custom-widget-aria-state | syntax | 3.0 (4) | none | none | A11Y (crunk-web) | own (heuristic, advisory severity) | - |
| WADV075 | link-text-unique | syntax | 3.0 (4) | jsx-a11y/anchor-ambiguous-text, jsx-a11y/anchor-has-content | partial | A11Y (crunk-web) | bind jsx-a11y/anchor-ambiguous-text, jsx-a11y/anchor-has-content | - |
| WADV091 | prop-drilling-vs-context | structural | 3.0 (4) | none | none | REACT (new grimble pack) | own (heuristic, advisory severity) | - |
| WADV069 | skip-link | structural | 3.0 (4) | none | designed | A11Y (crunk-web) | own (heuristic, advisory severity) | applies: Header precedes main on every page; no skip link |
| WADV077 | state-duplicated-source-of-truth | structural | 3.0 (4) | none | none | REACT (new grimble pack) | own (heuristic, advisory severity) | - |
| WADV099 | tabindex-nonnegative-nonfocusable | syntax | 3.0 (4) | jsx-a11y/no-noninteractive-tabindex | none | A11Y (crunk-web) | bind jsx-a11y/no-noninteractive-tabindex | - |
| WADV073 | aria-hidden-focusable | syntax | 3.0 (3) | jsx-a11y/no-aria-hidden-on-focusable | designed | A11Y (crunk-web) | bind jsx-a11y/no-aria-hidden-on-focusable | - |
| WADV085 | async-race-condition | structural | 3.0 (3) | react-hooks/exhaustive-deps, require-atomic-updates | none | REACT/DATA (new grimble pack) | bind react-hooks/exhaustive-deps, require-atomic-updates; own only the cross-file/effects extension | - |
| WADV095 | barrel-import-cycle | structural | 3.0 (3) | @typescript-eslint/no-restricted-imports, import/no-cycle | implemented | ARCH/NEAT (universal) | bind @typescript-eslint/no-restricted-imports, import/no-cycle; own only the cross-file/effects extension | - |
| WADV096 | children-as-jsx-to-avoid-rerender | structural | 3.0 (3) | react/no-children-prop | none | REACT (new grimble pack) | bind react/no-children-prop; own only the cross-file/effects extension | - |
| WADV086 | component-defined-inside-component | syntax | 3.0 (3) | react-hooks/component-hook-factories, react-hooks/static-components | none | REACT (new grimble pack) | bind react-hooks/component-hook-factories, react-hooks/static-components | - |
| WADV081 | css-naming-convention | syntax | 3.0 (3) | stylelint/selector-class-pattern | designed | WCSS (new, crunk) + TOKEN/ORG/TW | bind stylelint/selector-class-pattern | - |
| WADV089 | effect-object-dep-unstable | syntax | 3.0 (3) | @tanstack/query/no-unstable-deps, react-hooks/exhaustive-deps | none | REACT (new grimble pack) | bind @tanstack/query/no-unstable-deps, react-hooks/exhaustive-deps | - |
| WADV101 | fieldset-legend-group | syntax | 3.0 (3) | none | none | FORM (new) over A11Y | own | - |
| WADV102 | form-placeholder-as-label | syntax | 3.0 (3) | none | none | FORM (new) over A11Y | own | - |
| WADV070 | js-case-declarations | syntax | 3.0 (3) | array-callback-return, default-case-last | none | NEAT (universal) | bind array-callback-return, default-case-last | - |
| WADV097 | js-no-this-alias | syntax | 3.0 (3) | react/no-this-in-sfc | none | NEAT (universal) | bind react/no-this-in-sfc | - |
| WADV090 | lint-no-restricted-syntax | syntax | 3.0 (3) | no-restricted-globals, react/forbid-dom-props | none | NEAT (universal) | bind no-restricted-globals, react/forbid-dom-props | - |
| WADV082 | media-captions | syntax | 3.0 (3) | jsx-a11y/media-has-caption | designed | A11Y (crunk-web) | bind jsx-a11y/media-has-caption | - |
| WADV103 | memo-custom-comparator | syntax | 3.0 (3) | none | none | REACT (new grimble pack) | own (heuristic, advisory severity) | - |
| WADV076 | preload-misuse | syntax | 3.0 (3) | none | none | WEBPERF (crunk-web markup/assets; grimble-websec server) | own (heuristic, advisory severity) | - |
| WADV104 | sanitize-with-library | syntax | 3.0 (3) | none | none | WEBSEC (grimble-websec) | own (heuristic, advisory severity) | - |
| WADV083 | suspense-boundary | structural | 3.0 (3) | none | none | REACT/DATA (new grimble pack) | own (heuristic, advisory severity) | - |
| WADV092 | table-semantics | syntax | 3.0 (3) | jsx-a11y/scope | none | A11Y (crunk-web) | bind jsx-a11y/scope | - |
| WADV068 | test-flaky-wait | syntax | 3.0 (3) | testing-library/no-wait-for-multiple-assertions, testing-library/no-wait-for-side-effects | none | TEST (universal) + WTEST (new) | bind testing-library/no-wait-for-multiple-assertions, testing-library/no-wait-for-side-effects | - |
| WADV071 | test-implementation-details | syntax | 3.0 (3) | testing-library/no-container, testing-library/no-node-access | none | TEST (universal) + WTEST (new) | bind testing-library/no-container, testing-library/no-node-access | - |
| WADV072 | test-query-by-role | syntax | 3.0 (3) | testing-library/prefer-find-by, testing-library/prefer-presence-queries | none | TEST (universal) + WTEST (new) | bind testing-library/prefer-find-by, testing-library/prefer-presence-queries | ok: tests already use getByRole and getByLabelText |
| WADV078 | third-party-cost | structural | 3.0 (3) | none | none | WEBPERF (crunk-web markup/assets; grimble-websec server) | own (heuristic, advisory severity) | - |
| WADV093 | tsconfig-include-exclude | syntax | 3.0 (3) | none | none | WBUILD (new, small) | own | - |
| WADV084 | upload-validate-server | structural | 3.0 (3) | none | none | WEBSEC (grimble-websec) | own (heuristic, advisory severity) | - |
| WADV079 | use-client-too-high | structural | 3.0 (3) | none | partial | WEBPERF (crunk-web markup/assets; grimble-websec server) | own (heuristic, advisory severity) | - |
| WADV100 | usecallback-without-memo | structural | 3.0 (3) | react-hooks/exhaustive-deps | none | REACT (new grimble pack) | bind react-hooks/exhaustive-deps; own only the cross-file/effects extension | - |
| WADV094 | xss-output-encoding | syntax | 3.0 (3) | none | partial | WEBSEC (grimble-websec) | own (heuristic, advisory severity) | - |
| WADV105 | xss-url-scheme | syntax | 3.0 (3) | no-script-url, react/jsx-no-script-url | designed | WEBSEC (grimble-websec) | bind no-script-url, react/jsx-no-script-url | - |
| WADV113 | naming-convention | syntax | 2.5 (4) | @typescript-eslint/naming-convention, react/hook-use-state | none | NEAT (universal) | bind @typescript-eslint/naming-convention, react/hook-use-state | - |
| WADV114 | css-px-vs-rem | syntax | 2.5 (3) | stylelint/unit-disallowed-list | partial | WCSS (new, crunk) + TOKEN/ORG/TW | bind stylelint/unit-disallowed-list | - |
| WADV109 | error-not-color-only | syntax | 2.5 (3) | none | none | A11Y (crunk-web) | own (heuristic, advisory severity) | - |
| WADV107 | invalid-html-nesting | syntax | 2.5 (3) | react/jsx-no-useless-fragment, react/no-invalid-html-attribute | none | REACT (new grimble pack) | bind react/jsx-no-useless-fragment, react/no-invalid-html-attribute | - |
| WADV112 | keyboard-operable | syntax | 2.5 (3) | none | none | A11Y (crunk-web) | own (heuristic, advisory severity) | - |
| WADV106 | long-task-yield | effects | 2.5 (3) | none | none | WEBPERF (crunk-web markup/assets; grimble-websec server) | own with the effects capability (advisory heuristic first) | - |
| WADV115 | loose-equality | syntax | 2.5 (3) | eqeqeq | none | NEAT (universal) | bind eqeqeq | - |
| WADV110 | test-act-warning | syntax | 2.5 (3) | testing-library/no-unnecessary-act | none | TEST (universal) + WTEST (new) | bind testing-library/no-unnecessary-act | - |
| WADV108 | test-one-assertion-per-test | syntax | 2.5 (3) | jest/expect-expect, jest/no-conditional-expect | none | TEST (universal) + WTEST (new) | bind jest/expect-expect, jest/no-conditional-expect | - |
| WADV111 | ts-readonly | types | 2.5 (3) | @typescript-eslint/prefer-readonly, @typescript-eslint/prefer-readonly-parameter-types | none | TS (bind typescript-eslint) | bind @typescript-eslint/prefer-readonly, @typescript-eslint/prefer-readonly-parameter-types | - |
| WADV116 | viewport-no-zoom | syntax | 2.5 (3) | none | none | A11Y (crunk-web) | own | - |

(108 candidates; all 403 canonical rules are in section 6.)

### 5.2 Top 10 candidates frob should own (no ESLint-family rule found, lintable, static tier)

| # | Candidate | Why frob should own it |
|---|---|---|
| 1 | effect-fetch-no-cleanup | REACT: an effect that starts a request, timer or subscription without a cleanup or abort. Syntax tier, six voices (Abramov, React docs, Remix/React Router, Solid, Svelte, TanStack). react-hooks has exhaustive-deps but nothing for missing cleanup. Hullbreach already carries T-0102 for the fetch-timeout half. |
| 2 | code-splitting-route | ROUTE/WEBPERF: route components and heavy dependencies imported eagerly in the main bundle. Structural over the gob-frameworks route table plus the import graph; seven voices incl. the Web Almanac and Osmani. No linter does route-aware checks. |
| 3 | page-title-spa + focus-management-route-change | A11Y/ROUTE: a client route that neither updates document.title nor moves focus or announces on navigation. Structural over the route table (gob-frameworks) with effects facts; ten voices across the two rules (Sutton, O'Hara, Pickering, de Vries, W3C). axe cannot see it statically. Hullbreach applies (static title, window.location.assign). |
| 4 | secrets-in-bundle + env-var-leak-client | WEBSEC: secrets, source maps or server-only env reads reaching client bundles. Already ticketed as WEBSEC310-317; six voices (Next.js, Astro, Remix, Zod docs, Almanac). Not an ESLint rule; share the secret-pattern table with SEC001-003. |
| 5 | csrf-token + cookie-flags | WEBSEC: state-changing GET or loader, missing CSRF protection, cookies without httpOnly/secure/sameSite. Ticketed WEBSEC201-208; nine voices. Structural over route handlers. |
| 6 | heading-order + skip-link + focus-outline-removed | A11Y: heading level skips, absent skip link, outline:none without a replacement. Ticketed A11Y101-128; WebAIM, web.dev, Sutton, W3C agree; jsx-a11y has no heading-order or focus-style rule. Needs CSS plus JSX facts (markup and style capabilities). |
| 7 | form-placeholder-as-label + form-error-association + fieldset-legend-group | FORM/A11Y: placeholder without label, error text not tied to its field (aria-describedby plus aria-invalid), radio/checkbox groups without fieldset and legend. About ten voices (GOV.UK, Silver, O'Hara, React docs, W3C). jsx-a11y checks label association only. Hullbreach is half-compliant (aria-describedby yes, aria-invalid no). |
| 8 | state-colocate + prop-drilling-vs-context | REACT: state held far above its only reader; a prop forwarded unchanged through several components. Structural over the component tree with may bounds (props named at call sites are May). Eight voices (Abramov, Dodds, Erikson, React docs, Markbage, Remix). |
| 9 | usesyncexternalstore-for-subscriptions + effect-chain-state | REACT: effect plus setState subscriptions to external stores (use useSyncExternalStore) and effects that only set state to trigger another effect. React docs and Osmani; the new react-hooks compiler lints (set-state-in-effect) cover part but require plugin v6 and the compiler config. Hullbreach useSession is the first case. |
| 10 | ts-zod-parse-boundary + ts-assertion-as at response.json() | TS: unvalidated casts of network data at the boundary (res.json() as T). Types tier; typescript-eslint has no-unsafe-type-assertion but not boundary-aware parsing. Zod docs and Pocock; Hullbreach api/auth.ts is the exact shape. Treat as a types-capability candidate, advisory at first. |

Cross-cutting reason: these are the cases where the universal model (route table, import graph, markup plus style facts, May/Must bounds) sees more than a single-file ESLint visitor; everything else in 5.1 with a verified rule should be bound, not rewritten.

### 5.3 Applicability to project-hullbreach/platform (web/, read-only)

Stack read from package.json, eslint.config.js, tsconfig.json, vite.config.ts and web/src: React 18.3, react-router-dom 7, Tailwind 4, vite, vitest and Testing Library, 11 TSX and 5 TS files including tests, 4 of them test files. ESLint runs js recommended, typescript-eslint recommended (not type-checked), eslint-plugin-react recommended and react-hooks 5 recommended; no jsx-a11y, no testing-library or jest-dom plugin, no import plugin, no stylelint. tsconfig is strict with noUnusedLocals and noUnusedParameters, without noUncheckedIndexedAccess or exactOptionalPropertyTypes.

| Canonical rule | Status | Evidence in the platform tree |
|---|---|---|
| button-vs-link (WADV005) | applies | Header brand is a button that calls window.location.assign("/"); internal <a href> links bypass the router |
| dependency-vulnerable (WADV187) | applies | no npm audit or frob vet stage visible for package-lock.json in eslint config; frob.toml not inspected for it |
| error-boundary-missing (WADV040) | applies | createBrowserRouter routes define no errorElement |
| focus-management-route-change (WADV045) | applies | no focus or announcement on client navigation; login and logout use window.location.assign |
| form-autocomplete-attr (WADV033) | applies | Login/Register inputs carry no autocomplete attribute (username, current-password, new-password, email) |
| form-double-submit (WADV188) | applies | submit buttons are not disabled or aria-busy while the request is in flight |
| form-onchange-sync-everything (WADV142) | applies | controlled inputs mirror every keystroke into state (3 fields, harmless at this size) |
| form-pending-state (WADV143) | applies | no pending state on Login/Register submit |
| hardcoded-strings-i18n (WADV144) | applies | all copy is inline literal JSX text; no i18n layer |
| page-title-spa (WADV058) | applies | index.html has one static title; routes do not update document.title |
| skip-link (WADV069) | applies | Header precedes main on every page; no skip link |
| tailwind-arbitrary-value (WADV344) | applies | max-w-[24rem] in Login and Register |
| test-a11y-axe (WADV037) | applies | no axe or jest-axe test; 3 component test files only |
| token-in-localstorage (WADV336) | applies | web/src/auth/session.ts stores the bearer token in window.localStorage |
| ts-assertion-as (WADV119) | applies | as T and as Record<string, unknown> in api/auth.ts and auth/session.ts |
| ts-zod-parse-boundary (WADV244) | applies | web/src/api/auth.ts returns (await response.json()) as T with no runtime validation |
| typed-linting-enabled (WADV352) | applies | eslint.config.js uses tseslint.configs.recommended, not recommendedTypeChecked |
| typed-route-links (WADV205) | applies | paths are string literals in router and anchors |
| usesyncexternalstore-for-subscriptions (WADV161) | applies | useSession subscribes to the storage event with useState plus useEffect |
| csp-inline (WADV019) | partial | no CSP meta or header visible in the web tree; the Python server sets headers (out of scope here) |
| effect-fetch-no-cleanup (WADV013) | partial | requestJson has no AbortSignal or timeout (frob:todo T-0102 already records it) |
| form-error-association (WADV055) | partial | field errors use aria-describedby, but no aria-invalid and the banner role=alert does not receive focus |
| live-region (WADV014) | partial | role=alert banner present; success state replaces the page content without a live region |
| swallowed-error (WADV200) | partial | Header handleLogout has an intentional empty catch with a comment |
| target-size (WADV261) | partial | unstyled default inputs and buttons; sizes unchecked |
| unique-id-in-component (WADV138) | partial | ids are hard-coded (login-username); fine for single-instance pages, useId when a form repeats |
| alt-text (WADV003) | n/a | no images yet |
| bundle-size-budget (WADV020) | n/a | no budget configured; small app |
| code-splitting-route (WADV006) | n/a | three routes today; becomes relevant with the queued pages (T-0032 onward) |
| conditional-hook-call (WADV059) | ok | react-hooks/rules-of-hooks is on |
| contrast-ratio (WADV074) | ok | crunk reports declared roles at AA; stress-ok and warn pairs undeclared |
| effect-missing-deps (WADV038) | ok | react-hooks/exhaustive-deps is on (plugin v5) |
| env-var-leak-client (WADV120) | n/a | no import.meta.env use in web/src |
| error-boundary-as-control-flow (WADV366) | n/a | no boundaries yet |
| focus-outline-removed (WADV056) | ok | reset.css does not remove outlines |
| form-hidden-input-trust (WADV221) | n/a | none |
| form-no-label (WADV001) | ok | every input has a label with htmlFor |
| form-validation-server-too (WADV128) | ok | server errors are mapped to fields; no client validation beyond type=email |
| heading-order (WADV029) | ok | one h1 per page |
| key-index-as-key (WADV050) | n/a | no lists yet |
| landmark (WADV121) | ok | banner, main, contentinfo present; each route renders its own main |
| lang-attr (WADV063) | ok | index.html has lang="en" |
| memo-premature (WADV009) | ok | no memo or useCallback anywhere |
| react-compiler-directive-sparingly (WADV229) | n/a | compiler not used; eslint-plugin-react-hooks is v5 so the compiler-based lints (set-state-in-effect, refs, purity) are absent |
| route-loader-vs-effect (WADV288) | n/a | no data loading yet; React Router 7 data APIs are available |
| target-blank-noopener (WADV219) | ok | no target=_blank |
| test-query-by-role (WADV072) | ok | tests already use getByRole and getByLabelText |
| test-testid-overuse (WADV201) | ok | no getByTestId |
| test-user-event (WADV137) | ok | tests use userEvent.setup() |
| toast-auto-dismiss (WADV118) | n/a | no toasts |
| todo-untracked (WADV202) | ok | frob:todo with ticket ids is used throughout |
| ts-floating-promise (WADV375) | ok-by-hand | handlers use void handleSubmit(...) explicitly; no type-aware rule enforces it |
| ts-misused-promise (WADV363) | ok-by-hand | async handlers are wrapped; nothing enforces it |
| xss-dangerouslysetinnerhtml (WADV039) | ok | not used |

Candidate additions to the consumer config that need no frob work: eslint-plugin-jsx-a11y (recommended), typescript-eslint recommendedTypeChecked or strictTypeChecked with projectService, eslint-plugin-testing-library and jest-dom, eslint-plugin-react-hooks 6 (compiler lints), eslint-plugin-import no-cycle, and an axe check in the vitest suite. Each is an existing rule found in this study; frob can bind them as [[check.tool]] stages.

### 5.4 Do not lint (judgement, contested or tool-owned)

Judgement-only canonical rules (22): progressive-enhancement-baseline, render-prop-vs-hook, optimistic-update, form-error-message-specific, spa-vs-server-rendered, manual-screenreader-test, web-component-vs-framework, test-coverage-goal, slow-connection-baseline, lint-rules-prune-style, compound-component, async-order-assumption, test-real-browser, redux-logic-in-reducers, persistent-ui-state-cookie, memo-needed-for-identity, debounce-masking-slow-render, prominent-message-over-toast, tabs-vs-links, incremental-a11y-fix, stale-a11y-workaround, component-misuse-warnings. Contested rules that should stay off or advisory: memo-premature (measure first), ts-return-type-explicit, form-double-submit (disabled-button split), css-important (proactive versus reactive), copy-paste-dup, god-component, test-one-assertion-per-test, test-coverage-goal, ts-enum (see catalogue), naming-convention. Style and formatting rules from the plugin catalogues (jsx-one-expression-per-line and similar) were not extracted; Dan Abramov's advice to prune lint rules that never caught a bug and leave formatting to Prettier applies (ow-overreacted-resilient).

### 5.5 Already in frob-v2 per this evidence (design or code)

| ADV | Canonical rule | Score | Status | frob-v2 id |
|---|---|---|---|---|
| WADV001 | form-no-label | 9.0 | designed | A11Y101-115 (ticket "A11Y101-115: non-text content, structure, forms"): form-input label association; crunk proposals A11Y001/A11Y008 |
| WADV004 | icon-button-name | 7.5 | designed | A11Y101-115 (ticket "A11Y101-115: non-text content, structure, forms"): link and button accessible names; crunk proposal A11Y001 |
| WADV003 | alt-text | 7.5 | designed | A11Y101-115 (ticket "A11Y101-115: non-text content, structure, forms"): alt on img and svg role=img; crunk proposal A11Y007 |
| WADV018 | secrets-in-bundle | 5.5 | designed | WEBSEC310-317 (secrets in front-end bundles; shares secret-pattern table with SEC001-003) |
| WADV022 | csrf-token | 5.0 | designed | WEBSEC201-208 (missing CSRF middleware, state-changing GET) |
| WADV020 | bundle-size-budget | 5.0 | designed | WEBPERF101-108 (ticket "Core Web Vitals causes in markup"): bundle-budget config assertion |
| WADV021 | eval-like | 5.0 | designed | WEBSEC109-116 (eval/exec/new Function) |
| WADV019 | csp-inline | 5.0 | designed | WEBSEC301-309 (CSP with nonce) |
| WADV023 | tabindex-positive | 5.0 | designed | A11Y116-128 (ticket "keyboard, focus, target size, motion") |
| WADV028 | render-blocking-script | 4.5 | designed | WEBPERF101-108 (ticket "Core Web Vitals causes in markup"): defer/async on head scripts |
| WADV029 | heading-order | 4.5 | designed | A11Y101-115 (ticket "A11Y101-115: non-text content, structure, forms"): heading order and single h1; crunk proposal A11Y002 |
| WADV033 | form-autocomplete-attr | 4.25 | designed | A11Y101-115 (ticket "A11Y101-115: non-text content, structure, forms"): autocomplete on identity fields (SC 1.3.5) |
| WADV039 | xss-dangerouslysetinnerhtml | 4.0 | designed | WEBSEC102/WEBSEC103 (innerHTML family, dangerouslySetInnerHTML) |
| WADV037 | test-a11y-axe | 4.0 | designed | A11Y T3: axe-core and keyboard focus replay through Playwright (ticket) |
| WADV042 | asset-fingerprint-long-cache | 4.0 | designed | WEBPERF109-115 (ticket "server/network performance config"): Cache-Control on hashed assets |
| WADV054 | cookie-flags | 3.5 | designed | WEBSEC201-208 (SameSite cookie default, session config) |
| WADV063 | lang-attr | 3.5 | designed | A11Y104 (html lang); crunk proposal A11Y010 |
| WADV056 | focus-outline-removed | 3.5 | designed | A11Y116-128 (ticket "keyboard, focus, target size, motion"): focus-visible not suppressed (needs CSS grammar); crunk proposal A11Y004 |
| WADV053 | lazy-load-below-fold | 3.5 | designed | WEBPERF101-108 (ticket "Core Web Vitals causes in markup"): loading=lazy |
| WADV095 | barrel-import-cycle | 3.0 | implemented | CYCLE001 (import cycles, universal) |
| WADV073 | aria-hidden-focusable | 3.0 | designed | A11Y116-128 (ticket "keyboard, focus, target size, motion") |
| WADV074 | contrast-ratio | 3.0 | designed | crunk CONTRAST001 (declared role pairs; catalogued in crunk-spec, rule not yet in crunk-check); A11Y129-135 (ticket "redundant entry, accessible authentication, contrast") for literal pairs; CONTRAST003 rendered (proposed) |
| WADV069 | skip-link | 3.0 | designed | A11Y116-128 (ticket "keyboard, focus, target size, motion"): skip link SC 2.4.1 |
| WADV105 | xss-url-scheme | 3.0 | designed | language-engines.md s3 names href="javascript:" as a sink; WEBSEC117 URL-building injection adjacent |
| WADV082 | media-captions | 3.0 | designed | A11Y116-128 (ticket "keyboard, focus, target size, motion"): video without captions track |
| WADV081 | css-naming-convention | 3.0 | designed | crunk ORG001-005 (class_case, component_prefix; catalogued, not yet implemented in Rust) |
| WADV152 | autoplay | 2.0 | designed | A11Y116-128 (ticket "keyboard, focus, target size, motion"): autoplay media without controls |
| WADV145 | image-dimensions-cls | 2.0 | designed | WEBPERF101-108 (ticket "Core Web Vitals causes in markup"): img width/height |
| WADV141 | css-animate-transform | 2.0 | designed | crunk MOTION005 (animation of layout properties, proposed) |
| WADV157 | motion-reduced | 2.0 | designed | A11Y116-128 (ticket "keyboard, focus, target size, motion"): prefers-reduced-motion; crunk MOTION002/A11Y006 |
| WADV144 | hardcoded-strings-i18n | 2.0 | designed | crunk CONTENT001 (literal strings in scenes) and I18N002 (proposed) |
| WADV135 | cache-control-html-revalidate | 2.0 | designed | WEBPERF109-115 (ticket "server/network performance config"): Cache-Control; WEBSEC309 |
| WADV155 | eslint-disable-abuse | 2.0 | designed | EXC017 (native suppression of a bound-tool rule needs a frob exception) |
| WADV202 | todo-untracked | 1.5 | implemented | TODO001/TODO002 |
| WADV219 | target-blank-noopener | 1.5 | designed | language-engines.md s3 names target=_blank without rel as a grimble-websec sink; no WEBSEC id |
| WADV194 | fn-length | 1.5 | implemented | NEAT001 (function length; bound tool) plus universal implementation |
| WADV237 | css-physical-vs-logical | 1.0 | designed | crunk I18N001 (physical left/right, proposed) |
| WADV261 | target-size | 1.0 | designed | A11Y116-128 (ticket "keyboard, focus, target size, motion"): target size; crunk LAYOUT006 (layout tier) |

(38 multi-voice canonical rules map to a ticketed or implemented frob-v2 id; the practitioner evidence supports those designs, notably alt text, label association, heading order, focus visibility, skip links, target size, reduced motion, CSP/CSRF/cookies/secrets, image dimensions, lazy loading, defer/async and font-display.)

### 5.6 Meta-advice for how to run these lints

- Zakas (ESLint origin story): regex-over-source linters are fragile; use the AST, make every rule a pluggable unit with its own test, and give each rule off, warning or error; project-specific bans (a native API replaced by an in-house wrapper) are a first-class use. This is the frob policy-rule (POL) use case; the web equivalent is a restricted-imports or restricted-syntax rule per project.
- typescript-eslint docs: recommended is reserved for near-certain bugs so it can be dropped in without configuration; type-aware rules cost as much as type checking, so scope the project service to the linted folders and split complex types; scope rule sets with files globs; one installed version only. Implication: bind type-aware ESLint rules in a separate, slower stage, never in the 2 s check budget.
- 94 of the 249 rule docs carry a When-Not-To-Use-It section (the rule exists but the maintainers tell you when to switch it off): ship web rules with a stated opt-out condition, and make waivers carry a reason (frob already does).
- Dan Abramov (Writing Resilient Components): review lint rules periodically and disable those that never caught a bug; use the linter for bugs, Prettier for style.
- Kent C. Dodds and Testing Library: pair test lint plugins with the test library; a11y smoke tests (axe) belong in the test suite, not in a static pass.

### 5.7 Suggested family map for web engineering lints

| Topic | Canonical rules | Suggested family and pack | Notes |
|---|---|---|---|
| a11y | 79 | A11Y (crunk-web) | 24 have a verified existing rule (bind); 47 lintable without one (own candidates) |
| typescript | 37 | TS (bind typescript-eslint) | 24 have a verified existing rule (bind); 13 lintable without one (own candidates) |
| css | 36 | WCSS (new, crunk) + TOKEN/ORG/TW | 16 have a verified existing rule (bind); 19 lintable without one (own candidates) |
| react-render | 32 | REACT (new grimble pack) | 19 have a verified existing rule (bind); 13 lintable without one (own candidates) |
| security | 29 | WEBSEC (grimble-websec) | 6 have a verified existing rule (bind); 19 lintable without one (own candidates) |
| perf | 25 | WEBPERF (crunk-web markup/assets; grimble-websec server) | 0 have a verified existing rule (bind); 17 lintable without one (own candidates) |
| architecture | 24 | ARCH/NEAT (universal) | 9 have a verified existing rule (bind); 9 lintable without one (own candidates) |
| state | 24 | REACT (new grimble pack) | 3 have a verified existing rule (bind); 19 lintable without one (own candidates) |
| testing | 22 | TEST (universal) + WTEST (new) | 15 have a verified existing rule (bind); 4 lintable without one (own candidates) |
| other | 22 | NEAT (universal) | 18 have a verified existing rule (bind); 2 lintable without one (own candidates) |
| react-hooks | 20 | REACT (new grimble pack) | 7 have a verified existing rule (bind); 13 lintable without one (own candidates) |
| forms | 17 | FORM (new) over A11Y | 3 have a verified existing rule (bind); 13 lintable without one (own candidates) |
| data-fetching | 16 | REACT/DATA (new grimble pack) | 8 have a verified existing rule (bind); 7 lintable without one (own candidates) |
| build | 14 | WBUILD (new, small) | 1 have a verified existing rule (bind); 10 lintable without one (own candidates) |
| routing | 5 | ROUTE (grimble-websec) | 0 have a verified existing rule (bind); 5 lintable without one (own candidates) |
| i18n | 1 | I18N (crunk) | 1 have a verified existing rule (bind); 0 lintable without one (own candidates) |

## 6. Advice catalogue (403 normalised rules; WADV ids ordered by score)

Each row merges the raw items listed in the last column count (raw items 1981 in total). Voices column: F voices / O / C; ESLint = verified rule(s), ? = merely mentioned by an extractor; Cov = frob-v2 coverage; Cons = project-hullbreach applicability.

| ADV | Canonical | Rule statement | Topic | Tier | Lint | F/O/C | Score | Raw items | ESLint-family | Cov | Cons |
|---|---|---|---|---|---|---|---|---|---|---|---|
| WADV001 | form-no-label | Flag a form control without a programmatically associated visible label, or a label hidden with display none. | forms | syntax | yes | 9/0/2 | 9.0 | 19 | jsx-a11y/label-has-associated-control | designed | ok |
| WADV002 | effect-for-derived-state | Flag a useEffect whose body only derives state from props or other state and calls a setter. | react-hooks | structural | yes | 8/0/0 | 8.0 | 14 | react-hooks/set-state-in-effect | none | - |
| WADV003 | alt-text | Flag an img, area, input type image, svg or iframe lacking an alt or accessible name, or a decorative image without empty alt. | a11y | syntax | yes | 8/0/0 | 7.5 | 18 | jsx-a11y/alt-text, jsx-a11y/iframe-has-title, jsx-a11y/img-redundant-alt | designed | n/a |
| WADV004 | icon-button-name | Flag a button or link containing only an icon or svg with no accessible name. | a11y | syntax | yes | 7/0/1 | 7.5 | 11 | jsx-a11y/alt-text, jsx-a11y/anchor-has-content, jsx-a11y/control-has-associated-label | designed | - |
| WADV005 | button-vs-link | Flag navigation implemented as a button with onClick, or an anchor without a real href used as an action. | a11y | syntax | yes | 7/0/0 | 7.0 | 16 | jsx-a11y/anchor-is-valid, jsx-a11y/no-static-element-interactions | partial | applies |
| WADV006 | code-splitting-route | Flag a route component, heavy dependency or lazy boundary imported eagerly in the main bundle without dynamic import. | perf | structural | partial | 7/0/0 | 7.0 | 13 | - | none | n/a |
| WADV007 | aria-first-rule | Flag a div or span given an ARIA role to imitate a native element that exists, such as button, link, list or heading. | a11y | syntax | partial | 7/0/1 | 6.5 | 20 | jsx-a11y/aria-role, jsx-a11y/no-interactive-element-to-noninteractive-role, jsx-a11y/prefer-tag-over-role | none | - |
| WADV008 | stale-closure | Flag a callback or effect reading state captured from an earlier render, such as logging state right after its setter or a stale timer value. | react-hooks | structural | partial | 7/1/0 | 6.5 | 11 | react-hooks/exhaustive-deps, react/no-access-state-in-setstate | none | - |
| WADV009 | memo-premature | Flag blanket memo, useMemo, useCallback or shouldComponentUpdate with no measured render cost or stable-props justification. | react-render | structural | partial | 5/1/2 | 6.0 | 21 | react-hooks/preserve-manual-memoization, react-hooks/use-memo, react/require-optimization | none | ok |
| WADV010 | test-isolation | Flag tests sharing mutable state, leaking mock handlers between tests, or lacking per-test client reset and retry-off configuration. | testing | syntax | partial | 6/0/0 | 6.0 | 19 | jest/no-mocks-import, jest/no-standalone-expect, testing-library/no-manual-cleanup | none | - |
| WADV011 | fetch-in-effect-vs-query-lib | Flag hand-written fetch with effect and manual loading state, thunks or reducers where a query library or router loader is available. | data-fetching | structural | partial | 6/0/0 | 6.0 | 11 | react-hooks/exhaustive-deps | none | - |
| WADV012 | modal-focus-trap | Flag a modal or portal dialog that does not trap focus, restore it on close or lock background scrolling and inertness. | a11y | effects | partial | 6/0/0 | 6.0 | 10 | - | partial | - |
| WADV013 | effect-fetch-no-cleanup | Flag an effect that starts a request, timer or subscription without returning a cleanup or abort. | react-hooks | syntax | yes | 6/0/0 | 6.0 | 7 | - | none | partial |
| WADV014 | live-region | Flag dynamic status, error or result-count updates not announced through a role status or aria-live region, or a live region mounted with its content. | a11y | syntax | partial | 6/0/1 | 5.75 | 27 | - | partial | partial |
| WADV015 | aria-redundant-role | Flag a role or aria attribute that duplicates the native semantics of the element, or role none misused, or aria-roledescription. | a11y | syntax | yes | 4/0/3 | 5.5 | 18 | jsx-a11y/no-interactive-element-to-noninteractive-role, jsx-a11y/no-redundant-roles, jsx-a11y/prefer-tag-over-role | partial | - |
| WADV016 | role-without-keyboard | Flag an element given an interactive role without matching tabindex and key handlers. | a11y | syntax | yes | 5/0/1 | 5.5 | 14 | jsx-a11y/click-events-have-key-events, jsx-a11y/interactive-supports-focus, jsx-a11y/no-static-element-interactions | partial | - |
| WADV017 | state-derived-in-state | Flag a state variable that stores a value derivable from other state or props, or an unused state definition. | state | structural | partial | 5/0/1 | 5.5 | 8 | react/no-unused-state | none | - |
| WADV018 | secrets-in-bundle | Flag secrets, source maps, stack traces or sensitive inputs exposed to client bundles, logs or error responses. | security | structural | partial | 5/0/1 | 5.5 | 6 | - | designed | - |
| WADV019 | csp-inline | Flag inline scripts or styles, unsafe-inline, nonce allowlist bypass patterns or meta-delivered CSP where a header is required. | security | render | partial | 4/0/2 | 5.0 | 21 | - | designed | partial |
| WADV020 | bundle-size-budget | Flag a build whose shipped JavaScript or CSS bytes exceed the configured budget. | perf | render | yes | 5/0/0 | 5.0 | 18 | - | designed | n/a |
| WADV021 | eval-like | Flag eval, new Function, string arguments to setTimeout or setInterval, and dynamic script or worker URLs. | security | syntax | yes | 4/0/2 | 5.0 | 11 | @typescript-eslint/no-implied-eval, no-eval, no-implied-eval | designed | - |
| WADV022 | csrf-token | Flag a state-changing operation reachable by GET or a loader, or a mutating request without CSRF protection. | security | structural | partial | 5/0/0 | 5.0 | 10 | - | designed | - |
| WADV023 | tabindex-positive | Flag a tabindex attribute with a value greater than zero. | a11y | syntax | yes | 5/0/0 | 5.0 | 7 | jsx-a11y/no-noninteractive-tabindex, jsx-a11y/tabindex-no-positive | designed | - |
| WADV024 | dead-code | Flag unused exports, unreachable branches and option combinations nothing exercises. | architecture | structural | yes | 5/0/0 | 5.0 | 5 | @typescript-eslint/no-unused-vars, import/no-unused-modules, no-unused-vars | partial | - |
| WADV025 | css-specificity-wars | Flag long descendant or qualified selectors, context overrides or undo declarations used to beat specificity. | css | syntax | partial | 6/0/0 | 4.5 | 22 | stylelint/no-descending-specificity, stylelint/selector-max-compound-selectors, stylelint/selector-max-specificity | none | - |
| WADV026 | aria-label-misuse | Flag aria-label on an element that has visible text, or an aria-label used where a visible label element would work. | a11y | syntax | yes | 5/0/1 | 4.5 | 21 | jsx-a11y/aria-role | none | - |
| WADV027 | progressive-enhancement-baseline | Flag a feature that needs JavaScript for basic function, with no native form, link or select baseline. | architecture | human | no | 6/0/0 | 4.5 | 20 | - | none | - |
| WADV028 | render-blocking-script | Flag synchronous script tags in head, document.write, synchronous XHR or parser-blocking resources instead of module or deferred scripts. | perf | syntax | yes | 5/0/0 | 4.5 | 15 | - | designed | - |
| WADV029 | heading-order | Flag headings that skip levels or styled text standing in for a real heading element. | a11y | syntax | yes | 5/0/0 | 4.5 | 9 | - | designed | ok |
| WADV030 | inline-object-prop-rerender | Flag an object, array or arrow function literal passed as a prop to a memoized child component. | react-render | syntax | yes | 4/0/1 | 4.5 | 6 | react/jsx-no-bind, react/no-object-type-as-default-prop | none | - |
| WADV031 | css-id-selector | Flag an id selector or inline style attribute used for styling. | css | syntax | yes | 5/0/0 | 4.5 | 5 | stylelint/selector-max-id | none | - |
| WADV032 | form-native-elements | Flag form logic built on div or custom elements, missing name, novalidate misuse, form.submit instead of requestSubmit, or asterisk-only required. | forms | syntax | partial | 4/0/1 | 4.5 | 5 | - | none | - |
| WADV033 | form-autocomplete-attr | Flag an input lacking a valid autocomplete token, with incorrect inputmode or mobile font size, or blocking paste. | forms | syntax | yes | 4/0/2 | 4.25 | 11 | jsx-a11y/autocomplete-valid | designed | applies |
| WADV034 | css-global-leak | Flag unscoped global styles that leak across components or are blocked by shadow DOM boundaries. | css | structural | partial | 4/0/1 | 4.25 | 7 | - | none | - |
| WADV035 | server-client-boundary | Flag props passed from server to client components that are not serializable, or client-only APIs, hooks and handlers used in server components. | architecture | structural | yes | 4/0/0 | 4.0 | 18 | react-hooks/rules-of-hooks | partial | - |
| WADV036 | state-colocate | Flag state held in a distant ancestor or global store that only one component reads. | state | structural | partial | 4/0/0 | 4.0 | 15 | - | none | - |
| WADV037 | test-a11y-axe | Flag a test suite or page with no automated axe accessibility check, or axe violations suppressed broadly or snapshotted whole. | testing | syntax | partial | 4/0/0 | 4.0 | 15 | - | designed | applies |
| WADV038 | effect-missing-deps | Flag a hook dependency array that omits a reactive value used in the callback, or an effect with no array that resets a timer. | react-hooks | syntax | yes | 4/0/0 | 4.0 | 13 | react-hooks/exhaustive-deps | none | ok |
| WADV039 | xss-dangerouslysetinnerhtml | Flag dangerouslySetInnerHTML, innerHTML, v-html or other raw HTML sinks fed with non-constant data. | security | syntax | yes | 3/0/2 | 4.0 | 13 | react/no-danger, react/no-danger-with-children | designed | ok |
| WADV040 | error-boundary-missing | Flag a route or independently failing subtree with no error boundary above it. | react-render | structural | partial | 4/0/0 | 4.0 | 12 | react-hooks/error-boundaries | partial | applies |
| WADV041 | mutate-state-directly | Flag in-place mutation of state, props or reducer input, such as push on a state array, outside an immutable-update helper. | state | syntax | partial | 4/0/0 | 4.0 | 12 | react-hooks/immutability, react/no-direct-mutation-state | none | - |
| WADV042 | asset-fingerprint-long-cache | Flag static assets served without content-hashed filenames, self-hosting, or long-lived immutable Cache-Control. | build | structural | partial | 4/0/0 | 4.0 | 9 | - | designed | - |
| WADV043 | test-await-async | Flag an async assertion not awaited, or a done callback used instead of promises or await. | testing | syntax | yes | 4/0/0 | 4.0 | 9 | jest/no-done-callback, testing-library/await-async-events, testing-library/await-async-queries | none | - |
| WADV044 | div-onclick | Flag a click, keydown or mouse handler on a non-interactive element such as div or span. | a11y | syntax | yes | 4/0/1 | 4.0 | 8 | jsx-a11y/click-events-have-key-events, jsx-a11y/no-noninteractive-element-interactions, jsx-a11y/no-static-element-interactions | partial | - |
| WADV045 | focus-management-route-change | Flag a route change, dialog close, rerender or toast action that drops keyboard focus instead of moving or restoring it. | a11y | effects | partial | 5/0/0 | 4.0 | 7 | - | partial | applies |
| WADV046 | button-type-attr | Flag a button inside a form without an explicit type, or a page with several primary submit buttons. | forms | syntax | yes | 4/0/0 | 4.0 | 5 | react/button-has-type | none | - |
| WADV047 | mutable-export | Flag mutable exports, wildcard imports, default exports, imports with wrong path case, or exports not needed outside the module. | architecture | syntax | yes | 4/0/0 | 4.0 | 5 | import/no-default-export, import/no-mutable-exports | none | - |
| WADV048 | render-purity | Flag side effects, mutation of outer variables or nondeterministic calls inside a component render body. | react-render | effects | partial | 4/0/0 | 4.0 | 5 | react-hooks/globals, react-hooks/purity, react-hooks/rules-of-hooks | none | - |
| WADV049 | controlled-uncontrolled-switch | Flag an input or component that switches between controlled and uncontrolled, or mirrors a prop in state and also edits it. | state | structural | partial | 4/0/0 | 4.0 | 4 | react/checked-requires-onchange-or-readonly | none | - |
| WADV050 | key-index-as-key | Flag an array index used as the key of a list item. | react-render | syntax | yes | 4/0/0 | 4.0 | 4 | react/no-array-index-key | none | n/a |
| WADV051 | css-important | Flag any !important declaration outside designated utility classes. | css | syntax | yes | 3/0/3 | 3.75 | 6 | stylelint/declaration-no-important | none | - |
| WADV052 | render-prop-vs-hook | Flag duplicated subscription or stateful logic across components that should be extracted into a custom hook. | architecture | human | no | 3/0/1 | 3.5 | 12 | ?vue/no-mixin | none | - |
| WADV053 | lazy-load-below-fold | Flag loading lazy on images likely to appear in the first viewport, or missing loading lazy on below-fold images. | perf | syntax | partial | 3/0/1 | 3.5 | 11 | - | designed | - |
| WADV054 | cookie-flags | Flag session cookies lacking httpOnly, secure or sameSite, using a static expires date, or unsigned auth cookies. | security | syntax | yes | 3/0/1 | 3.5 | 10 | - | designed | - |
| WADV055 | form-error-association | Flag an input whose error or hint message is not linked by aria-describedby, or a hardcoded id duplicated across instances. | forms | syntax | yes | 4/0/0 | 3.5 | 10 | ?jsx-a11y/aria-proptypes | none | partial |
| WADV056 | focus-outline-removed | Flag outline none or outline 0 on focusable elements without a replacement indicator of adequate contrast. | a11y | syntax | yes | 4/0/0 | 3.5 | 8 | - | designed | ok |
| WADV057 | js-narrow-scope | Flag variables declared in a wider scope than needed, shadowed variables, var, or let that is never reassigned. | other | syntax | yes | 3/0/1 | 3.5 | 8 | @typescript-eslint/no-shadow, no-shadow, prefer-const | none | - |
| WADV058 | page-title-spa | Flag a route that does not update document.title on navigation, or duplicate or missing page titles. | a11y | effects | partial | 5/0/0 | 3.5 | 8 | - | partial | applies |
| WADV059 | conditional-hook-call | Flag a hook called inside a condition, loop, early-return path or nested function. | react-hooks | syntax | yes | 3/0/1 | 3.5 | 7 | react-hooks/rules-of-hooks | none | ok |
| WADV060 | dom-order-matches-visual | Flag DOM order or positive tabindex that diverges from visual reading order, such as CSS order or absolute positioning. | a11y | render | partial | 3/0/2 | 3.5 | 7 | - | none | - |
| WADV061 | key-reset-state | Flag state reset implemented by effects or prop comparison where a key on the component would reset it. | state | structural | partial | 3/0/1 | 3.5 | 7 | ?react/no-unsafe | none | - |
| WADV062 | hover-only-interaction | Flag a :hover rule or mouseenter handler with no corresponding focus style or keyboard equivalent. | a11y | syntax | partial | 4/0/0 | 3.5 | 6 | jsx-a11y/mouse-events-have-key-events | partial | - |
| WADV063 | lang-attr | Flag an html element lacking a valid lang attribute. | a11y | syntax | yes | 4/0/0 | 3.5 | 6 | jsx-a11y/html-has-lang, jsx-a11y/lang | designed | ok |
| WADV064 | ts-import-type | Flag a type-only import not using import type, or a value import of a server module only for its types. | typescript | syntax | yes | 4/0/0 | 3.5 | 6 | @typescript-eslint/consistent-type-imports, @typescript-eslint/no-import-type-side-effects | none | - |
| WADV065 | js-no-loops | Flag for-in, for-of or await-in-loop and closures created in loops where array methods or parallel awaits are expected. | other | syntax | yes | 3/0/1 | 3.5 | 5 | @typescript-eslint/no-for-in-array, no-await-in-loop, no-loop-func | none | - |
| WADV066 | css-dead-code | Flag CSS rules and utility classes that no markup uses. | css | render | partial | 4/0/0 | 3.5 | 4 | - | none | - |
| WADV067 | css-custom-property-tokens | Flag hard-coded colour, spacing or font literals repeated across rules instead of custom property tokens. | css | syntax | partial | 4/0/0 | 3.0 | 21 | stylelint/no-unknown-custom-properties | partial | - |
| WADV068 | test-flaky-wait | Flag waitFor with an empty callback, side effects or multiple assertions inside it, or fixed sleeps. | testing | syntax | yes | 3/0/0 | 3.0 | 16 | testing-library/no-wait-for-multiple-assertions, testing-library/no-wait-for-side-effects, testing-library/prefer-find-by | none | - |
| WADV069 | skip-link | Flag a page lacking a skip link to main content, or one hidden without becoming visible on focus or targeting a non-focusable element. | a11y | structural | partial | 3/1/0 | 3.0 | 14 | - | designed | applies |
| WADV070 | js-case-declarations | Flag small control-flow hygiene issues: lexical declarations in case clauses, empty blocks, else after return, constant conditions, comma operators, missing curly braces. | other | syntax | yes | 3/0/0 | 3.0 | 12 | array-callback-return, default-case-last, no-constant-condition | none | - |
| WADV071 | test-implementation-details | Flag a test asserting on state, instance methods, call counts or internals rather than user-visible output. | testing | syntax | partial | 3/0/0 | 3.0 | 12 | testing-library/no-container, testing-library/no-node-access | none | - |
| WADV072 | test-query-by-role | Flag a Testing Library query by class, selector or test id where getByRole with name would work. | testing | syntax | yes | 3/0/0 | 3.0 | 9 | testing-library/prefer-find-by, testing-library/prefer-presence-queries, testing-library/prefer-screen-queries | none | ok |
| WADV073 | aria-hidden-focusable | Flag an aria-hidden element that contains or is itself focusable (link, button, input, positive or zero tabindex). | a11y | syntax | yes | 3/0/0 | 3.0 | 8 | jsx-a11y/no-aria-hidden-on-focusable | designed | - |
| WADV074 | contrast-ratio | Flag text or UI component colours whose computed contrast ratio is below WCAG AA thresholds. | a11y | render | yes | 3/0/0 | 3.0 | 8 | - | designed | ok |
| WADV075 | link-text-unique | Flag links or buttons with identical or non-descriptive text such as read more, click here, without a distinguishing accessible name. | a11y | syntax | partial | 4/0/0 | 3.0 | 8 | jsx-a11y/anchor-ambiguous-text, jsx-a11y/anchor-has-content | partial | - |
| WADV076 | preload-misuse | Flag preload, preconnect or speculation-rules entries for resources that are unused or too broad. | perf | syntax | partial | 3/0/0 | 3.0 | 8 | - | none | - |
| WADV077 | state-duplicated-source-of-truth | Flag server or prop data copied into local state that then diverges from its source. | state | structural | partial | 2/0/2 | 3.0 | 8 | - | none | - |
| WADV078 | third-party-cost | Flag duplicate or redundant third-party providers, embeds and scripts that add load cost. | perf | structural | partial | 3/0/0 | 3.0 | 7 | - | none | - |
| WADV079 | use-client-too-high | Flag a use client directive on a large module or layout whose subtree is mostly non-interactive, or heavy hydration directives. | perf | structural | partial | 3/0/0 | 3.0 | 7 | - | partial | - |
| WADV080 | css-magic-number | Flag unexplained numeric spacing, size or offset literals not derived from tokens or the type scale. | css | syntax | partial | 4/0/0 | 3.0 | 6 | react/forbid-dom-props | partial | - |
| WADV081 | css-naming-convention | Flag class names that do not follow the project convention, such as state classes lacking an is- or has- prefix. | css | syntax | yes | 3/0/0 | 3.0 | 6 | stylelint/selector-class-pattern | designed | - |
| WADV082 | media-captions | Flag video without a captions track, audio without transcript, custom controls without keyboard support or missing media fallback. | a11y | syntax | partial | 3/0/0 | 3.0 | 6 | jsx-a11y/media-has-caption | designed | - |
| WADV083 | suspense-boundary | Flag a Suspense-using component or lazy component with no Suspense boundary, or fetches started inside the boundary instead of before render. | data-fetching | structural | partial | 3/0/0 | 3.0 | 6 | - | none | - |
| WADV084 | upload-validate-server | Flag a file upload handler trusting client Content-Type or extension, lacking size limits or rate limits. | security | structural | partial | 3/0/0 | 3.0 | 6 | - | none | - |
| WADV085 | async-race-condition | Flag an async fetch in an effect or handler that sets state without cancellation, abort or a stale-response guard. | data-fetching | structural | partial | 3/0/0 | 3.0 | 5 | react-hooks/exhaustive-deps, require-atomic-updates | none | - |
| WADV086 | component-defined-inside-component | Flag a component, or lazy component, declared inside another component's body. | react-render | syntax | yes | 3/0/0 | 3.0 | 5 | react-hooks/component-hook-factories, react-hooks/static-components, react/no-unstable-nested-components | none | - |
| WADV087 | copy-paste-dup | Flag near-identical code blocks duplicated across files or branches. | architecture | structural | partial | 3/1/0 | 3.0 | 5 | - | partial | - |
| WADV088 | custom-widget-aria-state | Flag a custom widget with ARIA role but missing aria-expanded, aria-haspopup, aria-selected or matching keyboard handling. | a11y | syntax | partial | 4/0/0 | 3.0 | 5 | - | none | - |
| WADV089 | effect-object-dep-unstable | Flag an object, array or function created in render and listed in an effect or memo dependency array. | react-hooks | syntax | yes | 3/0/0 | 3.0 | 5 | @tanstack/query/no-unstable-deps, react-hooks/exhaustive-deps | none | - |
| WADV090 | lint-no-restricted-syntax | Flag usage of banned globals, DOM props, in-house wrapper bypasses or syntax patterns declared in no-restricted-syntax. | other | syntax | yes | 3/0/0 | 3.0 | 5 | no-restricted-globals, react/forbid-dom-props | none | - |
| WADV091 | prop-drilling-vs-context | Flag a prop forwarded unchanged through several intermediate components that never use it. | state | structural | partial | 2/0/2 | 3.0 | 5 | - | none | - |
| WADV092 | table-semantics | Flag a data table lacking th header cells with scope or headers association, or layout tables with table semantics. | a11y | syntax | partial | 3/0/0 | 3.0 | 5 | jsx-a11y/scope | none | - |
| WADV093 | tsconfig-include-exclude | Flag tsconfig include globs that sweep build output or node_modules, unset types, or missing env typings such as vite/client. | build | syntax | yes | 3/0/0 | 3.0 | 5 | - | none | - |
| WADV094 | xss-output-encoding | Flag untrusted text inserted into HTML, attribute or script context without context-appropriate encoding. | security | syntax | partial | 3/0/0 | 3.0 | 5 | - | partial | - |
| WADV095 | barrel-import-cycle | Flag a circular import chain, including a module that imports the global store or app singleton directly. | architecture | structural | yes | 3/0/0 | 3.0 | 4 | @typescript-eslint/no-restricted-imports, import/no-cycle | implemented | - |
| WADV096 | children-as-jsx-to-avoid-rerender | Flag a stateful component that renders expensive static subtrees inline instead of receiving them as children props. | react-render | structural | partial | 3/0/0 | 3.0 | 4 | react/no-children-prop | none | - |
| WADV097 | js-no-this-alias | Flag aliasing this, getters and setters, this in function components, or sloppy-mode constructs. | other | syntax | yes | 3/0/0 | 3.0 | 4 | react/no-this-in-sfc | none | - |
| WADV098 | optimistic-update | Flag a mutation UI that waits for the server before reflecting the new value where formData can be shown optimistically. | data-fetching | human | no | 3/0/0 | 3.0 | 4 | - | none | - |
| WADV099 | tabindex-nonnegative-nonfocusable | Flag tabindex 0 on a non-interactive element such as a heading, or tabindex minus one on inactive content that should not take focus. | a11y | syntax | yes | 3/0/1 | 3.0 | 4 | jsx-a11y/no-noninteractive-tabindex | none | - |
| WADV100 | usecallback-without-memo | Flag a useCallback or useMemo whose result is passed only to non-memoized children or DOM elements. | react-render | structural | partial | 3/0/0 | 3.0 | 4 | react-hooks/exhaustive-deps | none | - |
| WADV101 | fieldset-legend-group | Flag a group of related radio, checkbox or inputs lacking a fieldset with legend. | forms | syntax | yes | 3/0/0 | 3.0 | 3 | - | none | - |
| WADV102 | form-placeholder-as-label | Flag an input that has a placeholder but no associated label. | forms | syntax | yes | 3/0/0 | 3.0 | 3 | - | none | - |
| WADV103 | memo-custom-comparator | Flag a memo comparator that ignores props such as callbacks or deep-compares large structures. | react-render | syntax | partial | 3/0/0 | 3.0 | 3 | - | none | - |
| WADV104 | sanitize-with-library | Flag ad hoc HTML escaping or sanitising instead of a vetted sanitiser such as DOMPurify. | security | syntax | partial | 3/0/0 | 3.0 | 3 | - | none | - |
| WADV105 | xss-url-scheme | Flag a user-controlled URL used in href or src without validating its scheme against an allowlist. | security | syntax | yes | 3/0/0 | 3.0 | 3 | no-script-url, react/jsx-no-script-url | designed | - |
| WADV106 | long-task-yield | Flag long synchronous main-thread work that never yields, where a worker, scheduler or chunking is warranted. | perf | effects | partial | 2/0/1 | 2.5 | 9 | - | none | - |
| WADV107 | invalid-html-nesting | Flag invalid HTML nesting or markup misuse: div in p, tr outside table, void element children, obsolete elements, bad attributes, entities. | react-render | syntax | yes | 2/0/1 | 2.5 | 8 | react/jsx-no-useless-fragment, react/no-invalid-html-attribute, react/no-unescaped-entities | none | - |
| WADV108 | test-one-assertion-per-test | Flag many tiny one-assertion tests splitting a single workflow, or tests with conditional expects, no assertions or soft assertions. | testing | syntax | partial | 2/0/1 | 2.5 | 7 | jest/expect-expect, jest/no-conditional-expect, jest/no-conditional-in-test | none | - |
| WADV109 | error-not-color-only | Flag an error message that is conveyed by colour alone or lacks an Error text prefix or error-message element semantics. | a11y | syntax | partial | 3/0/0 | 2.5 | 6 | - | none | - |
| WADV110 | test-act-warning | Flag unnecessary act wrappers around render or fireEvent, or a test finishing before async updates settle. | testing | syntax | partial | 2/0/1 | 2.5 | 6 | testing-library/no-unnecessary-act | none | - |
| WADV111 | ts-readonly | Flag mutable parameter, property or array types for data that should be read-only. | typescript | types | partial | 2/0/1 | 2.5 | 6 | @typescript-eslint/prefer-readonly, @typescript-eslint/prefer-readonly-parameter-types, react/prefer-read-only-props | none | - |
| WADV112 | keyboard-operable | Flag interactive UI not operable by keyboard: handlers that need a mouse, nested focusables, blur-closing popups or raw keyCode checks. | a11y | syntax | partial | 3/0/0 | 2.5 | 5 | - | none | - |
| WADV113 | naming-convention | Flag identifiers violating naming rules, such as hook state setter mismatch, handler names, I-prefixed interfaces or unclear names. | other | syntax | yes | 1/0/3 | 2.5 | 5 | @typescript-eslint/naming-convention, react/hook-use-state, react/jsx-handler-names | none | - |
| WADV114 | css-px-vs-rem | Flag font sizes and spacing set in px instead of rem or em. | css | syntax | yes | 3/0/0 | 2.5 | 4 | stylelint/unit-disallowed-list | partial | - |
| WADV115 | loose-equality | Flag == and != comparisons, null comparisons that need explicit handling, and typeof x object used as a null check. | other | syntax | yes | 2/0/1 | 2.5 | 4 | eqeqeq | none | - |
| WADV116 | viewport-no-zoom | Flag a meta viewport that disables zoom with user-scalable no or maximum-scale 1, or omits width=device-width. | a11y | syntax | yes | 3/0/0 | 2.5 | 4 | - | none | - |
| WADV117 | ts-any | Flag an explicit or implicit any type, an unsafe any return or assignment, or unknown used where a generic would preserve the type. | typescript | types | yes | 2/0/1 | 2.25 | 14 | @typescript-eslint/no-explicit-any, @typescript-eslint/no-unsafe-argument, @typescript-eslint/no-unsafe-assignment | none | - |
| WADV118 | toast-auto-dismiss | Flag a toast that auto-dismisses without the same information being available elsewhere, or that obscures content. | a11y | syntax | partial | 2/0/2 | 2.25 | 9 | - | none | n/a |
| WADV119 | ts-assertion-as | Flag a type assertion with as (or angle brackets in tsx) that is not narrowing or is applied to widen or cast through any. | typescript | types | yes | 2/0/1 | 2.25 | 7 | @typescript-eslint/consistent-type-assertions, @typescript-eslint/no-unnecessary-type-assertion, @typescript-eslint/no-unsafe-type-assertion | none | applies |
| WADV120 | env-var-leak-client | Flag a secret environment variable referenced from client code, or a client variable read via dynamic lookup that bundlers cannot inline. | security | syntax | yes | 2/0/0 | 2.0 | 12 | - | partial | n/a |
| WADV121 | landmark | Flag page content outside landmarks, or sections used as landmarks without an accessible name. | a11y | syntax | partial | 2/0/0 | 2.0 | 11 | - | partial | ok |
| WADV122 | test-mock-fetch-network-level | Flag jest.mock of an API client or fetch stub in component tests instead of network-level interception. | testing | syntax | yes | 2/1/0 | 2.0 | 10 | jest/no-mocks-import | none | - |
| WADV123 | css-invalid-value | Flag unknown property values, invalid at-rule position, scheme-relative URLs, units on zero, border none or missing generic font family. | css | syntax | yes | 2/0/0 | 2.0 | 8 | stylelint/color-named, stylelint/declaration-property-value-no-unknown, stylelint/font-family-no-missing-generic-family-keyword | none | - |
| WADV124 | css-media-vs-container | Flag media queries keyed to device widths where a container query or content-based breakpoint is appropriate. | css | syntax | partial | 3/0/0 | 2.0 | 8 | - | none | - |
| WADV125 | test-snapshot-large | Flag a large snapshot of a whole object or violations array. | testing | syntax | yes | 2/0/0 | 2.0 | 8 | jest/no-interpolation-in-snapshots, jest/no-large-snapshots, jest/valid-title | none | - |
| WADV126 | e2e-locator-resilience | Flag e2e locators using CSS classes or XPath, or Cypress chains with then, mid-chain assertions or actions followed by chaining. | testing | syntax | yes | 2/0/0 | 2.0 | 7 | ?cypress/unsafe-to-chain-command, playwright/no-nth-methods | none | - |
| WADV127 | form-error-message-specific | Flag generic validation messages that do not say what is wrong, or form fields cleared on validation error. | forms | human | no | 2/0/0 | 2.0 | 7 | - | none | - |
| WADV128 | form-validation-server-too | Flag a mutating action or endpoint that trusts client-side validation without validating input on the server. | forms | structural | partial | 2/0/0 | 2.0 | 7 | - | none | ok |
| WADV129 | combobox-aria-contract | Flag a combobox lacking role combobox, aria-expanded, aria-controls, listbox popup or an activedescendant-based option announcement. | a11y | syntax | partial | 2/0/1 | 2.0 | 6 | - | none | - |
| WADV130 | context-value-unstable | Flag a Context.Provider whose value is an object, array or function literal created during render. | react-render | syntax | yes | 2/0/0 | 2.0 | 6 | react/jsx-no-constructed-context-values | none | - |
| WADV131 | fetchpriority-lcp | Flag an LCP image that is lazy-loaded, lacks fetchpriority high, or is combined with loading lazy and fetchpriority high. | perf | syntax | yes | 2/0/0 | 2.0 | 6 | - | none | - |
| WADV132 | server-action-authz | Flag a server action or function that mutates data without an authorization check, or that uses its arguments without validation. | security | structural | partial | 2/0/0 | 2.0 | 6 | - | partial | - |
| WADV133 | ts-generic-needless | Flag a type parameter used only once, unconstrained where members are used, or an any-typed utility that should be generic. | typescript | types | partial | 2/0/1 | 2.0 | 6 | @typescript-eslint/no-unnecessary-type-parameters | none | - |
| WADV134 | visually-hidden-technique | Flag visually hidden text using offscreen positioning like left -9999px instead of a robust clip technique, or keeping focusable content hidden. | a11y | syntax | partial | 2/0/0 | 2.0 | 6 | - | none | - |
| WADV135 | cache-control-html-revalidate | Flag HTML or unversioned URLs served without no-cache or ETag revalidation, or with a long max-age on mutable content. | build | render | partial | 2/0/0 | 2.0 | 5 | - | designed | - |
| WADV136 | feature-vs-layer-structure | Flag one feature's code split across top-level layer folders (actions, reducers, components) instead of a feature folder. | architecture | structural | partial | 2/0/0 | 2.0 | 5 | import/no-restricted-paths, react/no-multi-comp | none | - |
| WADV137 | test-user-event | Flag fireEvent used where user-event could simulate the interaction, or click tests that never exercise the wiring. | testing | syntax | yes | 2/0/0 | 2.0 | 5 | testing-library/prefer-user-event | none | ok |
| WADV138 | unique-id-in-component | Flag a hard-coded id attribute in a reusable component, or ids from counters or random values instead of useId. | a11y | syntax | yes | 2/0/0 | 2.0 | 5 | - | partial | partial |
| WADV139 | utility-dynamic-class-string | Flag a class name built by string concatenation or interpolation that utility scanners cannot detect. | css | syntax | yes | 2/0/0 | 2.0 | 5 | tailwindcss/no-custom-classname | partial | - |
| WADV140 | clickjacking-frame-ancestors | Flag responses lacking a frame-ancestors CSP or X-Frame-Options, or lacking Permissions-Policy or strict Host and CORS credential handling. | security | render | partial | 2/0/0 | 2.0 | 4 | - | partial | - |
| WADV141 | css-animate-transform | Flag CSS animation or transition of layout properties such as width, height, top or left instead of transform. | css | syntax | yes | 2/0/0 | 2.0 | 4 | - | designed | - |
| WADV142 | form-onchange-sync-everything | Flag an onSubmit handler with preventDefault that manually syncs every field to state and cache, or watches all fields, where a form action or ref reads would do. | forms | structural | partial | 2/0/0 | 2.0 | 4 | - | none | applies |
| WADV143 | form-pending-state | Flag a submit button not disabled or labelled pending while an action runs, or hand-managed isPending state replaced by useActionState or useFormStatus. | forms | syntax | partial | 1/0/2 | 2.0 | 4 | - | none | applies |
| WADV144 | hardcoded-strings-i18n | Flag a user-visible string literal in JSX or aria-label that is not routed through the translation function. | i18n | syntax | yes | 2/0/0 | 2.0 | 4 | react/jsx-no-literals | designed | applies |
| WADV145 | image-dimensions-cls | Flag an img without width and height or aspect-ratio, or dynamic content inserted without reserved space. | perf | syntax | yes | 2/0/0 | 2.0 | 4 | - | designed | - |
| WADV146 | legacy-api-findDOMNode | Flag findDOMNode, string refs, defaultProps on function components or use of an API marked deprecated. | react-render | syntax | yes | 1/0/2 | 2.0 | 4 | @typescript-eslint/no-deprecated, react/no-find-dom-node | none | - |
| WADV147 | redux-dispatch-batch | Flag a handler that dispatches several actions in sequence for one logical event, or relies on unstable_batchedUpdates. | state | structural | partial | 2/0/0 | 2.0 | 4 | - | none | - |
| WADV148 | revalidation-skip | Flag router loaders that write global state, shared flash keys read by several loaders, or revalidation not scoped to the changed data. | routing | structural | partial | 2/0/0 | 2.0 | 4 | - | none | - |
| WADV149 | timer-id-in-ref | Flag a timer id or latest-callback stored in a render-scope variable or shared module variable rather than a ref. | react-hooks | syntax | partial | 2/0/0 | 2.0 | 4 | - | none | - |
| WADV150 | url-as-state | Flag shareable view or filter state kept in component state synced to the URL instead of derived from search params. | state | structural | partial | 2/0/0 | 2.0 | 4 | - | none | - |
| WADV151 | asChild-forward-ref | Flag a component used under an asChild slot that does not forward its ref or spread received props onto the DOM node. | architecture | structural | partial | 2/0/0 | 2.0 | 3 | - | none | - |
| WADV152 | autoplay | Flag auto-advancing carousels, autoplaying media or scrolling content that has no pause or stop control. | a11y | syntax | partial | 2/0/0 | 2.0 | 3 | jsx-a11y/no-distracting-elements | designed | - |
| WADV153 | css-shorthand-override | Flag a shorthand property that overrides a longhand declared earlier in the same block. | css | syntax | yes | 2/0/0 | 2.0 | 3 | stylelint/declaration-block-no-shorthand-property-overrides | none | - |
| WADV154 | effect-chain-state | Flag a useEffect that only sets state which triggers another effect, forming a chain of state updates. | react-hooks | structural | yes | 2/0/0 | 2.0 | 3 | - | none | - |
| WADV155 | eslint-disable-abuse | Flag a disable, ts-ignore or ts-expect-error comment lacking a specific rule name and written justification. | other | syntax | yes | 2/0/0 | 2.0 | 3 | @typescript-eslint/ban-ts-comment, unicorn/no-abusive-eslint-disable | designed | - |
| WADV156 | list-virtualization | Flag rendering of hundreds or thousands of list rows into the DOM without virtualization. | perf | render | partial | 2/0/0 | 2.0 | 3 | - | none | - |
| WADV157 | motion-reduced | Flag CSS or JS animation that does not respect prefers-reduced-motion. | a11y | syntax | partial | 2/0/0 | 2.0 | 3 | jsx-a11y/no-distracting-elements | designed | - |
| WADV158 | solid-untracked-read | Flag a Solid signal read in the component body outside JSX or a reactive scope. | state | syntax | yes | 2/0/0 | 2.0 | 3 | ?solid/reactivity, svelte/no-unused-state | none | - |
| WADV159 | test-providers-wrapper | Flag rendering of a provider-dependent component or hook without a wrapper supplying its providers. | testing | syntax | partial | 2/0/0 | 2.0 | 3 | - | none | - |
| WADV160 | ts-banned-boxed-types | Flag the boxed types String, Number, Boolean, Symbol or Object in a type annotation. | typescript | syntax | yes | 2/0/0 | 2.0 | 3 | @typescript-eslint/no-wrapper-object-types | none | - |
| WADV161 | usesyncexternalstore-for-subscriptions | Flag an effect plus setState subscription to an external store or browser API instead of useSyncExternalStore. | react-hooks | structural | partial | 2/0/0 | 2.0 | 3 | - | none | applies |
| WADV162 | accesskey | Flag any accessKey or accesskey attribute on an element. | a11y | syntax | yes | 2/0/0 | 2.0 | 2 | jsx-a11y/no-access-key | none | - |
| WADV163 | autofocus | Flag the autoFocus or autofocus attribute on any element. | a11y | syntax | yes | 2/0/0 | 2.0 | 2 | jsx-a11y/no-autofocus | none | - |
| WADV164 | css-nesting-depth | Flag Sass or CSS nesting deeper than three levels. | css | syntax | yes | 2/0/0 | 2.0 | 2 | stylelint/max-nesting-depth | none | - |
| WADV165 | dependency-undeclared | Flag an import of a package not declared in package.json, or react and @types/react versions that do not match. | build | syntax | yes | 2/0/0 | 2.0 | 2 | import/no-extraneous-dependencies | none | - |
| WADV166 | form-default-values | Flag a form initialised with per-field defaults or effect-driven reset instead of defaultValues or values on the form. | forms | syntax | partial | 2/0/0 | 2.0 | 2 | - | none | - |
| WADV167 | iframe-sandbox | Flag an iframe embedding third-party content without a sandbox attribute or restricted allow policy. | security | syntax | yes | 2/0/0 | 2.0 | 2 | react/iframe-missing-sandbox | none | - |
| WADV168 | js-hook-class-separation | Flag a CSS class used both for styling and as a JavaScript behaviour hook rather than a js- prefixed class. | css | syntax | partial | 2/0/0 | 2.0 | 2 | - | none | - |
| WADV169 | nested-ternary | Flag a nested ternary expression. | other | syntax | yes | 2/0/0 | 2.0 | 2 | no-nested-ternary | none | - |
| WADV170 | open-redirect | Flag a redirect whose target comes from request input without an allowlist, including remote image URLs. | security | syntax | partial | 2/0/0 | 2.0 | 2 | - | partial | - |
| WADV171 | profile-in-production-build | Flag performance measurement taken from a development build rather than a production build. | perf | render | partial | 2/0/0 | 2.0 | 2 | - | none | - |
| WADV172 | prototype-pollution | Flag calling Object.prototype methods directly on untrusted objects or merging untrusted keys such as __proto__. | security | syntax | yes | 2/0/0 | 2.0 | 2 | no-prototype-builtins | none | - |
| WADV173 | query-options-inline | Flag retry or similar defaults set inline on useQuery instead of QueryClient defaults or queryOptions. | data-fetching | syntax | partial | 2/0/0 | 2.0 | 2 | @tanstack/query/prefer-query-options | none | - |
| WADV174 | route-config-file-based | Flag a hand-stitched monolithic route config, or components that exist only to read route location. | routing | structural | partial | 2/0/0 | 2.0 | 2 | - | none | - |
| WADV175 | setstate-in-render | Flag an unconditional state setter call during component render. | react-render | syntax | yes | 2/0/0 | 2.0 | 2 | react-hooks/set-state-in-render | none | - |
| WADV176 | spread-props-overuse | Flag {...props} spread onto a DOM element or child without filtering unneeded props. | react-render | syntax | partial | 2/0/0 | 2.0 | 2 | react/jsx-props-no-spreading | none | - |
| WADV177 | state-impossible-states | Flag several boolean state variables that can contradict each other where a single status or index would do. | state | structural | partial | 2/0/0 | 2.0 | 2 | - | none | - |
| WADV178 | ts-truthiness-check-primitive | Flag a truthiness check on a string, number or nullable primitive where an explicit comparison is needed. | typescript | types | yes | 2/0/0 | 2.0 | 2 | @typescript-eslint/strict-boolean-expressions | none | - |
| WADV179 | use-before-define | Flag a variable, function or class referenced before its definition. | other | syntax | yes | 2/0/0 | 2.0 | 2 | @typescript-eslint/no-use-before-define | none | - |
| WADV180 | worker-bundling | Flag new Worker(url) usage without a bundler-aware worker entry configuration. | build | syntax | partial | 2/0/0 | 2.0 | 2 | - | none | - |
| WADV181 | spa-vs-server-rendered | Flag a content site built as a client-rendered SPA with blank initial HTML where server rendering or static output is feasible. | architecture | human | no | 1/0/2 | 1.75 | 5 | - | none | - |
| WADV182 | css-anchor-positioning | Flag CSS using position-area where anchor() is needed, user-select none on buttons, or filter invert dark-mode hacks. | css | syntax | partial | 1/0/2 | 1.75 | 3 | - | none | - |
| WADV183 | query-key-structure | Flag a queryKey that omits variables used by queryFn, is not an array, or is not structured generic to specific. | data-fetching | syntax | yes | 1/0/1 | 1.5 | 11 | @tanstack/query/exhaustive-deps | none | - |
| WADV184 | tabs-aria-pattern | Flag a tab widget missing tablist, tab, tabpanel roles with aria-selected and aria-controls relationships. | a11y | syntax | partial | 2/0/0 | 1.5 | 8 | - | none | - |
| WADV185 | aria-hint-text | Flag aria-label or hidden text that includes usage instructions or role words such as click, button, tab or use arrow keys. | a11y | syntax | partial | 1/0/1 | 1.5 | 6 | - | none | - |
| WADV186 | css-layer-order | Flag third-party or reset CSS not wrapped in an @layer, or layers with generic colliding names. | css | syntax | partial | 2/0/0 | 1.5 | 6 | - | none | - |
| WADV187 | dependency-vulnerable | Flag dependencies with known critical advisories, such as vulnerable react-server-dom versions. | security | structural | yes | 1/0/1 | 1.5 | 6 | - | partial | applies |
| WADV188 | form-double-submit | Flag a form submit that has no guard against double submission, or only a disabled button, with no server-side protection. | forms | effects | partial | 2/2/0 | 1.5 | 6 | - | none | applies |
| WADV189 | query-stale-time | Flag a query on stable data left at default staleTime zero, or refetch flags disabled instead of tuning staleTime. | data-fetching | syntax | partial | 1/0/1 | 1.5 | 6 | - | none | - |
| WADV190 | web-component-vs-framework | Flag a widget needed across frameworks implemented in a single framework, or a web component lacking accessible markup and display handling. | architecture | human | no | 1/0/1 | 1.5 | 6 | - | none | - |
| WADV191 | jsx-element-vs-reactnode | Flag a children prop typed as JSX.Element, or a JSX intrinsic element not declared in the typings. | typescript | types | yes | 2/0/0 | 1.5 | 5 | - | none | - |
| WADV192 | ssr-browser-api-access | Flag window, document or localStorage accessed during render or state initialisation in server-rendered code without a guard. | react-render | syntax | yes | 2/0/0 | 1.5 | 5 | ?react/no-is-mounted | none | - |
| WADV193 | css-vendor-prefix | Flag vendor-prefixed properties and custom-property usage needing a fallback for unsupported browsers. | css | syntax | yes | 1/0/2 | 1.5 | 4 | stylelint/property-no-vendor-prefix | none | - |
| WADV194 | fn-length | Flag functions exceeding configured limits of lines, cyclomatic complexity, nesting depth or parameter count. | architecture | syntax | yes | 1/0/1 | 1.5 | 4 | @typescript-eslint/max-params, complexity, max-depth | implemented | - |
| WADV195 | hoc-wrapper-hell | Flag a component wrapped by many nested higher-order components, or a HOC lacking displayName or colliding prop names. | architecture | structural | partial | 1/0/1 | 1.5 | 4 | react/display-name | none | - |
| WADV196 | manual-screenreader-test | Flag a release process without manual testing on representative screen reader and browser pairs, or keyboard-only testing. | testing | human | no | 2/0/0 | 1.5 | 4 | - | none | - |
| WADV197 | rule-jest-prefer-expect-assertions | Flag test files violating jest conventions: tests outside describe, missing expect.assertions, toEqual instead of toStrictEqual, wrong jest-dom setup. | testing | syntax | yes | 1/0/1 | 1.5 | 4 | jest/js-jestdom, jest/prefer-expect-assertions, jest/prefer-strict-equal | none | - |
| WADV198 | state-library-overuse | Flag a second client state store layered over the framework's state, or hand-synced copies of one state. | state | structural | partial | 1/0/1 | 1.5 | 4 | - | none | - |
| WADV199 | svg-decorative-hidden | Flag a decorative inline svg that is not aria-hidden or has focusable true, or uses hard-coded colour instead of currentColor. | a11y | syntax | yes | 3/0/0 | 1.5 | 4 | - | none | - |
| WADV200 | swallowed-error | Flag a catch that only rethrows or ignores the error, or a throw of a non-Error value. | other | syntax | yes | 1/0/1 | 1.5 | 4 | @typescript-eslint/only-throw-error, @typescript-eslint/prefer-promise-reject-errors, no-throw-literal | none | partial |
| WADV201 | test-testid-overuse | Flag getByTestId or data-testid used where role or visible text queries are possible. | testing | syntax | yes | 1/0/1 | 1.5 | 4 | testing-library/no-test-id-queries, testing-library/prefer-screen-queries | none | ok |
| WADV202 | todo-untracked | Flag TODO or FIXME comments without an issue reference, owner or specific failing condition, or opt-out directives without a removal plan. | other | syntax | yes | 1/0/1 | 1.5 | 4 | ?no-warning-comments | implemented | ok |
| WADV203 | ts-banned-function-type | Flag the Function type or a callback typed returning any or with needlessly optional parameters. | typescript | types | yes | 2/0/0 | 1.5 | 4 | ?typescript-eslint/no-unsafe-function-type | none | - |
| WADV204 | ts-isolated-modules | Flag tsconfig missing isolatedModules, project references or separate typecheck for the bundler setup. | build | syntax | partial | 2/0/0 | 1.5 | 4 | ?typescript-eslint/consistent-type-imports | none | - |
| WADV205 | typed-route-links | Flag a Link or navigate call using a string path not checked against the typed route tree. | routing | types | partial | 1/0/1 | 1.5 | 4 | - | partial | applies |
| WADV206 | utility-class-conflict | Flag conflicting utility classes on one element, unordered class lists, or hand-built class strings. | css | syntax | partial | 2/0/0 | 1.5 | 4 | tailwindcss/classnames-order, tailwindcss/no-contradicting-classname | partial | - |
| WADV207 | aria-hidden-vs-hidden | Flag aria-hidden used to hide content that should be hidden from everyone instead of hidden or display none. | a11y | syntax | partial | 2/0/0 | 1.5 | 3 | - | none | - |
| WADV208 | console-log-left | Flag console.log or console.debug calls left in committed source. | other | syntax | yes | 1/0/1 | 1.5 | 3 | no-console | none | - |
| WADV209 | query-spread-result | Flag rest destructuring or spreading of a useQuery result, or using the whole result object as a dependency. | data-fetching | syntax | yes | 1/0/1 | 1.5 | 3 | @tanstack/query/no-rest-destructuring | none | - |
| WADV210 | react-production-build | Flag a production deployment built in development mode, using legacy render instead of createRoot, or classic JSX runtime. | build | render | yes | 1/0/1 | 1.5 | 3 | ?react/no-deprecated, react/react-in-jsx-scope | none | - |
| WADV211 | sri | Flag a third-party script or stylesheet tag lacking an integrity attribute. | security | syntax | yes | 1/0/1 | 1.5 | 3 | - | none | - |
| WADV212 | ts-exhaustive-switch | Flag a switch over a union lacking an exhaustive never default or missing a case. | typescript | types | yes | 1/0/1 | 1.5 | 3 | @typescript-eslint/switch-exhaustiveness-check | none | - |
| WADV213 | ts-optional-vs-undefined | Flag null literals or optional properties against the project's undefined-only convention. | typescript | syntax | partial | 1/0/1 | 1.5 | 3 | unicorn/no-null | none | - |
| WADV214 | aria-menu-for-nav | Flag role menu or menuitem used for site navigation instead of a plain list of links. | a11y | syntax | yes | 2/0/0 | 1.5 | 2 | - | none | - |
| WADV215 | composite-single-tab-stop | Flag a composite widget whose every option is in the tab order instead of using roving tabindex or activedescendant. | a11y | syntax | partial | 2/0/0 | 1.5 | 2 | - | none | - |
| WADV216 | context-provider-depth | Flag several stacked state contexts or a client provider wrapping the whole document where a narrower subtree would suffice. | state | structural | partial | 1/0/1 | 1.5 | 2 | - | none | - |
| WADV217 | mutating-arguments | Flag assignment to or mutation of function parameters. | other | syntax | yes | 1/0/1 | 1.5 | 2 | no-param-reassign | none | - |
| WADV218 | roving-tabindex | Flag a tablist or composite widget whose inactive items keep tabindex zero instead of minus one with arrow-key navigation. | a11y | syntax | partial | 2/0/0 | 1.5 | 2 | - | none | - |
| WADV219 | target-blank-noopener | Flag an anchor with target _blank lacking rel noopener noreferrer. | security | syntax | yes | 1/0/1 | 1.5 | 2 | react/jsx-no-target-blank | designed | ok |
| WADV220 | details-element | Flag custom show-hide widgets that duplicate native details and summary behaviour. | a11y | syntax | partial | 1/0/1 | 1.25 | 2 | - | none | - |
| WADV221 | form-hidden-input-trust | Flag security-relevant values passed through hidden inputs, or hidden controls whose values still submit. | security | syntax | partial | 1/0/1 | 1.25 | 2 | - | none | n/a |
| WADV222 | fetch-waterfall | Flag nested components that each fetch in their own effect so requests start only after the parent renders. | data-fetching | effects | partial | 1/0/0 | 1.0 | 8 | - | none | - |
| WADV223 | cls-budget | Flag pages whose measured Cumulative Layout Shift exceeds 0.1 at the 75th percentile. | perf | render | yes | 1/0/0 | 1.0 | 7 | - | partial | - |
| WADV224 | csp-trusted-types | Flag a CSP without require-trusted-types-for script where DOM string sinks are used. | security | render | partial | 0/0/2 | 1.0 | 7 | - | partial | - |
| WADV225 | toggle-semantics | Flag toggle markup not matching behaviour: a checkbox or button lacking role switch or aria-pressed, or radio buttons misused for on/off. | a11y | syntax | partial | 2/0/0 | 1.0 | 7 | - | none | - |
| WADV226 | ts-strict-mode | Flag tsconfig without strict, noUncheckedIndexedAccess or strictFunctionTypes, or with skipLibCheck hiding errors. | typescript | syntax | yes | 1/0/1 | 1.0 | 7 | - | none | - |
| WADV227 | query-select-stable | Flag an inline select function doing expensive work, or query data transformed ad hoc where select with stable reference applies. | data-fetching | syntax | partial | 1/0/0 | 1.0 | 6 | @tanstack/query/no-unstable-deps | none | - |
| WADV228 | utility-class-duplication | Flag the same long utility class list repeated across elements without a component abstraction. | css | structural | partial | 1/0/0 | 1.0 | 6 | tailwindcss/enforces-shorthand, tailwindcss/no-contradicting-classname | none | - |
| WADV229 | react-compiler-directive-sparingly | Flag a use no memo or use memo directive lacking an explanatory comment, or compiler-incompatible library and syntax usage. | react-hooks | syntax | yes | 1/0/0 | 1.0 | 5 | react-hooks/incompatible-library, react-hooks/unsupported-syntax | none | n/a |
| WADV230 | test-arrange-act-assert | Flag deeply nested describe blocks, shared setup spread across tests, or multiple renders of the same component in one test. | testing | syntax | partial | 1/0/0 | 1.0 | 5 | jest/no-identical-title, jest/valid-title | none | - |
| WADV231 | test-coverage-goal | Flag a test suite driven by coverage numbers rather than behaviours whose breakage would matter. | testing | human | no | 1/0/0 | 1.0 | 5 | - | implemented | - |
| WADV232 | timing-adjustable | Flag session timeouts, meta refresh redirects or time limits that users cannot turn off, adjust or extend, or CAPTCHAs without alternatives. | a11y | syntax | partial | 1/0/0 | 1.0 | 5 | - | none | - |
| WADV233 | ts-return-type-explicit | Flag an exported function lacking an explicit return type, or a redundant annotation on an inferrable declaration. | typescript | syntax | yes | 0/0/2 | 1.0 | 5 | @typescript-eslint/explicit-module-boundary-types | none | - |
| WADV234 | vite-multipage-input | Flag build config missing HTML entries for multi-page apps, library peer deps bundled, or build files opened via file protocol. | build | structural | partial | 1/0/0 | 1.0 | 5 | - | none | - |
| WADV235 | aria-valid-attrs | Flag an unknown ARIA attribute or role, or a role missing its required ARIA properties. | a11y | syntax | yes | 1/0/0 | 1.0 | 4 | jsx-a11y/aria-props, jsx-a11y/aria-role, jsx-a11y/role-has-required-aria-props | designed | - |
| WADV236 | card-single-link | Flag a card whose entire content is wrapped in one anchor, or a card with several redundant links to the same destination. | a11y | syntax | partial | 2/0/0 | 1.0 | 4 | - | none | - |
| WADV237 | css-physical-vs-logical | Flag physical properties such as left, margin-left or min-width where logical equivalents are expected. | css | syntax | yes | 2/0/0 | 1.0 | 4 | - | designed | - |
| WADV238 | non-serializable-in-store | Flag a function, Promise, class instance, Map or socket placed into store state or dispatched actions. | state | effects | partial | 1/0/0 | 1.0 | 4 | - | none | - |
| WADV239 | oauth-pkce | Flag an OAuth flow using implicit or password grant, plain PKCE challenge or a non-HTTPS redirect URI. | security | syntax | partial | 1/0/0 | 1.0 | 4 | - | none | - |
| WADV240 | query-property-order | Flag query or mutation option objects whose properties are in an order that breaks type inference, or a query function returning void. | data-fetching | syntax | yes | 1/0/0 | 1.0 | 4 | @tanstack/query/infinite-query-property-order, @tanstack/query/mutation-property-order, @tanstack/query/no-void-query-fn | none | - |
| WADV241 | rule-unicorn-prefer-add-event-listener | Flag DOM on-function assignment, older query methods, innerText or window globals where addEventListener, querySelector, textContent or globalThis apply. | other | syntax | yes | 1/0/0 | 1.0 | 4 | unicorn/prefer-add-event-listener, unicorn/prefer-dom-node-text-content, unicorn/prefer-global-this | none | - |
| WADV242 | state-selectors-colocated | Flag components reading nested store state shape directly instead of via named selectors, or selectors returning new references each call. | state | structural | partial | 1/0/0 | 1.0 | 4 | - | none | - |
| WADV243 | toast-interactive-content | Flag interactive controls or links inside a toast or live-region notification. | a11y | syntax | partial | 1/0/1 | 1.0 | 4 | - | none | - |
| WADV244 | ts-zod-parse-boundary | Flag external input (JSON, form, fetch result) used without parsing through a schema at the boundary. | typescript | types | partial | 1/0/0 | 1.0 | 4 | - | none | applies |
| WADV245 | a11y-top-six | Flag the six dominant WCAG failures: low contrast, missing alt, unlabeled form control, empty link, empty button, missing html lang. | a11y | syntax | yes | 1/0/0 | 1.0 | 3 | jsx-a11y/alt-text | none | - |
| WADV246 | css-generated-content-meaning | Flag ::before or ::after content that carries meaning or text a user must read. | css | syntax | partial | 1/0/0 | 1.0 | 3 | - | none | - |
| WADV247 | css-unitless-line-height | Flag line-height declared with a length unit instead of a unitless number. | css | syntax | yes | 1/0/0 | 1.0 | 3 | - | none | - |
| WADV248 | data-access-layer | Flag server code mixing direct database access in components with a separate data access layer or API calls. | architecture | structural | partial | 1/0/0 | 1.0 | 3 | - | none | - |
| WADV249 | dialog-element | Flag a modal lacking role dialog, aria-modal, an accessible name or a visible close button, where native dialog could be used. | a11y | syntax | partial | 1/0/0 | 1.0 | 3 | - | none | - |
| WADV250 | early-return-states | Flag a component that renders loading, empty and data states through nested conditional JSX instead of early returns. | react-render | syntax | partial | 1/0/0 | 1.0 | 3 | react/jsx-no-leaked-render | none | - |
| WADV251 | effect-for-event-logic | Flag an effect that performs user-event work, such as posting a form, by watching a flag state set in a handler. | react-hooks | structural | partial | 1/0/0 | 1.0 | 3 | - | none | - |
| WADV252 | form-error-summary-focus | Flag a form that shows validation errors without an error summary receiving keyboard focus. | forms | effects | partial | 1/0/0 | 1.0 | 3 | - | none | - |
| WADV253 | form-state-in-global-store | Flag form field values dispatched to a global store on each keystroke, or form state kept in a store after unmount. | state | structural | partial | 1/0/0 | 1.0 | 3 | - | none | - |
| WADV254 | landmark-unique-label | Flag repeated landmark roles on a page without distinct aria-label or aria-labelledby. | a11y | structural | yes | 1/0/0 | 1.0 | 3 | - | none | - |
| WADV255 | legacy-js-transpile | Flag build output that transpiles modern syntax such as async functions and classes for browsers that already support it. | build | render | partial | 1/0/0 | 1.0 | 3 | - | none | - |
| WADV256 | loading-state-missing | Flag an async data-dependent component with no pending or loading state. | data-fetching | structural | partial | 1/0/0 | 1.0 | 3 | - | designed | - |
| WADV257 | query-notify-on-change-props | Flag a hard-coded notifyOnChangeProps list, or tracked-query usage that reads fields only in effects. | data-fetching | structural | partial | 1/0/0 | 1.0 | 3 | - | none | - |
| WADV258 | reducer-purity | Flag a reducer that performs side effects such as fetch, timers, logging, Math.random or Date.now. | state | effects | yes | 1/0/0 | 1.0 | 3 | - | none | - |
| WADV259 | redux-use-rtk | Flag hand-written Redux reducers, action constants or createStore instead of Redux Toolkit createSlice and configureStore. | state | syntax | yes | 1/0/0 | 1.0 | 3 | ?typescript-eslint/no-deprecated | none | - |
| WADV260 | state-normalized | Flag nested duplicated entities in state rather than normalized by id, or non-plain-object state. | state | structural | partial | 1/0/0 | 1.0 | 3 | - | none | - |
| WADV261 | target-size | Flag a pointer target smaller than the WCAG minimum size or spacing, such as secondary links with tiny hit areas. | a11y | render | yes | 2/0/0 | 1.0 | 3 | - | designed | partial |
| WADV262 | test-lint-plugins | Flag a test project without testing-library and jest-dom lint plugins or jest-dom matchers, using raw DOM property assertions instead. | testing | syntax | yes | 1/0/0 | 1.0 | 3 | ?jest-dom/prefer-enabled-disabled | none | - |
| WADV263 | test-use-screen | Flag Testing Library queries destructured from render, manual cleanup calls, or query variants used for presence assertions. | testing | syntax | yes | 1/0/0 | 1.0 | 3 | testing-library/no-manual-cleanup, testing-library/prefer-presence-queries, testing-library/prefer-screen-queries | none | - |
| WADV264 | ts-await-thenable | Flag await of a non-Promise value, or a Promise-returning function not declared async consistently. | typescript | types | yes | 1/0/0 | 1.0 | 3 | @typescript-eslint/await-thenable | none | - |
| WADV265 | ts-large-union | Flag a union with more than a dozen members, or a very complex inline conditional type used as a return annotation. | typescript | syntax | partial | 1/0/0 | 1.0 | 3 | - | none | - |
| WADV266 | ts-optional-chain | Flag a chained logical && check where optional chaining applies, unnecessary optional chain, or ?? misused. | typescript | types | yes | 1/0/0 | 1.0 | 3 | @typescript-eslint/prefer-nullish-coalescing, @typescript-eslint/prefer-optional-chain, no-unsafe-optional-chaining | none | - |
| WADV267 | usesyncexternalstore-snapshot-stable | Flag getSnapshot or subscribe that returns a new object or function on each call. | react-hooks | effects | partial | 1/0/0 | 1.0 | 3 | - | none | - |
| WADV268 | xss-json-in-script | Flag JSON serialised into an inline script block without escaping the less-than sequence. | security | syntax | yes | 1/0/0 | 1.0 | 3 | - | none | - |
| WADV269 | astro-single-head | Flag an Astro head element outside a layout component, or a script with attributes missing type module where imports are used. | build | syntax | partial | 1/0/0 | 1.0 | 2 | - | none | - |
| WADV270 | compound-component | Flag a component configured with arrays of items or render options where composable child components would give callers control. | architecture | human | no | 1/0/0 | 1.0 | 2 | - | none | - |
| WADV271 | context-vs-global-state | Flag mutable module-level state shared across server requests or used where context would scope it to the tree. | state | structural | partial | 1/0/0 | 1.0 | 2 | - | none | - |
| WADV272 | css-duplicate-declaration | Flag duplicate properties or duplicate selectors within a stylesheet. | css | syntax | yes | 1/0/0 | 1.0 | 2 | stylelint/declaration-block-no-duplicate-properties, stylelint/no-duplicate-selectors | none | - |
| WADV273 | css-file-per-component | Flag a context-qualified rule defined in a stylesheet other than the subject component's own file. | css | structural | partial | 1/0/0 | 1.0 | 2 | - | none | - |
| WADV274 | css-z-index-scale | Flag z-index literals outside the defined scale, or overlays that depend on stacking context instead of a portal. | css | syntax | partial | 1/0/0 | 1.0 | 2 | - | designed | - |
| WADV275 | hydration-mismatch | Flag render code whose output differs between server and client, such as Date.now, Math.random, window checks or invalid nesting. | react-render | effects | partial | 1/0/0 | 1.0 | 2 | - | none | - |
| WADV276 | inversion-of-control | Flag a reusable function whose options are flags for each use case rather than accepting a callback that decides. | architecture | structural | partial | 1/0/0 | 1.0 | 2 | - | none | - |
| WADV277 | js-parseint-radix | Flag parseInt without radix, global isNaN or isFinite, and new String, Number or Boolean wrappers. | other | syntax | yes | 1/0/0 | 1.0 | 2 | no-restricted-globals | none | - |
| WADV278 | jsdoc-public-api | Flag an exported function, interface, enum or class that has no doc comment. | other | syntax | yes | 1/0/0 | 1.0 | 2 | no-inline-comments | none | - |
| WADV279 | lint-rules-prune-style | Flag enabled lint rules that are purely stylistic and have never caught a bug, instead of formatter responsibility. | other | human | no | 1/0/0 | 1.0 | 2 | - | none | - |
| WADV280 | memory-leak-map-cache | Flag a Map or WeakRef cache keyed by objects that is never cleared where WeakMap would allow collection. | perf | structural | partial | 1/0/0 | 1.0 | 2 | - | none | - |
| WADV281 | module-boundary-deep-import | Flag an import that reaches into another module's internal files instead of its public entry point. | architecture | syntax | yes | 1/0/0 | 1.0 | 2 | import/no-internal-modules, import/no-relative-parent-imports | none | - |
| WADV282 | node-builtin-in-client | Flag import of a Node-only builtin such as fs from browser-bundled code, or a default import from a CommonJS module that lacks one. | build | structural | yes | 1/0/0 | 1.0 | 2 | - | none | - |
| WADV283 | portal-event-bubbling | Flag a portaled component rendered inside an ancestor with click handlers that would receive its events. | react-render | structural | partial | 1/0/0 | 1.0 | 2 | - | none | - |
| WADV284 | query-client-stable | Flag a QueryClient constructed inside a component body, or query cache used as local state. | data-fetching | syntax | yes | 1/0/0 | 1.0 | 2 | @tanstack/query/stable-query-client | none | - |
| WADV285 | ref-read-in-render | Flag reading or writing ref.current during render. | react-hooks | syntax | yes | 1/0/0 | 1.0 | 2 | react-hooks/refs | none | - |
| WADV286 | ref-vs-state | Flag a ref holding a value that is displayed or drives rendering, or state holding a value that never affects output. | react-hooks | structural | partial | 1/0/0 | 1.0 | 2 | - | none | - |
| WADV287 | rhf-controller-spread-field | Flag a UI-library input registered with register where Controller with spread field is required, or the reverse. | forms | syntax | partial | 1/0/0 | 1.0 | 2 | - | none | - |
| WADV288 | route-loader-vs-effect | Flag route components that fetch their own data on mount instead of loaders initiated at route boundaries. | routing | structural | partial | 1/0/0 | 1.0 | 2 | - | partial | n/a |
| WADV289 | server-action-return-minimal | Flag a server action returning raw database records, or closing over secrets or large variables. | security | types | partial | 1/0/0 | 1.0 | 2 | - | none | - |
| WADV290 | test-focused | Flag focused or skipped tests (fit, fdescribe, only, skip) left in committed test code. | testing | syntax | yes | 1/0/0 | 1.0 | 2 | jest/no-disabled-tests, jest/no-focused-tests | none | - |
| WADV291 | test-real-browser | Flag component or e2e tests run in jsdom or a simulated provider where real-browser behaviour matters. | testing | human | no | 1/1/0 | 1.0 | 2 | - | none | - |
| WADV292 | text-resize-200 | Flag layouts that clip or scroll horizontally at 200 percent text size or zoom. | a11y | render | yes | 1/0/0 | 1.0 | 2 | - | none | - |
| WADV293 | ts-discriminated-union | Flag a type with many optional fields or string tag where a discriminated union with literal kind would narrow correctly. | typescript | types | partial | 1/0/0 | 1.0 | 2 | - | none | - |
| WADV294 | ts-overload-collapse | Flag overloads that differ only by trailing parameters or one parameter type, or are ordered general before specific. | typescript | syntax | yes | 1/0/0 | 1.0 | 2 | ?typescript-eslint/adjacent-overload-signatures, typescript-eslint/unified-signatures | none | - |
| WADV295 | ts-return-await | Flag inconsistent await of returned promises, or an async function containing no await. | typescript | types | yes | 1/0/0 | 1.0 | 2 | @typescript-eslint/require-await, @typescript-eslint/return-await | none | - |
| WADV296 | use-client-position | Flag a use client or use server directive placed after imports or code, or in backticks. | architecture | syntax | yes | 1/0/0 | 1.0 | 2 | - | partial | - |
| WADV297 | use-server-misuse | Flag use server applied to mark a Server Component, or hooks and handlers in a file without use client. | architecture | syntax | yes | 1/0/0 | 1.0 | 2 | - | none | - |
| WADV298 | alt-redundant-words | Flag alt text that begins with or contains words such as image of, picture of or graphic of. | a11y | syntax | yes | 1/0/0 | 1.0 | 1 | jsx-a11y/img-redundant-alt | none | - |
| WADV299 | aria-current-page | Flag navigation links where the current page is indicated only by colour and lacks aria-current. | a11y | syntax | partial | 1/0/0 | 1.0 | 1 | - | none | - |
| WADV300 | async-order-assumption | Flag code that relies on the relative ordering of timers, promise callbacks or mutation observer callbacks across browsers. | other | human | no | 1/0/0 | 1.0 | 1 | - | none | - |
| WADV301 | bidi-control-chars | Flag Unicode bidirectional control characters in source files. | security | syntax | yes | 1/0/0 | 1.0 | 1 | - | none | - |
| WADV302 | boolean-prop-explosion | Flag a component or function whose signature accumulates boolean flags or option props that gate separate behaviours. | architecture | structural | partial | 1/0/0 | 1.0 | 1 | - | designed | - |
| WADV303 | class-super-props | Flag a class component constructor calling super() without passing props. | react-hooks | syntax | yes | 1/0/0 | 1.0 | 1 | ?react/require-render-return | none | - |
| WADV304 | component-display-name | Flag a component definition without a displayName where the tooling requires one. | react-render | syntax | yes | 1/0/0 | 1.0 | 1 | react/display-name | none | - |
| WADV305 | component-singleton-assumption | Flag component code that resets or cleans up module-level or global state on mount or unmount, assuming a single instance. | react-render | structural | partial | 1/0/0 | 1.0 | 1 | - | none | - |
| WADV306 | context-custom-hook | Flag components that call useContext on a raw context directly instead of a custom hook that validates the provider. | state | structural | partial | 1/0/0 | 1.0 | 1 | - | none | - |
| WADV307 | css-import | Flag a CSS @import rule that serialises stylesheet loading. | perf | syntax | yes | 1/0/0 | 1.0 | 1 | - | none | - |
| WADV308 | css-in-js | Flag runtime CSS-in-JS where styles are essential and the page must render without JavaScript. | css | structural | partial | 1/0/0 | 1.0 | 1 | - | none | - |
| WADV309 | css-sass-extend | Flag use of Sass @extend. | css | syntax | yes | 1/0/0 | 1.0 | 1 | - | none | - |
| WADV310 | error-boundary-async-gap | Flag code that expects an error boundary to catch errors from event handlers, async callbacks or SSR. | react-render | structural | partial | 1/0/0 | 1.0 | 1 | - | none | - |
| WADV311 | error-boundary-reset-keys | Flag an error boundary with no reset mechanism or resetKeys tied to the state that caused the failure. | react-render | syntax | partial | 1/0/0 | 1.0 | 1 | - | none | - |
| WADV312 | event-payload-object | Flag a custom event or callback that passes a raw value instead of an object payload. | architecture | syntax | partial | 1/0/0 | 1.0 | 1 | - | none | - |
| WADV313 | flushsync-in-effect | Flag a flushSync call inside render, an effect or a class lifecycle. | react-hooks | syntax | yes | 1/0/0 | 1.0 | 1 | - | none | - |
| WADV314 | framework-correlation | Flag pages loading heavy script stacks such as jQuery UI plugins, carousels or ad networks. | perf | render | partial | 1/0/0 | 1.0 | 1 | - | none | - |
| WADV315 | heading-empty | Flag a heading element with no accessible text content. | a11y | syntax | yes | 1/0/0 | 1.0 | 1 | jsx-a11y/heading-has-content | partial | - |
| WADV316 | hoist-constants | Flag a constant object, array or function created inside a component or wrapped in useMemo that could live at module scope. | react-render | syntax | partial | 1/0/0 | 1.0 | 1 | - | none | - |
| WADV317 | js-structural-selector | Flag DOM queries using long structural selectors instead of a single class or id. | other | syntax | yes | 1/0/0 | 1.0 | 1 | - | none | - |
| WADV318 | jsx-style | Flag a JSX element with no children that is not self-closed, or an explicit prop={true}. | react-render | syntax | yes | 1/0/0 | 1.0 | 1 | ?react/self-closing-comp | none | - |
| WADV319 | key-from-useid | Flag useId used to generate a list key or cache key. | react-render | syntax | yes | 1/0/0 | 1.0 | 1 | - | none | - |
| WADV320 | keyboard-trap | Flag a modal, menu or widget that traps focus with no Escape or other keyboard release. | a11y | effects | partial | 1/0/0 | 1.0 | 1 | - | none | - |
| WADV321 | landmark-in-modal | Flag a landmark region element wrapping modal dialog content. | a11y | syntax | yes | 1/0/0 | 1.0 | 1 | - | none | - |
| WADV322 | layout-thrash | Flag interleaved DOM reads of layout properties and writes inside the same frame or loop. | perf | effects | partial | 1/0/0 | 1.0 | 1 | - | none | - |
| WADV323 | link-underline | Flag inline links in body text with underline removed and no other non-colour cue at 3:1 contrast. | a11y | syntax | partial | 1/0/0 | 1.0 | 1 | - | none | - |
| WADV324 | presentational-children | Flag a heading, link or button placed inside a role whose children are presentational, such as button, checkbox, tab or switch. | a11y | syntax | partial | 1/0/0 | 1.0 | 1 | - | none | - |
| WADV325 | prop-name-dom-clash | Flag a component prop named style, className or another DOM attribute but used for a different purpose. | react-render | syntax | partial | 1/0/0 | 1.0 | 1 | - | none | - |
| WADV326 | props-destructuring | Flag props, state or context accessed without destructuring against the project convention. | react-render | syntax | yes | 1/0/0 | 1.0 | 1 | react/destructuring-assignment | none | - |
| WADV327 | props-minimal-primitives | Flag a memoized component receiving a whole object where it uses one field. | react-render | structural | partial | 1/0/0 | 1.0 | 1 | - | none | - |
| WADV328 | query-custom-hook | Flag useQuery called inline in components rather than wrapped in a feature custom hook. | data-fetching | structural | partial | 1/0/0 | 1.0 | 1 | - | none | - |
| WADV329 | route-auth-middleware | Flag per-route or per-loader auth checks duplicated instead of route middleware that redirects unauthenticated users. | routing | structural | partial | 1/0/0 | 1.0 | 1 | - | none | - |
| WADV330 | rule-unicorn-no-await-expression-member | Flag member access directly on an await expression. | other | syntax | yes | 1/0/0 | 1.0 | 1 | unicorn/no-await-expression-member | none | - |
| WADV331 | server-action-for-fetching | Flag a server action used for data reads instead of a query or loader. | architecture | structural | partial | 1/0/0 | 1.0 | 1 | - | none | - |
| WADV332 | server-action-transition | Flag a server function invoked outside a transition or form action. | react-hooks | structural | partial | 1/0/0 | 1.0 | 1 | - | none | - |
| WADV333 | slow-connection-baseline | Flag features or bundles that assume fast networks without a degraded or low-bandwidth path. | perf | human | no | 1/0/0 | 1.0 | 1 | - | none | - |
| WADV334 | style-injection | Flag user-provided strings bound to a style attribute or style element. | security | syntax | yes | 1/0/0 | 1.0 | 1 | - | none | - |
| WADV335 | table-cell-control-labels | Flag a control inside a table cell without a unique name combining its row and column header. | a11y | structural | partial | 1/0/0 | 1.0 | 1 | - | none | - |
| WADV336 | token-in-localstorage | Flag an auth or refresh token stored in localStorage or sessionStorage, or tokens lacking rotation or sender constraint. | security | syntax | partial | 1/0/0 | 1.0 | 1 | - | none | applies |
| WADV337 | use-promise-created-in-render | Flag a promise created during render and passed to use(). | data-fetching | effects | partial | 1/0/0 | 1.0 | 1 | - | none | - |
| WADV338 | title-attr-tooltip | Flag a title attribute used as the sole tooltip or accessible name for a control. | a11y | syntax | yes | 1/0/1 | 0.75 | 3 | - | none | - |
| WADV339 | css-intrinsic-layout | Flag fixed widths, width 100 percent on padded children, px line lengths or per-breakpoint layout where intrinsic flex or grid sizing works. | css | syntax | partial | 1/0/0 | 0.5 | 11 | - | none | - |
| WADV340 | worker-message-size | Flag large objects sent through postMessage without transferables, or heavy data copied to a worker. | perf | effects | partial | 0/0/1 | 0.5 | 7 | - | none | - |
| WADV341 | dom-clobbering-window-global | Flag reads of globals or named elements via window or document properties that attacker-controlled markup could shadow. | security | syntax | partial | 0/0/1 | 0.5 | 6 | ?no-implicit-globals, no-undef | none | - |
| WADV342 | pointer-down-activation | Flag an action triggered on mousedown, touchstart or pointerdown, or a drag action without abort. | a11y | syntax | yes | 0/0/1 | 0.5 | 6 | - | none | - |
| WADV343 | redux-logic-in-reducers | Flag business logic in components or action creators and setter-style actions, or sagas used for plain fetching. | state | human | no | 0/0/1 | 0.5 | 6 | - | none | - |
| WADV344 | tailwind-arbitrary-value | Flag Tailwind arbitrary values, custom classes or desktop-first breakpoints where theme tokens and mobile-first utilities exist. | css | syntax | partial | 0/0/1 | 0.5 | 6 | tailwindcss/no-custom-classname | partial | applies |
| WADV345 | vue-reactive-destructure | Flag destructuring of a reactive object or composable return that drops reactivity, or deep reactivity on large data. | state | syntax | yes | 0/0/1 | 0.5 | 6 | ?vue/no-ref-object-reactivity-loss | none | - |
| WADV346 | aria-list-roles | Flag a list styled with list-style none or restructured by wrappers that lacks explicit role list and listitem. | a11y | syntax | partial | 1/0/0 | 0.5 | 5 | - | none | - |
| WADV347 | coop-coep-isolation | Flag documents lacking Cross-Origin-Opener-Policy same-origin or related isolation headers where required. | security | render | partial | 0/0/1 | 0.5 | 5 | - | designed | - |
| WADV348 | lint-config-scope-files | Flag lint config that applies JS rules globally and disables them per file type, or has stale typed-lint setup and duplicate tool versions. | build | syntax | partial | 0/0/1 | 0.5 | 5 | - | none | - |
| WADV349 | persistent-ui-state-cookie | Flag UI preference state held only in client storage that causes flicker or SSR mismatch, instead of a cookie. | state | human | no | 0/1/1 | 0.5 | 5 | - | none | - |
| WADV350 | prominent-message-over-toast | Flag a transient toast used for important or error messages instead of a persistent, focused inline message. | a11y | human | no | 1/0/0 | 0.5 | 5 | - | none | - |
| WADV351 | ts-unnecessary-condition | Flag a condition whose type is always truthy or falsy, or a redundant type, template or conversion, or a default never used. | typescript | types | yes | 0/0/1 | 0.5 | 5 | @typescript-eslint/no-redundant-type-constituents, @typescript-eslint/no-unnecessary-condition, @typescript-eslint/no-unnecessary-template-expression | none | - |
| WADV352 | typed-linting-enabled | Flag a TypeScript lint config that does not enable type-checked rule presets, or enables a bypassed strict preset. | typescript | syntax | yes | 0/0/1 | 0.5 | 5 | - | none | applies |
| WADV353 | memo-needed-for-identity | Flag a component receiving frequently changing parent state props without memo where renders are measured to be wasteful. | react-render | human | no | 0/0/1 | 0.5 | 4 | react/jsx-no-bind | none | - |
| WADV354 | meta-charset-first | Flag a head that omits meta charset, places it after the title, or lacks favicon and Open Graph metadata. | build | syntax | yes | 1/0/0 | 0.5 | 4 | - | none | - |
| WADV355 | ts-enum | Flag a TypeScript enum, especially one mixing numeric and string members or a non-literal initialiser. | typescript | types | yes | 0/0/1 | 0.5 | 4 | @typescript-eslint/no-mixed-enums, @typescript-eslint/no-unsafe-enum-comparison, @typescript-eslint/prefer-literal-enum-member | none | - |
| WADV356 | ts-satisfies | Flag a loose-typed literal such as URLSearchParams or JSON body, or as const object, that is not checked with satisfies. | typescript | types | partial | 1/0/0 | 0.5 | 4 | - | none | - |
| WADV357 | accessible-name-concise | Flag an aria-label or accessible name longer than about three words. | a11y | syntax | partial | 1/0/0 | 0.5 | 3 | - | none | - |
| WADV358 | flushsync-sparingly | Flag flushSync calls outside integration with third-party code or browser callbacks. | perf | syntax | partial | 0/0/1 | 0.5 | 3 | - | none | - |
| WADV359 | god-component | Flag a component or file that mixes data fetching, layout and many responsibilities, or several unrelated components in one file. | architecture | structural | partial | 0/1/1 | 0.5 | 3 | react/no-multi-comp | partial | - |
| WADV360 | tailwind-apply-overuse | Flag heavy use of Tailwind @apply to build component classes instead of component abstraction. | css | syntax | partial | 0/0/1 | 0.5 | 3 | - | none | - |
| WADV361 | ts-empty-object-type | Flag an empty object type, extraneous class or misused spread of a non-object type. | typescript | syntax | yes | 0/0/1 | 0.5 | 3 | @typescript-eslint/no-empty-object-type, @typescript-eslint/no-extraneous-class, @typescript-eslint/no-misused-spread | none | - |
| WADV362 | ts-event-handler-typed | Flag an event handler parameter without an explicit event type when not contextually typed. | typescript | types | yes | 1/0/0 | 0.5 | 3 | ?typescript-eslint/no-explicit-any | none | - |
| WADV363 | ts-misused-promise | Flag a Promise-returning function passed where a void callback or conditional is expected, such as an async onClick handler. | typescript | types | yes | 0/0/1 | 0.5 | 3 | @typescript-eslint/no-misused-promises, @typescript-eslint/promise-function-async | none | ok-by-hand |
| WADV364 | ts-over-derived-types | Flag long chains of Pick, Omit or mapped types coupling UI props to a data model, or duplicated union literals beside a const object. | typescript | types | partial | 1/0/0 | 0.5 | 3 | - | none | - |
| WADV365 | ts-template-nonstring | Flag a template literal, plus operand or toString using a non-string type like object, undefined or number where disallowed. | typescript | types | yes | 0/0/1 | 0.5 | 3 | @typescript-eslint/no-base-to-string, @typescript-eslint/restrict-plus-operands, @typescript-eslint/restrict-template-expressions | none | - |
| WADV366 | error-boundary-as-control-flow | Flag throwing an Error for expected control flow such as validation failures. | react-render | syntax | partial | 0/0/1 | 0.5 | 2 | - | none | n/a |
| WADV367 | forwardref-deprecated | Flag forwardRef or Context.Provider used in React 19 code where ref as a prop or direct Context provider applies. | react-hooks | syntax | yes | 0/0/1 | 0.5 | 2 | - | none | - |
| WADV368 | label-in-name | Flag a control whose accessible name does not contain its visible label text. | a11y | syntax | yes | 1/0/0 | 0.5 | 2 | - | none | - |
| WADV369 | passive-listener | Flag a scroll, touch or wheel listener not registered as passive, or per-item listeners where delegation applies. | perf | syntax | yes | 1/0/0 | 0.5 | 2 | - | none | - |
| WADV370 | rhf-typed-form | Flag a useForm call without a form-values generic, or resolver and handler types left opaque. | forms | types | yes | 0/0/1 | 0.5 | 2 | - | none | - |
| WADV371 | rule-typescript-eslint-strict-void-return | Flag passing a value-returning function where a void-returning callback is expected, or a void expression used as a value. | typescript | types | yes | 0/0/1 | 0.5 | 2 | @typescript-eslint/no-confusing-void-expression, @typescript-eslint/strict-void-return | none | - |
| WADV372 | starting-style-vs-keyframes | Flag @starting-style or CSS animation constructs where plain @keyframes would be simpler and more broadly supported. | css | syntax | partial | 0/0/1 | 0.5 | 2 | - | none | - |
| WADV373 | text-compression | Flag text assets served without Brotli or gzip Content-Encoding. | perf | render | yes | 0/0/1 | 0.5 | 2 | - | designed | - |
| WADV374 | ts-dynamic-delete | Flag the delete operator on a computed key or array element. | typescript | syntax | yes | 0/0/1 | 0.5 | 2 | @typescript-eslint/no-array-delete, @typescript-eslint/no-dynamic-delete | none | - |
| WADV375 | ts-floating-promise | Flag a Promise-valued expression statement that is not awaited, caught, returned or marked void. | typescript | types | yes | 0/0/1 | 0.5 | 2 | @typescript-eslint/no-floating-promises | none | ok-by-hand |
| WADV376 | ts-interface-vs-type | Flag an object type alias composed by intersection where an interface extending would be used. | typescript | syntax | yes | 0/0/1 | 0.5 | 2 | ?typescript-eslint/consistent-type-definitions | none | - |
| WADV377 | ts-non-null-assertion | Flag the postfix non-null assertion operator. | typescript | syntax | yes | 0/0/1 | 0.5 | 2 | @typescript-eslint/no-non-null-assertion | none | - |
| WADV378 | ts-unknown-catch | Flag a catch variable used as a typed Error without narrowing, or a catch variable typed any. | typescript | types | yes | 0/0/1 | 0.5 | 2 | @typescript-eslint/use-unknown-in-catch-callback-variable | none | - |
| WADV379 | tsconfig-bundler-noemit | Flag a bundler project whose tsconfig emits output, or uses a target, lib or module setting not matching the runtime. | build | syntax | yes | 1/0/0 | 0.5 | 2 | - | none | - |
| WADV380 | uselayouteffect-sparingly | Flag useLayoutEffect that does not measure layout, or a measurement-dependent effect using useEffect causing flicker. | react-hooks | syntax | partial | 0/0/1 | 0.5 | 2 | - | none | - |
| WADV381 | accordion-button-in-heading | Flag an accordion header that is not a button inside a heading with aria-expanded and aria-controls. | a11y | syntax | partial | 1/0/0 | 0.5 | 1 | - | none | - |
| WADV382 | component-misuse-warnings | Flag design-system components that do not emit developer-facing warnings for invalid prop combinations. | architecture | human | no | 1/0/0 | 0.5 | 1 | - | none | - |
| WADV383 | custom-element-display | Flag a custom element used for layout without an explicit display declaration. | css | syntax | yes | 1/0/0 | 0.5 | 1 | - | none | - |
| WADV384 | debounce-masking-slow-render | Flag a debounce added to an input handler to hide slow rendering of global state. | perf | human | no | 0/0/1 | 0.5 | 1 | - | none | - |
| WADV385 | font-display | Flag @font-face without font-display or fonts loaded from external stylesheets that block rendering. | perf | syntax | yes | 0/0/1 | 0.5 | 1 | - | designed | - |
| WADV386 | incremental-a11y-fix | Flag an accessibility fix PR that rewrites large unrelated areas instead of staying within the story scope. | a11y | human | no | 0/0/1 | 0.5 | 1 | - | none | - |
| WADV387 | json-parse-large-literal | Flag a very large object literal that should be embedded as a JSON.parse string for parse speed. | perf | syntax | partial | 0/0/1 | 0.5 | 1 | - | none | - |
| WADV388 | key-missing | Flag an element rendered from map or iteration without a key prop. | react-render | syntax | yes | 0/0/1 | 0.5 | 1 | react/jsx-key | none | - |
| WADV389 | list-style-none-semantics | Flag list-style none on ul or ol, or display none on list items, where a list role is not restored. | a11y | syntax | partial | 0/0/1 | 0.5 | 1 | - | none | - |
| WADV390 | magic-value | Flag an unnamed numeric literal other than trivial values. | other | syntax | yes | 0/0/1 | 0.5 | 1 | @typescript-eslint/no-magic-numbers | designed | - |
| WADV391 | render-leaked-zero | Flag a JSX expression using && with a possibly numeric left operand that can render 0. | react-render | syntax | yes | 0/0/1 | 0.5 | 1 | react/jsx-no-leaked-render | none | - |
| WADV392 | stale-a11y-workaround | Flag legacy accessibility workarounds that need re-testing against current browsers and screen readers. | a11y | human | no | 1/0/0 | 0.5 | 1 | - | none | - |
| WADV393 | style-from-aria-state | Flag selected or expanded visual state styled by a class that is separate from the aria attribute exposing it. | css | syntax | partial | 1/0/0 | 0.5 | 1 | - | none | - |
| WADV394 | tabs-vs-links | Flag navigation or table of contents styled as tabs but behaving as links. | a11y | human | no | 1/0/0 | 0.5 | 1 | - | none | - |
| WADV395 | toggle-immediate-save | Flag a toggle switch that saves immediately without pending and error state handling. | forms | effects | partial | 1/0/0 | 0.5 | 1 | - | none | - |
| WADV396 | tooltip-aria-association | Flag a tooltip not associated with its trigger by aria-labelledby or aria-describedby. | a11y | syntax | partial | 1/0/0 | 0.5 | 1 | - | none | - |
| WADV397 | tooltip-interactive-content | Flag interactive controls such as links or close buttons inside a tooltip. | a11y | syntax | partial | 1/0/0 | 0.5 | 1 | - | none | - |
| WADV398 | ts-unbound-method | Flag a class method reference passed or assigned without binding. | typescript | types | yes | 0/0/1 | 0.5 | 1 | @typescript-eslint/unbound-method | none | - |
| WADV399 | usesyncexternalstore-server-snapshot | Flag useSyncExternalStore on a browser API without getServerSnapshot in server-rendered code. | react-hooks | syntax | yes | 0/0/1 | 0.5 | 1 | - | none | - |
| WADV400 | a11y-in-shared-component | Flag copies of a complex widget (menu, dialog, combobox) hand-rolled in feature code instead of using the project's shared accessible component. | a11y | structural | partial | 0/0/1 | 0.25 | 5 | - | none | - |
| WADV401 | css-margin-owl | Flag margin set on the element itself (e.g. p margin-bottom) rather than between siblings or via gap or a lobotomised owl selector. | css | syntax | partial | 0/0/1 | 0.25 | 4 | - | none | - |
| WADV402 | redundant-link-tabindex-hide | Flag several adjacent links to one URL in a card that are all focusable instead of hiding redundant ones from tab order and AT. | a11y | syntax | partial | 0/0/1 | 0.25 | 3 | - | none | - |
| WADV403 | forwardref-generic | Flag a forwardRef-wrapped generic component whose generic type inference is lost. | typescript | types | partial | 0/0/1 | 0.25 | 1 | - | none | - |

## 7. (see section 1 for the vetting tables)

## 8. Source list (563 processed units)

| slug | who | url | status | items |
|---|---|---|---|---|
| ar-misfire | Alex Russell | https://infrequently.org/2024/07/misfire/ | irrelevant | 0 |
| ar-notes-on-performance-remediation-strateg | Alex Russell | https://infrequently.org/2026/08/notes-on-performance-remediation-strategies/ | full | 4 |
| ar-state-management | Alex Russell | https://infrequently.org/2026/07/state-management/ | full | 3 |
| as-building-an-accessible-autocomplete-cont | Adam Silver | https://adamsilver.io/blog/building-an-accessible-autocomplete-control/ | full | 12 |
| as-can-you-make-toast-messages-accessible | Adam Silver | https://adamsilver.io/blog/can-you-make-toast-messages-accessible/ | full | 4 |
| as-javascript-isnt-always-available-and-its | Adam Silver | https://adamsilver.io/blog/javascript-isnt-always-available-and-its-not-the-users-fault/ | full | 5 |
| as-the-problem-with-toast-messages-and-what | Adam Silver | https://adamsilver.io/blog/the-problem-with-toast-messages-and-what-to-do-instead/ | full | 5 |
| as-why-toggle-switches-suck-and-what-to-do- | Adam Silver | https://adamsilver.io/blog/why-toggle-switches-suck-and-what-to-do-instead/ | full | 5 |
| ax-apg-combobox | W3C APG task force | https://www.w3.org/WAI/ARIA/apg/patterns/combobox/ | skimmed | 8 |
| ax-apg-dialog | W3C APG task force | https://www.w3.org/WAI/ARIA/apg/patterns/dialog-modal/ | full | 8 |
| ax-apg-hiding | W3C APG task force | https://www.w3.org/WAI/ARIA/apg/practices/hiding-semantics/ | full | 4 |
| ax-apg-landmarks | W3C APG task force | https://www.w3.org/WAI/ARIA/apg/practices/landmark-regions/ | full | 10 |
| ax-apg-readme | W3C ARIA Authoring Practices (Matt King, APG task force) | https://www.w3.org/WAI/ARIA/apg/practices/read-me-first/ | full | 4 |
| ax-apg-tabs | W3C APG task force | https://www.w3.org/WAI/ARIA/apg/patterns/tabs/ | full | 5 |
| ax-giraudel | Kitty Giraudel | https://kittygiraudel.com/2020/05/18/using-calc-to-figure-out-optimal-line-height/ | full | 2 |
| ax-govuk-a11y | GOV.UK Design System team | https://www.gov.uk/service-manual/helping-people-to-use-your-service/making-your-service-accessible-an-introduction | full | 2 |
| ax-govuk-button | GOV.UK Design System team | https://design-system.service.gov.uk/components/button/ | full | 8 |
| ax-govuk-error | GOV.UK Design System team | https://design-system.service.gov.uk/components/error-message/ | full | 9 |
| ax-govuk-errsum | GOV.UK Design System team | https://design-system.service.gov.uk/components/error-summary/ | full | 8 |
| ax-govuk-js | GOV.UK Design System team | https://www.gov.uk/service-manual/technology/using-progressive-enhancement | full | 8 |
| ax-mdn-aria-live | MDN contributors | https://developer.mozilla.org/en-US/docs/Web/Accessibility/ARIA/Guides/Live_regions | full | 7 |
| ax-mdn-multimedia | MDN contributors | https://developer.mozilla.org/en-US/docs/Learn_web_development/Core/Accessibility/Multimedia | full | 7 |
| ax-pickering-box | Heydon Pickering, Andy Bell (Every Layout) | https://every-layout.dev/rudiments/boxes/ | full | 6 |
| ax-pickering-cards | Heydon Pickering | https://inclusive-components.design/cards/ | full | 13 |
| ax-pickering-global | Heydon Pickering, Andy Bell (Every Layout) | https://every-layout.dev/rudiments/global-and-local-styling/ | full | 10 |
| ax-pickering-layout | Heydon Pickering, Andy Bell (Every Layout) | https://every-layout.dev/layouts/stack/ | full | 7 |
| ax-pickering-notif | Heydon Pickering | https://inclusive-components.design/notifications/ | full | 11 |
| ax-pickering-rules | Heydon Pickering, Andy Bell (Every Layout) | https://every-layout.dev/rudiments/axioms/ | mismatch | 5 |
| ax-pickering-sidebar | Heydon Pickering, Andy Bell (Every Layout) | https://every-layout.dev/layouts/sidebar/ | full | 6 |
| ax-pickering-tabs | Heydon Pickering | https://inclusive-components.design/tabbed-interfaces/ | full | 9 |
| ax-pickering-theme | Heydon Pickering | https://inclusive-components.design/a-theme-switcher/ | full | 10 |
| ax-pickering-tooltips | Heydon Pickering | https://inclusive-components.design/tooltips-toggletips/ | full | 11 |
| ax-roselli-aria-label | Adrian Roselli | https://adrianroselli.com/2019/11/aria-label-does-not-translate.html | full | 6 |
| ax-roselli-div-links | Adrian Roselli | https://adrianroselli.com/2016/01/links-buttons-submits-and-divs-oh-hell.html | full | 8 |
| ax-sutton-links | Marcy Sutton | https://marcysutton.com/links-vs-buttons-in-modern-web-applications | full | 6 |
| ax-sutton-testing | Marcy Sutton | https://marcysutton.com/accessibility-and-performance | mismatch | 6 |
| ax-wai-tips-carousels | W3C WAI | https://www.w3.org/WAI/tutorials/carousels/ | skimmed | 3 |
| ax-wai-tips-forms | W3C WAI | https://www.w3.org/WAI/tutorials/forms/ | skimmed | 3 |
| ax-wai-tips-menus | W3C WAI | https://www.w3.org/WAI/tutorials/menus/ | skimmed | 3 |
| ax-wai-tips-tables | W3C WAI | https://www.w3.org/WAI/tutorials/tables/ | skimmed | 2 |
| ax-wai-writing | W3C WAI | https://www.w3.org/WAI/tips/developing/ | full | 10 |
| ax-watson-cursor | Leonie Watson | https://tink.uk/accessibility-support-for-css-generated-content/ | full | 2 |
| ax-watson-tree | Leonie Watson | https://tink.uk/understanding-screen-reader-interaction-modes/ | full | 3 |
| ax-wcag-autocomplete | W3C WCAG WG | https://www.w3.org/WAI/WCAG22/Understanding/identify-input-purpose.html | full | 5 |
| ax-wcag-focus-order | W3C WCAG WG | https://www.w3.org/WAI/WCAG22/Understanding/focus-order.html | full | 5 |
| ax-wcag-labels | W3C WCAG WG | https://www.w3.org/WAI/WCAG22/Understanding/labels-or-instructions.html | full | 6 |
| ax-wcag-pointer | W3C WCAG WG | https://www.w3.org/WAI/WCAG22/Understanding/pointer-cancellation.html | full | 5 |
| ax-wcag-timing | W3C WCAG WG | https://www.w3.org/WAI/WCAG22/Understanding/timing-adjustable.html | full | 5 |
| ax-webaim-alt | Jared Smith (WebAIM) | https://webaim.org/techniques/alttext/ | full | 10 |
| ax-webaim-contrast | WebAIM | https://webaim.org/articles/contrast/ | full | 9 |
| ax-webaim-hidden | WebAIM | https://webaim.org/techniques/css/invisiblecontent/ | full | 6 |
| ax-webaim-keyboard | WebAIM | https://webaim.org/techniques/keyboard/ | full | 10 |
| ax-webaim-million | Jared Smith (WebAIM) | https://webaim.org/projects/million/ | full | 12 |
| ax-webaim-screenreader | WebAIM | https://webaim.org/projects/screenreadersurvey10/ | full | 7 |
| ax-webaim-skipnav | WebAIM | https://webaim.org/techniques/skipnav/ | full | 6 |
| cs-dalgleish | Mark Dalgleish | https://github.com/css-modules/css-modules | skimmed | 1 |
| cs-mdn-custom-props | MDN contributors | https://developer.mozilla.org/en-US/docs/Web/CSS/Using_CSS_custom_properties | full | 6 |
| cs-mdn-mem | MDN contributors | https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide/Memory_management | full | 3 |
| cs-mdn-sec-csrf | MDN contributors | https://developer.mozilla.org/en-US/docs/Web/Security/Attacks/CSRF | full | 6 |
| cs-mdn-sec-tt | MDN contributors | https://developer.mozilla.org/en-US/docs/Web/API/Trusted_Types_API | full | 7 |
| cs-mdn-sec-xss | MDN contributors | https://developer.mozilla.org/en-US/docs/Web/Security/Attacks/XSS | full | 9 |
| cs-owasp-dompurify | OWASP Cheat Sheet Series | https://raw.githubusercontent.com/OWASP/CheatSheetSeries/master/cheatsheets/DOM_Clobbering_Prevention_Cheat_Sheet.md | mismatch | 10 |
| cs-owasp-file-upload | OWASP Cheat Sheet Series | https://raw.githubusercontent.com/OWASP/CheatSheetSeries/master/cheatsheets/File_Upload_Cheat_Sheet.md | skimmed | 5 |
| cs-owasp-oauth | OWASP Cheat Sheet Series | https://raw.githubusercontent.com/OWASP/CheatSheetSeries/master/cheatsheets/OAuth2_Cheat_Sheet.md | skimmed | 7 |
| cs-owasp-sri | OWASP Cheat Sheet Series | https://raw.githubusercontent.com/OWASP/CheatSheetSeries/master/cheatsheets/Browser_Extension_Vulnerabilities_Cheat_Sheet.md | mismatch | 0 |
| cs-webdev-a11y-cls | web.dev / v8.dev (Chrome team; individual authors not verified) | https://web.dev/articles/cls | full | 7 |
| cs-webdev-a11y-focus | web.dev / v8.dev (Chrome team; individual authors not verified) | https://web.dev/articles/focus | full | 6 |
| cs-webdev-cache | web.dev / v8.dev (Chrome team; individual authors not verified) | https://web.dev/articles/http-cache | full | 4 |
| cs-webdev-coop | web.dev / v8.dev (Chrome team; individual authors not verified) | https://web.dev/articles/coop-coep | full | 4 |
| cs-webdev-lazy | web.dev / v8.dev (Chrome team; individual authors not verified) | https://web.dev/articles/lazy-loading-images | full | 4 |
| cs-webdev-tt | web.dev / v8.dev (Chrome team; individual authors not verified) | https://web.dev/articles/trusted-types | full | 8 |
| esl-array-callback-return | ESLint core team (rule doc) | https://raw.githubusercontent.com/eslint/eslint/main/docs/src/rules/array-callback-return.md | catalogue | 1 |
| esl-complexity | ESLint core team (rule doc) | https://raw.githubusercontent.com/eslint/eslint/main/docs/src/rules/complexity.md | catalogue | 1 |
| esl-default-case-last | ESLint core team (rule doc) | https://raw.githubusercontent.com/eslint/eslint/main/docs/src/rules/default-case-last.md | catalogue | 1 |
| esl-eqeqeq | ESLint core team (rule doc) | https://raw.githubusercontent.com/eslint/eslint/main/docs/src/rules/eqeqeq.md | catalogue | 1 |
| esl-max-depth | ESLint core team (rule doc) | https://raw.githubusercontent.com/eslint/eslint/main/docs/src/rules/max-depth.md | catalogue | 1 |
| esl-max-lines-per-function | ESLint core team (rule doc) | https://raw.githubusercontent.com/eslint/eslint/main/docs/src/rules/max-lines-per-function.md | catalogue | 1 |
| esl-no-await-in-loop | ESLint core team (rule doc) | https://raw.githubusercontent.com/eslint/eslint/main/docs/src/rules/no-await-in-loop.md | catalogue | 1 |
| esl-no-console | ESLint core team (rule doc) | https://raw.githubusercontent.com/eslint/eslint/main/docs/src/rules/no-console.md | catalogue | 1 |
| esl-no-constant-condition | ESLint core team (rule doc) | https://raw.githubusercontent.com/eslint/eslint/main/docs/src/rules/no-constant-condition.md | catalogue | 1 |
| esl-no-else-return | ESLint core team (rule doc) | https://raw.githubusercontent.com/eslint/eslint/main/docs/src/rules/no-else-return.md | catalogue | 1 |
| esl-no-empty | ESLint core team (rule doc) | https://raw.githubusercontent.com/eslint/eslint/main/docs/src/rules/no-empty.md | catalogue | 1 |
| esl-no-eval | ESLint core team (rule doc) | https://raw.githubusercontent.com/eslint/eslint/main/docs/src/rules/no-eval.md | catalogue | 1 |
| esl-no-implied-eval | ESLint core team (rule doc) | https://raw.githubusercontent.com/eslint/eslint/main/docs/src/rules/no-implied-eval.md | catalogue | 1 |
| esl-no-inline-comments | ESLint core team (rule doc) | https://raw.githubusercontent.com/eslint/eslint/main/docs/src/rules/no-inline-comments.md | catalogue | 1 |
| esl-no-loop-func | ESLint core team (rule doc) | https://raw.githubusercontent.com/eslint/eslint/main/docs/src/rules/no-loop-func.md | catalogue | 1 |
| esl-no-nested-ternary | ESLint core team (rule doc) | https://raw.githubusercontent.com/eslint/eslint/main/docs/src/rules/no-nested-ternary.md | catalogue | 1 |
| esl-no-new-func | ESLint core team (rule doc) | https://raw.githubusercontent.com/eslint/eslint/main/docs/src/rules/no-new-func.md | catalogue | 1 |
| esl-no-param-reassign | ESLint core team (rule doc) | https://raw.githubusercontent.com/eslint/eslint/main/docs/src/rules/no-param-reassign.md | catalogue | 1 |
| esl-no-promise-executor-return | ESLint core team (rule doc) | https://raw.githubusercontent.com/eslint/eslint/main/docs/src/rules/no-promise-executor-return.md | catalogue | 1 |
| esl-no-prototype-builtins | ESLint core team (rule doc) | https://raw.githubusercontent.com/eslint/eslint/main/docs/src/rules/no-prototype-builtins.md | catalogue | 1 |
| esl-no-restricted-globals | ESLint core team (rule doc) | https://raw.githubusercontent.com/eslint/eslint/main/docs/src/rules/no-restricted-globals.md | catalogue | 1 |
| esl-no-return-assign | ESLint core team (rule doc) | https://raw.githubusercontent.com/eslint/eslint/main/docs/src/rules/no-return-assign.md | catalogue | 1 |
| esl-no-script-url | ESLint core team (rule doc) | https://raw.githubusercontent.com/eslint/eslint/main/docs/src/rules/no-script-url.md | catalogue | 1 |
| esl-no-sequences | ESLint core team (rule doc) | https://raw.githubusercontent.com/eslint/eslint/main/docs/src/rules/no-sequences.md | catalogue | 1 |
| esl-no-shadow | ESLint core team (rule doc) | https://raw.githubusercontent.com/eslint/eslint/main/docs/src/rules/no-shadow.md | catalogue | 1 |
| esl-no-throw-literal | ESLint core team (rule doc) | https://raw.githubusercontent.com/eslint/eslint/main/docs/src/rules/no-throw-literal.md | catalogue | 1 |
| esl-no-unsafe-optional-chaining | ESLint core team (rule doc) | https://raw.githubusercontent.com/eslint/eslint/main/docs/src/rules/no-unsafe-optional-chaining.md | catalogue | 1 |
| esl-no-unused-vars | ESLint core team (rule doc) | https://raw.githubusercontent.com/eslint/eslint/main/docs/src/rules/no-unused-vars.md | catalogue | 1 |
| esl-no-useless-catch | ESLint core team (rule doc) | https://raw.githubusercontent.com/eslint/eslint/main/docs/src/rules/no-useless-catch.md | catalogue | 1 |
| esl-prefer-const | ESLint core team (rule doc) | https://raw.githubusercontent.com/eslint/eslint/main/docs/src/rules/prefer-const.md | catalogue | 1 |
| esl-require-atomic-updates | ESLint core team (rule doc) | https://raw.githubusercontent.com/eslint/eslint/main/docs/src/rules/require-atomic-updates.md | catalogue | 1 |
| fw-astro-env | Astro team | https://docs.astro.build/en/guides/environment-variables/ | full | 5 |
| fw-astro-perf | Astro team | https://docs.astro.build/en/guides/troubleshooting/ | mismatch | 5 |
| fw-astro-sec | Astro team | https://docs.astro.build/en/reference/configuration-reference/ | skimmed | 10 |
| fw-cy-conditional | Cypress team | https://docs.cypress.io/app/guides/conditional-testing | full | 3 |
| fw-cy-retry | Cypress team | https://docs.cypress.io/app/core-concepts/retry-ability | full | 7 |
| fw-jest-mock | Jest team | https://jestjs.io/docs/mock-functions | full | 5 |
| fw-jest-snap | Jest team | https://jestjs.io/docs/snapshot-testing | full | 7 |
| fw-js-import | Benjamin Mosior, eslint-plugin-import maintainers | https://raw.githubusercontent.com/import-js/eslint-plugin-import/main/docs/rules/no-cycle.md | catalogue | 1 |
| fw-js-import2 | eslint-plugin-import maintainers | https://raw.githubusercontent.com/import-js/eslint-plugin-import/main/docs/rules/no-default-export.md | catalogue | 1 |
| fw-js-import3 | eslint-plugin-import maintainers | https://raw.githubusercontent.com/import-js/eslint-plugin-import/main/docs/rules/no-extraneous-dependencies.md | catalogue | 1 |
| fw-js-import4 | eslint-plugin-import maintainers | https://raw.githubusercontent.com/import-js/eslint-plugin-import/main/docs/rules/no-internal-modules.md | catalogue | 1 |
| fw-js-import5 | eslint-plugin-import maintainers | https://raw.githubusercontent.com/import-js/eslint-plugin-import/main/docs/rules/no-relative-parent-imports.md | catalogue | 1 |
| fw-js-import6 | eslint-plugin-import maintainers | https://raw.githubusercontent.com/import-js/eslint-plugin-import/main/docs/rules/no-restricted-paths.md | catalogue | 1 |
| fw-js-import7 | eslint-plugin-import maintainers | https://raw.githubusercontent.com/import-js/eslint-plugin-import/main/docs/rules/no-unused-modules.md | catalogue | 1 |
| fw-js-import8 | eslint-plugin-import maintainers | https://raw.githubusercontent.com/import-js/eslint-plugin-import/main/docs/rules/no-mutable-exports.md | catalogue | 1 |
| fw-js-jest1 | eslint-plugin-jest maintainers (Jest community) | https://raw.githubusercontent.com/jest-community/eslint-plugin-jest/main/docs/rules/expect-expect.md | catalogue | 1 |
| fw-js-jest10 | eslint-plugin-jest maintainers | https://raw.githubusercontent.com/jest-community/eslint-plugin-jest/main/docs/rules/no-done-callback.md | catalogue | 1 |
| fw-js-jest11 | eslint-plugin-jest maintainers | https://raw.githubusercontent.com/jest-community/eslint-plugin-jest/main/docs/rules/no-identical-title.md | catalogue | 1 |
| fw-js-jest12 | eslint-plugin-jest maintainers | https://raw.githubusercontent.com/jest-community/eslint-plugin-jest/main/docs/rules/require-top-level-describe.md | catalogue | 1 |
| fw-js-jest13 | eslint-plugin-jest maintainers | https://raw.githubusercontent.com/jest-community/eslint-plugin-jest/main/docs/rules/prefer-strict-equal.md | catalogue | 1 |
| fw-js-jest14 | eslint-plugin-jest maintainers | https://raw.githubusercontent.com/jest-community/eslint-plugin-jest/main/docs/rules/no-mocks-import.md | catalogue | 1 |
| fw-js-jest15 | eslint-plugin-jest maintainers | https://raw.githubusercontent.com/jest-community/eslint-plugin-jest/main/docs/rules/no-interpolation-in-snapshots.md | catalogue | 1 |
| fw-js-jest2 | eslint-plugin-jest maintainers | https://raw.githubusercontent.com/jest-community/eslint-plugin-jest/main/docs/rules/no-conditional-expect.md | catalogue | 1 |
| fw-js-jest3 | eslint-plugin-jest maintainers | https://raw.githubusercontent.com/jest-community/eslint-plugin-jest/main/docs/rules/no-standalone-expect.md | catalogue | 1 |
| fw-js-jest4 | eslint-plugin-jest maintainers | https://raw.githubusercontent.com/jest-community/eslint-plugin-jest/main/docs/rules/no-disabled-tests.md | catalogue | 1 |
| fw-js-jest5 | eslint-plugin-jest maintainers | https://raw.githubusercontent.com/jest-community/eslint-plugin-jest/main/docs/rules/no-focused-tests.md | catalogue | 1 |
| fw-js-jest6 | eslint-plugin-jest maintainers | https://raw.githubusercontent.com/jest-community/eslint-plugin-jest/main/docs/rules/no-conditional-in-test.md | catalogue | 1 |
| fw-js-jest7 | eslint-plugin-jest maintainers | https://raw.githubusercontent.com/jest-community/eslint-plugin-jest/main/docs/rules/no-large-snapshots.md | catalogue | 1 |
| fw-js-jest8 | eslint-plugin-jest maintainers | https://raw.githubusercontent.com/jest-community/eslint-plugin-jest/main/docs/rules/valid-title.md | catalogue | 1 |
| fw-js-jest9 | eslint-plugin-jest maintainers | https://raw.githubusercontent.com/jest-community/eslint-plugin-jest/main/docs/rules/prefer-expect-assertions.md | catalogue | 1 |
| fw-js-jestdom | Testing Library (eslint-plugin-jest-dom) | https://raw.githubusercontent.com/testing-library/eslint-plugin-jest-dom/main/README.md | catalogue | 1 |
| fw-js-scope | Kyle Simpson | https://raw.githubusercontent.com/getify/You-Dont-Know-JS/2nd-ed/scope-closures/ch6.md | skimmed | 5 |
| fw-js-sorhus2 | Sindre Sorhus | https://raw.githubusercontent.com/sindresorhus/eslint-plugin-unicorn/main/docs/rules/prefer-add-event-listener.md | catalogue | 1 |
| fw-js-sorhus3 | Sindre Sorhus | https://raw.githubusercontent.com/sindresorhus/eslint-plugin-unicorn/main/docs/rules/no-null.md | catalogue | 1 |
| fw-js-sorhus4 | Sindre Sorhus | https://raw.githubusercontent.com/sindresorhus/eslint-plugin-unicorn/main/docs/rules/prefer-query-selector.md | catalogue | 1 |
| fw-js-sorhus5 | Sindre Sorhus | https://raw.githubusercontent.com/sindresorhus/eslint-plugin-unicorn/main/docs/rules/no-abusive-eslint-disable.md | catalogue | 1 |
| fw-js-sorhus6 | Sindre Sorhus | https://raw.githubusercontent.com/sindresorhus/eslint-plugin-unicorn/main/docs/rules/prefer-dom-node-text-content.md | catalogue | 1 |
| fw-js-sorhus7 | Sindre Sorhus | https://raw.githubusercontent.com/sindresorhus/eslint-plugin-unicorn/main/docs/rules/no-await-expression-member.md | catalogue | 1 |
| fw-js-sorhus8 | Sindre Sorhus | https://raw.githubusercontent.com/sindresorhus/eslint-plugin-unicorn/main/docs/rules/prefer-global-this.md | catalogue | 1 |
| fw-js-this | Kyle Simpson | https://raw.githubusercontent.com/getify/You-Dont-Know-JS/2nd-ed/get-started/ch4.md | irrelevant | 0 |
| fw-js-tw1 | eslint-plugin-tailwindcss maintainers (Francois Massart) | https://raw.githubusercontent.com/francoismassart/eslint-plugin-tailwindcss/master/docs/rules/no-contradicting-classname.md | catalogue | 1 |
| fw-js-tw2 | eslint-plugin-tailwindcss maintainers | https://raw.githubusercontent.com/francoismassart/eslint-plugin-tailwindcss/master/docs/rules/no-custom-classname.md | catalogue | 1 |
| fw-js-tw3 | eslint-plugin-tailwindcss maintainers | https://raw.githubusercontent.com/francoismassart/eslint-plugin-tailwindcss/master/docs/rules/enforces-shorthand.md | catalogue | 1 |
| fw-js-tw4 | eslint-plugin-tailwindcss maintainers | https://raw.githubusercontent.com/francoismassart/eslint-plugin-tailwindcss/master/docs/rules/classnames-order.md | catalogue | 1 |
| fw-markbage-1 | Sebastian Markbage | https://github.com/reactjs/react-basic | skimmed | 3 |
| fw-markbage-3 | Sebastian Markbage | https://react.dev/blog/2023/03/16/introducing-react-dev | irrelevant | 0 |
| fw-msw-structure | Artem Zakharchenko (Mock Service Worker) | https://mswjs.io/docs/best-practices/structuring-handlers | full | 2 |
| fw-msw-typescript | Artem Zakharchenko (Mock Service Worker) | https://mswjs.io/docs/best-practices/typescript | full | 3 |
| fw-next-composition | Next.js team (Vercel) | https://nextjs.org/docs/app/getting-started/server-and-client-components | full | 8 |
| fw-next-csp | Next.js team (Vercel) | https://nextjs.org/docs/app/guides/content-security-policy | full | 8 |
| fw-next-data-sec | Next.js team (Vercel) | https://nextjs.org/docs/app/guides/data-security | full | 12 |
| fw-next-env | Next.js team (Vercel) | https://nextjs.org/docs/app/guides/environment-variables | full | 6 |
| fw-next-fetching | Next.js team (Vercel) | https://nextjs.org/docs/app/getting-started/fetching-data | full | 6 |
| fw-next-forms | Next.js team (Vercel) | https://nextjs.org/docs/app/guides/forms | full | 9 |
| fw-pw-a11y | Playwright team (Microsoft) | https://playwright.dev/docs/accessibility-testing | full | 7 |
| fw-pw-assert | Playwright team (Microsoft) | https://playwright.dev/docs/test-assertions | full | 5 |
| fw-pw-best | Playwright team (Microsoft) | https://playwright.dev/docs/best-practices | full | 8 |
| fw-radix-a11y | Radix UI (WorkOS) | https://www.radix-ui.com/primitives/docs/overview/accessibility | full | 3 |
| fw-radix-as | Radix UI (WorkOS) | https://www.radix-ui.com/primitives/docs/guides/composition | full | 3 |
| fw-react-19 | React team | https://react.dev/blog/2024/12/05/react-19 | full | 11 |
| fw-react-aria-focus | Adobe React Aria team | https://react-spectrum.adobe.com/blog/building-a-combobox.html | full | 7 |
| fw-react-aria-interactions | Adobe React Aria team | https://react-spectrum.adobe.com/blog/building-a-button-part-1.html | full | 5 |
| fw-react-compiler-dir | React team | https://react.dev/reference/react-compiler/directives | full | 4 |
| fw-react-error-boundary | Brian Vaughn (react-error-boundary) | https://github.com/bvaughn/react-error-boundary | full | 4 |
| fw-react-keys | Dan Abramov | https://overreacted.io/why-do-we-write-super-props/ | mismatch | 1 |
| fw-react-security-2025 | React team | https://react.dev/blog/2025/12/03/critical-security-vulnerability-in-react-server-components | full | 3 |
| fw-react-server-components | React team | https://react.dev/reference/rsc/server-components | full | 4 |
| fw-react-use-client | React team | https://react.dev/reference/rsc/use-client | full | 7 |
| fw-react-use-server | React team | https://react.dev/reference/rsc/use-server | full | 7 |
| fw-redux-forms | Redux maintainers | https://redux.js.org/faq/actions | mismatch | 5 |
| fw-redux-pitfalls | Redux maintainers | https://redux.js.org/faq/immutable-data | full | 5 |
| fw-remix-philosophy | Remix team | https://remix.run/docs/en/main/discussion/introduction | full | 4 |
| fw-remix-state | Remix team | https://remix.run/docs/en/main/discussion/state-management | full | 7 |
| fw-rhf-docs | React Hook Form team (Bill Luo) | https://react-hook-form.com/advanced-usage | skimmed | 10 |
| fw-rhf-faq | React Hook Form team | https://react-hook-form.com/faqs | full | 8 |
| fw-rhf-ts | React Hook Form team | https://react-hook-form.com/ts | skimmed | 2 |
| fw-sentry-react | Sentry | https://docs.sentry.io/platforms/javascript/guides/react/features/error-boundary/ | full | 5 |
| fw-sl1 | Stylelint team (Richard Hallows, Mark Dalgleish et al.) | https://raw.githubusercontent.com/stylelint/stylelint/main/lib/rules/no-descending-specificity/README.md | catalogue | 1 |
| fw-sl10 | Stylelint team | https://raw.githubusercontent.com/stylelint/stylelint/main/lib/rules/selector-max-compound-selectors/README.md | catalogue | 1 |
| fw-sl11 | Stylelint team | https://raw.githubusercontent.com/stylelint/stylelint/main/lib/rules/no-invalid-position-at-import-rule/README.md | catalogue | 1 |
| fw-sl12 | Stylelint team | https://raw.githubusercontent.com/stylelint/stylelint/main/lib/rules/selector-class-pattern/README.md | catalogue | 1 |
| fw-sl13 | Stylelint team | https://raw.githubusercontent.com/stylelint/stylelint/main/lib/rules/color-named/README.md | catalogue | 1 |
| fw-sl14 | Stylelint team | https://raw.githubusercontent.com/stylelint/stylelint/main/lib/rules/property-no-vendor-prefix/README.md | catalogue | 1 |
| fw-sl15 | Stylelint team | https://raw.githubusercontent.com/stylelint/stylelint/main/lib/rules/no-unknown-custom-properties/README.md | catalogue | 1 |
| fw-sl16 | Stylelint team | https://raw.githubusercontent.com/stylelint/stylelint/main/lib/rules/selector-no-qualifying-type/README.md | catalogue | 1 |
| fw-sl17 | Stylelint team | https://raw.githubusercontent.com/stylelint/stylelint/main/lib/rules/max-nesting-depth/README.md | catalogue | 1 |
| fw-sl18 | Stylelint team | https://raw.githubusercontent.com/stylelint/stylelint/main/lib/rules/function-url-no-scheme-relative/README.md | catalogue | 1 |
| fw-sl19 | Stylelint team | https://raw.githubusercontent.com/stylelint/stylelint/main/lib/rules/length-zero-no-unit/README.md | catalogue | 1 |
| fw-sl2 | Stylelint team | https://raw.githubusercontent.com/stylelint/stylelint/main/lib/rules/declaration-no-important/README.md | catalogue | 1 |
| fw-sl20 | Stylelint team | https://raw.githubusercontent.com/stylelint/stylelint/main/lib/rules/declaration-block-no-shorthand-property-overrides/README.md | catalogue | 1 |
| fw-sl3 | Stylelint team | https://raw.githubusercontent.com/stylelint/stylelint/main/lib/rules/selector-max-id/README.md | catalogue | 1 |
| fw-sl4 | Stylelint team | https://raw.githubusercontent.com/stylelint/stylelint/main/lib/rules/selector-max-specificity/README.md | catalogue | 1 |
| fw-sl5 | Stylelint team | https://raw.githubusercontent.com/stylelint/stylelint/main/lib/rules/font-family-no-missing-generic-family-keyword/README.md | catalogue | 1 |
| fw-sl6 | Stylelint team | https://raw.githubusercontent.com/stylelint/stylelint/main/lib/rules/declaration-block-no-duplicate-properties/README.md | catalogue | 1 |
| fw-sl7 | Stylelint team | https://raw.githubusercontent.com/stylelint/stylelint/main/lib/rules/no-duplicate-selectors/README.md | catalogue | 1 |
| fw-sl8 | Stylelint team | https://raw.githubusercontent.com/stylelint/stylelint/main/lib/rules/declaration-property-value-no-unknown/README.md | catalogue | 1 |
| fw-sl9 | Stylelint team | https://raw.githubusercontent.com/stylelint/stylelint/main/lib/rules/unit-disallowed-list/README.md | catalogue | 1 |
| fw-storybook-a11y | Storybook team | https://storybook.js.org/docs/writing-tests/accessibility-testing | full | 8 |
| fw-tl-queries | Testing Library team | https://testing-library.com/docs/queries/about/ | full | 7 |
| fw-tl-setup | Testing Library team | https://testing-library.com/docs/react-testing-library/setup/ | full | 4 |
| fw-tw-adding-custom | Tailwind Labs | https://tailwindcss.com/docs/adding-custom-styles | full | 8 |
| fw-tw-responsive | Tailwind Labs | https://tailwindcss.com/docs/responsive-design | full | 5 |
| fw-tw-reuse | Tailwind Labs (Adam Wathan) | https://tailwindcss.com/docs/reusing-styles | full | 8 |
| fw-tw-utility | Tailwind Labs (Adam Wathan) | https://tailwindcss.com/docs/styling-with-utility-classes | full | 4 |
| fw-tw-wathan-utility | Adam Wathan | https://adamwathan.me/css-utility-classes-and-separation-of-concerns/ | full | 6 |
| fw-vite-build | Vite team | https://vite.dev/guide/build | full | 5 |
| fw-vite-features | Vite team (Evan You, Anthony Fu) | https://vite.dev/guide/features | full | 14 |
| fw-vite-troubleshoot | Vite team | https://vite.dev/guide/troubleshooting | full | 8 |
| fw-vitest-browser | Vitest team | https://vitest.dev/guide/browser/ | skimmed | 4 |
| fw-vitest-cov | Vitest team | https://vitest.dev/guide/coverage.html | full | 4 |
| fw-vitest-mock | Vitest team (Anthony Fu, Vladimir Sheremet) | https://vitest.dev/guide/mocking.html | full | 5 |
| fw-zod-basics | Colin McDonnell (Zod) | https://zod.dev/basics | full | 4 |
| fw-zod-errors | Colin McDonnell (Zod) | https://zod.dev/error-customization | full | 4 |
| hd-accessible-front-end-components-claims-v | Hidde de Vries | https://hidde.blog/accessible-front-end-components-claims-vs-reality/ | full | 3 |
| hd-accessible-page-titles-in-a-single-page- | Hidde de Vries | https://hidde.blog/accessible-page-titles-in-a-single-page-app/ | full | 6 |
| hd-accessibly-labelling-interactive-element | Hidde de Vries | https://hidde.blog/accessibly-labelling-interactive-elements/ | full | 7 |
| hd-baking-accessibility-into-components-how | Hidde de Vries | https://hidde.blog/baking-accessibility-into-components-how-frameworks-help/ | full | 5 |
| hd-better-accessible-names | Hidde de Vries | https://hidde.blog/better-accessible-names/ | full | 7 |
| hr-a-layered-approach-to-speculation-rules | Harry Roberts | https://csswizardry.com/2024/12/a-layered-approach-to-speculation-rules/ | full | 4 |
| hr-code-smells-in-css | Harry Roberts | https://csswizardry.com/2012/11/code-smells-in-css/ | coordinator-read | 8 |
| hr-code-smells-in-css-revisited | Harry Roberts | https://csswizardry.com/2017/02/code-smells-in-css-revisited/ | coordinator-read | 6 |
| hr-css-shorthand-syntax-considered-an-anti- | Harry Roberts | https://csswizardry.com/2016/12/css-shorthand-syntax-considered-an-anti-pattern/ | coordinator-read | 1 |
| hr-cyclomatic-complexity-logic-in-css | Harry Roberts | https://csswizardry.com/2015/04/cyclomatic-complexity-logic-in-css/ | coordinator-read | 1 |
| hr-finding-dead-css | Harry Roberts | https://csswizardry.com/2018/01/finding-dead-css/ | coordinator-read | 1 |
| hr-identifying-auditing-discussing-third-pa | Harry Roberts | https://csswizardry.com/2018/05/identifying-auditing-discussing-third-parties/ | full | 2 |
| hr-self-host-your-static-assets | Harry Roberts | https://csswizardry.com/2019/05/self-host-your-static-assets/ | full | 5 |
| ja-alt-text | eslint-plugin-jsx-a11y maintainers (rule doc) | https://raw.githubusercontent.com/jsx-eslint/eslint-plugin-jsx-a11y/main/docs/rules/alt-text.md | catalogue | 1 |
| ja-anchor-ambiguous-text | eslint-plugin-jsx-a11y maintainers (rule doc) | https://raw.githubusercontent.com/jsx-eslint/eslint-plugin-jsx-a11y/main/docs/rules/anchor-ambiguous-text.md | catalogue | 1 |
| ja-anchor-has-content | eslint-plugin-jsx-a11y maintainers (rule doc) | https://raw.githubusercontent.com/jsx-eslint/eslint-plugin-jsx-a11y/main/docs/rules/anchor-has-content.md | catalogue | 1 |
| ja-anchor-is-valid | eslint-plugin-jsx-a11y maintainers (rule doc) | https://raw.githubusercontent.com/jsx-eslint/eslint-plugin-jsx-a11y/main/docs/rules/anchor-is-valid.md | catalogue | 1 |
| ja-aria-props | eslint-plugin-jsx-a11y maintainers (rule doc) | https://raw.githubusercontent.com/jsx-eslint/eslint-plugin-jsx-a11y/main/docs/rules/aria-props.md | catalogue | 1 |
| ja-aria-role | eslint-plugin-jsx-a11y maintainers (rule doc) | https://raw.githubusercontent.com/jsx-eslint/eslint-plugin-jsx-a11y/main/docs/rules/aria-role.md | catalogue | 1 |
| ja-autocomplete-valid | eslint-plugin-jsx-a11y maintainers (rule doc) | https://raw.githubusercontent.com/jsx-eslint/eslint-plugin-jsx-a11y/main/docs/rules/autocomplete-valid.md | catalogue | 1 |
| ja-click-events-have-key-events | eslint-plugin-jsx-a11y maintainers (rule doc) | https://raw.githubusercontent.com/jsx-eslint/eslint-plugin-jsx-a11y/main/docs/rules/click-events-have-key-events.md | catalogue | 1 |
| ja-control-has-associated-label | eslint-plugin-jsx-a11y maintainers (rule doc) | https://raw.githubusercontent.com/jsx-eslint/eslint-plugin-jsx-a11y/main/docs/rules/control-has-associated-label.md | catalogue | 1 |
| ja-heading-has-content | eslint-plugin-jsx-a11y maintainers (rule doc) | https://raw.githubusercontent.com/jsx-eslint/eslint-plugin-jsx-a11y/main/docs/rules/heading-has-content.md | catalogue | 1 |
| ja-html-has-lang | eslint-plugin-jsx-a11y maintainers (rule doc) | https://raw.githubusercontent.com/jsx-eslint/eslint-plugin-jsx-a11y/main/docs/rules/html-has-lang.md | catalogue | 1 |
| ja-iframe-has-title | eslint-plugin-jsx-a11y maintainers (rule doc) | https://raw.githubusercontent.com/jsx-eslint/eslint-plugin-jsx-a11y/main/docs/rules/iframe-has-title.md | catalogue | 1 |
| ja-img-redundant-alt | eslint-plugin-jsx-a11y maintainers (rule doc) | https://raw.githubusercontent.com/jsx-eslint/eslint-plugin-jsx-a11y/main/docs/rules/img-redundant-alt.md | catalogue | 1 |
| ja-interactive-supports-focus | eslint-plugin-jsx-a11y maintainers (rule doc) | https://raw.githubusercontent.com/jsx-eslint/eslint-plugin-jsx-a11y/main/docs/rules/interactive-supports-focus.md | catalogue | 1 |
| ja-label-has-associated-control | eslint-plugin-jsx-a11y maintainers (rule doc) | https://raw.githubusercontent.com/jsx-eslint/eslint-plugin-jsx-a11y/main/docs/rules/label-has-associated-control.md | catalogue | 1 |
| ja-lang | eslint-plugin-jsx-a11y maintainers (rule doc) | https://raw.githubusercontent.com/jsx-eslint/eslint-plugin-jsx-a11y/main/docs/rules/lang.md | catalogue | 1 |
| ja-media-has-caption | eslint-plugin-jsx-a11y maintainers (rule doc) | https://raw.githubusercontent.com/jsx-eslint/eslint-plugin-jsx-a11y/main/docs/rules/media-has-caption.md | catalogue | 1 |
| ja-mouse-events-have-key-events | eslint-plugin-jsx-a11y maintainers (rule doc) | https://raw.githubusercontent.com/jsx-eslint/eslint-plugin-jsx-a11y/main/docs/rules/mouse-events-have-key-events.md | catalogue | 1 |
| ja-no-access-key | eslint-plugin-jsx-a11y maintainers (rule doc) | https://raw.githubusercontent.com/jsx-eslint/eslint-plugin-jsx-a11y/main/docs/rules/no-access-key.md | catalogue | 1 |
| ja-no-aria-hidden-on-focusable | eslint-plugin-jsx-a11y maintainers (rule doc) | https://raw.githubusercontent.com/jsx-eslint/eslint-plugin-jsx-a11y/main/docs/rules/no-aria-hidden-on-focusable.md | catalogue | 1 |
| ja-no-autofocus | eslint-plugin-jsx-a11y maintainers (rule doc) | https://raw.githubusercontent.com/jsx-eslint/eslint-plugin-jsx-a11y/main/docs/rules/no-autofocus.md | catalogue | 1 |
| ja-no-distracting-elements | eslint-plugin-jsx-a11y maintainers (rule doc) | https://raw.githubusercontent.com/jsx-eslint/eslint-plugin-jsx-a11y/main/docs/rules/no-distracting-elements.md | catalogue | 1 |
| ja-no-interactive-element-to-noninteractive-role | eslint-plugin-jsx-a11y maintainers (rule doc) | https://raw.githubusercontent.com/jsx-eslint/eslint-plugin-jsx-a11y/main/docs/rules/no-interactive-element-to-noninteractive-role.md | catalogue | 1 |
| ja-no-noninteractive-element-interactions | eslint-plugin-jsx-a11y maintainers (rule doc) | https://raw.githubusercontent.com/jsx-eslint/eslint-plugin-jsx-a11y/main/docs/rules/no-noninteractive-element-interactions.md | catalogue | 1 |
| ja-no-noninteractive-tabindex | eslint-plugin-jsx-a11y maintainers (rule doc) | https://raw.githubusercontent.com/jsx-eslint/eslint-plugin-jsx-a11y/main/docs/rules/no-noninteractive-tabindex.md | catalogue | 1 |
| ja-no-redundant-roles | eslint-plugin-jsx-a11y maintainers (rule doc) | https://raw.githubusercontent.com/jsx-eslint/eslint-plugin-jsx-a11y/main/docs/rules/no-redundant-roles.md | catalogue | 1 |
| ja-no-static-element-interactions | eslint-plugin-jsx-a11y maintainers (rule doc) | https://raw.githubusercontent.com/jsx-eslint/eslint-plugin-jsx-a11y/main/docs/rules/no-static-element-interactions.md | catalogue | 1 |
| ja-prefer-tag-over-role | eslint-plugin-jsx-a11y maintainers (rule doc) | https://raw.githubusercontent.com/jsx-eslint/eslint-plugin-jsx-a11y/main/docs/rules/prefer-tag-over-role.md | catalogue | 1 |
| ja-role-has-required-aria-props | eslint-plugin-jsx-a11y maintainers (rule doc) | https://raw.githubusercontent.com/jsx-eslint/eslint-plugin-jsx-a11y/main/docs/rules/role-has-required-aria-props.md | catalogue | 1 |
| ja-role-supports-aria-props | eslint-plugin-jsx-a11y maintainers (rule doc) | https://raw.githubusercontent.com/jsx-eslint/eslint-plugin-jsx-a11y/main/docs/rules/role-supports-aria-props.md | catalogue | 1 |
| ja-scope | eslint-plugin-jsx-a11y maintainers (rule doc) | https://raw.githubusercontent.com/jsx-eslint/eslint-plugin-jsx-a11y/main/docs/rules/scope.md | catalogue | 1 |
| ja-tabindex-no-positive | eslint-plugin-jsx-a11y maintainers (rule doc) | https://raw.githubusercontent.com/jsx-eslint/eslint-plugin-jsx-a11y/main/docs/rules/tabindex-no-positive.md | catalogue | 1 |
| ja2-give-footnotes-the-boot | Jake Archibald | https://jakearchibald.com/2025/give-footnotes-the-boot/ | full | 4 |
| jc-css-vs-javascript | Josh Comeau | https://www.joshwcomeau.com/animation/css-vs-javascript/ | full | 5 |
| jc-starting-style | Josh Comeau | https://www.joshwcomeau.com/css/starting-style/ | full | 4 |
| lv-dark-mode-toggles | Lea Verou | https://lea.verou.me/blog/2026/dark-mode-toggles/ | full | 3 |
| lv-wcs-vs-frameworks | Lea Verou | https://lea.verou.me/blog/2024/wcs-vs-frameworks/ | full | 2 |
| mm-aria-haspopup-menu | Manuel Matuzovic | https://www.matuzo.at/blog/2026/aria-haspopup-menu | full | 3 |
| mm-content-aware-headings | Manuel Matuzovic | https://www.matuzo.at/blog/2026/content-aware-headings | full | 3 |
| mm-html-boilerplate | Manuel Matuzovic | https://www.matuzo.at/blog/2026/html-boilerplate | full | 9 |
| mm-lowering-specificity-of-multiple-rules | Manuel Matuzovic | https://www.matuzo.at/blog/2026/lowering-specificity-of-multiple-rules | full | 5 |
| mm-skip-links-tabindex | Manuel Matuzovic | https://www.matuzo.at/blog/2026/skip-links-tabindex | full | 4 |
| mp-an-unknown-cant-always-fix-an-any | Matt Pocock | https://www.totaltypescript.com/an-unknown-cant-always-fix-an-any | full | 4 |
| mp-any-considered-harmful | Matt Pocock | https://www.totaltypescript.com/any-considered-harmful | full | 3 |
| mp-deriving-vs-decoupling | Matt Pocock | https://www.totaltypescript.com/deriving-vs-decoupling | full | 3 |
| mp-dont-use-function-keyword-in-typescript | Matt Pocock | https://www.totaltypescript.com/dont-use-function-keyword-in-typescript | full | 2 |
| mp-event-types-in-react-and-typescript | Matt Pocock | https://www.totaltypescript.com/event-types-in-react-and-typescript | full | 3 |
| mp-forwardref-with-generic-components | Matt Pocock | https://www.totaltypescript.com/forwardref-with-generic-components | full | 1 |
| mp-how-to-use-satisfies-operator | Matt Pocock | https://www.totaltypescript.com/how-to-use-satisfies-operator | full | 5 |
| mp-jsx-element-vs-react-reactnode | Matt Pocock | https://www.totaltypescript.com/jsx-element-vs-react-reactnode | full | 3 |
| ms-accessibility-and-the-shadow-dom | Marcy Sutton | https://marcysutton.com/accessibility-and-the-shadow-dom | full | 3 |
| ms-how-i-audit-a-website-for-accessibility | Marcy Sutton | https://marcysutton.com/how-i-audit-a-website-for-accessibility | full | 8 |
| ms-live-coding-accessibility | Marcy Sutton | https://marcysutton.com/live-coding-accessibility | skimmed | 3 |
| mz-cascade-layers | Miriam Suzanne | https://css-tricks.com/cascade-layers/ | skimmed | 3 |
| nz-the-inception-of-eslint | Nicholas Zakas | https://humanwhocodes.com/blog/2018/02/the-inception-of-eslint/ | coordinator-read | 1 |
| ow-airbnb-css | Airbnb JavaScript style guide (contributors) | https://raw.githubusercontent.com/airbnb/css/master/README.md | full | 9 |
| ow-airbnb-js | Airbnb JavaScript style guide (contributors) | https://raw.githubusercontent.com/airbnb/javascript/master/README.md | skimmed | 19 |
| ow-airbnb-react | Airbnb JavaScript style guide (contributors) | https://raw.githubusercontent.com/airbnb/javascript/master/react/README.md | full | 12 |
| ow-kcd-appstate | Kent C. Dodds | https://kentcdodds.com/blog/application-state-management-with-react | full | 7 |
| ow-kcd-colocation | Kent C. Dodds | https://kentcdodds.com/blog/state-colocation-will-make-your-react-app-faster | full | 4 |
| ow-kcd-common-mistakes | Kent C. Dodds | https://kentcdodds.com/blog/common-mistakes-with-react-testing-library | full | 15 |
| ow-kcd-derive | Kent C. Dodds | https://kentcdodds.com/blog/dont-sync-state-derive-it | full | 4 |
| ow-kcd-impl-details | Kent C. Dodds | https://kentcdodds.com/blog/testing-implementation-details | full | 5 |
| ow-kcd-inversion | Kent C. Dodds | https://kentcdodds.com/blog/inversion-of-control | full | 5 |
| ow-kcd-longer-tests | Kent C. Dodds | https://kentcdodds.com/blog/write-fewer-longer-tests | full | 7 |
| ow-kcd-mock-fetch | Kent C. Dodds | https://kentcdodds.com/blog/stop-mocking-fetch | full | 7 |
| ow-kcd-usememo | Kent C. Dodds | https://kentcdodds.com/blog/usememo-and-usecallback | full | 6 |
| ow-mark-context | Mark Erikson | https://blog.isquaredsoftware.com/2021/01/context-redux-differences/ | full | 6 |
| ow-mark-orgstate | Mark Erikson, Redux maintainers | https://redux.js.org/faq/organizing-state | full | 4 |
| ow-mark-rendering | Mark Erikson | https://blog.isquaredsoftware.com/2020/05/blogged-answers-a-mostly-complete-guide-to-react-rendering-behavior/ | full | 15 |
| ow-mark-rtk-why | Mark Erikson | https://redux.js.org/introduction/why-rtk-is-redux-today | full | 5 |
| ow-mark-sideeffects | Mark Erikson, Redux maintainers | https://redux.js.org/usage/side-effects-approaches | skimmed | 5 |
| ow-mark-structure | Mark Erikson, Redux maintainers | https://redux.js.org/faq/code-structure | full | 6 |
| ow-mark-style | Mark Erikson, Redux maintainers | https://redux.js.org/style-guide/ | full | 14 |
| ow-matt-tsconfig | Matt Pocock | https://www.totaltypescript.com/tsconfig-cheat-sheet | full | 7 |
| ow-overreacted-algebraic | Dan Abramov | https://overreacted.io/algebraic-effects-for-the-rest-of-us/ | irrelevant | 0 |
| ow-overreacted-memo | Dan Abramov | https://overreacted.io/before-you-memo/ | full | 4 |
| ow-overreacted-ownership | Dan Abramov | https://overreacted.io/react-for-two-computers/ | skimmed | 2 |
| ow-overreacted-resilient | Dan Abramov | https://overreacted.io/writing-resilient-components/ | full | 10 |
| ow-overreacted-setinterval | Dan Abramov | https://overreacted.io/making-setinterval-declarative-with-react-hooks/ | full | 6 |
| ow-overreacted-ui-eng | Dan Abramov | https://overreacted.io/the-elements-of-ui-engineering/ | irrelevant | 3 |
| ow-overreacted-useeffect | Dan Abramov | https://overreacted.io/a-complete-guide-to-useeffect/ | full | 8 |
| ow-primer-react | GitHub Primer team | https://primer.style/product/getting-started/react/ | full | 3 |
| ow-react-batching | React 18 Working Group discussion (React team; poster not verified) | https://github.com/reactwg/react-18/discussions/21 | skimmed | 4 |
| ow-react-derived-state | Brian Vaughn (React blog) | https://legacy.reactjs.org/blog/2018/06/07/you-probably-dont-need-derived-state.html | full | 8 |
| ow-react-optimizing | React team (legacy docs) | https://legacy.reactjs.org/docs/optimizing-performance.html | full | 4 |
| ow-react-usesync | React 18 Working Group discussion (React team; poster not verified) | https://github.com/reactwg/react-18/discussions/86 | skimmed | 4 |
| ow-rf-remix-data | Ryan Florence / Michael Jackson (Remix) | https://remix.run/blog/react-router-v6 | skimmed | 4 |
| ow-rf-remix-forms | Ryan Florence / Michael Jackson (Remix) | https://remix.run/blog/remixing-react-router | full | 8 |
| ow-rr-data-loading | React Router team | https://reactrouter.com/start/data/route-object | skimmed | 3 |
| ow-rr-error | React Router team | https://reactrouter.com/how-to/error-boundary | full | 5 |
| ow-rr-fetchers | React Router team | https://reactrouter.com/how-to/fetchers | full | 5 |
| ow-rr-form | React Router team | https://reactrouter.com/how-to/form-validation | full | 3 |
| ow-rr-picking-mode | React Router team | https://reactrouter.com/start/modes | irrelevant | 1 |
| ow-rr-progressive | React Router team | https://reactrouter.com/explanation/progressive-enhancement | full | 4 |
| ow-rr-race | React Router team | https://reactrouter.com/explanation/race-conditions | full | 3 |
| ow-rr-sessions | React Router team | https://reactrouter.com/explanation/sessions-and-cookies | full | 7 |
| ow-rr-state | React Router team | https://reactrouter.com/explanation/state-management | full | 5 |
| ow-solid-compare | Solid team | https://docs.solidjs.com/concepts/intro-to-reactivity | full | 4 |
| ow-svelte-a11y | Svelte team | https://svelte.dev/docs/svelte/compiler-warnings | full | 22 |
| ow-svelte-derived | Svelte team | https://svelte.dev/docs/svelte/$derived | full | 4 |
| ow-svelte-effect | Rich Harris and the Svelte team | https://svelte.dev/docs/svelte/$effect | full | 7 |
| ow-svelte-runes | Rich Harris | https://svelte.dev/blog/runes | full | 3 |
| ow-svelte-sk-perf | SvelteKit team | https://svelte.dev/docs/kit/performance | full | 8 |
| ow-svelte-sk-security | SvelteKit team | https://svelte.dev/docs/kit/web-standards | mismatch | 2 |
| ow-svelte-sk-state | SvelteKit team | https://svelte.dev/docs/kit/state-management | full | 6 |
| ow-svelte-vdom | Rich Harris | https://svelte.dev/blog/virtual-dom-is-pure-overhead | full | 2 |
| ow-tan-query-docs | TanStack team | https://tanstack.com/query/latest/docs/framework/react/guides/important-defaults | full | 4 |
| ow-tan-query-pitfall | TanStack team | https://tanstack.com/query/latest/docs/framework/react/guides/query-keys | full | 3 |
| ow-tan-router-type | TanStack team | https://tanstack.com/router/latest/docs/framework/react/decisions-on-dx | full | 4 |
| ow-tkdodo-component-comp | Dominik Dorfmeister | https://tkdodo.eu/blog/component-composition-is-great-btw | full | 5 |
| ow-tkdodo-forms | Dominik Dorfmeister | https://tkdodo.eu/blog/react-query-and-forms | full | 6 |
| ow-tkdodo-keys | Dominik Dorfmeister | https://tkdodo.eu/blog/effective-react-query-keys | full | 6 |
| ow-tkdodo-practical | Dominik Dorfmeister | https://tkdodo.eu/blog/practical-react-query | full | 7 |
| ow-tkdodo-reacttypes | Dominik Dorfmeister | https://tkdodo.eu/blog/react-query-data-transformations | mismatch | 4 |
| ow-tkdodo-render-opt | Dominik Dorfmeister | https://tkdodo.eu/blog/react-query-render-optimizations | full | 5 |
| ow-tkdodo-stale | Dominik Dorfmeister | https://tkdodo.eu/blog/hooks-dependencies-and-stale-closures | full | 4 |
| ow-tkdodo-statemgr | Dominik Dorfmeister | https://tkdodo.eu/blog/react-query-as-a-state-manager | full | 5 |
| ow-tkdodo-testing | Dominik Dorfmeister | https://tkdodo.eu/blog/testing-react-query | full | 6 |
| ow-ts-coding | TypeScript team (wiki) | https://github.com/microsoft/TypeScript/wiki/Coding-guidelines | full | 7 |
| ow-ts-donts | TypeScript team (handbook) | https://www.typescriptlang.org/docs/handbook/declaration-files/do-s-and-don-ts.html | full | 7 |
| ow-ts-everyday | TypeScript team (handbook) | https://www.typescriptlang.org/docs/handbook/2/everyday-types.html | skimmed | 7 |
| ow-ts-generics | TypeScript team (handbook) | https://www.typescriptlang.org/docs/handbook/2/generics.html | skimmed | 3 |
| ow-ts-jsx | TypeScript team (handbook) | https://www.typescriptlang.org/docs/handbook/jsx.html | skimmed | 4 |
| ow-ts-narrowing | TypeScript team (handbook) | https://www.typescriptlang.org/docs/handbook/2/narrowing.html | skimmed | 6 |
| ow-ts-perf | TypeScript team (wiki) | https://github.com/microsoft/TypeScript/wiki/Performance | skimmed | 9 |
| ow-tseslint-faqs | typescript-eslint team | https://typescript-eslint.io/troubleshooting/faqs/general | skimmed | 4 |
| ow-tseslint-perf | typescript-eslint team | https://typescript-eslint.io/troubleshooting/typed-linting/performance | full | 4 |
| ow-tseslint-shared | typescript-eslint team | https://typescript-eslint.io/users/configs | skimmed | 3 |
| ow-tseslint-typed | typescript-eslint team | https://typescript-eslint.io/getting-started/typed-linting | full | 2 |
| ow-tseslint-vs-tslint | typescript-eslint team | https://typescript-eslint.io/rules/ | skimmed | 14 |
| ow-vue-a11y | Vue team | https://vuejs.org/guide/best-practices/accessibility | full | 11 |
| ow-vue-composables | Vue team | https://vuejs.org/guide/reusability/composables | full | 8 |
| ow-vue-perf | Vue team | https://vuejs.org/guide/best-practices/performance | full | 9 |
| ow-vue-reactivity | Evan You | https://vuejs.org/guide/extras/reactivity-in-depth | full | 6 |
| ow-vue-security | Vue team | https://vuejs.org/guide/best-practices/security | full | 9 |
| ow-vue-style | Evan You and the Vue team | https://vuejs.org/style-guide/ | irrelevant | 0 |
| ow-zakas-eslint | Nicholas Zakas | https://humanwhocodes.com/blog/2013/07/16/introducing-eslint/ | coordinator-read | 1 |
| pf-addy-budget | web.dev / v8.dev (Chrome team; individual authors not verified) | https://web.dev/articles/performance-budgets-101 | full | 4 |
| pf-addy-cost-js | web.dev / v8.dev (Chrome team; individual authors not verified) | https://v8.dev/blog/cost-of-javascript-2019 | full | 5 |
| pf-addy-hoc | Addy Osmani, Lydia Hallie (patterns.dev) | https://www.patterns.dev/react/hoc-pattern/ | full | 7 |
| pf-addy-hooks | Addy Osmani, Lydia Hallie (patterns.dev) | https://www.patterns.dev/react/hooks-pattern/ | full | 12 |
| pf-addy-lazyload | web.dev / v8.dev (Chrome team; individual authors not verified) | https://web.dev/articles/browser-level-image-lazy-loading | full | 7 |
| pf-addy-patterns-islands | Addy Osmani (patterns.dev) | https://www.patterns.dev/vanilla/islands-architecture/ | full | 4 |
| pf-addy-render | Addy Osmani, Lydia Hallie (patterns.dev) | https://www.patterns.dev/react/render-props-pattern/ | full | 6 |
| pf-archibald-sw | Jake Archibald | https://jakearchibald.com/2016/caching-best-practices/ | full | 5 |
| pf-archibald-tasks | Jake Archibald | https://jakearchibald.com/2015/tasks-microtasks-queues-and-schedules/ | full | 1 |
| pf-lh-csp | Lighthouse team (Chrome) | https://developer.chrome.com/docs/lighthouse/best-practices/csp-xss | full | 6 |
| pf-lh-long-cache | Lighthouse team (Chrome) | https://developer.chrome.com/docs/lighthouse/performance/uses-long-cache-ttl | full | 2 |
| pf-lh-paste | Lighthouse team (Chrome) | https://developer.chrome.com/docs/lighthouse/best-practices/password-inputs-can-be-pasted-into | full | 2 |
| pf-lh-render-blocking | Lighthouse team (Chrome) | https://developer.chrome.com/docs/lighthouse/performance/render-blocking-resources | full | 4 |
| pf-lh-text-compression | Lighthouse team (Chrome) | https://developer.chrome.com/docs/lighthouse/performance/uses-text-compression | full | 2 |
| pf-lh-vulnerable | Lighthouse team (Chrome) | https://developer.chrome.com/docs/lighthouse/best-practices/no-vulnerable-libraries | full | 1 |
| pf-souders-spof | Steve Souders | https://www.stevesouders.com/blog/2010/06/01/frontend-spof/ | full | 5 |
| pf-surma-actor | web.dev / v8.dev (Chrome team; individual authors not verified) | https://web.dev/articles/off-main-thread | full | 4 |
| pf-surma-offmain | Surma | https://surma.dev/things/when-workers/ | full | 5 |
| pf-surma-postmessage | Surma | https://surma.dev/things/is-postmessage-slow/ | full | 6 |
| pf-webalmanac-a11y | HTTP Archive Web Almanac 2024 | https://almanac.httparchive.org/en/2024/accessibility | skimmed | 21 |
| pf-webalmanac-js | HTTP Archive Web Almanac 2024 | https://almanac.httparchive.org/en/2024/javascript | skimmed | 10 |
| pf-webalmanac-markup | HTTP Archive Web Almanac 2024 | https://almanac.httparchive.org/en/2024/markup | full | 10 |
| pf-webalmanac-sec | HTTP Archive Web Almanac 2024 | https://almanac.httparchive.org/en/2024/security | skimmed | 14 |
| pf-webalmanac-third | HTTP Archive Web Almanac 2024 | https://almanac.httparchive.org/en/2024/third-parties | full | 2 |
| pw-css-architecture | Philip Walton | https://philipwalton.com/articles/css-architecture/ | coordinator-read | 2 |
| pw-decoupling-html-css-and-javascript | Philip Walton | https://philipwalton.com/articles/decoupling-html-css-and-javascript/ | full | 6 |
| pw-do-we-actually-need-specificity-in-css | Philip Walton | https://philipwalton.com/articles/do-we-actually-need-specificity-in-css/ | coordinator-read | 1 |
| pw-dynamic-lcp-priority | Philip Walton | https://philipwalton.com/articles/dynamic-lcp-priority/ | full | 4 |
| rc-a-hands-on-introduction-to-fine-grained- | Ryan Carniato | https://dev.to/ryansolid/a-hands-on-introduction-to-fine-grained-reactivity-3ndf | full | 4 |
| rc-scheduling-derivations-in-reactivity-468 | Ryan Carniato | https://dev.to/this-is-learning/scheduling-derivations-in-reactivity-4687 | full | 3 |
| rd-learn-referencing-values-with-refs | React team (react.dev) | https://raw.githubusercontent.com/reactjs/react.dev/main/src/content/learn/referencing-values-with-refs.md | full | 6 |
| rd-learn-sharing-state-between-components | React team (react.dev) | https://raw.githubusercontent.com/reactjs/react.dev/main/src/content/learn/sharing-state-between-components.md | full | 4 |
| rd-reference-react-dom-createPortal | React team (react.dev) | https://raw.githubusercontent.com/reactjs/react.dev/main/src/content/reference/react-dom/createPortal.md | full | 4 |
| rd-reference-react-dom-flushSync | React team (react.dev) | https://raw.githubusercontent.com/reactjs/react.dev/main/src/content/reference/react-dom/flushSync.md | full | 3 |
| rd-reference-react-lazy | React team (react.dev) | https://raw.githubusercontent.com/reactjs/react.dev/main/src/content/reference/react/lazy.md | full | 3 |
| rd-reference-react-memo | React team (react.dev) | https://raw.githubusercontent.com/reactjs/react.dev/main/src/content/reference/react/memo.md | full | 10 |
| rd-reference-react-useId | React team (react.dev) | https://raw.githubusercontent.com/reactjs/react.dev/main/src/content/reference/react/useId.md | full | 6 |
| rd-reference-react-useLayoutEffect | React team (react.dev) | https://raw.githubusercontent.com/reactjs/react.dev/main/src/content/reference/react/useLayoutEffect.md | full | 5 |
| rd-reference-react-useSyncExternalStore | React team (react.dev) | https://raw.githubusercontent.com/reactjs/react.dev/main/src/content/reference/react/useSyncExternalStore.md | full | 7 |
| rh-component-hook-factories | React team (eslint-plugin-react-hooks lint) | https://raw.githubusercontent.com/reactjs/react.dev/main/src/content/reference/eslint-plugin-react-hooks/lints/component-hook-factories.md | catalogue | 1 |
| rh-error-boundaries | React team (eslint-plugin-react-hooks lint) | https://raw.githubusercontent.com/reactjs/react.dev/main/src/content/reference/eslint-plugin-react-hooks/lints/error-boundaries.md | catalogue | 1 |
| rh-exhaustive-deps | React team (eslint-plugin-react-hooks lint) | https://raw.githubusercontent.com/reactjs/react.dev/main/src/content/reference/eslint-plugin-react-hooks/lints/exhaustive-deps.md | catalogue | 1 |
| rh-globals | React team (eslint-plugin-react-hooks lint) | https://raw.githubusercontent.com/reactjs/react.dev/main/src/content/reference/eslint-plugin-react-hooks/lints/globals.md | catalogue | 1 |
| rh-immutability | React team (eslint-plugin-react-hooks lint) | https://raw.githubusercontent.com/reactjs/react.dev/main/src/content/reference/eslint-plugin-react-hooks/lints/immutability.md | catalogue | 1 |
| rh-incompatible-library | React team (eslint-plugin-react-hooks lint) | https://raw.githubusercontent.com/reactjs/react.dev/main/src/content/reference/eslint-plugin-react-hooks/lints/incompatible-library.md | catalogue | 1 |
| rh-preserve-manual-memoization | React team (eslint-plugin-react-hooks lint) | https://raw.githubusercontent.com/reactjs/react.dev/main/src/content/reference/eslint-plugin-react-hooks/lints/preserve-manual-memoization.md | catalogue | 1 |
| rh-purity | React team (eslint-plugin-react-hooks lint) | https://raw.githubusercontent.com/reactjs/react.dev/main/src/content/reference/eslint-plugin-react-hooks/lints/purity.md | catalogue | 1 |
| rh-refs | React team (eslint-plugin-react-hooks lint) | https://raw.githubusercontent.com/reactjs/react.dev/main/src/content/reference/eslint-plugin-react-hooks/lints/refs.md | catalogue | 1 |
| rh-rules-of-hooks | React team (eslint-plugin-react-hooks lint) | https://raw.githubusercontent.com/reactjs/react.dev/main/src/content/reference/eslint-plugin-react-hooks/lints/rules-of-hooks.md | catalogue | 1 |
| rh-set-state-in-effect | React team (eslint-plugin-react-hooks lint) | https://raw.githubusercontent.com/reactjs/react.dev/main/src/content/reference/eslint-plugin-react-hooks/lints/set-state-in-effect.md | catalogue | 1 |
| rh-set-state-in-render | React team (eslint-plugin-react-hooks lint) | https://raw.githubusercontent.com/reactjs/react.dev/main/src/content/reference/eslint-plugin-react-hooks/lints/set-state-in-render.md | catalogue | 1 |
| rh-static-components | React team (eslint-plugin-react-hooks lint) | https://raw.githubusercontent.com/reactjs/react.dev/main/src/content/reference/eslint-plugin-react-hooks/lints/static-components.md | catalogue | 1 |
| rh-unsupported-syntax | React team (eslint-plugin-react-hooks lint) | https://raw.githubusercontent.com/reactjs/react.dev/main/src/content/reference/eslint-plugin-react-hooks/lints/unsupported-syntax.md | catalogue | 1 |
| rh-use-memo | React team (eslint-plugin-react-hooks lint) | https://raw.githubusercontent.com/reactjs/react.dev/main/src/content/reference/eslint-plugin-react-hooks/lints/use-memo.md | catalogue | 1 |
| rl2-avoid-aria-roledescription | Adrian Roselli | https://adrianroselli.com/2020/04/avoid-aria-roledescription.html | full | 6 |
| rl2-my-priority-of-methods-for-labeling-a-co | Adrian Roselli | https://adrianroselli.com/2020/01/my-priority-of-methods-for-labeling-a-control.html | full | 10 |
| rl2-stop-giving-control-hints-to-screen-read | Adrian Roselli | https://adrianroselli.com/2019/10/stop-giving-control-hints-to-screen-readers.html | full | 5 |
| rr-button-has-type | eslint-plugin-react maintainers (rule doc) | https://raw.githubusercontent.com/jsx-eslint/eslint-plugin-react/master/docs/rules/button-has-type.md | catalogue | 1 |
| rr-checked-requires-onchange-or-readonly | eslint-plugin-react maintainers (rule doc) | https://raw.githubusercontent.com/jsx-eslint/eslint-plugin-react/master/docs/rules/checked-requires-onchange-or-readonly.md | catalogue | 1 |
| rr-destructuring-assignment | eslint-plugin-react maintainers (rule doc) | https://raw.githubusercontent.com/jsx-eslint/eslint-plugin-react/master/docs/rules/destructuring-assignment.md | catalogue | 1 |
| rr-display-name | eslint-plugin-react maintainers (rule doc) | https://raw.githubusercontent.com/jsx-eslint/eslint-plugin-react/master/docs/rules/display-name.md | catalogue | 1 |
| rr-forbid-dom-props | eslint-plugin-react maintainers (rule doc) | https://raw.githubusercontent.com/jsx-eslint/eslint-plugin-react/master/docs/rules/forbid-dom-props.md | catalogue | 1 |
| rr-hook-use-state | eslint-plugin-react maintainers (rule doc) | https://raw.githubusercontent.com/jsx-eslint/eslint-plugin-react/master/docs/rules/hook-use-state.md | catalogue | 1 |
| rr-iframe-missing-sandbox | eslint-plugin-react maintainers (rule doc) | https://raw.githubusercontent.com/jsx-eslint/eslint-plugin-react/master/docs/rules/iframe-missing-sandbox.md | catalogue | 1 |
| rr-jsx-handler-names | eslint-plugin-react maintainers (rule doc) | https://raw.githubusercontent.com/jsx-eslint/eslint-plugin-react/master/docs/rules/jsx-handler-names.md | catalogue | 1 |
| rr-jsx-key | eslint-plugin-react maintainers (rule doc) | https://raw.githubusercontent.com/jsx-eslint/eslint-plugin-react/master/docs/rules/jsx-key.md | catalogue | 1 |
| rr-jsx-no-bind | eslint-plugin-react maintainers (rule doc) | https://raw.githubusercontent.com/jsx-eslint/eslint-plugin-react/master/docs/rules/jsx-no-bind.md | catalogue | 1 |
| rr-jsx-no-constructed-context-values | eslint-plugin-react maintainers (rule doc) | https://raw.githubusercontent.com/jsx-eslint/eslint-plugin-react/master/docs/rules/jsx-no-constructed-context-values.md | catalogue | 1 |
| rr-jsx-no-leaked-render | eslint-plugin-react maintainers (rule doc) | https://raw.githubusercontent.com/jsx-eslint/eslint-plugin-react/master/docs/rules/jsx-no-leaked-render.md | catalogue | 1 |
| rr-jsx-no-literals | eslint-plugin-react maintainers (rule doc) | https://raw.githubusercontent.com/jsx-eslint/eslint-plugin-react/master/docs/rules/jsx-no-literals.md | catalogue | 1 |
| rr-jsx-no-script-url | eslint-plugin-react maintainers (rule doc) | https://raw.githubusercontent.com/jsx-eslint/eslint-plugin-react/master/docs/rules/jsx-no-script-url.md | catalogue | 1 |
| rr-jsx-no-target-blank | eslint-plugin-react maintainers (rule doc) | https://raw.githubusercontent.com/jsx-eslint/eslint-plugin-react/master/docs/rules/jsx-no-target-blank.md | catalogue | 1 |
| rr-jsx-no-useless-fragment | eslint-plugin-react maintainers (rule doc) | https://raw.githubusercontent.com/jsx-eslint/eslint-plugin-react/master/docs/rules/jsx-no-useless-fragment.md | catalogue | 1 |
| rr-jsx-props-no-spreading | eslint-plugin-react maintainers (rule doc) | https://raw.githubusercontent.com/jsx-eslint/eslint-plugin-react/master/docs/rules/jsx-props-no-spreading.md | catalogue | 1 |
| rr-no-access-state-in-setstate | eslint-plugin-react maintainers (rule doc) | https://raw.githubusercontent.com/jsx-eslint/eslint-plugin-react/master/docs/rules/no-access-state-in-setstate.md | catalogue | 1 |
| rr-no-array-index-key | eslint-plugin-react maintainers (rule doc) | https://raw.githubusercontent.com/jsx-eslint/eslint-plugin-react/master/docs/rules/no-array-index-key.md | catalogue | 1 |
| rr-no-children-prop | eslint-plugin-react maintainers (rule doc) | https://raw.githubusercontent.com/jsx-eslint/eslint-plugin-react/master/docs/rules/no-children-prop.md | catalogue | 1 |
| rr-no-danger | eslint-plugin-react maintainers (rule doc) | https://raw.githubusercontent.com/jsx-eslint/eslint-plugin-react/master/docs/rules/no-danger.md | catalogue | 1 |
| rr-no-danger-with-children | eslint-plugin-react maintainers (rule doc) | https://raw.githubusercontent.com/jsx-eslint/eslint-plugin-react/master/docs/rules/no-danger-with-children.md | catalogue | 1 |
| rr-no-direct-mutation-state | eslint-plugin-react maintainers (rule doc) | https://raw.githubusercontent.com/jsx-eslint/eslint-plugin-react/master/docs/rules/no-direct-mutation-state.md | catalogue | 1 |
| rr-no-find-dom-node | eslint-plugin-react maintainers (rule doc) | https://raw.githubusercontent.com/jsx-eslint/eslint-plugin-react/master/docs/rules/no-find-dom-node.md | catalogue | 1 |
| rr-no-invalid-html-attribute | eslint-plugin-react maintainers (rule doc) | https://raw.githubusercontent.com/jsx-eslint/eslint-plugin-react/master/docs/rules/no-invalid-html-attribute.md | catalogue | 1 |
| rr-no-multi-comp | eslint-plugin-react maintainers (rule doc) | https://raw.githubusercontent.com/jsx-eslint/eslint-plugin-react/master/docs/rules/no-multi-comp.md | catalogue | 1 |
| rr-no-object-type-as-default-prop | eslint-plugin-react maintainers (rule doc) | https://raw.githubusercontent.com/jsx-eslint/eslint-plugin-react/master/docs/rules/no-object-type-as-default-prop.md | catalogue | 1 |
| rr-no-this-in-sfc | eslint-plugin-react maintainers (rule doc) | https://raw.githubusercontent.com/jsx-eslint/eslint-plugin-react/master/docs/rules/no-this-in-sfc.md | catalogue | 1 |
| rr-no-unescaped-entities | eslint-plugin-react maintainers (rule doc) | https://raw.githubusercontent.com/jsx-eslint/eslint-plugin-react/master/docs/rules/no-unescaped-entities.md | catalogue | 1 |
| rr-no-unstable-nested-components | eslint-plugin-react maintainers (rule doc) | https://raw.githubusercontent.com/jsx-eslint/eslint-plugin-react/master/docs/rules/no-unstable-nested-components.md | catalogue | 1 |
| rr-no-unused-state | eslint-plugin-react maintainers (rule doc) | https://raw.githubusercontent.com/jsx-eslint/eslint-plugin-react/master/docs/rules/no-unused-state.md | catalogue | 1 |
| rr-prefer-read-only-props | eslint-plugin-react maintainers (rule doc) | https://raw.githubusercontent.com/jsx-eslint/eslint-plugin-react/master/docs/rules/prefer-read-only-props.md | catalogue | 1 |
| rr-require-optimization | eslint-plugin-react maintainers (rule doc) | https://raw.githubusercontent.com/jsx-eslint/eslint-plugin-react/master/docs/rules/require-optimization.md | catalogue | 1 |
| rr-void-dom-elements-no-children | eslint-plugin-react maintainers (rule doc) | https://raw.githubusercontent.com/jsx-eslint/eslint-plugin-react/master/docs/rules/void-dom-elements-no-children.md | catalogue | 1 |
| sa-metrics-by-proxy | Sophie Alpert | https://sophiebits.com/2018/12/04/metrics-by-proxy | irrelevant | 1 |
| sa-preventing-xss-json | Sophie Alpert | https://sophiebits.com/2012/08/03/preventing-xss-json | full | 3 |
| sa-todos-arent-for-doing | Sophie Alpert | https://sophiebits.com/2025/07/21/todos-arent-for-doing | full | 2 |
| sa-type-errors-with-inference-need-stacks | Sophie Alpert | https://sophiebits.com/2018/05/21/type-errors-with-inference-need-stacks | irrelevant | 0 |
| sa-using-react-to-speed-up-khan-academy | Sophie Alpert | https://sophiebits.com/2013/06/09/using-react-to-speed-up-khan-academy | irrelevant | 1 |
| sa-why-review-code | Sophie Alpert | https://sophiebits.com/2018/12/25/why-review-code | irrelevant | 0 |
| sd-dominteractive-is-it-really | Steve Souders | https://www.stevesouders.com/blog/2015/08/07/dominteractive-is-it-really/ | full | 2 |
| sd-moving-beyond-window-onload | Steve Souders | https://www.stevesouders.com/blog/2013/05/13/moving-beyond-window-onload/ | full | 2 |
| se-how-custom-property-values-are-computed | Stephanie Eckles | https://moderncss.dev/how-custom-property-values-are-computed/ | full | 4 |
| se-practical-uses-of-css-math-functions-cal | Stephanie Eckles | https://moderncss.dev/practical-uses-of-css-math-functions-calc-clamp-min-max/ | full | 8 |
| sh-css-container-style-queries | Ahmad Shadeed | https://ishadeed.com/article/css-container-style-queries/ | skimmed | 4 |
| sh-flex-wrap-balance | Ahmad Shadeed | https://ishadeed.com/article/flex-wrap-balance | full | 4 |
| so-a-toast-to-a11y-toasts | Scott O'Hara | https://www.scottohara.me/blog/2019/07/08/a-toast-to-a11y-toasts.html | full | 9 |
| so-aria-lists | Scott O'Hara | https://www.scottohara.me/blog/2018/05/26/aria-lists.html | full | 4 |
| so-hidden-vs-none | Scott O'Hara | https://www.scottohara.me/blog/2018/05/05/hidden-vs-none.html | full | 7 |
| so-names-and-labels | Scott O'Hara | https://www.scottohara.me/blog/2021/11/02/names-and-labels.html | full | 8 |
| so-the-output-element | Scott O'Hara | https://www.scottohara.me/blog/2019/07/10/the-output-element.html | full | 5 |
| ss-accessible-text-labels | Sara Soueidan | https://www.sarasoueidan.com/blog/accessible-text-labels/ | full | 5 |
| ss-accordion-markup | Sara Soueidan | https://www.sarasoueidan.com/blog/accordion-markup/ | full | 5 |
| ss-keyboard-friendlier-article-listings | Sara Soueidan | https://www.sarasoueidan.com/blog/keyboard-friendlier-article-listings/ | full | 5 |
| ss-style-settings-with-css-variables | Sara Soueidan | https://www.sarasoueidan.com/blog/style-settings-with-css-variables/ | full | 6 |
| ss-toggle-switch-design | Sara Soueidan | https://www.sarasoueidan.com/blog/toggle-switch-design/ | full | 6 |
| tk-growing-contentful-gap | Tim Kadlec | https://timkadlec.com/remembers/2023/04/growing-contentful-gap/ | full | 2 |
| tk-single-visionary-fairytale | Tim Kadlec | https://timkadlec.com/remembers/2023/06/single-visionary-fairytale/ | irrelevant | 0 |
| tl-await-async-events | Testing Library plugin maintainers (rule doc) | https://raw.githubusercontent.com/testing-library/eslint-plugin-testing-library/main/docs/rules/await-async-events.md | catalogue | 1 |
| tl-await-async-queries | Testing Library plugin maintainers (rule doc) | https://raw.githubusercontent.com/testing-library/eslint-plugin-testing-library/main/docs/rules/await-async-queries.md | catalogue | 1 |
| tl-no-container | Testing Library plugin maintainers (rule doc) | https://raw.githubusercontent.com/testing-library/eslint-plugin-testing-library/main/docs/rules/no-container.md | catalogue | 1 |
| tl-no-manual-cleanup | Testing Library plugin maintainers (rule doc) | https://raw.githubusercontent.com/testing-library/eslint-plugin-testing-library/main/docs/rules/no-manual-cleanup.md | catalogue | 1 |
| tl-no-node-access | Testing Library plugin maintainers (rule doc) | https://raw.githubusercontent.com/testing-library/eslint-plugin-testing-library/main/docs/rules/no-node-access.md | catalogue | 1 |
| tl-no-render-in-lifecycle | Testing Library plugin maintainers (rule doc) | https://raw.githubusercontent.com/testing-library/eslint-plugin-testing-library/main/docs/rules/no-render-in-lifecycle.md | catalogue | 1 |
| tl-no-test-id-queries | Testing Library plugin maintainers (rule doc) | https://raw.githubusercontent.com/testing-library/eslint-plugin-testing-library/main/docs/rules/no-test-id-queries.md | catalogue | 1 |
| tl-no-unnecessary-act | Testing Library plugin maintainers (rule doc) | https://raw.githubusercontent.com/testing-library/eslint-plugin-testing-library/main/docs/rules/no-unnecessary-act.md | catalogue | 1 |
| tl-no-wait-for-multiple-assertions | Testing Library plugin maintainers (rule doc) | https://raw.githubusercontent.com/testing-library/eslint-plugin-testing-library/main/docs/rules/no-wait-for-multiple-assertions.md | catalogue | 1 |
| tl-no-wait-for-side-effects | Testing Library plugin maintainers (rule doc) | https://raw.githubusercontent.com/testing-library/eslint-plugin-testing-library/main/docs/rules/no-wait-for-side-effects.md | catalogue | 1 |
| tl-prefer-find-by | Testing Library plugin maintainers (rule doc) | https://raw.githubusercontent.com/testing-library/eslint-plugin-testing-library/main/docs/rules/prefer-find-by.md | catalogue | 1 |
| tl-prefer-presence-queries | Testing Library plugin maintainers (rule doc) | https://raw.githubusercontent.com/testing-library/eslint-plugin-testing-library/main/docs/rules/prefer-presence-queries.md | catalogue | 1 |
| tl-prefer-screen-queries | Testing Library plugin maintainers (rule doc) | https://raw.githubusercontent.com/testing-library/eslint-plugin-testing-library/main/docs/rules/prefer-screen-queries.md | catalogue | 1 |
| tl-prefer-user-event | Testing Library plugin maintainers (rule doc) | https://raw.githubusercontent.com/testing-library/eslint-plugin-testing-library/main/docs/rules/prefer-user-event.md | catalogue | 1 |
| tq-exhaustive-deps | TanStack Query team (eslint plugin) | https://raw.githubusercontent.com/TanStack/query/main/docs/eslint/exhaustive-deps.md | catalogue | 1 |
| tq-infinite-query-property-order | TanStack Query team (eslint plugin) | https://raw.githubusercontent.com/TanStack/query/main/docs/eslint/infinite-query-property-order.md | catalogue | 1 |
| tq-mutation-property-order | TanStack Query team (eslint plugin) | https://raw.githubusercontent.com/TanStack/query/main/docs/eslint/mutation-property-order.md | catalogue | 1 |
| tq-no-rest-destructuring | TanStack Query team (eslint plugin) | https://raw.githubusercontent.com/TanStack/query/main/docs/eslint/no-rest-destructuring.md | catalogue | 1 |
| tq-no-unstable-deps | TanStack Query team (eslint plugin) | https://raw.githubusercontent.com/TanStack/query/main/docs/eslint/no-unstable-deps.md | catalogue | 1 |
| tq-no-void-query-fn | TanStack Query team (eslint plugin) | https://raw.githubusercontent.com/TanStack/query/main/docs/eslint/no-void-query-fn.md | catalogue | 1 |
| tq-prefer-query-options | TanStack Query team (eslint plugin) | https://raw.githubusercontent.com/TanStack/query/main/docs/eslint/prefer-query-options.md | catalogue | 1 |
| tq-stable-query-client | TanStack Query team (eslint plugin) | https://raw.githubusercontent.com/TanStack/query/main/docs/eslint/stable-query-client.md | catalogue | 1 |
| tse-await-thenable | typescript-eslint team (rule doc) | https://raw.githubusercontent.com/typescript-eslint/typescript-eslint/main/packages/eslint-plugin/docs/rules/await-thenable.mdx | catalogue | 1 |
| tse-ban-ts-comment | typescript-eslint team (rule doc) | https://raw.githubusercontent.com/typescript-eslint/typescript-eslint/main/packages/eslint-plugin/docs/rules/ban-ts-comment.mdx | catalogue | 1 |
| tse-consistent-type-assertions | typescript-eslint team (rule doc) | https://raw.githubusercontent.com/typescript-eslint/typescript-eslint/main/packages/eslint-plugin/docs/rules/consistent-type-assertions.mdx | catalogue | 1 |
| tse-consistent-type-imports | typescript-eslint team (rule doc) | https://raw.githubusercontent.com/typescript-eslint/typescript-eslint/main/packages/eslint-plugin/docs/rules/consistent-type-imports.mdx | catalogue | 1 |
| tse-explicit-module-boundary-types | typescript-eslint team (rule doc) | https://raw.githubusercontent.com/typescript-eslint/typescript-eslint/main/packages/eslint-plugin/docs/rules/explicit-module-boundary-types.mdx | catalogue | 1 |
| tse-max-params | typescript-eslint team (rule doc) | https://raw.githubusercontent.com/typescript-eslint/typescript-eslint/main/packages/eslint-plugin/docs/rules/max-params.mdx | catalogue | 1 |
| tse-naming-convention | typescript-eslint team (rule doc) | https://raw.githubusercontent.com/typescript-eslint/typescript-eslint/main/packages/eslint-plugin/docs/rules/naming-convention.mdx | catalogue | 1 |
| tse-no-array-delete | typescript-eslint team (rule doc) | https://raw.githubusercontent.com/typescript-eslint/typescript-eslint/main/packages/eslint-plugin/docs/rules/no-array-delete.mdx | catalogue | 1 |
| tse-no-base-to-string | typescript-eslint team (rule doc) | https://raw.githubusercontent.com/typescript-eslint/typescript-eslint/main/packages/eslint-plugin/docs/rules/no-base-to-string.mdx | catalogue | 1 |
| tse-no-confusing-void-expression | typescript-eslint team (rule doc) | https://raw.githubusercontent.com/typescript-eslint/typescript-eslint/main/packages/eslint-plugin/docs/rules/no-confusing-void-expression.mdx | catalogue | 1 |
| tse-no-deprecated | typescript-eslint team (rule doc) | https://raw.githubusercontent.com/typescript-eslint/typescript-eslint/main/packages/eslint-plugin/docs/rules/no-deprecated.mdx | catalogue | 1 |
| tse-no-dynamic-delete | typescript-eslint team (rule doc) | https://raw.githubusercontent.com/typescript-eslint/typescript-eslint/main/packages/eslint-plugin/docs/rules/no-dynamic-delete.mdx | catalogue | 1 |
| tse-no-empty-object-type | typescript-eslint team (rule doc) | https://raw.githubusercontent.com/typescript-eslint/typescript-eslint/main/packages/eslint-plugin/docs/rules/no-empty-object-type.mdx | catalogue | 1 |
| tse-no-explicit-any | typescript-eslint team (rule doc) | https://raw.githubusercontent.com/typescript-eslint/typescript-eslint/main/packages/eslint-plugin/docs/rules/no-explicit-any.mdx | catalogue | 1 |
| tse-no-extraneous-class | typescript-eslint team (rule doc) | https://raw.githubusercontent.com/typescript-eslint/typescript-eslint/main/packages/eslint-plugin/docs/rules/no-extraneous-class.mdx | catalogue | 1 |
| tse-no-floating-promises | typescript-eslint team (rule doc) | https://raw.githubusercontent.com/typescript-eslint/typescript-eslint/main/packages/eslint-plugin/docs/rules/no-floating-promises.mdx | catalogue | 1 |
| tse-no-for-in-array | typescript-eslint team (rule doc) | https://raw.githubusercontent.com/typescript-eslint/typescript-eslint/main/packages/eslint-plugin/docs/rules/no-for-in-array.mdx | catalogue | 1 |
| tse-no-implied-eval | typescript-eslint team (rule doc) | https://raw.githubusercontent.com/typescript-eslint/typescript-eslint/main/packages/eslint-plugin/docs/rules/no-implied-eval.mdx | catalogue | 1 |
| tse-no-import-type-side-effects | typescript-eslint team (rule doc) | https://raw.githubusercontent.com/typescript-eslint/typescript-eslint/main/packages/eslint-plugin/docs/rules/no-import-type-side-effects.mdx | catalogue | 1 |
| tse-no-magic-numbers | typescript-eslint team (rule doc) | https://raw.githubusercontent.com/typescript-eslint/typescript-eslint/main/packages/eslint-plugin/docs/rules/no-magic-numbers.mdx | catalogue | 1 |
| tse-no-misused-promises | typescript-eslint team (rule doc) | https://raw.githubusercontent.com/typescript-eslint/typescript-eslint/main/packages/eslint-plugin/docs/rules/no-misused-promises.mdx | catalogue | 1 |
| tse-no-misused-spread | typescript-eslint team (rule doc) | https://raw.githubusercontent.com/typescript-eslint/typescript-eslint/main/packages/eslint-plugin/docs/rules/no-misused-spread.mdx | catalogue | 1 |
| tse-no-mixed-enums | typescript-eslint team (rule doc) | https://raw.githubusercontent.com/typescript-eslint/typescript-eslint/main/packages/eslint-plugin/docs/rules/no-mixed-enums.mdx | catalogue | 1 |
| tse-no-non-null-assertion | typescript-eslint team (rule doc) | https://raw.githubusercontent.com/typescript-eslint/typescript-eslint/main/packages/eslint-plugin/docs/rules/no-non-null-assertion.mdx | catalogue | 1 |
| tse-no-redundant-type-constituents | typescript-eslint team (rule doc) | https://raw.githubusercontent.com/typescript-eslint/typescript-eslint/main/packages/eslint-plugin/docs/rules/no-redundant-type-constituents.mdx | catalogue | 1 |
| tse-no-restricted-imports | typescript-eslint team (rule doc) | https://raw.githubusercontent.com/typescript-eslint/typescript-eslint/main/packages/eslint-plugin/docs/rules/no-restricted-imports.mdx | catalogue | 1 |
| tse-no-shadow | typescript-eslint team (rule doc) | https://raw.githubusercontent.com/typescript-eslint/typescript-eslint/main/packages/eslint-plugin/docs/rules/no-shadow.mdx | catalogue | 1 |
| tse-no-unnecessary-condition | typescript-eslint team (rule doc) | https://raw.githubusercontent.com/typescript-eslint/typescript-eslint/main/packages/eslint-plugin/docs/rules/no-unnecessary-condition.mdx | catalogue | 1 |
| tse-no-unnecessary-template-expression | typescript-eslint team (rule doc) | https://raw.githubusercontent.com/typescript-eslint/typescript-eslint/main/packages/eslint-plugin/docs/rules/no-unnecessary-template-expression.mdx | catalogue | 1 |
| tse-no-unnecessary-type-assertion | typescript-eslint team (rule doc) | https://raw.githubusercontent.com/typescript-eslint/typescript-eslint/main/packages/eslint-plugin/docs/rules/no-unnecessary-type-assertion.mdx | catalogue | 1 |
| tse-no-unnecessary-type-conversion | typescript-eslint team (rule doc) | https://raw.githubusercontent.com/typescript-eslint/typescript-eslint/main/packages/eslint-plugin/docs/rules/no-unnecessary-type-conversion.mdx | catalogue | 1 |
| tse-no-unnecessary-type-parameters | typescript-eslint team (rule doc) | https://raw.githubusercontent.com/typescript-eslint/typescript-eslint/main/packages/eslint-plugin/docs/rules/no-unnecessary-type-parameters.mdx | catalogue | 1 |
| tse-no-unsafe-argument | typescript-eslint team (rule doc) | https://raw.githubusercontent.com/typescript-eslint/typescript-eslint/main/packages/eslint-plugin/docs/rules/no-unsafe-argument.mdx | catalogue | 1 |
| tse-no-unsafe-assignment | typescript-eslint team (rule doc) | https://raw.githubusercontent.com/typescript-eslint/typescript-eslint/main/packages/eslint-plugin/docs/rules/no-unsafe-assignment.mdx | catalogue | 1 |
| tse-no-unsafe-call | typescript-eslint team (rule doc) | https://raw.githubusercontent.com/typescript-eslint/typescript-eslint/main/packages/eslint-plugin/docs/rules/no-unsafe-call.mdx | catalogue | 1 |
| tse-no-unsafe-enum-comparison | typescript-eslint team (rule doc) | https://raw.githubusercontent.com/typescript-eslint/typescript-eslint/main/packages/eslint-plugin/docs/rules/no-unsafe-enum-comparison.mdx | catalogue | 1 |
| tse-no-unsafe-member-access | typescript-eslint team (rule doc) | https://raw.githubusercontent.com/typescript-eslint/typescript-eslint/main/packages/eslint-plugin/docs/rules/no-unsafe-member-access.mdx | catalogue | 1 |
| tse-no-unsafe-return | typescript-eslint team (rule doc) | https://raw.githubusercontent.com/typescript-eslint/typescript-eslint/main/packages/eslint-plugin/docs/rules/no-unsafe-return.mdx | catalogue | 1 |
| tse-no-unsafe-type-assertion | typescript-eslint team (rule doc) | https://raw.githubusercontent.com/typescript-eslint/typescript-eslint/main/packages/eslint-plugin/docs/rules/no-unsafe-type-assertion.mdx | catalogue | 1 |
| tse-no-unused-vars | typescript-eslint team (rule doc) | https://raw.githubusercontent.com/typescript-eslint/typescript-eslint/main/packages/eslint-plugin/docs/rules/no-unused-vars.mdx | catalogue | 1 |
| tse-no-use-before-define | typescript-eslint team (rule doc) | https://raw.githubusercontent.com/typescript-eslint/typescript-eslint/main/packages/eslint-plugin/docs/rules/no-use-before-define.mdx | catalogue | 1 |
| tse-no-useless-default-assignment | typescript-eslint team (rule doc) | https://raw.githubusercontent.com/typescript-eslint/typescript-eslint/main/packages/eslint-plugin/docs/rules/no-useless-default-assignment.mdx | catalogue | 1 |
| tse-no-wrapper-object-types | typescript-eslint team (rule doc) | https://raw.githubusercontent.com/typescript-eslint/typescript-eslint/main/packages/eslint-plugin/docs/rules/no-wrapper-object-types.mdx | catalogue | 1 |
| tse-only-throw-error | typescript-eslint team (rule doc) | https://raw.githubusercontent.com/typescript-eslint/typescript-eslint/main/packages/eslint-plugin/docs/rules/only-throw-error.mdx | catalogue | 1 |
| tse-prefer-literal-enum-member | typescript-eslint team (rule doc) | https://raw.githubusercontent.com/typescript-eslint/typescript-eslint/main/packages/eslint-plugin/docs/rules/prefer-literal-enum-member.mdx | catalogue | 1 |
| tse-prefer-nullish-coalescing | typescript-eslint team (rule doc) | https://raw.githubusercontent.com/typescript-eslint/typescript-eslint/main/packages/eslint-plugin/docs/rules/prefer-nullish-coalescing.mdx | catalogue | 1 |
| tse-prefer-optional-chain | typescript-eslint team (rule doc) | https://raw.githubusercontent.com/typescript-eslint/typescript-eslint/main/packages/eslint-plugin/docs/rules/prefer-optional-chain.mdx | catalogue | 1 |
| tse-prefer-promise-reject-errors | typescript-eslint team (rule doc) | https://raw.githubusercontent.com/typescript-eslint/typescript-eslint/main/packages/eslint-plugin/docs/rules/prefer-promise-reject-errors.mdx | catalogue | 1 |
| tse-prefer-readonly | typescript-eslint team (rule doc) | https://raw.githubusercontent.com/typescript-eslint/typescript-eslint/main/packages/eslint-plugin/docs/rules/prefer-readonly.mdx | catalogue | 1 |
| tse-prefer-readonly-parameter-types | typescript-eslint team (rule doc) | https://raw.githubusercontent.com/typescript-eslint/typescript-eslint/main/packages/eslint-plugin/docs/rules/prefer-readonly-parameter-types.mdx | catalogue | 1 |
| tse-promise-function-async | typescript-eslint team (rule doc) | https://raw.githubusercontent.com/typescript-eslint/typescript-eslint/main/packages/eslint-plugin/docs/rules/promise-function-async.mdx | catalogue | 1 |
| tse-require-await | typescript-eslint team (rule doc) | https://raw.githubusercontent.com/typescript-eslint/typescript-eslint/main/packages/eslint-plugin/docs/rules/require-await.mdx | catalogue | 1 |
| tse-restrict-plus-operands | typescript-eslint team (rule doc) | https://raw.githubusercontent.com/typescript-eslint/typescript-eslint/main/packages/eslint-plugin/docs/rules/restrict-plus-operands.mdx | catalogue | 1 |
| tse-restrict-template-expressions | typescript-eslint team (rule doc) | https://raw.githubusercontent.com/typescript-eslint/typescript-eslint/main/packages/eslint-plugin/docs/rules/restrict-template-expressions.mdx | catalogue | 1 |
| tse-return-await | typescript-eslint team (rule doc) | https://raw.githubusercontent.com/typescript-eslint/typescript-eslint/main/packages/eslint-plugin/docs/rules/return-await.mdx | catalogue | 1 |
| tse-strict-boolean-expressions | typescript-eslint team (rule doc) | https://raw.githubusercontent.com/typescript-eslint/typescript-eslint/main/packages/eslint-plugin/docs/rules/strict-boolean-expressions.mdx | catalogue | 1 |
| tse-strict-void-return | typescript-eslint team (rule doc) | https://raw.githubusercontent.com/typescript-eslint/typescript-eslint/main/packages/eslint-plugin/docs/rules/strict-void-return.mdx | catalogue | 1 |
| tse-switch-exhaustiveness-check | typescript-eslint team (rule doc) | https://raw.githubusercontent.com/typescript-eslint/typescript-eslint/main/packages/eslint-plugin/docs/rules/switch-exhaustiveness-check.mdx | catalogue | 1 |
| tse-unbound-method | typescript-eslint team (rule doc) | https://raw.githubusercontent.com/typescript-eslint/typescript-eslint/main/packages/eslint-plugin/docs/rules/unbound-method.mdx | catalogue | 1 |
| tse-use-unknown-in-catch-callback-variable | typescript-eslint team (rule doc) | https://raw.githubusercontent.com/typescript-eslint/typescript-eslint/main/packages/eslint-plugin/docs/rules/use-unknown-in-catch-callback-variable.mdx | catalogue | 1 |

Fetched but not processed: 739 prose pages (not read, not used). Fetch failures (HTTP 404 on guessed URLs, 526 on reach.tech, 500 on sophiebits.com) were dropped, not retried with other tools.
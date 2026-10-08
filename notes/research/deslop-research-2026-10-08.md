# De-slopifying the front end: hallmarks, classic mistakes, soul, and what crunk can check

Research only. Date of research: 2026-10-08. ASCII only. Citations are [S#] keys into
the sources table in section 9 (URL, author, date, fetched yes/no). Anything I could not
fetch is marked [unsourced] and carries no recommendation by itself. Unverified
secondary claims are marked [verify].

## 0. Method, denominator and honesty

- Tooling reality: the WebSearch, WebFetch and playwright tools named by the coordinator
  are NOT available in this agent (ToolSearch returned "No matching deferred tools" for
  them, twice). I fetched every source with curl from the shell (HTTP 200 and body read),
  discovered sources through the Hacker News Algolia API and one DuckDuckGo query
  (Bing, Brave, Mojeek, Startpage returned captchas or junk). No source below was cited
  from memory; where I recall a claim but could not fetch it, it is [unsourced].
- Denominator: about 130 URLs were attempted; 96 rows in the sources table (section 9)
  were fetched with readable content (95 pages plus the HN Algolia API). 19 of those are
  marked fetched-but-not-mined, tangential or thin and support no claim; so 77 sources
  are cited as support for at least one claim. About 14 attempts failed or returned
  stubs (section 9.3).
- Biggest finding on the sources: of the named practitioners in the brief (Comeau,
  Wathan/Schoger, Rauno, Paco, Emil, Frost, Chimero, Soueidan, Pickering, Bell/Every
  Layout, Shadeed, Butterick, Silver, Rams, Tufte, NN/g, Linear, Stripe, Vercel), none
  of the pages I fetched is a direct essay naming "AI slop front-end tells". What they
  provide is the craft canon the tells violate. The slop taxonomy itself comes from
  (a) Anthropic's own prompt and skill text [S3][S4], (b) a Show HN measurement by Adrian
  Krebs with a public deterministic detector [S1][S2], (c) compilers and tool vendors
  [S5][S6][S7][S8][S9][S12][S13][S14] who are credible on observation but have commercial
  or promotional motives, and (d) NN/g on the sparkle icon [S21]. Treat the taxonomy as
  "well documented as convergence, weakly documented as causal".
- The Adam Wathan "sorry for bg-indigo-500" tweet (Aug 2025) is repeated by three
  secondary sources [S10][S11][S12] with identical wording. I could not fetch the
  tweet. Mark: [verify] primary. The Tailwind docs do still show `bg-indigo-500` in
  their own example markup [S78], which supports the "default propagated" story.
- Not fetched, therefore [unsourced]: Paco Coursey's essays (only the index
  fetched, nothing mined), Jen Simmons, Rachel Andrew, Jhey Tompkins, Una Kravets, Lea
  Verou, Val Head (stub page), Sarah Richards (stub page), Bringhurst, Wroblewski
  (404), Teenage Engineering (empty), Panic (stub), Arc/Browser Company (stub), Tufte
  primary (403), Material Design motion tokens (JS shell), Cell Patterns convergence
  paper (Cloudflare block), arXiv (rate limited). Do not build rules from these.

## 1. Hallmarks of AI-generated front ends

Reliability labels follow [S5]: strong / moderate / weak alone. "Doc" means how well
documented by fetched sources. Five generic mechanisms explain every hallmark:
statistical averaging of Tailwind-era training data, toolchain defaults (Tailwind,
shadcn, Lucide, Framer Motion), preference tuning, and a feedback loop [S5][S10][S11].

### 1.1 Primary evidence: Anthropic's own text names the problem

- Anthropic's cookbook says the model "tends to converge toward generic, on distribution
  outputs" and that users call this the "AI slop" aesthetic; it lists overused fonts
  (Inter, Roboto, Arial, system), cliched colour schemes (purple gradients on white),
  predictable layouts, and warns that it still converges on Space Grotesk [S3]. This is
  the earliest fetched primary use of the term in a front-end context (notebook posted
  2025-11-14 per HN listing).
- The current Anthropic `frontend-design` skill goes further: it names tells it itself
  produces, including cream background near #F4F1EA with serif display and a terracotta
  accent near #D97757, near-black plus one acid accent, the "SaaS-card kit" (identical
  rounded cards, one radius everywhere, same soft grey shadow, gradient washes),
  tracked ALL-CAPS eyebrow above every heading, middle-dot meta strings, spaced em-dash
  labels, a "->" appended to links, a big number with small label plus stats as the
  default hero, numbered 01/02/03 markers where there is no sequence, single accented
  word in a headline, fade-and-slide-up on every section [S4]. It also states "visual
  structure is information": borders, numbering, eyebrows are only legitimate if they
  encode something [S4]. Note the model vendor documenting its own fingerprint is the
  strongest single piece of evidence that the list moves over time.

### 1.2 Measured evidence

- Krebs scored ~1,590 Show HN landing pages with Playwright DOM and computed-style checks:
  22% triggered 4+ of the patterns (high), 32% 2-3, 46% 0-1; his manual QA puts false
  positives at 5-10% [S1]. The public detector lists 14 patterns: templated display fonts
  (Space Grotesk, Instrument Serif, Geist, Syne, Fraunces), hero font mix, vibe purple,
  gradients, accent stripe on cards, glassmorphism, coloured glow, emoji nav, centred
  hero plus Inter, perma-dark with muted grey body, numbered steps, stat banner, headline
  badge, FAQ accordion [S2]. His score is simply flagged/total, which he warns is
  per-pattern weak [S1][S2]. (The HN thread's 333 points is quoted by [S9]; [verify].)
- Krebs's own quote from a designer: coloured left borders are "almost as reliable a
  sign of AI-generated design as em-dashes for text" [S1].
- Vendor claims such as "94% rely on ..." and "23% lower conversion for Grade D sites
  across 200 A/B tests" [S13] are vendor numbers: [verify], and I do not recommend using
  them.

### 1.3 Hallmark table

| # | Hallmark | Documented by | Rel. | Notes / caveat |
|---|---|---|---|---|
| H1 | Indigo/violet/purple accent, esp. indigo-500 #6366F1 family | [S1][S2][S3][S5][S10][S11][S12] | mod | Origin story via Tailwind demo default [S5][S10][S11]; Wathan tweet [verify]. Tailwind docs example still uses indigo-500 [S78]. Decays: models now flee to cream, emerald [S5][S7][S4]. |
| H2 | Gradient everything, gradient clipped headline text, orbs and blobs | [S1][S2][S5][S6] | mod | Krebs: >=4-5 gradient backgrounds or gradient hero H1 [S2]. Rauno's own guidelines require gradient text to unset gradient on ::selection - so gradient text is legitimate when handled [S32]. |
| H3 | Coloured glow shadows, neon on dark, radial halo | [S1][S2][S5][S6][S7] | weak alone | "Linear style" was hand-built by humans first; FP large [S5]. |
| H4 | Perma dark mode with medium-grey body text, barely passing contrast | [S1][S2][S9] | mod | NN/g: light mode gives better visual performance for normal vision; dark helps some low-vision users [S49]. So dark-by-default is a choice needing a reason. |
| H5 | Inter (or system sans) as the only face, centred hero | [S1][S2][S3][S5][S6] | weak alone | Even Linear uses Inter [S5][verify]. Tell = unchosen font beside 20 unchosen defaults [S5]. |
| H6 | Second-wave fonts: Space Grotesk, Geist, Instrument Serif, Fraunces; italic serif accent word | [S1][S2][S3][S4][S5][S7] | mod | Anthropic says Space Grotesk is its own reflex [S3]. Banning Inter just moves the mode [S7][S3]. |
| H7 | Eyebrow chip / pill badge above H1; repeated all-caps kickers | [S1][S2][S4][S5][S6][S7] | mod | Skill: only legitimate if it encodes info [S4]. |
| H8 | Three identical icon-topped feature cards, bento, icon tile above heading | [S1][S2][S5][S6][S10][S11][S12] | mod | S5: "single most consistently named tell". FP: triptychs are valid. |
| H9 | Cookie-cutter page order: hero, logos, 3 cards, testimonials, stats, pricing, FAQ, CTA | [S5][S6][S18] | weak alone | Standard human playbook too. |
| H10 | Stat banner, hero metric, "1-2-3" steps, "01/02/03" markers, FAQ accordion | [S1][S2][S4][S5][S6] | weak-mod | Strong only if numbers are false [S5]. |
| H11 | Same large radius on everything (rounded-2xl), "ghost card" hairline plus wide shadow, cards inside cards, accent stripe | [S5][S6][S18][S4] | mod | S6 treats "Hairline border with wide shadow", "Nested cards", "Side-tab accent border" as separate detector rules. Refactoring UI itself teaches "add colour with accent borders" [S35], so the stripe is a human tactic over-applied: semantic on alerts, decoration elsewhere [S5]. |
| H12 | Glassmorphism without a layering problem | [S1][S2][S5][S6] | mod | NN/g: glass is legitimate for depth over complex backgrounds but readability suffers; more blur is better; give users a transparency control [S47]. NN/g slams Apple's Liquid Glass for text-on-busy-background contrast [S48]. |
| H13 | Emoji as bullets, feature icons, nav icons | [S1][S2][S5][S19] | strong (decorative) | Rare in hand-built professional work [S5]. |
| H14 | Icon soup: same Lucide five (Sparkles, Zap, Shield, Check, ArrowRight) | [S5] | mod | Linear itself reduced icons because they proliferated [S25]. NN/g: icons need text labels; "universal" icons are rare [S53]. |
| H15 | Sparkle glyph as AI badge | [S21][S22][S23] | n/a | NN/g (n=107 icon study): ambiguous, no standardised meaning; Google design research on the same [S21][S22]. |
| H16 | Uniform motion: same fade-up on every section, stagger, bounce/elastic, pulsing status dots, marquees | [S4][S5][S6] | weak-mod | Skill and S6 both call it out [S4][S6]. Emil: animation must have purpose; frequency of use matters [S28]. |
| H17 | Monotonous spacing, uniform density, one weight everywhere | [S5][S6][S8] | mod | S8 measured "density register" 1.33:1 vs a 1.75 floor across themes [S8]. |
| H18 | Weightless/buzzword copy, em-dash density, forced contrast ("Not X. Y."), fake trust (logos, testimonials, counts) | [S4][S5][S6][S15] | strong when fabricated | Rate not occurrence is the signal [S5]. |
| H19 | Fake terminal hero, emoji headings, placeholder illustrations, plastic 3D blobs | [S5][S6] | mod | |
| H20 | Typeface not shipped (font stack falls back to OS font while token claims Inter/other) | [S8] | strong, verifiable | 6 of 7 generated themes shipped no font file [S8]. |
| H21 | Design intent in a comment never reached a token (claimed raised surface is 0.027 L away) | [S8] | strong, verifiable | Rationale and value written separately, nothing checks they agree [S8]. |
| H22 | One hue pretending to be two (accent within ~5 degrees of primary) | [S8] | strong, verifiable | S8: under ~20 degrees apart is one colour [S8]. |
| H23 | No state ramp: hover/press/disabled invented per component with alpha colours | [S8] | mod | |
| H24 | Missing function: no focus states, no reduced-motion, div soup, skipped headings, no validation | [S5][S10][S13] | strong | Aligns with WCAG [S59][S61][S62]. |
| H25 | Generator attribution/default favicon left in | [S5] | strong | |

### 1.4 What the best sources say about the tells themselves (meta)

1. Judge the absence of decisions, not the presence of a style; stack signs, never single
   ones [S5]. Krebs: "not really bad, just uninspired" [S1].
2. Written guidance fails; mechanical gates work. Solodesign measured six components in
   three arms (no skill / written guidance / mechanical gate): written guidance was equal
   or worse than nothing on 5 of 6 (bento 7.0 -> 11.7 failures), the gate cut it to ~0
   [S7]. Reason: "be distinctive" is read as "add more".
3. Whack-a-mole: close one default and the model finds the next: ban indigo -> emerald;
   ban Inter -> Space Grotesk; ban purple -> cream and italic serif [S3][S5][S7]. Rules
   built as blocklists rot; they need expiry dates and positive requirements.
4. Gates can cause damage: a "load animation needs reduce-motion fallback" rule made the
   model stop writing motion; animated declarations fell 12.4 -> 5.0 and "pages went
   dead" [S7]. Another rule flagged a real unread-notification dot as the decorative
   eyebrow dot [S7].
5. Detector and human disagree: a build set scored cleaner by the detector while the
   human rated it worse [S7]. Human tier is not optional.
6. Authority-adjacent warning: Frank Chimero distrusts "taste" as a label, preferring
   technique and discernment ("if taste exists in technology, it needs to be smuggled
   in") [S81]. Emil Kowalski's counter-position is that taste is articulable as reasons
   (why scale(0) feels wrong) and can be packaged as rules [S27][S31]. Crunk should
   follow Emil: encode reasons, not vibes.

## 2. Classic design mistakes, as catalogued by the craft canon

Each item: mistake -> source -> mechanisation hint (ID in section 4).

### Hierarchy, depth, colour (Refactoring UI, Wathan and Schoger)
- The book's TOC is the catalogue: "Choose a personality", "Limit your choices", "Not all
  elements are equal", "Don't use grey text on colored backgrounds", "Establish a type
  scale", "Establish a spacing and sizing system", "Use fewer borders", "Emulate a light
  source", "Use shadows to convey elevation", "Don't overlook empty states", "You don't
  have to fill the whole screen", "Labels are a last resort", "Supercharge the defaults"
  [S35].
- Palette: you need 8-10 greys, 5-10 shades of primary, and accent/semantic colours with
  shades; define shades up front; do not generate with lighten()/darken() or you get
  "35 slightly different blues"; trust your eyes over formulas [S36].
- Use fewer borders: use shadow, background contrast or space instead [S35]. Linear's own
  refresh says the same ("structure should be felt not seen"; borders "quietly
  proliferated") [S25].
- Shadows (Comeau): decide one light source; every shadow shares the same offset ratio;
  shadows signal elevation and direct attention; otherwise "a bunch of blurry borders"
  [S37].

### Typography
- Butterick: body text decides typographic quality; body size 15-25 px on the web; line
  spacing 120-145% of point size; line length 45-90 characters (2-3 alphabets); avoid
  system fonts and free ubiquitous fonts when possible; "never choose Times New Roman or
  Arial" [S40][S41][S42][S43].
- Every Layout: measure 45-75 characters per Elements of Typographic Style; design
  axioms system-wide or "output will be inconsistent and malformed" [S44]; modular
  scale from a single ratio custom property [S45]; the Stack primitive owns vertical
  rhythm instead of per-component margins [S46].
- Emil's typography rules: cap body ~65ch, tabular-nums for numbers, loosen letter-spacing
  on uppercase labels, fallback stack metric-matched to avoid layout shift, reserve
  underline for links, prefer bold over italic for UI emphasis [S27].
- Impeccable's catalog agrees: line length 65-75, line-height ~1.5, body ~16px,
  no justified text, no all-caps body, no crushed tracking, flat hierarchy [S6].

### Contrast and accessibility
- WCAG 2.2 SC 1.4.3: 4.5:1 normal text, 3:1 large text [S59]. SC 2.5.8 target >= 24x24
  CSS px (with spacing exception) [S60]. SC 2.4.13 focus appearance [S61]; Soueidan:
  focus indicators need 3:1 against adjacent colours, never `outline: none` without
  replacement [S65]. SC 2.3.3 interaction-triggered motion must be disableable [S62].
- APCA: perceptual lightness contrast Lc; WCAG 2 contrast math has known issues; still
  a draft model, so treat as advisory [S64].
- Stripe: audit found none of its default small-text colours (except black) met 4.5:1;
  fixed by a perceptual-colour tool that keeps hues vibrant while guaranteeing contrast;
  design goals "predictable accessibility, clear vibrant hues, consistent visual weight"
  [S73].
- Disabled buttons: no feedback, feel broken, low contrast, not focusable, deceptive;
  prefer an enabled button plus an error summary (Adam Silver, 2023-05-14) [S66]. Rauno:
  disabled buttons should not have tooltips (not focusable) [S32].
- Tooltips: Pickering's Inclusive Components distinguishes tooltips from toggletips and
  warns on hover-only content [S67].

### Layout and rhythm
- Every Layout: compose from primitives (Stack, etc.) with a modular scale instead of
  ad hoc margins [S45][S46]. Refactoring UI: "grids are overrated", avoid ambiguous
  spacing, start with too much white space [S35].
- Heading closer to the previous section than its own content, cramped padding, text
  touching viewport edge, unbalanced columns are catalogued as layout quality bugs [S6].

### Motion
- Emil: animations need a purpose; consider frequency (Raycast has none, optimal); under
  300 ms; ease-out for entering/exiting; no scale(0); button press scale 0.97;
  transform-origin from the trigger; subsequent tooltips skip delay [S28][S29][S30][S27].
- Rauno: duration <= 200 ms for interactions to feel immediate; animation values
  proportional to trigger size; skip animation on frequent low-novelty actions; hover
  states only for hover-capable devices; pause offscreen loops [S32].
- NN/g: animation guidance - consider goal, frequency, mechanics [S52]. Smashing
  "Gild just one lily": fundamentals first, then one restrained flourish [S86].

### Copy and content design
- Mailchimp: constant voice, varying tone by user emotional state; "subtle over noisy,
  wry over farcical" [S69]. GOV.UK style guide demonstrates enforceable plain-English
  term rules (e.g. prefer "send" over "deliver" in a legal context) [S70].
- Anthropic's skill: CTA names the action ("Save changes" not "Submit"), same name through
  the flow, errors never apologise and never vague, empty screen is an invitation [S4].
- Sarah Richards / content design: [unsourced] (stub page only).

### Forms, density, affordance
- NN/g form spacing: group related fields with whitespace [S58]. Flat design removes
  signifiers on clickables; "Flat 2.0" restores them [S50]. Hidden navigation cuts
  discoverability roughly in half [S56]. Heuristic 8: every extra unit of information
  competes with the relevant units [S51]. Photos: users ignore decorative stock photos
  and scrutinise real people and products [S54]. Trust: design quality, upfront
  disclosure, comprehensive current content, connection to the web [S55]. Legibility,
  readability, comprehension [S57].
- Tufte: chartjunk = decoration that conveys nothing; the dataviz parallel of H2/H3.
  Fetched only via Wikipedia (primary 403): secondary [S72].
- Dieter Rams (Vitsoe): good design is unobtrusive, honest, and "as little design as
  possible: less, but better" [S71].

## 3. What "soul" means concretely (craft signals)

Evidence-backed craft signals, with who praises what:

1. Decisions you can name. Linear's Karri Saarinen: quality is a commitment; spec is the
   baseline not the goal; the best design is opinionated for someone in particular;
   reduce scope to raise quality; trust intuition over A/B data [S24]. Refactoring UI:
   "choose a personality", "limit your choices" [S35].
2. Restraint as hierarchy. Linear March 2026 refresh: "don't compete for attention you
   haven't earned" (dim the sidebar, shrink tabs, reduce icon use, remove coloured icon
   backgrounds) and "structure should be felt not seen" (fewer, softer borders) [S25].
   Linear 2024 redesign: reduce visual noise, maintain alignment, raise density [S26].
3. Semantic colour with roles, not a swatch. Vercel Geist: 10 scales, numbered roles
   (1-3 component backgrounds with hover/active, 4-6 borders, 7-8 high-contrast fills,
   9-10 text/icons) [S75]; Stripe: accessible and vibrant with consistent visual weight
   [S73]; Refactoring UI greys/primary/accent split [S36].
4. A real type system. Geist ships typography presets bundling size, line-height,
   tracking and weight [S76]; Butterick/Every Layout supply measure, leading, scale
   [S40][S41][S44][S45]; Anthropic skill: set a clear type scale; one or two families,
   clearly distinct if two [S4].
5. Interaction details. Rauno's "Invisible details": interaction design as making
   experiences "fluidly respond to human intent" and rewarding reused metaphors [S33];
   his guidelines: label focuses input, no dead zones between list items, prediction
   cone for nested menus, optimistic updates, `::selection` styled, empty states
   prompt creation, inline checkmark on copy instead of a toast [S32]. Emil: origin-aware
   popovers, spring interactions for decorative response, 44 px hit areas [S30][S27].
6. Optical alignment. Shadeed: icon-and-label lists must keep the icon aligned to the
   first line when text wraps, rather than centring [S68] (a 2026-09-15 article).
7. Aesthetic with authoring intent. Rauno: contrasting aesthetics with "authoring
   intent, purpose, and a sense of iteration" as opposed to arbitrary excess [S34].
   Smashing: gild one lily after the fundamentals [S86].
8. Honest copy with a voice. Mailchimp voice vs tone [S69]; skill rules on plain verbs
   [S4]; trust requires upfront disclosure [S55]; real people photos [S54].
9. Real content and imagery, density suited to the task. Anthropic skill: "build with
   the brief's real content", open with the most characteristic thing in the subject
   world [S4]. NN/g photos [S54]. Linear keeps "rich density of information" without
   overwhelm [S25].
10. Consistent component behaviour and the boring system. Brad Frost (via Josh Clark):
    "the most exciting design systems are boring" - systems carry the burden of the
    boring so humans solve new problems [S84].
11. Performance and robustness as craft. Rauno: subset fonts, avoid giant blur values,
    pause offscreen animations, adapt to device capability [S32]; Impeccable lists
    content stuck at opacity 0, JS errors on load, clipped menus as quality defects [S6].

Products praised (only what I could fetch):
- Linear: own writing on craft and calm UI [S24][S25][S26]; the Saarinen rules are
  self-reported, not third-party praise.
- Stripe: public engineering on accessible vibrant colour and a front-end built with
  CSS Grid and per-frame-computed 3D shading for the Connect page [S73][S74].
- Vercel: Geist colour and type systems [S75][S76].
- Things (Cultured Code): two Apple Design Awards and press quotes on "never feels messy
  or overbearing" [S77] (vendor page quoting third parties).
- Teenage Engineering, Panic, Arc: [unsourced]; fetch failed. No rule derived from them.
- Caution: praising Linear/Stripe/Vercel is a loop; the dark glow SaaS look is a Linear
  descendant, and copying it is a slop source [S5].

## 4. Mechanical detectability catalogue

Tiers follow crunk's draft: T0 static (tokens/CSS/TSX/copy), T1 layout solve, T2 render,
T3 live DOM, T4 human [crunk.md section 4]. IDs: new families SLOP (known tells, defaults
without a decision) and CRAFT (positive requirements, so rules cannot be satisfied by
deleting things). Where an existing family fits, I give that ID and cross-list.

Severity vocabulary: Advisory (default for SLOP), Warn, Error. SLOP rules fire
Advisory only when the project did not declare the choice in `design/` (the "unchosen"
test). Impeccable already ships exactly this idea as "Font/Color/Radius/Font size outside
DESIGN.md" [S6]; crunk should generalise it: every SLOP rule has a "declared intent"
escape (token with a `rationale` string).

### 4.1 Colour

| ID | Signal | Tier | Heuristic | FP risk | Sev | Src |
|---|---|---|---|---|---|---|
| SLOP001 | Default Tailwind indigo/violet/purple accent unchosen | T0 | Resolve CTA/link/primary colours; flag if equal (OKLCH distance < 0.02) to Tailwind indigo/violet/purple 400-700 stops (#6366F1 #8B5CF6 #A855F7 etc.) AND no semantic token named for the brand maps to it. Krebs: filled indigo/violet accent count >= 1 [S2] | Real purple brands | Advisory | [S2][S5][S78] |
| SLOP002 | Any untouched default palette | T0 | Share of distinct colour literals that exactly match a Tailwind default scale stop (>60%) and zero custom tokens (cf. COLOR "literal not a token") | Tailwind-using teams that use tokens as aliases | Advisory | [S5][S78][S79] |
| SLOP003 | Gradient abuse | T0/T2 | Count elements with visible-stop gradient backgrounds; Krebs minBgGradients = 4, plus hero H1 with background-clip:text and font-size >= 40px [S2]. Add: gradient on text/metric numbers anywhere | Data viz, brand art | Advisory (>=4), Warn (gradient text on > 1 element without token) | [S2][S5][S6] |
| SLOP004 | Coloured glow shadows | T0 | box-shadow colour saturation > 0.3, lightness 0.2-0.9, blur >= 15 px, >= 2 instances [S2] | Focus rings legitimately glow | Advisory | [S2][S6] |
| SLOP005 | Perma-dark body contrast | T2 | Dark surface luminance < 0.2 and >= N% of body text under 7:1 (AAA) on it [S2]. Never as Error: WCAG AA is the Error rule (A11Y) | Dark brands | Advisory | [S2][S49] |
| SLOP006 | Accent that is one hue twice | T0 | OKLCH hue delta between primary and accent < 20 degrees (and chroma/lightness near) [S8]; unused-role accent | Monochrome by design - allow `palette.style = "mono"` | Warn | [S8] |
| SLOP007 | Evenly weighted timid palette | T0 | No token has > 2x the use share of others; > 4 hues at similar chroma used at similar frequency | Weak signal | Advisory, weight "weak" | [S5][S3] |
| SLOP008 | Second-wave palette defaults | T0 | cream background in [#F2EDE3..#F6F3EC] + accent in terracotta band; or near-black + single acid green/vermilion; emerald #10B981 as primary [S4][S5][S7]. Treat as data file with as_of date | Editorial/food brands | Advisory, weak | [S4][S5][S7] |
| COLOR-ROLE | Missing roles: no semantic danger/warn/success, one grey only | T0 | Palette must define greys (8+ steps) primary, accent, semantic (Refactoring UI) [S36]; Geist shows a numbered role model [S75] | Tiny projects | Warn | [S36][S75] |
| COLOR-GREYTXT | Grey text on a coloured background | T0/T2 | Compute contrast; flag text with chroma < 0.02 on a surface chroma > 0.08 | Few | Warn | [S35][S6] |
| A11Y-CONTRAST | 4.5:1 / 3:1 | T0 (declared pairs), T2 (images, gradients) | Standard; APCA as secondary advisory [S59][S64] | Gradient/glass text | Error | [S59][S64][S47] |

### 4.2 Typography

| ID | Signal | Tier | Heuristic | FP | Sev | Src |
|---|---|---|---|---|---|---|
| SLOP010 | Font unchosen | T0 | Computed families for body+heading are exactly {Inter, Roboto, Arial, system-ui} or the second-wave set {Space Grotesk, Geist, Instrument Serif, Fraunces, Syne} and `design/fonts.toml` has no `rationale` | Chosen Inter | Advisory | [S2][S3][S5] |
| SLOP011 | Font declared but not shipped | T0 | `--font-*` first family not present in fonts.toml hash list / no @font-face or font file; falls to ui-sans-serif/system-ui [S8] | System stack by decision | Warn (Error if tokens claim a named face) | [S8] |
| SLOP012 | Single family, single weight, flat hierarchy | T0 | Count distinct (family, size, weight); fewer than 4 sizes in use, or adjacent scale ratio < 1.125, or h1/body ratio < 1.8 [S6] | Dense tools | Warn | [S5][S6][S35] |
| SLOP013 | Italic serif accent word in sans headline | T0 | `<em>/<i>` or span inside h1/h2 whose font-family differs from heading family; or italic serif display > 48 px | Editorial brands | Advisory | [S2][S4][S5][S6] |
| SLOP014 | Eyebrow/kicker chrome | T0 | Short (<= 4 words) uppercase+tracked text immediately before an h1/h2 in >= 3 sections; a pill with fill/border above H1 (Krebs rules) [S2] | Section navigation labels | Advisory | [S2][S4][S6] |
| SLOP015 | All-caps overuse | T0 | > 25% of headings/labels `text-transform: uppercase`; any body paragraph > 3 lines uppercase [S6] | Short UI labels are fine | Advisory | [S4][S5][S6] |
| SLOP016 | Monospace as decoration | T0 | Body paragraphs or marketing labels in a `monospace` family outside code/data contexts | Dev tools | Advisory | [S5][S7] |
| TYPE-SCALE | Off-scale font sizes | T0 | Size not in declared scale (crunk TYPE family already) | None | Warn | [S45][S6] |
| TYPE-MEASURE | Line length | T1/T2 | Paragraph max-width in ch: warn > 80ch; error > 100ch; min 45 [S40][S41][S44] | Wide tables | Warn | [S41][S44] |
| TYPE-LEADING | Line-height | T0 | Body unitless line-height outside 1.2-1.5 (Butterick 120-145%); headings < 1.0 | Large display type | Warn | [S40] |
| TYPE-SIZE | Tiny body text | T0 | Body < 15px (Butterick 15-25) or < 16 px on touch inputs (Rauno) [S32][S42] | Captions | Warn | [S32][S42] |
| TYPE-TRACK | Crushed tracking, wide tracking on body | T0 | letter-spacing < -0.04em at < 32px; > 0.1em on > 3-line text | Display logos | Warn | [S6][S27] |
| TYPE-NUM | tabular-nums missing in numeric columns | T0 | Table/stat cells containing digits without font-variant-numeric: tabular-nums | Few | Advisory | [S27][S32] |
| TYPE-JUSTIFY | text-align: justify on web body | T0 | | | Warn | [S6] |

### 4.3 Layout, spacing, structure

| ID | Signal | Tier | Heuristic | FP | Sev | Src |
|---|---|---|---|---|---|---|
| SLOP020 | Three identical icon-topped cards | T0 (TSX) / T1 | Sibling group with 3 children of near-identical structure (icon, heading, paragraph), or >= 3 repeated cards with same component and no variation prop | Legit feature trio | Advisory, moderate | [S5][S6][S10] |
| SLOP021 | Everything-is-a-card / nesting | T0/T1 | Card-like surface (bg+border/shadow+radius) nesting depth > 2 [S6]; > 70% of section children are cards | Dashboards | Warn at depth 3 | [S5][S6] |
| SLOP022 | Uniform radius | T0 | Distinct border-radius values in use <= 1 across >= 3 element kinds, or radius >= 16px on > 60% of surfaces, or a radius scale token set with all steps equal. Counter-signal: crunk RADIUS policy declares per-role radii [S79 derived scale] | Rounded-by-design brand | Advisory | [S5][S6][S18][S4] |
| SLOP023 | Accent stripe on card | T0/T2 | border-left/top >= 2 px solid saturated (s >= 0.2) on a non-alert element with other sides ~0, or narrow full-edge ::before (Krebs thresholds) [S2] | Real alerts: gate on role=alert/status | Advisory (Warn if > 2 instances) | [S1][S2][S5][S6] |
| SLOP024 | Ghost card | T0 | Same surface has 1px border AND blur >= 20px shadow | Common | Advisory | [S5][S6] |
| SLOP025 | Glassmorphism | T0/T2 | backdrop-filter blur on translucent surface not overlapping imagery/other layer (needs T2 occlusion check); + contrast fail over background [S47] | Overlay on photo | Advisory; contrast part Error | [S2][S5][S47] |
| SLOP026 | Centred everything | T0/T1 | text-align:center on blocks > 3 lines (or > 160 chars); > 60% of sections centre-aligned | Hero, short blocks | Warn >3 lines | [S2][S4][S5] |
| SLOP027 | One layout for all sections | T1 | Structural fingerprint (grid columns, alignment, count of children) identical across >= 4 consecutive sections; also high similarity in section padding | Documentation pages | Advisory | [S5][S6][S8] |
| SLOP028 | Monotonous spacing / no rhythm | T0/T1 | Entropy of used spacing tokens: > 80% usage on one step; identical vertical padding for all sections; or section gaps equal to intra-card gaps (no grouping) [S6] | Dense lists | Advisory | [S5][S6][S8] |
| SLOP029 | Uniform density | T1 | Ratio of largest to smallest vertical band weight < 1.75 (Tailthemes' measured floor) [S8]; zero "oversized moments" | Apps | Advisory | [S8] |
| SPACE-SCALE | Off-scale spacing/padding | T0 | Spacing literal not in token scale (crunk SPACE) | None | Warn | [S35][S45] |
| SPACE-GROUP | Heading closer to previous block than own content | T1 | Gap-above < gap-below | None | Warn | [S6] |
| LAYOUT-FILL | Cards flush against scroller edge, body touching viewport edge, cramped padding | T1 | | | Warn | [S6] |
| SLOP030 | Cookie-cutter section order | T0 | Section role sequence matches {hero, logos, features3, testimonials, stats, pricing, faq, cta} with edit distance <= 1 | Honest landing pages | Advisory, weak | [S5] |
| SLOP031 | Hero formula | T0/T1 | Centred stack: pill + H1 >= 56px + one-line sub + 2 CTAs (primary "Get Started") + decorative glow [S5][S2] | Many real heroes | Advisory | [S2][S5] |
| SLOP032 | Stat banner / hero metric | T0 | 3-6 sibling items each with number <= 10 chars at >= 22 px [S2]; counters animated | Real metrics | Advisory | [S2][S6] |
| SLOP033 | Numbered markers without sequence | T0 | 01/02/03 labels where list is not `<ol>` or flow steps [S4][S6] | Real steps | Advisory | [S2][S4] |
| SLOP034 | FAQ accordion with 3+ Q&A paraphrasing page content | T0/T4 | Count + near-duplicate text (embedding or n-gram overlap) of Q with headings on same page | Real FAQs | Advisory | [S2][S5] |

### 4.4 Components, icons, imagery

| ID | Signal | Tier | Heuristic | FP | Sev | Src |
|---|---|---|---|---|---|---|
| SLOP040 | Emoji as bullet/icon/nav | T0 | Unicode emoji codepoints (Extended_Pictographic) at start of list items, headings, nav labels, buttons [S2] | Chat apps, user content | Warn (high precision) | [S2][S5] |
| SLOP041 | Icon soup | T0 | Icon-to-text ratio: > 1 icon per 12 words in a section; icons on > 80% of cards; same Lucide icon subset across unrelated products (Sparkles, Zap, Shield, Check, ArrowRight) [S5] | Toolbars | Advisory | [S5][S25][S53] |
| SLOP042 | Icon tile above heading | T0 | Rounded-square container with only an icon, preceding a heading in a card [S6] | Common | Advisory | [S5][S6] |
| SLOP043 | Sparkle as AI glyph | T0 | Sparkles icon/emoji without accessible label naming the feature [S21] | Product that does AI | Advisory | [S21][S22][S23] |
| COMP-ICONLABEL | Icon-only control lacks text or aria-label | T0 | [S32][S53] | | Error (a11y) | [S32][S53] |
| SLOP044 | Placeholder/stock illustration | T2/T4 | alt/src patterns (unsplash, placeholder, picsum), generic circles-and-blocks SVG heuristics weak; recommend T4 | Hard | Advisory | [S5][S6][S54] |
| SLOP045 | Fake trust artifacts | T0/T4 | Logo wall: image names do not map to a declared customers list; testimonials without verifiable names/links; "Trusted by N+" literal not bound to a data key; SOC 2 badge with no `evidence` field [S5][S15] | None | Warn when content keys lack provenance | [S5][S15][S55] |
| SLOP046 | Fake terminal hero | T0 | Three dots (red/yellow/green circles) + monospace block in hero of non-dev product | Dev tools | Advisory | [S5] |
| SLOP047 | Generator residue | T0 | "Built with v0/Lovable", default favicon, `lovable.dev` meta, shadcn default file names | | Warn | [S5] |
| STATE-COVER | Empty / loading / error / disabled states exist per component | T0 | Component spec must declare states; empty-state must offer an action [S4][S32][S35] | | Warn | [S4][S32][S35] |
| COMP-DISABLED | Disabled submit button without explanation | T0 | `disabled` on form submit; recommend enabled + error summary [S66] | Rare | Warn | [S66][S32] |
| COMP-TOOLTIP | Interactive content in hover tooltip; tooltip on disabled | T0 | [S67][S32] | | Warn | [S67][S32] |

### 4.5 Motion

| ID | Signal | Tier | Heuristic | FP | Sev | Src |
|---|---|---|---|---|---|---|
| SLOP050 | Same entrance on every section | T0 | One keyframe/Motion variant (opacity 0 + translateY 20) applied to >= 4 siblings sections with uniform stagger [S4][S5] | Pages with one reveal | Advisory | [S4][S5] |
| MOTION-TOKEN | Duration/easing literals outside tokens | T0 | | | Warn | [S28][S27] |
| MOTION-DUR | Duration > 300 ms for UI (non-marketing), > 200 for interactions | T0 | Emil <300 ms; Rauno <= 200 ms for immediate feel [S28][S32] | Marketing | Warn | [S28][S32] |
| MOTION-SCALE0 | Entrance from scale(0) | T0 | [S29][S32] | | Warn | [S29] |
| MOTION-BOUNCE | Bounce/elastic overshoot on routine dialogs | T0 | cubic-bezier y > 1.0 / spring bounce > 0 on dialog/menu [S6] | Playful brands | Advisory | [S5][S6] |
| MOTION-LAYOUT | Animating width/height/top/left | T0 | [S6][S32] | | Warn | [S6] |
| MOTION-REDUCED | No `prefers-reduced-motion` twin | T0 | Any non-essential motion token without reduced twin (SC 2.3.3) [S62] | | Error at release | [S62] |
| MOTION-FREQ | Animation on high-frequency/keyboard-driven actions | T4 | command palettes/menus: should be none [S28] | | Human only | [S28] |
| SLOP051 | Decorative perpetual motion | T0 | infinite animation on status dots, blinking cursors, marquees, pulsing | Real activity indicators | Advisory | [S6] |
| SLOP052 | Hover-zoom on every image/card | T0 | transform scale on :hover in > N components | | Advisory | [S6][S4] |
| MOTION-STUCK | Content waits at opacity:0 | T3 | Elements opacity 0 after load+timeout [S6] | | Error | [S6] |
| MOTION-FLASH | Flash threshold | T2 | | | Error | [S59][S62] |

### 4.6 Copy

| ID | Signal | Tier | Heuristic | FP | Sev | Src |
|---|---|---|---|---|---|---|
| SLOP060 | Buzzword density | T0 | Weighted lexicon (seamless, unlock, elevate, supercharge, streamline, empower, world-class, enterprise-grade, best-in-class, battle-tested, unleash, robust, comprehensive, "in today's fast-paced world") per 100 words > threshold; per `design/content` tone file allow/deny list [S5][S6] | Quoted copy | Advisory (density), never single hit | [S5][S6] |
| SLOP061 | Weightless headline | T0/T4 | "Build faster. Ship smarter." three-beat parallel structure; heading with no noun from the glossary / product terms [S5] | Hard | Advisory | [S5] |
| SLOP062 | Em-dash density, forced contrast, "not X. Y." | T0 | Em dash > 1 per 60 words in marketing copy; regex "Not a .*\. A " ; "isn't just" [S5][S6] | Good writers | Advisory | [S5][S6] |
| SLOP063 | Title Case Everything | T0 | > 90% of headings/buttons Title Case when voice file says sentence case [S5][S4] | | Advisory | [S4][S5] |
| CONTENT-CTA | Generic CTA labels ("Submit", "Get Started") | T0 | CTA verbs not from glossary; success toast name differs from button verb [S4] | | Warn | [S4] |
| CONTENT-ERR | Error copy apologises or is vague; empty state without action | T0 | Lexicon "Oops", "Sorry"; no remediation noun [S4] | | Warn | [S4][S69] |
| CONTENT-DUP | Same label repeated in one container / redundant field explanation | T0 | [S6] | | Warn | [S6] |
| CONTENT-BUDGET | Length budgets (existing) | T0/T1 | | | Warn | [S69][S70] |
| CONTENT-VOICE | Voice and tone file present and used | T0 | `design/content/voice.toml` must exist when any scene uses copy keys | | Warn | [S69] |

### 4.7 CRAFT (positive requirements)

Purpose: make the removal of a feature not satisfy the rule (see 1.4 point 4, [S7]).

| ID | Requirement | Tier | Heuristic | Src |
|---|---|---|---|---|
| CRAFT001 | Focus-visible style defined and >= 3:1 on every interactive component state | T0/T3 | [S61][S65] |
| CRAFT002 | Hover, active, disabled, focus, loading, error, empty states exist per component | T0 | [S4][S32] |
| CRAFT003 | Exactly one declared "moment": at most one oversized element/band per screen is allowed; fewer than 1 on a long page is advisory | T1 | [S8][S4] |
| CRAFT004 | Fonts shipped and subset; font-display and metric-matched fallback | T0 | [S8][S27][S32] |
| CRAFT005 | Press feedback present on primary actions (transform scale ~0.97 or colour step) | T0 | [S29][S27] |
| CRAFT006 | Type scale and spacing scale present, ratios declared | T0 | [S45][S35] |
| CRAFT007 | Elevation system: shadow tokens share one offset ratio and light angle | T0 | [S37][S35] |
| CRAFT008 | Semantic colour roles complete with state ramp | T0 | [S36][S75][S8] |
| CRAFT009 | Real content: every copy key bound; imagery has alt and provenance record | T0 | [S54][S4] |
| CRAFT010 | Reduced-motion and reduced-transparency twins | T0 | [S62][S47] |
| CRAFT011 | Optical alignment spot-checks: icon-label first-line alignment, baseline vs centre alignment of mixed sizes | T1 | [S68][S35] |
| CRAFT012 | Intent coverage: >= 90% of rendered values resolve to declared tokens | T0 | [S6][S8] |

### 4.8 Only a human can judge (T4)

- Whether a font fits the product's register (S7: "matching the typeface to the register
  instead of reaching for the most distinctive face") [S7].
- Distinctiveness and composition; "would I ship it" [S7].
- Whether a motion is purposeful and correctly felt (Emil: "what it can't do is know what
  feels right") [S31]; frequency-appropriate motion [S28].
- Whether a grid of three cards is honest structure or forced triplicate [S5].
- Whether copy has a voice rather than buzzwords; whether claims are true [S5][S69].
- Whether imagery is specific to the subject or generic stock/AI art [S54][S6].
- Whether a "gild" is earned [S86].
- Calibrating the tell list over time (tells decay) [S5].

#### How crunk records the verdicts (proposal)

1. Verdict record per subject: `design/verdicts/<subject>.toml` or `crunk.lock` rows
   keyed by (subject id, content hash, rule id): `verdict = "present"|"not_present"|"intentional"|"skip"`,
   `by`, `at`, `note`. Mirrors the label tool Krebs ships (present / not_present / skip,
   appended to `dataset/labels.jsonl`, with `npm run eval` computing precision/recall
   against labels) [S2]. Mirrors crunk draft's existing ack-by-content-hash for T4 [crunk.md 4.1].
2. "Intentional" is a first-class verdict that writes a waiver with a reason
   (waivers are how S6's "a finding is a reason to look closer" works in practice [S6]).
3. Gallery triage: the gallery renders each screen/state at each profile, shows the
   overlay of findings (Impeccable's overlays are prior art [S6]), asks one
   question per subject group ("Does this section show a decision or a default?"), and
   stores verdicts. Rate-limit the queue: show the K subjects with the highest
   disagreement between SLOP signal count and last verdict.
4. Eval loop: every verdict feeds `crunk eval` precision/recall per rule; a rule whose
   precision drops below a floor (Krebs saw 5-10% FP [S1]) auto-demotes severity.
   Solodesign found a rule that flagged a legitimate unread-notification dot; verdicts
   scope rules to contexts [S7].
5. Side-by-side convergence test: render the same brief for N projects and diff
   structural fingerprints; S5 notes convergence across unrelated sources is the
   meta-tell [S5].

## 5. The anti-slop design-system starter (minimum decisions)

Principle: crunk checks code against declared intent, not taste. Adopted from
Impeccable's "outside DESIGN.md" checks [S6], Anthropic skill's two-pass plan with
4-6 named hex values and type roles [S4], and Noqta/Tailthemes arguments that AI and
reviewers need exact values not adjectives [S18][S8].

Minimum files (all under `design/`, per crunk draft; additions are marked NEW):

1. Subject statement (NEW `design/brief.toml`): product, audience, primary job, three
   adjectives, one "memorable thing" per screen, and named non-goals. Source: skill
   "ground your designs in the subject matter" [S4]; Karri "design for someone in
   particular" [S24].
2. Type: <= 2 families with roles and a one-line rationale each; licence and hash
   (fonts.toml); modular scale ratio and base size; measure (ch) per context; line-height
   rules; tracking rules for caps [S40][S41][S44][S45][S27].
3. Palette roles (NOT swatches): neutral ramp (8-10), primary ramp, accent ramp, and
   semantic (success/warn/danger/info) each with a state ramp; contrast pairs declared per
   mode; one dominant colour and one sharp accent [S36][S75][S73][S3].
4. Spacing rhythm: base unit, named steps, and a declared rhythm map (tight inside group,
   loose between groups, section spacing varies by role) [S46][S35][S6].
5. Radius policy: named radii by role (control, surface, overlay, pill) with numbers;
   explicit statement of when a different radius is allowed [S79][S6].
6. Elevation/depth policy: border-or-shadow choice, one light source, shadow ratio [S37][S25].
7. Motion policy: duration bands, easing per intent, frequency exemptions (no animation
   on keyboard-driven or high-frequency actions), reduced-motion behaviour [S28][S32][S62].
8. Density policy per surface (marketing / app / data): what base text size, row height,
   cards allowed or not [S25][S51].
9. Icon policy: one icon set, size ladder, labelled-or-tooltip rule, no emoji [S53][S25].
10. Voice and tone file: voice (constant), tone by situation, banned/preferred lexicon with
    reasons, CTA verb glossary, error and empty-state templates [S69][S70][S4].
11. Imagery/provenance policy: real photography or illustration style, alt text rule,
    no stock-of-people, record source/licence [S54].
12. Trust-claims register: every number, logo, testimonial and badge has a source and
    verifiability date, or it is not shipped [S5][S55].
13. Waiver ledger: decisions that deliberately match a "tell" (e.g., Inter chosen because
    ...), each with reason and review date (tells decay) [S5].

## 6. Slop score report (never an opaque single number)

Design (informed by Krebs's flagged/total formula [S2] and Tailthemes' per-component
critiques [S8]):

- Unit of report: per-signal evidence list, grouped by family and weighted class
  (strong / moderate / weak from [S5]), each with: rule id, location (screen, node,
  token), measured value, threshold, "declared?" flag, waiver flag.
- Headline is a vector, not a scalar: `{ strong: n, moderate: n, weak: n,
  unchosen_defaults: n/total_decisions, intent_coverage: %, human_verdicts: {present, intentional, open} }`.
  Optionally a tier label ("converged defaults" when >= 4 moderate unchosen signals,
  echoing Krebs's 4+ = high, 2-3 = medium, 0-1 = low [S1]) with the vector shown next to it.
- Show what was NOT checked (T2/T3/T4 skipped) so a clean score cannot be mistaken for
  quality: "clean detector only proves no known defect" [S7].
- Pair with CRAFT presence checks and a "delta since last run" to detect gate-gaming
  (e.g., motion declarations dropping 60% in one change) [S7].
- Stable explain output: `crunk explain SLOP022` prints the cause (Tailwind/shadcn default
  radius scale [S79]), the fix, FP cases, and sources.
- Shipping rule: SLOP never blocks CI by itself; blocks at release only on strong
  signals (fabricated trust, undelivered fonts, generator residue, missing focus
  or reduced-motion) and unreviewed T4 items [S5][S8].

## 7. Design-for-crunk recommendations (derived, each tied to evidence)

1. Define tell lists as data with `as_of` and `status` (active / migrating / retired)
   because the list rots (purple -> cream/emerald; hands retired in image tells) [S5].
2. Treat "unchosen" as the trigger: no declared token with rationale -> advisory.
3. Pair every SLOP rule with a CRAFT presence rule (anti-gaming) [S7].
4. Prefer structural fingerprints (sibling similarity, alignment, entropy) over
   blocklists; blocklists get whack-a-moled [S3][S7].
5. Make the human verdict part of the loop and measure rule precision [S2][S7].
6. Do not derive rules from unfetched sources; the unsourced list in section 0 is a
   to-do for the next research pass.

## 8. Open questions / [verify]

- Primary Wathan tweet (Aug 2025) and its view count [verify].
- Krebs HN thread score and the "16 vs 14 patterns" discrepancy: blog lists 16 patterns,
  repo lists 14 [S1][S2][S9]; likely sub-signals split (fonts) [verify].
- Vendor stats [S13] [verify].
- Whether Linear/Stripe/Vercel craft claims hold in current product (self-reported) [S24-S26].
- APCA status in WCAG 3 draft [verify]; use as advisory only [S64].

## 9. Sources table

Key | Fetched | Author, title, date | URL | Supports
(fetched = yes means HTTP 200 body read with curl in this session)

### 9.1 AI-slop discourse and detectors

| Key | Fetched | Author, title, date | URL | Supports |
|---|---|---|---|---|
| S1 | yes | Adrian Krebs, "Scoring Show HN submissions for AI design patterns", Apr 2026 (HN listing 2026-04-19) | https://www.adriankrebs.ch/blog/design-slop/ | 16 patterns, 22/32/46% tiers, FP 5-10%, left border quote |
| S2 | yes | Adrian Krebs, design-slop-cop README and src/patterns (gradients.js, accent-stripe.js, perma-dark-mode.js, hero-eyebrow-pill.js, stat-banner.js, colored-glows.js, purple-accent.js) | https://raw.githubusercontent.com/AdrianKrebs/ai-design-checker/main/README.md ; https://raw.githubusercontent.com/AdrianKrebs/design-slop-cop/main/src/patterns/gradients.js | 14 patterns, thresholds, label tool |
| S3 | yes | Anthropic, claude-cookbooks "Frontend Aesthetics: A Prompting Guide" notebook, 2025-11-14 (HN listing) | https://raw.githubusercontent.com/anthropics/claude-cookbooks/main/coding/prompting_for_frontend_aesthetics.ipynb | Model self-description of slop; Space Grotesk convergence |
| S4 | yes | Anthropic, skills/frontend-design SKILL.md, n.d. (current main) | https://raw.githubusercontent.com/anthropics/skills/main/skills/frontend-design/SKILL.md | Tells list, structure-as-information, writing rules |
| S5 | yes | febbhav (Febian), "Signs of AI design" README, n.d. (2026) | https://raw.githubusercontent.com/febbhav/signs-of-ai-design/main/README.md (and SOURCES.md) | Hallmark taxonomy, reliability grades, mechanisms |
| S6 | yes | Impeccable, "Slop" catalog, n.d. | https://impeccable.style/slop/ | 59 detector rules, design-system-outside checks |
| S7 | yes | solodesign.cc, "AI design slop: the tells...", 2026-06-06 | https://solodesign.cc/blog/ai-design-slop-the-tells/ | Gate vs guidance data, whack-a-mole, motion deletion |
| S8 | yes | TailThemes, "AI Design Slop: The 5 Tells...", 2026-08-20 | https://tailthemes.com/blog/ai-design-slop-quality-gate | Measured checks: fonts not shipped, hue delta, density |
| S9 | yes | Developers Digest, "AI Design Slop: 16 Patterns...", 2026-04-22 (upd. Oct 6 2026) | https://www.developersdigest.tech/blog/ai-design-slop-and-how-to-spot-it | Secondary summary of S1 |
| S10 | yes | prg.sh, "Why Your AI Keeps Building the Same Purple Gradient Website", 2025-10-26 | https://prg.sh/ramblings/Why-Your-AI-Keeps-Building-the-Same-Purple-Gradient-Website | Wathan story (secondary), missing functional pieces |
| S11 | yes | dev.to alanwest, "Why Every AI-Built Website Looks the Same (Blame Tailwind's Indigo-500)", 2026-03-25 | https://dev.to/alanwest/why-every-ai-built-website-looks-the-same-blame-tailwinds-indigo-500-3h2p | Mechanism, feedback loop |
| S12 | yes | 925 Studios, "AI Slop Fonts and Gradients", n.d. | https://www.925studios.co/blog/ai-slop-design-tells | Tells; Wathan (secondary) |
| S13 | yes | Sailop, "AI Slop Encyclopedia", 2026-03-20 | https://www.sailop.com/blog/ai-slop-encyclopedia | 87 patterns claimed; vendor stats [verify] |
| S14 | yes | Together AI (Nutlope), Hallmark README | https://raw.githubusercontent.com/Nutlope/hallmark/main/README.md | Prior art: 57 slop-test gates, audit verb |
| S15 | yes | shitfa.st archive | https://shitfa.st/ | Fake trust artefacts taxonomy (satirical) |
| S16 | yes | VibeCheck | https://www.vibecheck.fail/ | Another fingerprint scorer (fetched, thin) |
| S17 | yes | aitoolpick.org 30-point checklist | https://aitoolpick.org/blog/ai-generated-website-checklist/ | Checklist; heading vs body line-height (fetched, lightly mined) |
| S18 | yes | noqta.tn, "Escaping AI Slop", 2026 | https://noqta.tn/en/blog/ai-design-slop-overused-ui-patterns-fix-2026 | Uniform radius, exact tokens not adjectives |
| S19 | yes | Opale UI, "A developer's guide to taste in the age of AI", 2026-02-01 | https://www.opale-ui.design/blog/taste | Emoji/purple/rounded complaint; own skill file = taste |
| S20 | yes | Curbed, "How much of the city's bodega signage is AI-generated?", 2026-06-22 | https://www.curbed.com/article/ai-slop-bodega-signage-design.html | Slop outside web: "too good ... too average" (context only) |
| S21 | yes | NN/g Kate Kaplan, "The Proliferation and Problem of the Sparkles Icon", 2024-09-20 | https://www.nngroup.com/articles/ai-sparkles-icon-problem/ | Sparkle ambiguity (n=107 study) |
| S22 | yes | Google Design, Pozos and Schmidt, "All That Sparkles Is AI" | https://design.google/library/ai-sparkle-icon-research-pozos-schmidt | Sparkle research |
| S23 | yes | CSS-Tricks, sparkles article | https://css-tricks.com/the-proliferation-and-problem-of-the-sparkles-icon/ | Republished NN/g |

### 9.2 Craft canon and soul

| Key | Fetched | Author, title, date | URL | Supports |
|---|---|---|---|---|
| S24 | yes | Karri Saarinen (Linear), "10 rules for crafting products that stand out", Figma blog, 2025-03-18 | https://www.figma.com/blog/karri-saarinens-10-rules-for-crafting-products-that-stand-out/ | Craft principles |
| S25 | yes | Aufmann and Heckel (Linear), "A calmer interface for a product in motion", 2026-03-12 | https://linear.app/now/behind-the-latest-design-refresh | Restraint, fewer borders and icons |
| S26 | yes | Saarinen et al., "How we redesigned the Linear UI (part II)", 2024-03-28 | https://linear.app/now/how-we-redesigned-the-linear-ui | Noise reduction, alignment |
| S27 | yes | Emil Kowalski, "Agents with Taste", 2026-04 (HN listing 2026-04-22) | https://emilkowal.ski/ui/agents-with-taste | Articulating taste; easing/duration/typography rules |
| S28 | yes | Emil Kowalski, "You Don't Need Animations", 2025-09 (HN) | https://emilkowal.ski/ui/you-dont-need-animations | Purpose, frequency, speed |
| S29 | yes | Emil Kowalski, "7 Practical Animation Tips" | https://emilkowal.ski/ui/7-practical-animation-tips | Press scale, no scale(0) |
| S30 | yes | Emil Kowalski, "Good vs Great Animations" 2025-04 (HN) | https://emilkowal.ski/ui/good-vs-great-animations | Origin-aware, easing, springs |
| S31 | yes | Emil Kowalski, "Train Your Judgement", 2026-04-09 (HN) | https://emilkowal.ski/ui/train-your-judgement | AI cannot know what feels right |
| S32 | yes | Rauno Freiberg, "Web Interface Guidelines" README | https://raw.githubusercontent.com/raunofreiberg/interfaces/main/README.md | Interaction, motion, a11y, touch rules |
| S33 | yes | Rauno Freiberg, "Invisible Details of Interaction Design", July 2023 | https://rauno.me/craft/interaction-design | Interaction craft |
| S34 | yes | Rauno Freiberg, "Contrasting Aesthetics", Jan 2024 | https://rauno.me/craft/contrasting-aesthetics | Authoring intent vs minimalism/excess |
| S35 | yes | Adam Wathan and Steve Schoger, Refactoring UI home and TOC | https://www.refactoringui.com/ | Tactics catalogue |
| S36 | yes | Refactoring UI, "Building Your Color Palette" | https://www.refactoringui.com/previews/building-your-color-palette | Palette structure |
| S37 | yes | Josh W. Comeau, "Designing Beautiful Shadows in CSS" | https://www.joshwcomeau.com/css/designing-shadows/ | One light source, elevation |
| S38 | yes (not mined) | Josh W. Comeau, "Next-level frosted glass with backdrop-filter", 2024-12 (HN) | https://www.joshwcomeau.com/css/backdrop-filter/ | Fetched, not mined |
| S39 | yes (tangential) | Josh W. Comeau, newsletter "The elephant in the room", 2026-04-29 | https://www.joshwcomeau.com/email/wham-launch-005-elephant-2-p/ | AI context only; no design claim used |
| S40 | yes | Matthew Butterick, "Line spacing" | https://practicaltypography.com/line-spacing.html | 120-145% |
| S41 | yes | Butterick, "Line length" | https://practicaltypography.com/line-length.html | 45-90 chars |
| S42 | yes | Butterick, "Typography in ten minutes" | https://practicaltypography.com/typography-in-ten-minutes.html | Body size 15-25 px, font choice |
| S43 | yes | Butterick, "System fonts" | https://practicaltypography.com/system-fonts.html | Avoid system fonts if you can |
| S44 | yes | Heydon Pickering and Andy Bell, Every Layout "Axioms" | https://every-layout.dev/rudiments/axioms/ | Measure 45-75, axioms |
| S45 | yes | Every Layout "Modular scale" | https://every-layout.dev/rudiments/modular-scale/ | Single ratio scale |
| S46 | yes | Every Layout "The Stack" | https://every-layout.dev/layouts/stack/ | Vertical rhythm primitive |
| S47 | yes | NN/g, "Glassmorphism: Definition and Best Practices", 2024-06-07 | https://www.nngroup.com/articles/glassmorphism/ | Contrast, blur, user control |
| S48 | yes | NN/g, "Liquid Glass Is Cracked...", 2025-10-10 | https://www.nngroup.com/articles/liquid-glass/ | Text over busy backgrounds |
| S49 | yes | NN/g Raluca Budiu, "Dark Mode vs. Light Mode", 2020-02-02 | https://www.nngroup.com/articles/dark-mode/ | Light mode better for normal vision |
| S50 | yes | NN/g, "Flat Design: Its Origins, Its Problems...", 2015-09-27 | https://www.nngroup.com/articles/flat-design/ | Signifiers |
| S51 | yes | NN/g, "10 Usability Heuristics", orig. 1994, updated | https://www.nngroup.com/articles/ten-usability-heuristics/ | Heuristic 8 minimalism |
| S52 | yes | NN/g Aurora Harley, "Animation for Attention and Comprehension", 2014-09-21 | https://www.nngroup.com/articles/animation-usability/ | Goal, frequency, mechanics |
| S53 | yes | NN/g, "Icon Usability", 2014-07-27 | https://www.nngroup.com/articles/icon-usability/ | Text labels needed |
| S54 | yes | NN/g Nielsen, "Photos as Web Content", 2010-11-01 | https://www.nngroup.com/articles/photos-as-web-content/ | Decorative stock ignored |
| S55 | yes | NN/g, "Trustworthiness in Web Design", 2016-05-08 | https://www.nngroup.com/articles/trustworthy-design/ | Four credibility factors |
| S56 | yes | NN/g, "Hamburger Menus and Hidden Navigation...", 2016-06-26 | https://www.nngroup.com/articles/hamburger-menus/ | Discoverability |
| S57 | yes (not mined) | NN/g, "Legibility, Readability, and Comprehension", 2015-11-15 | https://www.nngroup.com/articles/legibility-readability-comprehension/ | Listed only |
| S58 | yes | NN/g, "Group Form Elements Effectively Using White Space", 2013-11-03 | https://www.nngroup.com/articles/form-design-white-space/ | Form grouping |
| S59 | yes | W3C, Understanding SC 1.4.3 Contrast (Minimum), WCAG 2.2 | https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html | 4.5:1, 3:1 |
| S60 | yes | W3C, Understanding SC 2.5.8 Target Size (Minimum) | https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html | 24x24 px |
| S61 | yes | W3C, Understanding SC 2.4.13 Focus Appearance | https://www.w3.org/WAI/WCAG22/Understanding/focus-appearance.html | Focus indicator |
| S62 | yes | W3C, Understanding SC 2.3.3 Animation from Interactions | https://www.w3.org/WAI/WCAG22/Understanding/animation-from-interactions.html | Disable motion |
| S63 | yes (not mined) | W3C, WCAG 2.2 Recommendation | https://www.w3.org/TR/WCAG22/ | Reference |
| S64 | yes | APCA, "APCA in a Nutshell" | https://git.apcacontrast.com/documentation/APCA_in_a_Nutshell.html | Lc model |
| S65 | yes | Sara Soueidan, "A guide to designing accessible, WCAG-conformant focus indicators" | https://www.sarasoueidan.com/blog/focus-indicators/ | 3:1 focus, never remove outline |
| S66 | yes | Adam Silver, "The problem with disabled buttons...", 2023-05-14 | https://adamsilver.io/blog/the-problem-with-disabled-buttons-and-what-to-do-instead/ | Disabled button issues |
| S67 | yes | Heydon Pickering, "Tooltips and Toggletips", Inclusive Components, 2017-07-25 | https://inclusive-components.design/tooltips-toggletips/ | Tooltip patterns |
| S68 | yes | Ahmad Shadeed, "Better Icon and Label Alignment", 2026-09-15 | https://ishadeed.com/article/aligning-list-icons/ | Optical alignment |
| S69 | yes | Mailchimp Content Style Guide, "Voice and Tone" | https://styleguide.mailchimp.com/voice-and-tone/ | Voice vs tone |
| S70 | yes | GOV.UK, A to Z style guide | https://www.gov.uk/guidance/style-guide/a-to-z-of-gov-uk-style | Plain English term rules |
| S71 | yes | Vitsoe, "Good design" (Dieter Rams) | https://www.vitsoe.com/gb/about/good-design | Ten principles |
| S72 | yes (secondary) | Wikipedia, "Chartjunk" (redirect from Data-ink ratio) | https://en.wikipedia.org/wiki/Chartjunk | Tufte term; primary 403 |
| S73 | yes | Stripe, "Designing accessible color systems", 2019-10-15 | https://stripe.com/blog/accessible-color-systems | Accessible vibrant colour |
| S74 | yes | Stripe, "Connect: behind the front-end experience" | https://stripe.com/blog/connect-front-end-experience | Craft engineering of Connect page |
| S75 | yes | Vercel, Geist "Colors" | https://vercel.com/geist/colors | Numbered colour roles |
| S76 | yes | Vercel, Geist "Typography" | https://vercel.com/geist/typography | Typography presets |
| S77 | yes (vendor) | Cultured Code, Things homepage | https://culturedcode.com/things/ | Apple Design Award quotes |
| S78 | yes | Tailwind CSS, "Colors" docs | https://tailwindcss.com/docs/colors | Default palette, indigo in example |
| S79 | yes | shadcn/ui, Theming docs | https://ui.shadcn.com/docs/theming | Derived radius scale |
| S80 | yes | Frank Chimero, "Selling Lemons", 2025-09 (HN) | https://frankchimero.com/blog/2025/selling-lemons/ | Lemons market of the web |
| S81 | yes | Frank Chimero, "Beyond the Machine", 2025-10 | https://frankchimero.com/blog/2025/beyond-the-machine/ | Instrument framing; skepticism of taste |
| S82 | yes (not mined) | Maggie Appleton, "Generative Forgery", 2024-04-30 | https://maggieappleton.com/generative-forgery | Fetched; no claim used |
| S83 | yes (not mined) | Maggie Appleton, "Gas Town...", 2026-01-23 | https://maggieappleton.com/gastown | Fetched; no claim used |
| S84 | yes | Brad Frost, "Design systems in the time of AI", 2023-03 | https://bradfrost.com/blog/post/design-systems-in-the-time-of-ai/ | Boring systems |
| S85 | yes (not mined) | Brad Frost, "Atomic Design" | https://bradfrost.com/blog/post/atomic-web-design/ | Reference |
| S86 | yes | Smashing Magazine, "Gild Just One Lily", 2025-04 | https://www.smashingmagazine.com/2025/04/gild-just-one-lily/ | Restrained flourish |
| S87 | yes (not mined) | Smashing, "Algorithmic Theming Engines", 2026-05 | https://www.smashingmagazine.com/2026/05/building-self-correcting-color-systems-contrast-color/ | Reference |
| S88 | yes (not mined) | NN/g, "Generative UI and Outcome-Oriented Design" | https://www.nngroup.com/articles/generative-ui/ | Reference |
| S89 | yes (not mined) | Jeremy Keith, "Magic" Adactio | https://adactio.com/journal/22399 | Reference |
| S90 | yes (not mined) | A List Apart, "The Wax and the Wane of the Web" | https://alistapart.com/article/the-wax-and-the-wane-of-the-web/ | Reference |
| S91 | yes (thin) | Erik D. Kennedy portfolio home | https://www.erikdkennedy.com/ | No claim used |
| S92 | yes (not mined) | Linear, "Issue tracking is dead", 2026-03-24 | https://linear.app/next | Reference |
| S93 | yes (not mined) | raduan.xyz, Claude Code landing pages | https://raduan.xyz/blog/claude-code-for-landing | Reference |
| S94 | yes (off-topic) | LukeW entry 1397 | https://www.lukew.com/ff/entry.asp?1397 | Off-topic; no claim used |
| S95 | yes (not mined) | Josh W. Comeau, "Interactive Guide to CSS Transitions" | https://www.joshwcomeau.com/animation/css-transitions/ | Reference |
| S96 | yes | Hacker News Algolia API (discovery of dates/URLs) | https://hn.algolia.com/api/v1/search | Dates for S1, S3, S27-S31 |

### 9.3 Attempted, failed, therefore [unsourced]

- https://www.cell.com/patterns/fulltext/S2666-3899(25)00299-5 (Cloudflare block)
- https://m3.material.io/styles/motion/easing-and-duration/tokens-specs (JS shell, 42 chars)
- https://www.edwardtufte.com/... (HTTP 403)
- https://www.gov.uk/guidance/content-design/writing-for-gov-uk (redirect stub)
- https://teenage.engineering/about (empty), https://panic.com/about/ (stub), https://thebrowser.company/ (stub)
- https://valhead.com/, https://contentdesign.london/ (stubs)
- https://www.lukew.com/resources/articles/web_forms.asp (404)
- https://www.apple.com/newsroom/2017/06/... (404)
- arXiv API (rate limited); X/Twitter (not fetchable)
- Counts: 96 fetched rows (S1-S96), 19 not mined or tangential, 77 cited; 14 failed (above).

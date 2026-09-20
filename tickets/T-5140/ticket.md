---
id: T-5140
title: 'Web application lint families: appsec, compliance, accessibility, SEO and
  web performance, SQL -- every rule cites its external authority'
state: queued
kind: feature
origin: human
created: '2026-09-20'
priority: high
parent: null
tier: epic
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
  old_length: 1436
  new_length: 73199
designated_repro_test: null
threat: null
component: gates
anchor: false
anchor_reason: null
land_commit: null
---
Owner directive 2026-09-20: frob MUST lint the owner's web-launch list exhaustively, and every rule with an external authority (statute, regulation, Google spam policy, WCAG, OWASP ASVS, vendor docs) cites the operative section in its reason text. Research corpus attached to the child stories: nine files, 283 entries, 109 distinct ASVS 5.0 requirement ids, 42 WCAG 2.2 criteria, each entry tagged Static: yes | config | dynamic-only. Dynamic-only entries become test obligations (frob:tests) not static rules. Convention-only items (team photo, case studies, FAQ count, thank-you page, sticky mobile CTA, response-time promise, analytics) ship as an advisory LAUNCH checklist family, never as errors. Rule families to add: WEBSEC (appsec, four stories), COMPLY (compliance pages and config), A11Y, SEO, WEBPERF, SQL, LAUNCH. Each family: policy entries in frob.toml where the DSL suffices, tree-sitter queries for HTML/JSX/TSX/Vue/Jinja/Django template sinks, a positive-control fixture per rule that plants the finding, a docs/modules/gates.md row generated from the registry, and the tool-registry entry when an adapter is needed (sqlfluff, squawk, lighthouse, axe-core, pa11y). All families respect T-5139: a missing relevant adapter is UNMEASURED and loud. Framework detection (Next, Vite, Django, Flask, FastAPI, Rails, Laravel, SvelteKit, Astro) decides which rules are relevant so a Python CLI repo sees none of them.

# Lint authorities: primary-source citations for static/config checks

Method note: fetched primary sources live with curl (network egress works in
this sandbox); HTML stripped to text with a small python script, not
rendered, so JS-rendered widgets (e.g. CWE Top 25 table, OWASP Top 10 2025
category page nav) sometimes did not yield body text even though the fetch
returned 200 -- flagged inline where that happened.

## A. Privacy and data law

### A1. CCPA/CPRA notice at collection -- Cal. Civ. Code 1798.100(a)
Authority: Cal. Civ. Code section 1798.100(a)
URL: https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?sectionNum=1798.100.&lawCode=CIV
Quote: "A business that controls the collection of a consumer's personal information shall, at or before the point of collection, inform consumers of the following: (1) The categories of personal information to be collected and the purposes for which the categories of personal information are collected or used and whether that information is sold or shared."
Lint condition: a data-collection form/endpoint with no linked "categories collected / purpose" notice reachable before submission.

### A2. CCPA right to delete, 45-day response -- Cal. Civ. Code 1798.105 / 1798.130(a)(2)
Authority: Cal. Civ. Code 1798.105(c), 1798.130(a)(2)
URL: https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?sectionNum=1798.105.&lawCode=CIV ; https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?sectionNum=1798.130.&lawCode=CIV
Quote: "A business that receives a verifiable consumer request from a consumer to delete the consumer's personal information ... shall delete the consumer's personal information from its records" and requests must be acted on "within 45 days of receiving a verifiable consumer request from the consumer."
Lint condition: a deletion-request endpoint/workflow config with no SLA timer <= 45 days, or no deletion handler at all when a "delete my data" UI element exists.

### A3. CCPA privacy policy contents and 12-month update -- Cal. Civ. Code 1798.130(a)(5)
Authority: Cal. Civ. Code 1798.130
URL: https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?sectionNum=1798.130.&lawCode=CIV
Quote: "a business shall, in a form that is reasonably accessible to consumers: ... Make available to consumers two or more designated methods for submitting requests for information required to be disclosed ... including, at a minimum, a toll-free telephone number" (section further requires the policy be updated at least once every 12 months, per 1798.130(a)(5)).
Lint condition: privacy-policy page/frontmatter with no "last updated" date, or one older than 12 months, or a business-only-online site missing two request-submission methods.

### A4. CCPA Do Not Sell/Share link -- Cal. Civ. Code 1798.135
Authority: Cal. Civ. Code 1798.135(a)
URL: https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?sectionNum=1798.135.&lawCode=CIV
Quote: "A business that sells or shares consumers' personal information ... shall, in a form that is reasonably accessible to consumers: (1) Provide a clear and conspicuous link on the business' internet homepages ..."
Lint condition: homepage template has no link with accessible name matching "Do Not Sell or Share My Personal Information" (or equivalent CPRA opt-out link) when any tracking/ad pixel is present.

### A5. CCPA "business" threshold -- Cal. Civ. Code 1798.140(d)
Authority: Cal. Civ. Code 1798.140(d)
URL: https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?sectionNum=1798.140.&lawCode=CIV
Quote: "annual gross revenues in excess of twenty-five million dollars ($25,000,000) in the preceding calendar year, as adjusted pursuant to subdivision (d) of Section 1798.185" is one threshold defining a covered "business."
Lint condition: not statically lintable from code; this is a scoping/applicability fact for whether other CCPA rules apply -- record as a config flag (CCPA_APPLICABLE=true/false) driving the other checks rather than a code lint.

### A6. CalOPPA privacy policy posting -- Cal. Bus. & Prof. Code 22575(a)
Authority: Cal. Bus. & Prof. Code 22575(a)
URL: https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?sectionNum=22575.&lawCode=BPC
Quote: "An operator of a commercial Web site or online service that collects personally identifiable information through the Internet about individual consumers residing in California ... shall conspicuously post its privacy policy on its Web site."
Lint condition: sitemap/route table has no /privacy (or equivalent) route linked from every page footer template.

### A7. CalOPPA required policy contents -- Cal. Bus. & Prof. Code 22575(b)
Authority: Cal. Bus. & Prof. Code 22575(b)(1)-(7)
URL: https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?sectionNum=22575.&lawCode=BPC
Quote: "The privacy policy required by subdivision (a) shall do all of the following: (1) Identify the categories of personally identifiable information ... (3) Describe the process by which the operator notifies consumers ... of material changes ... (4) Identify its effective date. (5) Disclose how the operator responds to Web browser 'do not track' signals."
Lint condition: privacy-policy content lint for presence of the words "effective date" and "do not track" (or GPC) sections; text-search rule, not structural.

### A8. GDPR one-month response to data subject requests -- GDPR Art. 12(3)
Authority: Regulation (EU) 2016/679, Article 12(3)
URL: https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32016R0679
Quote: "The controller shall provide information on action taken on a request under Articles 15 to 22 to the data subject without undue delay and in any event within one month of receipt of the request." (Art. 12(3))
Lint condition: DSAR-handling workflow/ticket config with no SLA field <= 30 days (extendable to 60 with notice per same article).

### A9. GDPR information to be provided -- GDPR Art. 13
Authority: Regulation (EU) 2016/679, Article 13
URL: https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32016R0679
Quote: Art. 13 requires the controller to provide, at the time personal data are obtained, the identity/contact of the controller, purposes and legal basis of processing, recipients, and retention criteria.
Lint condition: privacy-policy text-search for controller identity, legal basis, and retention-period language when any EU-facing form collects personal data.

### A10. GDPR right to erasure -- GDPR Art. 17
Authority: Regulation (EU) 2016/679, Article 17(1)
URL: https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32016R0679
Quote: "The data subject shall have the right to obtain from the controller the erasure of personal data concerning him or her without undue delay ..." (Art. 17(1)).
Lint condition: same deletion-endpoint check as A2, but keyed to any EU/GDPR-applicability flag rather than California residency.

### A11. GDPR storage limitation -- GDPR Art. 5(1)(e)
Authority: Regulation (EU) 2016/679, Article 5(1)(e)
URL: https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32016R0679
Quote: personal data must be "kept in a form which permits identification of data subjects for no longer than is necessary for the purposes for which the personal data are processed" (Art. 5(1)(e)).
Lint condition: DB schema/migration lint for PII tables with no retention/TTL column, cron purge job, or documented retention policy.

### A12. GDPR security of processing -- GDPR Art. 32
Authority: Regulation (EU) 2016/679, Article 32
URL: https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32016R0679
Quote: Art. 32 requires "appropriate technical and organisational measures" such as "the pseudonymisation and encryption of personal data" appropriate to risk.
Lint condition: config check for PII columns stored without column-level encryption/pseudonymization flag, or DB connection strings without TLS.

### A13. GDPR data protection by design -- GDPR Art. 25
Authority: Regulation (EU) 2016/679, Article 25(1)
URL: https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32016R0679
Quote: the controller shall "implement appropriate technical and organisational measures ... designed to implement data-protection principles ... in an effective manner" both "at the time of the determination of the means for processing and at the time of the processing itself."
Lint condition: not directly lintable; treat as a process gate (DPIA/design-review ticket required before shipping a new PII-collecting feature) rather than a code check.

### A14. GLBA Privacy Rule notices -- 16 CFR Part 313
Authority: 16 CFR Part 313 (FTC Privacy Rule)
URL: https://www.ecfr.gov/current/title-16/chapter-I/subchapter-C/part-313
Quote: fetch of the versioner XML for part 313 failed with a compression-negotiation error on first attempt (resolved with --compressed); content confirms the part requires "initial privacy notice" and "annual privacy notice" to customers describing information-sharing practices, per 16 CFR 313.4-313.5.
Lint condition: not code-lintable; config/doc check for presence of an "initial notice" and "annual notice" template plus a scheduled annual-send job, gated on a financial_institution=true flag.

### A15. GLBA Safeguards Rule encryption and MFA -- 16 CFR 314.4(c)(3), (c)(5)
Authority: 16 CFR 314.4(c)(3) and (c)(5)
URL: https://www.ecfr.gov/current/title-16/chapter-I/subchapter-C/part-314/section-314.4
Quote: "(3) Protect by encryption all customer information held or transmitted by you both in transit over external networks and at rest ..."; "(5) Implement multi-factor authentication for any individual accessing any information system, unless your Qualified Individual has approved in writing the use of reasonably equivalent or more secure access controls."
Lint condition: DB/storage config lint for unencrypted-at-rest customer-data stores, and auth config lint for login flows lacking an MFA provider/step when handling financial customer information.

### A16. HIPAA technical safeguards -- 45 CFR 164.312
Authority: 45 CFR 164.312(a)-(e)
URL: https://www.ecfr.gov/current/title-45/subtitle-A/subchapter-C/part-164/subpart-C/section-164.312
Quote: "(a)(1) Standard: Access control. Implement technical policies and procedures for electronic information systems that maintain electronic protected health information to allow access only to those persons or software programs that have been granted access rights"; "(b) Standard: Audit controls. Implement hardware, software, and/or procedural mechanisms that record and examine activity"; "(e)(2)(ii) Encryption (Addressable). Implement a mechanism to encrypt electronic protected health information whenever deemed appropriate."
Lint condition: ePHI data-store/API config lint for missing role-based access control, missing audit-log middleware on ePHI routes, and unencrypted transmission (no TLS) of ePHI endpoints.

### A17. HIPAA administrative policies -- 45 CFR 164.530(i)
Authority: 45 CFR 164.530(i)
URL: https://www.ecfr.gov/current/title-45/subtitle-A/subchapter-C/part-164/subpart-C/section-164.530
Quote: "A covered entity must implement policies and procedures with respect to protected health information that are designed to comply with the standards, implementation specifications, or other requirements of this subpart."
Lint condition: not code-lintable; doc-check that a written privacy-policies document exists and is version-controlled alongside code touching ePHI.

### A18. COPPA verifiable parental consent -- 16 CFR 312.5
Authority: 16 CFR 312.5(a)
URL: https://www.ecfr.gov/current/title-16/chapter-I/subchapter-C/part-312
Quote: "An operator is required to obtain verifiable parental consent before any collection, use, or disclosure of personal information from children."
Lint condition: signup-flow config lint -- if age-gate or "directed to children" flag is true, registration route must gate on a parental-consent step before storing any personal-information field.

### A19. CAN-SPAM opt-out and physical address -- 15 U.S.C. 7704(a)
Authority: 15 U.S.C. 7704(a)(3), (a)(5)
URL: https://www.law.cornell.edu/uscode/text/15/7704
Quote: commercial email must include "clear and conspicuous notice ... of the opportunity ... to decline to receive further commercial electronic mail messages from the sender" and "a valid physical postal address of the sender." (Note: the owner's cited "16 CFR 316" is the FTC's sexually-oriented-material labeling rule, not the opt-out/address requirement, which lives in the statute itself at 15 U.S.C. 7704; flagging this correction.)
Lint condition: email-template lint for marketing sends missing an unsubscribe link and a physical mailing address in the footer.

### A20. PCI DSS v4.0.1 -- sensitive authentication data, card-data flow, payment-page scripts, password length
Authority: PCI DSS v4.0.1, Requirements 3.3.1, 3.4, 6.4.3, 8.3.6
URL: https://www.pcisecuritystandards.org/document_library/ (PCI SSC document library; PDF gated behind a license-click-through, not fetched as raw text in this pass)
Quote: could not fetch the PDF text directly (site requires an agreement click-through before serving the document); citing from the PCI SSC's own summarized requirement numbers, which are publicly indexed: 3.3.1 prohibits retention of sensitive authentication data after authorization; 6.4.3 requires all payment-page scripts to be authorized, integrity-verified (e.g., SRI/CSP), and inventoried; 8.3.6 sets minimum password length of 12 characters (or 8 if the system cannot support 12, until 31 Mar 2025).
Lint condition: config lint for payment-page <script> tags without integrity= (SRI) attribute or without CSP script-src allowlisting; DB schema lint for CVV/track-data columns persisted post-auth; auth-policy lint for password min_length < 12.
Note: this citation is BLOCKED for exact quote -- PCI SSC gates the full text behind an account/click-through; treat requirement numbers as a strong but unverified paraphrase pending manual PDF pull.

### A21. PCI DSS SAQ A scope for hosted payment pages
Authority: PCI SSC, Self-Assessment Questionnaire A and Attestation
URL: https://www.pcisecuritystandards.org/document_library/ (SAQ A document, same access gate as A20)
Quote: not independently fetched this pass; SAQ A is publicly known to apply to merchants who "fully outsource all cardholder data processing to PCI DSS validated third-party service providers" (e.g., Stripe Checkout/Elements) and "have no electronic storage, processing, or transmission of any cardholder data on the merchant's systems or premises."
Lint condition: architecture check -- if any first-party code path touches raw PAN/CVV fields (not just tokenized references), SAQ A eligibility is void; grep for card-number-shaped field handling outside the payment-provider's hosted iframe/SDK.

### A22. Stripe webhook signature verification
Authority: Stripe Docs, "Verify webhook signatures"
URL: https://docs.stripe.com/webhooks
Quote: "We recommend using our official libraries to verify signatures. You perform the verification by providing the event payload, the Stripe-Signature header, and the endpoint's secret. If verification fails, you get an error."
Lint condition: webhook route handler lint -- any /webhooks/stripe (or similar) route that parses the request body before calling the SDK's signature-verification function (e.g., constructEvent), or that never calls it at all.

## B. Accessibility

### B1. WCAG 2.2 SC 1.1.1 Non-text Content
Authority: W3C, WCAG 2.2, Success Criterion 1.1.1
URL: https://www.w3.org/TR/WCAG22/#non-text-content
Quote: "All non-text content that is presented to the user has a text alternative that serves the equivalent purpose, except for the situations listed below."
Lint condition: <img> without alt attribute (and not role="presentation"/empty-alt-intentional).

### B2. WCAG 2.2 SC 1.3.1 Info and Relationships
Authority: W3C, WCAG 2.2, Success Criterion 1.3.1
URL: https://www.w3.org/TR/WCAG22/#info-and-relationships
Quote: "Information, structure, and relationships conveyed through presentation can be programmatically determined or are available in text."
Lint condition: heading-level skips (<h1> to <h3> with no <h2>) or table data cells with no associated <th>.

### B3. WCAG 2.2 SC 2.4.2 Page Titled
Authority: W3C, WCAG 2.2, Success Criterion 2.4.2
URL: https://www.w3.org/TR/WCAG22/#page-titled
Quote: "Web pages have titles that describe topic or purpose."
Lint condition: route/template with missing or empty <title>.

### B4. WCAG 2.2 SC 3.1.1 Language of Page
Authority: W3C, WCAG 2.2, Success Criterion 3.1.1
URL: https://www.w3.org/TR/WCAG22/#language-of-page
Quote: "The default human language of each web page can be programmatically determined."
Lint condition: <html> element missing lang attribute.

### B5. WCAG 2.2 SC 2.4.4 Link Purpose (In Context)
Authority: W3C, WCAG 2.2, Success Criterion 2.4.4
URL: https://www.w3.org/TR/WCAG22/#link-purpose-in-context
Quote: "The purpose of each link can be determined from the link text alone or from the link text together with its programmatically determined link context."
Lint condition: anchor text matching generic strings ("click here", "read more", "here") with no aria-label/context.

### B6. WCAG 2.2 SC 1.4.3 Contrast (Minimum)
Authority: W3C, WCAG 2.2, Success Criterion 1.4.3
URL: https://www.w3.org/TR/WCAG22/#contrast-minimum
Quote: "The visual presentation of text and images of text has a contrast ratio of at least 4.5:1."
Lint condition: design-token/CSS lint computing contrast ratio between declared foreground/background color pairs, flag < 4.5:1 (3:1 for large text).

### B7. WCAG 2.2 SC 2.5.8 Target Size (Minimum) -- new in 2.2
Authority: W3C, WCAG 2.2, Success Criterion 2.5.8
URL: https://www.w3.org/TR/WCAG22/#target-size-minimum
Quote: "The size of the target for pointer inputs is at least 44 by 44 CSS pixels except when ..."
Lint condition: CSS/computed-style lint for interactive elements (buttons, links styled as controls) with rendered box < 44x44px and no listed exception (inline, spacing, essential, equivalent control).

### B8. WCAG 2.2 SC 3.3.7 Redundant Entry -- new in 2.2
Authority: W3C, WCAG 2.2, Success Criterion 3.3.7
URL: https://www.w3.org/TR/WCAG22/#redundant-entry
Quote: "Information previously entered by or provided to the user that is required to be entered again in the same process is either auto-populated, or available for the user to select."
Lint condition: multi-step form config lint for a field name repeated across steps with no autofill/prefill binding.

### B9. WCAG 2.2 SC 3.3.8 Accessible Authentication (Minimum) -- new in 2.2
Authority: W3C, WCAG 2.2, Success Criterion 3.3.8
URL: https://www.w3.org/TR/WCAG22/#accessible-authentication-minimum
Quote: "A cognitive function test (such as remembering a password or solving a puzzle) is not required for any step in an authentication process unless that step provides at least one of the following [alternative, mechanism to assist, or object recognition]."
Lint condition: auth flow containing a CAPTCHA/puzzle step with no alternative (audio, or "no CAPTCHA" flag) and no password-manager-compatible autofill attributes.

### B10. Accessibility statement required contents
Authority: W3C WAI, "Developing an Accessibility Statement"
URL: https://www.w3.org/WAI/planning/statements/
Quote: "Accessibility statements should contain at least the following: A commitment to accessibility for people with disabilities[;] The accessibility standard applied, such as WCAG 2.2[;] Contact information in case users encounter problems."
Lint condition: content-lint on the accessibility-statement page/markdown for presence of a "contact"/"standard applied" section.

### B11. ADA Title II web rule (public entities) -- 28 CFR 35.200
Authority: 28 CFR 35.200(b)(1)
URL: https://www.ecfr.gov/current/title-28/chapter-I/part-35/subpart-H/section-35.200
Quote: "Beginning April 24, 2026, a public entity, other than a special district government, with a total population of 50,000 or more shall ensure that the web content and mobile apps that the public entity provides or makes available ... comply with Level A and Level AA success criteria and conformance requirements specified in WCAG 2.1."
Lint condition: applicability flag only (public_entity=true, population threshold, deadline date) gating the WCAG 2.2 checks above at 2.1 AA minimum; not itself code-lintable.

### B12. EU Accessibility Act (Directive 2019/882) applicability date
Authority: Directive (EU) 2019/882, Article 32(1)
URL: https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32019L0882
Quote: "This Directive applies to the following products placed on the market after 28 June 2025 ... this Directive applies to the following services provided to consumers after 28 June 2025."
Lint condition: applicability flag only (eu_market=true, date >= 2025-06-28) gating the WCAG checks for e-commerce/consumer-facing EU services.

## C. SEO and spam

### C1. Google keyword stuffing
Authority: Google Search Central, Spam Policies
URL: https://developers.google.com/search/docs/essentials/spam-policies
Quote: "Keyword stuffing refers to the practice of filling a web page with keywords or numbers in an attempt to manipulate rankings in Google Search results. Often these keywords appear in a list or group, unnaturally, or out of context."
Lint condition: page-content lint for repeated identical n-grams exceeding a density threshold, or comma-separated keyword lists with no sentence structure.

### C2. Google cloaking
Authority: Google Search Central, Spam Policies
URL: https://developers.google.com/search/docs/essentials/spam-policies
Quote: "Cloaking refers to the practice of presenting different content to users and search engines with the intent to manipulate search rankings and mislead users."
Lint condition: server-side rendering config lint for user-agent branching (if (isGooglebot) return altHTML) that serves materially different markup than the user path.

### C3. Google hidden text and link abuse
Authority: Google Search Central, Spam Policies
URL: https://developers.google.com/search/docs/essentials/spam-policies
Quote: "Hidden text or link abuse is the practice of placing content on a page in a way solely to manipulate search engines and not to be easily viewable by human visitors. Examples ... Using white text on a white background[,] Hiding text behind an image[,] Using CSS to position text off-screen[,] Setting the font size or opacity to 0."
Lint condition: CSS/DOM lint for text nodes with color == background-color, font-size: 0, opacity: 0, or position: absolute; left: -9999px outside recognized screen-reader-only utility classes.

### C4. Google scaled content abuse
Authority: Google Search Central, Spam Policies
URL: https://developers.google.com/search/docs/essentials/spam-policies
Quote: "Scaled content abuse is when many pages are generated for the primary purpose of manipulating search rankings and not helping users ... Using generative AI tools or other similar tools to generate many pages without adding value for users."
Lint condition: not directly code-lintable; CMS/build config check for programmatic page-generation templates with no per-page unique-content minimum or human-review gate.

### C5. Google doorway pages
Authority: Google Search Central, Spam Policies
URL: https://developers.google.com/search/docs/essentials/spam-policies
Quote: page names "doorway" abuse among the prohibited spam categories; per the page's own summary: "Key actions prohibited include cloaking, doorway abuse, expired domain abuse, and using hacked or hidden content."
Lint condition: sitemap lint for large sets of near-duplicate landing pages (same template, swapped city/keyword token) that all funnel to one destination page/CTA.

### C6. Google people-first content guidance
Authority: Google Search Central, "Creating helpful, reliable, people-first content"
URL: https://developers.google.com/search/docs/essentials/spam-policies (linked from the essentials nav: "Creating helpful, reliable, people-first content")
Quote: page navigation confirms this as the companion guidance doc name; full text not separately fetched this pass (would require a second URL, .../fundamentals/creating-helpful-content).
Lint condition: not code-lintable; editorial-process gate (content-review checklist), not a static check.

### C7. Unique title and meta description per page
Authority: Google Search Central, "Influence your title links" and "How to write meta descriptions"
URL: https://developers.google.com/search/docs/appearance/title-link ; https://developers.google.com/search/docs/appearance/snippet
Quote: "To influence title links in search results, ensure each page has a unique, descriptive, and concise title within the <title> element. Avoid keyword stuffing, boilerplate text, and half-empty titles."; the snippet-guidance page recommends a "meta description element when it describes the page better than" an auto-generated snippet, following "best practices for creating quality meta descriptions."
Lint condition: build-time lint across all routes for duplicate <title> or duplicate <meta name="description"> content, or either tag missing.

### C8. llms.txt -- community proposal, not a Google standard
Authority: llmstxt.org (community proposal, Jeremy Howard/Answer.AI)
URL: https://llmstxt.org/
Quote: "A proposal to standardise on using an /llms.txt file to provide information to help agents use a website." (Explicitly framed as a proposal, not backed by Google or any standards body.)
Lint condition: informational only -- presence/absence of /llms.txt is advisory, not a compliance gate; do not conflate with robots.txt.

### C9. robots.txt / Google-Extended AI crawler control
Authority: Google Search Central, Robots.txt and crawler documentation
URL: https://developers.google.com/search/docs/crawling-indexing/robots/create-robots-txt (not independently re-fetched this pass; cited from the same Search Central domain as C1/C7, consistent access pattern)
Quote: not fetched verbatim this pass -- flagging as a gap; Google publicly documents Google-Extended as a separate user-agent token site owners can disallow to opt out of Gemini/AI training use of content, independent of standard Googlebot indexing rules in robots.txt.
Lint condition: robots.txt lint -- presence/absence of a User-agent: Google-Extended block is a deliberate policy choice to record, not a pass/fail; flag only if the file is malformed (missing trailing newline, wrong Disallow path casing).

### C10. Structured data / LocalBusiness schema
Authority: Schema.org, LocalBusiness type
URL: https://schema.org/LocalBusiness
Quote: Schema.org defines LocalBusiness as "A particular physical business or branch of an organization. Examples of LocalBusiness include a restaurant, a particular branch of a restaurant chain, a branch of a bank, a medical practice, a club, etc." with expected properties inherited from Organization and Place (address, telephone, openingHoursSpecification).
Lint condition: JSON-LD lint for a LocalBusiness block missing required/expected address, name, or telephone properties, or mismatched @type.

### C11. Open Graph protocol required properties
Authority: Open Graph Protocol
URL: https://ogp.me/
Quote: "og:title - The title of your object as it should appear within the graph... og:type - The type of your object... og:image - An image URL which should represent your object... og:url - The canonical URL of your object."
Lint condition: <head> lint for pages missing any of og:title, og:type, og:image, og:url meta tags.

### C12. XML Sitemap protocol
Authority: Sitemaps.org protocol
URL: https://www.sitemaps.org/protocol.html
Quote: "This document describes the XML schema for the Sitemap protocol. The Sitemap protocol format consists of XML tags."
Lint condition: sitemap.xml validation against the http://www.sitemaps.org/schemas/sitemap/0.9 namespace/schema; flag malformed <urlset> or missing <loc>.

### C13. Canonical link element
Authority: RFC 6596, "The Canonical Link Relation"
URL: https://www.rfc-editor.org/rfc/rfc6596
Quote: "The canonical link relation are to specify the preferred version of an [Internationalized Resource Identifier]" used to designate the preferred IRI among duplicate/near-duplicate resources.
Lint condition: template lint for pages with query-string variants (tracking params, pagination) and no <link rel="canonical"> pointing to the clean URL.

### C14. HTML lang attribute
Authority: WHATWG HTML Standard, "The lang and xml:lang attributes"
URL: https://html.spec.whatwg.org/multipage/dom.html#the-lang-and-xml:lang-attributes
Quote: the spec defines the lang attribute as specifying "the primary language for the element's contents and for any of the element's attributes that contain text," used identically to WCAG 3.1.1 above.
Lint condition: same as B4 -- duplicate cross-reference, not a separate check.

### C15. Favicon guidelines
Authority: Google Search Central, Favicon guidelines
URL: https://developers.google.com/search/docs/appearance/favicon-in-search (not independently re-fetched this pass; same domain/access pattern verified for C1/C7/C9)
Quote: not fetched verbatim this pass -- flagging as a gap; Google's documented favicon rules require a square, minimum-size icon reachable at a stable URL for it to appear in search results.
Lint condition: <head> lint for missing <link rel="icon">/favicon.ico, or an icon file below Google's minimum documented pixel dimensions.

## D. Web performance

### D1. Core Web Vitals thresholds
Authority: web.dev (Google), "Web Vitals"
URL: https://web.dev/articles/vitals
Quote: page defines the "good" thresholds for the three Core Web Vitals: Largest Contentful Paint (LCP) <= 2.5s, Interaction to Next Paint (INP) <= 200ms, Cumulative Layout Shift (CLS) <= 0.1, each measured at the 75th percentile of page loads.
Lint condition: CI/Lighthouse-CI budget config asserting LCP/INP/CLS thresholds; flag builds exceeding budget.

### D2. Lighthouse performance audits
Authority: web.dev / Lighthouse documentation (audit catalog referenced via web.dev)
URL: https://web.dev/articles/vitals (Lighthouse audit set is the standard companion tooling for these metrics; a dedicated audits-list page was not separately re-fetched this pass)
Quote: not independently re-quoted this pass -- flagging as a gap for the exact audit-catalog page text; the audits (unused JavaScript, render-blocking resources, next-gen image formats, offscreen-image lazy loading, minification, text compression, source maps) are Lighthouse's well-documented standard categories.
Lint condition: CI Lighthouse config asserting unused-javascript, render-blocking-resources, modern-image-formats, offscreen-images, unminified-css/unminified-javascript, uses-text-compression audits pass above a score threshold.

### D3. HTTP caching -- Cache-Control
Authority: RFC 9111, HTTP Caching
URL: https://www.rfc-editor.org/rfc/rfc9111
Quote: RFC 9111 defines the Cache-Control header field and directives (max-age, no-store, no-cache, must-revalidate) governing response cacheability.
Lint condition: server/CDN config lint for static-asset responses with no Cache-Control header or no-store on cacheable assets (JS/CSS/images with content-hashed filenames).

### D4. HTTP compression negotiation
Authority: RFC 9110, HTTP Semantics
URL: https://www.rfc-editor.org/rfc/rfc9110
Quote: RFC 9110 defines the Accept-Encoding request header and content-negotiation mechanism used to select compressed representations.
Lint condition: server config lint for missing gzip/brotli compression middleware on text-based responses (HTML/CSS/JS/JSON).

### D5. OWASP security headers
Authority: OWASP Secure Headers Project
URL: https://owasp.org/www-project-secure-headers/
Quote: page failed to yield full body text in this pass (14KB stub, likely a redirect/loader shell); citing the project's well-documented recommended header set: Content-Security-Policy, Strict-Transport-Security, X-Content-Type-Options: nosniff, X-Frame-Options/frame-ancestors, Referrer-Policy, Permissions-Policy.
Lint condition: response-header lint (integration test or CI header-scanner) for absence of each listed header on production responses.

### D6. loading="lazy" attribute
Authority: WHATWG HTML Standard, lazy-loading attributes
URL: https://html.spec.whatwg.org/multipage/urls-and-fetching.html#lazy-loading-attributes
Quote: the spec defines the loading content attribute on img/iframe with values lazy and eager controlling deferred fetching of offscreen resources.
Lint condition: template lint for below-the-fold <img>/<iframe> elements with no loading="lazy" attribute.

### D7. defer/async script attributes
Authority: WHATWG HTML Standard, the script element
URL: https://html.spec.whatwg.org/multipage/scripting.html#attr-script-defer (companion section to D6, same spec; not independently re-fetched this pass)
Quote: not independently re-quoted this pass -- flagging as a gap; the spec's well-documented behavior is that defer delays execution until after parsing and async allows out-of-order fetch-and-execute, both avoiding parser-blocking behavior of a bare synchronous <script src>.
Lint condition: HTML lint for <script src=...> tags in <head> with neither defer nor async and no inline-critical justification.

## E. Security (OWASP Top 10 / ASVS / NIST / cheat sheets / Supabase / CWE)

Note: OWASP retired the 2021 Top 10 in November 2025; the current edition is
Top 10:2025 (owasp.org/Top10/2025/). Category names below are 2025 current;
2021 names given in parens where they differ materially.

### E1. A01:2025 Broken Access Control
Authority: OWASP Top 10:2025, A01
URL: https://owasp.org/Top10/2025/
Quote: category is titled "A01:2025 - Broken Access [Control]" (2025 list, confirmed via page text extraction); IDOR, missing server-side authorization checks, and predictable resource IDs are the canonical examples across both the 2021 and 2025 editions.
Lint condition: route/middleware lint for handlers touching a resource-by-ID with no ownership/permission check before the DB read/write (see ASVS V8.2.2, E20 below, for the precise requirement).

### E2. A02:2025 Security Misconfiguration (was A05 in 2021)
Authority: OWASP Top 10:2025, A02
URL: https://owasp.org/Top10/2025/
Quote: "A02:2025 - Security Misconfiguration" -- note the category moved up from A05:2021 to A02:2025.
Lint condition: config lint for CORS: * with credentials, debug flags enabled in prod config, stack traces in error responses, and exposed source maps in production build output.

### E3. A03:2025 Software Supply Chain Failures (new; absorbs part of 2021's A06 Vulnerable Components)
Authority: OWASP Top 10:2025, A03
URL: https://owasp.org/Top10/2025/
Quote: "A03:2025 - Software Supply Chain Failures" is new in the 2025 edition, broadening 2021's "Vulnerable and Outdated Components" to cover build/CI pipeline and dependency-provenance risk.
Lint condition: dependency-manifest lint for unpinned versions (^/~ ranges without lockfile), and CI-pipeline lint for GitHub Actions steps referencing uses: action@v1 (tag) instead of a pinned commit SHA.

### E4. A04:2025 Cryptographic Failures (was A02:2021) -- password storage
Authority: OWASP Top 10:2025, A04; ASVS 5.0 V11.4.2 (Cryptography)
URL: https://owasp.org/Top10/2025/ ; https://github.com/OWASP/ASVS (5.0 flat requirements)
Quote: ASVS V11.4.2: "Verify that passwords are stored using an approved, computationally intensive, key derivation function (also known as a 'password hashing function'), with parameter settings configured based on current guidance."
Lint condition: code lint for password-hashing calls using md5/sha1/plain-text compare instead of bcrypt/argon2/scrypt/PBKDF2.

### E5. A05:2025 Injection (was A03:2021) -- SQL/NoSQL/OS command
Authority: ASVS 5.0 V1.2.4, V1.2.5 (chapter V1, Encoding and Sanitization)
URL: https://github.com/OWASP/ASVS
Quote: V1.2.4: "Verify that data selection or database queries (e.g., SQL, HQL, NoSQL, Cypher) use parameterized queries, ORMs, entity frameworks, or are otherwise protected from injection attacks." V1.2.5: "Verify that the application protects against OS command injection and that operating system calls use parameterized OS queries."
Lint condition: AST/regex lint for string-concatenated SQL ("SELECT * FROM " + table + where), subprocess/os.system calls with shell=True and interpolated input, and eval/exec on request data.

### E6. Deserialization of untrusted data
Authority: ASVS 5.0 V1.5.2 (chapter V1)
URL: https://github.com/OWASP/ASVS
Quote: "Verify that deserialization of untrusted data enforces safe input handling, such as using an allowlist of object types or restricting client-defined object types, to prevent deserialization attacks. Deserialization mechanisms that are explicitly defined as insecure must not be used with untrusted input."
Lint condition: code lint for pickle.load/pickle.loads or yaml.load (without SafeLoader) applied to request bodies/uploaded files.

### E7. XML external entities
Authority: ASVS 5.0 V1.5.1 (chapter V1)
URL: https://github.com/OWASP/ASVS
Quote: "Verify that the application configures XML parsers to use a restrictive configuration and that unsafe features such as resolving external entities are [disabled]."
Lint condition: XML-parser instantiation lint for missing resolve_entities=False / DTDLoadOption disabled / XMLConstants.FEATURE_SECURE_PROCESSING equivalents.

### E8. SSRF
Authority: ASVS 5.0 V1.3.6 (chapter V1)
URL: https://github.com/OWASP/ASVS
Quote: "Verify that the application protects against Server-side Request Forgery (SSRF) attacks, by validating untrusted data against an allowlist of protocols, domains, paths and ports and sanitizing potentially dangerous characters before using the data to call another service."
Lint condition: code lint for server-side HTTP-fetch calls (requests.get, fetch, axios) whose URL argument derives from unvalidated request input with no allowlist check.

### E9. Open redirect
Authority: ASVS 5.0 V3.7.2 (chapter V3, Web Frontend Security)
URL: https://github.com/OWASP/ASVS
Quote: "Verify that the application will only automatically redirect the user to a different hostname or domain (which is not controlled by the application) [with] ... explicit user confirmation."
Lint condition: code lint for redirect handlers (redirect(request.args.get('next'))) with no allowlist/relative-path check.

### E10. Path traversal in file serving/upload
Authority: ASVS 5.0 V5.3.2 (chapter V5, File Handling)
URL: https://github.com/OWASP/ASVS
Quote: "Verify that when the application creates file paths for file operations, instead of user-submitted filenames, it uses internally generated or trusted filenames, or that user input is validated to prevent directory traversal."
Lint condition: code lint for file-open/serve calls building a path via string concatenation of a user-supplied filename without normalization/allowlist against .. or absolute paths.

### E11. Clickjacking -- frame-ancestors
Authority: ASVS 5.0 V3.4.6 (chapter V3)
URL: https://github.com/OWASP/ASVS
Quote: "Verify that the web application uses the frame-ancestors directive of the Content-Security-Policy header field for every HTTP response ... Note that the X-Frame-Options header field, although supported by browsers, is obsolete and may not be relied upon."
Lint condition: response-header lint for missing Content-Security-Policy: frame-ancestors directive.

### E12. CORS misconfiguration
Authority: ASVS 5.0 V3.4.2 (chapter V3)
URL: https://github.com/OWASP/ASVS
Quote: "Verify that the Cross-Origin Resource Sharing (CORS) Access-Control-Allow-Origin header field is a fixed value by the application, or if the Origin HTTP request header field value is used, it is validated against an allowlist of trusted origins."
Lint condition: server config lint for CORS middleware set to origin: '*' combined with credentials: true, or reflecting request.headers.origin verbatim with no allowlist.

### E13. Cookie flags -- Secure/HttpOnly/SameSite
Authority: ASVS 5.0 V3.3.1, V3.3.2 (chapter V3)
URL: https://github.com/OWASP/ASVS
Quote: V3.3.1: "Verify that cookies have the 'Secure' attribute set, and if the '__Host-' prefix is not used for the cookie name, the '__Secure-' prefix must [be]." V3.3.2: "Verify that each cookie's 'SameSite' attribute value is set according to the purpose of the cookie, to limit exposure to user interface redress[ing]/CSRF."
Lint condition: cookie-setter code/config lint (session middleware config) for cookies missing Secure, HttpOnly, or SameSite attributes.

### E14. Session termination on logout
Authority: ASVS 5.0 V7.4.1 (chapter V7, Session Management)
URL: https://github.com/OWASP/ASVS
Quote: "Verify that when session termination is triggered (such as logout or expiration), the application disallows any further use of the session."
Lint condition: logout-handler lint for a route that clears client cookie but never invalidates the corresponding server-side session/token record.

### E15. JWT algorithm allowlist / algorithm confusion
Authority: ASVS 5.0 V9.1.2 (chapter V9, Self-contained Tokens)
URL: https://github.com/OWASP/ASVS
Quote: "Verify that only algorithms on an allowlist can be used to create and verify self-contained tokens, for a given context."
Lint condition: JWT-verification code lint for algorithms= parameter omitted (library default may accept none) or including both symmetric (HS256) and asymmetric (RS256) algorithms in the same allowlist.

### E16. OAuth PKCE
Authority: ASVS 5.0 V10.4.6 (chapter V10, OAuth and OIDC)
URL: https://github.com/OWASP/ASVS
Quote: "Verify that, if the code grant is used, the authorization server mitigates authorization code interception attacks by requiring proof key for code exchange (PKCE)."
Lint condition: OAuth client-config lint for authorization-code flow with no code_challenge/code_verifier parameters.

### E17. Password length -- no composition rules, allow long passwords
Authority: ASVS 5.0 V6.2.1, V6.2.5, V6.2.9 (chapter V6, Authentication); NIST SP 800-63B section 5.1.1.2 memorized secret requirements
URL: https://github.com/OWASP/ASVS ; https://pages.nist.gov/800-63-3/sp800-63b.html
Quote: ASVS "V6.2.1 Verify that user set passwords are at least 8 characters in length although a minimum of 15 characters is strongly recommended." "V6.2.5 ... no requirement for a minimum number of upper or lower case characters, numbers, or special characters." "V6.2.9 Verify that passwords of at least 64 characters are permitted." NIST 800-63B: "at least 8 characters in length if chosen by the subscriber" is the SHALL floor, and "Verifiers SHOULD permit subscriber-chosen memorized secrets at least 64 characters in length."
Lint condition: auth-policy config lint for max_length < 64 or any regex requiring mixed character classes on password fields.

### E18. Rate limiting / anti-automation / lockout
Authority: ASVS 5.0 V6.1.1, V6.6.3 (chapter V6)
URL: https://github.com/OWASP/ASVS
Quote: "Verify that application documentation defines how controls such as rate limiting, anti-automation, and adaptive response, are used to defend against automated attacks." V6.6.3: OTP/code-based auth must be "protected against brute force attacks by using rate limiting."
Lint condition: route config lint for login/OTP/password-reset endpoints with no rate-limit middleware attached.

### E19. Multi-factor authentication availability
Authority: ASVS 5.0 V6.3.3 (chapter V6)
URL: https://github.com/OWASP/ASVS
Quote: "Verify that either a multi-factor authentication mechanism or a combination of single-factor authentication mechanisms, must be used" for sensitive operations.
Lint condition: not purely static; config check for whether an MFA provider/step is registered at all in the auth stack (absence is flaggable; per-user enforcement is dynamic-only).

### E20. IDOR / BOLA -- object-level authorization
Authority: ASVS 5.0 V8.2.2 (chapter V8, Authorization)
URL: https://github.com/OWASP/ASVS
Quote: "Verify that the application ensures that data-specific access is restricted to consumers with explicit permissions to specific data items to mitigate insecure direct object reference (IDOR) and broken object level authorization (BOLA)."
Lint condition: handler lint for GET/PUT/DELETE /resource/:id with no WHERE owner_id = current_user (or RLS-equivalent) clause.

### E21. Field-level authorization / BOPLA
Authority: ASVS 5.0 V8.2.3 (chapter V8)
URL: https://github.com/OWASP/ASVS
Quote: "Verify that the application ensures that field-level access is restricted to consumers with explicit permissions to specific fields to mitigate broken object property level authorization (BOPLA)."
Lint condition: serializer lint for API response schemas that expose all model fields by default rather than an explicit allowlist per role.

### E22. Mass assignment
Authority: ASVS 5.0 V15.3.3 (chapter V15, Secure Coding and Architecture)
URL: https://github.com/OWASP/ASVS
Quote: "Verify that the application has countermeasures to protect against mass assignment attacks by limiting allowed fields per controller and action, e.g., it is not possible to insert or update a field value when it was not intended to be part of that action."
Lint condition: ORM lint for Model.create(**request.json) / Model(**form.data) style whole-body assignment with no explicit field allowlist/DTO.

### E23. HTTP Parameter Pollution
Authority: ASVS 5.0 V15.3.7 (chapter V15)
URL: https://github.com/OWASP/ASVS
Quote: "Verify that the application has defenses against HTTP parameter pollution attacks, particularly if the application framework makes no distinction about the source of request parameters (query string, body parameters, cookies, or header fields)."
Lint condition: dynamic-only in general; static check limited to flagging frameworks/configs known to silently merge duplicate parameter sources without an explicit precedence rule.

### E24. Prototype pollution (JS)
Authority: ASVS 5.0 V15.3.6 (chapter V15)
URL: https://github.com/OWASP/ASVS
Quote: "Verify that JavaScript code is written in a way that prevents prototype pollution, for example, by using Set() or Map() instead of object literals."
Lint condition: JS/TS lint (eslint rule class) for obj[userKey] = value patterns on plain object literals with unvalidated key names, especially __proto__/constructor/prototype literals.

### E25. ReDoS
Authority: ASVS 5.0 V1.3.12 (chapter V1)
URL: https://github.com/OWASP/ASVS
Quote: "Verify that regular expressions are free from elements causing exponential backtracking, and ensure untrusted input is sanitized to mitigate ReDoS."
Lint condition: static regex-complexity linter (e.g., detecting nested quantifiers like (a+)+) run against regex literals that process untrusted input.

### E26. File upload validation (type, size, magic bytes)
Authority: ASVS 5.0 V5.1.1, V5.2.1, V5.2.2 (chapter V5)
URL: https://github.com/OWASP/ASVS
Quote: V5.2.2: "Verify that when the application accepts a file ... it checks if the file extension matches an expected file extension and validates that the contents correspond to the type represented by the extension. This includes ... checking the initial 'magic bytes' ..." V5.2.1: "Verify that the application will only accept files of a size which it can process without causing a loss of performance or a denial of service attack."
Lint condition: upload-handler lint for missing content-type/magic-byte verification and missing max-size enforcement before the file is written to disk/bucket.

### E27. Zip/archive extraction bombs
Authority: ASVS 5.0 V5.2.2 (archive-content clause, chapter V5)
URL: https://github.com/OWASP/ASVS
Quote: same requirement text as E26 explicitly extends "on its own or within an archive such as a zip file."
Lint condition: extraction-code lint for zipfile.extractall()/tar.extractall() calls with no per-entry size cap or path-traversal check on entry names.

### E28. GraphQL introspection and depth/cost limiting
Authority: ASVS 5.0 V4.3.1, V4.3.2 (chapter V4, API and Web Service)
URL: https://github.com/OWASP/ASVS
Quote: V4.3.1: "Verify that a query allowlist, depth limiting, amount limiting, or query cost analysis is used to prevent GraphQL or data layer expression [DoS]." V4.3.2: "Verify that GraphQL introspection queries are disabled in the production environment unless the GraphQL API is meant to be used by other parties."
Lint condition: GraphQL server config lint for introspection: true in a production config file, and for missing depth/cost-limit middleware.

### E29. WebSocket origin check and TLS
Authority: ASVS 5.0 V4.4.1, V4.4.2 (chapter V4)
URL: https://github.com/OWASP/ASVS
Quote: V4.4.1: "Verify that WebSocket over TLS (WSS) is used for all WebSocket connections." V4.4.2: "Verify that, during the initial HTTP WebSocket handshake, the Origin header field is checked against a list of origins allowed for the application."
Lint condition: WS-server config lint for ws:// (non-TLS) listener in production, and handler lint for missing origin-check in the connection/upgrade callback.

### E30. Debug mode / directory listing in production
Authority: ASVS 5.0 V13.4.2, V13.4.3 (chapter V13, Configuration)
URL: https://github.com/OWASP/ASVS
Quote: V13.4.2: "Verify that debug modes are disabled for all components in production environments to prevent exposure of debugging features and information leakage." V13.4.3: "Verify that web servers do not expose directory listings to clients unless explicitly intended."
Lint condition: config lint for DEBUG=True/app.debug=true in a production environment file, and web-server config lint for autoindex on (nginx) or missing Options -Indexes (Apache).

### E31. Browser storage for sensitive data / tokens
Authority: ASVS 5.0 V14.3.3 (chapter V14, Data Protection); OWASP HTML5 Security Cheat Sheet
URL: https://github.com/OWASP/ASVS ; https://cheatsheetseries.owasp.org/cheatsheets/HTML5_Security_Cheat_Sheet.html
Quote: ASVS V14.3.3: "Verify that data stored in browser storage (such as localStorage, sessionStorage, IndexedDB, or cookies) does not contain sensitive data, with the exception of [documented cases]."
Lint condition: JS lint for localStorage.setItem/sessionStorage.setItem calls storing values named/typed like token, jwt, access_token, password.

### E32. Third-party component provenance / supply chain
Authority: ASVS 5.0 V15.2.4 (chapter V15)
URL: https://github.com/OWASP/ASVS
Quote: "Verify that third-party components and all of their transitive dependencies are included from the expected repository, whether internally owned or an approved external repository."
Lint condition: package-manifest lint for dependencies pulled from non-default/unpinned registries, or lockfile hashes mismatched against the manifest.

### E33. Race conditions on shared/financial state (TOCTOU)
Authority: ASVS 5.0 V15.4.1, V15.4.2 (chapter V15)
URL: https://github.com/OWASP/ASVS
Quote: V15.4.1: "Verify that shared objects in multi-threaded code (such as caches, files, or in-memory objects accessed by multiple threads) are accessed safely." V15.4.2: "Verify that checks on a resource's state, such as its existence or permissions, and the actions that depend on them are performed as a single atomic operation."
Lint condition: code lint for a read-check-then-write pattern on balance/coupon/inventory fields with no DB-level lock/transaction/unique constraint enforcing atomicity.

### E34. Insecure randomness for tokens/IDs
Authority: ASVS 5.0 V6.5.3, V11.2.2 (chapters V6, V11)
URL: https://github.com/OWASP/ASVS
Quote: V6.5.3: lookup secrets/OTP seeds must be "generated using a Cryptographically [Secure Random Number Generator]." V11.2.2 requires crypto agility for "random number, authenticated encryption, MAC, or hashing algorithms."
Lint condition: code lint for Math.random()/random.random() (non-CSPRNG) used to generate session IDs, password-reset tokens, or API keys.

### E35. Supabase / Postgres RLS off by default
Authority: Supabase Docs, Row Level Security
URL: https://supabase.com/docs/guides/database/postgres/row-level-security
Quote: fetch succeeded (614KB) but the targeted grep for the exact "disabled by default" sentence did not isolate cleanly from the rendered doc shell in this pass; Supabase's documented behavior (consistent across its RLS guide) is that tables created via the SQL editor/migrations have RLS disabled by default, and any table exposed through the auto-generated API without RLS enabled is queryable by anyone holding the public anon key.
Lint condition: migration-file lint for CREATE TABLE statements in a Supabase/Postgres project with no matching ALTER TABLE ... ENABLE ROW LEVEL SECURITY in the same or a later migration.
Note: quote is a paraphrase pending a cleaner re-fetch; treat as high-confidence but not verbatim-cited.

### E36. CWE Top 25 (2024) cross-reference
Authority: MITRE, 2024 CWE Top 25 Most Dangerous Software Weaknesses
URL: https://cwe.mitre.org/top25/archive/2024/2024_cwe_top25.html
Quote: page fetched (19.7KB) but the ranked list itself renders via client-side JS/table and did not appear in the static HTML text extraction -- BLOCKED for exact quote/ranking this pass. The page's static text confirms scope: "This list demonstrates the currently most common and impactful software weaknesses" derived from "31,770 Common Vulnerabilities and Exposures (CVE) Records."
Lint condition: cross-reference only -- tag existing lint items above with their CWE ID in tooling output (CWE-79 XSS output-encoding items, CWE-89 SQLi via E5, CWE-352 CSRF via E13/SameSite, CWE-22 path traversal via E10, CWE-434 unrestricted upload via E26, CWE-863/862 authorization via E1/E20/E21, CWE-306/287 auth failures via E17-E19, CWE-798 hard-coded credentials via E32/secrets scanning); exact 2024 ranking needs a manual re-pull (JS-rendered table), so treat rank order as unverified this pass.

## F. SQL

### F1. SQL logical processing order
Authority: PostgreSQL Documentation, 7.2. Table Expressions
URL: https://www.postgresql.org/docs/current/queries-table-expressions.html
Quote: "A table expression computes a table. The table expression contains a FROM clause that is optionally followed by WHERE, GROUP BY, and HAVING clauses ... The optional WHERE, GROUP BY, and HAVING clauses in the table expression specify a pipeline of successive transformations performed on the table derived in the FROM clause." (section 7.2.3 title: "The GROUP BY and HAVING Clauses")
Lint condition: SQL-linter rule flagging a HAVING clause referencing a column that could instead be filtered in WHERE (a non-aggregate predicate placed in HAVING), which is correct-but-inefficient since HAVING runs after grouping while WHERE runs before.

### F2. Index foreign-key columns
Authority: PostgreSQL Documentation, 5.5.5 Foreign Keys
URL: https://www.postgresql.org/docs/current/ddl-constraints.html
Quote: "Since a DELETE of a row from the referenced table or an UPDATE of a referenced column will require a scan of the referencing table for rows matching the old value, it is often a good idea to index the referencing columns too ... the declaration of a foreign key constraint does not automatically create an index on the referencing columns."
Lint condition: schema/migration lint for REFERENCES (foreign key) columns with no corresponding CREATE INDEX/btree index in the same migration set.

### F3. Keyset pagination vs. OFFSET
Authority: use-the-index-luke.com, "No Offset"
URL: https://use-the-index-luke.com/no-offset
Quote: "As it turns out, living without offset is quite simple: just use a where clause that selects only data you haven't seen yet" -- contrasted against OFFSET-based paging, which the same page shows produces duplicate/skipped rows "in case there were new rows inserted between fetching two pages."
Lint condition: query-builder/ORM lint for .offset(n).limit(m) pagination patterns on large or frequently-written tables with no keyset (WHERE id > :cursor ORDER BY id LIMIT :n) alternative available.

## G. What web and SaaS operators are actually being sued or fined for (2022-2026)

### G1. ADA Title III / California Unruh Act website accessibility suits
Authority: 42 U.S.C. 12182 (ADA Title III); Cal. Civ. Code 51 (Unruh Civil Rights Act, incorporating ADA violations as per se Unruh violations); leading case Robles v. Domino's Pizza, LLC, 913 F.3d 898 (9th Cir. 2019)
URL: https://www.law.cornell.edu/uscode/text/42/12182 ; https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?sectionNum=51.&lawCode=CIV
Quote: not independently re-fetched this pass for Robles or Unruh text -- BLOCKED for exact quote; annual filing-count data (UsableNet/Seyfarth trackers report thousands of federal ADA web-accessibility suits per year since 2022, with California state-court Unruh filings comparably high) is industry-report data, not primary-source text, and was not independently verified in this pass.
Lint condition: same as B1-B9 (WCAG 2.2 AA violations) -- these are the fact pattern plaintiffs' firms scan for (missing alt text, unlabeled form fields, no keyboard focus order, insufficient contrast).

### G2. Session-replay/pixel wiretap suits -- CIPA 631, VPPA
Authority: Cal. Penal Code 631(a); 18 U.S.C. 2710 (Video Privacy Protection Act)
URL: https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?sectionNum=631.&lawCode=PEN ; https://www.law.cornell.edu/uscode/text/18/2710
Quote: CIPA 631(a): a person is liable who "willfully and without the consent of all parties to the communication, or in any unauthorized manner, reads, or attempts to read, or to learn the contents or meaning of any message, report, or communication while the same is in transit." VPPA defines a "video tape service provider" (extended by courts to online video-on-demand) whose disclosure of a consumer's video-viewing history to a third party without consent creates statutory liability.
Lint condition: page-level lint flagging any session-replay/analytics script (FullStory, Hotjar, Meta Pixel) loaded on a page containing a <video> element or a form, with no documented two-party consent/cookie-consent gate preceding script load.

### G3. Illinois BIPA -- biometrics
Authority: 740 ILCS 14 (Biometric Information Privacy Act), section 15(b)
URL: https://www.ilga.gov/legislation/ilcs/ilcs3.asp?ActID=3004&ChapterID=57
Quote: fetch returned an ILGA listing page rather than section 15 text directly in this pass -- flagging as a gap; BIPA section 15(b) is well-documented to require written notice and consent before "collecting, capturing, purchasing, receiving through trade, or otherwise obtaining" a person's biometric identifier (fingerprint, faceprint, voiceprint, retina/iris scan). Leading case: Rosenbach v. Six Flags Entertainment Corp., 2019 IL 123186 (no actual injury required to sue).
Lint condition: code lint for any face/voice/fingerprint SDK call (e.g., face-detection library, voice-biometric auth) with no preceding consent-capture step logged.

### G4. FTC dark patterns / Click-to-Cancel and California ARL
Authority: FTC Act Section 5 (15 U.S.C. 45); 16 CFR Part 425 (Negative Option Rule, "Click-to-Cancel," vacated on procedural grounds by the 8th Circuit in July 2025); Cal. Bus. & Prof. Code 17600 et seq. (Automatic Renewal Law)
URL: https://www.ecfr.gov/current/title-16/chapter-I/subchapter-F/part-425 ; https://www.ftc.gov/legal-library/browse/rules/negative-option-rule
Quote: the Negative Option Rule (as promulgated) required that "the mechanism [to cancel] must be at least as easy to use as the mechanism the consumer used to consent to the negative option feature" (the "click to cancel" standard); this rule was vacated on procedural (not substantive) grounds by the Eighth Circuit in July 2025, so the FTC currently enforces the same substance under Section 5's general dark-patterns theory plus the still-standing prior Negative Option Rule provisions for telemarketing/direct-mail.
Lint condition: subscription-management-page lint for a cancel flow requiring more steps/contact channels (phone-only cancel) than the signup flow, or with no visible "Cancel" affordance of equal prominence to "Subscribe."

### G5. TCPA -- SMS marketing consent
Authority: 47 U.S.C. 227(b)
URL: https://www.law.cornell.edu/uscode/text/47/227
Quote: TCPA restricts autodialed/prerecorded calls and texts made without "prior express consent," with statutory carve-outs including "prior express invitation or permission" and "established business relationship" contexts. (The FCC's 2025 "one-to-one consent" rule, which would have required consent to be tied to a single specific seller, was vacated by the 11th Circuit in January 2025 before its effective date -- current FCC guidance treats broad lead-generation consent-sharing as still permissible pending further rulemaking.)
Lint condition: SMS-signup-form lint for a single checkbox pre-checked or bundling multiple advertisers' consent into one unlabeled opt-in, and for outbound-SMS code paths with no consent-timestamp record per recipient.

### G6. COPPA 2025 amended rule
Authority: 16 CFR Part 312, as amended (FTC Final Rule, effective components phasing in 2025-2026)
URL: https://www.ecfr.gov/current/title-16/chapter-I/subchapter-C/part-312
Quote: same section 15 quote as A18 above; the 2025 amendments (not separately re-fetched this pass) are documented by the FTC to add a separate, opt-in consent requirement for disclosing children's data to third parties for targeted advertising, and to tighten data-retention/minimization language -- citing from prior general knowledge, flagging as BLOCKED for a fresh direct quote of the amendment text this pass.
Lint condition: same as A18, plus a new check for a distinct "share with third parties for advertising" consent toggle separate from the base collection consent.

### G7. State comprehensive privacy laws beyond California -- universal opt-out/GPC
Authority: Colo. Rev. Stat. 6-1-1306(1)(a)(IV) (Colorado Privacy Act, universal opt-out mechanism); Cal. Code Regs. tit. 11, 7025 (CCPA regs, GPC recognition)
URL: https://iapp.org/resources/article/us-state-privacy-legislation-tracker/ (secondary tracker, used only to confirm the current roster/effective-date landscape, not as the primary legal citation)
Quote: not independently re-fetched primary statute text for Colorado/Virginia/Connecticut/Texas/Oregon/Montana this pass -- BLOCKED for exact quote; the IAPP tracker (secondary source) confirms as of this pass that, in addition to California/Colorado/Virginia/Connecticut (live since 2023), Texas (July 2024), Oregon (July 2024), Montana (Oct 2024), and a wave of others are now in force, with most requiring GPC/universal-opt-out-signal honoring similar to Colorado's.
Lint condition: consent-management config lint for a cookie/consent banner or backend flag with no code path that reads the Sec-GPC: 1 request header and auto-applies an opt-out.

### G8. Washington My Health My Data Act / Nevada SB 370 -- consumer health data
Authority: Wash. Rev. Code ch. 19.373; Nev. Rev. Stat. ch. 603A (as amended by 2023 SB 370)
URL: https://app.leg.wa.gov/rcw/default.aspx?cite=19.373 ; https://www.leg.state.nv.us/App/NELIS/REL/82nd2023/Bill/9852/Text
Quote: RCW 19.373 index confirms operative sections include "19.373.030 Consumer health data -- Requirements" and "19.373.040 Consumer rights and requests" and "19.373.050 Data security practices" (section text itself not independently re-quoted verbatim this pass -- flagging as a partial gap); both statutes extend health-data protections (broadly defined, including inferred health status) to consumer apps outside HIPAA's covered-entity scope, with a private right of action under WA MHMDA.
Lint condition: data-classification lint flagging any collected field/derived attribute matching a health-data taxonomy (symptoms, reproductive health, biometric health metrics) processed outside an existing HIPAA-compliance code path, with no MHMDA/NV-specific consent banner.

### G9. GDPR cookie-consent fines and ePrivacy
Authority: GDPR Art. 7(3) (consent withdrawal as easy as giving it); French CNIL enforcement against Google and Facebook (Jan 2022, EUR 150m and EUR 60m respectively) for making cookie refusal harder than acceptance
URL: https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32016R0679 (GDPR text; the CNIL decision itself not independently re-fetched this pass)
Quote: not independently re-quoted verbatim this pass for Art. 7(3) text -- flagging as a partial gap; this is the statutory basis CNIL applied when it fined Google/Facebook for a cookie banner with a one-click "Accept" but no equally simple "Reject."
Lint condition: consent-banner DOM lint for an "Accept all" button with no "Reject all"/"Decline" control of equal visual prominence (same size/step-count) on the same screen.

### G10. EU AI Act Art. 50 -- AI chatbot/content transparency
Authority: Regulation (EU) 2024/1689 (AI Act), Article 50; applicability 2 August 2026 for this obligation
URL: https://artificialintelligenceact.eu/article/50/
Quote: "Providers shall ensure that AI systems intended to interact directly with natural persons are designed and developed in such a way that the natural persons concerned are informed that they are interacting with an AI system," and providers of AI generating synthetic content must ensure their "technical solutions are effective, interoperable, robust and reliable as far as this is technically feasible" for marking outputs as AI-generated.
Lint condition: chat-widget/content-generation code lint for an AI chat interface with no disclosure string ("You are chatting with an AI") in the initial render, and for AI-image/text-generation output pipelines with no watermark/metadata-tagging step.

### G11. California AI transparency laws -- AB 2013, SB 942
Authority: Cal. Civ. Code (AB 2013, training-data transparency, effective Jan 1 2026); Cal. Bus. & Prof. Code (SB 942, California AI Transparency Act, effective Jan 1 2026 per 2025 amendment delay)
URL: not independently re-fetched this pass (leginfo section numbers for AB 2013/SB 942 were not pulled in this session) -- BLOCKED, citing from general knowledge of the bill numbers/effective dates only.
Lint condition: model-release lint requiring a published training-data summary document for any generative-AI feature offered to California users, and a detection/watermark API endpoint for SB 942-covered generative systems.

### G12. NYC Local Law 144 -- automated employment decision tools
Authority: N.Y.C. Admin. Code 20-870 et seq. (Local Law 144 of 2021)
URL: not independently re-fetched this pass -- BLOCKED, citing from general knowledge; the law requires a bias audit and public notice before using an "automated employment decision tool" in NYC hiring.
Lint condition: HR-tech code lint flagging any resume-screening/ranking model deployed against NYC job postings with no linked bias-audit report page.

### G13. Data breach notification -- Cal. Civ. Code 1798.82; SEC cyber disclosure rule
Authority: Cal. Civ. Code 1798.82; 17 CFR 229.106 (Item 106 of Regulation S-K, SEC cybersecurity disclosure rule, effective Dec 2023)
URL: https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?sectionNum=1798.82.&lawCode=CIV ; SEC rule URL not independently re-fetched this pass
Quote: not independently re-fetched this pass for either citation -- BLOCKED; both are well-documented: Cal. Civ. Code 1798.82 requires notification "in the most expedient time possible and without unreasonable delay" after a breach of unencrypted personal information; SEC Item 106 requires public companies to disclose material cybersecurity incidents on Form 8-K within four business days of a materiality determination.
Lint condition: incident-response runbook/config check for an automated breach-notification workflow with no SLA timer, and (for public companies) no linked materiality-assessment/8-K-filing checklist triggered by a confirmed breach ticket.

### G14. Age verification -- Texas HB 1181 upheld in Free Speech Coalition v. Paxton
Authority: Tex. Civ. Prac. & Rem. Code ch. 129B (HB 1181); Free Speech Coalition, Inc. v. Paxton, 606 U.S. ___ (2025)
URL: https://www.supremecourt.gov/opinions/24pdf/23-1122_c18e.pdf (PDF fetch returned empty in this pass -- BLOCKED)
Quote: not independently re-fetched this pass -- BLOCKED; the case is widely reported (and consistent with prior general knowledge) as the Supreme Court applying intermediate scrutiny and upholding Texas's age-verification mandate for adult content sites against a First Amendment challenge, decided June 27, 2025.
Lint condition: content-gating lint flagging any route serving adult-content classification with no age-verification middleware/gate in front of it, for sites with material Texas (or similarly-legislating-state) traffic.

## Items with no external authority (advisory/convention only)

- Team photo / "About us" page with staff bios.
- Customer case studies / testimonials pages.
- Generic "Thank you" post-submission page.
- A fixed count of FAQs (e.g., "5 FAQs").
- A promised response-time SLA on a contact page (e.g., "we reply within 24 hours") absent a specific regulatory SLA (contrast with A2/A8's actual 45-day/1-month statutory deadlines).
- Sticky/floating mobile call-to-action button placement.
- Loading skeleton/spinner UI pattern.
- Google Analytics (or similar) installation as such -- the tool is not itself a compliance item; its data flows are covered under A1-A13/G2/G9 above.
- Blog "read time" estimates, related-posts widgets, breadcrumb styling choices.
- Dark/light theme toggle, cookie-banner visual design (beyond the G9 equal-prominence lint condition).
# CWE Top 25 2024 (owner-supplied 2026-09-20, from cwe.mitre.org/top25)

Rank | CWE | Name | CVEs in KEV | Rank last year
1 | CWE-79 | Cross-site Scripting | 3 | 2
2 | CWE-787 | Out-of-bounds Write | 18 | 1
3 | CWE-89 | SQL Injection | 4 | 3
4 | CWE-352 | Cross-Site Request Forgery | 0 | 9
5 | CWE-22 | Path Traversal | 4 | 8
6 | CWE-125 | Out-of-bounds Read | 3 | 7
7 | CWE-78 | OS Command Injection | 5 | 5
8 | CWE-416 | Use After Free | 5 | 4
9 | CWE-862 | Missing Authorization | 0 | 11
10 | CWE-434 | Unrestricted Upload of File with Dangerous Type | 0 | 10
11 | CWE-94 | Code Injection | 7 | 23
12 | CWE-20 | Improper Input Validation | 1 | 6
13 | CWE-77 | Command Injection | 4 | 16
14 | CWE-287 | Improper Authentication | 4 | 13
15 | CWE-269 | Improper Privilege Management | 0 | 22
16 | CWE-502 | Deserialization of Untrusted Data | 5 | 15
17 | CWE-200 | Exposure of Sensitive Information | 0 | 30
18 | CWE-863 | Incorrect Authorization | 2 | 24
19 | CWE-918 | Server-Side Request Forgery | 2 | 19
20 | CWE-119 | Improper Restriction of Operations within Memory Buffer | 2 | 17
21 | CWE-476 | NULL Pointer Dereference | 0 | 12
22 | CWE-798 | Use of Hard-coded Credentials | 2 | 18
23 | CWE-190 | Integer Overflow or Wraparound | 3 | 14
24 | CWE-400 | Uncontrolled Resource Consumption | 0 | 37
25 | CWE-306 | Missing Authentication for Critical Function | 5 | 20

Mapping note: 19 of 25 are web/appsec and map to the WEBSEC stories. Six are memory-safety
(787, 125, 416, 119, 476, 190) and apply to frob's C, C++, Rust-unsafe and C# unsafe support,
not to web rules; they need their own MEMSAFE family (or LANG/FFI extension) with the CWE id
in the reason. The 2025 list (published Nov 2025) must be fetched and diffed before the rule
ids are frozen; the researcher's fetch of the ranked table was blocked by JS rendering.

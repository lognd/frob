---
id: T-5145
title: 'COMPLY: required pages, disclosures and config for CCPA/CPRA, CalOPPA, GDPR
  and ePrivacy, UK, Canada, Brazil, Australia, Japan, India, US state laws, HIPAA/GLBA/COPPA/FERPA,
  AI transparency laws, CASL/CAN-SPAM/TCPA, DSA, breach notification -- each rule
  cites the section'
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
  old_length: 1636
  new_length: 28337
designated_repro_test: null
threat: null
component: gates
anchor: false
anchor_reason: null
land_commit: null
---
36 entries here plus 22 in lint-authorities.md section A and 14 in section G (litigation and enforcement patterns: ADA/Unruh accessibility suits, CIPA session-replay and pixel wiretap suits, VPPA, BIPA, FTC click-to-cancel and dark patterns, TCPA SMS, COPPA 2025 rule, state privacy laws with GPC, health data laws, cookie consent fines, EU AI Act Art. 50, California AI laws, NYC LL144, breach rules, age verification). 26 entries are BLOCKED on statute text fetch and carry the official-domain citation only; the implementer re-fetches and quotes before shipping the rule text. Rule shape: (a) required-page checks keyed on what the repo does: collects email -> privacy policy page with the CalOPPA 22575(b) contents and CCPA 1798.130 sections; uses AI on user data -> terms of service with AI disclosure and EU AI Act Art. 50 chatbot notice; has subscriptions -> cancel path of equal prominence (16 CFR 425, Cal. B&P 17600); sells/shares -> Do Not Sell link and GPC signal handling in consent code; sends SMS -> TCPA consent capture; embeds session replay, chat widget or Meta pixel -> disclosure and consent gate before load (CIPA 631/638.51, VPPA); processes health data outside HIPAA -> MHMDA consent; (b) config checks: analytics/pixel scripts loaded before consent in EU-targeted builds; data retention config absent for PII stores (ties to PII003); delete-my-data path: a request route or documented mailbox plus a 45-day (CCPA) / one-month (GDPR Art. 12(3)) SLA recorded; breach notification runbook present. Owner directive: delete-my-data reaches a human-read mailbox, clock starts at receipt, data-handling policy required.

# International and remaining US privacy/compliance lint authorities

Fills gaps left in lint-authorities.md section A. Sources fetched this pass:
eur-lex GDPR consolidated text (Articles 28/30/33/35/44/45), Canada's
Justice Laws site (PIPEDA), Quebec's LegisQuebec (Law 25 / P-39.1), Brazil's
Planalto (LGPD), Australia's OAIC page, Switzerland's Fedlex (nFADP), and
California's leginfo/oag.ca.gov (Delete Act). Several sources returned
JS-rendered shells (India's DPDP, Japan's APPI) or index pages rather than
operative text -- flagged individually as BLOCKED.

### 1. GDPR Art. 28 -- processor contracts (DPA)
Authority: Regulation (EU) 2016/679, Article 28(3)
URL: https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:02016R0679-20160504&from=EN
Quote: "Processing by a processor shall be governed by a contract or other legal act ... that sets out the subject-matter and duration of the processing, the nature and purpose of the processing, the type of personal data and categories of data subjects and the obligations and rights of the controller. That contract ... shall stipulate, in particular, that the processor: (a) processes the personal data only on documented instructions from the controller ..."
Lint condition: vendor-management config lint for any third-party processor (analytics, email, hosting) integrated into the codebase with no linked signed Data Processing Agreement (DPA) record in the vendor registry.
Static: config

### 2. GDPR Art. 30 -- records of processing activities (RoPA)
Authority: Regulation (EU) 2016/679, Article 30(1)
URL: https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:02016R0679-20160504&from=EN
Quote: "Each controller ... shall maintain a record of processing activities under its responsibility. That record shall contain ... (b) the purposes of the processing; (c) a description of the categories of data subjects and of the categories of personal data ... (f) where possible, the envisaged time limits for erasure ..."
Lint condition: doc-check for a maintained RoPA document/table mapped 1:1 against the codebase's actual PII-collecting endpoints (a data-flow inventory diff would flag an endpoint with no RoPA entry).
Static: config

### 3. GDPR Art. 35 -- DPIA for high-risk processing
Authority: Regulation (EU) 2016/679, Article 35(1), (3)
URL: https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:02016R0679-20160504&from=EN
Quote: "Where a type of processing in particular using new technologies ... is likely to result in a high risk to the rights and freedoms of natural persons, the controller shall, prior to the processing, carry out an assessment of the impact ..."; required for "(a) a systematic and extensive evaluation of personal aspects ... based on automated processing, including profiling, ... (b) processing on a large scale of special categories of data ..."
Lint condition: feature-flag/ticket-gate lint requiring a linked DPIA document before merging a feature that adds automated-decision/profiling logic or bulk special-category-data (health, biometric) processing.
Static: config

### 4. GDPR Art. 44-45 -- international transfers and adequacy
Authority: Regulation (EU) 2016/679, Article 44, Article 45(1)
URL: https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:02016R0679-20160504&from=EN
Quote: Art. 44: "Any transfer of personal data ... to a third country or to an international organisation shall take place only if ... the conditions laid down in this Chapter are complied with." Art. 45(1): "A transfer of personal data to a third country ... may take place where the Commission has decided that the third country ... ensures an adequate level of protection."
Lint condition: infra config lint for a database/storage region or third-party SaaS vendor located outside the EEA with no linked Standard Contractual Clauses (SCC) record or adequacy-decision reference (e.g., EU-US Data Privacy Framework self-certification) in the vendor registry, for any EU-personal-data-processing workload.
Static: config

### 5. GDPR Art. 33-34 -- 72-hour breach notification
Authority: Regulation (EU) 2016/679, Article 33(1)
URL: https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:02016R0679-20160504&from=EN
Quote: "In the case of a personal data breach, the controller shall without undue delay and, where feasible, not later than 72 hours after having become aware of it, notify the personal data breach to the supervisory authority ... unless the personal data breach is unlikely to result in a risk to the rights and freedoms of natural persons."
Lint condition: incident-response runbook config check for an automated breach-notification workflow with no SLA timer <= 72 hours for EU-scoped incidents, distinct from the CCPA "expedient time" and SEC "4 business days" timers already logged in lint-authorities.md item G13.
Static: config

### 6. ePrivacy Directive Art. 5(3) -- cookie consent
Authority: Directive 2002/58/EC (ePrivacy Directive), as amended, Article 5(3)
URL: not independently re-fetched this pass (the amended consolidated ePrivacy Directive text was not pulled in this session) -- BLOCKED for a verbatim quote; the well-documented requirement is that storing or accessing information on a user's terminal equipment (cookies, local storage, fingerprinting scripts) requires prior informed consent, subject to a narrow "strictly necessary" exemption.
Lint condition: same as lint-authorities.md item G9's consent-banner DOM lint, extended to check that no non-essential cookie/tracking script fires before the user's affirmative consent action (i.e., consent-gating happens before script load, not just before data use).
Static: yes

### 7. UK GDPR / Data Protection Act 2018
Authority: UK GDPR (retained EU law) and Data Protection Act 2018
URL: not independently re-fetched this pass -- BLOCKED for a verbatim quote; the UK regime is substantively identical to EU GDPR post-Brexit with the ICO as the supervisory authority, so the lint conditions in items 1-5 above apply unchanged with "ICO" substituted for the EU supervisory authority.
Lint condition: same as items 1-5, gated on a UK-applicability flag rather than EU.
Static: config

### 8. UK Age Appropriate Design Code (Children's Code)
Authority: ICO, Age Appropriate Design Code (statutory code under DPA 2018 s.123)
URL: not independently re-fetched this pass -- BLOCKED for a verbatim quote; the well-documented standard requires services "likely to be accessed by children" to apply high-privacy defaults, disable profiling-based ad targeting by default for child accounts, and avoid "nudge techniques" toward lower-privacy settings.
Lint condition: account-settings config lint for a consumer service with no age-assurance signal where child-accessible content exists, and default-settings lint for privacy toggles defaulting to the lower-privacy option rather than the higher one.
Static: config

### 9. Canada PIPEDA -- meaningful consent
Authority: Personal Information Protection and Electronic Documents Act (PIPEDA), S.C. 2000, c. 5, Schedule 1
URL: https://laws-lois.justice.gc.ca/eng/acts/p-8.6/
Quote: fetch returned the statute's navigation/index page (24.6KB) rather than the Schedule 1 principles text directly in this pass -- flagging as a partial gap; PIPEDA's Schedule 1 Principle 4.3 is well-documented to require "knowledge and consent" of the individual for collection, use, or disclosure of personal information, except where inappropriate.
Lint condition: same consent-banner and privacy-notice checks as items A1/A6-A7 in lint-authorities.md, gated on a Canada-applicability flag.
Static: config

### 10. Quebec Law 25 (Act respecting the protection of personal information in the private sector, as amended)
Authority: CQLR c. P-39.1, sections 3.5-3.8 (confidentiality incident notification)
URL: https://www.legisquebec.gouv.qc.ca/en/document/cs/p-39.1
Quote: "Any person carrying on an enterprise who has cause to believe that a confidentiality incident involving personal information the person holds has occurred must take reasonable measures to reduce the risk of injury ... If the incident presents a risk of serious injury, the person carrying on an enterprise must promptly notify the Commission d'acces a l'information ... He must also notify any person whose personal information is concerned ..." and "'confidentiality incident' means (1) access not authorized by law ... (4) loss of personal information or any other breach of the protection of such information," with a mandatory "register of confidentiality incidents" under s.3.8.
Lint condition: incident-response config lint for no maintained breach/incident register (matching s.3.8's requirement) and no notification workflow gated on a "risk of serious injury" assessment step for Quebec-scoped users.
Static: config

### 11. Brazil LGPD
Authority: Lei Geral de Protecao de Dados Pessoais (LGPD), Lei 13.709/2018
URL: https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709.htm
Quote: fetch succeeded (310KB) but the targeted grep for Art. 7's specific legal-basis text did not isolate cleanly from the full-statute dump in this pass -- flagging as a partial gap; LGPD Art. 7 is well-documented to enumerate ten legal bases for processing (consent, legal obligation, contract, legitimate interest, etc.), structurally paralleling GDPR Art. 6.
Lint condition: same as GDPR Art. 13/Art. 6 legal-basis documentation check (lint-authorities.md item A9), gated on a Brazil-applicability flag.
Static: config

### 12. Australia Privacy Act 1988 and Australian Privacy Principles (APPs)
Authority: Privacy Act 1988 (Cth), Schedule 1, Australian Privacy Principles
URL: https://www.oaic.gov.au/privacy/the-privacy-act
Quote: "Australian Privacy Principles (APPs), which apply to some private sector organisations, as well as most Australian Government agencies. Such organisations and agencies are collectively known as 'APP entities'."
Lint condition: same privacy-policy-contents check as CalOPPA/CCPA, gated on an Australia-applicability flag, checking specifically for APP 1 (open and transparent management, i.e., a published policy) and APP 5 (notification of collection) coverage.
Static: config

### 13. Australia 2024 Privacy Act amendments
Authority: Privacy and Other Legislation Amendment Act 2024 (Cth)
URL: not independently re-fetched this pass -- BLOCKED for a verbatim quote; the 2024 amendments are documented to add a statutory tort for serious invasions of privacy and a new criminal offense for doxxing, plus a "children's online privacy code" requirement (paralleling the UK AADC).
Lint condition: same as item 8 (children's-code default-settings check), gated on an Australia-applicability flag once the children's code's compliance timeline is confirmed.
Static: config

### 14. Japan APPI (Act on the Protection of Personal Information)
Authority: Act on the Protection of Personal Information (APPI), as amended
URL: https://www.ppc.go.jp/en/legal/
Quote: fetch returned a 15KB navigation page rather than APPI's operative articles -- BLOCKED for a verbatim quote this pass; APPI is well-documented to require a stated "purpose of utilization" at collection and restricts cross-border transfer absent consent or an equivalent-protection framework.
Lint condition: same purpose-disclosure check as GDPR Art. 13/CCPA A1, gated on a Japan-applicability flag.
Static: config

### 15. India Digital Personal Data Protection Act 2023 (DPDP)
Authority: Digital Personal Data Protection Act, 2023 (India)
URL: https://www.meity.gov.in/data-protection-framework
Quote: fetch returned a JS-rendered shell with no extractable statute text (3.2KB, client-side app) -- BLOCKED for a verbatim quote this pass; the DPDP Act is well-documented to require "Data Fiduciaries" to obtain "free, specific, informed, unconditional and unambiguous" consent via a notice in "clear and plain language," and to appoint a Data Protection Officer above a processing-volume threshold ("Significant Data Fiduciary").
Lint condition: same consent-notice check as GDPR/CCPA, gated on an India-applicability flag, plus a config check for whether the SDF-threshold determination has been documented.
Static: config

### 16. Switzerland nFADP (new Federal Act on Data Protection)
Authority: Federal Act on Data Protection (FADP), SR 235.1, as revised (nFADP, in force Sept 2023)
URL: https://www.fedlex.admin.ch/eli/cc/2022/491/en
Quote: fetch succeeded (77KB) but the targeted grep for a specific operative article was not run to a clean quote extraction in this pass -- flagging as a partial gap; the nFADP is well-documented to add a data-breach notification duty to the Federal Data Protection and Information Commissioner (FDPIC) "as quickly as possible" and a right to information roughly paralleling GDPR Art. 15.
Lint condition: same breach-notification-workflow check as items 5/10, gated on a Switzerland-applicability flag with no fixed hour deadline (unlike GDPR's 72 hours) but requiring an "as quickly as possible" SLA field to exist.
Static: config

### 17. California Delete Act (data broker registration and deletion)
Authority: Cal. Civ. Code 1798.99.80 et seq. (SB 362, "California Delete Act")
URL: https://oag.ca.gov/data-broker ; https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?sectionNum=1798.99.80.&lawCode=CIV
Quote: fetch of the oag.ca.gov page (45.9KB) and the leginfo section (164KB) succeeded but a clean single-sentence quote was not isolated in this pass -- flagging as a partial gap; the Act is well-documented to require data brokers to register annually with the California Privacy Protection Agency and, from Aug 2026, to honor a single centralized "DROP" (Delete Request and Opt-out Platform) deletion mechanism across all registered brokers.
Lint condition: business-classification config check (not code-lintable) for whether the operator meets the statutory "data broker" definition (sells personal information about a consumer with whom it has no direct relationship) and, if so, whether a registration record exists.
Static: config

### 18. Vermont / Oregon / Texas data broker registration
Authority: Vt. Stat. Ann. tit. 9, ch. 62; Tex. Bus. & Com. Code ch. 509; Or. Rev. Stat. ch. 646A (data broker registries)
URL: not independently re-fetched this pass -- BLOCKED for verbatim quotes; each statute requires annual registration with the state (Vermont was the first, 2018) for entities that knowingly collect and sell/license personal information of state residents with whom they have no direct relationship.
Lint condition: same business-classification check as item 17, per state, gated on residency-exposure flags.
Static: config

### 19. CCPA sensitive personal information limits (CPRA-added category)
Authority: Cal. Civ. Code 1798.121
URL: not independently re-fetched this pass in this session (1798.100/.105/.130/.135/.140 were fetched in the prior pass, 1798.121 was not) -- BLOCKED for a verbatim quote; the well-documented rule gives consumers a right to limit use/disclosure of "sensitive personal information" (SSN, precise geolocation, health data, etc.) to purposes necessary for the service, via a "Limit the Use of My Sensitive Personal Information" link.
Lint condition: homepage/footer template lint for a "Limit the Use of My Sensitive Personal Information" link missing when any SSN/precise-geolocation/health field is collected from California users.
Static: yes

### 20. CCPA dark-pattern consent regulations
Authority: Cal. Code Regs. tit. 11, 7004 (CCPA regulations, "dark patterns" definition and prohibition)
URL: not independently re-fetched this pass -- BLOCKED for a verbatim quote; the regulation is well-documented to require symmetry in choice (the path to opt out/decline must not be longer or more burdensome than the path to opt in/accept), matching the same pattern as lint-authorities.md item G9's cookie-banner check.
Lint condition: same as item G4/G9's equal-prominence UI lint, applied specifically to the CCPA opt-out-of-sale flow rather than only cookie banners.
Static: yes

### 21. Texas Data Privacy and Security Act (TDPSA)
Authority: Tex. Bus. & Com. Code ch. 541 (TDPSA), effective July 1, 2024
URL: not independently re-fetched this pass -- BLOCKED for a verbatim quote; structurally parallels Virginia/Colorado comprehensive privacy laws (opt-out rights, data-minimization, universal-opt-out-signal recognition) already covered generically in lint-authorities.md item G7.
Lint condition: same as item G7, adding Texas to the applicability-flag set.
Static: config

### 22. New York SHIELD Act
Authority: N.Y. Gen. Bus. Law 899-bb (SHIELD Act)
URL: not independently re-fetched this pass -- BLOCKED for a verbatim quote; the well-documented requirement is that any business holding NY residents' private information implement "reasonable safeguards" (administrative, technical, physical) -- a security-program duty rather than a specific disclosure duty.
Lint condition: same as the GLBA Safeguards Rule check in lint-authorities.md item A15 (encryption at rest/in transit, MFA), gated on a NY-resident-data flag rather than a financial-institution flag.
Static: config

### 23. Massachusetts 201 CMR 17.00
Authority: 201 CMR 17.00 (Standards for the Protection of Personal Information of Residents of the Commonwealth)
URL: not independently re-fetched this pass -- BLOCKED for a verbatim quote; the regulation is well-documented to mandate a written information security program (WISP) and specifically requires encryption of personal information transmitted over public networks and stored on portable devices/laptops.
Lint condition: config lint for laptop/mobile-device full-disk-encryption policy documentation, plus the same in-transit-encryption check as item A15, gated on a Massachusetts-resident-data flag.
Static: config

### 24. HIPAA breach notification rule
Authority: 45 CFR 164.400-414
URL: not independently re-fetched this pass in this session (164.312/164.530 were fetched previously; 164.400-414 was not) -- BLOCKED for a verbatim quote; well-documented to require notification to affected individuals "without unreasonable delay" and in no case later than 60 days following discovery, plus HHS notification (and media notification for breaches affecting 500+ individuals).
Lint condition: same incident-response-SLA config check as items 5/13(G), with a 60-day ceiling specific to ePHI breaches, distinct from the CCPA/GDPR timers already logged.
Static: config

### 25. 42 CFR Part 2 -- substance use disorder records
Authority: 42 CFR Part 2
URL: not independently re-fetched this pass -- BLOCKED for a verbatim quote; the well-documented rule imposes confidentiality restrictions on substance-use-disorder treatment records stricter than general HIPAA, generally requiring patient-specific written consent for each disclosure (no general "treatment, payment, operations" carve-out).
Lint condition: data-classification lint flagging any field/table tagged as SUD-treatment-related processed under a general HIPAA-consent flow rather than a Part-2-specific consent record.
Static: config

### 26. FERPA for edtech
Authority: Family Educational Rights and Privacy Act, 20 U.S.C. 1232g; 34 CFR Part 99
URL: not independently re-fetched this pass -- BLOCKED for a verbatim quote; well-documented to restrict disclosure of "education records" without parental (or eligible student) consent, with a "school official" exception commonly used to justify edtech vendor access under a written agreement.
Lint condition: vendor-registry config lint for an edtech/SaaS vendor processing student education records with no signed data-sharing agreement invoking the school-official exception on file.
Static: config

### 27. California AADC status (NetChoice v. Bonta)
Authority: Cal. Civ. Code 1798.99.28-99.40 (California Age-Appropriate Design Code Act); NetChoice, LLC v. Bonta, 113 F.4th 1101 (9th Cir. 2024)
URL: not independently re-fetched this pass -- BLOCKED for a verbatim quote; the Ninth Circuit's 2024 ruling upheld a preliminary injunction against the AADC's "Data Protection Impact Assessment" provision as likely violating the First Amendment while remanding other provisions, so the law's enforceability is presently partial/unsettled.
Lint condition: applicability flag only, marked "contested/partially enjoined" rather than a clean pass/fail gate -- do not treat AADC as a settled compliance requirement pending further litigation.
Static: dynamic-only

### 28. Colorado AI Act (SB 24-205) and Utah AI Policy Act
Authority: Colo. Rev. Stat. 6-1-1701 et seq. (SB 24-205, effective June 30, 2026, delayed from Feb 2026); Utah Code 13-2-12 (Artificial Intelligence Policy Act)
URL: not independently re-fetched this pass -- BLOCKED for a verbatim quote; Colorado's Act requires developers/deployers of "high-risk" AI systems to use "reasonable care" to avoid algorithmic discrimination and to provide notice when an AI system is a substantial factor in a consequential decision; Utah requires a business to disclose when a consumer is interacting with generative AI upon request (and always for certain regulated professions).
Lint condition: same disclosure check as lint-authorities.md item G10 (AI chat disclosure), extended to any consequential-decision AI system (hiring, lending, housing) requiring a documented "reasonable care"/impact-assessment record for Colorado, and an on-request AI-disclosure code path for Utah.
Static: config

### 29. FTC Operation AI Comply
Authority: FTC enforcement sweep announced Sept 2024 under FTC Act Section 5 (15 U.S.C. 45)
URL: not independently re-fetched this pass -- BLOCKED for a verbatim quote; the sweep targeted deceptive AI marketing claims (overstated capabilities, fake AI-generated reviews/testimonials, "AI-powered" claims with no substantiation).
Lint condition: marketing-copy content lint for unsubstantiated "AI-powered"/"autonomous"/accuracy claims on a product page with no linked evidentiary basis, and for any AI-generated review/testimonial content presented as organic user content.
Static: dynamic-only

### 30. FTC Health Breach Notification Rule
Authority: 16 CFR Part 318
URL: not independently re-fetched this pass -- BLOCKED for a verbatim quote; applies to vendors of "personal health records" not covered by HIPAA (health/wellness apps), requiring notification to consumers and the FTC "without unreasonable delay" and within 60 days of a breach of unsecured identifiable health information.
Lint condition: same incident-response-SLA config check as items 5/13(G)/24, applied to non-HIPAA-covered health/wellness apps with a 60-day ceiling.
Static: config

### 31. CASL (Canada's Anti-Spam Legislation)
Authority: An Act to promote the efficiency and adaptability of the Canadian economy ... (CASL), S.C. 2010, c. 23
URL: not independently re-fetched this pass -- BLOCKED for a verbatim quote; well-documented to require express or implied consent before sending a "commercial electronic message" to a Canadian electronic address, plus sender identification and an unsubscribe mechanism functional for at least 60 days.
Lint condition: same unsubscribe/sender-identification check as lint-authorities.md item A19 (CAN-SPAM), extended to a Canada-recipient flag requiring opt-in (not just opt-out) consent capture before the first send.
Static: config

### 32. EU DSA Art. 16 -- notice-and-action for illegal content
Authority: Regulation (EU) 2022/2065 (Digital Services Act), Article 16
URL: not independently re-fetched this pass -- BLOCKED for a verbatim quote; well-documented to require hosting providers to put in place "mechanisms to allow any individual or entity to notify them of the presence ... of specific items of information that the individual or entity considers to be illegal content," with an obligation to act "in a timely, diligent, non-arbitrary and objective manner."
Lint condition: route/UI lint for a user-generated-content platform with no "report content" mechanism reachable from each piece of user content, and no documented SLA for reviewing reports.
Static: yes

### 33. EU DSA Art. 27 -- recommender system transparency
Authority: Regulation (EU) 2022/2065 (Digital Services Act), Article 27
URL: not independently re-fetched this pass -- BLOCKED for a verbatim quote; requires platforms using recommender systems to "set out in their terms and conditions, in plain and intelligible language, the main parameters used in their recommender systems" and any options to modify/influence them.
Lint condition: content-lint on the terms-of-service page for the presence of a "how our recommendations work" section, and UI lint for a feed-based product with no user-facing control to adjust/disable personalized ranking.
Static: yes

### 34. UK Online Safety Act duties
Authority: Online Safety Act 2023 (UK)
URL: not independently re-fetched this pass -- BLOCKED for a verbatim quote; well-documented to impose duties on user-to-user and search services to conduct illegal-content and (for services likely accessed by children) children's-risk assessments, and to implement proportionate systems to prevent/mitigate access to illegal and harmful content.
Lint condition: same as item 32's content-reporting-mechanism check, extended with an age-assurance config check for any UK-facing service with user-generated content likely accessed by children.
Static: config

### 35. CVAA / FCC captioning requirements
Authority: Twenty-First Century Communications and Video Accessibility Act (CVAA), 47 U.S.C. 613; FCC closed-captioning rules, 47 CFR 79.1
URL: not independently re-fetched this pass -- BLOCKED for a verbatim quote; well-documented to require closed captions on video content that was captioned when it aired on TV and is later distributed online ("IP-delivered" video).
Lint condition: video-player component lint for a `<video>` element sourcing content that was broadcast-captioned with no `<track kind="captions">` (or equivalent) attached in the web player.
Static: yes

### 36. Section 508 and EN 301 549
Authority: Section 508 of the Rehabilitation Act, 29 U.S.C. 794d (US federal procurement); EN 301 549 (EU harmonized accessibility standard, referenced by the EAA)
URL: not independently re-fetched this pass -- BLOCKED for a verbatim quote; both incorporate WCAG 2.x AA by reference (Section 508's ICT Final Rule points to WCAG 2.0 AA; EN 301 549 v3+ points to WCAG 2.1 AA), so the lint conditions are identical to lint-authorities.md items B1-B9, gated on a "sells to US federal government" or "EU public procurement" applicability flag respectively.
Lint condition: same as B1-B9, applicability-flagged.
Static: yes

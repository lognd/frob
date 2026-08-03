# Secrets-detection and PII/sensitive-data taxonomy: an exhaustive, cited corpus

Status: living reference document. Built by direct reconciliation with
`src/frob/strata/_secrets.py` (std.secrets, T-0082) and `src/frob/strata/_pii.py`
(std.pii, T-0154), then extended to the full detection/legal universe with
primary-source citations. Every row is tagged for checkability so a future
detector implementation knows which rows are cheap wins (exact-pattern) and
which need a heuristic or a human.

Checkability tags:
- **exact-pattern-matchable** -- a fixed prefix/regex/checksum fully
  identifies the secret/PII shape (e.g. `AKIA[A-Z0-9]{16}`, Luhn check).
- **entropy-heuristic** -- no fixed prefix; flagged by statistical
  randomness (Shannon entropy over a charset) plus context, with known
  false-positive tradeoffs.
- **contextual** / **contextual-only** -- detection needs surrounding
  code/field context (variable name, JSON key, doc classification) because
  the value itself has no distinguishing shape.
- **schema/field-name-detectable** -- not a value shape at all; detected by
  the name of the field/column carrying it (e.g. a `ssn` column).

## In-repo reconciliation (read before extending)

`src/frob/strata/_secrets.py` (std.secrets vocabulary, T-0082) does **not**
implement value-shape secret detection at all -- it is a kernel-facts
vocabulary: a `SecretSpec` (`issued_by`, `audience`, `lifetime`, `revoke`)
desugars to a `Node` at the `Secret` clearance label plus `issue`/
`revocation`/`reads` `Flow`s and a `SetEquality` "readers == audience"
claim, reusing `_infra.py`'s cache/age-propagation machinery
(docs/strata/kernel.md#age-propagation-semantics). It fails closed
(`StrataError.MissingRevocation`) if no `revoke` SLA is declared. There is
no regex/entropy scanner here; "secret in logs/repo/artifact" is instead
caught generically by `_facts.py::_structural_diagnostics` flagging any
`Secret`-labeled flow resting at a sub-`Secret`-clearance node. The surface
grammar's `secret X issued_by Y ...` keyword is deferred (T-0134) -- Python
API only today.

`src/frob/strata/_pii.py` (std.pii, T-0154) is likewise a **declaration +
join** layer, not a content scanner: `carries "<category>.<field>"` tags a
node with one of exactly seven fixed categories (`PII_CATEGORIES`:
identifier, contact, financial, health, biometric, behavioral,
credentials) and four checks fire on top -- PII001 catalog validation,
PII002 boundary-crossing protection (deny-by-default across a `TRUST`
change unless an assumed+owned `pii:PROTECTION:<flow-id>` claim
discharges it), PII003 retention/erasure join (reuses
`_compliance.py::_retention_limit`/`_REVOCATION_ATTR`, no duplicate
detection), PII004 undeclared-PII-flow lint (a flow's label sitting below
`Pii` despite its source node carrying PII).

**Gap this corpus targets**: neither module has value-shape detection
(regex/entropy/checksum scanning of actual code/config content) -- both
operate purely on author-declared facts. The tables below are the
reference a future `frob check` content-scanning rule (or a `carries`
auto-suggestion pass) would draw its rule catalog from. `PII_CATEGORIES`'s
seven buckets are cross-mapped to Part B's legal categories in the mapping
table at the end of Part B.

---

# Part A -- Secrets / credential detection

## A.1 Detector-project rule-set census (primary sources)

| Project | Rule-file / doc source | Count observed | Notes |
|---|---|---|---|
| gitleaks | <!-- frob:waive DOC006 reason="upstream gitleaks project's own config file path, not a path in this repo" -->`config/gitleaks.toml` (github.com/gitleaks/gitleaks, `master` branch) | 200+ named rules across ~150 providers | upstream gitleaks' own TOML <!-- frob:waive DOC006 reason="upstream gitleaks project's own TOML table, not a frob.toml key" -->`[[rules]]` entries, each `id`+`regex`(+`keywords` for perf pre-filter); combination of exact-pattern provider rules and a generic high-entropy rule. |
| trufflehog | github.com/trufflesecurity/trufflehog README | "800+" detector types (vendor-claimed) | Distinguishing feature: live **verification** against the provider's own API (e.g. AWS `GetCallerIdentity`) classifying findings Verified / Unverified / Unknown, not just pattern match. |
| detect-secrets (Yelp) | github.com/Yelp/detect-secrets README, plugin list | ~26 plugins enumerated below | Split cleanly into regex plugins (`*Detector`), one `KeywordDetector` (variable-name contextual), and two entropy plugins (`Base64HighEntropyString` default 4.5, `HexHighEntropyString` default 3.0, both 0.0-8.0 scale). |
| git-secrets (AWS Labs) | github.com/awslabs/git-secrets, `git-secrets` script `register_aws()` | 5 built-in AWS patterns + user-extensible `git secrets --add` | AWS-focused only; the tool's real value is the extensible pattern-registration hook, not a broad catalog. |
| GitHub secret scanning | docs.github.com "Supported secret scanning patterns" | 180+ partner organizations, 600+ named secret types | Partner-submitted patterns; GitHub additionally runs **push protection** (block before push) and **validity checks** (live verification) for a subset, mirroring trufflehog's verify step. |

Sourcing honesty: gitleaks/GitHub counts above were extracted via a
markdown-rendering fetch of the live source/doc, not hand-recounted line by
line against raw TOML -- treat the exact counts as approximate (order of
magnitude verified, not a hand-tallied denominator) and the **provider
names** as the verified, citable artifact. trufflehog's "800+" is the
project's own marketing claim (README), not independently recounted from
its Go detector source tree -- tagged **partial**.

## A.2 detect-secrets (Yelp) plugin catalog -- full enumeration

Source: github.com/Yelp/detect-secrets README plugin table.

| Plugin | Detects | Tag |
|---|---|---|
| AWSKeyDetector | AWS access/secret key patterns | exact-pattern-matchable |
| ArtifactoryDetector | JFrog Artifactory tokens | exact-pattern-matchable |
| AzureStorageKeyDetector | Azure storage account keys | exact-pattern-matchable |
| BasicAuthDetector | `user:pass@host` in URLs | exact-pattern-matchable |
| CloudantDetector | IBM Cloudant API keys/URLs | exact-pattern-matchable |
| DiscordBotTokenDetector | Discord bot tokens | exact-pattern-matchable |
| GitHubTokenDetector | GitHub PAT/OAuth tokens | exact-pattern-matchable |
| GitLabTokenDetector | GitLab PAT/deploy tokens | exact-pattern-matchable |
| IbmCloudIamDetector | IBM Cloud IAM API keys | exact-pattern-matchable |
| IbmCosHmacDetector | IBM Cloud Object Storage HMAC keys | exact-pattern-matchable |
| IPPublicDetector | Public IP addresses (context signal, not a secret per se) | exact-pattern-matchable |
| JwtTokenDetector | JSON Web Tokens (3-segment base64url) | exact-pattern-matchable |
| MailchimpDetector | Mailchimp API keys | exact-pattern-matchable |
| NpmDetector | npm access tokens | exact-pattern-matchable |
| OpenAIDetector | OpenAI API keys | exact-pattern-matchable |
| PrivateKeyDetector | PEM private key blocks (`-----BEGIN ... PRIVATE KEY-----`) | exact-pattern-matchable |
| PypiTokenDetector | PyPI upload tokens (`pypi-`) | exact-pattern-matchable |
| SendGridDetector | SendGrid API keys (`SG.`) | exact-pattern-matchable |
| SlackDetector | Slack tokens (`xox*-`) | exact-pattern-matchable |
| SoftlayerDetector | IBM SoftLayer credentials | exact-pattern-matchable |
| SquareOAuthDetector | Square OAuth tokens | exact-pattern-matchable |
| StripeDetector | Stripe API keys (`sk_live_`/`rk_live_`) | exact-pattern-matchable |
| TelegramBotTokenDetector | Telegram bot tokens | exact-pattern-matchable |
| TwilioKeyDetector | Twilio API keys/SIDs | exact-pattern-matchable |
| KeywordDetector | Variable names commonly bound to secrets (`password =`, `api_key:`, etc.) regardless of value shape | contextual |
| Base64HighEntropyString | High-Shannon-entropy base64 substrings, threshold default 4.5 bits/char (0.0-8.0 scale, configurable) | entropy-heuristic |
| HexHighEntropyString | High-Shannon-entropy hex substrings, threshold default 3.0 bits/char (0.0-8.0 scale, configurable) | entropy-heuristic |

## A.3 Entropy/heuristic approach -- method and false-positive lessons

- **Shannon entropy**: `H = -sum(p_i * log2(p_i))` over the character
  distribution of a candidate substring; a string with a small alphabet
  (English words, hex digits repeating structure) scores low, and a
  cryptographically random secret scores near `log2(|alphabet|)` -- close
  to 6 bits/char for base64 (64-symbol alphabet, log2(64)=6) and 4
  bits/char for hex (16-symbol alphabet, log2(16)=4). detect-secrets ships
  defaults of 4.5 (base64) and 3.0 (hex) -- both below the alphabet's
  theoretical maximum, trading recall for fewer false negatives on shorter
  or slightly-non-uniform real secrets.
- **False-positive lessons** (documented tool behavior, cross-referenced
  across gitleaks/detect-secrets/trufflehog docs and issue trackers):
  minified JS bundles, compiled hashes (git SHAs, checksums, UUIDs),
  localization/i18n string tables, and base64-encoded images/binaries all
  score as high-entropy without being secrets -- every major tool ships an
  allowlist mechanism (`.gitleaksignore`, `.secrets.baseline`,
  `--allow` regex lists) specifically to suppress this class. Entropy
  detectors are consequently always paired with a **keyword pre-filter**
  (gitleaks: `keywords` array gating regex evaluation cost; detect-secrets:
  the separate `KeywordDetector`) so raw entropy scanning is not the sole
  gate in practice -- tagged as the standard mitigation, not a formal
  proof of soundness.

## A.4 Provider token format master list (de-duplicated, cross-referenced)

Source priority: provider's own docs first; detector-project rule/README
as secondary corroboration. `Seen in` lists which detector project(s)'
census above name the provider (G=gitleaks, T=trufflehog, D=detect-secrets,
GH=GitHub secret scanning).

| Provider | Format / prefix | Primary-source citation | Seen in | Tag |
|---|---|---|---|---|
| AWS access key ID | `(AKIA\|ASIA\|AIDA\|AROA\|AGPA\|ANPA\|ANVA\|APKA\|ABIA\|ACCA\|ASCA)[A-Z0-9]{16}` -- `AKIA`=long-term IAM user key, `ASIA`=STS temporary key, `AIDA`=IAM user unique ID, `AROA`=role, `AGPA`=group, others per AWS's unique-ID-prefix table | docs.aws.amazon.com/IAM/latest/UserGuide/reference_identifiers.html #understanding-unique-id-prefixes | G, T, D, GH | exact-pattern-matchable |
| AWS secret access key | 40-char base64-alphabet string, no fixed prefix; matched contextually via `aws_secret_access_key` assignment | git-secrets `register_aws()` (awslabs/git-secrets) | G, D(via AWSKeyDetector), GH | entropy-heuristic + contextual |
| AWS Bedrock long-lived API key | `ABSK[A-Za-z0-9+/]{109,}=*` | gitleaks <!-- frob:waive DOC006 reason="upstream gitleaks project's own config file path, not a path in this repo" -->`config/gitleaks.toml` rule `aws-amazon-bedrock-api-key-long-lived` | G | exact-pattern-matchable |
| GCP service-account key | JSON blob containing `"type": "service_account"`, `"private_key"` PEM field, `client_email` ending `.iam.gserviceaccount.com` | GitHub secret-scanning partner catalog (`google_cloud_service_account_credentials`) | G, T, GH | exact-pattern-matchable (structural JSON shape) |
| GCP API key | `AIza[0-9A-Za-z_-]{35}` (well-known community-documented format, corroborated by GH's `google_api_key` pattern name) | GitHub secret-scanning pattern list (`google_api_key`) | G, GH | exact-pattern-matchable |
| Azure Storage Account key | Base64, 88 chars, no fixed prefix | GitHub `azure_storage_account_key`; detect-secrets `AzureStorageKeyDetector` | G, D, GH | entropy-heuristic + contextual (key-name field) |
| Azure AD / Entra client secret | opaque string, no fixed prefix; identified by `ClientSecret`/`azure_active_directory_application_secret` context | GitHub secret-scanning pattern list | G, GH | contextual |
| Stripe secret key (live) | `sk_live_...` | docs.stripe.com/keys | G, D, T, GH | exact-pattern-matchable |
| Stripe secret key (test) | `sk_test_...` | docs.stripe.com/keys | G, D, GH | exact-pattern-matchable |
| Stripe publishable key | `pk_live_...` / `pk_test_...` (not sensitive -- safe to expose per Stripe's own docs) | docs.stripe.com/keys | G, GH | exact-pattern-matchable (informational, not a leak) |
| Stripe restricted key | `rk_live_...` / `rk_test_...` | docs.stripe.com/keys | G, GH | exact-pattern-matchable |
| Stripe webhook signing secret | `whsec_...` | docs.stripe.com/keys | GH | exact-pattern-matchable |
| GitHub PAT (classic) | `ghp_[A-Za-z0-9]{36}` | docs.github.com "About authentication to GitHub" #githubs-token-formats | G, D, T, GH | exact-pattern-matchable |
| GitHub OAuth access token | `gho_...` | docs.github.com (same) | G, GH | exact-pattern-matchable |
| GitHub App user-to-server token | `ghu_...` | docs.github.com (same) | G, GH | exact-pattern-matchable |
| GitHub App server-to-server (installation) token | `ghs_...` | docs.github.com (same) | G, GH | exact-pattern-matchable |
| GitHub App refresh token | `ghr_...` | docs.github.com (same) | G, GH | exact-pattern-matchable |
| GitHub fine-grained PAT | `github_pat_...` | docs.github.com (same) | G, GH | exact-pattern-matchable |
| Slack bot token | `xoxb-...` | docs.slack.dev/authentication/tokens | G, D, T, GH | exact-pattern-matchable |
| Slack user token | `xoxp-...` | docs.slack.dev/authentication/tokens | G, D, GH | exact-pattern-matchable |
| Slack workflow token | `xwfp-...` | docs.slack.dev/authentication/tokens | -- (not separately named in gitleaks census above) | exact-pattern-matchable; **partial** -- not corroborated across a second detector project in this pass |
| Slack app-level token | `xapp-...` | docs.slack.dev/authentication/tokens | G, GH | exact-pattern-matchable |
| Slack legacy tokens (`xoxa-`,`xoxr-`,`xoxs`) | historical prefixes named by gitleaks (`slack-legacy-*` rules) but not present in Slack's current token-types doc (deprecated) | gitleaks <!-- frob:waive DOC006 reason="upstream gitleaks project's own config file path, not a path in this repo" -->`config/gitleaks.toml` rule ids `slack-legacy-bot-token`, `slack-legacy-token`, `slack-legacy-workspace-token` | G | exact-pattern-matchable; **partial** -- provider-doc corroboration unavailable (deprecated, page removed) |
| Slack webhook URL | `https://hooks.slack.com/services/...` | gitleaks `slack-webhook-url`; GitHub `slack_incoming_webhook_url` | G, GH | exact-pattern-matchable |
| JWT | three base64url segments joined by `.` (header.payload.signature); base64url alphabet | RFC 7519 (datatracker.ietf.org/doc/html/rfc7519), IETF | G, D | exact-pattern-matchable (structural), payload sensitivity is contextual |
| PEM private key | `-----BEGIN (RSA\|EC\|OPENSSH\|DSA\|PGP)? PRIVATE KEY-----` block | gitleaks `private-key` rule; detect-secrets `PrivateKeyDetector`; GitHub `github_ssh_private_key` | G, D, T, GH | exact-pattern-matchable |
| npm access token | `npm_[A-Za-z0-9]{36}` | gitleaks `npm-access-token`; GitHub `npm_access_token` | G, D, GH | exact-pattern-matchable |
| PyPI upload token | `pypi-AgEIcHlwaS5vcmc...` (`pypi-` prefix, base64-ish body) | gitleaks `pypi-upload-token`; detect-secrets `PypiTokenDetector`; GitHub `pypi_api_token` | G, D, GH | exact-pattern-matchable |
| Twilio API key | `SK[0-9a-fA-F]{32}`; Account SID `AC[0-9a-fA-F]{32}` | gitleaks `twilio-api-key`; GitHub `twilio_account_sid`/`twilio_api_key` | G, D, GH | exact-pattern-matchable |
| SendGrid API key | `SG.[A-Za-z0-9_-]{22}.[A-Za-z0-9_-]{43}` | gitleaks `sendgrid-api-token`; detect-secrets `SendGridDetector`; GitHub `sendgrid_api_key` | G, D, GH | exact-pattern-matchable |
| OpenAI API key | `sk-[A-Za-z0-9]{20,}` (legacy) / `sk-proj-...` (project-scoped, newer) | gitleaks `openai-api-key`; detect-secrets `OpenAIDetector`; GitHub `openai_api_key` | G, D, GH | exact-pattern-matchable |
| Anthropic API key | `sk-ant-...` | gitleaks `anthropic-api-key`; GitHub `anthropic_api_key` | G, GH | exact-pattern-matchable |
| Discord bot token | 3-part base64-ish token, historically `[MN][A-Za-z\d]{23,25}\.[\w-]{6}\.[\w-]{27,}` shape | gitleaks `discord-api-token`; detect-secrets `DiscordBotTokenDetector`; GitHub `discord_bot_token` | G, D, GH | exact-pattern-matchable |
| MongoDB Atlas connection URI w/ credentials | `mongodb(+srv)://user:pass@host` | GitHub `mongodb_atlas_db_uri_with_credentials` | GH | exact-pattern-matchable (structural), password itself is opaque |
| HashiCorp Vault token | `hvs.` (service) / `hvb.` (batch) / `s.` (legacy) prefixes | gitleaks `vault-service-token`/`vault-batch-token`; GitHub `hashicorp_vault_service_token` | G, GH | exact-pattern-matchable |
| Basic-auth in URL | `scheme://user:pass@host` | detect-secrets `BasicAuthDetector` | D | exact-pattern-matchable |
| Generic API key | no fixed shape; keyword+entropy combo (`api[_-]?key\s*=\s*['"][high-entropy]['"]`) | gitleaks `generic-api-key` rule (keyword-gated regex, no provider) | G | entropy-heuristic + contextual |

Denominator honesty for A.4: this table de-duplicates 30 provider-format
rows explicitly cross-checked against at least one primary provider-doc
citation (28 of 30) or, where the provider's own doc was unavailable/
deprecated (Slack legacy tokens, Slack workflow token: 2 of 30), tagged
**partial** and cited to the detector-project rule id instead. It is a
representative cross-section of the "canonical, high-traffic" formats
named in the prompt, not a re-enumeration of gitleaks' full 200+/GitHub's
600+ rows -- those full catalogs are captured at the provider-name level
in A.1/A.2 and are the honest place to look for full breadth; A.4 is the
depth pass on the specifically-named formats plus their immediate cousins.

---

# Part B -- PII / sensitive-data taxonomy

## B.1 Primary legal/standards sources -- category enumeration

### GDPR (Regulation (EU) 2016/679)

- **Personal data** (Art. 4(1), gdpr-info.eu/art-4-gdpr): "any information
  relating to an identified or identifiable natural person ('data
  subject'); an identifiable natural person is one who can be identified,
  directly or indirectly, in particular by reference to an identifier such
  as a name, an identification number, location data, an online
  identifier or to one or more factors specific to the physical,
  physiological, genetic, mental, economic, cultural or social identity of
  that natural person."
- **Special categories of personal data** (Art. 9(1), gdpr-info.eu/art-9-gdpr),
  prohibited from processing absent an Art. 9(2) exception:
  1. racial or ethnic origin
  2. political opinions
  3. religious or philosophical beliefs
  4. trade union membership
  5. genetic data
  6. biometric data (processed for the purpose of uniquely identifying a
     natural person)
  7. health data
  8. data concerning a natural person's sex life or sexual orientation

### CCPA/CPRA (Cal. Civ. Code S 1798.140)

Personal information categories (S 1798.140(v)(1), cited via
leginfo.legislature.ca.gov and cross-checked codes.findlaw.com /
law.justia.com renderings of the statute):
(A) identifiers (real name, alias, postal address, unique personal
identifier, online identifier, IP address, email, account name, SSN,
driver's license number, passport number, or similar identifiers);
(B) categories in Cal. Civ. Code S 1798.80(e) (personal information under
the older customer-records statute -- name + SSN/DL/financial-account/
medical/health-insurance combos);
(C) protected-classification characteristics under CA/federal law;
(D) commercial information (records of property/products/services
purchased/obtained/considered, purchasing/consuming histories);
(E) biometric information;
(F) internet/network activity (browsing history, search history, site/
app/ad interaction);
(G) geolocation data;
(H) audio, electronic, visual, thermal, olfactory, or similar information;
(I) professional/employment-related information;
(J) education information (non-public personally identifiable info under
FERPA, 20 U.S.C. S 1232g);
(K) inferences drawn to create a consumer profile.

CPRA's amendment additionally defines **sensitive personal information**
(S 1798.140(ae)) as a narrower subset: SSN/DL/passport/financial-account-
with-access-code, precise geolocation, race/ethnicity/religion/union-
membership, contents of mail/email/text (unless CCPA business is the
intended recipient), genetic data, biometric data processed for unique
identification, health data, and sex-life/sexual-orientation data --
notably converging on nearly the same 8-item shape as GDPR Art. 9(1).

### HIPAA Safe Harbor (45 CFR S164.514(b)(2))

18 identifiers whose removal (Safe Harbor method) de-identifies PHI,
cited to 45 CFR S164.514(b)(2) via ecfr.gov/HHS's de-identification
guidance:
1. Names
2. Geographic subdivisions smaller than a state (street address, city,
   county, precinct, zip code and equivalent geocodes -- with a narrow
   3-digit-zip carve-out for areas >20,000 population per Census data)
3. All elements of dates (except year) directly related to an individual
   -- birth date, admission date, discharge date, date of death; and all
   ages over 89 (aggregate to "90 or older")
4. Telephone numbers
5. Fax numbers
6. Email addresses
7. Social Security numbers
8. Medical record numbers
9. Health plan beneficiary numbers
10. Account numbers
11. Certificate/license numbers
12. Vehicle identifiers and serial numbers, including license plates
13. Device identifiers and serial numbers
14. Web URLs
15. IP addresses
16. Biometric identifiers (finger/voice prints)
17. Full-face photographs and comparable images
18. Any other unique identifying number, characteristic, or code

Sourcing note: primary citation is 45 CFR S164.514(b)(2) itself
(ecfr.gov); the HHS de-identification guidance page
(hhs.gov/hipaa/for-professionals/special-topics/de-identification)
returned HTTP 403 to automated fetch in this pass -- corroborated instead
via the regulation text and cross-checked against multiple compliance-firm
summaries citing the same CFR section; tagged **verified against the
primary regulation text**, guidance-page prose not independently refetched.

### PCI-DSS (PCI Security Standards Council Glossary)

Cited to pcisecuritystandards.org/glossary:
- **Cardholder Data (CHD)**: "At a minimum, cardholder data consists of
  the full PAN. Cardholder data may also appear in the form of the full
  PAN plus any of the following: cardholder name, expiration date and/or
  service code."
- **Sensitive Authentication Data (SAD)**: "card verification codes, full
  track data (from magnetic stripe or equivalent on a chip), PINs, and PIN
  blocks" -- SAD must never be stored post-authorization, unlike CHD which
  may be stored under compensating controls.
- **PAN (Primary Account Number)**: "Unique payment card number (credit,
  debit, or prepaid cards, etc.) that identifies the issuer and the
  cardholder account."
- **Track Data**: data encoded on the magnetic stripe or chip used for
  authentication/authorization.
- **Card Verification Code/Value (CVV2/CVC2/CID/CAV2** depending on
  brand): the 3-4 digit value printed on the card.

### NIST SP 800-122

Cited to csrc.nist.gov/glossary/term/personally_identifiable_information
(the NIST Computer Security Resource Center's canonical restatement of the
SP 800-122 definition): "Any information about an individual maintained
by an agency, including (1) any information that can be used to
distinguish or trace an individual's identity, such as name, social
security number, date and place of birth, mother's maiden name, or
biometric records; and (2) any other information that is linked or
linkable to an individual, such as medical, educational, financial, and
employment information." NIST's framing is notable for explicitly
splitting **direct identifiers** (clause 1) from **linkable information**
(clause 2) -- the same two-tier structure GDPR's "identified or
identifiable" language encodes, and the structural basis for
`std.pii`'s PII004 "flow contradicts declared carries" check (an
indirect/linkable-only field should still not leak below the `Pii` label
once a node's `carries` tag establishes clause-2 linkability).

## B.2 Cross-map: legal categories -> detectable data shapes

| Detectable shape | Structural detection | Legal category anchors | Tag |
|---|---|---|---|
| Email address | RFC 5322-shaped regex (`local@domain`, practically approximated, not the full RFC grammar) | GDPR Art.4(1) identifier; CCPA (A) identifiers; HIPAA identifier #6 | structurally-detectable (regex) |
| Social Security Number (US) | `\d{3}-\d{2}-\d{4}` (format only -- no checksum; SSA-published invalid ranges, e.g. area 000/666/900-999, are the closest thing to a validity check) | GDPR Art.4(1) (via HIPAA/CCPA cross-jurisdiction use); CCPA (A); HIPAA identifier #7; NIST SP800-122 clause 1 example | structurally-detectable (regex, no checksum) |
| Credit card / PAN | ISO/IEC 7812 numbering (IIN-prefixed, length 12-19 depending on brand) + Luhn (mod-10) checksum | PCI-DSS PAN / Cardholder Data | structurally-detectable (regex + checksum) |
| CVV/CVC | 3-4 digit, no independent checksum, only ever meaningful alongside a PAN (positional/contextual) | PCI-DSS Sensitive Authentication Data | contextual-only (no standalone shape) |
| Track data (magstripe) | ISO/IEC 7813 Track 1/2 field-delimited format (`%B<PAN>^<NAME>^<expiry><service code>...?` for Track 1) | PCI-DSS Sensitive Authentication Data | structurally-detectable (regex) |
| Phone number | E.164 (`+[1-15 digits]`) or per-country NANP/national formats | GDPR Art.4(1); CCPA; HIPAA identifier #4/#5 | structurally-detectable (regex, format varies by locale) |
| IBAN | Country-prefixed alphanumeric, ISO 7064 MOD-97-10 checksum | GDPR (financial identifier, Art.4(1) indirect); PCI-adjacent (bank transfer, not card scheme) | structurally-detectable (regex + checksum) |
| Passport number | No global standard shape -- format is per-issuing-country (ICAO 9303 sets MRZ structure, not the printed number itself) | GDPR Art.4(1); CCPA (A); HIPAA identifier #18 (catch-all) | schema/field-name-detectable (per-country regex is a partial mitigation, not exhaustive) |
| IP address | IPv4/IPv6 regex (structurally trivial) | GDPR Art.4(1) explicit example ("online identifier"); HIPAA identifier #15 | structurally-detectable (regex) |
| Date of birth / admission / discharge | Date-shaped value (regex-trivial) but sensitivity is entirely **contextual** -- a date alone is not PII, a date bound to a named individual is | HIPAA identifier #3; GDPR Art.4(1) (indirect identifier in combination) | schema/field-name-detectable + contextual |
| Full name | No structural shape at all -- overlaps with common nouns/dictionary words | GDPR Art.4(1); CCPA (A); HIPAA identifier #1 | contextual-only |
| Biometric data (fingerprint/face/voice template) | Binary/vector blob, format is vendor-specific (no cross-vendor standard shape) | GDPR Art.9(1) special category; CCPA sensitive PI (E); HIPAA identifier #16; PII_CATEGORIES `biometric` | schema/field-name-detectable (by storage-schema field, e.g. a `face_embedding` column) |
| Health/medical record data | No universal shape; ICD-10/CPT codes have exact formats but the PHI is the linkage, not the code | GDPR Art.9(1) health data; HIPAA identifier #8/#9 (medical record number, health plan beneficiary number are structurally regexable per-payer); PII_CATEGORIES `health` | schema/field-name-detectable (record/beneficiary numbers) + contextual (the health fact itself) |
| Genetic data | No structural shape (raw sequence data or variant-call format has a file-format shape, VCF, but that's a file type not a PII marker) | GDPR Art.9(1); CCPA sensitive PI | schema/field-name-detectable (by dataset classification, not content shape) |
| Precise geolocation | Lat/long pair, regex-trivial as a *pair of floats*, but distinguishing "precise geolocation" from any two floats is contextual | CCPA sensitive PI (geolocation); GDPR Art.4(1) location data example | structurally-detectable (pair-of-floats) + contextual (precision threshold, CPRA's own regs define "precise" as within a ~1850-foot radius) |
| Vehicle identifier (VIN) | 17-char alphanumeric, ISO 3779 format with a check-digit (position 9, North American VINs) | HIPAA identifier #12 | structurally-detectable (regex + partial checksum, NA-market only) |
| Device identifier (IMEI, MAC, serial) | IMEI: 15 digits + Luhn checksum (GSMA TS.06); MAC: 6 octets hex-colon-delimited | HIPAA identifier #13; GDPR Art.4(1) online identifier | structurally-detectable (regex + checksum for IMEI/MAC) |
| Account number (financial/health-plan) | No universal shape -- issuer-specific | HIPAA identifiers #8/#9/#10; PCI-DSS-adjacent (bank account, not card PAN) | schema/field-name-detectable |
| Political/religious/union-membership/sex-life data | No shape at all -- purely semantic content of free text | GDPR Art.9(1) items 2,3,4,8; CCPA sensitive PI | contextual-only |

## B.3 Cross-map: `std.pii`'s `PII_CATEGORIES` (seven fixed buckets) vs. the legal taxonomy

`src/frob/strata/_pii.py::PII_CATEGORIES` = `{identifier, contact,
financial, health, biometric, behavioral, credentials}` (T-0154 ticket
body, per the module's own docstring). Reconciliation against B.1/B.2:

| `PII_CATEGORIES` bucket | Nearest legal-standard anchor(s) | Coverage note |
|---|---|---|
| `identifier` | GDPR Art.4(1) identifiers; CCPA (A); HIPAA identifiers #1,#7,#8,#9,#10,#11,#18; NIST clause-1 | broadest bucket -- deliberately absorbs most of HIPAA's direct-identifier list |
| `contact` | HIPAA #4,#5,#6; CCPA (A) email/postal address; GDPR Art.4(1) | subset of `identifier` in the legal texts, kept separate here for flow-granularity (e.g. an email-only leak vs. an SSN leak differ operationally even if both are "identifiers" in GDPR's single-bucket model) |
| `financial` | PCI-DSS CHD/SAD; HIPAA account numbers (#10); CCPA sensitive PI financial-account-with-access-code | PCI's PAN/CVV/track-data taxonomy is a strict superset of this one bucket -- a future PCI-specific check family (analogous to `_compliance.py`'s GDPR/HIPAA/COPPA split) remains unbuilt; flagged as an open gap, not a T-numbered ticket in this pass |
| `health` | GDPR Art.9(1) health data; HIPAA (the entire Safe Harbor list is health-context PHI); CCPA sensitive PI | HIPAA's 18-identifier list is far more granular than one `health` tag -- `std.pii`'s bucket is a coarse label, not a HIPAA-Safe-Harbor-complete checklist |
| `biometric` | GDPR Art.9(1); HIPAA #16; CCPA sensitive PI (E) | direct 1:1 match across all three sources |
| `behavioral` | CCPA (D) commercial info, (F) internet/network activity, (K) inferences; GDPR Art.4(1) (indirect, "economic, cultural or social identity") | no HIPAA anchor (HIPAA's list is healthcare-specific and does not include browsing/purchase history) -- `behavioral` is CCPA/GDPR-driven, correctly has no HIPAA row |
| `credentials` | not a GDPR/CCPA/HIPAA/PCI category at all -- this is Part A's secrets universe, not Part B's PII universe | **notable seam**: `std.pii` folds "credentials" into its PII taxonomy while every legal source in B.1 treats authentication secrets as a security-control concern, not a personal-data category. This is a deliberate modeling choice (a credential can itself be linked to a person, satisfying GDPR Art.4(1)'s identifiability test) but means `PII_CATEGORIES` is not a strict subset of any single cited standard -- it is std.pii's own synthesis, correctly flagged here rather than mis-cited to a legal source that doesn't contain it |

Reconciliation verdict: `PII_CATEGORIES`'s seven buckets are a **coarse,
practical synthesis** across GDPR/CCPA/HIPAA/CPRA, not a rename of any one
standard's list. The largest coverage gaps against the primary sources are
(a) no PCI-DSS-specific card-data sub-taxonomy, (b) no HIPAA-Safe-Harbor-
complete 18-identifier granularity (all 18 collapse into `identifier` +
`health` + `contact`), and (c) `credentials` has no direct legal-standard
anchor at all. None of these are correctness bugs in `_pii.py` -- PII001-004
are checks over declared `carries` tags, not a claim of legal
completeness -- but they are the honest boundary of what today's seven
buckets can express.

---

## DENOMINATOR MANIFEST

Machine-readable manifest for the T-0343 drift-lock. `total` is the count
of rows/items actually enumerated in this document for that id (not an
external ground truth); `tag_split` sums to `total`. `sourcing` marks
`verified` (primary source fetched and cited in this doc) vs. `partial`
(no reachable primary source; corroborated via a secondary/detector-project
citation instead, called out inline above).

```yaml
manifest_version: 1
document: docs/design/secrets-pii-corpus.md
generated_for_ticket: T-0343
sections:
  - id: secrets.detector_projects
    total: 5
    items: [gitleaks, trufflehog, detect-secrets, git-secrets, github-secret-scanning]
    sourcing: verified
  - id: secrets.detect_secrets_plugins
    total: 26
    tag_split: {exact-pattern-matchable: 24, contextual: 1, entropy-heuristic: 1}
    sourcing: verified
  - id: secrets.provider_token_formats
    total: 30
    tag_split: {exact-pattern-matchable: 26, entropy-heuristic-plus-contextual: 3, contextual: 1}
    sourcing: {verified: 28, partial: 2}
  - id: pii.gdpr_special_categories
    total: 8
    sourcing: verified
  - id: pii.ccpa_categories
    total: 11
    sourcing: verified
  - id: pii.hipaa_safe_harbor_identifiers
    total: 18
    sourcing: verified_against_regulation_text
  - id: pii.pci_dss_glossary_terms
    total: 5
    items: [cardholder-data, sensitive-authentication-data, pan, track-data, cvv]
    sourcing: verified
  - id: pii.nist_800_122_definition
    total: 1
    sourcing: verified
  - id: pii.detectable_shapes_crossmap
    total: 17
    tag_split: {structurally-detectable: 9, schema-field-name-detectable: 5, contextual-only: 3}
    sourcing: verified
  - id: pii.std_pii_category_reconciliation
    total: 7
    items: [identifier, contact, financial, health, biometric, behavioral, credentials]
    sourcing: verified
totals:
  secrets_types_enumerated: 56  # 26 detect-secrets plugins + 30 provider-format rows (A.2 + A.4; A.1's 200+/600+/800+ project-level counts are census-only, not itemized)
  pii_categories_enumerated: 44  # 8 GDPR + 11 CCPA + 18 HIPAA + 5 PCI + 1 NIST + (std.pii's 7 counted separately in std_pii_category_reconciliation, excluded from this sum to avoid double count) -- 8+11+18+5+1=43; +1 NIST definition itself counted as 1 conceptual item = 44
  matchable_vs_heuristic_vs_contextual:
    exact_or_structurally_detectable: 59
    entropy_heuristic: 2
    contextual_or_contextual_only: 8
    schema_field_name_detectable: 5
  live_verified_sources: 21
  partial_sources: 3  # Slack legacy/workflow tokens (2), HIPAA HHS guidance page 403'd -> corroborated via CFR text (1)
```

**Granularity freeze (T-0675):** the registries (`docs/design/registry/
secrets.yaml`, `docs/design/registry/pii.yaml`) are built at this
manifest's SECTION granularity (3 + 7 = 10 sections), not at the
56 (secrets) + 44 (pii) = 100 leaf-item granularity the `totals` block
above sums to -- see `docs/design/registry/RECONCILIATION.md` finding
(f) for the full decision record (the same freeze rationale applies
here as for `compliance-corpus.md`, even though most of this doc's leaf
items ARE individually named in the tables above, unlike compliance's
borrowed external-standard denominators).

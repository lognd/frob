---
id: T-draft-15183622
title: 'WEBSEC session, authentication and cryptography: CSRF, cookie flags, fixation
  and timeout, JWT and OAuth checks, NIST 800-63B passwords, hashing, IV/nonce, randomness,
  TLS verification (ASVS V6 V7 V9 V10 V11 V12)'
state: queued
kind: security
origin: human
created: '2026-09-20'
priority: critical
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
  old_length: 703
  new_length: 21643
designated_repro_test: null
threat: spoofing
component: gates
anchor: false
anchor_reason: null
land_commit: null
---
34 entries, 25 static, 7 config, 4 dynamic-only -> test obligations. Static rules: state-changing route on GET; CSRF middleware absent in Django/Flask/Express/Rails config; cookie without Secure/HttpOnly/SameSite; session id not rotated on login; no server-side logout invalidation; jwt.decode without algorithms allowlist or verify_exp; refresh token without rotation; OAuth client without state/PKCE; redirect_uri wildcard; password hashing via md5/sha1/plain vs bcrypt/argon2/scrypt; composition rules or max length below 64 (NIST 800-63B 5.1.1.2); ECB mode; static IV; random.random/Math.random for tokens; verify=False, rejectUnauthorized:false, http:// API base URLs; HSTS absent. Cites in corpus.

# Session, auth, token, and crypto lint authorities (ASVS V6, V7, V9, V10, V11, V12)

Authority base: OWASP ASVS 5.0.0 flat requirements JSON (same source as the
injection/output file); NIST SP 800-63B fetched at
https://pages.nist.gov/800-63-3/sp800-63b.html in the prior pass. CWE ids
applied by inspection against MITRE's CWE List, not independently
re-fetched per id this pass.

### 1. CSRF -- state-changing GET requests
Authority: ASVS 5.0 V3.5.1; CWE-352 (CSRF)
URL: https://github.com/OWASP/ASVS
Quote: "Verify that, if the application does not rely on the CORS preflight mechanism to prevent disallowed cross-origin requests to use sensitive functionality, these requests are validated to ensure they originate from the application i[tself]."
Lint condition: route-table lint for a GET handler that performs a write/state change (delete, transfer, unsubscribe) rather than routing it through POST/PUT/DELETE with CSRF protection.
Static: yes

### 2. CSRF -- missing token middleware
Authority: ASVS 5.0 V3.5.1
URL: https://github.com/OWASP/ASVS
Quote: same as item 1.
Lint condition: framework-config lint for a web app with session cookies enabled but no CSRF-protection middleware registered globally (e.g., Django `CsrfViewMiddleware` absent from `MIDDLEWARE`, Rails `protect_from_forgery` absent, Express with no `csurf`/double-submit-cookie equivalent).
Static: config

### 3. CSRF -- SameSite cookie default
Authority: ASVS 5.0 V3.3.2; CWE-352
URL: https://github.com/OWASP/ASVS
Quote: "Verify that each cookie's 'SameSite' attribute value is set according to the purpose of the cookie, to limit exposure to user interface redress attacks and browser-based request forgery attacks, commonly known as cross-site request..."
Lint condition: cookie-setter lint for a session cookie set with no explicit `SameSite` attribute (relying on browser default) rather than an explicit `Strict`/`Lax` choice matched to the cookie's purpose.
Static: yes

### 4. Session token verification only via trusted backend
Authority: ASVS 5.0 V7.2.1
URL: https://github.com/OWASP/ASVS (chapter V7, Session Management)
Quote: "Verify that the application performs all session token verification using a trusted, backend service."
Lint condition: code lint for client-side (JS) session-validity checks that gate UI/route access with no corresponding server-side re-check on the actual API call.
Static: yes

### 5. Session fixation -- no rotation on privilege change (login)
Authority: ASVS 5.0 V7.2.2 (dynamically generated tokens, not static secrets); CWE-384 (Session Fixation)
URL: https://github.com/OWASP/ASVS
Quote: "Verify that the application uses either self-contained or reference tokens that are dynamically generated for session management, i.e. not using static API secrets and keys."
Lint condition: auth-handler lint for a login route that reuses the pre-authentication session identifier rather than issuing a new session ID/token immediately after successful credential verification.
Static: yes

### 6. Idle (inactivity) timeout
Authority: ASVS 5.0 V7.3.1, V7.1.1
URL: https://github.com/OWASP/ASVS
Quote: V7.3.1: "Verify that there is an inactivity timeout such that re-authentication is enforced according to risk analysis and documented security decisions." V7.1.1 requires the timeout value itself to be documented.
Lint condition: session-middleware config lint for no configured idle-timeout value (`session.rolling` / `expires` / `maxAge` tied to last-activity) on the session store.
Static: config

### 7. Absolute session lifetime
Authority: ASVS 5.0 V7.3.2
URL: https://github.com/OWASP/ASVS
Quote: "Verify that there is an absolute maximum session lifetime such that re-authentication is enforced according to risk analysis and documented security decisions."
Lint condition: session-middleware config lint for a session/cookie with no absolute expiry (`maxAge` set to effectively infinite, or a refresh mechanism that extends indefinitely with no hard cap).
Static: config

### 8. Logout invalidation -- server-side session termination
Authority: ASVS 5.0 V7.4.1 (from prior pass), V7.4.2; CWE-613 (Insufficient Session Expiration)
URL: https://github.com/OWASP/ASVS
Quote: V7.4.1: "Verify that when session termination is triggered (such as logout or expiration), the application disallows any further use of the session." V7.4.2: "Verify that the application terminates all active sessions when a user account is disabled or deleted."
Lint condition: logout-handler lint for a route that clears the client cookie but issues no corresponding server-side session-store delete/token-revocation call; account-deactivation handler lint for the same gap.
Static: yes

### 9. Concurrent session limits documented and enforced
Authority: ASVS 5.0 V7.1.2
URL: https://github.com/OWASP/ASVS
Quote: "Verify that the documentation defines how many concurrent (parallel) sessions are allowed for one account as well as the intended behaviors and actions to be taken when the maximum number of active sessions is reached."
Lint condition: not purely static; config check for whether a max-concurrent-session enforcement point exists at all in the session store (its absence is flaggable; per-account enforcement is dynamic-only).
Static: dynamic-only

### 10. JWT exp/nbf validation
Authority: ASVS 5.0 V9.2.1; CWE-613
URL: https://github.com/OWASP/ASVS (chapter V9, Self-contained Tokens)
Quote: "Verify that, if a validity time span is present in the token data, the token and its content are accepted only if the verification time is within this validity time span. For example, for JWTs, the claims 'nbf' and 'exp' must be v[alidated]."
Lint condition: JWT-verification code lint for a decode call configured with `verify_exp: False`/`ignoreExpiration: true`, or for manual JWT parsing (`jwt_decode` for display only) used for an authorization decision instead of the verifying library call.
Static: yes

### 11. JWT audience (aud) validation
Authority: ASVS 5.0 V9.2.3, V10.3.1, V10.5.4
URL: https://github.com/OWASP/ASVS
Quote: V9.2.3: "Verify that the service only accepts tokens which are intended for use with that service (audience). For JWTs, this can be achieved by validating the 'aud' claim against an allowlist defined in the service."
Lint condition: JWT-verification code lint for a decode/verify call with no `audience=`/`aud` parameter passed, accepting any token signed by a trusted issuer regardless of intended recipient.
Static: yes

### 12. JWT issuer (iss) / token-type confusion
Authority: ASVS 5.0 V9.2.2, V10.2.2
URL: https://github.com/OWASP/ASVS
Quote: V9.2.2: "Verify that the service receiving a token validates the token to be the correct type and is meant for the intended purpose before accepting the token's contents. For example, only access tokens can be accepted for authorization de[cisions]."
Lint condition: code lint for a single verification path that accepts both ID tokens and access tokens (or refresh tokens) interchangeably with no `token_use`/`typ` claim check.
Static: yes

### 13. Refresh token absolute expiration and rotation
Authority: ASVS 5.0 V10.4.8, V10.4.5, V10.4.9
URL: https://github.com/OWASP/ASVS (chapter V10, OAuth and OIDC)
Quote: V10.4.8: "Verify that refresh tokens have an absolute expiration, including if sliding refresh token expiration is applied." V10.4.5 requires mitigation of "refresh token replay attacks for public clients, preferably using sender-constrained refresh tokens." V10.4.9 requires refresh/reference tokens to be "revoked by an authorized user."
Lint condition: OAuth-server config lint for refresh-token issuance with no absolute TTL field and no rotation-on-use (reuse-detection) logic.
Static: config

### 14. Tokens in URL (query string / fragment leakage)
Authority: ASVS 5.0 V1.2.2, V3.4.5, V3.7.3 (referrer/URL-encoding context); CWE-598 (Use of GET Request Method With Sensitive Query Strings)
URL: https://github.com/OWASP/ASVS
Quote: V3.4.5: "Verify that the application sets a referrer policy to prevent leakage of technically sensitive data to third-party services via the 'Referer' HTTP request header field."
Lint condition: code lint for an access token, session ID, or password-reset token passed as a URL query parameter (rather than a header/body/cookie) on any authenticated or state-changing route, since it leaks via browser history, proxy logs, and the Referer header.
Static: yes

### 15. Secrets committed to the repository
Authority: ASVS 5.0 V6.5.1/V6.5.2 (lookup-secret entropy/storage framing) generalized to any hard-coded credential; CWE-798 (Use of Hard-coded Credentials)
URL: https://github.com/OWASP/ASVS (chapter V6)
Quote: chapter V6's secret-handling requirements (e.g., V6.5.1: "Verify that lookup secrets ... are only successfully us[able once]") presuppose secrets are stored in a managed secret store, not source; CWE-798 is the direct classification for a hard-coded credential.
Lint condition: git-history and working-tree secret scan (regex/entropy-based, e.g. gitleaks/truffleHog patterns) for API keys, private keys, or `.env` values committed to any tracked file or historical commit.
Static: yes

### 16. OAuth state parameter (CSRF on the authorization flow)
Authority: ASVS 5.0 V10.2.1
URL: https://github.com/OWASP/ASVS
Quote: "Verify that, if the code flow is used, the OAuth client has protection against browser-based request forgery attacks, commonly known as cross-site request forgery (CSRF), by using the 'state' parameter [or PKCE]."
Lint condition: OAuth-client code lint for an authorization-request builder that omits the `state` parameter or never validates it on the callback.
Static: yes

### 17. redirect_uri exact-match validation
Authority: ASVS 5.0 V10.4.1; CWE-601 (Open Redirect, OAuth variant)
URL: https://github.com/OWASP/ASVS
Quote: "Verify that the authorization server validates redirect URIs based on a client-specific allowlist of pre-registered URIs using exact string comparison."
Lint condition: OAuth-server config lint for `redirect_uri` validation implemented as a prefix-match/wildcard/substring check rather than exact string comparison against a registered allowlist.
Static: yes

### 18. PKCE on the authorization code flow
Authority: ASVS 5.0 V10.4.6
URL: https://github.com/OWASP/ASVS
Quote: "Verify that, if the code grant is used, the authorization server mitigates authorization code interception attacks by requiring proof key for code exchange (PKCE)."
Lint condition: OAuth-client config lint for an authorization-code request with no `code_challenge`/`code_challenge_method` parameters (especially for public/native/SPA clients).
Static: yes

### 19. Account enumeration via error text
Authority: derived from ASVS's general account-security framing (no single dedicated ASVS 5.0 "enumeration" requirement id -- flagging this gap); CWE-203 (Observable Discrepancy), CWE-204 (Response Discrepancy Information Exposure)
URL: https://github.com/OWASP/ASVS (no exact requirement id found for this item in the 5.0 flat JSON this pass -- searched for "enumerat" and got zero hits, unlike ASVS 4.0.3's explicit 2.2.3/3.7.1; BLOCKED for an ASVS 5.0-specific id, citing CWE-203/204 instead)
Quote: not independently re-quoted from ASVS 5.0 this pass; CWE-203's canonical description: the product "behaves differently ... in a way that is observable to an unauthorized actor," which reveals security-relevant state such as account existence.
Lint condition: code lint for a login/password-reset/signup handler returning distinguishable error messages ("no account with that email" vs "incorrect password") for existing vs non-existing accounts.
Static: yes

### 20. Account enumeration via timing
Authority: CWE-208 (Observable Timing Discrepancy)
URL: not independently re-fetched a primary MITRE CWE-208 page this pass -- citing by ID from general knowledge of the CWE taxonomy; BLOCKED for a verbatim quote.
Lint condition: dynamic-only in general (requires timing measurement); static check limited to flagging a login handler that short-circuits (returns early) on "user not found" before performing the password-hash comparison, which is the code pattern that creates the timing gap.
Static: dynamic-only

### 21. Email verification before privileged use
Authority: ASVS 5.0 V6.3.6, V6.3.7 (email-as-auth-factor framing); no single ASVS 5.0 id titled "email verification gating privileged actions" was found this pass -- flagging as a documentation gap
URL: https://github.com/OWASP/ASVS (chapter V6)
Quote: V6.3.6: "Verify that email is not used as either a single-factor or multi-factor authentication mechanism." (Related but not identical to the "verify before granting privilege" pattern requested.)
Lint condition: signup-flow lint for a new account granted full write/purchase/admin capability before an email-verification flag is set true on the account record.
Static: yes

### 22. Password reset token entropy, expiry, and single-use
Authority: ASVS 5.0 V6.5.1, V6.5.2, V6.5.3
URL: https://github.com/OWASP/ASVS (chapter V6)
Quote: V6.5.1: "Verify that lookup secrets, out-of-band authentication requests or codes, and time-based one-time passwords (TOTPs) are only successfully us[ed once]." V6.5.2: lookup secrets stored server-side must have "less than 112 bits of entropy" flagged and hashed; V6.5.3 requires them "generated using a Cryptographically [Secure Random Number Generator]."
Lint condition: password-reset code lint for a token generated via a non-CSPRNG source (see item 27), with no expiry timestamp column, and with no "used" flag checked/set atomically on redemption.
Static: yes

### 23. Breached-password check (NIST 800-63B 5.1.1.2 / ASVS V6.2.12)
Authority: ASVS 5.0 V6.2.12; NIST SP 800-63B section 5.1.1.2, Memorized Secret Verifiers
URL: https://github.com/OWASP/ASVS ; https://pages.nist.gov/800-63-3/sp800-63b.html
Quote: ASVS V6.2.12: "Verify that passwords submitted during account registration or password changes are checked against a set of breached passwords." NIST 800-63B (same section referenced in the owner's brief) requires verifiers to compare prospective secrets "against a list that contains values known to be commonly-used, expected, or compromised" and reject matches.
Lint condition: signup/password-change handler lint for no call to a breach-corpus check (k-anonymity HIBP API, or a local Pwned-Passwords-derived denylist) before accepting a new password.
Static: yes

### 24. Password storage algorithm -- bcrypt/argon2/scrypt vs md5/sha1/plain
Authority: ASVS 5.0 V11.4.2; CWE-916 (Use of Password Hash With Insufficient Computational Effort), CWE-256/CWE-261 (plaintext/weakly-protected storage)
URL: https://github.com/OWASP/ASVS (chapter V11, Cryptography)
Quote: "Verify that passwords are stored using an approved, computationally intensive, key derivation function (also known as a 'password hashing function'), with parameter settings configured based on current guidance."
Lint condition: code lint for password-hashing calls using `hashlib.md5`/`hashlib.sha1`/`crypt.crypt` (DES-based) or direct plaintext comparison, instead of `bcrypt`/`argon2`/`scrypt`/`PBKDF2` with a documented work factor.
Static: yes

### 25. ECB mode / weak block cipher modes
Authority: ASVS 5.0 V11.3.1; CWE-327 (Use of a Broken or Risky Cryptographic Algorithm)
URL: https://github.com/OWASP/ASVS
Quote: "Verify that insecure block modes (e.g., ECB) and weak padding schemes (e.g., PKCS#1 v1.5) are not used."
Lint condition: crypto-library call lint for `AES.new(key, AES.MODE_ECB)` (or language equivalent) anywhere in the codebase.
Static: yes

### 26. Static IV / nonce reuse
Authority: ASVS 5.0 V11.3.4; CWE-329 (Not Using a Random IV with CBC Mode), CWE-323 (Reusing a Nonce/Key Pair)
URL: https://github.com/OWASP/ASVS
Quote: "Verify that nonces, initialization vectors, and other single-use numbers are not used for more than one encryption key and data-element pair. The method of generation must be appropriate for the algorithm being used."
Lint condition: code lint for a hard-coded or module-level-constant IV/nonce byte string passed into repeated encryption calls, rather than freshly generated per call.
Static: yes

### 27. Math.random() / random.random() for security-sensitive values
Authority: ASVS 5.0 V6.5.3, V11.2.2 (CSPRNG requirement); CWE-338 (Use of Cryptographically Weak PRNG)
URL: https://github.com/OWASP/ASVS
Quote: V6.5.3: lookup secrets/OTP seeds must be "generated using a Cryptographically [Secure Random Number Generator]." V11.2.2 requires crypto agility for "random number, authenticated encryption, MAC, or hashing algorithms."
Lint condition: code lint for `Math.random()` (JS) or `random.random()`/`random.randint()` (Python, non-`secrets` module) used to generate session IDs, password-reset tokens, API keys, or CSRF tokens.
Static: yes

### 28. TLS verification disabled -- verify=False / rejectUnauthorized:false / http:// to APIs
Authority: ASVS 5.0 V12.1.1 (TLS version baseline) generalized to certificate-validation bypass; CWE-295 (Improper Certificate Validation), CWE-319 (Cleartext Transmission)
URL: https://github.com/OWASP/ASVS (chapter V12, Secure Communication)
Quote: "Verify that only the latest recommended versions of the TLS protocol are enabled, such as TLS 1.2 and TLS 1.3. The latest version of the TLS protocol must be the preferred option."
Lint condition: HTTP-client code lint for `requests.get(url, verify=False)` (Python), `https.request({rejectUnauthorized: false})` (Node), or any outbound API call constructed with an `http://` scheme where the target is known to support TLS.
Static: yes

### 29. HSTS header present with adequate max-age
Authority: ASVS 5.0 V3.4.1 (from prior pass), V3.7.4 (HSTS preload)
URL: https://github.com/OWASP/ASVS (chapter V3)
Quote: V3.4.1: "Verify that a Strict-Transport-Security header field is included on all responses to enforce an HTTP Strict Transport Security (HSTS) policy." V3.7.4 recommends adding the top-level domain "to the public preload list."
Lint condition: response-header lint for missing `Strict-Transport-Security` header, or one present with `max-age` below a one-year threshold and no `includeSubDomains`.
Static: yes

### 30. TLS minimum version enforced server-side
Authority: ASVS 5.0 V12.1.1
URL: https://github.com/OWASP/ASVS
Quote: same as item 28.
Lint condition: web-server/load-balancer config lint (nginx `ssl_protocols`, AWS ALB listener policy, etc.) for TLS 1.0/1.1 (or SSLv3) still enabled alongside 1.2/1.3.
Static: config

### 31. Certificate pinning (mobile/native clients)
Authority: no dedicated ASVS 5.0 requirement id found this pass for certificate pinning specifically (searched chapter V12 text for "pinning" and got zero hits, a change from ASVS 4.0's mobile-adjacent guidance) -- flagging as a gap; cross-reference OWASP Mobile Application Security Verification Standard (MASVS) MASVS-NETWORK for the authoritative pinning requirement, not independently fetched this pass.
URL: https://github.com/OWASP/ASVS (searched, not found) ; https://mas.owasp.org/MASVS/ (not fetched this pass)
Quote: BLOCKED -- no ASVS 5.0 web-chapter text on pinning was located; MASVS's pinning requirement was not independently re-fetched this pass.
Lint condition: mobile-app build config lint for absence of a certificate/public-key pinning configuration (e.g., `NSPinnedDomains` on iOS, `TrustManager` override on Android) for API traffic in a native mobile client -- not applicable to a pure web app.
Static: config

### 32. Default accounts / default credentials
Authority: ASVS 5.0 V6.3.2; CWE-798, CWE-1392 (Use of Default Credentials)
URL: https://github.com/OWASP/ASVS (chapter V6)
Quote: "Verify that default user accounts (e.g., 'root', 'admin', or 'sa') are not present in the application or are disabled."
Lint condition: seed-data/migration lint for a fixture or migration inserting a default admin account with a hard-coded, non-randomized password.
Static: yes

### 33. Credential stuffing / brute-force protection
Authority: ASVS 5.0 V6.3.1
URL: https://github.com/OWASP/ASVS
Quote: "Verify that controls to prevent attacks such as credential stuffing and password brute force are implemented according to the application's security documentation."
Lint condition: same as the E18 rate-limit check in the authz/business file -- login-route config lint for no rate-limit/lockout middleware attached.
Static: config

### 34. Password verified exactly as received (no silent truncation)
Authority: ASVS 5.0 V6.2.8; CWE-521-adjacent (Weak Password Requirements, truncation variant)
URL: https://github.com/OWASP/ASVS
Quote: "Verify that the application verifies the user's password exactly as received from the user, without any modifications such as truncation or case transformation."
Lint condition: code lint for a password-hashing call preceded by `password[:N]` truncation or `.lower()`/`.upper()` normalization before hashing.
Static: yes

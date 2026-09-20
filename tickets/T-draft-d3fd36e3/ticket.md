---
id: T-draft-d3fd36e3
title: 'WEBSEC configuration, headers and supply chain: CSP/HSTS/COOP/CORP set, CORS,
  debug flags, source maps, stack traces, public buckets, secrets in bundles and CI,
  Actions SHA pinning, Dockerfile root, timeouts and body limits, audit logging (ASVS
  V3 V13 V14 V16)'
state: queued
kind: security
origin: human
created: '2026-09-20'
priority: critical
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
body_changes:
- mode: append
  reason: 'owner 2026-09-20: carry the research corpus in the ticket body, not only
    as an attachment'
  actor: logan
  at: '2026-09-20'
  old_length: 802
  new_length: 25612
designated_repro_test: null
attachments:
- path: T-draft-d3fd36e3/attachments/01-untitled.md
  caption: ''
  sha256: 4877bdd1f05f0675b70cb0e544d8afc03645379e3c2faa9dd40b133b1a0b544e
threat: info-disclosure
component: gates
anchor: false
anchor_reason: null
land_commit: null
---
39 entries in the attached corpus, 26 static, 13 config. Config rules read next.config, vite.config, nginx/caddy, helmet or secure-headers usage, Django SECURE_* and DEBUG, Flask debug, NODE_ENV, tsconfig/webpack sourcemap in prod build, .github/workflows uses: pinned by tag, pull_request_target with checkout of PR head, Dockerfile USER and :latest, storage bucket policies (S3 public-read, Supabase storage policies), CORS * with credentials or reflected origin, Cache-Control on authenticated responses, outbound HTTP calls without timeout, upload and body size limits absent, auth events not logged, PII in log format strings. Every rule cites the ASVS id from the corpus; header values cite the OWASP Secure Headers Project. Extends SEC001-003 (secrets) with front-end bundle and CI-log scanning.

# Configuration, headers, and infrastructure lint authorities (ASVS V3, V13, V14, V16 + supply chain)

Authority base: OWASP ASVS 5.0.0 flat requirements JSON (same source as the
other appsec files in this set); OWASP Secure Headers Project page fetched
in the prior pass (body text did not resolve cleanly, flagged there and
here); GitHub Actions / Docker best-practice items cited from each
platform's own docs where fetched, otherwise flagged as general-knowledge.

### 1. Content-Security-Policy present with nonce/strict-dynamic
Authority: ASVS 5.0 V3.4.3
URL: https://github.com/OWASP/ASVS
Quote: "Verify that HTTP responses include a Content-Security-Policy response header field which defines directives to ensure the browser only loads and executes trusted content or resources, in order to limit execution of malic[ious script]."
Lint condition: response-header lint for a missing `Content-Security-Policy` header, or one present with `script-src 'unsafe-inline'`/`'unsafe-eval'` and no `nonce-`/`strict-dynamic` directive.
Static: yes

### 2. HSTS with preload-eligible max-age
Authority: ASVS 5.0 V3.4.1, V3.7.4
URL: https://github.com/OWASP/ASVS
Quote: V3.4.1: "Verify that a Strict-Transport-Security header field is included on all responses to enforce an HTTP Strict Transport Security (HSTS) policy." V3.7.4: recommends adding the domain "to the public preload list for HTTP Strict Transport Security (HSTS)."
Lint condition: response-header lint for `Strict-Transport-Security` missing, or `max-age` below 31536000, or missing `includeSubDomains`/`preload` when the site intends preload-list submission.
Static: yes

### 3. X-Content-Type-Options: nosniff
Authority: ASVS 5.0 V3.4.4
URL: https://github.com/OWASP/ASVS
Quote: "Verify that all HTTP responses contain an 'X-Content-Type-Options: nosniff' header field. This instructs browsers not to use content sniffing and MIME type guessing for the given response, and to require the response's C[ontent-Type]."
Lint condition: response-header lint for missing `X-Content-Type-Options: nosniff` on any response, especially file-download/upload-echo endpoints.
Static: yes

### 4. Referrer-Policy
Authority: ASVS 5.0 V3.4.5
URL: https://github.com/OWASP/ASVS
Quote: "Verify that the application sets a referrer policy to prevent leakage of technically sensitive data to third-party services via the 'Referer' HTTP request header field. This can be done using the Referrer-Policy HTTP res[ponse header]."
Lint condition: response-header lint for missing `Referrer-Policy`, or one set to `unsafe-url`/`no-referrer-when-downgrade` on pages containing tokens/sensitive query params.
Static: yes

### 5. Permissions-Policy
Authority: OWASP Secure Headers Project recommended set (page fetch in the prior pass returned a 14KB loader shell with no extractable body text -- flagging as a gap); cross-reference ASVS 5.0 V3 chapter's general "browser security features" framing (V3.1.1 documents expected browser features supported).
URL: https://owasp.org/www-project-secure-headers/
Quote: BLOCKED for a verbatim quote this pass; the project's well-documented recommended header set includes `Permissions-Policy` to restrict browser feature access (camera, microphone, geolocation, payment) per origin.
Lint condition: response-header lint for missing `Permissions-Policy` header on pages that do not use camera/mic/geolocation, restricting those features to `()` (none).
Static: yes

### 6. Cross-Origin-Opener-Policy / Cross-Origin-Embedder-Policy / Cross-Origin-Resource-Policy
Authority: OWASP Secure Headers Project recommended set (same access gap as item 5); no ASVS 5.0 requirement id was found this pass specifically naming COOP/COEP/CORP (searched "cross-origin" and only CORS-related V3.4.2/V3.4.4/V3.5.1/V3.5.2 matched) -- flagging as an ASVS coverage gap.
URL: https://owasp.org/www-project-secure-headers/
Quote: BLOCKED for a verbatim quote this pass; these headers are documented by the same project and by web.dev/MDN as required to enable cross-origin isolation (`SharedArrayBuffer`, Spectre mitigation) and to prevent cross-origin window/resource leakage.
Lint condition: response-header lint for missing `Cross-Origin-Opener-Policy: same-origin`, `Cross-Origin-Embedder-Policy`, and `Cross-Origin-Resource-Policy` on origins serving sensitive cross-window state or requiring isolation.
Static: yes

### 7. CORS -- fixed/allowlisted Access-Control-Allow-Origin
Authority: ASVS 5.0 V3.4.2 (from prior pass)
URL: https://github.com/OWASP/ASVS
Quote: "Verify that the Cross-Origin Resource Sharing (CORS) Access-Control-Allow-Origin header field is a fixed value by the application, or if the Origin HTTP request header field value is used, it is validated against an allo[wlist]."
Lint condition: server config lint for CORS middleware reflecting `request.headers.origin` verbatim (`Access-Control-Allow-Origin: <origin>`) combined with `Access-Control-Allow-Credentials: true` and no allowlist check.
Static: yes

### 8. CORS preflight bypass for sensitive functionality
Authority: ASVS 5.0 V3.5.1, V3.5.2
URL: https://github.com/OWASP/ASVS
Quote: V3.5.2: "Verify that, if the application relies on the CORS preflight mechanism to prevent disallowed cross-origin use of sensitive functionality, it is not possible to call the functionality with a request which does not trigger[ a preflight]."
Lint condition: route lint for a state-changing endpoint reachable via a "simple request" (GET/POST with only allowlisted content-types, no custom headers) that relies solely on CORS preflight for protection rather than a CSRF token.
Static: yes

### 9. Cache-Control: no-store on authenticated/sensitive responses
Authority: ASVS 5.0 V14.3.2; CWE-525 (Information Exposure Through Browser Caching)
URL: https://github.com/OWASP/ASVS (chapter V14, Data Protection)
Quote: "Verify that the application sets sufficient anti-caching HTTP response header fields (i.e., Cache-Control: no-store) so that sensitive data is not cached in browsers."
Lint condition: response-header lint for an authenticated API/HTML response (account page, invoice, session-scoped data) with no `Cache-Control: no-store` (or `private, no-cache`) header, especially behind a shared CDN/proxy.
Static: yes

### 10. Cache poisoning via unkeyed headers
Authority: no dedicated ASVS 5.0 requirement id was found this pass for "cache key" / "unkeyed header" (searched "cache poison" and got zero hits) -- flagging as an ASVS coverage gap; cross-reference CWE-444 (HTTP Request/Response Smuggling, related class) and general CDN-vendor documentation (Cloudflare/Fastly cache-key docs, not independently fetched this pass).
URL: not independently fetched this pass -- BLOCKED for a primary-source quote.
Lint condition: CDN/reverse-proxy config lint for a cache configuration that varies response content based on a header (`X-Forwarded-Host`, `Host`, custom A/B header) that is not included in the cache key, allowing a poisoned response to be served to other users.
Static: config

### 11. DEBUG=True / FLASK_DEBUG / NODE_ENV in production
Authority: ASVS 5.0 V13.4.2 (from prior pass); CWE-489 (Active Debug Code)
URL: https://github.com/OWASP/ASVS (chapter V13, Configuration)
Quote: "Verify that debug modes are disabled for all components in production environments to prevent exposure of debugging features and information leakage."
Lint condition: environment-config lint for `DEBUG=True`/`FLASK_DEBUG=1`/`app.debug=true` in a file loaded by the production environment, or `NODE_ENV` unset/not equal to `production` in a deployed container/service definition.
Static: config

### 12. Source maps deployed to production
Authority: ASVS 5.0 V13.4.2 (information-leakage framing, same requirement as item 11); CWE-540 (Inclusion of Sensitive Information in Source Code, adjacent)
URL: https://github.com/OWASP/ASVS
Quote: same as item 11 -- source maps are a documented instance of "exposure of debugging features and information leakage."
Lint condition: build-config lint for `devtool: 'source-map'` (webpack) or equivalent producing a publicly served `.map` file, or a `.map` file present in the production static-asset output directory.
Static: yes

### 13. Verbose errors / stack traces returned to the client
Authority: ASVS 5.0 V16.5.1; CWE-209 (Information Exposure Through an Error Message)
URL: https://github.com/OWASP/ASVS (chapter V16, Security Logging and Error Handling)
Quote: "Verify that a generic message is returned to the consumer when an unexpected or security-sensitive error occurs, ensuring no exposure of sensitive internal system data such as stack traces, queries, secret keys, and toke[ns]."
Lint condition: error-handler config lint for a global exception handler that serializes the exception object/traceback directly into the HTTP response body rather than a generic message plus a correlation ID.
Static: yes

### 14. Directory listing exposed
Authority: ASVS 5.0 V13.4.3 (from prior pass)
URL: https://github.com/OWASP/ASVS
Quote: "Verify that web servers do not expose directory listings to clients unless explicitly intended."
Lint condition: web-server config lint for `autoindex on` (nginx) or missing `Options -Indexes` (Apache) on a static-file-serving location block.
Static: config

### 15. .git/.svn metadata deployed and reachable
Authority: ASVS 5.0 V13.4.1
URL: https://github.com/OWASP/ASVS
Quote: "Verify that the application is deployed either without any source control metadata, including the .git or .svn folders, or in a way that these folders are inaccessible both externally and to the application itself."
Lint condition: deploy-pipeline lint for a build/publish step that copies the full working tree (including `.git/`) into the served static-asset directory with no exclusion rule.
Static: config

### 16. Default credentials / hard-coded secrets in code (cross-ref)
Authority: ASVS 5.0 V6.3.2, V13.3.1; CWE-798, CWE-1392
URL: https://github.com/OWASP/ASVS
Quote: V13.3.1: "Verify that a secrets management solution, such as a key vault, is used to securely create, store, control access to, and destroy backend secrets. These could include passwords, key material, integrations with databases and third-[party services]."
Lint condition: config lint for database/API credentials hard-coded in a source file or committed `.env`, rather than sourced from a vault/secret-manager reference at deploy time.
Static: yes

### 17. Public S3/GCS buckets and Supabase storage policies
Authority: derived from ASVS's general access-control framing (V8.2.1, function-level access restricted to explicit permissions), applied to object storage; no dedicated ASVS 5.0 "object storage ACL" requirement id exists -- flagging as a coverage gap; cross-reference the Supabase RLS finding already logged in lint-authorities.md item E35.
URL: https://github.com/OWASP/ASVS ; https://supabase.com/docs/guides/database/postgres/row-level-security
Quote: ASVS V8.2.1: "Verify that the application ensures that function-level access is restricted to consumers with explicit permissions." (Generalized here to bucket/object-level access rather than function-level.)
Lint condition: IaC lint (Terraform/CloudFormation/Pulumi) for an S3 bucket policy or GCS bucket IAM binding granting `AllUsers`/`AllAuthenticatedUsers`/`public-read` without an explicit justification tag, and Supabase-storage-bucket config lint for a bucket with `public: true` holding user-uploaded files with no per-object RLS policy.
Static: config

### 18. Secrets in front-end bundles
Authority: ASVS 5.0 V14.3.3 (browser-storage sensitive-data framing, from prior pass) generalized to build-time secret inlining; CWE-540
URL: https://github.com/OWASP/ASVS
Quote: same class of requirement as V14.3.3's "data stored in browser storage ... does not contain sensitive data" -- a secret baked into a JS bundle is reachable by any client exactly as browser storage is.
Lint condition: build-output lint (grep the compiled JS bundle) for API keys, private service-role tokens, or database connection strings matching known secret-key patterns, distinguishing from intentionally-public keys (e.g., publishable Stripe keys).
Static: yes

### 19. Secrets in logs
Authority: ASVS 5.0 V16.4.2 (log-content sensitivity, cross-referenced from V14.2.4's "how the data is to be logged" clause); CWE-532 (Insertion of Sensitive Information into Log File)
URL: https://github.com/OWASP/ASVS (chapters V14, V16)
Quote: V14.2.4: "Verify that controls around sensitive data related to encryption, integrity verification, retention, how the data is to be logged, access controls around sensitive data in logs, privacy and privacy-enhancing technologies..." are documented and enforced.
Lint condition: logging-call lint for full request/response objects (headers, body) logged verbatim without redaction of `Authorization`, `Cookie`, `password`, `token`, or card-number-shaped fields.
Static: yes

### 20. Secrets in git history (post-removal)
Authority: same class as item 15 (CWE-798), applied to historical commits rather than the working tree
URL: not independently re-fetched a dedicated primary source this pass; standard practice per gitleaks/truffleHog tooling documentation.
Lint condition: git-history secret scan (not just working-tree) for credentials that were committed and later "removed" in a subsequent commit but remain retrievable via `git log -p`/`git show`.
Static: yes

### 21. Secrets in CI logs
Authority: same class as item 19, applied to CI/CD build-log output; CWE-532
URL: not independently re-fetched a platform-specific primary source this pass (e.g., GitHub Actions' own secret-masking docs) -- flagging as a gap; GitHub Actions is documented to auto-mask registered `secrets.*` values in log output, but only for values referenced via that mechanism.
Lint condition: CI-pipeline lint for a workflow step that echoes an environment variable or command substitution containing a credential without it being registered as a GitHub/CI "secret" (so the platform's masking never applies), or that sets `::add-mask::` incorrectly.
Static: config

### 22. GitHub Actions pinned by tag, not commit SHA
Authority: no dedicated ASVS 5.0 requirement id found this pass for CI-action pinning specifically; covered under the general A03:2025 Software Supply Chain Failures category (OWASP Top 10:2025) and GitHub's own security-hardening guide (not independently re-fetched this pass).
URL: https://owasp.org/Top10/2025/ ; https://docs.github.com/actions/security-guides/security-hardening-for-github-actions (not independently re-fetched this pass -- BLOCKED for a verbatim quote)
Quote: A03:2025 category name confirmed in the prior pass: "A03:2025 - Software Supply Chain Failures."
Lint condition: workflow-YAML lint for `uses: owner/action@v1` (or `@main`/`@master`) instead of `uses: owner/action@<40-char-commit-sha>`.
Static: yes

### 23. pull_request_target misuse
Authority: same A03:2025 Software Supply Chain Failures framing; GitHub's own docs on `pull_request_target` risk (not independently re-fetched this pass)
URL: https://owasp.org/Top10/2025/ ; GitHub Actions events documentation (not independently re-fetched this pass -- BLOCKED for a verbatim quote)
Quote: BLOCKED for a verbatim GitHub-docs quote this pass; the well-documented risk is that `pull_request_target` runs with the base repository's secrets/token against code checked out from the untrusted fork ref.
Lint condition: workflow-YAML lint for `on: pull_request_target` combined with a `actions/checkout` step that checks out `github.event.pull_request.head.sha` (the fork's code) and later steps that use `secrets.*` or run the checked-out code (build/test scripts).
Static: yes

### 24. Dockerfile running as root
Authority: no dedicated ASVS 5.0 id found this pass for container-user configuration; covered under A02:2025 Security Misconfiguration general framing; Docker's own best-practices docs (not independently re-fetched this pass).
URL: https://owasp.org/Top10/2025/ ; https://docs.docker.com/develop/develop-images/dockerfile_best-practices/ (not independently re-fetched this pass -- BLOCKED for a verbatim quote)
Quote: BLOCKED for a verbatim Docker-docs quote this pass; Docker's documented recommendation is to add a non-root `USER` directive before the final `CMD`/`ENTRYPOINT`.
Lint condition: Dockerfile lint for no `USER <non-root>` instruction before the final stage's entrypoint, meaning the container runs as root by default.
Static: yes

### 25. Dockerfile :latest tag
Authority: same class as item 24, A02:2025/A03:2025 framing
URL: https://owasp.org/Top10/2025/
Quote: same category citations as items 22-24.
Lint condition: Dockerfile/compose/Kubernetes-manifest lint for a base image or deployed image reference using the `:latest` tag (or no tag, which defaults to `latest`) instead of a pinned version/digest.
Static: yes

### 26. Dependency pinning and lockfile presence
Authority: ASVS 5.0 V15.2.4 (from prior pass); A03:2025 Software Supply Chain Failures
URL: https://github.com/OWASP/ASVS ; https://owasp.org/Top10/2025/
Quote: V15.2.4: "Verify that third-party components and all of their transitive dependencies are included from the expected repository, whether internally owned or an approved external repository."
Lint condition: repository lint for a manifest (`package.json`, `pyproject.toml`, `Gemfile`) present with no corresponding lockfile (`package-lock.json`/`yarn.lock`/`uv.lock`/`Gemfile.lock`) committed, or a lockfile out of sync with the manifest.
Static: yes

### 27. Typosquat distance on newly added dependencies
Authority: same A03:2025 framing; no dedicated ASVS requirement id found for typosquat detection specifically
URL: https://owasp.org/Top10/2025/
Quote: same category citation.
Lint condition: dependency-add lint (CI check on manifest diffs) computing edit distance between a newly added package name and the top-N most-downloaded packages in that ecosystem, flagging distance-1/2 matches for manual review.
Static: config

### 28. Audit logging of authentication events
Authority: ASVS 5.0 V16.3.1, V16.3.2
URL: https://github.com/OWASP/ASVS (chapter V16)
Quote: V16.3.1: "Verify that all authentication operations are logged, including successful and unsuccessful attempts. Additional metadata, such as the type of authentication or factors used, should also be collected." V16.3.2: "Verify that failed authorization attempts are logged."
Lint condition: auth-handler lint for a login/logout/password-reset/MFA-challenge code path with no corresponding audit-log call.
Static: yes

### 29. Log entry metadata completeness (who/what/when/where) and clock sync
Authority: ASVS 5.0 V16.2.1, V16.2.2
URL: https://github.com/OWASP/ASVS
Quote: V16.2.1: "Verify that each log entry includes necessary metadata (such as when, where, who, what) that would allow for a detailed investigation of the timeline when an event happens." V16.2.2 requires "timestamps in security event metadata use UTC or include an explicit time zone offset."
Lint condition: logging-configuration lint for a log formatter that omits user-id/actor, timestamp, or source-IP fields, or that emits local-time timestamps with no timezone/UTC marker.
Static: config

### 30. PII in logs
Authority: ASVS 5.0 V14.2.4 (from item 19); CWE-532
URL: https://github.com/OWASP/ASVS
Quote: same as item 19.
Lint condition: same as item 19, specifically matched against a PII field-name denylist (email, ssn, dob, address) rather than only credential-shaped values.
Static: yes

### 31. Log retention policy for sensitive data
Authority: ASVS 5.0 V14.2.7
URL: https://github.com/OWASP/ASVS (chapter V14)
Quote: "Verify that sensitive information is subject to data retention classification, ensuring that outdated or unnecessary data is deleted automatically, on a defined schedule, or as the situation requires."
Lint condition: log-pipeline/infra config lint for a log-storage bucket/index with no lifecycle/retention policy (indefinite retention) holding PII-bearing log streams.
Static: config

### 32. Outbound request timeouts (server-side HTTP client calls)
Authority: ASVS 5.0 V13.1.3, V13.2.6 (documented resource-management strategy per external service)
URL: https://github.com/OWASP/ASVS (chapter V13)
Quote: V13.1.3: "Verify that the application documentation defines resource-management strategies for every external system or service it uses (e.g., databases, file handles, threads, HTTP connections). This should include resource-relea[se behavior]." V13.2.6 covers per-connection limits and "behavior when maximum allowed connections is reached."
Lint condition: HTTP-client code lint for an outbound call (`requests.get`, `axios`, `fetch`) with no `timeout=`/`signal: AbortSignal.timeout()` argument, risking indefinite hangs under a slow/unresponsive upstream.
Static: yes

### 33. Request body size limits
Authority: no dedicated ASVS 5.0 id found this pass with the exact phrase "request body size"; covered under the general resource-exhaustion framing of V15.2.2 and A10:2025 Mishandling of Exceptional Conditions.
URL: https://github.com/OWASP/ASVS ; https://owasp.org/Top10/2025/
Quote: V15.2.2: "Verify that the application has implemented defenses against loss of availability due to functionality which is time-consuming or resource-demanding, based on the documented security decisions and strategies for this."
Lint condition: web-framework config lint for a body-parsing middleware (Express `body-parser`, Django `DATA_UPLOAD_MAX_MEMORY_SIZE`) with no configured maximum request-body size, or one set above a documented threshold.
Static: config

### 34. Server-side request timeouts (inbound, for the app's own handlers)
Authority: same class as item 32-33, V13.1.3/V15.2.2
URL: https://github.com/OWASP/ASVS
Quote: same as items 32-33.
Lint condition: web-server/gateway config lint for no configured request/connection timeout on the listening server (nginx `client_body_timeout`, load-balancer idle-timeout) allowing slow-loris-style connection exhaustion.
Static: config

### 35. WebSocket origin check
Authority: ASVS 5.0 V4.4.2 (from prior pass)
URL: https://github.com/OWASP/ASVS (chapter V4)
Quote: "Verify that, during the initial HTTP WebSocket handshake, the Origin header field is checked against a list of origins allowed for the application."
Lint condition: WS-server handler lint for a connection/upgrade callback with no `Origin` header check against an allowlist.
Static: yes

### 36. GraphQL depth/cost/introspection limits
Authority: ASVS 5.0 V4.3.1, V4.3.2 (from prior pass)
URL: https://github.com/OWASP/ASVS (chapter V4)
Quote: V4.3.1: "Verify that a query allowlist, depth limiting, amount limiting, or query cost analysis is used to prevent GraphQL or data layer expression [DoS]." V4.3.2: "Verify that GraphQL introspection queries are disabled in the production environment unless the GraphQL API is meant to be used by other parties."
Lint condition: GraphQL-server config lint for `introspection: true` in a production config and for no depth/cost-limit plugin registered.
Static: config

### 37. Least-functionality in production (no test/dev endpoints shipped)
Authority: ASVS 5.0 V15.2.3
URL: https://github.com/OWASP/ASVS (chapter V15)
Quote: "Verify that the production environment only includes functionality that is required for the application to function, and does not expose extraneous functionality such as test code, sample snippets, and development functionality."
Lint condition: route-table lint for a debug/test/seed-data route (`/debug`, `/test-login`, `/__reset_db`) present in the production build's router registration.
Static: yes

### 38. Outbound allowlist for server-initiated requests (SSRF egress control)
Authority: ASVS 5.0 V13.2.5
URL: https://github.com/OWASP/ASVS (chapter V13)
Quote: "Verify that the web or application server is configured with an allowlist of resources or systems to which the server can send requests or load data or files from."
Lint condition: network/egress-policy config lint (security group, firewall rule, service-mesh policy) for a server workload with unrestricted outbound access rather than an explicit allowlist of destination hosts/services.
Static: config

### 39. Client storage cleared on session termination
Authority: ASVS 5.0 V14.3.1
URL: https://github.com/OWASP/ASVS (chapter V14)
Quote: "Verify that authenticated data is cleared from client storage, such as the browser DOM, after the client or session is terminated. The 'Clear-Site-Data' HTTP response header field may be able to help with this but the client-side..."
Lint condition: logout-handler lint (frontend) for no call clearing `localStorage`/`sessionStorage`/in-memory app state, and no `Clear-Site-Data` response header on the logout endpoint.
Static: yes

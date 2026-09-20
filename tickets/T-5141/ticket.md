---
id: T-5141
title: 'WEBSEC injection and output encoding: XSS sinks, SSTI, eval/exec, unsafe deserialization,
  command/NoSQL/LDAP/log/header injection, input bounds (ASVS V1 V2 V5 V15)'
state: queued
kind: security
origin: human
created: '2026-09-20'
priority: critical
parent: T-5140
tier: story
sprint: v1.1.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: sprint
  old_value: v0.534.0
  new_value: v1.1.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-20'
body_changes:
- mode: append
  reason: 'owner 2026-09-20: carry the research corpus in the ticket body, not only
    as an attachment'
  actor: logan
  at: '2026-09-20'
  old_length: 633
  new_length: 17389
designated_repro_test: null
threat: tampering
component: gates
anchor: false
anchor_reason: null
land_commit: null
---
28 entries in the attached corpus, 25 static. Sinks by framework: innerHTML, dangerouslySetInnerHTML, v-html, Jinja |safe and autoescape=False, Django mark_safe, Rails raw/html_safe; yaml.load without SafeLoader, pickle.loads on untrusted, subprocess shell=True with non-literal argv, eval/exec/Function; CRLF in log calls, header values from input; XML parsers with external entities; JSON/XML depth and size limits. Each rule reason cites the ASVS 5.0 id and CWE from the corpus. Frob's existing SEC005 taint substrate is the engine: extend sources (request params, headers, body, URL, cookies, file names) and sinks per framework.

# Injection and output-encoding lint authorities (ASVS V1, V2, V5, V15)

Authority base: OWASP ASVS 5.0.0 flat requirements JSON, fetched from
https://raw.githubusercontent.com/OWASP/ASVS/master/5.0/docs_en/OWASP_Application_Security_Verification_Standard_5.0.0_en.flat.json
in the prior research pass (345 requirements, chapters V1-V17). CWE ids
below are standard mappings for these vulnerability classes (MITRE CWE
List, cwe.mitre.org) applied by inspection, not independently re-fetched
per-id this pass -- flagged where that matters.

### 1. Reflected/stored XSS -- output encoding by context
Authority: ASVS 5.0 V1.2.1; CWE-79
URL: https://github.com/OWASP/ASVS
Quote: "Verify that output encoding for an HTTP response, HTML document, or XML document is relevant for the context required, such as encoding the relevant characters for HTML elements, HTML attributes, HTML..."
Lint condition: template-render lint for a variable interpolated into HTML output with no auto-escape or explicit encode call, matched against known unsafe sinks in item 2.
Static: yes

### 2. DOM XSS via innerHTML
Authority: ASVS 5.0 V1.1.2 (output encoding as final step before interpreter use); CWE-79, CWE-83 (XSS via script in attribute)
URL: https://github.com/OWASP/ASVS
Quote: "Verify that the application performs output encoding and escaping either as a final step before being used by the interpreter for which it i[s intended]."
Lint condition: JS/TS AST lint for assignment to `.innerHTML`, `.outerHTML`, `document.write()`, or `insertAdjacentHTML()` where the right-hand side is not a literal or a call to a known sanitizer (DOMPurify).
Static: yes

### 3. React dangerouslySetInnerHTML
Authority: ASVS 5.0 V1.1.2 / V1.2.1 (same encoding-before-sink requirement, framework-specific sink); CWE-79
URL: https://github.com/OWASP/ASVS
Quote: same as item 1; ASVS is framework-agnostic, the sink itself is documented in React's own docs as bypassing its default escaping.
Lint condition: JSX/TSX lint for `dangerouslySetInnerHTML={{__html: X}}` where X is not passed through a sanitizer call in the same expression.
Static: yes

### 4. Vue v-html
Authority: ASVS 5.0 V1.1.2 / V1.2.1; CWE-79
URL: https://github.com/OWASP/ASVS
Quote: same as item 1; Vue's own docs mark `v-html` as bypassing template escaping.
Lint condition: template lint for `v-html="expr"` bindings where `expr` is not a compile-time constant or sanitized value.
Static: yes

### 5. Jinja2 |safe filter and autoescape=False
Authority: ASVS 5.0 V1.2.1; CWE-79
URL: https://github.com/OWASP/ASVS
Quote: same output-encoding-by-context requirement as item 1; Jinja2's own docs document `|safe` and `Environment(autoescape=False)` as disabling its default context-aware escaping.
Lint condition: template-source lint for `|safe` filter applied to a variable sourced from request input, and Python config lint for `Environment(` / `Flask(...)` with `autoescape=False` or missing `autoescape=True`.
Static: yes

### 6. Django mark_safe
Authority: ASVS 5.0 V1.2.1; CWE-79
URL: https://github.com/OWASP/ASVS
Quote: same as item 1; Django's own docs document `mark_safe()` and the `{% autoescape off %}` block tag as disabling escaping.
Lint condition: Python AST lint for `django.utils.safestring.mark_safe(x)` where `x` is built from a request-derived string via concatenation/format, and template lint for `{% autoescape off %}` blocks containing interpolated variables.
Static: yes

### 7. Rails html_safe / raw
Authority: ASVS 5.0 V1.2.1; CWE-79
URL: https://github.com/OWASP/ASVS
Quote: same as item 1; Rails' own docs document `.html_safe` and the `raw()` helper as disabling ERB's automatic escaping.
Lint condition: Ruby AST/regex lint for `.html_safe` called on a string built from `params[...]` or `request.` derived data, and view-template lint for `raw(...)` wrapping non-literal content.
Static: yes

### 8. PHP echo of unescaped request data
Authority: ASVS 5.0 V1.2.1; CWE-79
URL: https://github.com/OWASP/ASVS
Quote: same as item 1; PHP has no default output escaping, so any `echo`/`print`/short-echo (`<?=`) of `$_GET`/`$_POST`/`$_REQUEST` without `htmlspecialchars()` is a direct sink.
Lint condition: PHP lint for `echo`/`print`/`<?=` statements whose argument traces to a superglobal (`$_GET`, `$_POST`, `$_REQUEST`, `$_COOKIE`) with no `htmlspecialchars`/`htmlentities` call in the expression.
Static: yes

### 9. Server-side template injection (SSTI)
Authority: ASVS 5.0 V1.3.7; CWE-1336 (SSTI), CWE-94
URL: https://github.com/OWASP/ASVS (chapter V1)
Quote: "Verify that the application protects against template injection attacks by not allowing templates to be built based on untrusted input. Where there is no alternative, any untrusted input being included..."
Lint condition: code lint for template-engine `render_template_string()` (Flask/Jinja2), `Template(userInput)` (Django), or string-concatenated template source built from request data before being compiled/rendered.
Static: yes

### 10. eval/exec/Function/new Function on untrusted input
Authority: ASVS 5.0 V1.2.4 (parameterization principle extends to code-as-data sinks); CWE-95 (Eval Injection), CWE-94
URL: https://github.com/OWASP/ASVS
Quote: injection-prevention principle (parameterize, never build interpretable strings from untrusted data) applies identically to code interpreters as to SQL/OS interpreters per V1.2's chapter framing.
Lint condition: JS/TS lint for `eval(`, `new Function(`, `setTimeout(stringArg, ...)`, `setInterval(stringArg, ...)`; Python lint for `eval(`, `exec(` with an argument that traces to request/user input.
Static: yes

### 11. yaml.load without SafeLoader
Authority: ASVS 5.0 V1.5.2; CWE-502 (Deserialization of Untrusted Data)
URL: https://github.com/OWASP/ASVS
Quote: "Verify that deserialization of untrusted data enforces safe input handling, such as using an allowlist of object types or restricting client-defined object types, to prevent deserialization attacks. Deserialization mechanisms that are explicitly defined as insecure must not be used with untrusted input."
Lint condition: Python AST lint for `yaml.load(x)` with no `Loader=yaml.SafeLoader`/`CSafeLoader` keyword argument.
Static: yes

### 12. pickle.load/pickle.loads on untrusted data
Authority: ASVS 5.0 V1.5.2; CWE-502
URL: https://github.com/OWASP/ASVS
Quote: same as item 11 -- pickle is explicitly the canonical "mechanism ... defined as insecure" for untrusted input in the Python ecosystem.
Lint condition: Python AST lint for `pickle.load`/`pickle.loads`/`cPickle` calls whose input traces to a network request, uploaded file, or cache/queue payload rather than a trusted internal source.
Static: yes

### 13. OS command injection via shell=True
Authority: ASVS 5.0 V1.2.5; CWE-78 (OS Command Injection)
URL: https://github.com/OWASP/ASVS
Quote: "Verify that the application protects against OS command injection and that operating system calls use parameterized OS queries or use contextual command line escaping when parameterization is not available."
Lint condition: Python AST lint for `subprocess.run/Popen/call(..., shell=True)` or `os.system(...)` where the command string is built via f-string/concatenation from request input; Node lint for `child_process.exec()` (vs `execFile`) with interpolated input.
Static: yes

### 14. LDAP injection
Authority: ASVS 5.0 V1.2.6; CWE-90 (LDAP Injection)
URL: https://github.com/OWASP/ASVS
Quote: "Verify that the application protects against LDAP injection vulnerabilities, or that specific security controls to prevent LDAP injection have been implemented."
Lint condition: code lint for LDAP filter strings built via string concatenation/format of user input rather than an escaping helper (e.g., `ldap3`'s `escape_filter_chars` or equivalent).
Static: yes

### 15. NoSQL / operator injection
Authority: ASVS 5.0 V1.2.4; CWE-943 (Improper Neutralization of Special Elements in Data Query Logic)
URL: https://github.com/OWASP/ASVS
Quote: "Verify that data selection or database queries (e.g., SQL, HQL, NoSQL, Cypher) use parameterized queries, ORMs, entity frameworks, or are otherwise protected from SQL Injection and other database injection attacks."
Lint condition: code lint for a MongoDB (or similar) query object built by directly assigning `req.body`/`req.query` as a filter value without type-checking/sanitizing for operator keys (`$where`, `$gt`, `$ne`) originating from user JSON.
Static: yes

### 16. LaTeX/shell-escape injection
Authority: ASVS 5.0 V1.2.8; CWE-94
URL: https://github.com/OWASP/ASVS
Quote: "Verify that LaTeX processors are configured securely (such as not using the '--shell-escape' flag) and an allowlist of commands is used to prevent LaTeX injection attacks."
Lint condition: build/config lint for a LaTeX-compilation invocation (`pdflatex`, `xelatex`) including `--shell-escape`/`-shell-escape` when compiling user-supplied `.tex` source.
Static: yes

### 17. URL-building injection / open-redirect-adjacent header injection
Authority: ASVS 5.0 V1.2.2, V4.2.5; CWE-601 (Open Redirect), CWE-113 (HTTP Response Splitting)
URL: https://github.com/OWASP/ASVS
Quote: V1.2.2: "Verify that when dynamically building URLs, untrusted data is encoded according to its context ... Ensure that only safe URL protocols..." V4.2.5: "Verify that ... the application ... uses validation, sanitization, or other mechanisms to avoid creating URIs (such as for API calls) or HTTP request he[aders]..."
Lint condition: code lint for URL-construction from request input with no `urlencode`/allowlisted-scheme check, and for header-value assignment built from user input with no CR/LF stripping.
Static: yes

### 18. HTTP/2-3 header/CRLF injection (response splitting)
Authority: ASVS 5.0 V4.2.3, V4.2.4; CWE-113, CWE-93 (CRLF Injection)
URL: https://github.com/OWASP/ASVS (chapter V4, API and Web Service)
Quote: V4.2.4: "Verify that the application only accepts HTTP/2 and HTTP/3 requests where the header fields and values do not contain any CR (\r), LF (\n), or CRLF (\r\n) sequences, to prevent header injection attacks." V4.2.3 bars forwarding connection-specific fields like `Transfer-Encoding` to prevent response splitting/smuggling.
Lint condition: reverse-proxy/gateway config lint for missing header-sanitization middleware, and code lint for `response.setHeader(name, userInput)` calls with no CR/LF stripping on `userInput`.
Static: config

### 19. Log injection / CRLF in log lines
Authority: ASVS 5.0 V16.4.1; CWE-117 (Improper Output Neutralization for Logs)
URL: https://github.com/OWASP/ASVS (chapter V16, Security Logging and Error Handling)
Quote: "Verify that all logging components appropriately encode data to prevent log injection."
Lint condition: logging-call lint for `logger.info(f"... {user_input} ...")` (or string concatenation) passed to a logger with no configured encoder that strips/escapes `\n`/`\r`, especially where log lines feed a SIEM parser.
Static: yes

### 20. HTML injection in transactional email
Authority: ASVS 5.0 V1.2.1 (context-appropriate output encoding extends to email/HTML bodies); CWE-79 (email-as-HTML-sink variant)
URL: https://github.com/OWASP/ASVS
Quote: same encoding-by-context text as item 1, applied to the HTML-email-body context.
Lint condition: email-template lint for user-supplied fields (display name, order note, support-ticket subject) interpolated into an HTML email template with no escaping, matching the same sinks as items 5-8 for whatever templating engine renders the email.
Static: yes

### 21. Filename/header encoding for served files and attachments
Authority: ASVS 5.0 V5.4.2; CWE-113
URL: https://github.com/OWASP/ASVS (chapter V5, File Handling)
Quote: "Verify that file names served (e.g., in HTTP response header fields or email attachments) are encoded or sanitized (e.g., following RFC 6266) to preserve document structure and prevent injection attacks."
Lint condition: code lint for `Content-Disposition` header construction using a raw user-supplied filename with no RFC 6266 encoding (`filename*=UTF-8''...`) or sanitization of quote/CRLF characters.
Static: yes

### 22. Input length limits (unbounded input as a resource-consumption vector)
Authority: ASVS 5.0 V2.1.1 (documented validation rules), and general A04:2025/A10:2025 framing for exceptional-condition/resource-consumption handling
URL: https://github.com/OWASP/ASVS (chapter V2, Validation and Business Logic)
Quote: "Verify that the application's documentation defines input validation rules for how to check the validity of data items against an expected structure."
Lint condition: schema lint (JSON Schema/Pydantic/Zod/class-validator) for string/array fields with no `maxLength`/`max_length`/`maxItems` constraint on any request-body field.
Static: yes

### 23. XML entity/bomb (billion laughs) and unrestricted XML parsing
Authority: ASVS 5.0 V1.5.1; CWE-776 (DTD/XML Entity Expansion), CWE-611 (XXE)
URL: https://github.com/OWASP/ASVS (chapter V1)
Quote: "Verify that the application configures XML parsers to use a restrictive configuration and that unsafe features such as resolving external entities are [disabled]."
Lint condition: XML-parser instantiation lint for missing `resolve_entities=False`, missing `DTD` disabling, or missing entity-expansion limits (e.g., `defusedxml` not used where `lxml`/`ElementTree` parses untrusted XML).
Static: yes

### 24. JSON bomb / unbounded nesting depth
Authority: ASVS 5.0 V2.1.1 (documented structural validation) plus A10:2025 Mishandling of Exceptional Conditions framing (OWASP Top 10:2025); CWE-674 (Uncontrolled Recursion), CWE-776-adjacent
URL: https://github.com/OWASP/ASVS ; https://owasp.org/Top10/2025/
Quote: ASVS text as item 22; the 2025 Top 10's new A10 category is explicitly about unhandled resource-exhaustion/exceptional conditions from malformed or oversized input (category name confirmed in prior fetch: "A10:2025 - Mishandling of Exceptional Conditions").
Lint condition: web-framework config lint for a JSON body-parser with no configured max depth/size (e.g., Express `body-parser` `limit` option unset, or a recursive-descent JSON parser with no depth counter).
Static: config

### 25. Unbounded recursion on user-controlled input
Authority: CWE-674 (Uncontrolled Recursion); framed under ASVS V2 business-logic-limits chapter (V2.1.3, V2.3.2 documented limits) as the general "undocumented limit" gap
URL: https://github.com/OWASP/ASVS (chapter V2)
Quote: V2.1.3: "Verify that expectations for business logic limits and validations are documented, including both per-user and globally across the application." V2.3.2: "Verify that business logic limits are implemented per the application's documentation to avoid business logic flaws being exploited."
Lint condition: code lint for a recursive function (parser, tree-walker, nested-comment renderer) whose recursion depth is bound only by input structure with no explicit max-depth counter/guard.
Static: yes

### 26. Field-level over-exposure (returning full object instead of subset)
Authority: ASVS 5.0 V15.3.1; CWE-213 (Exposure of Sensitive Information Due to Incompatible Policies)
URL: https://github.com/OWASP/ASVS (chapter V15)
Quote: "Verify that the application only returns the required subset of fields from a data object. For example, it should not return an entire data object, as some individual fields should not be accessible t[o all callers]."
Lint condition: serializer lint for API responses built via `jsonify(model.__dict__)` / `model.to_dict()` / ORM `SELECT *`-backed serialization with no explicit field allowlist per endpoint/role.
Static: yes

### 27. Backend following redirects from untrusted URLs (SSRF-adjacent)
Authority: ASVS 5.0 V15.3.2; CWE-918 (SSRF)
URL: https://github.com/OWASP/ASVS (chapter V15)
Quote: "Verify that where the application backend makes calls to external URLs, it is configured to not follow redirects unless it is intended functionality."
Lint condition: HTTP-client config lint for `requests.get(url, allow_redirects=True)` (default) or `axios`/`fetch` with redirect-follow enabled on a server-side call whose `url` derives from user input.
Static: yes

### 28. Business-logic step-skipping (workflow order enforcement)
Authority: ASVS 5.0 V2.3.1; CWE-841 (Improper Enforcement of Behavioral Workflow)
URL: https://github.com/OWASP/ASVS (chapter V2)
Quote: "Verify that the application will only process business logic flows for the same user in the expected sequential step order and without skipping steps."
Lint condition: dynamic-only in general (requires exercising the workflow); static check limited to confirming each multi-step handler validates a `state`/`status` field transition before proceeding, rather than trusting the step parameter alone.
Static: dynamic-only

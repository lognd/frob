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

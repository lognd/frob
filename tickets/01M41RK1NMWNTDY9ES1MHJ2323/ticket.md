+++
id = "01M41RK1NMWNTDY9ES1MHJ2323"
title = "frob check fails CI: .github/dependabot.yml carries the v1 directive frob:used-by (DSL001)"
type = "bug"
category = "done"
outcome = "done"
priority = "critical"
points = 1
reporter = "lognd"
created = "2026-10-03T20:51:46Z"
updated = "2026-10-03T21:01:48Z"
scope = [".github/dependabot.yml"]

[[acceptance]]
text = "Given the repository, when frob check runs, then no DSL001 is reported for any YAML file"
bound = true
+++

Since ~2PM2R2K frob reads YAML comments, so the v1-only directive '# frob:used-by .github/workflows/ci.yml' on line 1 of .github/dependabot.yml is DSL001 (error) and the ubuntu CI frob check step fails (run 37151892875). Replace it with the v2 equivalent if one exists (check docs/reference/directives or the directive registry), otherwise remove it and keep the plain explanatory comment. Also grep every tracked YAML file for other v1 directives that are now scanned.

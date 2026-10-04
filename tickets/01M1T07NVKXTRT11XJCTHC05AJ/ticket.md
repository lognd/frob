+++
id = "01M1T07NVKXTRT11XJCTHC05AJ"
title = "shell grammar for ops/**.sh plus starter policy"
type = "security"
category = "triage"
priority = "low"
parent = "01M1QDTYTRW714S858S0TP6YWM"
reporter = "agent"
created = "2026-09-06T00:00:00Z"
updated = "2026-10-04T21:04:43Z"
aliases = ["T-3955"]
labels = ["v1-cluster:B4", "triage:accepted"]
scope = ["src/frob/lang/_walk_bash.py"]

[[acceptance]]
text = "given a cost estimate for a shell/tree-sitter-bash grammar addition, when this ticket's design step completes, then a go/no-go decision is recorded with the estimate"
bound = false

[[acceptance]]
text = "given a go decision, when the grammar lands, then a starter [[policy.pattern]] catalogue ships alongside it that flags at minimum: credentials in argv (e.g. a password positional/PGPASSWORD-adjacent pattern) and an unguarded rm -rf under a documented DRY_RUN gate"
bound = false
+++

Convergence 3 of T-3928 (threat-model item 3 + edge/ops item 2, arrived independently). Also relevant to T-3920 item 3 -- cite this ticket there, do not duplicate. FINDING THIS WOULD HAVE CAUGHT: two of four confirmed threat-model findings are structurally invisible to policy today because shell has no frob grammar (Caddyfile too, tracked separately). Edge/ops adds two concrete findings needing nothing else: a database password in pg_dump's argv (a REGRESSION of the identical bug already fixed for rclone in the same file) and an unwrapped destructive rm -rf in a script that documents itself as printing-only under DRY_RUN. THEIR KEY CAVEAT, preserve it: ship a STARTER POLICY CATALOGUE with the grammar, because the grammar alone only makes rules possible, it does not by itself catch anything. Cost this before committing: how many grammars does frob already carry (see LANG_COLLECTORS / lang adapters), and is a shell grammar (tree-sitter-bash or similar) proportionate. Related but distinct from T-3858 (frob:waive inert in no-grammar files is about DIRECTIVES; this is about POLICY over ops/**.sh).

CORRECTION after filing: verified src/frob/lang/_walk_bash.py already exists (T-1604) -- frob ALREADY HAS a bash/shell tree-sitter grammar and walker. The grammar-cost question this ticket originally posed is MOOT; do not build a new grammar. The real remaining gap is narrower: no [[policy.pattern]] rules ship targeting ops/**.sh today (grep of design/*.strata for policy blocks found none), so the walked symbols are not yet fed into any policy surface with a starter catalogue. Retitle the actual work as: confirm ops/**.sh is reachable via the existing walker for policy.pattern matching, and ship the starter catalogue (credentials-in-argv, unguarded rm -rf under DRY_RUN) the auditors asked for.

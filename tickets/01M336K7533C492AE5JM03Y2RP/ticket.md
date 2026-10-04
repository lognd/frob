+++
id = "01M336K7533C492AE5JM03Y2RP"
title = "frob.app._config_external missing T-5132 CLI field allowlist entries (points/tokens/unsized-ack silently dropped)"
type = "bug"
category = "done"
outcome = "wont-fix"
priority = "medium"
reporter = "human"
created = "2026-09-22T00:00:00Z"
updated = "2026-09-22T00:00:02Z"
aliases = ["T-5283"]
scope = ["src/frob/app/_config_external.py"]
+++

found while working T-draft-ac05cce9 (the T-5132 LEDGER_VERB_STRATEGY fix): _config_external.py's from_external allowlist never got ticket_points, ticket_points_value, ticket_unsized_ack, ticket_tokens_in, ticket_tokens_out, ticket_tokens_cache_read added -- every one of those CLI flags is silently dropped to its AppConfig default on a real frob invocation (only visible via direct AppConfig construction in tests, e.g. --points on new, --unsized-ack on start, and frob ticket points/tokens's own value are all affected). Blocked from fixing directly in T-draft-ac05cce9: src/frob/app/_config_external.py is leased by T-4702.

## Drop reason
- 2026-09-22: allowlist entries landed inside T-4702 (197238c35e) (absorbed by T-4702)

+++
id = "01M1QDTV211A9TXMZHP71EVB6R"
title = "[tokens] json_file: committed JSON export with drift check (A-026)"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
reporter = "human"
created = "2026-09-05T00:00:00Z"
updated = "2026-09-05T00:00:02Z"
aliases = ["crunk:T-0065"]
labels = ["component:crunk", "source:crunk"]
scope = ["src/crunk/spec/models.py", "src/crunk/spec/load.py", "src/crunk/tokens/**", "tests/unit/test_spec.py", "tests/unit/test_tokens.py", "tests/system/test_e2e_27_theme.py", "docs/design/subsystems/tokens.md", "docs/design/subsystems/spec.md", "docs/design/02-specification.md", "docs/commands/tokens.md"]

[[links]]
kind = "blocked-by"
target = "01M1QDTV1ZC490G7YY856GTCNB"

[[acceptance]]
text = "given [tokens] json_file configured, when bare crunk tokens runs, then the flat JSON token map is written; hand-editing it makes tokens --check exit 1 and TOKENS001 name it; unset means no write and no check"
bound = false
+++

Field finding A-026: a committed tokens.generated.json (T-0056's source-of-truth file) can only be produced by shell redirection and has no drift check, so a stale committed JSON passes tokens --check while the CSS matches. Design (r6 addendum, decided): TokensConfig gains json_file: str = '' (root-relative, exactly like tailwind.tokens_file); bare crunk tokens writes render_json(spec) there when set; check_tokens covers it with the same TokensStatus/which-file naming T-0063 lands for the theme file; --format json preview behavior unchanged. DOC LINES TO ADD VERBATIM (design decided by coordinator): tokens.md under the Tailwind theme rendering section: '- r6 (A-026): [tokens].json_file receives render_json(spec) on the bare write and the same drift treatment -- a committed flat JSON export is first-class, never a shell-redirection artifact.'; spec.md r6 bullet gains json_file alongside tokens_file; 02 [tailwind]/[tokens] schema comment gains the key with the one-line explanation; docs/commands/tokens.md documents it. Present-tense as implemented.

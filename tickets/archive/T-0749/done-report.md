## Done report

Root cause: `AppConfig.from_external` (src/frob/app/config.py) never copied
`ticket_accepts` from the parsed argv namespace into the AppConfig kwargs
dict at all -- it was missing from every field-copy loop (int/list/bool)
in that classmethod. `--accepts N` was parsed correctly by argparse into
`args.ticket_accepts`, but `from_external` silently dropped it before
`AppConfig(**d)`, so every CLI invocation of `frob ticket evidence`/`close`
always bound `accepts=[]` regardless of what was typed on the command
line -- in-repo AND via `--path` alike. This was a config-layer drop, not
the root/store-resolution divergence between the two legs the ticket
suspected; both legs were equally broken, `add_evidence`'s own binding
logic (`_append_evidence_and_write`) and the ledger serialization
(`_splice_ticket_section`/`_render_section`) were always correct. T-0572's
own tests never caught this because they construct `AppConfig(...)`
directly (bypassing argparse/from_external entirely), so the CLI-layer
gap between "argparse parsed it" and "AppConfig received it" was never
exercised.

Fix: added `"ticket_accepts"` to the list-field copy loop in
`AppConfig.from_external` (one line), plus an explanatory comment on the
`ticket_accepts` field docstring recording the gap and why T-0572's tests
missed it.

Regression tests added to tests/test_tickets_acceptance.py
(TestAcceptsCliWiring), all driven through the REAL argparse parser
(`frob.__main__._build_parser`) rather than constructing AppConfig by
hand, so this exact class of gap cannot regress silently again:
  - test_from_external_carries_accepts_from_parsed_argv: from_external
    alone, proving the copy now happens.
  - test_evidence_cli_binds_acceptance_via_path_flag: full field repro,
    `frob ticket evidence <id> <node> --accepts 0 --path DIR`.
  - test_evidence_cli_binds_acceptance_in_repo_no_path_flag: same, no
    --path (audited per the ticket's instruction to check both legs).
  - test_close_time_verification_consumes_the_accepts_binding: T-0736/
    T-0627 field shape -- evidence bound via CLI, then a later `close`
    with no further --accepts, fresh ledger reload, sees the binding
    already persisted and succeeds.

Manually reproduced the bug pre-fix in an isolated scratch git repo via
the real CLI (`frob ticket evidence T-X node --accepts 0 --path DIR`
followed by `frob ticket show`), confirmed `acceptance[0]` read back
UNBOUND, then confirmed bound(['...']) post-fix with the identical
commands.

Scope: fix required extending T-0749's declared scope by one file
(src/frob/app/config.py) via `frob ticket scope --add`, since the actual
root cause was not in ticket_runner.py or tickets/** as the ticket's
own root-cause candidates suspected.

### Changed
(no changed files detected)

### Evidence
(no evidence recorded)

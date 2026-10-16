# crunk-query

Pure queries over a crunk project: the ingested stylesheets ([`crunk_ingest::ProjectStyles`])
and the token set ([`crunk_tokens::TokenSet`]). Each query returns plain row types that derive
`Serialize` and `JsonSchema`; the `crunk` binary wraps them in the `query`, `map` and `explain`
verbs. Nothing here reads the disk or prints.

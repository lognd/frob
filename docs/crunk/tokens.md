# crunk tokens

- `crunk tokens` writes every configured file atomically: `tokens.css` (the optional
  `[tokens] header` line, a GENERATED banner, one `:root` block), the flat JSON export
  (`[tokens] json_file`) and the Tailwind theme mapping (`[tailwind] tokens_file`).
- `crunk tokens --target css|json|tailwind` previews one target on stdout and writes nothing.
  (`--target`, not `--format`, because `--format` is the global output-format flag.)
- `crunk tokens --check` exits 1 and names each drifted or missing file. CSS is compared byte
  for byte; JSON is compared after parsing, so a formatter rewrap is clean.

The renderers live in `crunk_tokens::export`; `generated_files` is the expected-bytes source
for the TOKENS001 rule.

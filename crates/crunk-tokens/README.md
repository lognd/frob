# crunk-tokens

The crunk design-token model (`TokenSet`) and its exporters; the `crunk tokens` verb lives in the
`crunk` crate (`crunk tokens [--target css|json|tailwind] [--check]`).

## Token exports

`crunk tokens` renders the token set of `crunk.toml` through one exporter per target; the
exporters live in `crunk_tokens::export` behind the `Exporter` trait, so the later targets (DTCG,
USS, a C# class) are further implementations, not new code paths.

| Target | File (from `crunk.toml`) | Drift compare |
|---|---|---|
| `css` | `[project] tokens_file`, resolved against `css_root`; always written | byte for byte |
| `tailwind` | `[tailwind] tokens_file`, resolved against the project root; skipped when unset | parsed JSON |
| `json` | `[tokens] json_file`, resolved against the project root; skipped when unset | parsed JSON |

- Output is byte-identical to the Python crunk (same header passthrough, banner, `-rgb` companions,
  sorted two-space JSON with ASCII escapes).
- Writes are atomic (temp file, fsync, rename). `--dry-run` lists the files without writing.
- Drift reads files with universal newlines, so a checkout that converts to CRLF is clean (the
  Python crunk behaves the same).
- `--target` replaces the Python crunk's `--format`, which is the global output format here.
- Bare scale keys that collide with Tailwind v3 default theme keys are reported as warnings (and in
  `data.collisions`) unless `[tailwind] namespace_keys` is on.
- `TOKENS001` takes its input from `crunk_tokens::export::check` (`DriftReport`), or from
  `render_managed` plus `compare` over text it read itself.

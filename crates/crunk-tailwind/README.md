# crunk-tailwind

Tailwind knowledge for crunk: default-theme key tables, the utility candidate parser and the
node runtime bridge.

## The runtime bridge (`crunk_tailwind::runtime`, feature `runtime`)

Tailwind's truth (which class compiles to which CSS, what the merged theme holds) exists only in
Tailwind, so the bridge runs the **project's own** `tailwindcss` (v3) or `@tailwindcss/node` (v4)
through `node` and the shipped `node/helper.mjs`. Node is a runtime dependency here and nowhere
else.

- **Safety.** The helper executes project code (the Tailwind config and its plugins). Every spawn
  goes through `gob-exec` with a scrubbed environment (`PATH`, `HOME`, `NODE_PATH`, `NODE_ENV`;
  never a secret-shaped variable), the project root as working directory, a timeout (20 s) and an
  output cap (8 MiB). A helper over either limit is killed and the error names the limit.
- **First-run notice.** Before a given config first runs for a project on this machine, a notice
  names the config, the node binary and the opt-outs (`--static`, `[tailwind] engine = "static"`).
  The acknowledgement is recorded under the user's state directory
  (`$XDG_STATE_HOME/crunk/exec-notice/`), never in the repository, and replays only when the
  resolved config path changes. `CRUNK_QUIET_EXEC_NOTICE=1` hides the text, not the record.
- **Unresolved, never clean.** No node on `PATH`, no `node_modules/tailwindcss`, static mode, an
  unsupported version or a missing v4 CSS entry yield `Evaluation::Unresolved(reason)` with the
  code `unresolved-by-tailwind`. Nothing crashes and nothing is skipped silently.
- **Caching.** Results are cached per (Tailwind version, config content) in one universe entry that
  merges candidates across runs. The key also covers the relative files the config and CSS entry
  import (`@import`, `@config`, `import ... from "./x"`, `require("./x")`), so regenerating a theme
  JSON invalidates the entry.
- **`doctor`.** `Runtime::doctor` returns the presence table (node, tailwindcss and its version,
  whether the helper runs) with issues and the static-fallback notice.

Tests run the real helper under real node against stub `tailwindcss`, `postcss` and
`@tailwindcss/node` modules, so they need `node` but no npm install; without node they skip
loudly unless `CRUNK_REQUIRE_NODE=1`. `CRUNK_REAL_TAILWIND_PROJECT` and `CRUNK_REAL_TAILWIND_CSS`
point one test at a real project.

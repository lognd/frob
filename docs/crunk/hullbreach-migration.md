# Switching hullbreach CI from the Python crunk to the Rust crunk

Status: current
Owner: crunk
Decisions: none
Audience: contributor

<!-- frob:ticket 01M4CXSH25SNDV9NGGJ1DF39BA -->

Phase 1 exit of `docs/design/crunk.md` section 9: the hullbreach platform's CI crunk step runs
the Rust `crunk` binary instead of `uv run crunk`. This page is the step to change and the
reasoned list of every divergence from the Python crunk (commit `8ce8c29f`, 0.1.1.dev57; see
`tests/crunk-parity/PROVENANCE`). The hullbreach repository is not part of this checkout, so the
workflow edit itself is made there; the commands below are what it changes to, and
`crates/crunk/tests/hullbreach_exit.rs` pins that the Rust crunk passes such a project and that
this list stays reasoned.

## The CI step

| Python step | Rust step | Why it differs |
|---|---|---|
| `uv run crunk check` | `crunk check` | Same verb and exit codes (0 ok, 1 findings at or above `--fail-on`, 2 usage, 3 config). No Python environment is needed. |
| `uv run crunk check --json` | `crunk check --json` | The document is the `gob.sibling/1` envelope with `product = "crunk"`; read findings from `data.findings`. |
| `uv run crunk tokens --format css` | `crunk tokens --target css` | `--format` is the global output format of every goblin binary, so the export selector is `--target`. |
| `uv run crunk tokens --check` | `crunk tokens --check` | Unchanged: exits 1 naming each missing or drifted file, never writes. |
| `uv run crunk query ... --no-cache` | `crunk query ...` | `--no-cache` is accepted and a no-op; queries always ingest fresh. |

Install the binary with `cargo install crunk` (or the release archive of the `crunk` tag), pinned
to a version, in place of `uv sync`. Before enabling the step as a required check, run it once
beside the Python step and compare the findings against the list below; any finding in neither
list is a bug to file against crunk.

## Divergences

Every row is a deliberate behaviour change, with the reason. "Source" is where the module-level
list lives next to the code.

### Findings and rules

| Divergence | Reason | Source |
|---|---|---|
| A `crunk:waive` with no reason, or a blank `reason=""`, grants nothing; the waived finding stays and WAIVE001 reports the waiver. Python silenced the rule and nagged separately. | A waiver is an accepted exception and an exception without a reason is not one; WAIVE001 is not waivable so it cannot silence itself. | `crates/crunk-rules/src/rules/waive001.rs` |
| COLOR001, SPACE001 and the other scale rules locate the finding at the offending token, not the declaration line, and the message names the nearest step (and the two bracketing steps for SPACE001). | Precise anchors let waivers and editors target the literal; the Python fix payload carried the nearest step. | `color001.rs`, `space001.rs`, `scales/mod.rs` |
| SPACE001 messages use the project's `[tokens]` prefixes, not a hard-coded `--space`. | Projects with a custom prefix got wrong names. | `space001.rs` |
| COLOR001, SPACE001 and the scale rules carry no autofix payload in the finding (`fix = Manual`); `crunk fix` owns fixes. | Fix logic moved to the `crunk-fix` crate. | `color001.rs`, `space001.rs` |
| COLOR002 counts a `var(--x)` as defined by the token export or by any custom property of any ingested sheet, and is Unresolved (never clean) when a source could not be indexed. Python knew only the export. | Absence is certified only after the whole space was searched. | `color002.rs` |
| A colour-looking literal that cannot be read (unsupported `color()` space, relative colour, malformed hex) is an Unresolved finding. | Never silently clean. | `color001.rs` |
| CONTRAST001 sits at the start of `crunk.toml` (Python: line 0) and is judged per declared mode against each role's own floor; APCA is advisory and opt-in. | A spec-level finding has no stylesheet line; modes are new. | `contrast001.rs` |
| RADIUS001 on a project with no declared radii is counted and reported as inapplicable (Python returned nothing). | A skipped rule must be visible. | `radius001.rs` |
| New rules with no Python counterpart: EXPORT001, EXPORT002, TOKEN002 to TOKEN009. They are absent from every Python golden. | Added after the Python capture; configure with `[lint]` (`off` drops them). | `crates/crunk/tests/query_parity.rs` |
| `crunk query violations` omits Unresolved findings, reports line 0 for a finding anchored at the start of a file and words messages as the Rust rules do; the Python `version` field is dropped. | The envelope carries the version; Unresolved is not a violation. | `docs/crunk/README.md` |
| `crunk query dupes` scores whole sheets by shared `(property, value)` declarations over the smaller sheet. | The Rust scoring is defined on whole sheets rather than per rule. | `crates/crunk-query` |

### Ingest (CSS, JSX, Tailwind)

| Divergence | Reason | Source |
|---|---|---|
| Spans are byte offsets (Python: code points). | Equal on ASCII; bytes are what editors and fixers need. | `crates/crunk-ingest/src/lib.rs` |
| The walk honors `.gitignore`: an ignored `.css` is not ingested and is not "ungoverned". | Generated and vendored output should not produce findings. | `crates/crunk-ingest/src/lib.rs` |
| CSS nesting and `@container`, `@scope`, `@starting-style` blocks are ingested. | Python dropped their declarations silently, hiding violations. | `crates/crunk-ingest/src/lib.rs` |
| A named file outside `css_root` is skipped (Python raised); a malformed `crunk:waive` comment becomes a diagnostic (Python ignored it). | One bad path must not abort the run; a typo must not silently waive nothing. | `crates/crunk-ingest/src/lib.rs` |
| Parse errors read `css syntax error at line N` and `jsx syntax error at line N`. | Parser messages are not a stable contract. | `crates/crunk-ingest/src/lib.rs`, `jsx/mod.rs` |
| JSX style keys are the CSS spelling (`WebkitMask` is `-webkit-mask`); a custom property keeps its case. | Python lowercased both. | `jsx/mod.rs` |
| React's full unitless list applies (`flex: 1` is no length). | Python covered seven properties and read `flex: 1` as `1px`. | `jsx/mod.rs` |
| `style={{...} as CSSProperties}` and wrapped objects are read; a string value with an escape keeps its whole raw text. | Python skipped or truncated them. | `jsx/mod.rs` |
| `createElement` identifiers resolve through the scope and module graph; unresolved sites and `className` parts that are not static are recorded in `dynamic_classes`. Callee recognition is by name. | Python skipped them silently or classified by import. | `jsx/mod.rs` |
| Tailwind: numeric theme values are kept as text, same-file spreads and member accesses are evaluated, theme collisions with Tailwind defaults are facts with waivers, and a `.css` `[tailwind] config` is the v4 entry. An entry in a subdirectory needs `[tailwind] css_entry`; non-`.json` relative imports are not followed. | Python dropped these or only logged a warning. | `crates/crunk-ingest/src/tailwind/mod.rs` |
| Glob matching keeps Python `fnmatch` semantics for `[org] entry`, `[org] ignore` and `[jsx] globs`. | Not a divergence; listed so nobody rewrites a glob. | `crates/crunk-ingest/src/glob.rs` |

### Spec, values and tokens

| Divergence | Reason | Source |
|---|---|---|
| `crunk.toml` value types are strict: `root_font_size = "16"` is rejected (pydantic coerced it). | Typed config; the error names the key and a suggestion. | `crates/crunk-spec/src/lib.rs` |
| Paths are normalized lexically and never resolved through symlinks. | Deterministic across machines. | `crates/crunk-spec/src/lib.rs` |
| `format_step` and token rendering print a step below `1e-4` positionally, not as `1e-05`. | CSS and tooling read positional numbers reliably. | `crates/crunk-spec/src/naming.rs`, `crates/crunk-tokens/src/model.rs` |
| Digits in colour and length literals are ASCII only; rejections are typed errors instead of `Nothing`. | Python `\d` accepted other Unicode digits. | `crates/crunk-values/src/lib.rs` |
| Tables owned by shared crates (`[check]`, `[perf]`, ...) are accepted and left to their owners. | The goblin family shares one config file. | `crates/crunk-spec/src/lib.rs` |
| `crunk tokens --target` replaces `--format` (see the step table). | `--format` is the global output format. | `crates/crunk/src/tokens.rs` |

### Not yet at parity

- Playwright-backed gallery and web-page scenarios were never captured (no browser in the
  capture environment, `PROVENANCE`); `crunk gallery check` is opt-in (`--features gallery`).
  Keep the Python gallery step until hullbreach adopts the Rust gallery.
- The gallery manifest shapes were rebuilt from the design notes (README, "Gallery (opt-in)").

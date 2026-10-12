//! The directive DSL: derive support, comment scanner, binding and the PARSE
//! and DSL rules (code-model section 4, decisions D24 and D32).
//!
//! # Overview
//!
//! - [`Directive`]: implemented by `#[derive(Directive)]` on a struct with
//!   `#[directive(namespace = "frob", verb = "ticket")]`; fields carry
//!   `#[arg(positional)]`, `#[arg(key = "because")]`, `#[arg(list)]`,
//!   `optional` and `ticket_ref`. The derive also emits a [`DirectiveMeta`]
//!   (docs and [`DirectiveMeta::json_schema`]) and an `inventory` entry that
//!   [`all_directives`] lists.
//! - [`Scanner`]: finds `<namespace>:<verb> <args>` at the start of a comment
//!   line (Rust `//`, `///`, `//!`, `/* */` via the syntax tree; markdown
//!   `<!-- -->` outside code blocks; TOML `#`), returning
//!   [`DirectiveRecord`]s and findings.
//! - Rules [`Parse001`] (malformed directive), [`Dsl001`] (unknown verb with
//!   did-you-mean) and [`Dsl002`] (abbreviated ticket id).
//! - [`frob`]: the milestone-1 verbs `ticket`, `todo`, `doc`, `tests`,
//!   `invariant`, `accept`, `defer`, and the milestone-2 claim verbs `effects`,
//!   `pure`, `honest`, `core`, `shell`, `hook`, `dispatcher`, `idempotent`,
//!   `trusted`, `calls` (parsed only; see [`EffectSet`] for the effect grammar).
//!
//! # Grammar
//!
//! Arguments are whitespace separated: a bare word, `key=value`, or
//! `key="quoted value"` (`\"` and `\\` escapes). Positionals fill the
//! positional fields in order; a `list` field takes the rest. Unknown
//! namespaces are ignored; one directive per comment line. A trailing foreign
//! pragma (`# noqa`, `// eslint-disable-line`, `# type: ignore`) ends the
//! arguments. A line ending in `\` continues onto the next comment line
//! (`#`, `//`, block-comment `*`), joining directly even mid-token. The v1
//! forms `note="..."` on `frob:todo` and `reason="..."` on `frob:invariant`
//! are read as trailing text and reported as DSL002 with a `--fix` rewrite.
//!
//! # Binding
//!
//! A directive binds to the outermost symbol starting within two lines after
//! it, else the innermost symbol enclosing it, else the file. Inner doc
//! comments (`//!`) and markdown comments skip the first step (markdown binds
//! to the preceding heading). A `tests` directive written inside a test item
//! binds to its named target, recording the test in
//! [`DirectiveRecord::source`].

// The derive expands to `::gob_directives::...`, which must resolve here too.
extern crate self as gob_directives;

mod args;
mod bind;
mod comments;
mod compat;
mod config;
mod effects;
pub mod frob;
pub mod grimble;
mod lex;
mod meta;
mod rules;
mod scan;
mod ulid;
mod wire;

pub use args::{ArgError, ArgKind, ArgList, ArgMeta, Cursor, FromArg, FromArgs, Keyed, Token};
pub use bind::Binding;
pub use config::DirectivesConfig;
pub use effects::{EffectAlias, EffectAtom, EffectBase, EffectSet, EffectsClaim, effects_claim};
pub use gob_macros::Directive;
pub use inventory;
pub use meta::{Directive, DirectiveEntry, DirectiveMeta, all_directives, validate};
pub use rules::{Dsl001, Dsl002, Parse001};
pub use scan::{DirectiveRecord, NOT_ATTACHED, REORIENT_VERB, ScanConfig, ScanResult, Scanner};
// frob:ticket 01M4GK42XB93XT5TFDQDRQ36JC
pub use ulid::{is_full_ulid, is_v1_alias, looks_like_ticket_ref};
pub use wire::{WIRE_VERSION, decode_records, encode_records};

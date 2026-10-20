//! Output contract: JSON envelope, exit-code table, text and JSON renderers.
//!
//! Text is a view over the same data as the JSON envelope (cli.md section 2).
//! Exit conversion note: this crate never names the standard process module
//! (PROC001), so [`ExitCode`] converts to `i32` and the binary builds its
//! own process exit value from that.

mod command;
mod envelope;
mod escape;
mod exit;
mod record;
mod refusal;
mod required;
mod source;
mod text;

pub use command::{RemedyCommand, RemedyFlag};
pub use envelope::{Envelope, EnvelopeError, SCHEMA_VERSION, envelope_schema, render_json};
pub use escape::{escape_for_origin, escape_line, escape_non_ascii, escape_text, is_dangerous};
pub use exit::{ExitCode, fail_on};
pub use gob_rules::RequiredReason;
pub use record::{
    EditRecord, FindingRecord, FixRecord, SecurityDecisionKind, Summary, TextOrigin,
    is_plugin_unfinished,
};
pub use refusal::{Refusal, RefusalClass};
pub use required::UnresolvedPolicy;
pub use source::{MemorySources, SourceProvider};
pub use text::{
    Annotations, ColorChoice, FindingNotes, Report, SecondarySpan, TextOptions, is_tty,
    render_text, render_text_annotated, render_text_with_decisions, severity_label,
};

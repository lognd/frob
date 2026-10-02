//! Output contract: JSON envelope, exit-code table, text and JSON renderers.
//!
//! Text is a view over the same data as the JSON envelope (cli.md section 2).
//! Exit conversion note: this crate never names the standard process module
//! (PROC001), so [`ExitCode`] converts to `i32` and the binary builds its
//! own process exit value from that.

mod envelope;
mod exit;
mod record;
mod refusal;
mod required;
mod source;
mod text;

pub use envelope::{Envelope, EnvelopeError, SCHEMA_VERSION, envelope_schema, render_json};
pub use exit::{ExitCode, fail_on};
pub use gob_rules::RequiredReason;
pub use record::FindingRecord;
pub use refusal::{Refusal, RefusalClass};
pub use required::UnresolvedPolicy;
pub use source::{MemorySources, SourceProvider};
pub use text::{ColorChoice, Report, TextOptions, is_tty, render_text, severity_label};

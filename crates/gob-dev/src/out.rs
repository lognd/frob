//! The one place the generator writes to stdout.

use std::io::Write as _;

/// Write `text` and a newline to stdout; the single output function of the crate.
pub fn emit(text: &str) {
    let mut out = std::io::stdout().lock();
    // A closed pipe is not worth failing a generation run over.
    if writeln!(out, "{text}").is_err() {
        tracing::debug!("stdout closed while emitting");
    }
}

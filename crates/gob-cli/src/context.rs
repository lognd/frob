//! The resolved global flags handed to every verb.

use std::path::PathBuf;

use clap::ValueEnum;
use gob_diagnostics::ColorChoice;

/// `--format`: how the result is rendered.
#[derive(Debug, Clone, Copy, PartialEq, Eq, ValueEnum)]
pub enum FormatChoice {
    /// JSON when stdout is not a terminal, text when it is.
    Auto,
    /// The JSON envelope.
    Json,
    /// Human text, a view over the same envelope.
    Text,
}

/// `--color`: when to emit ANSI escapes in text output.
#[derive(Debug, Clone, Copy, PartialEq, Eq, ValueEnum)]
pub enum ColorMode {
    /// Color when stdout is a terminal and `NO_COLOR` is unset.
    Auto,
    /// Always color.
    Always,
    /// Never color.
    Never,
}

/// Global flags after resolution; verbs read this, never raw argv.
#[derive(Debug, Clone)]
pub struct Context {
    /// Absolute working directory (`--cwd` or the process directory).
    pub cwd: PathBuf,
    /// Resolved color policy for text output.
    pub color: ColorChoice,
    /// True when the result is rendered as the JSON envelope.
    pub json: bool,
    /// Count of `-v` flags.
    pub verbosity: u8,
    /// `--quiet`: suppress text output on success.
    pub quiet: bool,
    /// `--dry-run` was passed (only verbs that opt in accept it).
    pub dry_run: bool,
}

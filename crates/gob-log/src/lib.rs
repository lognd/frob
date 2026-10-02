//! Logging and redaction shared by every goblin.
//!
//! Products install one subscriber via [`init`] and never `println!`
//! outside their renderer crate: anything written to stderr goes through
//! the tracing layers built here. `FROB_LOG` is the one documented
//! diagnostic environment variable; it takes `tracing` env-filter
//! directives such as `gob_git=debug,warn`. [`redact`] masks secret-shaped
//! strings before output is stored as evidence or logged.

mod init;
mod redact;
#[cfg(any(test, feature = "test-util"))]
pub mod testing;

pub use init::{InitError, LOG_ENV, init};
pub use redact::{REDACTED, redact};

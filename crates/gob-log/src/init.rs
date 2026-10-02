//! Subscriber construction and installation.

use std::io::IsTerminal;

use thiserror::Error;
use tracing_subscriber::fmt::format::FmtSpan;
use tracing_subscriber::layer::SubscriberExt;
use tracing_subscriber::util::SubscriberInitExt;
use tracing_subscriber::{EnvFilter, Layer, Registry};

/// Name of the one documented diagnostic environment variable.
pub const LOG_ENV: &str = "FROB_LOG";

/// Failure to install the global subscriber.
#[derive(Debug, Error)]
pub enum InitError {
    /// `FROB_LOG` held directives that do not parse.
    #[error("invalid {LOG_ENV} filter {spec:?}: {source}")]
    Filter {
        /// The offending filter text.
        spec: String,
        /// Parse failure from the env-filter.
        #[source]
        source: tracing_subscriber::filter::ParseError,
    },
    /// `FROB_LOG` was set but is not valid unicode.
    #[error("{LOG_ENV} is not valid unicode")]
    NotUnicode,
    /// A global subscriber was already installed.
    #[error("a global tracing subscriber is already installed")]
    AlreadyInitialized(#[source] tracing_subscriber::util::TryInitError),
}

/// Default level directive for a `-v` count: 0 warn, 1 info, 2 debug, 3+ trace.
pub(crate) fn default_directive(verbosity: u8) -> &'static str {
    match verbosity {
        0 => "warn",
        1 => "info",
        2 => "debug",
        _ => "trace",
    }
}

/// Builds the filter from an explicit spec, falling back to the verbosity default.
pub(crate) fn build_filter(spec: Option<&str>, verbosity: u8) -> Result<EnvFilter, InitError> {
    match spec.map(str::trim).filter(|s| !s.is_empty()) {
        Some(s) => EnvFilter::try_new(s).map_err(|source| InitError::Filter {
            spec: s.to_owned(),
            source,
        }),
        None => Ok(EnvFilter::new(default_directive(verbosity))),
    }
}

/// Installs the global subscriber for `product`.
///
/// Events go to stderr as human text, or as JSON lines when `json` is set.
/// The filter comes from `FROB_LOG` when set, else from `verbosity`
/// (0 warn, 1 info, 2 debug, 3+ trace). Span close events carry timing so
/// command spans report their duration.
///
/// # Errors
///
/// Returns [`InitError`] if `FROB_LOG` is invalid, or if a global
/// subscriber is already installed (a second call never panics).
pub fn init(product: &str, verbosity: u8, json: bool) -> Result<(), InitError> {
    let spec = match std::env::var(LOG_ENV) {
        Ok(s) => Some(s),
        Err(std::env::VarError::NotPresent) => None,
        Err(std::env::VarError::NotUnicode(_)) => return Err(InitError::NotUnicode),
    };
    let filter = build_filter(spec.as_deref(), verbosity)?;
    let layer: Box<dyn Layer<Registry> + Send + Sync> = if json {
        tracing_subscriber::fmt::layer()
            .json()
            .with_writer(std::io::stderr)
            .with_span_events(FmtSpan::CLOSE)
            .boxed()
    } else {
        tracing_subscriber::fmt::layer()
            .with_writer(std::io::stderr)
            .with_ansi(std::io::stderr().is_terminal())
            .with_span_events(FmtSpan::CLOSE)
            .boxed()
    };
    tracing_subscriber::registry()
        .with(layer.with_filter(filter))
        .try_init()
        .map_err(InitError::AlreadyInitialized)?;
    tracing::debug!(product, verbosity, json, "logging initialised");
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn verbosity_maps_to_levels() {
        assert_eq!(default_directive(0), "warn");
        assert_eq!(default_directive(1), "info");
        assert_eq!(default_directive(2), "debug");
        assert_eq!(default_directive(9), "trace");
    }

    #[test]
    fn invalid_spec_is_an_error() {
        assert!(matches!(
            build_filter(Some("gob_git=loud"), 0),
            Err(InitError::Filter { .. })
        ));
    }

    #[test]
    fn empty_spec_uses_default() {
        assert!(build_filter(Some("  "), 1).is_ok());
        assert!(build_filter(None, 1).is_ok());
    }

    #[test]
    fn second_init_is_an_error_not_a_panic() {
        // The first call may fail only if another test installed a global; either way
        // the second must return Err(AlreadyInitialized).
        let _ = init("frob", 0, false);
        assert!(matches!(
            init("frob", 0, true),
            Err(InitError::AlreadyInitialized(_))
        ));
    }
}

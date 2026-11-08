//! Typed errors of text measurement.

// frob:ticket 01M5XCWY5RFEP343E8Z6XH9D6C

/// Why a text measurement could not be produced.
#[derive(Debug, Clone, PartialEq, Eq, thiserror::Error)]
pub enum TextError {
    /// The requested font family is not one of the bundled fonts.
    #[error("font '{font}' is not in the bundle (bundled: {bundled})")]
    FontNotBundled {
        /// The family name that was asked for.
        font: String,
        /// Comma-separated bundled family names.
        bundled: String,
    },
}

//! Typed errors of the layout-solve output.

// frob:ticket 01M5XCWY267M72G3GPYE2ZAPQ5

/// Why a solve could not be turned into (or written as) layout-solve JSON.
#[derive(Debug, thiserror::Error)]
pub enum OutputError {
    /// A coordinate, size or metric is NaN or infinite (or overflows the 1/64 grid).
    #[error("non-finite value in `{field}` of {owner}")]
    NonFinite {
        /// What carries the value: `node 'id'` or `viewport`.
        owner: String,
        /// The offending field name.
        field: &'static str,
    },
    /// Serialization failed.
    #[error("layout-solve serialization failed: {0}")]
    Serialize(#[from] serde_json::Error),
}

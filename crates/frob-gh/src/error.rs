//! The typed errors of the GitHub client.

/// Everything the client can fail with; none is retried silently beyond the [`crate::ErrorPolicy`].
#[derive(Debug, thiserror::Error)]
pub enum Error {
    /// Neither `GH_TOKEN` nor `GITHUB_TOKEN` is set (or both are empty).
    #[error("no GitHub token: set GH_TOKEN or GITHUB_TOKEN (frob never reads gh's config)")]
    NoToken,
    /// The base URL is not `https`; the client refuses plain HTTP.
    #[error("refusing non-https base url {0}")]
    InsecureBase(String),
    /// The connection, TLS or body read failed.
    #[error("transport failure: {0}")]
    Transport(String),
    /// No recorded exchange matched (fixture transport only).
    #[error("no recorded exchange for {method} {url}")]
    Unrecorded {
        /// Request method.
        method: String,
        /// Request URL.
        url: String,
    },
    /// A non-success status that is not rate limiting.
    #[error("github answered {status} for {url}")]
    Status {
        /// HTTP status.
        status: u16,
        /// Request URL.
        url: String,
    },
    /// Rate limited with no budget left: the run stops without sleeping.
    #[error("rate limited with no budget left; window resets at {reset:?} (epoch seconds)")]
    RateLimited {
        /// `x-ratelimit-reset`, UTC epoch seconds, when reported.
        reset: Option<u64>,
    },
    /// A GraphQL response carried errors; the whole scope failed.
    #[error(transparent)]
    Graphql(#[from] crate::GraphqlFailure),
    /// Retry-able answers on every attempt the policy allows.
    #[error("still rate limited after {attempts} attempts")]
    RetriesExhausted {
        /// Attempts made, including the first.
        attempts: u32,
    },
    /// The body is not the JSON the caller asked for.
    #[error("invalid json body: {0}")]
    Json(String),
}

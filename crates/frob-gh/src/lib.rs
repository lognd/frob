//! GitHub over HTTPS for frob (docs/design/mirror.md 3.2, git-io.md 4, security.md network rules).
//!
//! - [`Client`]: REST and GraphQL calls over a [`Transport`], conditional requests through an
//!   in-memory `ETag` cache, rate-limit headers surfaced as [`RateLimit`] (or `None`), and
//!   `Retry-After` backoff bounded by [`Policy`].
//! - [`Token`]: read from `GH_TOKEN` or `GITHUB_TOKEN` only; never from `gh`'s config; redacted
//!   in every `Debug` rendering.
//! - [`ReqwestTransport`]: the live transport (HTTPS only, redirects off).
//! - [`FixtureTransport`]: replays recorded exchanges and refuses anything unrecorded, so tests
//!   never touch the network.
//!
//! The stop-instead-of-sleep rule, the 60 s doubling and GraphQL `errors` arrays belong to the
//! error-policy ticket, which builds on this client.

mod client;
mod culprit;
mod error;
mod fixture;
mod live;
mod rate;
mod token;
mod transport;

pub use client::{Client, Method, Pause, Policy, Reply, TokioPause};
pub use culprit::{
    BLOCKS_LANDS_LABEL, Commit, Culprit, CulpritError, FixTicket, LAND_PREFIX, RunRecord, Verdict,
    find_culprit,
};
pub use error::Error;
pub use fixture::{Exchange, FixtureTransport, RecordedRequest, RecordedResponse};
pub use live::ReqwestTransport;
pub use rate::RateLimit;
pub use token::Token;
pub use transport::{RawRequest, RawResponse, Transport};

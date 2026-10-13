//! GitHub over HTTPS for frob (docs/design/mirror.md 3.2, git-io.md 4, security.md network rules).
//!
//! - [`Client`]: REST and GraphQL calls over a [`Transport`], conditional requests through an
//!   in-memory `ETag` cache, rate-limit headers surfaced as [`RateLimit`] (or `None`), and
//!   retries via [`ErrorPolicy`].
//! - [`Token`]: read from `GH_TOKEN` or `GITHUB_TOKEN` only; never from `gh`'s config; redacted
//!   in every `Debug` rendering.
//! - [`ReqwestTransport`]: the live transport (HTTPS only, redirects off).
//! - [`FixtureTransport`]: replays recorded exchanges and refuses anything unrecorded, so tests
//!   never touch the network.
//!
//! The stop-instead-of-sleep rule, the 60 s doubling ([`send_with_policy`]) and GraphQL `errors`
//! arrays ([`parse_response`]) live in the policy and graphql modules.

pub mod capabilities;
mod client;
mod culprit;
mod error;
mod fixture;
mod graphql;
mod live;
mod policy;
mod rate;
mod token;
mod transport;

pub use client::{Client, Method, Pause, Reply, TokioPause};
pub use culprit::{
    BLOCKS_LANDS_LABEL, Commit, Culprit, CulpritError, FixTicket, LAND_PREFIX, RunRecord, Verdict,
    find_culprit,
};
pub use error::Error;
pub use fixture::{Exchange, FixtureTransport, RecordedRequest, RecordedResponse};
pub use graphql::{GraphqlFailure, parse_response};
pub use live::ReqwestTransport;
pub use policy::{ErrorPolicy, Halt, send_with_policy};
pub use rate::RateLimit;
pub use token::Token;
pub use transport::{RawRequest, RawResponse, Transport};

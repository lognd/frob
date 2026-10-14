//! Tests that link the sibling products (`grimble`, `crunk`) into the test binary.
//!
//! Linking a sibling registers its config sections and verbs in this process, so these tests stay out
//! of the `it` binary, where frob runs in process and must see only frob's own registry.
// frob:ticket 01M4CTE9W9QH6SBZSJ3E0E8M28
#[path = "../it/common/mod.rs"]
mod common;
mod remedies;
mod web_conformance;

//! `.grmb` support that needs no tree-sitter grammar (grmb-spec 9, ticket G08).
//!
//! The grimble model language has a hand-written parser (`grimble-model`), so it has no
//! entry in the feature-gated grammar table. This module gives the rest of the workspace
//! the two facts it needs from here: detection by extension and a cache-key identity.
//!
//! It is deliberately not a [`crate::Language`] variant yet: adding one breaks the
//! exhaustive matches in `gob-directives` (`comments::segments`) and `frob-obligations`
//! (`comments::comment_lines`), which are outside the scope of the ticket that added this.

// frob:ticket 01M3Z713VGKF4Z0JJ3263XJMC3

use std::path::Path;

/// The language tag of `.grmb` files in U terms and cache keys.
pub const NAME: &str = "grmb";

/// The file extension that selects the grimble model language.
pub const EXTENSION: &str = "grmb";

/// The version of the hand-written parser's identity: this crate's version.
const VERSION: &str = env!("CARGO_PKG_VERSION");

/// True when `path` is a `.grmb` file (extension, case-insensitive).
pub fn is_grmb_path(path: impl AsRef<Path>) -> bool {
    let found = path
        .as_ref()
        .extension()
        .and_then(|e| e.to_str())
        .is_some_and(|e| e.eq_ignore_ascii_case(EXTENSION));
    tracing::trace!(path = %path.as_ref().display(), found, "grmb detect");
    found
}

/// Identity string for the `.grmb` parser, for cache keys: no grammar crate, so the crate version.
pub fn grammar_identity() -> String {
    format!("{NAME}:hand-written@{VERSION}:no-tree-sitter")
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn detects_by_extension() {
        assert!(is_grmb_path("design/frob.grmb"));
        assert!(is_grmb_path("X.GRMB"));
        assert!(!is_grmb_path("a.rs"));
        assert!(!is_grmb_path("grmb"));
    }

    #[test]
    fn identity_comes_from_the_crate_version() {
        assert_eq!(grammar_identity(), format!("grmb:hand-written@{VERSION}:no-tree-sitter"));
    }
}

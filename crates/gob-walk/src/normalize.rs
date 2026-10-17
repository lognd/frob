//! The seam through which a git-aware crate supplies "content as git would store it".
//!
//! gob-walk must not link a git implementation (it sits under the pure model crates), so it
//! defines the reader traits and a link-time provider registry. A crate that can normalize
//! (gob-git) implements [`NormalizedSource`] and submits a [`SourceProvider`] with
//! `inventory::submit!`; any binary that links it gets normalized digests with no wiring, and
//! one that does not reads raw bytes.

// frob:ticket 01M4CTE0GYDX0XW64JRNF2ZMQG

use std::error::Error;
use std::fmt::Debug;
use std::path::Path;
use std::sync::Arc;

/// Boxed error a [`NormalizedReader`] reports; the caller logs it and falls back to raw bytes.
pub type NormalizeError = Box<dyn Error + Send + Sync>;

/// Reads files of one source, reusing whatever expensive state (filter pipeline) it builds.
pub trait NormalizedReader {
    /// The bytes git would store for `rel` (source-root relative), or `None` when absent.
    ///
    /// # Errors
    /// Any failure of the normalization pipeline; callers fall back to raw bytes.
    fn read(&mut self, rel: &str) -> Result<Option<Vec<u8>>, NormalizeError>;
}

/// A thread-safe handle on a normalizing content origin; opens a fresh reader per use.
pub trait NormalizedSource: Send + Sync + Debug {
    /// Calls `f` exactly once with a reader over the current state of the origin.
    fn with_reader(&self, f: &mut dyn FnMut(&mut dyn NormalizedReader));
}

/// A link-time registered way to find a [`NormalizedSource`] for a directory.
pub struct SourceProvider {
    /// The source for `root` when this provider recognises it (for gob-git: inside a checkout).
    pub locate: fn(root: &Path) -> Option<Arc<dyn NormalizedSource>>,
}

inventory::collect!(SourceProvider);

/// The first registered provider's source for `root`, or `None` (raw reads).
pub(crate) fn locate_registered(root: &Path) -> Option<Arc<dyn NormalizedSource>> {
    inventory::iter::<SourceProvider>
        .into_iter()
        .find_map(|p| (p.locate)(root))
}

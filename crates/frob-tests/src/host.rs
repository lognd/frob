//! The host trait frob-tests' `#[rule]` declarations evaluate against.

// frob:ticket 01M48R02V2J0R5ZXWP9MXXGNZ3

use gob_directives::DirectiveRecord;
use gob_symbols::SymbolGraph;

/// What `TEST001` may ask of its product: the directives, the symbol graph and file text.
pub trait TestsHost {
    /// Every well-formed directive of the repository, in file then source order.
    fn directives(&self) -> &[DirectiveRecord];

    /// The symbol graph the `frob:tests` targets resolve against.
    fn graph(&self) -> &SymbolGraph;

    /// The text of the repository-relative file `path` (the `#[test]` attribute scan); `None` when unreadable.
    fn read_source(&self, path: &str) -> Option<String>;
}

//! Verb metadata registered by `#[derive(Command)]`.

use gob_diagnostics::ExitCode;

/// Static description of a verb, enough to generate the CLI reference.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct CommandMeta {
    /// Verb path, words separated by single spaces (`config show`).
    pub verb: &'static str,
    /// Product that ships the verb (`frob`).
    pub product: &'static str,
    /// True when repeating the same request is safe (`already: true`).
    pub idempotent: bool,
    /// True when the verb accepts `--dry-run`.
    pub dry_run: bool,
    /// Exit codes the verb declares it can return.
    pub exits: &'static [ExitCode],
    /// One-line summary from the doc comment.
    pub summary: &'static str,
    /// Module path of the declaring type.
    pub module: &'static str,
}

/// Implemented by `#[derive(Command)]`: the verb's static metadata.
pub trait Described {
    /// Metadata declared on the type.
    const META: CommandMeta;
}

/// An inventory record of one verb, submitted by `#[derive(Command)]`.
pub struct CommandEntry {
    meta: &'static CommandMeta,
}

impl CommandEntry {
    /// Wrap a verb's metadata for registration.
    pub const fn new(meta: &'static CommandMeta) -> Self {
        Self { meta }
    }
}

inventory::collect!(CommandEntry);

/// Every verb linked into the binary, sorted by product then verb.
pub fn all_commands() -> impl Iterator<Item = &'static CommandMeta> {
    let mut metas: Vec<&'static CommandMeta> =
        inventory::iter::<CommandEntry>().map(|e| e.meta).collect();
    metas.sort_by_key(|m| (m.product, m.verb));
    metas.into_iter()
}

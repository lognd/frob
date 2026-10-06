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

/// A verb whose summary starts with this is a deprecated alias of the form named in the first backticks.
///
/// It stays registered (output unchanged) but is hidden from help and the generated
/// reference, and prints one deprecation line on stderr (cli.md section 4.0, D104).
pub const DEPRECATED_PREFIX: &str = "Deprecated alias of `";

impl CommandMeta {
    /// The replacement form (`ticket show --format md`) when this verb is a deprecated alias.
    pub fn deprecated_form(&self) -> Option<&'static str> {
        let rest = self.summary.strip_prefix(DEPRECATED_PREFIX)?;
        rest.split_once('`').map(|(form, _)| form)
    }

    /// The one-line stderr note for a deprecated alias of `product`, or `None` for a live verb.
    pub fn deprecation_note(&self, product: &str) -> Option<String> {
        self.deprecated_form().map(|form| {
            format!(
                "{product}: `{}` is deprecated and will be removed in the next minor release; use `{product} {form}`",
                self.verb
            )
        })
    }
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

#[cfg(test)]
mod tests {
    use super::*;

    const fn meta(summary: &'static str) -> CommandMeta {
        CommandMeta {
            verb: "ticket brief",
            product: "frob",
            idempotent: true,
            dry_run: false,
            exits: &[ExitCode::Ok],
            summary,
            module: "m",
        }
    }

    #[test]
    fn a_deprecated_alias_names_its_replacement() {
        let m = meta("Deprecated alias of `ticket show --format md`, removed next minor.");
        assert_eq!(m.deprecated_form(), Some("ticket show --format md"));
        let note = m.deprecation_note("frob").expect("note");
        assert!(note.contains("`ticket brief` is deprecated"), "{note}");
        assert!(
            note.ends_with("use `frob ticket show --format md`"),
            "{note}"
        );
    }

    #[test]
    fn a_live_verb_has_no_note() {
        assert_eq!(meta("Show a ticket.").deprecation_note("frob"), None);
    }
}

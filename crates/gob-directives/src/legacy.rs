//! Deprecated `frob:` claim spellings and their DSL003 findings (cohesion.md 4, D120).

use gob_rules::{Applicability, Finding, Fix, FixKind, RuleId};
use gob_text::{FileId, Span, TextRange};

use crate::rules::Dsl003;

/// What a deprecated spelling becomes.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub(crate) enum Remedy {
    /// A `grimble:` verb, with optional extra argument words.
    Rename {
        /// The new verb in the `grimble` namespace.
        verb: &'static str,
        /// Words appended after the verb (`none` for `pure`).
        args: Option<&'static str>,
    },
    /// An `accept` exception on the named rule.
    Accept(&'static str),
    /// Nothing replaces it; the text says what to do instead.
    Drop(&'static str),
}

/// The deprecated `frob:` verbs.
const LEGACY: &[(&str, Remedy)] = &[
    (
        "effects",
        Remedy::Rename {
            verb: "effects",
            args: None,
        },
    ),
    (
        "core",
        Remedy::Rename {
            verb: "core",
            args: None,
        },
    ),
    (
        "shell",
        Remedy::Rename {
            verb: "shell",
            args: None,
        },
    ),
    (
        "calls",
        Remedy::Rename {
            verb: "calls",
            args: None,
        },
    ),
    (
        "pure",
        Remedy::Rename {
            verb: "effects",
            args: Some("none"),
        },
    ),
    (
        "honest",
        Remedy::Rename {
            verb: "effects",
            args: Some("honest"),
        },
    ),
    ("dispatcher", Remedy::Accept("NEAT031")),
    ("hook", Remedy::Accept("NEAT030")),
    (
        "trusted",
        Remedy::Drop(
            "accept the UNVERIFIED finding with `frob:accept <RULE> because=\"...\" until=...`",
        ),
    ),
    (
        "idempotent",
        Remedy::Drop(
            "bind a test of kind `idempotent` with `frob:tests`; the binding states the claim",
        ),
    ),
];

/// The remedy for the deprecated spelling `namespace:verb`, if it is one.
pub(crate) fn lookup(namespace: &str, verb: &str) -> Option<Remedy> {
    if namespace != "frob" {
        return None;
    }
    LEGACY.iter().find(|(v, _)| *v == verb).map(|(_, r)| *r)
}

/// The DSL003 finding for `frob:{verb}` over `range` (the `frob:verb` text), with its fix.
pub(crate) fn finding(
    verb: &str,
    remedy: Remedy,
    file: FileId,
    range: TextRange,
    anchor: &str,
) -> Finding {
    let meta = &Dsl003::META;
    let id: RuleId = meta
        .id
        .parse()
        .unwrap_or_else(|e| unreachable!("derive validated rule id {}: {e}", meta.id));
    let (message, fix) = match remedy {
        Remedy::Rename { verb: new, args } => {
            let to = args.map_or_else(
                || format!("grimble:{new}"),
                |a| format!("grimble:{new} {a}"),
            );
            (
                format!("`frob:{verb}` is deprecated; write `{to}`"),
                Some((FixKind::Deterministic, Applicability::Machine, to)),
            )
        }
        Remedy::Accept(rule) => {
            let to = format!("frob:accept {rule} because=\"state the reason\"");
            (
                format!("`frob:{verb}` is dropped; accept {rule} here with a reason instead"),
                Some((FixKind::FixIt, Applicability::HasPlaceholders, to)),
            )
        }
        Remedy::Drop(how) => (format!("`frob:{verb}` is dropped; {how}"), None),
    };
    tracing::debug!(verb, "deprecated directive spelling");
    let finding = Finding::new(
        id,
        meta.severity,
        Some(Span::new(file, range)),
        message,
        anchor,
    );
    match fix {
        Some((kind, applicability, to)) => finding.with_fix(Fix {
            kind,
            applicability,
            title: format!("replace `frob:{verb}` with `{to}`"),
            edits: vec![gob_rules::TextEdit {
                file,
                range,
                replacement: to,
            }],
        }),
        None => finding,
    }
}

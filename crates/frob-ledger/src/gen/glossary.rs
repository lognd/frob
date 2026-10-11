//! `GLOSSARY.md`: fields, states, links and handles as this repository is configured
//! (`navigation.md` sections 3.1 and 3.3).
//!
//! Every table is derived from the live declarations (the frontmatter schema, the category and
//! link enums) and from the repository's own `[tickets]` settings, never from the defaults, so
//! the page cannot drift from the code. [`check`] is the GEN001 cross-check that the page
//! documents exactly the schema's fields.
// frob:ticket 01M3ZX86CE8WDE9PJHNS90ZNMR

use std::collections::BTreeSet;
use std::fmt::Write as _;

use crate::id::RANDOM_LEN;
use crate::model::{Category, LinkKind, Outcome};
use crate::reindex::{GENERATED_MARKER_PREFIX, GenInput};
use crate::schema::{FrontmatterSchema, TicketSchema, TicketSchemaDescription};

/// Branch-relative path of the glossary.
pub const PATH: &str = "GLOSSARY.md";

/// Rule id reported by [`check`].
pub const GEN001: &str = "GEN001";

/// A glossary that disagrees with the schema (rule `GEN001`).
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum GlossaryDrift {
    /// A schema field has no entry in the glossary.
    MissingField(String),
    /// The glossary has an entry for a field the schema does not declare.
    UnknownField(String),
}

impl GlossaryDrift {
    /// The rule id, always `GEN001`.
    #[must_use]
    pub const fn rule(&self) -> &'static str {
        GEN001
    }
}

impl std::fmt::Display for GlossaryDrift {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::MissingField(k) => {
                write!(f, "{GEN001}: schema field `{k}` has no glossary entry")
            }
            Self::UnknownField(k) => {
                write!(f, "{GEN001}: glossary entry `{k}` is not a schema field")
            }
        }
    }
}

/// Escape `text` for one table cell.
fn cell(text: &str) -> String {
    text.replace('|', "\\|").replace(['\n', '\r'], " ")
}

/// One-line meaning of a workflow category.
const fn category_doc(c: Category) -> &'static str {
    match c {
        Category::Triage => "Awaiting a decision to accept the ticket.",
        Category::Todo => "Accepted and queued.",
        Category::InProgress => "Being worked; a lease is held.",
        Category::Done => "Terminal; carries an outcome.",
    }
}

/// One-line meaning of a `done` outcome.
const fn outcome_doc(o: Outcome) -> &'static str {
    match o {
        Outcome::Fixed => "The work was completed and verified.",
        Outcome::WontFix => "Deliberately not done.",
        Outcome::Duplicate => "Another ticket covers it.",
        Outcome::Invalid => "The report is not valid.",
        Outcome::Done => "Completed work with nothing to fix (a feature, a chore).",
    }
}

/// One-line meaning of a link kind, read from the ticket that carries it.
const fn link_doc(k: LinkKind) -> &'static str {
    match k {
        LinkKind::Blocks => "This ticket blocks the target.",
        LinkKind::BlockedBy => "The target blocks this ticket.",
        LinkKind::Relates => "Related; symmetric.",
        LinkKind::Duplicates => "This ticket duplicates the target.",
        LinkKind::DuplicatedBy => "The target duplicates this ticket.",
        LinkKind::Causes => "This ticket causes the target.",
        LinkKind::CausedBy => "The target causes this ticket.",
        LinkKind::SplitFrom => "This ticket was split out of the target.",
        LinkKind::Splits => "The target was split out of this ticket.",
        LinkKind::DiscoveredFrom => "This ticket was discovered while working the target.",
        LinkKind::Spawned => "The target was discovered while working this ticket.",
        LinkKind::EnablerFor => "This ticket enables the target story.",
        LinkKind::EnabledBy => "The target enables this story.",
        LinkKind::Supersedes => "This ticket supersedes the target.",
        LinkKind::SupersededBy => "The target supersedes this ticket.",
    }
}

/// Render the glossary for `schema` and the repository settings in `input`.
#[must_use]
pub fn render_for(schema: &TicketSchemaDescription, input: &GenInput<'_>) -> String {
    let as_of = input.as_of.unwrap_or("none");
    let min_len = input.handle_min_len.clamp(1, RANDOM_LEN);
    let mut out = format!(
        "{GENERATED_MARKER_PREFIX} v{}: DO NOT EDIT -->\n# Glossary\n\nAs of event {as_of}. Generated from this repository's effective configuration.\n\n",
        input.version
    );
    out.push_str("## Fields\n\n");
    out.push_str(&schema.docs_table());
    out.push_str("\n## States\n\n| Category | Meaning |\n|---|---|\n");
    for c in Category::ALL {
        let _ = writeln!(out, "| `{}` | {} |", c.as_str(), cell(category_doc(*c)));
    }
    out.push_str("\nA ticket in `done` carries one outcome:\n\n| Outcome | Meaning |\n|---|---|\n");
    for o in Outcome::ALL {
        let _ = writeln!(out, "| `{}` | {} |", o.as_str(), cell(outcome_doc(*o)));
    }
    out.push_str("\n## Links\n\n| Link | Inverse | Meaning |\n|---|---|---|\n");
    for k in LinkKind::ALL {
        let _ = writeln!(
            out,
            "| `{}` | `{}` | {} |",
            k.as_str(),
            k.inverse().as_str(),
            cell(link_doc(*k))
        );
    }
    let _ = write!(
        out,
        "\n## Handles\n\nA handle is `~` plus the shortest suffix of a ticket's random id part that no other ticket shares, never shorter than `handle_min_len`. In this repository `handle_min_len` is {min_len}, so handles are at least {min_len} characters (at most {RANDOM_LEN}).\n"
    );
    out
}

/// Render `GLOSSARY.md` for the ticket schema; a pure function of `input`.
#[must_use]
pub fn render(input: &GenInput<'_>) -> Vec<(String, Vec<u8>)> {
    vec![(
        PATH.to_owned(),
        render_for(FrontmatterSchema::describe(), input).into_bytes(),
    )]
}

/// The field keys the glossary page lists in its `## Fields` table.
fn documented_fields(page: &str) -> BTreeSet<String> {
    page.lines()
        .skip_while(|l| *l != "## Fields")
        .skip(1)
        .take_while(|l| !l.starts_with("## "))
        .filter_map(|l| l.strip_prefix("| `"))
        .filter_map(|l| l.split_once("` |").map(|(k, _)| k.to_owned()))
        .collect()
}

/// GEN001 cross-check: the glossary `page` must document exactly the fields of `schema`.
#[must_use]
pub fn check(page: &str, schema: &TicketSchemaDescription) -> Vec<GlossaryDrift> {
    let documented = documented_fields(page);
    let declared: BTreeSet<&str> = schema.fields.iter().map(|f| f.key).collect();
    let mut drift: Vec<GlossaryDrift> = schema
        .fields
        .iter()
        .filter(|f| !documented.contains(f.key))
        .map(|f| GlossaryDrift::MissingField(f.key.to_owned()))
        .collect();
    drift.extend(
        documented
            .iter()
            .filter(|k| !declared.contains(k.as_str()))
            .map(|k| GlossaryDrift::UnknownField(k.clone())),
    );
    drift
}

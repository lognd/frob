//! The frontmatter field table: names, types, which fields `update` may set.
//!
//! This is the hand-written stand-in for the `TicketField` derive (T-0028):
//! one declaration drives `ticket update` validation, the docs table and the
//! generic get/set used by events and the fold.

use std::fmt::Write as _;

use crate::id::TicketId;
use crate::model::{Category, Outcome, Points, Priority, Ticket, TicketType};

/// How a field's value is typed and parsed.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum FieldKind {
    /// Free text.
    Text,
    /// One of a closed set of spellings.
    Choice(&'static [&'static str]),
    /// Story points (Fibonacci 1..13).
    Points,
    /// A list of strings.
    List,
    /// A ticket id.
    TicketRef,
    /// An RFC 3339 instant.
    Instant,
    /// A list of objects (links, acceptance); never set through `update`.
    Objects,
}

/// Description of one frontmatter field.
#[derive(Debug, Clone, Copy)]
pub struct FieldDescription {
    /// Key in the frontmatter and in `field` events.
    pub name: &'static str,
    /// Value type.
    pub kind: FieldKind,
    /// True when the field may be absent.
    pub optional: bool,
    /// True when `ticket update --set` may change it.
    pub settable: bool,
    /// One-line description.
    pub doc: &'static str,
}

const fn f(
    name: &'static str,
    kind: FieldKind,
    optional: bool,
    settable: bool,
    doc: &'static str,
) -> FieldDescription {
    FieldDescription {
        name,
        kind,
        optional,
        settable,
        doc,
    }
}

/// Every frontmatter field, in file order.
pub const FIELDS: &[FieldDescription] = &[
    f(
        "id",
        FieldKind::TicketRef,
        false,
        false,
        "ULID of the ticket; also its directory name",
    ),
    f("title", FieldKind::Text, false, true, "One-line title"),
    f(
        "type",
        FieldKind::Choice(TicketType::NAMES),
        false,
        true,
        "Ticket type",
    ),
    f(
        "flavour",
        FieldKind::Text,
        true,
        true,
        "Free-form flavour such as user_story",
    ),
    f(
        "category",
        FieldKind::Choice(Category::NAMES),
        false,
        false,
        "Workflow category; changed by transitions only",
    ),
    f(
        "outcome",
        FieldKind::Choice(Outcome::NAMES),
        true,
        false,
        "Why the ticket is done; set by close and drop",
    ),
    f(
        "priority",
        FieldKind::Choice(Priority::NAMES),
        false,
        true,
        "low, medium, high or critical",
    ),
    f(
        "points",
        FieldKind::Points,
        true,
        true,
        "Story points: 1, 2, 3, 5, 8 or 13",
    ),
    f("parent", FieldKind::TicketRef, true, true, "Parent ticket"),
    f(
        "reporter",
        FieldKind::Text,
        false,
        false,
        "Who filed the ticket",
    ),
    f(
        "assignee",
        FieldKind::Text,
        true,
        true,
        "Who owns the ticket",
    ),
    f("created", FieldKind::Instant, false, false, "Creation time"),
    f(
        "updated",
        FieldKind::Instant,
        false,
        false,
        "Time of the latest event",
    ),
    f("persona", FieldKind::Text, true, true, "Story persona"),
    f(
        "capability",
        FieldKind::Text,
        true,
        true,
        "Story capability",
    ),
    f(
        "outcome_text",
        FieldKind::Text,
        true,
        true,
        "Story outcome (so that ...)",
    ),
    f(
        "idempotency_key",
        FieldKind::Text,
        true,
        false,
        "Key that deduplicated ticket new",
    ),
    f(
        "aliases",
        FieldKind::List,
        true,
        true,
        "Ids from other systems, such as v1 T-0042",
    ),
    f("labels", FieldKind::List, true, true, "Labels"),
    f("scope", FieldKind::List, true, true, "Write-scope globs"),
    f(
        "links",
        FieldKind::Objects,
        true,
        false,
        "Typed links; changed by link and unlink",
    ),
    f(
        "acceptance",
        FieldKind::Objects,
        true,
        false,
        "Acceptance criteria",
    ),
    f(
        "body",
        FieldKind::Text,
        true,
        true,
        "Markdown body (the text after the frontmatter)",
    ),
];

/// The description of `name`, if it is a field.
pub fn field(name: &str) -> Option<&'static FieldDescription> {
    FIELDS.iter().find(|d| d.name == name)
}

/// The names `ticket update --set` accepts.
pub fn settable_names() -> Vec<&'static str> {
    FIELDS
        .iter()
        .filter(|d| d.settable)
        .map(|d| d.name)
        .collect()
}

/// A markdown table of the fields, for generated documentation.
pub fn docs_table() -> String {
    let mut out = String::from(
        "| Field | Type | Required | Settable | Description |\n|---|---|---|---|---|\n",
    );
    for d in FIELDS {
        let ty = match d.kind {
            FieldKind::Text => "text".to_owned(),
            FieldKind::Choice(names) => names.join(" \\| "),
            FieldKind::Points => "points".to_owned(),
            FieldKind::List => "list".to_owned(),
            FieldKind::TicketRef => "ticket id".to_owned(),
            FieldKind::Instant => "RFC 3339".to_owned(),
            FieldKind::Objects => "objects".to_owned(),
        };
        let _ = writeln!(
            out,
            "| `{}` | {ty} | {} | {} | {} |",
            d.name,
            if d.optional { "no" } else { "yes" },
            if d.settable { "yes" } else { "no" },
            d.doc
        );
    }
    out
}

fn strings(v: &[String]) -> toml::Value {
    toml::Value::Array(v.iter().cloned().map(toml::Value::String).collect())
}

fn opt_text(v: Option<&String>) -> Option<toml::Value> {
    v.cloned().map(toml::Value::String)
}

/// The current value of a settable field of `t`, as a TOML value (`None` when unset).
pub fn get_field(t: &Ticket, name: &str) -> Option<toml::Value> {
    let fm = &t.front;
    let list = |v: &Vec<String>| (!v.is_empty()).then(|| strings(v));
    match name {
        "title" => Some(toml::Value::String(fm.title.clone())),
        "type" => Some(toml::Value::String(fm.ty.to_string())),
        "flavour" => opt_text(fm.flavour.as_ref()),
        "priority" => Some(toml::Value::String(fm.priority.to_string())),
        "points" => fm.points.map(|p| toml::Value::Integer(i64::from(p.get()))),
        "parent" => fm.parent.map(|p| toml::Value::String(p.to_string())),
        "assignee" => opt_text(fm.assignee.as_ref()),
        "persona" => opt_text(fm.persona.as_ref()),
        "capability" => opt_text(fm.capability.as_ref()),
        "outcome_text" => opt_text(fm.outcome_text.as_ref()),
        "aliases" => list(&fm.aliases),
        "labels" => list(&fm.labels),
        "scope" => list(&fm.scope),
        "body" => (!t.body.is_empty()).then(|| toml::Value::String(t.body.clone())),
        _ => None,
    }
}

fn want_text(name: &str, v: &toml::Value) -> Result<String, String> {
    v.as_str()
        .map(str::to_owned)
        .ok_or_else(|| format!("field `{name}` expects text"))
}

fn want_list(name: &str, v: &toml::Value) -> Result<Vec<String>, String> {
    let arr = v
        .as_array()
        .ok_or_else(|| format!("field `{name}` expects a list of text"))?;
    arr.iter().map(|x| want_text(name, x)).collect()
}

/// Set a settable field of `t` from a TOML value (`None` unsets an optional field).
///
/// # Errors
///
/// A message when the field is unknown, not settable here, required but unset,
/// or the value has the wrong type or spelling.
pub fn set_field(t: &mut Ticket, name: &str, value: Option<&toml::Value>) -> Result<(), String> {
    let desc = field(name).ok_or_else(|| format!("unknown field `{name}`"))?;
    if !desc.settable {
        return Err(format!("field `{name}` cannot be set directly"));
    }
    let Some(v) = value else {
        if !desc.optional {
            return Err(format!("field `{name}` is required and cannot be unset"));
        }
        unset(t, name);
        return Ok(());
    };
    let fm = &mut t.front;
    match name {
        "title" => fm.title = want_text(name, v)?,
        "type" => {
            fm.ty = want_text(name, v)?
                .parse()
                .map_err(|e: crate::model::ParseEnumError| e.to_string())?;
        }
        "flavour" => fm.flavour = Some(want_text(name, v)?),
        "priority" => {
            fm.priority = want_text(name, v)?
                .parse()
                .map_err(|e: crate::model::ParseEnumError| e.to_string())?;
        }
        "points" => {
            let n = v
                .as_integer()
                .ok_or_else(|| "field `points` expects an integer".to_owned())?;
            let n = u8::try_from(n)
                .map_err(|_| format!("points must be one of 1, 2, 3, 5, 8, 13 (got {n})"))?;
            fm.points = Some(Points::new(n).map_err(|e| e.to_string())?);
        }
        "parent" => {
            fm.parent = Some(
                want_text(name, v)?
                    .parse::<TicketId>()
                    .map_err(|e| e.to_string())?,
            );
        }
        "assignee" => fm.assignee = Some(want_text(name, v)?),
        "persona" => fm.persona = Some(want_text(name, v)?),
        "capability" => fm.capability = Some(want_text(name, v)?),
        "outcome_text" => fm.outcome_text = Some(want_text(name, v)?),
        "aliases" => fm.aliases = want_list(name, v)?,
        "labels" => fm.labels = want_list(name, v)?,
        "scope" => fm.scope = want_list(name, v)?,
        "body" => t.body = crate::model::normalize_body(&want_text(name, v)?),
        other => return Err(format!("field `{other}` cannot be set directly")),
    }
    Ok(())
}

fn unset(t: &mut Ticket, name: &str) {
    let fm = &mut t.front;
    match name {
        "flavour" => fm.flavour = None,
        "points" => fm.points = None,
        "parent" => fm.parent = None,
        "assignee" => fm.assignee = None,
        "persona" => fm.persona = None,
        "capability" => fm.capability = None,
        "outcome_text" => fm.outcome_text = None,
        "aliases" => fm.aliases.clear(),
        "labels" => fm.labels.clear(),
        "scope" => fm.scope.clear(),
        "body" => t.body.clear(),
        _ => {}
    }
}

/// Parse command-line text for field `name` into a TOML value (`None` for empty text on optional fields).
///
/// Lists split on commas; choices and points are validated here so the
/// message names the accepted spellings.
///
/// # Errors
///
/// A message when the field is unknown or not settable, or the text does not parse.
pub fn parse_text_value(name: &str, text: &str) -> Result<Option<toml::Value>, String> {
    let desc = field(name).ok_or_else(|| {
        format!(
            "unknown field `{name}`; settable fields: {}",
            settable_names().join(", ")
        )
    })?;
    if !desc.settable {
        return Err(format!(
            "field `{name}` cannot be set with update; settable fields: {}",
            settable_names().join(", ")
        ));
    }
    if text.is_empty() && desc.optional {
        return Ok(None);
    }
    let v = match desc.kind {
        FieldKind::Text | FieldKind::TicketRef => toml::Value::String(text.to_owned()),
        FieldKind::Choice(names) => {
            if !names.contains(&text) {
                return Err(format!(
                    "`{text}` is not valid for `{name}`; expected one of: {}",
                    names.join(", ")
                ));
            }
            toml::Value::String(text.to_owned())
        }
        FieldKind::Points => toml::Value::Integer(i64::from(
            text.parse::<Points>().map_err(|e| e.to_string())?.get(),
        )),
        FieldKind::List => strings(
            &text
                .split(',')
                .map(str::trim)
                .filter(|s| !s.is_empty())
                .map(str::to_owned)
                .collect::<Vec<_>>(),
        ),
        FieldKind::Instant | FieldKind::Objects => {
            return Err(format!("field `{name}` cannot be set with update"));
        }
    };
    Ok(Some(v))
}

//! `edit FILE --patch PATCH.json`: id-addressed RFC 6902 edits to a design file.
//!
//! The patch is applied to an in-memory copy, the result is re-validated by the file kind's own
//! schema parser, and only then written (atomically). The report carries a unified diff and the
//! findings of a fresh `crunk check` restricted to the objects the patch touched. The file is
//! edited in place as a `toml_edit` document: only the keys and tables the patch changed are
//! rewritten, so comments, spacing, key order and line endings elsewhere stay byte-identical.

// frob:ticket 01M4CXRA570ABD65ZDFAFVVZ8Y
// frob:ticket 01M5H8MMRPN3RFSMP5KCEXPWC7

use std::path::Path;

use gob_cli::clap::ArgMatches;
use gob_cli::{CliError, Command, Context, Outcome, Payload, Refusal, RefusalClass};
use indexmap::IndexMap;
use serde::Serialize;

use crate::PRODUCT;
use crate::dtcg::relative;
use crate::patch::{self, Node};
use crate::rewrite::{Change, commit_atomic};

/// Apply an id-addressed JSON Patch to a screen, component or content file.
#[derive(Debug, Clone, Default, gob_cli::Command)]
#[command(
    verb = "edit",
    product = "crunk",
    idempotent = false,
    dry_run,
    exits(ok, refused, usage, internal)
)]
pub struct Edit {
    file: String,
    patch: String,
}

/// `Edit` arguments.
#[derive(Debug, Clone, clap::Args)]
#[command(about = None, long_about = None)]
struct EditArgs {
    #[arg(
        value_name = "FILE",
        help = "The *.screen.toml, *.component.toml or design/content/*.toml file to edit"
    )]
    file: String,
    #[arg(
        long,
        value_name = "PATCH.json",
        help = "A JSON array of RFC 6902 operations; array elements are addressed by id or name"
    )]
    patch: String,
}

/// One finding on a touched object.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, schemars::JsonSchema)]
pub struct EditFinding {
    /// The rule id.
    pub rule: String,
    /// `error`, `warning` or another severity name.
    pub severity: String,
    /// 1-based line in the edited file, 0 for a whole-file finding.
    pub line: usize,
    /// The finding message.
    pub message: String,
}

/// The report of `edit`.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, schemars::JsonSchema)]
pub struct EditData {
    /// The edited file, relative to the project root.
    pub file: String,
    /// `screen`, `component` or `content`.
    pub kind: String,
    /// True when nothing was written.
    pub dry_run: bool,
    /// True when the file's text changed.
    pub changed: bool,
    /// Operations in the patch.
    pub ops: usize,
    /// Unified diff of the change; empty when nothing changed.
    pub diff: String,
    /// Ids of the objects the patch touched.
    pub touched: Vec<String>,
    /// Findings whose message names a touched id.
    pub findings: Vec<EditFinding>,
    /// False when the check did not run (dry run or no write).
    pub findings_checked: bool,
    /// Why the post-write check could not run, if it could not.
    pub check_error: Option<String>,
}

/// Why an edit was refused, with a stable code.
#[derive(Debug, thiserror::Error)]
pub enum EditError {
    /// The file is outside the project or not a recognised design file.
    #[error("{0}")]
    Target(String),
    /// A file could not be read.
    #[error("cannot read {0}: {1}")]
    Read(String, String),
    /// The patch is malformed or does not apply.
    #[error("{0}")]
    Patch(#[from] patch::PatchError),
    /// The patched file no longer satisfies its schema.
    #[error("the patched file is invalid, nothing written: {0}")]
    Schema(String),
}

impl EditError {
    /// The stable refusal code.
    #[must_use]
    pub fn code(&self) -> &'static str {
        match self {
            Self::Target(_) => "E-EDIT-PATH",
            Self::Read(..) => "E-EDIT-READ",
            Self::Patch(_) => "E-EDIT-PATCH",
            Self::Schema(_) => "E-EDIT-SCHEMA",
        }
    }
}

impl From<EditError> for CliError {
    fn from(err: EditError) -> Self {
        tracing::info!(code = err.code(), error = %err, "edit refused");
        Refusal::new(err.code(), RefusalClass::GuardNeedsAction, err.to_string())
            .with_remedy("fix the file or the patch as described; the file was not modified")
            .into()
    }
}

impl Command for Edit {
    type Data = EditData;

    fn configure(cmd: gob_cli::clap::Command) -> gob_cli::clap::Command {
        gob_cli::augment::<EditArgs>(cmd)
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        let a = gob_cli::parse::<EditArgs>(m)?;
        Ok(Self {
            file: a.file,
            patch: a.patch,
        })
    }

    fn run(&self, ctx: &Context) -> Outcome<EditData> {
        let root = gob_product::workspace::locate_root(PRODUCT, &ctx.cwd);
        let path = crunk_spec::normalize_join(&ctx.cwd, &self.file);
        let patch_path = crunk_spec::normalize_join(&ctx.cwd, &self.patch);
        let plan = plan(&root, &path, &patch_path)?;
        let mut data = plan.data(&root, &path, ctx.dry_run);
        if plan.changed && !ctx.dry_run {
            let change = Change {
                path: path.clone(),
                before: Some(plan.before.clone()),
                after: plan.after.clone(),
                kind: "edit",
                replacements: plan.ops,
            };
            commit_atomic(&[change]).map_err(|e| {
                Refusal::new(
                    "E-EDIT-WRITE",
                    RefusalClass::GuardNeedsAction,
                    e.to_string(),
                )
                .with_remedy("fix the file permissions; the file was rolled back")
            })?;
            tracing::info!(file = %data.file, ops = plan.ops, "edit: written");
            data.findings_checked = true;
            match touched_findings(&root, &data.file, &plan.after, &plan.touched) {
                Ok(f) => data.findings = f,
                Err(e) => {
                    tracing::warn!(error = %e, "edit: check failed after write");
                    data.check_error = Some(e);
                }
            }
        } else {
            tracing::info!(changed = plan.changed, "edit: nothing written");
        }
        let lines = data.lines();
        Ok(Payload::new(data).with_rendered(lines))
    }
}

impl EditData {
    /// Human lines: a headline, the diff, then the findings.
    #[must_use]
    pub fn lines(&self) -> Vec<String> {
        let verb = match (self.changed, self.dry_run) {
            (false, _) => "unchanged",
            (true, true) => "would edit",
            (true, false) => "edited",
        };
        let mut lines = vec![format!(
            "{verb} {} ({} op(s); touched: {})",
            self.file,
            self.ops,
            self.touched.join(", ")
        )];
        lines.extend(self.diff.lines().map(str::to_owned));
        for f in &self.findings {
            lines.push(format!(
                "{} {} line {}: {}",
                f.severity, f.rule, f.line, f.message
            ));
        }
        if let Some(e) = &self.check_error {
            lines.push(format!("check did not run: {e}"));
        }
        lines
    }
}

/// A validated, not yet written edit.
struct Plan {
    kind: &'static str,
    before: String,
    after: String,
    ops: usize,
    changed: bool,
    touched: Vec<String>,
}

impl Plan {
    /// The report for this plan before any check has run.
    fn data(&self, root: &Path, path: &Path, dry_run: bool) -> EditData {
        let file = relative(root, path);
        let diff = if self.changed {
            similar::TextDiff::from_lines(&self.before, &self.after)
                .unified_diff()
                .context_radius(3)
                .header(&side("a", &file), &side("b", &file))
                .to_string()
        } else {
            String::new()
        };
        EditData {
            file,
            kind: self.kind.to_owned(),
            dry_run,
            changed: self.changed,
            ops: self.ops,
            diff,
            touched: self.touched.clone(),
            findings: Vec::new(),
            findings_checked: false,
            check_error: None,
        }
    }
}

/// A diff header name: `file` under the `a` or `b` side.
fn side(side: &str, file: &str) -> String {
    Path::new(side).join(file).to_string_lossy().into_owned()
}

/// Which design file kind `path` is, from its location and name.
fn kind_of(root: &Path, path: &Path) -> Result<&'static str, EditError> {
    let Ok(rel) = path.strip_prefix(root) else {
        return Err(EditError::Target(format!(
            "{} is outside the project root",
            path.to_string_lossy()
        )));
    };
    let name = rel
        .file_name()
        .map(|n| n.to_string_lossy())
        .unwrap_or_default();
    let in_content = rel.starts_with(Path::new("design").join("content"));
    if name.ends_with(".screen.toml") {
        Ok("screen")
    } else if name.ends_with(".component.toml") {
        Ok("component")
    } else if in_content && name.ends_with(".toml") {
        Ok("content")
    } else {
        Err(EditError::Target(format!(
            "{} is not a screen, component or content design file (*.screen.toml, *.component.toml, or a .toml under design content)",
            rel.to_string_lossy()
        )))
    }
}

/// Check `text` against the schema of `kind`.
fn validate(kind: &str, text: &str) -> Result<(), String> {
    match kind {
        "screen" => crunk_spec::parse_screen_file(text)
            .map(drop)
            .map_err(|e| e.to_string()),
        "component" => crunk_spec::parse_component_file(text)
            .map(drop)
            .map_err(|e| e.to_string()),
        _ => crunk_spec::parse_content_file(text)
            .map(drop)
            .map_err(|e| e.to_string()),
    }
}

/// The text of `before` with `patched` applied by editing only what differs; comments and layout
/// of untouched keys survive. A file that does not parse as a TOML document is an error.
// frob:ticket 01M5H8MMRPN3RFSMP5KCEXPWC7
fn surgery(before: &str, patched: &Node) -> Result<String, String> {
    let Node::Map(map) = patched else {
        return Err("the patched document is not a table".to_owned());
    };
    let mut doc: toml_edit::DocumentMut = before.parse().map_err(|e| format!("{e}"))?;
    sync_table(doc.as_table_mut(), map, false)?;
    let text = doc.to_string();
    Ok(match_line_endings(before, &text))
}

/// `text` with CRLF line endings when `before` was all CRLF: new lines are written with `\n`, and a
/// file that was all CRLF stays all CRLF.
pub(crate) fn match_line_endings(before: &str, text: &str) -> String {
    let crlf =
        before.contains("\r\n") && before.matches('\n').count() == before.matches("\r\n").count();
    if crlf {
        text.replace("\r\n", "\n").replace('\n', "\r\n")
    } else {
        text.to_owned()
    }
}

/// A parsed item as a [`Node`]; `None` for a datetime, which the tree cannot hold.
fn item_node(item: &toml_edit::Item) -> Option<Node> {
    use toml_edit::Item;
    match item {
        Item::Value(v) => value_node(v),
        Item::Table(t) => table_node(t),
        Item::ArrayOfTables(a) => a
            .iter()
            .map(|t| table_node(t))
            .collect::<Option<Vec<_>>>()
            .map(Node::Arr),
        Item::None => None,
    }
}

/// A parsed value as a [`Node`].
fn value_node(v: &toml_edit::Value) -> Option<Node> {
    use toml_edit::Value;
    match v {
        Value::String(s) => Some(Node::Str(s.value().clone())),
        Value::Integer(i) => Some(Node::Int(*i.value())),
        Value::Float(f) => Some(Node::Float(*f.value())),
        Value::Boolean(b) => Some(Node::Bool(*b.value())),
        Value::Datetime(_) => None,
        Value::Array(a) => a
            .iter()
            .map(value_node)
            .collect::<Option<Vec<_>>>()
            .map(Node::Arr),
        Value::InlineTable(t) => table_node(t),
    }
}

/// A table-like as a [`Node::Map`].
fn table_node(t: &dyn toml_edit::TableLike) -> Option<Node> {
    t.iter()
        .map(|(k, v)| item_node(v).map(|n| (k.to_owned(), n)))
        .collect::<Option<IndexMap<_, _>>>()
        .map(Node::Map)
}

/// A fresh item for `node`; inside an inline table it is a value, elsewhere tables stay tables.
fn build(node: &Node, inline: bool) -> Result<toml_edit::Item, String> {
    let mut wrap = IndexMap::new();
    wrap.insert("v", node);
    let mut doc = toml_edit::ser::to_document(&wrap).map_err(|e| e.to_string())?;
    tabulate(doc.as_table_mut());
    let item = doc.as_table_mut().remove("v").unwrap_or_default();
    Ok(if inline {
        item.into_value().map_or_else(|i| i, toml_edit::Item::Value)
    } else {
        item
    })
}

/// Make `table` hold exactly `new`, touching only entries that differ.
fn sync_table(
    table: &mut dyn toml_edit::TableLike,
    new: &IndexMap<String, Node>,
    inline: bool,
) -> Result<(), String> {
    let stale: Vec<String> = table
        .iter()
        .map(|(k, _)| k.to_owned())
        .filter(|k| !new.contains_key(k))
        .collect();
    for k in stale {
        tracing::debug!(key = %k, "edit: key removed");
        table.remove(&k);
    }
    for (k, v) in new {
        if let Some(item) = table.get_mut(k) {
            sync_item(item, v)?;
        } else {
            tracing::debug!(key = %k, "edit: key added");
            table.insert(k, build(v, inline)?);
        }
    }
    Ok(())
}

/// Bring one existing item in line with `v`, recursing where the shapes still match.
fn sync_item(item: &mut toml_edit::Item, v: &Node) -> Result<(), String> {
    use toml_edit::{Item, Value};
    if item_node(item).as_ref() == Some(v) {
        return Ok(());
    }
    match (&mut *item, v) {
        (Item::Table(t), Node::Map(m)) => return sync_table(t, m, false),
        (Item::Value(Value::InlineTable(t)), Node::Map(m)) => return sync_table(t, m, true),
        (Item::ArrayOfTables(a), Node::Arr(els))
            if !els.is_empty() && els.iter().all(|e| matches!(e, Node::Map(_))) =>
        {
            return sync_aot(a, els);
        }
        _ => {}
    }
    tracing::debug!("edit: value replaced");
    let decor = item.as_value().map(|old| old.decor().clone());
    let mut fresh = build(v, false)?;
    if let (Some(decor), Item::Value(value)) = (decor, &mut fresh) {
        *value.decor_mut() = decor;
    }
    *item = fresh;
    Ok(())
}

/// The `id` (else `name`) string of a table node.
fn id_of(node: &Node) -> Option<&str> {
    let Node::Map(m) = node else { return None };
    match m.get("id").or_else(|| m.get("name")) {
        Some(Node::Str(s)) => Some(s),
        _ => None,
    }
}

/// Re-sync an array of tables: unchanged elements are kept verbatim, same-id elements are edited
/// in place, the rest are new; elements absent from `els` are dropped.
fn sync_aot(a: &mut toml_edit::ArrayOfTables, els: &[Node]) -> Result<(), String> {
    let mut old: Vec<Option<(toml_edit::Table, Option<Node>)>> = Vec::new();
    while !a.is_empty() {
        let t = a.remove(0);
        let n = table_node(&t);
        old.push(Some((t, n)));
    }
    let mut slots: Vec<Option<toml_edit::Table>> = els.iter().map(|_| None).collect();
    let mut pending: Vec<usize> = Vec::new();
    for (i, e) in els.iter().enumerate() {
        let hit = old
            .iter()
            .position(|o| o.as_ref().is_some_and(|(_, n)| n.as_ref() == Some(e)));
        match hit.and_then(|h| old[h].take()) {
            Some((t, _)) => slots[i] = Some(t),
            None => pending.push(i),
        }
    }
    for i in pending {
        let e = &els[i];
        let hit = id_of(e).and_then(|id| {
            old.iter().position(|o| {
                o.as_ref()
                    .is_some_and(|(_, n)| n.as_ref().and_then(id_of) == Some(id))
            })
        });
        slots[i] = Some(match (hit.and_then(|h| old[h].take()), e) {
            (Some((mut t, _)), Node::Map(m)) => {
                sync_table(&mut t, m, false)?;
                t
            }
            _ => build(e, false)?.into_table().unwrap_or_default(),
        });
    }
    for t in slots.into_iter().flatten() {
        a.push(t);
    }
    Ok(())
}

/// Turn inline tables and arrays of inline tables into standard tables, recursively.
fn tabulate(table: &mut toml_edit::Table) {
    use toml_edit::{Item, Value};
    for (_, item) in table.iter_mut() {
        if matches!(item, Item::Value(Value::InlineTable(_))) {
            let taken = std::mem::take(item);
            *item = Item::Table(taken.into_table().unwrap_or_default());
        } else if matches!(item, Item::Value(Value::Array(a)) if !a.is_empty() && a.iter().all(Value::is_inline_table))
        {
            let taken = std::mem::take(item);
            *item = Item::ArrayOfTables(taken.into_array_of_tables().unwrap_or_default());
        }
        match item {
            Item::Table(t) => tabulate(t),
            Item::ArrayOfTables(a) => a.iter_mut().for_each(tabulate),
            _ => {}
        }
    }
}

/// Read, patch and validate; nothing is written.
fn plan(root: &Path, path: &Path, patch_path: &Path) -> Result<Plan, EditError> {
    let kind = kind_of(root, path)?;
    let read = |p: &Path| {
        std::fs::read_to_string(p)
            .map_err(|e| EditError::Read(p.to_string_lossy().into_owned(), e.to_string()))
    };
    let before = read(path)?;
    let ops = patch::parse_ops(&read(patch_path)?)?;
    let doc: Node = toml_edit::de::from_str(&before)
        .map_err(|e| EditError::Schema(format!("the file is not valid TOML: {e}")))?;
    let (patched, touched) = patch::apply(&doc, &ops)?;
    let after = if patched == doc {
        before.clone()
    } else {
        surgery(&before, &patched).map_err(EditError::Schema)?
    };
    validate(kind, &after).map_err(EditError::Schema)?;
    tracing::debug!(
        kind,
        ops = ops.len(),
        touched = touched.len(),
        "edit planned"
    );
    Ok(Plan {
        kind,
        changed: after != before,
        before,
        after,
        ops: ops.len(),
        touched: touched.into_iter().collect(),
    })
}

/// True when `id` occurs in `msg` not glued to identifier characters.
fn names(msg: &str, id: &str) -> bool {
    let word = |c: char| c.is_alphanumeric() || c == '_' || c == '-';
    msg.match_indices(id).any(|(i, _)| {
        !msg[..i].chars().next_back().is_some_and(word)
            && !msg[i + id.len()..].chars().next().is_some_and(word)
    })
}

/// Run the check and keep this file's findings that name a touched id.
fn touched_findings(
    root: &Path,
    rel: &str,
    text: &str,
    touched: &[String],
) -> Result<Vec<EditFinding>, String> {
    let run =
        crunk_check::run(root, &crunk_check::CheckOptions::default()).map_err(|e| e.to_string())?;
    let mut rows: Vec<EditFinding> = run
        .report
        .findings
        .iter()
        .filter(|f| f.severity != gob_rules::Severity::Unresolved)
        .filter_map(|f| {
            let span = f.span?;
            if run.report.files.path(span.file)? != rel {
                return None;
            }
            if !touched.iter().any(|id| names(&f.message, id)) {
                return None;
            }
            let start = usize::try_from(u32::from(span.range.start())).unwrap_or(0);
            let line = if start == 0 {
                0
            } else {
                text.get(..start).map_or(1, |s| s.matches('\n').count() + 1)
            };
            Some(EditFinding {
                rule: f.rule.as_str().to_owned(),
                severity: format!("{:?}", f.severity).to_lowercase(),
                line,
                message: f.message.clone(),
            })
        })
        .collect();
    rows.sort_by(|a, b| (a.line, &a.rule).cmp(&(b.line, &b.rule)));
    tracing::debug!(rows = rows.len(), "edit findings collected");
    Ok(rows)
}

//! The model-side facts of a run: entities, exceptions and file status, read from the `.grmb` files.
//!
//! Everything here is derived from `grimble-model` and is deterministic: rows are sorted by
//! anchor (entities) or by file and offset (exceptions), so two runs print equal documents.

use std::collections::BTreeMap;

use gob_ir::DIGEST_SCHEME;
use gob_rules::{BoundException, Exception, ExceptionKind, RuleId};
use grimble_model::ast::{ClauseKind, ExcKind, FileStatus, Spanned, Value};
use grimble_model::model::{Index, LoadedRoot, load_roots};
use grimble_model::{ModelFiles, fold_file, parse_file};
use serde_json::{Value as Json, json};

/// A `frob:` directive written in a `.grmb` file, handed to frob unparsed (sibling-contract 3.7).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct DirectiveRow {
    /// The verb after `frob:`.
    pub verb: String,
    /// The raw argument text.
    pub args: String,
    /// 1-based line of the directive.
    pub line: u32,
    /// Byte range of the directive text.
    pub range: (usize, usize),
}

/// One declared model entity.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct EntityRow {
    /// `kind/full-name`, the target of a `design:` link.
    pub anchor: String,
    /// Entity kind keyword.
    pub kind: String,
    /// Declared name.
    pub name: String,
    /// The model (module) name, empty when the root declares none.
    pub module: String,
    /// Repo-relative file.
    pub file: String,
    /// 1-based line of the entity.
    pub line: u32,
    /// Byte range of the whole item.
    pub range: (usize, usize),
    /// Former names (`renamed_from`).
    pub renamed_from: Vec<String>,
    /// `frob:` directives bound to the entity or one of its clauses.
    pub directives: Vec<DirectiveRow>,
}

/// One parsed exception clause with the region it covers.
#[derive(Debug, Clone)]
pub struct ExceptionRow {
    /// Stable hex id from kind, rule and site.
    pub id: String,
    /// `accept`, `defer` or `hotfix`.
    pub kind: &'static str,
    /// The excepted rule id as written.
    pub rule: String,
    /// The target: an entity anchor or the `on` path as written.
    pub on: String,
    /// File the exception is written in.
    pub file: String,
    /// 1-based line.
    pub line: u32,
    /// The `because=` text, verbatim.
    pub because: String,
    /// The `until=` date, if written.
    pub until: Option<String>,
    /// The `ticket=` value, verbatim and opaque; never set on an `accept`.
    pub ticket: Option<String>,
    /// The binding `gob_rules` matches findings against, when the rule id is well formed.
    pub bound: Option<BoundException>,
}

/// How one `.grmb` file was read.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct FileRow {
    /// Repo-relative path.
    pub path: String,
    /// `parsed`, `opaque` or `refused`.
    pub status: &'static str,
    /// Why, for `opaque` and `refused`.
    pub reason: Option<String>,
    /// Syntax holes in the file.
    pub holes: usize,
}

/// Everything the document and the verbs need from the model.
#[derive(Debug, Clone, Default)]
pub struct ModelView {
    /// Number of `.grmb` files supplied.
    pub files: usize,
    /// Entities sorted by anchor then file.
    pub entities: Vec<EntityRow>,
    /// Exceptions sorted by file then line.
    pub exceptions: Vec<ExceptionRow>,
    /// One row per file, sorted by path.
    pub file_rows: Vec<FileRow>,
}

/// 1-based line of byte `offset` in `text`.
fn line_of(text: &str, offset: usize) -> u32 {
    let n = text.bytes().take(offset).filter(|b| *b == b'\n').count();
    u32::try_from(n + 1).unwrap_or(u32::MAX)
}

fn str_of(v: &Spanned<Value>) -> Option<String> {
    match &v.value {
        Value::Str(s) | Value::Date(s) => Some(s.clone()),
        _ => None,
    }
}

fn exception_id(kind: &str, rule: &str, file: &str, start: usize) -> String {
    let mut h = blake3::Hasher::new();
    for part in [kind, rule, file] {
        h.update(part.as_bytes());
        h.update(b"\0");
    }
    h.update(&start.to_le_bytes());
    h.finalize().to_hex().as_str()[..16].to_owned()
}

fn bound_kind(kind: ExcKind) -> ExceptionKind {
    match kind {
        ExcKind::Accept => ExceptionKind::Accept,
        ExcKind::Defer => ExceptionKind::Defer,
        ExcKind::Hotfix => ExceptionKind::Hotfix,
    }
}

/// Where an exception is written and what it covers.
struct Site<'a> {
    file: &'a str,
    text: &'a str,
    start: usize,
    on: String,
    cover_file: &'a str,
    cover: (usize, usize),
}

fn exception_row(x: &grimble_model::ast::Exception, site: &Site<'_>) -> ExceptionRow {
    let attr = |k: &str| {
        x.attrs
            .iter()
            .find(|a| a.key.text == k)
            .and_then(|a| str_of(&a.value))
    };
    let kind = x.kind.keyword();
    let because = attr("because").unwrap_or_default();
    let ticket = if x.kind == ExcKind::Accept {
        None
    } else {
        attr("ticket")
    };
    let until = attr("until");
    let bound = x
        .rule
        .text
        .parse::<RuleId>()
        .ok()
        .map(|rule| BoundException {
            exception: Exception {
                kind: bound_kind(x.kind),
                rule,
                reason: because.clone(),
                ticket: ticket.clone(),
                until: until.clone(),
            },
            path: site.cover_file.to_owned(),
            range: Some(site.cover.0..site.cover.1),
        });
    ExceptionRow {
        id: exception_id(kind, &x.rule.text, site.file, site.start),
        kind,
        rule: x.rule.text.clone(),
        on: site.on.clone(),
        file: site.file.to_owned(),
        line: line_of(site.text, site.start),
        because,
        until,
        ticket,
        bound,
    }
}

fn root_module(root: &LoadedRoot) -> String {
    root.files
        .first()
        .and_then(|f| f.parsed.module.as_ref())
        .map(|m| m.name.text.clone())
        .unwrap_or_default()
}

/// The first two `/` segments of an anchor: `flow/f/producer[0]` gives `flow/f`.
fn entity_part(anchor: &str) -> Option<String> {
    let mut it = anchor.splitn(3, '/');
    let (kind, name) = (it.next()?, it.next()?);
    (kind != "file").then(|| format!("{kind}/{name}"))
}

fn directives_of(root: &LoadedRoot) -> BTreeMap<(String, String), Vec<DirectiveRow>> {
    let mut out: BTreeMap<(String, String), Vec<DirectiveRow>> = BTreeMap::new();
    for f in &root.files {
        let Ok(folded) = fold_file(&f.parsed, &f.mount) else {
            continue;
        };
        for d in folded
            .directives
            .iter()
            .filter(|d| d.hit.namespace == "frob")
        {
            let Some(entity) = entity_part(&d.anchor) else {
                continue;
            };
            out.entry((f.parsed.path.clone(), entity))
                .or_default()
                .push(DirectiveRow {
                    verb: d.hit.verb.clone(),
                    args: d.hit.args.clone(),
                    line: line_of(&f.parsed.text, d.hit.span.start),
                    range: (d.hit.span.start, d.hit.span.end),
                });
        }
    }
    out
}

impl ModelView {
    /// Read entities, exceptions and file status out of `files`.
    pub fn build(files: &ModelFiles) -> Self {
        let mut entities: BTreeMap<(String, String, usize), EntityRow> = BTreeMap::new();
        let mut exceptions: BTreeMap<(String, usize), ExceptionRow> = BTreeMap::new();
        for root in &load_roots(files) {
            let module = root_module(root);
            let directives = directives_of(root);
            let idx = Index::build(root);
            for rec in &idx.entities {
                let parsed = &root.files[rec.file].parsed;
                let e = rec.entity;
                let anchor = format!("{}/{}", e.kind.keyword(), rec.full);
                let renamed_from = e
                    .clauses
                    .iter()
                    .filter_map(|c| match &c.kind {
                        ClauseKind::RenamedFrom(i) => Some(i.text.clone()),
                        _ => None,
                    })
                    .collect();
                let row = EntityRow {
                    directives: directives
                        .get(&(parsed.path.clone(), anchor.clone()))
                        .cloned()
                        .unwrap_or_default(),
                    anchor: anchor.clone(),
                    kind: e.kind.keyword().to_owned(),
                    name: e.name.text.clone(),
                    module: module.clone(),
                    file: parsed.path.clone(),
                    line: line_of(&parsed.text, e.span.start),
                    range: (e.span.start, e.span.end),
                    renamed_from,
                };
                entities.insert((anchor, parsed.path.clone(), e.span.start), row);
                for c in &e.clauses {
                    if let ClauseKind::Exception(x) = &c.kind {
                        let site = Site {
                            file: &parsed.path,
                            text: &parsed.text,
                            start: c.span.start,
                            on: format!("{}/{}", e.kind.keyword(), rec.full),
                            cover_file: &parsed.path,
                            cover: (e.span.start, e.span.end),
                        };
                        exceptions
                            .insert((parsed.path.clone(), c.span.start), exception_row(x, &site));
                    }
                }
            }
            for top in &idx.top_exceptions {
                let parsed = &root.files[top.file].parsed;
                let x = &top.exc.exception;
                let target =
                    x.on.as_ref()
                        .and_then(|on| idx.resolve(&top.ctx, on))
                        .map(|r| &idx.entities[r.rec]);
                let (cover_file, cover) = match target {
                    Some(t) => (
                        root.files[t.file].parsed.path.as_str(),
                        (t.entity.span.start, t.entity.span.end),
                    ),
                    None => (parsed.path.as_str(), (top.exc.span.start, top.exc.span.end)),
                };
                let site = Site {
                    file: &parsed.path,
                    text: &parsed.text,
                    start: top.exc.span.start,
                    on: x
                        .on
                        .as_ref()
                        .map(grimble_model::ast::RefPath::written)
                        .unwrap_or_default(),
                    cover_file,
                    cover,
                };
                exceptions.insert(
                    (parsed.path.clone(), top.exc.span.start),
                    exception_row(x, &site),
                );
            }
        }
        let mut file_rows: Vec<FileRow> = files
            .files
            .iter()
            .map(|(path, bytes)| file_row(path, bytes))
            .collect();
        file_rows.sort_by(|a, b| a.path.cmp(&b.path));
        let view = Self {
            files: files.files.len(),
            entities: entities.into_values().collect(),
            exceptions: exceptions.into_values().collect(),
            file_rows,
        };
        tracing::info!(
            files = view.files,
            entities = view.entities.len(),
            exceptions = view.exceptions.len(),
            "model view built"
        );
        view
    }

    /// The bound exceptions, in the order of [`Self::exceptions`] (rows with a malformed rule id are skipped).
    pub fn bound(&self) -> Vec<(usize, &BoundException)> {
        self.exceptions
            .iter()
            .enumerate()
            .filter_map(|(i, e)| e.bound.as_ref().map(|b| (i, b)))
            .collect()
    }

    /// The `entities` array of the sibling document.
    pub fn entities_json(&self) -> Vec<Json> {
        self.entities
            .iter()
            .map(|e| {
                json!({
                    "anchor": e.anchor,
                    "kind": e.kind,
                    "name": e.name,
                    "module": e.module,
                    "file": e.file,
                    "line": e.line,
                    "range": {"start": e.range.0, "end": e.range.1},
                    "digest_scheme": DIGEST_SCHEME,
                    "body_digest": Json::Null,
                    "doc_digest": Json::Null,
                    "renamed_from": e.renamed_from,
                    "directives": e.directives.iter().map(|d| json!({
                        "namespace": "frob",
                        "verb": d.verb,
                        "args": d.args,
                        "line": d.line,
                        "range": {"start": d.range.0, "end": d.range.1},
                    })).collect::<Vec<_>>(),
                })
            })
            .collect()
    }
}

/// How the model file at `path` reads: its status and hole count.
pub fn file_row(path: &str, bytes: &[u8]) -> FileRow {
    let parsed = parse_file(path, bytes);
    let (status, reason) = match &parsed.status {
        FileStatus::Parsed => ("parsed", None),
        FileStatus::Opaque(r) => ("opaque", Some((*r).to_owned())),
        FileStatus::Refused(r) => ("refused", Some((*r).to_owned())),
    };
    FileRow {
        path: path.to_owned(),
        status,
        reason,
        holes: parsed.holes,
    }
}

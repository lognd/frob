//! The relation B: rank 1 (directives), rank 2 (selector clauses), rank 3 (inference stub) and
//! rank 4 (the hidden remainder), before the owner merge (binding.md 2.1 to 2.4).

// frob:ticket 01M3Z71450ZE377RBK3EG1XSWC

use std::cell::RefCell;
use std::collections::{BTreeMap, HashMap};
use std::rc::Rc;

use gob_ir::{UnitIndex, owner_of_unit_in, select};
use gob_walk::{EntityName, Selector, select_files};
use grimble_model::ast::EntityKind;

use crate::anchors::{ROW_KIND, row_anchors};
use crate::code::{Code, CodeFile, Unit, unit_kind};
use crate::directives::CodeDirective;
use crate::model::{Clause, Entity, Model};
use crate::types::{BindFinding, Reason, Role, Row, Source, Status};
use gob_rules::Severity;

/// A unit a symref or selector resolved to.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct UnitHit {
    /// The symref text.
    pub symref: String,
    /// The unit kind.
    pub kind: String,
    /// Must or May.
    pub status: Status,
}

/// The answer of resolving a symref operand (docs/design/shared/code-model.md section 2, query Q22).
#[derive(Clone, Debug, PartialEq, Eq)]
pub enum Resolution {
    /// Exactly one identity.
    One(UnitHit),
    /// Several candidates; none is chosen.
    Ambiguous(Vec<UnitHit>),
    /// Nothing; `hidden` says why the answer is Unknown rather than empty.
    NotFound {
        /// True when the target file is in the walk.
        file_in_walk: bool,
        /// Set when the target file hides units the operand could name.
        hidden: Option<Reason>,
    },
}

fn status_of(s: gob_ir::Status) -> Status {
    match s {
        gob_ir::Status::Must => Status::Must,
        gob_ir::Status::May | gob_ir::Status::Unknown => Status::May,
    }
}

/// Why `f` hides units a selector or operand could name, if it does.
pub fn hidden_reason(f: &CodeFile) -> Option<Reason> {
    if f.unreadable || (f.has_unseen() && !f.is_opaque()) {
        Some(Reason::UnseenRemainder)
    } else if f.is_opaque() || f.fidelity < gob_symbols::Fidelity::F2 {
        Some(Reason::Fidelity)
    } else {
        None
    }
}

/// The file path of a symref text (`path::qualname` or `path#slug`).
fn path_of_symref(text: &str) -> &str {
    let path = text.split('#').next().unwrap_or(text);
    path.split("::").next().unwrap_or(path)
}

/// The units of one file, with a first-part-by-symref index, computed once per build.
struct FileUnits {
    units: Vec<Unit>,
    by_symref: HashMap<String, Vec<usize>>,
}

impl FileUnits {
    /// Walk `file`'s units once and index them by symref text.
    fn new(file: &CodeFile) -> Self {
        let units = file.units();
        let mut by_symref: HashMap<String, Vec<usize>> = HashMap::new();
        for (i, u) in units.iter().enumerate() {
            by_symref.entry(u.symref.clone()).or_default().push(i);
        }
        Self { units, by_symref }
    }

    /// The first unit spelled `symref`, in document order.
    fn first(&self, symref: &str) -> Option<&Unit> {
        self.by_symref
            .get(symref)
            .and_then(|v| v.first())
            .map(|&i| &self.units[i])
    }
}

/// Per-file [`FileUnits`], so N directives into one file cost one unit walk instead of N.
#[derive(Default)]
struct UnitCache(RefCell<HashMap<String, Rc<FileUnits>>>);

impl UnitCache {
    /// The cached units of `file`, walking them on first use.
    fn get(&self, file: &CodeFile) -> Rc<FileUnits> {
        if let Some(hit) = self.0.borrow().get(&file.path) {
            return Rc::clone(hit);
        }
        let fresh = Rc::new(FileUnits::new(file));
        self.0
            .borrow_mut()
            .insert(file.path.clone(), Rc::clone(&fresh));
        fresh
    }
}

/// The table-row ids of a markdown `file` that `text` (`path#anchor` or `path::anchor`) names.
fn row_hits(file: &CodeFile, units: &[crate::code::Unit], text: &str) -> Vec<UnitHit> {
    let Some(anchor) = row_anchor(file, text) else {
        return Vec::new();
    };
    row_hit_at(file, units, anchor)
}

/// The anchor part of `text` when `file` is markdown and the anchor is non-empty.
fn row_anchor<'t>(file: &CodeFile, text: &'t str) -> Option<&'t str> {
    let at = text.find(['#', ':'])?;
    let anchor = text[at..].trim_start_matches(['#', ':']);
    (file.language == "markdown" && !anchor.is_empty()).then_some(anchor)
}

/// The table-row hit for `anchor` in the markdown `file`, or none when no row carries it.
fn row_hit_at(file: &CodeFile, units: &[crate::code::Unit], anchor: &str) -> Vec<UnitHit> {
    let prefix = format!("{}::", file.path);
    let headings: Vec<String> = units
        .iter()
        .filter_map(|u| u.symref.strip_prefix(&prefix).map(str::to_owned))
        .collect();
    let Some(src) = file.source() else {
        return Vec::new();
    };
    if !row_anchors(&src, &headings).iter().any(|a| a == anchor) {
        return Vec::new();
    }
    tracing::debug!(path = %file.path, anchor, "ref resolved to a table-row id");
    vec![UnitHit {
        symref: format!("{prefix}{anchor}"),
        kind: ROW_KIND.to_owned(),
        status: Status::Must,
    }]
}

/// Resolve `text` (`path::qualname` or `path#slug`): exact spelling, then the unique-suffix rule.
pub fn resolve_symref(code: &Code, text: &str) -> Resolution {
    resolve_cached(code, &UnitCache::default(), text)
}

/// [`resolve_symref`] over a shared [`UnitCache`], so repeated resolutions into a file stay linear.
fn resolve_cached(code: &Code, cache: &UnitCache, text: &str) -> Resolution {
    let path = path_of_symref(text);
    let Some(file) = code.file(path) else {
        return Resolution::NotFound {
            file_in_walk: false,
            hidden: None,
        };
    };
    let fu = cache.get(file);
    let units = &fu.units;
    // A markdown anchor `path#slug` is the unit `path::slug` of the markdown adapter.
    let spelled = text.replacen('#', "::", 1);
    let mut at: Vec<usize> = [text, spelled.as_str()]
        .iter()
        .filter_map(|k| fu.by_symref.get(*k))
        .flatten()
        .copied()
        .collect();
    at.sort_unstable();
    at.dedup();
    let exact: Vec<UnitHit> = at
        .into_iter()
        .map(|i| &units[i])
        .map(|u| UnitHit {
            symref: u.symref.clone(),
            kind: u.kind.clone(),
            status: Status::Must,
        })
        .collect();
    let mut hits = exact;
    hits.dedup_by(|a, b| a.symref == b.symref);
    if hits.is_empty() {
        hits = row_hits(file, units, text);
    }
    if hits.is_empty()
        && let (Some(folded), Ok(sel)) = (file.folded(), Selector::parse(&format!("{text:?}")))
    {
        let m = select(&sel, &folded.term, &folded.scopes, &code.walk);
        let index = UnitIndex::new(&folded.term);
        hits = m
            .matches
            .into_iter()
            .map(|u| {
                let node = index
                    .parts(&u.symref)
                    .first()
                    .map(|&n| unit_kind(&folded.term, n))
                    .unwrap_or_default();
                UnitHit {
                    symref: u.symref.to_string(),
                    kind: node,
                    status: status_of(u.status),
                }
            })
            .collect();
    }
    match hits.len() {
        0 => Resolution::NotFound {
            file_in_walk: true,
            hidden: hidden_reason(file),
        },
        1 => Resolution::One(hits.remove(0)),
        _ => Resolution::Ambiguous(hits),
    }
}

/// What one selector or ref clause matched, for the clause rules (SYS003 to SYS011).
#[derive(Clone, Debug)]
pub struct ClauseResult {
    /// Anchor of the entity.
    pub entity: String,
    /// The clause.
    pub clause: Clause,
    /// Units the clause matched with their status.
    pub matches: Vec<(UnitHit, String)>,
    /// Hidden placeholders and why.
    pub hidden: Vec<Reason>,
    /// Files whose path the selector may match (zero means MDL005 territory).
    pub files_matched: usize,
}

impl ClauseResult {
    /// Matches at Must.
    pub fn lo(&self) -> usize {
        self.matches
            .iter()
            .filter(|(h, _)| h.status == Status::Must)
            .count()
    }

    /// Matches at May only.
    pub fn may(&self) -> usize {
        self.matches
            .iter()
            .filter(|(h, _)| h.status != Status::Must)
            .count()
    }

    /// True when `hi` is empty: no Must, no May and no hidden placeholder.
    pub fn hi_empty(&self) -> bool {
        self.matches.is_empty() && self.hidden.is_empty()
    }
}

/// A rank 1 owner row of an identity.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct DirOwn {
    /// The node anchor.
    pub entity: String,
    /// The directive site, `path@offset`.
    pub site: String,
    /// The file of the directive.
    pub file: String,
    /// The directive range.
    pub range: (usize, usize),
}

/// A code-to-code `binds` edge (binding.md 1.4, the relation C).
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct CEdge {
    /// The directive's target unit.
    pub from: String,
    /// The resolved identity.
    pub to: String,
    /// The mechanism, `manual` by default.
    pub via: String,
    /// Must when the operand resolved uniquely, May for each of several candidates.
    pub status: Status,
}

/// The relation before ownership is merged.
#[derive(Debug, Default)]
pub struct Relation {
    /// Rows of B, rank 1 to 4.
    pub rows: Vec<Row>,
    /// One result per selector or ref clause.
    pub clauses: Vec<ClauseResult>,
    /// Rank 1 owners by identity.
    pub dir_owns: BTreeMap<String, Vec<DirOwn>>,
    /// SYS003 findings of operands (`dangling-operand`, `ambiguous-operand`).
    pub findings: Vec<BindFinding>,
    /// Operands examined (SYS003 subjects).
    pub operands: usize,
    /// The relation C.
    pub edges: Vec<CEdge>,
}

fn site(file: &str, range: (usize, usize)) -> String {
    format!("{file}@{}", range.0)
}

fn hidden_for(f: &CodeFile) -> Reason {
    hidden_reason(f).unwrap_or(Reason::UnseenRemainder)
}

fn residual(entity: &str, clause: &Clause, reason: Reason) -> Row {
    Row {
        entity: entity.to_owned(),
        role: clause.role,
        identity: None,
        unit_kind: None,
        status: Status::Unknown,
        source: Source::Residual,
        anchor: Some(clause.anchor.clone()),
        reason: Some(reason.code().to_owned()),
        specificity: None,
        overridden: false,
        realization_kind: clause.realization_kind.clone(),
    }
}

fn selector_clause(code: &Code, entity: &str, clause: &Clause, sel: &Selector, rel: &mut Relation) {
    let pm = select_files(sel, &code.walk);
    code.prefold(pm.iter().map(|m| m.path.as_str()));
    let mut result = ClauseResult {
        entity: entity.to_owned(),
        clause: clause.clone(),
        matches: Vec::new(),
        hidden: Vec::new(),
        files_matched: pm.len(),
    };
    let name = EntityName::from(entity.to_owned());
    for m in &pm {
        let Some(file) = code.file(&m.path) else {
            continue;
        };
        let Some(folded) = file.folded() else {
            result.hidden.push(Reason::UnseenRemainder);
            rel.rows
                .push(residual(entity, clause, Reason::UnseenRemainder));
            continue;
        };
        let selection = select(sel, &folded.term, &folded.scopes, &code.walk);
        let index = UnitIndex::new(&folded.term);
        for u in selection.matches {
            let spec = (clause.role == Role::Owns)
                .then(|| {
                    owner_of_unit_in(
                        &[(name.clone(), sel.clone())],
                        &u.symref,
                        &folded.term,
                        &folded.scopes,
                        &index,
                    )
                    .and_then(|o| o.candidates.iter().map(|c| c.spec).max())
                    .map(|s| s.components())
                })
                .flatten();
            let kind = index
                .parts(&u.symref)
                .first()
                .map(|&n| unit_kind(&folded.term, n))
                .unwrap_or_default();
            let status = status_of(u.status);
            rel.rows.push(Row {
                entity: entity.to_owned(),
                role: clause.role,
                identity: Some(u.symref.to_string()),
                unit_kind: Some(kind.clone()),
                status,
                source: Source::Selector,
                anchor: Some(clause.anchor.clone()),
                reason: None,
                specificity: spec,
                overridden: false,
                realization_kind: clause.realization_kind.clone(),
            });
            result.matches.push((
                UnitHit {
                    symref: u.symref.to_string(),
                    kind,
                    status,
                },
                file.path.clone(),
            ));
        }
        if clause.role == Role::Runnable && !result.matches.iter().any(|(_, p)| *p == file.path) {
            js_title_hit(sel, file, entity, clause, rel, &mut result);
        }
        for _ in selection.hidden {
            let reason = hidden_for(file);
            result.hidden.push(reason);
            rel.rows.push(residual(entity, clause, reason));
        }
    }
    rel.clauses.push(result);
}

/// The bracketed title a vitest/jest selector names: `file::[describe > title]` gives the text
/// inside the brackets.
fn bracket_title(sel: &Selector) -> Option<String> {
    let q = sel.literal()?.qual()?;
    let inner = q.strip_prefix('[')?.strip_suffix(']')?;
    Some(inner.to_owned())
}

/// Binds a `file::[a > b]` runnable selector to a vitest/jest title the symbol view does not
/// carry: scans the file's `describe`/`it`/`test` calls and emits a test unit on an exact id.
fn js_title_hit(
    sel: &Selector,
    file: &CodeFile,
    entity: &str,
    clause: &Clause,
    rel: &mut Relation,
    result: &mut ClauseResult,
) {
    let Some(title) = declared_js_title(sel, file) else {
        return;
    };
    let symref = format!("{}::[{title}]", file.path);
    tracing::debug!(%symref, anchor = %clause.anchor, "runnable bound to a test title");
    let kind = "test".to_owned();
    rel.rows.push(Row {
        entity: entity.to_owned(),
        role: clause.role,
        identity: Some(symref.clone()),
        unit_kind: Some(kind.clone()),
        status: Status::Must,
        source: Source::Selector,
        anchor: Some(clause.anchor.clone()),
        reason: None,
        specificity: None,
        overridden: false,
        realization_kind: clause.realization_kind.clone(),
    });
    result.matches.push((
        UnitHit {
            symref,
            kind,
            status: Status::Must,
        },
        file.path.clone(),
    ));
}

/// The bracketed test title of `sel` when `file` is a JS test file that declares it.
fn declared_js_title(sel: &Selector, file: &CodeFile) -> Option<String> {
    let title = bracket_title(sel)?;
    let lang = gob_languages::Language::detect(&file.path)?;
    let text = file.source()?;
    gob_languages::js_test_ids(lang, &text)
        .contains(&title)
        .then_some(title)
}

fn ref_clause(
    code: &Code,
    cache: &UnitCache,
    entity: &Entity,
    clause: &Clause,
    text: &str,
    rel: &mut Relation,
) {
    rel.operands += 1;
    let mut result = ClauseResult {
        entity: entity.anchor.clone(),
        clause: clause.clone(),
        matches: Vec::new(),
        hidden: Vec::new(),
        files_matched: 0,
    };
    let at = Some((clause.file.as_str(), (clause.span.start, clause.span.end)));
    match resolve_cached(code, cache, text) {
        Resolution::One(h) => {
            result.files_matched = 1;
            result
                .matches
                .push((h, text.split(['#', ':']).next().unwrap_or("").to_owned()));
        }
        Resolution::Ambiguous(hits) => {
            result.files_matched = 1;
            let names: Vec<&str> = hits.iter().map(|h| h.symref.as_str()).collect();
            rel.findings.push(BindFinding {
                rule: "SYS003",
                severity: Severity::Error,
                file: at.map(|(f, _)| f.to_owned()),
                range: at.map(|(_, r)| r),
                message: format!(
                    "ambiguous-operand: `{text}` in {} names several identities: {}",
                    clause.anchor,
                    names.join(", ")
                ),
                reason: None,
                anchor: clause.anchor.clone(),
            });
            for h in hits {
                result.matches.push((
                    UnitHit {
                        status: Status::May,
                        ..h
                    },
                    String::new(),
                ));
            }
        }
        Resolution::NotFound {
            file_in_walk,
            hidden,
        } => {
            result.files_matched = usize::from(file_in_walk);
            if let Some(r) = hidden {
                result.hidden.push(r);
                rel.rows.push(residual(&entity.anchor, clause, r));
            }
        }
    }
    for (h, _) in &result.matches {
        rel.rows.push(Row {
            entity: entity.anchor.clone(),
            role: clause.role,
            identity: Some(h.symref.clone()),
            unit_kind: Some(h.kind.clone()),
            status: h.status,
            source: Source::Selector,
            anchor: Some(clause.anchor.clone()),
            reason: None,
            specificity: None,
            overridden: false,
            realization_kind: clause.realization_kind.clone(),
        });
    }
    rel.clauses.push(result);
}

fn operand_entity(model: &Model, operand: &str) -> Option<Result<String, String>> {
    let rest = operand.strip_prefix("design:")?;
    Some(if model.entities.contains_key(rest) {
        Ok(rest.to_owned())
    } else {
        Err(format!("`{operand}` names no entity of the model"))
    })
}

fn directive_role(kind: EntityKind, role: Option<&str>) -> Result<Role, String> {
    let named = role.map(|r| Role::parse(r).ok_or_else(|| format!("`role={r}` is not a role")));
    match kind {
        EntityKind::Node => Ok(Role::Owns),
        EntityKind::Contract => Ok(Role::Shape),
        EntityKind::Claim => Ok(Role::Evidence),
        EntityKind::Flow => match named {
            Some(Ok(r @ (Role::Producer | Role::Consumer))) => Ok(r),
            _ => Err("a flow binding needs `role=producer` or `role=consumer`".to_owned()),
        },
        EntityKind::Vmodel => match named {
            Some(Ok(r @ (Role::Runnable | Role::Ref))) => Ok(r),
            _ => Err("a vmodel binding needs `role=runnable` or `role=ref`".to_owned()),
        },
        EntityKind::Boundary | EntityKind::Pack | EntityKind::Template | EntityKind::Policy => {
            Err("a boundary, pack or template has no code binding".to_owned())
        }
    }
}

struct Bind<'a> {
    entity: String,
    role: Role,
    identity: String,
    status: Status,
    file: &'a str,
    range: (usize, usize),
}

fn push_directive_row(code: &Code, cache: &UnitCache, b: &Bind<'_>, rel: &mut Relation) {
    let path = b
        .identity
        .split("::")
        .next()
        .unwrap_or("")
        .split('#')
        .next()
        .unwrap_or("");
    let kind = code
        .file(path)
        .and_then(|f| cache.get(f).first(&b.identity).map(|u| u.kind.clone()));
    rel.rows.push(Row {
        entity: b.entity.clone(),
        role: b.role,
        identity: Some(b.identity.clone()),
        unit_kind: kind,
        status: b.status,
        source: Source::Directive,
        anchor: Some(site(b.file, b.range)),
        reason: None,
        specificity: None,
        overridden: false,
        realization_kind: None,
    });
    if b.role == Role::Owns {
        rel.dir_owns
            .entry(b.identity.clone())
            .or_default()
            .push(DirOwn {
                entity: b.entity.clone(),
                site: site(b.file, b.range),
                file: b.file.to_owned(),
                range: b.range,
            });
    }
}

fn operand_finding(kind: &str, message: &str, file: &str, range: (usize, usize)) -> BindFinding {
    BindFinding {
        rule: "SYS003",
        severity: Severity::Error,
        file: Some(file.to_owned()),
        range: Some(range),
        message: format!("{kind}: {message}"),
        reason: None,
        anchor: site(file, range),
    }
}

fn code_directive(
    model: &Model,
    code: &Code,
    cache: &UnitCache,
    d: &CodeDirective,
    rel: &mut Relation,
) {
    rel.operands += 1;
    let range = d.range;
    if let Some(res) = operand_entity(model, &d.operand) {
        let entity = match res {
            Ok(e) => e,
            Err(msg) => {
                rel.findings
                    .push(operand_finding("dangling-operand", &msg, &d.file, range));
                return;
            }
        };
        let kind = model.entities[&entity].kind;
        match directive_role(kind, d.role.as_deref()) {
            Ok(role) => push_directive_row(
                code,
                cache,
                &Bind {
                    entity,
                    role,
                    identity: d.target.clone(),
                    status: Status::Must,
                    file: &d.file,
                    range,
                },
                rel,
            ),
            Err(msg) => rel.findings.push(operand_finding(
                "dangling-operand",
                &format!("`{}`: {msg}", d.operand),
                &d.file,
                range,
            )),
        }
        return;
    }
    let via = d.via.clone().unwrap_or_else(|| "manual".to_owned());
    match resolve_cached(code, cache, &d.operand) {
        Resolution::One(h) => rel.edges.push(CEdge {
            from: d.target.clone(),
            to: h.symref,
            via,
            status: Status::Must,
        }),
        Resolution::Ambiguous(hits) => {
            let names: Vec<&str> = hits.iter().map(|h| h.symref.as_str()).collect();
            rel.findings.push(operand_finding(
                "ambiguous-operand",
                &format!(
                    "`{}` names several identities: {}",
                    d.operand,
                    names.join(", ")
                ),
                &d.file,
                range,
            ));
            for h in hits {
                rel.edges.push(CEdge {
                    from: d.target.clone(),
                    to: h.symref,
                    via: via.clone(),
                    status: Status::May,
                });
            }
        }
        Resolution::NotFound {
            hidden: Some(_), ..
        } => {
            tracing::debug!(operand = %d.operand, "operand target hides units; unresolved, no finding");
        }
        Resolution::NotFound { hidden: None, .. } => rel.findings.push(operand_finding(
            "dangling-operand",
            &format!("`{}` resolves to nothing", d.operand),
            &d.file,
            range,
        )),
    }
}

fn explicit_role(anchor: &str, kind: EntityKind) -> Option<Role> {
    let tail = anchor
        .splitn(3, '/')
        .nth(2)
        .map(|t| t.split('[').next().unwrap_or(t));
    tail.and_then(Role::parse).or(match kind {
        EntityKind::Node => Some(Role::Owns),
        EntityKind::Contract => Some(Role::Shape),
        EntityKind::Claim => Some(Role::Evidence),
        EntityKind::Vmodel => Some(Role::Ref),
        _ => None,
    })
}

fn model_directives(model: &Model, code: &Code, cache: &UnitCache, rel: &mut Relation) {
    for x in &model.explicit {
        rel.operands += 1;
        let Some(ent) = model.entities.get(&x.entity) else {
            continue;
        };
        let range = (x.span.start, x.span.end);
        let Some(role) = explicit_role(&x.anchor, ent.kind) else {
            rel.findings.push(operand_finding(
                "dangling-operand",
                &format!("`{}` binds a flow without naming its end", x.symref),
                &x.file,
                range,
            ));
            continue;
        };
        match resolve_cached(code, cache, &x.symref) {
            Resolution::One(h) => push_directive_row(
                code,
                cache,
                &Bind {
                    entity: x.entity.clone(),
                    role,
                    identity: h.symref,
                    status: Status::Must,
                    file: &x.file,
                    range,
                },
                rel,
            ),
            Resolution::Ambiguous(hits) => {
                let names: Vec<&str> = hits.iter().map(|h| h.symref.as_str()).collect();
                rel.findings.push(operand_finding(
                    "ambiguous-operand",
                    &format!(
                        "`{}` names several identities: {}",
                        x.symref,
                        names.join(", ")
                    ),
                    &x.file,
                    range,
                ));
                for h in hits {
                    push_directive_row(
                        code,
                        cache,
                        &Bind {
                            entity: x.entity.clone(),
                            role,
                            identity: h.symref,
                            status: Status::May,
                            file: &x.file,
                            range,
                        },
                        rel,
                    );
                }
            }
            Resolution::NotFound {
                hidden: Some(_), ..
            } => {}
            Resolution::NotFound { hidden: None, .. } => rel.findings.push(operand_finding(
                "dangling-operand",
                &format!("`{}` resolves to nothing", x.symref),
                &x.file,
                range,
            )),
        }
    }
}

/// Rank 3: pack inference. Packs do not load yet (G04), so no rule runs and no row is added;
/// an entity that asked for inference (`attr infer`) is reported through
/// `Entity::infer_requested`, which the rules read as `inference-unavailable`.
fn infer(model: &Model, _code: &Code, _rel: &mut Relation) {
    let asked = model
        .entities
        .values()
        .filter(|e| e.infer_requested)
        .count();
    if asked > 0 {
        tracing::warn!(
            entities = asked,
            "pack inference requested but packs are not loaded"
        );
    }
}

/// Build B from the four sources.
pub fn build(model: &Model, code: &Code, directives: &[CodeDirective]) -> Relation {
    let mut rel = Relation::default();
    let cache = UnitCache::default();
    // Directive operands and targets resolve serially below; fold their files in parallel first.
    code.prefold(
        directives
            .iter()
            .flat_map(|d| [d.file.as_str(), d.target.as_str(), d.operand.as_str()])
            .chain(
                model
                    .entities
                    .values()
                    .flat_map(|e| &e.clauses)
                    .filter_map(|c| c.symref.as_deref()),
            )
            .map(path_of_symref),
    );
    for entity in model.entities.values() {
        for clause in &entity.clauses {
            if let Some(sel) = &clause.selector {
                selector_clause(code, &entity.anchor, clause, sel, &mut rel);
            } else if let Some(text) = &clause.symref {
                ref_clause(code, &cache, entity, clause, text, &mut rel);
            }
        }
    }
    for p in &model.plan {
        for clause in &p.clauses {
            if let Some(sel) = &clause.selector {
                selector_clause(code, &p.node.anchor, clause, sel, &mut rel);
            }
        }
    }
    for d in directives {
        code_directive(model, code, &cache, d, &mut rel);
    }
    model_directives(model, code, &cache, &mut rel);
    infer(model, code, &mut rel);
    tracing::info!(
        rows = rel.rows.len(),
        clauses = rel.clauses.len(),
        edges = rel.edges.len(),
        findings = rel.findings.len(),
        "relation built"
    );
    rel
}

#[cfg(test)]
mod tests {
    use std::fmt::Write;
    use std::path::Path;

    use grimble_model::ModelFiles;

    use super::build;
    use crate::code::Code;

    fn write_file(root: &Path, rel: &str, text: &str) {
        let p = root.join(rel);
        std::fs::create_dir_all(p.parent().expect("a file has a parent")).expect("mkdir");
        // frob:accept LOG001 because="test fixture writes a temp source file, not log output"
        std::fs::write(p, text).expect("write");
    }

    /// The python source, markdown spec and model ref blocks of `n` units.
    fn fixture_sources(n: usize) -> (String, String, String) {
        let (mut py, mut md, mut refs) = (String::new(), String::new(), String::new());
        for i in 0..n {
            write!(py, "def f{i}():\n    pass\n\n").ok();
            write!(md, "## Heading {i}\n\ntext\n\n").ok();
            write!(
                refs,
                "vmodel r{i} {{\n  kind artifact;\n  level requirements;\n  ref \"docs/spec.md#heading-{i}\";\n}}\n"
            )
            .ok();
        }
        (py, md, refs)
    }

    /// `Term::units` calls made by `build` over `n` selected units and `n` refs into one file.
    fn units_calls(n: usize) -> (usize, usize) {
        let dir = tempfile::tempdir().expect("tempdir");
        let model = write_fixture(dir.path(), n);
        measure_units(dir.path(), &model)
    }

    /// Writes the `n`-unit fixture tree under `root`; returns the model text.
    fn write_fixture(root: &Path, n: usize) -> String {
        let (py, md, refs) = fixture_sources(n);
        let model = format!(
            "grimble = \"2\";\nmodule m;\nnode a : trusted {{\n  owns \"src/**\";\n}}\n{refs}"
        );
        let tree = [
            ("src/m.py", &py),
            ("docs/spec.md", &md),
            ("design/m.grmb", &model),
        ];
        for (rel, text) in tree {
            write_file(root, rel, text);
        }
        model
    }

    /// `(units calls, row count)` of `build` over the fixture at `root`.
    fn measure_units(root: &Path, model: &str) -> (usize, usize) {
        let (code, directives) = fixture_code(root);
        let files = ModelFiles::new().with_file("design/m.grmb", model.as_bytes().to_vec());
        count_units(&crate::model::load(&files), &code, &directives)
    }

    /// The scanned code and directives of the fixture at `root`.
    fn fixture_code(root: &Path) -> (Code, Vec<crate::directives::CodeDirective>) {
        let walked = gob_walk::walk(root, &gob_walk::WalkConfig::default()).expect("walk");
        let code = Code::build(root, &walked.files);
        let directives = crate::directives::scan(&code);
        (code, directives)
    }

    /// `(units calls, row count)` of one `build` over the loaded model and scanned code.
    fn count_units(
        loaded: &crate::model::Model,
        code: &Code,
        directives: &[crate::directives::CodeDirective],
    ) -> (usize, usize) {
        let before = gob_ir::units_call_count();
        let rel = build(loaded, code, directives);
        let calls = gob_ir::units_call_count() - before;
        (calls, rel.rows.len())
    }

    #[test]
    // frob:tests crates/grimble-bind/src/relation.rs::build
    // frob:ticket 01M6ABTQZE6E047SKG212CQ663
    fn build_walks_units_a_constant_number_of_times_per_file() {
        let (small, small_rows) = units_calls(8);
        let (large, large_rows) = units_calls(64);
        assert!(
            small_rows >= 8 && large_rows >= 64,
            "{small_rows} {large_rows}"
        );
        assert!(small > 0, "the probe must see the walks");
        assert_eq!(
            small, large,
            "Term::units calls must not grow with the unit count"
        );
    }
}

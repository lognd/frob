//! The MDL checks (grmb-spec 11) over the AST and the loaded model.

// frob:ticket 01M4FGXTB8T0F8AHNN604XCAZV
// frob:ticket 01M4FGXVQTN5NJ0JBGWAMVHK82
// frob:ticket 01M3Z713VGKF4Z0JJ3263XJMC3

use std::collections::BTreeSet;

use gob_directives::is_full_ulid;
use gob_rules::{Finding, Registry, RequiredReason, RuleId, Severity};
use gob_text::{FileInterner, Span as TextSpan, TextRange};
use gob_walk::selector::{Expr, Node};

use crate::ast::{
    ClaimWhat, Clause, ClauseKind, Direction, Entity, EntityKind, Evidence, Exception, FileStatus,
    Header, Ident, KeyVal, Link, LinkKind, ModuleKind, QuantKey, Quantity, RefPath, Sel, Value,
};
use crate::fold::{LABELS, TRUST_LEVELS};
use crate::model::{EntityRec, Index, LoadedRoot, ModelFiles, Via, load_roots, root_list};
use crate::span::Span;
use crate::text::{canonical_level, clause_key, clause_text, selector_text};

/// Core node kinds (grmb-spec 4.1); a pack may add more.
const NODE_KINDS: [&str; 6] = [
    "component",
    "store",
    "queue",
    "cache",
    "gateway",
    "external",
];
/// Builtin transports (grmb-spec 4.2; `in-process` is spelled `in_process` to lex as an atom).
const TRANSPORTS: [&str; 5] = ["in_process", "http", "ipc", "ffi", "file"];
/// Vmodel levels, requirement side first (grmb-spec 4.5).
const LEVEL_PAIRS: [(&str, &str); 5] = [
    ("requirements", "customer_test"),
    ("requirement_spec", "customer_test_plan"),
    ("system_spec", "system_integration_test_plan"),
    ("system_design", "subsystem_integration_test_plan"),
    ("component_design", "component_unit_test"),
];

/// A deterministic file table: every supplied path interned in sorted order.
pub fn file_table(files: &ModelFiles) -> FileInterner {
    let mut t = FileInterner::new();
    for p in files.files.keys() {
        t.intern(p);
    }
    t
}

/// Runs every MDL rule over the models of `files` and returns the findings, sorted.
///
/// Spans use the ids of [`file_table`]. No file is read: the caller supplies bytes.
pub fn check_model(files: &ModelFiles) -> Vec<Finding> {
    let roots = load_roots(files);
    let mut ids = file_table(files);
    let mut out = root_findings(files, &roots, &mut ids);
    let mut seen_modules: Vec<(String, String)> = Vec::new();
    for root in &roots {
        let mut ck = Checker::new(files, root, &mut ids);
        ck.run();
        let module = root.files[0]
            .parsed
            .module
            .as_ref()
            .filter(|m| m.kind == ModuleKind::Module);
        if let Some(m) = module {
            if let Some((_, other)) = seen_modules.iter().find(|(n, _)| *n == m.name.text) {
                let msg = format!(
                    "root `{}` declares module `{}` which root `{other}` already declares",
                    root.root, m.name.text
                );
                ck.emit("MDL011", None, 0, m.name.span, msg, "file");
            }
            seen_modules.push((m.name.text.clone(), root.root.clone()));
        }
        out.extend(ck.out);
    }
    out.sort_by(|a, b| {
        let key = |f: &Finding| {
            f.span
                .map(|s| (s.file, u32::from(s.range.start()), u32::from(s.range.end())))
        };
        key(a)
            .cmp(&key(b))
            .then_with(|| a.rule.cmp(&b.rule))
            .then_with(|| a.message.cmp(&b.message))
    });
    out.dedup_by(|a, b| a.rule == b.rule && a.span == b.span && a.message == b.message);
    tracing::info!(findings = out.len(), roots = roots.len(), "model checked");
    out
}

/// MDL021 (no usable root) and MDL019 (orphan files) for the model roots of `files`.
// frob:ticket 01M3ZP159QB9VT8D4MBB5XVMKR
fn root_findings(files: &ModelFiles, roots: &[LoadedRoot], ids: &mut FileInterner) -> Vec<Finding> {
    let mut out = Vec::new();
    if files.files.is_empty() {
        return out;
    }
    let declared = root_list(files);
    let mut unresolved = |msg: String| {
        tracing::warn!(%msg, "no usable model root");
        if let Ok(id) = "MDL021".parse::<RuleId>() {
            out.push(
                Finding::new(id, Severity::Unresolved, None, msg, "model-root").with_required(
                    RequiredReason::ZeroSubjects {
                        rule: "MDL021".to_owned(),
                    },
                ),
            );
        }
    };
    if declared.is_empty() {
        unresolved(format!(
            "{} .grmb file(s) found but no model root is declared; list the entry file under `[grimble] models` in grimble.toml (`grimble init` writes `design/model.grmb`)",
            files.files.len()
        ));
        return out;
    }
    for r in declared.iter().filter(|r| !files.files.contains_key(*r)) {
        unresolved(format!(
            "declared model root `{r}` is not a .grmb file of the walk; fix `[grimble] models` in grimble.toml"
        ));
    }
    let reached: BTreeSet<&str> = roots
        .iter()
        .flat_map(|r| r.files.iter().map(|f| f.parsed.path.as_str()))
        .collect();
    let Ok(rule) = "MDL019".parse::<RuleId>() else {
        return out;
    };
    for path in files.files.keys().filter(|p| !reached.contains(p.as_str())) {
        tracing::debug!(%path, "orphan model file");
        let fid = ids.intern(path);
        out.push(Finding::new(
            rule.clone(),
            Severity::Warn,
            Some(TextSpan::new(fid, TextRange::new(0.into(), 0.into()))),
            format!(
                "`{path}` is reachable from no model root; include it from a root, list it under `[grimble] models`, or exclude it in `[check] exclude`"
            ),
            path,
        ));
    }
    out
}

#[derive(Clone, Copy, PartialEq, Eq, Debug)]
enum Dim {
    Time,
    Size,
    Count,
    Ratio,
    Rate,
}

const TIME: [&str; 7] = ["ns", "us", "ms", "s", "min", "h", "d"];
const SIZE: [&str; 5] = ["B", "KiB", "MiB", "GiB", "TiB"];
const COUNT: [&str; 4] = ["req", "msg", "evt", "op"];

fn dim_of(unit: &str) -> Option<Dim> {
    match unit.split_once('/') {
        None if TIME.contains(&unit) => Some(Dim::Time),
        None if SIZE.contains(&unit) => Some(Dim::Size),
        None if COUNT.contains(&unit) => Some(Dim::Count),
        None if unit == "%" => Some(Dim::Ratio),
        Some((n, d))
            if (COUNT.contains(&n) || SIZE.contains(&n) || n == "%") && TIME.contains(&d) =>
        {
            Some(Dim::Rate)
        }
        _ => None,
    }
}

fn date_ok(s: &str) -> bool {
    let p: Vec<&str> = s.split('-').collect();
    let [year, month, day] = p[..] else {
        return false;
    };
    let (Ok(year), Ok(month), Ok(day)) = (
        year.parse::<u32>(),
        month.parse::<u32>(),
        day.parse::<u32>(),
    ) else {
        return false;
    };
    let leap = (year % 4 == 0 && year % 100 != 0) || year % 400 == 0;
    let days = match month {
        1 | 3 | 5 | 7 | 8 | 10 | 12 => 31,
        4 | 6 | 9 | 11 => 30,
        2 if leap => 29,
        2 => 28,
        _ => return false,
    };
    (1..=days).contains(&day)
}

fn allowed(kind: EntityKind, key: &str) -> bool {
    if matches!(
        key,
        "alias" | "renamed_from" | "attr" | "accept" | "defer" | "hotfix"
    ) {
        return true;
    }
    match kind {
        EntityKind::Node => matches!(
            key,
            "kind" | "clearance" | "owns" | "may" | "excuses" | "surface"
        ),
        EntityKind::Flow => matches!(
            key,
            "label"
                | "rate"
                | "age"
                | "size"
                | "fanout"
                | "growth"
                | "transport"
                | "condition"
                | "producer"
                | "consumer"
                | "contract"
        ),
        EntityKind::Contract => matches!(key, "shape" | "versioning"),
        EntityKind::Claim => matches!(
            key,
            "noflow" | "reach" | "bound" | "proof" | "assumed" | "evidence"
        ),
        EntityKind::Vmodel => {
            matches!(key, "kind" | "level" | "ref" | "runnable")
                || LinkKind::ALL.iter().any(|l| l.keyword() == key)
        }
        EntityKind::Boundary => false,
        EntityKind::Pack => matches!(key, "ref" | "version" | "digest"),
    }
}

/// List clauses may repeat and be added by `extend`; everything else is scalar.
fn is_list(key: &str) -> bool {
    matches!(
        key,
        "owns"
            | "may"
            | "excuses"
            | "surface"
            | "producer"
            | "consumer"
            | "evidence"
            | "alias"
            | "renamed_from"
            | "attr"
            | "accept"
            | "defer"
            | "hotfix"
    ) || LinkKind::ALL.iter().any(|l| l.keyword() == key)
}

fn scalar_group(key: &str) -> &str {
    match key {
        "noflow" | "reach" | "bound" => "what",
        k => k,
    }
}

/// Where an exception clause sits.
#[derive(Clone, Copy)]
struct ExcCtx {
    file: usize,
    top: bool,
}

/// A `; did you mean ...` hint naming registered atoms whose last segment is `name` (`env` for `process.env`).
fn near_miss(name: &str) -> String {
    let tail = format!(".{name}");
    let hits: Vec<String> = gob_ir::registry::atoms()
        .into_iter()
        .filter(|a| a.name.ends_with(&tail))
        .map(|a| format!("`{}`", a.name))
        .collect();
    if hits.is_empty() {
        String::new()
    } else {
        format!("; did you mean {}?", hits.join(" or "))
    }
}

struct Checker<'a> {
    input: &'a ModelFiles,
    root: &'a LoadedRoot,
    idx: Index<'a>,
    ids: &'a mut FileInterner,
    out: Vec<Finding>,
    known_rules: BTreeSet<String>,
}

impl<'a> Checker<'a> {
    fn new(input: &'a ModelFiles, root: &'a LoadedRoot, ids: &'a mut FileInterner) -> Self {
        let mut known_rules: BTreeSet<String> =
            Registry::global().iter().map(|m| m.id.to_owned()).collect();
        known_rules.extend(input.extra_rules.iter().cloned());
        Self {
            input,
            root,
            idx: Index::build(root),
            ids,
            out: Vec::new(),
            known_rules,
        }
    }

    fn emit(
        &mut self,
        rule: &str,
        sev: Option<Severity>,
        file: usize,
        span: Span,
        msg: String,
        anchor: &str,
    ) {
        let Ok(id) = rule.parse::<RuleId>() else {
            return;
        };
        let severity = sev.unwrap_or_else(|| {
            Registry::global()
                .by_id(rule)
                .map_or(Severity::Error, |m| m.severity)
        });
        let path = &self.root.files[file].parsed.path;
        let fid = self.ids.intern(path);
        let clamp = |n: usize| u32::try_from(n).unwrap_or(u32::MAX);
        let range = TextRange::new(
            clamp(span.start).into(),
            clamp(span.end.max(span.start)).into(),
        );
        tracing::debug!(rule, path = %path, %span, %msg, "mdl finding");
        self.out.push(Finding::new(
            id,
            severity,
            Some(TextSpan::new(fid, range)),
            msg,
            anchor,
        ));
    }

    fn run(&mut self) {
        self.file_level();
        self.duplicates();
        let n = self.idx.entities.len();
        for i in 0..n {
            let rec = self.idx.entities[i].clone();
            self.entity(&rec);
        }
        for rec in self.idx.extensions.clone() {
            self.extension(&rec);
        }
        for top in self.idx.top_exceptions.clone() {
            self.top_exception(&top);
        }
        self.packs();
    }

    // ----- files, versions, modules, includes -----

    fn file_level(&mut self) {
        for fd in self.root.diags.clone() {
            let path = self.root.files[fd.file].parsed.path.clone();
            self.emit(
                fd.diag.rule,
                None,
                fd.file,
                fd.diag.span,
                fd.diag.message,
                &path,
            );
        }
        let majors: BTreeSet<&str> = self
            .root
            .files
            .iter()
            .filter_map(|f| f.parsed.version.as_ref().map(|v| v.value.as_str()))
            .collect();
        let root_module = self.root.files[0]
            .parsed
            .module
            .as_ref()
            .map(|m| m.name.text.clone());
        for (fi, f) in self.root.files.clone().iter().enumerate() {
            let p = &f.parsed;
            let path = p.path.clone();
            for d in &p.diags {
                self.emit(d.rule, None, fi, d.span, d.message.clone(), &path);
            }
            if let Some(v) = &p.version
                && majors.len() > 1
                && v.value
                    != self.root.files[0]
                        .parsed
                        .version
                        .as_ref()
                        .map_or("", |r| r.value.as_str())
            {
                self.emit(
                    "MDL007",
                    None,
                    fi,
                    v.span,
                    format!(
                        "file carries language major `{}` but the model's root differs",
                        v.value
                    ),
                    &path,
                );
            }
            if p.status != FileStatus::Parsed {
                continue;
            }
            for hit in crate::directive::scan(&p.comments) {
                if let Some((rule, msg)) = &hit.problem {
                    self.emit(rule, None, fi, hit.span, msg.clone(), &path);
                }
            }
            if let Some(m) = &p.module {
                match (m.kind, f.is_root) {
                    (ModuleKind::Module, false) => self.emit(
                        "MDL011",
                        None,
                        fi,
                        m.span,
                        format!("included file `{path}` declares `module`; only the root does"),
                        &path,
                    ),
                    (ModuleKind::PartOf, false) if Some(&m.name.text) != root_module.as_ref() => {
                        self.emit(
                            "MDL011",
                            None,
                            fi,
                            m.name.span,
                            format!(
                                "`part of {}` does not match the root module `{}`",
                                m.name.text,
                                root_module.as_deref().unwrap_or("?")
                            ),
                            &path,
                        );
                    }
                    (ModuleKind::PartOf, true) => self.emit(
                        "MDL011",
                        None,
                        fi,
                        m.span,
                        "the root file must declare `module`, not `part of`".to_owned(),
                        &path,
                    ),
                    _ => {}
                }
            }
        }
    }

    fn duplicates(&mut self) {
        for (name, claims) in self.idx.claims.clone() {
            let Some(first) = claims.first() else {
                continue;
            };
            for d in claims.iter().skip(1) {
                let msg = format!(
                    "`{name}` is already declared at {}:{}",
                    self.idx.path(first.file),
                    first.span
                );
                self.emit("MDL001", None, d.file, d.span, msg, &name);
            }
        }
    }

    // ----- helpers -----

    fn unresolved_sev(&self) -> Option<Severity> {
        self.idx.degraded.then_some(Severity::Unresolved)
    }

    fn resolve_kind(
        &mut self,
        (file, ctx): (usize, &[String]),
        path: &RefPath,
        want: &[EntityKind],
        wrong_kind_rule: &str,
        anchor: &str,
    ) -> Option<usize> {
        let Some(r) = self.idx.resolve(ctx, path) else {
            let sev = self.unresolved_sev();
            self.emit(
                "MDL006",
                sev,
                file,
                path.span,
                format!("`{}` resolves to no entity", path.written()),
                anchor,
            );
            return None;
        };
        if r.via == Via::Renamed {
            self.emit(
                "MDL012",
                None,
                file,
                path.span,
                format!(
                    "`{}` is a `renamed_from` name; use `{}`",
                    path.written(),
                    self.idx.entities[r.rec].full
                ),
                anchor,
            );
        }
        if let Some(sh) = r.shadows {
            self.emit(
                "MDL015",
                None,
                file,
                path.span,
                format!(
                    "`{}` resolves to `{}` which shadows `{}`; write `::{}` for the outer one",
                    path.written(),
                    self.idx.entities[r.rec].full,
                    self.idx.entities[sh].full,
                    path.dotted()
                ),
                anchor,
            );
        }
        let kind = self.idx.kind(r.rec);
        if !want.contains(&kind) {
            let names: Vec<&str> = want.iter().map(|k| k.keyword()).collect();
            self.emit(
                wrong_kind_rule,
                None,
                file,
                path.span,
                format!(
                    "`{}` is a {} but a {} is required here",
                    path.written(),
                    kind.keyword(),
                    names.join(" or ")
                ),
                anchor,
            );
            return None;
        }
        Some(r.rec)
    }

    fn lattice(&mut self, rec: &EntityRec<'_>, id: &Ident, set: &[&str], what: &str, anchor: &str) {
        if !set.contains(&id.text.as_str()) {
            self.emit(
                "MDL009",
                None,
                rec.file,
                id.span,
                format!("`{}` is not {what} ({})", id.text, set.join(", ")),
                anchor,
            );
        }
    }

    fn quantity(&mut self, rec: &EntityRec<'_>, q: &Quantity, want: Dim, what: &str, anchor: &str) {
        let msg = if q.unit.is_empty() {
            Some(format!("{what} needs a unit, found bare `{}`", q.number))
        } else {
            match dim_of(&q.unit) {
                None => Some(format!("`{}` is not a unit in the closed table", q.unit)),
                Some(d) if d == want => None,
                Some(d) => Some(format!(
                    "{what} needs a {want:?} quantity but `{}` is {d:?}",
                    q.unit
                )),
            }
        };
        if let Some(msg) = msg {
            self.emit("MDL009", None, rec.file, q.span, msg, anchor);
        }
    }

    fn value_dates(&mut self, rec: &EntityRec<'_>, v: &Value, span: Span, anchor: &str) {
        match v {
            Value::Date(d) if !date_ok(d) => self.emit(
                "MDL009",
                None,
                rec.file,
                span,
                format!("`{d}` is not a valid calendar date"),
                anchor,
            ),
            Value::Quantity(q) => self.quantity_any(rec, q, anchor),
            Value::List(items) => {
                for i in items {
                    self.value_dates(rec, i, span, anchor);
                }
            }
            _ => {}
        }
    }

    fn quantity_any(&mut self, rec: &EntityRec<'_>, q: &Quantity, anchor: &str) {
        if !q.unit.is_empty() && dim_of(&q.unit).is_none() {
            self.emit(
                "MDL009",
                None,
                rec.file,
                q.span,
                format!("`{}` is not a unit in the closed table", q.unit),
                anchor,
            );
        }
    }

    fn atom(
        &mut self,
        rec: &EntityRec<'_>,
        atom: &crate::ast::Atom,
        transport: bool,
        anchor: &str,
    ) {
        let known = match &atom.pack {
            None if transport => TRANSPORTS.contains(&atom.name.as_str()),
            None => {
                gob_ir::registry::atom(&atom.name).is_some()
                    || self
                        .input
                        .packs
                        .values()
                        .any(|pin| pin.atoms.contains(&atom.name))
            }
            Some(p) => {
                let declared = self
                    .idx
                    .entities
                    .iter()
                    .find(|e| e.entity.kind == EntityKind::Pack && e.entity.name.text == *p);
                declared
                    .and_then(|e| pack_id(e.entity))
                    .and_then(|id| self.input.packs.get(id))
                    .is_some_and(|pin| pin.atoms.contains(&atom.name))
            }
        };
        if !known {
            self.emit(
                "MDL016",
                None,
                rec.file,
                atom.span,
                format!(
                    "`{}` is in no registry and no enabled pack{}",
                    atom.written(),
                    near_miss(&atom.name)
                ),
                anchor,
            );
        }
    }

    fn selector(&mut self, rec: &EntityRec<'_>, sel: &Sel, anchor: &str) {
        let Ok(parsed) = &sel.parsed else { return };
        if let Some(walk) = &self.input.walk {
            let mut globs = Vec::new();
            collect_globs(parsed.root(), &mut globs);
            if !globs.is_empty() && !globs.iter().any(|g| walk.iter().any(|p| g.matches_path(p))) {
                self.emit(
                    "MDL005",
                    None,
                    rec.file,
                    sel.span,
                    format!(
                        "selector {} matches no file in the walk",
                        selector_text(sel)
                    ),
                    anchor,
                );
            }
        }
        if !satisfiable(parsed.root()) {
            self.emit(
                "MDL010",
                None,
                rec.file,
                sel.span,
                format!(
                    "selector {} cannot match anything whatever the repository holds",
                    selector_text(sel)
                ),
                anchor,
            );
        }
    }

    // ----- entities -----

    fn entity(&mut self, rec: &EntityRec<'_>) {
        let e = rec.entity;
        let anchor = format!("{}/{}", e.kind.keyword(), rec.full);
        let has_hole = e
            .clauses
            .iter()
            .any(|c| matches!(c.kind, ClauseKind::Hole(_)));
        let missing_sev = has_hole.then_some(Severity::Unresolved);
        self.header(rec, &anchor, missing_sev);
        self.clauses(rec, &anchor, false);
        self.required(rec, &anchor, missing_sev);
        if e.kind == EntityKind::Vmodel {
            self.vmodel(rec, &anchor);
        }
    }

    fn header(&mut self, rec: &EntityRec<'_>, anchor: &str, missing_sev: Option<Severity>) {
        let e = rec.entity;
        match &e.header {
            Header::Node { trust: Some(t) } => self.lattice(rec, t, &TRUST_LEVELS, "a trust level", anchor),
            Header::Node { trust: None } => self.emit(
                "MDL008",
                missing_sev,
                rec.file,
                e.name.span,
                format!("node `{}` has no trust level (`node {} : trusted`); there is no security default", e.name.text, e.name.text),
                anchor,
            ),
            Header::Flow { from, to } => {
                for r in [from, to] {
                    self.resolve_kind((rec.file, &rec.ctx), r, &[EntityKind::Node], "MDL006", anchor);
                }
            }
            Header::Boundary {
                direction,
                flow,
                from,
                to,
                ..
            } => {
                self.resolve_kind((rec.file, &rec.ctx), flow, &[EntityKind::Flow], "MDL006", anchor);
                let (set, what): (&[&str], &str) = match direction {
                    Direction::Endorse => (&TRUST_LEVELS, "an element of the trust lattice"),
                    Direction::Declassify => (&LABELS, "an element of the label lattice"),
                };
                for id in [from, to] {
                    self.lattice(rec, id, set, what, anchor);
                }
            }
            Header::None => {}
        }
    }

    fn required(&mut self, rec: &EntityRec<'_>, anchor: &str, sev: Option<Severity>) {
        let e = rec.entity;
        let has = |keys: &[&str]| {
            e.clauses
                .iter()
                .any(|c| keys.contains(&clause_key(&c.kind)))
        };
        let need: &[(&str, &[&str])] = match e.kind {
            EntityKind::Flow => &[("label", &["label"])],
            EntityKind::Contract => &[("shape", &["shape"])],
            EntityKind::Claim => &[("what", &["noflow", "reach", "bound"])],
            EntityKind::Vmodel => &[("kind", &["kind"]), ("level", &["level"])],
            EntityKind::Pack => &[("ref", &["ref"]), ("version", &["version"])],
            _ => &[],
        };
        for (name, keys) in need {
            if !has(keys) {
                self.emit(
                    "MDL008",
                    sev,
                    rec.file,
                    e.name.span,
                    format!(
                        "{} `{}` is missing required field `{name}`",
                        e.kind.keyword(),
                        e.name.text
                    ),
                    anchor,
                );
            }
        }
    }

    fn clauses(&mut self, rec: &EntityRec<'_>, anchor: &str, extension: bool) {
        let e = rec.entity;
        let mut seen: Vec<(String, String, Span)> = Vec::new();
        let mut scalar_seen: BTreeSet<String> = BTreeSet::new();
        let mut attr_keys: Vec<(String, String)> = Vec::new();
        for c in &e.clauses {
            let key = clause_key(&c.kind);
            let canon = clause_text(&c.kind);
            if matches!(c.kind, ClauseKind::Hole(_)) {
                continue;
            }
            if !allowed(e.kind, key) {
                self.emit(
                    "MDL000",
                    None,
                    rec.file,
                    c.span,
                    format!("clause `{key}` is not valid in a {}", e.kind.keyword()),
                    anchor,
                );
                continue;
            }
            if !is_list(key) {
                if extension {
                    self.emit(
                        "MDL008",
                        None,
                        rec.file,
                        c.span,
                        format!("`extend` may only add list clauses; `{key}` is scalar"),
                        anchor,
                    );
                } else if !scalar_seen.insert(scalar_group(key).to_owned()) {
                    self.emit(
                        "MDL008",
                        None,
                        rec.file,
                        c.span,
                        format!("scalar clause `{}` appears twice", scalar_group(key)),
                        anchor,
                    );
                }
            }
            if let ClauseKind::Attr { key: k, value } = &c.kind {
                let txt = value
                    .as_ref()
                    .map(|v| crate::text::value_text(&v.value))
                    .unwrap_or_default();
                if let Some((_, prev)) = attr_keys.iter().find(|(pk, _)| *pk == k.text) {
                    if *prev != txt {
                        self.emit(
                            "MDL008",
                            None,
                            rec.file,
                            c.span,
                            format!("attribute `{}` is set twice with different values", k.text),
                            anchor,
                        );
                    }
                } else {
                    attr_keys.push((k.text.clone(), txt));
                }
            }
            if is_list(key)
                && !matches!(c.kind, ClauseKind::Link(_))
                && let Some((_, _, first)) = seen.iter().find(|(k, t, _)| k == key && *t == canon)
            {
                let msg = format!("`{canon}` repeats the clause at bytes {first}");
                self.emit("MDL017", None, rec.file, c.span, msg, anchor);
            }
            seen.push((key.to_owned(), canon, c.span));
            self.clause(rec, c, anchor);
        }
    }

    #[allow(
        clippy::too_many_lines,
        reason = "a flat dispatch with one arm per clause kind (grmb-spec 4 and 11)"
    )]
    fn clause(&mut self, rec: &EntityRec<'_>, c: &Clause, anchor: &str) {
        let e = rec.entity;
        match &c.kind {
            ClauseKind::Owns(s)
            | ClauseKind::Surface(s)
            | ClauseKind::Producer(s)
            | ClauseKind::Consumer(s)
            | ClauseKind::Shape(s)
            | ClauseKind::Runnable(s)
            | ClauseKind::Evidence(Evidence::Tests(s)) => {
                self.selector(rec, s, anchor);
            }
            ClauseKind::May(m) => {
                self.atom(rec, &m.atom, false, anchor);
                if let Some(at) = &m.at {
                    self.selector(rec, at, anchor);
                }
            }
            ClauseKind::Excuses(x) => {
                self.atom(rec, &x.atom, false, anchor);
                if !matches!(x.attrs.iter().find(|a| a.key.text == "because"), Some(KeyVal { value, .. }) if matches!(value.value, Value::Str(_)))
                {
                    self.emit(
                        "MDL008",
                        None,
                        rec.file,
                        c.span,
                        format!("`excuses {}` requires `because=\"...\"`", x.atom.written()),
                        anchor,
                    );
                }
            }
            ClauseKind::Clearance(i) | ClauseKind::Label(i) => {
                self.lattice(rec, i, &LABELS, "a label", anchor);
            }
            ClauseKind::Kind(i) if e.kind == EntityKind::Node => {
                let has_pack = self
                    .idx
                    .entities
                    .iter()
                    .any(|x| x.entity.kind == EntityKind::Pack);
                if !has_pack && !NODE_KINDS.contains(&i.text.as_str()) {
                    self.emit(
                        "MDL009",
                        None,
                        rec.file,
                        i.span,
                        format!(
                            "`{}` is not a node kind ({})",
                            i.text,
                            NODE_KINDS.join(", ")
                        ),
                        anchor,
                    );
                }
            }
            ClauseKind::Kind(i) if e.kind == EntityKind::Vmodel => {
                if !["artifact", "test", "decision"].contains(&i.text.as_str()) {
                    self.emit(
                        "MDL009",
                        None,
                        rec.file,
                        i.span,
                        format!(
                            "`{}` is not a vmodel kind (artifact, test, decision)",
                            i.text
                        ),
                        anchor,
                    );
                }
            }
            ClauseKind::Quantity(k, q) => {
                let want = match k {
                    QuantKey::Rate => Dim::Rate,
                    QuantKey::Age => Dim::Time,
                    QuantKey::Size => Dim::Size,
                };
                self.quantity(rec, q, want, k.keyword(), anchor);
            }
            ClauseKind::Growth(q) => {
                self.quantity(rec, q, Dim::Rate, "growth", anchor);
                if q.unit.contains('/') && !q.unit.starts_with('%') {
                    self.emit(
                        "MDL009",
                        None,
                        rec.file,
                        q.span,
                        "growth is a ratio per time such as `15 %/d`".to_owned(),
                        anchor,
                    );
                }
            }
            ClauseKind::Transport(atoms) => {
                for a in atoms {
                    self.atom(rec, a, true, anchor);
                }
            }
            ClauseKind::Condition(i) => {
                if !["on_ok", "on_err"].contains(&i.text.as_str()) {
                    self.emit(
                        "MDL009",
                        None,
                        rec.file,
                        i.span,
                        format!("`{}` is not a condition (on_ok, on_err)", i.text),
                        anchor,
                    );
                }
            }
            ClauseKind::Contract(r) => {
                self.resolve_kind(
                    (rec.file, &rec.ctx),
                    r,
                    &[EntityKind::Contract],
                    "MDL006",
                    anchor,
                );
            }
            ClauseKind::Versioning(v) => self.versioning(rec, v, anchor),
            ClauseKind::What(w) => self.what(rec, w, anchor),
            ClauseKind::Proof(i) => {
                if !["L1", "L2", "L3", "L4", "L5"].contains(&i.text.as_str()) {
                    self.emit(
                        "MDL009",
                        None,
                        rec.file,
                        i.span,
                        format!("`{}` is not a proof level (L1..L5)", i.text),
                        anchor,
                    );
                }
            }
            ClauseKind::Assumed(kvs) => {
                for k in ["owner", "review", "because"] {
                    if !kvs.iter().any(|kv| kv.key.text == k) {
                        self.emit(
                            "MDL008",
                            None,
                            rec.file,
                            c.span,
                            format!("`assumed` requires `{k}=`"),
                            anchor,
                        );
                    }
                }
                for kv in kvs {
                    if kv.key.text == "review" && !matches!(kv.value.value, Value::Date(_)) {
                        self.emit(
                            "MDL009",
                            None,
                            rec.file,
                            kv.value.span,
                            "`review=` needs a date".to_owned(),
                            anchor,
                        );
                    }
                    self.value_dates(rec, &kv.value.value, kv.value.span, anchor);
                }
            }
            ClauseKind::Level(i) => {
                let canon = canonical_level(&i.text);
                let known = LEVEL_PAIRS.iter().any(|(a, b)| *a == canon || *b == canon);
                if !known {
                    self.emit(
                        "MDL009",
                        None,
                        rec.file,
                        i.span,
                        format!("`{}` is not a vmodel level", i.text),
                        anchor,
                    );
                }
            }
            ClauseKind::Attr { value: Some(v), .. } => {
                self.value_dates(rec, &v.value, v.span, anchor);
            }
            ClauseKind::Version(s) => {
                let ok = s.value.split('.').count() == 3
                    && s.value
                        .split('.')
                        .all(|p| !p.is_empty() && p.bytes().all(|b| b.is_ascii_digit()));
                if !ok {
                    self.emit(
                        "MDL009",
                        None,
                        rec.file,
                        s.span,
                        format!("`{}` is not an exact X.Y.Z version (no ranges)", s.value),
                        anchor,
                    );
                }
            }
            ClauseKind::Exception(x) => {
                let ctx = ExcCtx {
                    file: rec.file,
                    top: false,
                };
                self.exception(ctx, x, c.span, anchor);
            }
            _ => {}
        }
    }

    fn versioning(&mut self, rec: &EntityRec<'_>, v: &crate::ast::Versioning, anchor: &str) {
        for kv in &v.attrs {
            let val = match &kv.value.value {
                Value::Ident(i) => Some(i.as_str()),
                _ => None,
            };
            let (ok, what) = match kv.key.text.as_str() {
                "scheme" => (
                    val.is_some_and(|s| ["semver", "date", "integer", "none"].contains(&s)),
                    "scheme is one of semver, date, integer, none",
                ),
                "compat" => (
                    val.is_some_and(|s| ["backward", "forward", "full", "none"].contains(&s)),
                    "compat is one of backward, forward, full, none",
                ),
                "current" => (
                    matches!(kv.value.value, Value::Str(_)),
                    "current is a string",
                ),
                _ => (false, "versioning knows scheme, current and compat"),
            };
            if !ok {
                self.emit(
                    "MDL009",
                    None,
                    rec.file,
                    kv.value.span,
                    what.to_owned(),
                    anchor,
                );
            }
        }
    }

    fn what(&mut self, rec: &EntityRec<'_>, w: &ClaimWhat, anchor: &str) {
        match w {
            ClaimWhat::Noflow(a, b) | ClaimWhat::Reach(a, b) => {
                for r in [a, b] {
                    self.resolve_kind(
                        (rec.file, &rec.ctx),
                        r,
                        &[EntityKind::Node],
                        "MDL006",
                        anchor,
                    );
                }
            }
            ClaimWhat::Bound {
                metric,
                target,
                limit,
            } => {
                self.resolve_kind(
                    (rec.file, &rec.ctx),
                    target,
                    &[EntityKind::Node, EntityKind::Flow],
                    "MDL006",
                    anchor,
                );
                let want = match metric.text.as_str() {
                    "age" | "latency" => Some(Dim::Time),
                    "rate" => Some(Dim::Rate),
                    "size" => Some(Dim::Size),
                    "utilization" => Some(Dim::Ratio),
                    _ => None,
                };
                match want {
                    Some(d) => {
                        self.quantity(rec, limit, d, &format!("`bound {}`", metric.text), anchor);
                    }
                    None => self.emit(
                        "MDL009",
                        None,
                        rec.file,
                        metric.span,
                        format!(
                            "`{}` is not a metric (age, rate, latency, size, utilization)",
                            metric.text
                        ),
                        anchor,
                    ),
                }
            }
        }
    }

    // ----- exceptions -----

    fn exception(&mut self, ctx: ExcCtx, x: &Exception, span: Span, anchor: &str) {
        let ExcCtx { file, top } = ctx;
        if !self.known_rules.contains(&x.rule.text) && crate::parse::is_rule_token(&x.rule.text) {
            self.emit(
                "MDL013",
                None,
                file,
                x.rule.span,
                format!("`{}` is not a known rule id", x.rule.text),
                anchor,
            );
        }
        match (&x.on, top) {
            (Some(on), false) => self.emit(
                "MDL013",
                None,
                file,
                on.span,
                "`on` is omitted inside an entity body; the target is that entity".to_owned(),
                anchor,
            ),
            (None, true) => self.emit(
                "MDL013",
                None,
                file,
                span,
                "a top-level exception needs `on REF`".to_owned(),
                anchor,
            ),
            _ => {}
        }
        let (required, optional): (&[&str], &[&str]) = match x.kind {
            crate::ast::ExcKind::Accept => (&["because"], &[]),
            crate::ast::ExcKind::Defer => (&["ticket", "because"], &["until"]),
            crate::ast::ExcKind::Hotfix => (&["ticket", "because"], &[]),
        };
        for r in required {
            if !x.attrs.iter().any(|a| a.key.text == *r) {
                self.emit(
                    "MDL013",
                    None,
                    file,
                    span,
                    format!("`{}` requires `{r}=`", x.kind.keyword()),
                    anchor,
                );
            }
        }
        for a in &x.attrs {
            let k = a.key.text.as_str();
            if !required.contains(&k) && !optional.contains(&k) {
                self.emit(
                    "MDL013",
                    None,
                    file,
                    a.key.span,
                    format!("`{}` does not take `{k}=`", x.kind.keyword()),
                    anchor,
                );
                continue;
            }
            let ok = match (k, &a.value.value) {
                ("because", Value::Str(_)) => true,
                ("ticket", Value::Str(s)) => is_full_ulid(s),
                ("until", Value::Date(d)) => date_ok(d),
                _ => false,
            };
            if !ok {
                self.emit(
                    "MDL013",
                    None,
                    file,
                    a.value.span,
                    format!("`{k}=` is malformed (because: string, ticket: full ULID string, until: calendar date)"),
                    anchor,
                );
            }
        }
    }

    fn top_exception(&mut self, top: &crate::model::TopExcRec<'_>) {
        let x = &top.exc.exception;
        let anchor = format!("exception/{}", x.rule.text);
        let ctx = ExcCtx {
            file: top.file,
            top: true,
        };
        self.exception(ctx, x, top.exc.span, &anchor);
        if let Some(on) = &x.on {
            self.resolve_kind(
                (top.file, &top.ctx),
                on,
                &EntityKind::ALL,
                "MDL006",
                &anchor,
            );
        }
    }

    // ----- extensions -----

    fn extension(&mut self, rec: &EntityRec<'_>) {
        let e = rec.entity;
        let anchor = format!("{}/{}", e.kind.keyword(), rec.full);
        if self
            .resolve_kind(
                (rec.file, &rec.ctx),
                &e.target,
                &[e.kind],
                "MDL006",
                &anchor,
            )
            .is_some()
        {
            self.clauses(rec, &anchor, true);
        }
    }

    // ----- vmodel -----

    fn vmodel(&mut self, rec: &EntityRec<'_>, anchor: &str) {
        let e = rec.entity;
        let kind = vm_ident(e, true);
        let slevel = vm_ident(e, false);
        let has = |k: &str| e.clauses.iter().any(|c| clause_key(&c.kind) == k);
        if kind.as_deref() == Some("artifact") && !has("ref") {
            let msg = format!("artifact `{}` needs `ref \"SYMREF\"`", e.name.text);
            self.emit("MDL014", None, rec.file, e.name.span, msg, anchor);
        }
        if kind.as_deref() == Some("test") && !has("runnable") {
            let msg = format!("test `{}` needs `runnable SELECTOR`", e.name.text);
            self.emit("MDL014", None, rec.file, e.name.span, msg, anchor);
        }
        let mut seen: Vec<String> = Vec::new();
        for c in &e.clauses {
            let ClauseKind::Link(l) = &c.kind else {
                continue;
            };
            let text = clause_text(&c.kind);
            if seen.contains(&text) {
                self.emit(
                    "MDL014",
                    None,
                    rec.file,
                    c.span,
                    format!("duplicate link `{text}`"),
                    anchor,
                );
                continue;
            }
            seen.push(text);
            self.vmodel_link(rec, anchor, c, l, (kind.as_deref(), slevel.as_deref()));
        }
    }

    fn vmodel_link(
        &mut self,
        rec: &EntityRec<'_>,
        anchor: &str,
        c: &Clause,
        l: &Link,
        (kind, level): (Option<&str>, Option<&str>),
    ) {
        let file = rec.file;
        if l.kind == LinkKind::Supersedes && l.because.is_none() {
            let msg = "`supersedes` requires `because=\"...\"`".to_owned();
            self.emit("MDL014", None, file, c.span, msg, anchor);
        }
        let Some(r) = self.idx.resolve(&rec.ctx, &l.target) else {
            let sev = self.unresolved_sev();
            let msg = format!("`{}` resolves to no entity", l.target.written());
            self.emit("MDL006", sev, file, l.target.span, msg, anchor);
            return;
        };
        let target = self.idx.entities[r.rec].entity;
        if r.via == Via::Renamed {
            let msg = format!("`{}` is a `renamed_from` name", l.target.written());
            self.emit("MDL012", None, file, l.target.span, msg, anchor);
        }
        if target.kind != EntityKind::Vmodel {
            let msg = format!(
                "link target `{}` is a {}, not a vmodel",
                l.target.written(),
                target.kind.keyword()
            );
            self.emit("MDL014", None, file, l.target.span, msg, anchor);
            return;
        }
        let tkind = vm_ident(target, true);
        let tlevel = vm_ident(target, false);
        if let Some(msg) = link_error(l.kind, (kind, level), (tkind.as_deref(), tlevel.as_deref()))
        {
            self.emit("MDL014", None, file, c.span, msg, anchor);
        }
    }

    // ----- packs -----

    fn packs(&mut self) {
        for rec in self.idx.entities.clone() {
            let e = rec.entity;
            if e.kind != EntityKind::Pack {
                continue;
            }
            let anchor = format!("pack/{}", rec.full);
            let Some(id) = pack_id(e) else { continue };
            let pin = |key: &str| {
                e.clauses.iter().find_map(|c| match (&c.kind, key) {
                    (ClauseKind::Version(s), "version") | (ClauseKind::Digest(s), "digest") => {
                        Some(s.clone())
                    }
                    _ => None,
                })
            };
            let Some(avail) = self.input.packs.get(id).cloned() else {
                self.emit(
                    "MDL004",
                    None,
                    rec.file,
                    e.name.span,
                    match self.input.pack_problems.get(id) {
                        Some(why) => format!("pack `{id}` cannot be loaded: {why}"),
                        None => format!("pack `{id}` is not enabled or not under `packs/`"),
                    },
                    &anchor,
                );
                continue;
            };
            if let Some(v) = pin("version")
                && v.value != avail.version
            {
                self.emit(
                    "MDL004",
                    None,
                    rec.file,
                    v.span,
                    format!(
                        "pack `{id}` is pinned at {} but {} is available",
                        v.value, avail.version
                    ),
                    &anchor,
                );
            }
            if let (Some(d), Some(have)) = (pin("digest"), &avail.digest)
                && d.value != *have
            {
                self.emit(
                    "MDL004",
                    None,
                    rec.file,
                    d.span,
                    format!("pack `{id}` digest differs from the pin"),
                    &anchor,
                );
            }
        }
    }
}

fn pack_id(e: &Entity) -> Option<&str> {
    e.clauses.iter().find_map(|c| match &c.kind {
        ClauseKind::Ref(s) => Some(s.value.as_str()),
        _ => None,
    })
}

fn collect_globs(n: &Node, out: &mut Vec<gob_walk::Glob>) {
    match &n.expr {
        Expr::Glob(g) => out.push(g.clone()),
        Expr::Not(i) => collect_globs(i, out),
        Expr::And(ops) | Expr::Or(ops) => ops.iter().for_each(|o| collect_globs(o, out)),
        _ => {}
    }
}

fn text_of(n: &Node) -> String {
    gob_walk::Selector::new(n.clone()).to_string()
}

/// False when the selector cannot match any identity whatever the repository holds.
fn satisfiable(n: &Node) -> bool {
    match &n.expr {
        Expr::Or(ops) => ops.iter().any(satisfiable),
        Expr::And(ops) => {
            if !ops.iter().all(satisfiable) {
                return false;
            }
            let mut langs: Vec<&str> = ops
                .iter()
                .filter_map(|o| match &o.expr {
                    Expr::Lang(l) => Some(l.as_str()),
                    _ => None,
                })
                .collect();
            langs.sort_unstable();
            langs.dedup();
            if langs.len() > 1 {
                return false;
            }
            let kinds: Vec<&Vec<String>> = ops
                .iter()
                .filter_map(|o| match &o.expr {
                    Expr::Kind(k) => Some(k),
                    _ => None,
                })
                .collect();
            if kinds.len() > 1
                && kinds[0]
                    .iter()
                    .all(|k| kinds.iter().any(|ks| !ks.contains(k)))
            {
                return false;
            }
            let positive: Vec<String> = ops
                .iter()
                .filter(|o| !matches!(o.expr, Expr::Not(_)))
                .map(text_of)
                .collect();
            !ops.iter().any(|o| match &o.expr {
                Expr::Not(inner) => positive.contains(&text_of(inner)),
                _ => false,
            })
        }
        _ => true,
    }
}

/// The `kind` (or canonical `level`) identifier of a vmodel entity.
fn vm_ident(e: &Entity, kind: bool) -> Option<String> {
    e.clauses.iter().find_map(|c| match &c.kind {
        ClauseKind::Kind(i) if kind => Some(i.text.clone()),
        ClauseKind::Level(i) if !kind => Some(canonical_level(&i.text).to_owned()),
        _ => None,
    })
}

/// Why a link between two vmodel entities is ill-formed (grmb-spec 4.5), if it is.
fn link_error(
    link: LinkKind,
    (kind, level): (Option<&str>, Option<&str>),
    (tkind, tlevel): (Option<&str>, Option<&str>),
) -> Option<String> {
    match link {
        LinkKind::Verifies if kind != Some("test") || tkind != Some("artifact") => {
            Some("`verifies` joins a test to an artifact".to_owned())
        }
        LinkKind::Verifies => match (level, tlevel) {
            (Some(sl), Some(tl))
                if !LEVEL_PAIRS
                    .iter()
                    .any(|(req, test)| *req == tl && *test == sl) =>
            {
                Some(format!(
                    "`verifies` between unpaired levels `{sl}` and `{tl}`"
                ))
            }
            _ => None,
        },
        LinkKind::Satisfies if kind != Some("artifact") || tkind != Some("artifact") => {
            Some("`satisfies` joins two artifacts".to_owned())
        }
        LinkKind::Supersedes if kind != Some("decision") || tkind != Some("decision") => {
            Some("`supersedes` joins two decisions".to_owned())
        }
        _ => None,
    }
}

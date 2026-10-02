//! The U encoding of a parsed file (grmb-spec 9): one term and scope graph per file.
//!
//! The fold builds a small owned tree first so that every `group(unordered)` can be put in
//! canonical order (sorted by a location-free key) before it is lowered into the arena.
//! That is what makes `a & b` and `b & a`, and a file with its items permuted, one term.

use std::collections::BTreeMap;

use gob_ir::{
    AttrValue, DeclKind, GroupOrder, Label, Location, NodeId, NodeSpec, Operator, ScopeGraph,
    Status, Term, TermBuilder, TermError, reserved,
};
use gob_text::FileInterner;
use gob_walk::selector::{Cmp, Expr, Node, Value as SelValue};

use crate::ast::{
    ClaimWhat, Clause, ClauseKind, Direction, Entity, EntityKind, Evidence, Exception, FileStatus,
    Header, Item, KeyVal, ParsedFile, Quantity, Sel, Value,
};
use crate::directive::{DirectiveHit, scan};
use crate::lex::CommentKind;
use crate::span::Span;
use crate::text::{
    canon_node, canonical_level, clause_key, clause_sort_key, clause_text, quantity_text,
    value_kind, value_text,
};

/// The language tag of every .grmb term.
pub const LANG: &str = "grmb";

/// Trust lattice, lowest first (grmb-spec 4.1).
pub const TRUST_LEVELS: [&str; 3] = ["foreign", "authenticated", "trusted"];
/// Label lattice, lowest first (grmb-spec 4.1).
pub const LABELS: [&str; 4] = ["Public", "Internal", "Pii", "Secret"];

/// Where a clause lands in the unit (facet placement).
#[derive(Clone, Copy, PartialEq, Eq)]
enum Place {
    Sig,
    Body,
    Attr,
}

/// An owned, location-carrying term tree.
struct T {
    op: Operator,
    name: Option<String>,
    span: Span,
    attrs: Vec<(String, AttrValue)>,
    children: Vec<T>,
    binders: Vec<String>,
    tag: Option<usize>,
}

impl T {
    fn new(op: Operator, span: Span, children: Vec<T>) -> Self {
        Self {
            op,
            name: None,
            span,
            attrs: Vec::new(),
            children,
            binders: Vec::new(),
            tag: None,
        }
    }

    fn named(mut self, name: &str) -> Self {
        self.name = Some(name.to_owned());
        self
    }

    fn with(mut self, k: &str, v: impl Into<AttrValue>) -> Self {
        self.attrs.push((k.to_owned(), v.into()));
        self
    }

    fn tagged(mut self, id: usize) -> Self {
        self.tag = Some(id);
        self
    }

    fn sig(self) -> Self {
        self.with(reserved::FACET, "sig")
    }

    fn key(&self) -> String {
        let kids: Vec<String> = self.children.iter().map(T::key).collect();
        format!("{:?}|{:?}|{:?}|[{}]", self.op, self.name, self.binders, kids.join(","))
    }

    fn is_unordered_group(&self) -> bool {
        matches!(
            &self.op,
            Operator::Universal(gob_ir::Universal::Group {
                order: GroupOrder::Unordered
            })
        )
    }
}

fn lit(kind: &str, lexeme: &str, span: Span) -> T {
    T::new(Operator::lit(kind, lexeme), span, vec![])
}

fn reference(name: &str, span: Span) -> T {
    T::new(Operator::reference(name), span, vec![])
}

fn attr(name: &str, span: Span, children: Vec<T>) -> T {
    T::new(Operator::attr(name), span, children)
}

fn apply(kind: &str, span: Span, children: Vec<T>) -> T {
    T::new(Operator::apply(kind), span, children)
}

fn group(order: GroupOrder, span: Span, children: Vec<T>) -> T {
    T::new(Operator::group(order), span, children)
}

fn unordered(span: Span, children: Vec<T>) -> T {
    group(GroupOrder::Unordered, span, children)
}

fn sel_value_lit(v: &SelValue, span: Span) -> T {
    match v {
        SelValue::Str(s) => lit("string", s, span),
        SelValue::Number(n) => lit("number", n, span),
        SelValue::Quantity { number, unit } => {
            let q = Quantity {
                number: number.clone(),
                unit: unit.clone(),
                span,
            };
            lit("quantity", &quantity_text(&q), span)
        }
        SelValue::Ident(i) => lit("ident", i, span),
    }
}

fn expr_t(n: &Node) -> T {
    let span = Span::new(n.span.start, n.span.end);
    match &n.expr {
        Expr::Glob(g) => lit("glob", &g.text(), span),
        Expr::Lang(l) => apply("pred", span, vec![reference("lang", span), lit("ident", l, span)]),
        Expr::Kind(ks) => {
            let mut kids = vec![reference("kind", span)];
            kids.extend(ks.iter().map(|k| lit("ident", k, span)));
            apply("pred", span, kids)
        }
        Expr::Attr(p) => {
            let mut kids = vec![reference("attr", span), lit("ident", &p.name, span)];
            if let Some((cmp, v)) = &p.test {
                let sym = match cmp {
                    Cmp::Eq | Cmp::Ne | Cmp::Match | Cmp::Le => cmp.symbol(),
                };
                kids.push(lit("cmp", sym, span));
                kids.push(sel_value_lit(v, span));
            }
            apply("pred", span, kids)
        }
        Expr::Not(inner) => apply("not", span, vec![unordered(span, vec![expr_t(inner)])]),
        Expr::And(ops) => apply(
            "and",
            span,
            vec![unordered(span, ops.iter().map(expr_t).collect())],
        ),
        Expr::Or(ops) => apply(
            "or",
            span,
            vec![unordered(span, ops.iter().map(expr_t).collect())],
        ),
    }
}

fn select_t(sel: &Sel) -> T {
    let expr = match &sel.parsed {
        Ok(s) => expr_t(&canon_node(s.root())),
        Err(_) => T::new(Operator::hole("parse-error"), sel.span, vec![]),
    };
    apply("select", sel.span, vec![expr])
}

fn kv_attr(kv: &KeyVal) -> T {
    let payload = match &kv.value.value {
        Value::List(items) => group(
            GroupOrder::Sequence,
            kv.value.span,
            items.iter().map(|v| lit(value_kind(v), &lit_lexeme(v), kv.value.span)).collect(),
        ),
        v => lit(value_kind(v), &lit_lexeme(v), kv.value.span),
    };
    attr(&kv.key.text, kv.key.span.to(kv.value.span), vec![payload])
}

/// The lexeme of a scalar literal: strings unquoted, others as spelled.
fn lit_lexeme(v: &Value) -> String {
    match v {
        Value::Str(s) => s.clone(),
        other => value_text(other),
    }
}

fn exception_t(e: &Exception, span: Span) -> T {
    let mut kids = vec![reference(&e.rule.text, e.rule.span)];
    if let Some(on) = &e.on {
        kids.push(reference(&on.written(), on.span));
    }
    kids.extend(e.attrs.iter().map(kv_attr));
    attr(e.kind.keyword(), span, vec![unordered(span, kids)])
}

/// The outcome of folding one file.
pub struct FoldedFile {
    /// The term.
    pub term: Term,
    /// The scope graph with the builtin scope.
    pub scopes: ScopeGraph,
    /// Every directive bound to its target.
    pub directives: Vec<BoundDirective>,
}

/// A directive and the anchor of the item it binds to.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct BoundDirective {
    /// The directive.
    pub hit: DirectiveHit,
    /// The logical location of the target: `file`, `node/cli` or `node/cli/owns[0]`.
    pub anchor: String,
    /// The term node the directive attr hangs under.
    pub target: NodeId,
}

struct Folder<'a> {
    f: &'a ParsedFile,
    prefix: String,
    hits: Vec<DirectiveHit>,
    anchors: BTreeMap<usize, String>,
}

/// Folds a parsed file into its U term (total; a bad file yields holes and opaque nodes).
///
/// `mount` is the `include ... as P` prefix the file is mounted under (empty at the root).
///
/// # Errors
///
/// [`TermError`] only if the fold builds an ill-formed term (a bug in this module).
pub fn fold_file(file: &ParsedFile, mount: &str) -> Result<FoldedFile, TermError> {
    let hits = scan(&file.comments);
    let mut fo = Folder {
        f: file,
        prefix: mount.to_owned(),
        hits,
        anchors: BTreeMap::new(),
    };
    let tree = fo.file_tree();
    let mut files = FileInterner::new();
    let fid = files.intern(&file.path);
    let edition = file
        .version
        .as_ref()
        .map_or_else(|| "?".to_owned(), |v| v.value.clone());
    let lang_param = format!("grimble=\"{edition}\"");
    let mut b = TermBuilder::new(&file.path, LANG);
    let mut ids = BTreeMap::new();
    let root = lower(&tree, &mut b, fid, &lang_param, &mut ids)?;
    let term = b.finish(root)?;
    let mut scopes = ScopeGraph::from_term(&term);
    add_builtin_scope(&term, &mut scopes);
    let mut directives = Vec::new();
    for hit in &fo.hits {
        let target_id = fo.target_of(hit);
        let anchor = target_id.and_then(|t| fo.anchors.get(&t).cloned()).unwrap_or_else(|| "file".to_owned());
        let node = target_id.and_then(|t| ids.get(&t).copied()).unwrap_or(root);
        directives.push(BoundDirective {
            hit: hit.clone(),
            anchor,
            target: node,
        });
    }
    tracing::debug!(
        path = %file.path,
        nodes = term.len(),
        directives = directives.len(),
        "grmb file folded"
    );
    Ok(FoldedFile {
        term,
        scopes,
        directives,
    })
}

fn lower(
    t: &T,
    b: &mut TermBuilder,
    fid: gob_text::FileId,
    lang_param: &str,
    ids: &mut BTreeMap<usize, NodeId>,
) -> Result<NodeId, TermError> {
    let mut order: Vec<&T> = t.children.iter().collect();
    if t.is_unordered_group() {
        order.sort_by_cached_key(|c| c.key());
    }
    let mut kids = Vec::with_capacity(order.len());
    for c in order {
        kids.push(lower(c, b, fid, lang_param, ids)?);
    }
    let clamp = |n: usize| u32::try_from(n).unwrap_or(u32::MAX);
    let mut spec = NodeSpec::new(
        t.op.clone(),
        Location::text(fid, clamp(t.span.start), clamp(t.span.end.max(t.span.start))),
    )
    .lang_param(lang_param);
    if let Some(n) = &t.name {
        spec = spec.named(n);
    }
    if !t.binders.is_empty() {
        let names: Vec<&str> = t.binders.iter().map(String::as_str).collect();
        spec = spec.binders(&names);
    }
    for (k, v) in &t.attrs {
        spec = spec.attr(k, v.clone());
    }
    let id = b.node(spec, &kids)?;
    if let Some(tag) = t.tag {
        ids.insert(tag, id);
    }
    Ok(id)
}

fn add_builtin_scope(term: &Term, g: &mut ScopeGraph) {
    let Some(file_scope) = g.scope_at(term.root()) else {
        return;
    };
    let Some(root_scope) = g.edges(file_scope).first().map(|e| e.target) else {
        return;
    };
    let builtin = g.add_scope(None);
    let mut names: Vec<String> = TRUST_LEVELS
        .iter()
        .chain(LABELS.iter())
        .map(|s| (*s).to_owned())
        .collect();
    names.extend(["lang", "kind", "attr"].map(str::to_owned));
    names.extend(gob_ir::registry::atoms().iter().map(|a| a.name.to_owned()));
    names.extend(
        gob_rules::Registry::global()
            .iter()
            .map(|m| m.id.to_owned()),
    );
    for n in names {
        g.declare(builtin, &n, None, DeclKind::Other, Status::Must, None);
    }
    g.add_edge(root_scope, Label::Custom("builtin".to_owned()), builtin, Status::Must);
}

impl Folder<'_> {
    fn full_name(&self, ns: &[String], name: &str) -> String {
        let mut parts: Vec<&str> = Vec::new();
        if !self.prefix.is_empty() {
            parts.push(&self.prefix);
        }
        parts.extend(ns.iter().map(String::as_str));
        parts.push(name);
        parts.join(".")
    }

    fn target_of(&self, hit: &DirectiveHit) -> Option<usize> {
        self.f
            .attachments
            .by_target
            .iter()
            .find(|(_, cs)| cs.contains(&hit.comment))
            .map(|(id, _)| *id)
    }

    /// Doc attrs, comments and directive attrs bound to target `id`.
    fn attachments(&self, id: Option<usize>) -> Vec<T> {
        let comments: &[usize] = match id {
            Some(id) => self.f.attachments.of(id),
            None => &self.f.attachments.file,
        };
        let mut out = Vec::new();
        let docs: Vec<&crate::lex::Comment> = comments
            .iter()
            .map(|&i| &self.f.comments[i])
            .filter(|c| c.kind == CommentKind::Doc)
            .collect();
        if let Some(first) = docs.first() {
            let text = docs
                .iter()
                .map(|c| c.doc_text())
                .collect::<Vec<_>>()
                .join("\n");
            let span = first.span.to(docs[docs.len() - 1].span);
            out.push(attr("doc", span, vec![lit("prose", &text, span)]));
        }
        for &ci in comments {
            let c = &self.f.comments[ci];
            if c.kind != CommentKind::Doc {
                out.push(T::new(Operator::comment(&c.text), c.span, vec![]));
            }
        }
        for h in &self.hits {
            if comments.contains(&h.comment) {
                out.push(attr(
                    &h.qualified(),
                    h.span,
                    vec![lit("directive", &h.args, h.span)],
                ));
            }
        }
        out
    }

    fn file_tree(&mut self) -> T {
        let f = self.f;
        let whole = Span::new(0, f.size);
        let mut root = T::new(Operator::unit("module", "declaration"), whole, vec![])
            .with(reserved::ATTRS_PROVIDED, true);
        if let Some(v) = &f.version {
            root.children
                .push(attr("grimble-version", v.span, vec![lit("string", &v.value, v.span)]));
        }
        match &f.status {
            FileStatus::Opaque(reason) => {
                root.children
                    .push(T::new(Operator::opaque(reason, &f.raw), whole, vec![]));
                return root;
            }
            FileStatus::Refused(reason) => {
                root.children
                    .push(T::new(Operator::opaque(reason, f.text.as_bytes()), whole, vec![]));
                return root;
            }
            FileStatus::Parsed => {}
        }
        if let Some(m) = &f.module {
            let mut n = attr("module", m.span, vec![lit("ident", &m.name.text, m.name.span)]).tagged(m.id);
            n.children.extend(self.attachments(Some(m.id)));
            self.anchors.insert(m.id, "file/module".to_owned());
            root.children.push(n);
        }
        let mut items = Vec::new();
        let mut extra = Vec::new();
        self.items(&f.items, &[], &mut items, &mut extra);
        for s in &f.lex_holes {
            items.push(T::new(Operator::hole("parse-error"), *s, vec![]));
        }
        if !items.is_empty() {
            root.children.push(unordered(whole, items));
        }
        root.children.extend(extra);
        root.children.extend(self.attachments(None));
        root
    }

    fn items(&mut self, items: &[Item], ns: &[String], out: &mut Vec<T>, extra: &mut Vec<T>) {
        for item in items {
            match item {
                Item::Include(inc) => {
                    let head = reference(&inc.path.value, inc.path.span);
                    let ap = apply("include", inc.span, vec![head]);
                    let mut node = match &inc.mount {
                        Some(m) => {
                            let mut b = T::new(
                                Operator::bind("mount", "prefix"),
                                inc.span,
                                vec![unordered(inc.span, vec![]), ap],
                            );
                            b.binders = vec![m.dotted()];
                            b
                        }
                        None => ap,
                    }
                    .tagged(inc.id);
                    self.anchors.insert(inc.id, format!("include/{}", inc.path.value));
                    node.children.extend(self.attachments(Some(inc.id)));
                    out.push(node);
                }
                Item::Namespace(n) => {
                    let mut inner_ns = ns.to_vec();
                    inner_ns.push(n.name.text.clone());
                    let mut inner = Vec::new();
                    self.items(&n.items, &inner_ns, &mut inner, extra);
                    let full = self.full_name(ns, &n.name.text);
                    self.anchors.insert(n.id, format!("namespace/{full}"));
                    let mut u = T::new(Operator::unit("namespace", "declaration"), n.span, vec![])
                        .named(&n.name.text)
                        .with("grmb.anchor", format!("namespace/{full}"))
                        .tagged(n.id);
                    if !inner.is_empty() {
                        u.children.push(unordered(n.span, inner));
                    }
                    u.children.extend(self.attachments(Some(n.id)));
                    out.push(u);
                }
                Item::Entity(e) => out.push(self.entity(e, ns)),
                Item::Exception(t) => {
                    let mut a = exception_t(&t.exception, t.span).tagged(t.id);
                    self.anchors.insert(t.id, format!("exception/{}", t.exception.rule.text));
                    a.children.extend(self.attachments(Some(t.id)));
                    extra.push(a);
                }
                Item::Hole { id, span, .. } => {
                    self.anchors.insert(*id, "file".to_owned());
                    out.push(T::new(Operator::hole("parse-error"), *span, vec![]).tagged(*id));
                    // Comments bound to a hole cannot hang on it: hoist them to the file.
                    extra.extend(self.attachments(Some(*id)));
                }
            }
        }
    }

    fn entity(&mut self, e: &Entity, ns: &[String]) -> T {
        let unit_name = if e.extension {
            e.target.dotted()
        } else {
            e.name.text.clone()
        };
        let full = self.full_name(ns, &unit_name);
        let kw = e.kind.keyword();
        let anchor = format!("{kw}/{full}");
        self.anchors.insert(e.id, anchor.clone());
        let role = if e.extension { "extension" } else { "declaration" };
        let mut unit = T::new(Operator::unit(kw, role), e.span, vec![])
            .named(&unit_name)
            .with("grmb.anchor", anchor.clone())
            .tagged(e.id);
        self.header_nodes(e, &mut unit);
        let mut clauses: Vec<&Clause> = e.clauses.iter().collect();
        clauses.sort_by_cached_key(|c| clause_sort_key(c));
        let mut counters: BTreeMap<&'static str, usize> = BTreeMap::new();
        let mut body = Vec::new();
        let mut direct = Vec::new();
        let mut prev: Option<(&Clause, String)> = None;
        for c in clauses {
            let text = clause_text(&c.kind);
            let has_att = !self.f.attachments.of(c.id).is_empty();
            if let Some((_, pt)) = &prev
                && *pt == text
                && !has_att
            {
                continue;
            }
            prev = Some((c, text));
            let key = clause_key(&c.kind);
            let n = counters.entry(key).or_insert(0);
            let clause_anchor = format!("{anchor}/{key}[{n}]");
            *n += 1;
            self.anchors.insert(c.id, clause_anchor.clone());
            let (mut node, place) = self.clause(e.kind, c);
            node = node.with("grmb.anchor", clause_anchor).tagged(c.id);
            if matches!(node.op, Operator::Universal(gob_ir::Universal::Hole { .. })) {
                // Holes take no children; hoist their comments to the entity.
                unit.children.extend(self.attachments(Some(c.id)));
            } else {
                node.children.extend(self.attachments(Some(c.id)));
            }
            match place {
                Place::Sig => unit.children.push(node.sig()),
                Place::Body => body.push(node),
                Place::Attr => direct.push(node),
            }
        }
        if !body.is_empty() {
            unit.children.push(unordered(e.span, body));
        }
        unit.children.extend(direct);
        unit.children.extend(self.attachments(Some(e.id)));
        unit
    }

    fn header_nodes(&self, e: &Entity, unit: &mut T) {
        match &e.header {
            Header::Node { trust: Some(t) } => {
                unit.children.push(
                    attr("trust", t.span, vec![reference(&t.text, t.span)]).sig(),
                );
            }
            Header::Flow { from, to } => {
                unit.children.push(
                    apply(
                        "connect",
                        from.span.to(to.span),
                        vec![reference(&from.written(), from.span), reference(&to.written(), to.span)],
                    )
                    .sig(),
                );
            }
            Header::Boundary {
                direction,
                flow,
                from,
                to,
                when,
            } => {
                let mut kids = vec![
                    reference(&flow.written(), flow.span),
                    reference(&from.text, from.span),
                    reference(&to.text, to.span),
                ];
                if let Some(w) = when {
                    kids.push(lit("string", &w.value, w.span));
                }
                let kind = match direction {
                    Direction::Endorse => "endorse",
                    Direction::Declassify => "declassify",
                };
                unit.children.push(apply(kind, e.span, kids).sig());
            }
            Header::Node { trust: None } | Header::None => {}
        }
    }

    fn clause(&self, entity: EntityKind, c: &Clause) -> (T, Place) {
        let sp = c.span;
        let sel_attr = |name: &str, s: &Sel, place: Place| (attr(name, sp, vec![select_t(s)]), place);
        match &c.kind {
            ClauseKind::Alias(i) => (attr("alias", sp, vec![lit("ident", &i.text, i.span)]), Place::Body),
            ClauseKind::RenamedFrom(i) => (
                attr("renamed_from", sp, vec![lit("ident", &i.text, i.span)]),
                Place::Body,
            ),
            ClauseKind::Attr { key, value } => {
                let payload = match value {
                    None => unordered(sp, vec![]),
                    Some(v) => match &v.value {
                        Value::List(items) => group(
                            GroupOrder::Sequence,
                            v.span,
                            items.iter().map(|x| lit(value_kind(x), &lit_lexeme(x), v.span)).collect(),
                        ),
                        x => lit(value_kind(x), &lit_lexeme(x), v.span),
                    },
                };
                (attr(&format!("attr:{}", key.text), sp, vec![payload]), Place::Attr)
            }
            ClauseKind::Exception(e) => (exception_t(e, sp), Place::Attr),
            ClauseKind::Kind(i) => {
                let n = attr("kind", sp, vec![lit("ident", &i.text, i.span)]);
                if entity == EntityKind::Vmodel {
                    (n, Place::Sig)
                } else {
                    (n, Place::Body)
                }
            }
            ClauseKind::Clearance(i) => (attr("clearance", sp, vec![reference(&i.text, i.span)]), Place::Body),
            ClauseKind::Owns(s) => sel_attr("owns", s, Place::Body),
            ClauseKind::Surface(s) => sel_attr("surface", s, Place::Body),
            ClauseKind::May(m) => {
                let mut kids = vec![
                    reference(&m.atom.written(), m.atom.span),
                    unordered(
                        sp,
                        m.args.iter().map(|a| lit("string", &a.value, a.span)).collect(),
                    ),
                ];
                if let Some(at) = &m.at {
                    kids.push(select_t(at));
                }
                (attr("may", sp, vec![apply("grant", sp, kids)]), Place::Body)
            }
            ClauseKind::Excuses(x) => {
                let mut kids = vec![reference(&x.atom.written(), x.atom.span)];
                kids.extend(x.attrs.iter().map(kv_attr));
                (attr("excuses", sp, kids), Place::Body)
            }
            ClauseKind::Label(i) => (
                attr("label", sp, vec![reference(&i.text, i.span)]),
                Place::Sig,
            ),
            ClauseKind::Quantity(k, q) => (
                attr(k.keyword(), sp, vec![lit("quantity", &quantity_text(q), q.span)]),
                Place::Body,
            ),
            ClauseKind::Fanout(n) => (attr("fanout", sp, vec![lit("number", &n.value, n.span)]), Place::Body),
            ClauseKind::Growth(q) => (
                attr("growth", sp, vec![lit("quantity", &quantity_text(q), q.span)]),
                Place::Body,
            ),
            ClauseKind::Transport(atoms) => (
                attr(
                    "transport",
                    sp,
                    vec![unordered(
                        sp,
                        atoms.iter().map(|a| reference(&a.written(), a.span)).collect(),
                    )],
                ),
                Place::Body,
            ),
            ClauseKind::Condition(i) => (attr("condition", sp, vec![lit("ident", &i.text, i.span)]), Place::Body),
            ClauseKind::Producer(s) => sel_attr("producer", s, Place::Sig),
            ClauseKind::Consumer(s) => sel_attr("consumer", s, Place::Sig),
            ClauseKind::Contract(r) => (
                attr("contract", sp, vec![reference(&r.written(), r.span)]),
                Place::Sig,
            ),
            ClauseKind::Shape(s) => sel_attr("shape", s, Place::Sig),
            ClauseKind::Versioning(v) => (
                attr("versioning", sp, vec![unordered(sp, v.attrs.iter().map(kv_attr).collect())]),
                Place::Sig,
            ),
            ClauseKind::What(w) => (what_t(w, sp), Place::Body),
            ClauseKind::Proof(i) => (attr("proof", sp, vec![lit("ident", &i.text, i.span)]), Place::Body),
            ClauseKind::Assumed(kvs) => (
                attr("assumed", sp, vec![unordered(sp, kvs.iter().map(kv_attr).collect())]),
                Place::Body,
            ),
            ClauseKind::Evidence(Evidence::Tests(s)) => sel_attr("evidence", s, Place::Body),
            ClauseKind::Evidence(Evidence::Ref(s)) => (
                attr("evidence", sp, vec![reference(&s.value, s.span)]),
                Place::Body,
            ),
            ClauseKind::Level(i) => (
                attr("level", sp, vec![lit("ident", canonical_level(&i.text), i.span)]),
                Place::Sig,
            ),
            ClauseKind::Ref(s) => {
                let payload = if entity == EntityKind::Pack {
                    lit("string", &s.value, s.span)
                } else {
                    reference(&s.value, s.span)
                };
                (attr("ref", sp, vec![payload]), Place::Body)
            }
            ClauseKind::Runnable(s) => sel_attr("runnable", s, Place::Body),
            ClauseKind::Link(l) => {
                let mut kids = vec![reference(&l.target.written(), l.target.span)];
                if let Some(b) = &l.because {
                    kids.push(attr("because", b.span, vec![lit("string", &b.value, b.span)]));
                }
                (apply(l.kind.keyword(), sp, kids), Place::Body)
            }
            ClauseKind::Version(s) => (attr("version", sp, vec![lit("string", &s.value, s.span)]), Place::Body),
            ClauseKind::Digest(s) => (attr("digest", sp, vec![lit("string", &s.value, s.span)]), Place::Body),
            ClauseKind::Hole(_) => (T::new(Operator::hole("parse-error"), sp, vec![]), Place::Body),
        }
    }
}

fn what_t(w: &ClaimWhat, sp: Span) -> T {
    match w {
        ClaimWhat::Noflow(a, b) => apply(
            "noflow",
            sp,
            vec![reference(&a.written(), a.span), reference(&b.written(), b.span)],
        ),
        ClaimWhat::Reach(a, b) => apply(
            "reach",
            sp,
            vec![reference(&a.written(), a.span), reference(&b.written(), b.span)],
        ),
        ClaimWhat::Bound {
            metric,
            target,
            limit,
        } => apply(
            "bound",
            sp,
            vec![
                lit("ident", &metric.text, metric.span),
                reference(&target.written(), target.span),
                lit("quantity", &quantity_text(limit), limit.span),
            ],
        ),
    }
}

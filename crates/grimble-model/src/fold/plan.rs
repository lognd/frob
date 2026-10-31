//! The U encoding of planning items (grmb-planning 8.2), folded into the same owned tree.

// frob:ticket 01M4FDBAAEX7HMVM8H6VKN98M6

#![allow(clippy::too_many_lines, clippy::many_single_char_names)]

use std::collections::BTreeMap;

use gob_ir::{GroupOrder, Operator};

use super::{Folder, Place, T, apply, attr, group, lit, reference, select_t, unordered};
use crate::ast::{EntityKind, RefPath};
use crate::plan::{
    Arm, Chain, Elem, Hop, ImplTarget, PClause, PClauseKind, Pattern, PlanItem, ScMember, Tail,
};
use crate::span::Span;
use crate::text::clause_key;

/// Anchor key of a planning clause (grmb-planning 8.1).
fn pclause_key(k: &PClauseKind) -> &'static str {
    match k {
        PClauseKind::Title(_) => "title",
        PClauseKind::Verified(_) => "verified_by",
        PClauseKind::Common(c) => clause_key(&c.kind),
        PClauseKind::Node(_) => "node",
        PClauseKind::Entry => "entry",
        PClauseKind::From(_) => "from",
        PClauseKind::Realization(_) => "realization",
        PClauseKind::RequiresPage(_) => "requires_page",
        PClauseKind::InNode(_) => "in_node",
        PClauseKind::Hole(_) => "hole",
    }
}

/// The element as a term: a step reference or an `invoke` of a scenario.
fn elem_t(e: &Elem) -> T {
    match e {
        Elem::Step(p) => reference(&p.written(), p.span),
        Elem::Include(p) => apply("invoke", p.span, vec![reference(&p.written(), p.span)]),
    }
}

/// The arm pattern as a term (`lit(ident)`, `ref . lit(ident)` or `lit(wildcard)`).
fn pattern_t(p: &Pattern) -> T {
    match p {
        Pattern::Wild(s) => lit("wildcard", "_", *s),
        Pattern::Path(path) => match path.segments.split_last() {
            Some((last, rest)) if !rest.is_empty() => group(
                GroupOrder::Sequence,
                path.span,
                vec![
                    reference(&rest.join("."), path.span),
                    lit("ident", last, path.span),
                ],
            ),
            _ => lit("ident", &path.dotted(), path.span),
        },
    }
}

/// A chain as one right-nested `seq`/`try` expression ending in its tail.
fn chain_t(c: &Chain) -> T {
    let mut acc = tail_t(&c.tail);
    for (elem, hop) in c.links.iter().rev() {
        let kind = match hop {
            Hop::Seq => "seq",
            Hop::Try => "try",
        };
        let sp = elem.path().span.to(c.span);
        acc = apply(kind, sp, vec![elem_t(elem), acc]);
    }
    acc
}

fn tail_t(t: &Tail) -> T {
    match t {
        Tail::Match { elem, arms } => apply(
            "match",
            elem.path().span,
            vec![
                elem_t(elem),
                unordered(elem.path().span, arms.iter().map(arm_t).collect()),
            ],
        ),
        Tail::Open(e) => elem_t(e),
        Tail::EndOk(s) => apply("end", *s, vec![lit("ident", "ok", *s)]),
        Tail::EndErr(v) => apply(
            "end",
            v.span,
            vec![apply("err", v.span, vec![lit("ident", &v.text, v.span)])],
        ),
        Tail::Retry {
            step,
            max,
            otherwise,
            span,
        } => {
            let mut kids = vec![reference(&step.written(), step.span)];
            if let Some(m) = max {
                kids.push(lit("number", &m.value, m.span));
            }
            if let Some(o) = otherwise {
                kids.push(chain_t(o));
            }
            apply("retry", *span, kids)
        }
    }
}

fn arm_t(a: &Arm) -> T {
    apply(
        "arm",
        a.span,
        vec![pattern_t(&a.pattern), chain_t(&a.chain)],
    )
    .tagged(a.id)
}

fn dotted_ref(p: &RefPath) -> T {
    reference(&p.written(), p.span)
}

impl Folder<'_> {
    /// Folds one planning item into `out`, recursing into a system interior.
    pub(super) fn plan_item(
        &mut self,
        p: &PlanItem,
        ns: &[String],
        out: &mut Vec<T>,
        extra: &mut Vec<T>,
    ) {
        match p {
            PlanItem::System(s) => {
                let mut inner_ns = ns.to_vec();
                inner_ns.push(s.name.text.clone());
                let mut inner = Vec::new();
                self.items(&s.items, &inner_ns, &mut inner, extra);
                let full = self.full_name(ns, &s.name.text);
                let anchor = format!("system/{full}");
                let mut u =
                    self.plan_unit("system", "declaration", &s.name.text, &anchor, s.id, s.span);
                let (sig, body, direct) = self.pclauses(&anchor, &s.clauses);
                inner.extend(body);
                u.children.extend(sig);
                if !inner.is_empty() {
                    u.children.push(unordered(s.span, inner));
                }
                u.children.extend(direct);
                u.children.extend(self.attachments(Some(s.id)));
                out.push(u);
            }
            PlanItem::Actor(a) => {
                let full = self.full_name(ns, &a.name.text);
                let anchor = format!("actor/{full}");
                let mut u =
                    self.plan_unit("actor", "declaration", &a.name.text, &anchor, a.id, a.span);
                u.children.push(
                    attr(
                        "kind",
                        a.kind.span,
                        vec![reference(&a.kind.text, a.kind.span)],
                    )
                    .sig(),
                );
                self.finish_unit(&mut u, &anchor, &a.clauses, a.id, a.span);
                out.push(u);
            }
            PlanItem::Goal(g) => {
                let full = self.full_name(ns, &g.path.dotted());
                let anchor = format!("goal/{full}");
                let mut u =
                    self.plan_unit("goal", "extension", &g.path.dotted(), &anchor, g.id, g.span);
                if let Some(k) = &g.key {
                    u.children
                        .push(attr("dimension", k.span, vec![lit("ident", &k.text, k.span)]).sig());
                }
                let mut variants = Vec::new();
                for v in &g.variants {
                    let vfull = format!("{full}.{}", v.name.text);
                    let vanchor = format!("goal/{vfull}");
                    let mut vu =
                        self.plan_unit("goal", "declaration", &v.name.text, &vanchor, v.id, v.span);
                    let mut body: Vec<T> = v
                        .requires
                        .iter()
                        .map(|r| apply("requires", r.span, vec![dotted_ref(r)]))
                        .collect();
                    let (sig, cbody, direct) = self.pclauses(&vanchor, &v.clauses);
                    vu.children.extend(sig);
                    body.extend(cbody);
                    if !body.is_empty() {
                        vu.children.push(unordered(v.span, body));
                    }
                    vu.children.extend(direct);
                    vu.children.extend(self.attachments(Some(v.id)));
                    variants.push(vu);
                }
                if !variants.is_empty() {
                    u.children.push(unordered(g.span, variants));
                }
                u.children.extend(self.attachments(Some(g.id)));
                out.push(u);
            }
            PlanItem::Step(s) => {
                let full = self.full_name(ns, &s.target.dotted());
                let anchor = format!("step/{full}");
                let mut u = self.plan_unit(
                    "step",
                    "declaration",
                    &s.target.dotted(),
                    &anchor,
                    s.id,
                    s.span,
                );
                let owner = if s.is_system() {
                    lit("ident", "system", s.target.span)
                } else {
                    dotted_ref(&s.owner())
                };
                u.children
                    .push(attr("owner", s.target.span, vec![owner]).sig());
                if let Some(outs) = &s.outcome {
                    let vs = outs
                        .iter()
                        .map(|o| {
                            let mut kids = vec![lit("ident", &o.name.text, o.name.span)];
                            if let Some(p) = &o.payload {
                                kids.push(dotted_ref(p));
                            }
                            apply("variant", o.name.span, kids)
                        })
                        .collect();
                    u.children
                        .push(attr("outcome", s.span, vec![unordered(s.span, vs)]).sig());
                }
                self.finish_unit(&mut u, &anchor, &s.clauses, s.id, s.span);
                out.push(u);
            }
            PlanItem::Scenario(s) => {
                let full = self.full_name(ns, &s.name.text);
                let anchor = format!("scenario/{full}");
                let mut u = self.plan_unit(
                    "scenario",
                    "declaration",
                    &s.name.text,
                    &anchor,
                    s.id,
                    s.span,
                );
                if !s.realizes.is_empty() {
                    u.children.push(
                        apply(
                            "realizes",
                            s.span,
                            s.realizes.iter().map(dotted_ref).collect(),
                        )
                        .sig(),
                    );
                }
                if let Some(f) = &s.fails {
                    let vs = f.iter().map(|v| lit("ident", &v.text, v.span)).collect();
                    u.children
                        .push(attr("fails", s.span, vec![unordered(s.span, vs)]).sig());
                }
                let mut body = Vec::new();
                let mut n_chain = 0usize;
                let mut direct = Vec::new();
                let mut clauses: Vec<PClause> = Vec::new();
                for m in &s.members {
                    match m {
                        ScMember::Chain(id, c) => {
                            let a = if n_chain == 0 {
                                format!("{anchor}/chain")
                            } else {
                                format!("{anchor}/chain[{n_chain}]")
                            };
                            n_chain += 1;
                            self.anchors.insert(*id, a.clone());
                            self.chain_arm_anchors(c, &a);
                            let mut n = attr(
                                "chain",
                                c.span,
                                vec![group(GroupOrder::Sequence, c.span, vec![chain_t(c)])],
                            )
                            .with("grmb.anchor", a)
                            .tagged(*id);
                            n.children.extend(self.attachments(Some(*id)));
                            body.push(n);
                        }
                        ScMember::Handle(h) => {
                            let a = format!("{anchor}/handle");
                            self.anchors.insert(h.id, a.clone());
                            for arm in &h.arms {
                                self.anchors.insert(
                                    arm.id,
                                    format!("{anchor}/handle[{}]", arm.pattern.written()),
                                );
                                self.chain_arm_anchors(&arm.chain, &anchor);
                            }
                            let mut n = attr(
                                "handle",
                                h.span,
                                vec![unordered(h.span, h.arms.iter().map(arm_t).collect())],
                            )
                            .with("grmb.anchor", a)
                            .tagged(h.id);
                            n.children.extend(self.attachments(Some(h.id)));
                            body.push(n);
                        }
                        ScMember::Clause(c) => clauses.push(c.clone()),
                    }
                }
                let (sig, cbody, cdirect) = self.pclauses(&anchor, &clauses);
                u.children.extend(sig);
                body.extend(cbody);
                direct.extend(cdirect);
                if !body.is_empty() {
                    u.children.push(unordered(s.span, body));
                }
                u.children.extend(direct);
                u.children.extend(self.attachments(Some(s.id)));
                out.push(u);
            }
            PlanItem::Impl(i) => {
                let tname = match &i.target {
                    ImplTarget::Scenario(p) => p.dotted(),
                    ImplTarget::Any(_) => "_".to_owned(),
                };
                // grmb-planning 4.6: `S.SCENARIO.OWNER.STEP`, and `S._.OWNER.STEP` for `for *`.
                let uname = format!("{tname}.{}", i.step.dotted());
                let full = self.full_name(ns, &uname);
                let anchor = format!("impl/{full}");
                let mut u = self.plan_unit("impl", "declaration", &uname, &anchor, i.id, i.span);
                let target = match &i.target {
                    ImplTarget::Scenario(p) => dotted_ref(p),
                    ImplTarget::Any(s) => lit("any", "*", *s),
                };
                u.children
                    .push(apply("realize", i.span, vec![dotted_ref(&i.step), target]).sig());
                self.finish_unit(&mut u, &anchor, &i.clauses, i.id, i.span);
                out.push(u);
            }
            PlanItem::Page(pg) => {
                let full = self.full_name(ns, &pg.name.text);
                let anchor = format!("page/{full}");
                let mut u = self.plan_unit(
                    "page",
                    "declaration",
                    &pg.name.text,
                    &anchor,
                    pg.id,
                    pg.span,
                );
                self.finish_unit(&mut u, &anchor, &pg.clauses, pg.id, pg.span);
                out.push(u);
            }
        }
    }

    /// Registers the anchors of the arms nested in `c` as `arm[OWNER.STEP.VARIANT]`.
    fn chain_arm_anchors(&mut self, c: &Chain, scenario_anchor: &str) {
        let scenario_anchor = scenario_anchor
            .split("/chain")
            .next()
            .unwrap_or(scenario_anchor)
            .to_owned();
        if let Tail::Match { elem, arms } = &c.tail {
            for arm in arms {
                let owner = elem.path().dotted();
                let tail = match &arm.pattern {
                    Pattern::Wild(_) => "_".to_owned(),
                    Pattern::Path(p) if p.segments.len() > 1 => p.dotted(),
                    Pattern::Path(p) => format!("{owner}.{}", p.dotted()),
                };
                self.anchors
                    .insert(arm.id, format!("{scenario_anchor}/arm[{tail}]"));
                self.chain_arm_anchors(&arm.chain, &scenario_anchor);
            }
        }
        if let Tail::Retry {
            otherwise: Some(o), ..
        } = &c.tail
        {
            self.chain_arm_anchors(o, &scenario_anchor);
        }
    }

    fn plan_unit(
        &mut self,
        kind: &str,
        role: &str,
        name: &str,
        anchor: &str,
        id: usize,
        span: Span,
    ) -> T {
        self.anchors.insert(id, anchor.to_owned());
        T::new(Operator::unit(kind, role), span, vec![])
            .named(name)
            .with("grmb.anchor", anchor.to_owned())
            .tagged(id)
    }

    /// Adds the clauses and attachments of `id` to a unit whose sig is already set.
    fn finish_unit(&mut self, u: &mut T, anchor: &str, clauses: &[PClause], id: usize, span: Span) {
        let (sig, body, direct) = self.pclauses(anchor, clauses);
        u.children.extend(sig);
        if !body.is_empty() {
            u.children.push(unordered(span, body));
        }
        u.children.extend(direct);
        u.children.extend(self.attachments(Some(id)));
    }

    /// Folds planning clauses into (sig, body, direct) node lists.
    fn pclauses(&mut self, anchor: &str, clauses: &[PClause]) -> (Vec<T>, Vec<T>, Vec<T>) {
        let (mut sig, mut body, mut direct) = (Vec::new(), Vec::new(), Vec::new());
        let mut counters: BTreeMap<&'static str, usize> = BTreeMap::new();
        for c in clauses {
            let key = pclause_key(&c.kind);
            let n = counters.entry(key).or_insert(0);
            let ca = format!("{anchor}/{key}[{n}]");
            *n += 1;
            self.anchors.insert(c.id, ca.clone());
            let sp = c.span;
            let (nodes, place): (Vec<T>, Place) = match &c.kind {
                PClauseKind::Title(t) => (
                    vec![attr("title", sp, vec![lit("string", &t.value, t.span)])],
                    Place::Attr,
                ),
                PClauseKind::Verified(v) => {
                    let mut kids = vec![select_t(&v.sel)];
                    if let Some(p) = &v.pair {
                        let (last, rest) = p.segments.split_last().expect("non-empty path");
                        kids.push(apply(
                            "arm_ref",
                            p.span,
                            vec![
                                reference(&rest.join("."), p.span),
                                lit("ident", last, p.span),
                            ],
                        ));
                    }
                    (vec![attr("verified_by", sp, kids)], Place::Body)
                }
                PClauseKind::Common(cl) => {
                    let (t, place) = Self::clause(EntityKind::Node, cl);
                    (vec![t], place)
                }
                PClauseKind::Node(p) => (vec![attr("node", sp, vec![dotted_ref(p)])], Place::Body),
                PClauseKind::Entry => (vec![attr("entry", sp, vec![])], Place::Body),
                PClauseKind::From(ps) => (
                    ps.iter()
                        .map(|p| apply("from", p.span, vec![dotted_ref(p)]))
                        .collect(),
                    Place::Body,
                ),
                PClauseKind::Realization(r) => {
                    let mut kids = vec![reference(&r.kind.text, r.kind.span)];
                    if let Some(n) = &r.name {
                        kids.push(lit("ident", &n.text, n.span));
                    }
                    kids.push(select_t(&r.sel));
                    (
                        vec![attr("realization", sp, vec![unordered(sp, kids)])],
                        Place::Body,
                    )
                }
                PClauseKind::RequiresPage(p) => (
                    vec![attr("requires_page", sp, vec![dotted_ref(p)])],
                    Place::Body,
                ),
                PClauseKind::InNode(p) => {
                    (vec![attr("in_node", sp, vec![dotted_ref(p)])], Place::Body)
                }
                PClauseKind::Hole(_) => (
                    vec![T::new(Operator::hole("parse-error"), sp, vec![])],
                    Place::Body,
                ),
            };
            let mut first = true;
            for mut node in nodes {
                if first {
                    node = node.with("grmb.anchor", ca.clone()).tagged(c.id);
                    if matches!(node.op, Operator::Universal(gob_ir::Universal::Hole { .. })) {
                        // Holes take no children: their comments hang off the file.
                    } else {
                        node.children.extend(self.attachments(Some(c.id)));
                    }
                    first = false;
                }
                match place {
                    Place::Sig => sig.push(node.sig()),
                    Place::Body => body.push(node),
                    Place::Attr => direct.push(node),
                }
            }
        }
        (sig, body, direct)
    }
}

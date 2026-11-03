//! Printing of planning items (grmb-spec 9.6).

// frob:ticket 01M4FDBAAEX7HMVM8H6VKN98M6

use std::fmt::Write as _;

use super::Printer;
use crate::ast::Item;
use crate::plan::{
    Arm, Chain, Debt, Elem, ImplTarget, Outcome, PClause, PClauseKind, PlanItem, Policy,
    Realization, ScMember, Tail,
};
use crate::text::{clause_text, quantity_text, quote, selector_text};

/// The `item_rank` tuple of a planning item: after templates (3,6), kinds in `PLAN_HEADS` order.
pub(super) fn rank(p: &PlanItem) -> (u8, u8, String, bool, String) {
    let k = crate::plan::PLAN_HEADS
        .iter()
        .position(|h| *h == p.keyword())
        .unwrap_or(0);
    let name = match p {
        PlanItem::System(x) => x.name.text.clone(),
        PlanItem::Actor(x) => x.name.text.clone(),
        PlanItem::Goal(x) => x.path.written(),
        PlanItem::Step(x) => x.target.written(),
        PlanItem::Scenario(x) => x.name.text.clone(),
        PlanItem::Impl(x) => x.step.written(),
        PlanItem::Page(x) => x.name.text.clone(),
    };
    let tie = match p {
        PlanItem::Impl(x) => match &x.target {
            ImplTarget::Scenario(r) => r.written(),
            ImplTarget::Any(_) => "*".to_owned(),
        },
        PlanItem::Goal(x) => x.key.as_ref().map(|i| i.text.clone()).unwrap_or_default(),
        _ => String::new(),
    };
    (3, 7 + u8::try_from(k).unwrap_or(0), name, false, tie)
}

fn outcome_text(o: &[Outcome]) -> String {
    let parts: Vec<String> = o
        .iter()
        .map(|v| match &v.payload {
            Some(p) => format!("{}({})", v.name.written(), p.written()),
            None => v.name.written(),
        })
        .collect();
    format!("{{ {} }}", parts.join(", "))
}

/// The text of one planning clause, without its `;`.
pub fn pclause_text(c: &PClause) -> String {
    match &c.kind {
        PClauseKind::Title(s) => format!("title {}", quote(&s.value)),
        PClauseKind::Verified(v) => {
            let mut t = format!("verified_by {}", selector_text(&v.sel));
            if let Some(p) = &v.pair {
                write!(t, " for {}", p.written()).ok();
            }
            t
        }
        PClauseKind::Common(c) => clause_text(&c.kind),
        PClauseKind::Node(r) | PClauseKind::InNode(r) => format!("in node {}", r.written()),
        PClauseKind::Entry => "entry".to_owned(),
        PClauseKind::From(rs) => {
            let parts: Vec<String> = rs.iter().map(crate::ast::RefPath::written).collect();
            format!("from {}", parts.join(", "))
        }
        PClauseKind::Realization(r) => realization_text(r),
        // frob:ticket 01M6CFZKEKAJM0YF9FB5820W3Y
        PClauseKind::Ambient(a) => format!("ambient {}", policy_text(&a.policy)),
        PClauseKind::NonGoal(n) => format!("non_goal {}", n.written()),
        PClauseKind::Chain(_) => "chain".to_owned(),
        PClauseKind::Sorry(d) => debt_text(d),
        PClauseKind::RequiresPage(r) => format!("on page {}", r.written()),
        PClauseKind::Hole(_) => unreachable!("a file with a hole is never printed"),
    }
}

/// `KIND [NAME] = SELECTOR`, shared by realization clauses and chain waypoints.
fn realization_text(r: &Realization) -> String {
    let mut t = r.kind.text.clone();
    if let Some(n) = &r.name {
        write!(t, " {}", n.text).ok();
    }
    write!(t, " = {}", selector_text(&r.sel)).ok();
    t
}

/// The printed ambient policy: `action [max N] [within Q] [else POLICY]`.
fn policy_text(p: &Policy) -> String {
    let mut t = p.action.text.clone();
    if let Some(m) = &p.max {
        write!(t, " max {}", m.value).ok();
    }
    if let Some(w) = &p.within {
        write!(t, " within {}", quantity_text(w)).ok();
    }
    if let Some(o) = &p.otherwise {
        write!(t, " else {}", policy_text(o)).ok();
    }
    t
}

/// A debt value is bare only when it is a date, otherwise quoted.
fn debt_value_text(v: &str) -> String {
    let date = v.len() == 10
        && v.char_indices().all(|(i, c)| match i {
            4 | 7 => c == '-',
            _ => c.is_ascii_digit(),
        });
    if date { v.to_owned() } else { quote(v) }
}

/// The printed `sorry` hole with its `key = value` pairs in written order.
fn debt_text(d: &Debt) -> String {
    let mut t = "sorry".to_owned();
    for k in &d.keys {
        write!(
            t,
            " {} = {}",
            k.key.written(),
            debt_value_text(&k.value.value)
        )
        .ok();
    }
    t
}

fn clause_rank(k: &PClauseKind) -> u8 {
    match k {
        PClauseKind::Title(_) => 0,
        PClauseKind::Node(_) | PClauseKind::Entry | PClauseKind::From(_) => 1,
        PClauseKind::RequiresPage(_) | PClauseKind::InNode(_) => 2,
        PClauseKind::Verified(_) => 4,
        PClauseKind::Realization(_)
        | PClauseKind::Ambient(_)
        | PClauseKind::NonGoal(_)
        | PClauseKind::Chain(_)
        | PClauseKind::Sorry(_) => 3,
        PClauseKind::Common(_) | PClauseKind::Hole(_) => 5,
    }
}

fn elem_text(e: &Elem) -> String {
    match e {
        Elem::Step(p) => p.written(),
        Elem::Include(p) => format!("include {}", p.written()),
    }
}

/// The lines of a chain's inline tail (`end ...` or `retry ...`) as one string.
fn terminal_text(t: &Tail, out: &mut String, indent: usize) {
    match t {
        Tail::Open(e) => out.push_str(&elem_text(e)),
        Tail::Sorry(d) => out.push_str(&debt_text(d)),
        Tail::EndOk(_) => out.push_str("end ok"),
        Tail::EndErr(v) => {
            write!(out, "end err({})", v.written()).ok();
        }
        Tail::Retry {
            step,
            step_written,
            max,
            within,
            otherwise,
            ..
        } => {
            out.push_str("retry");
            if *step_written {
                write!(out, " {}", step.written()).ok();
            }
            if let Some(m) = max {
                write!(out, " max {}", m.value).ok();
            }
            if let Some(w) = within {
                write!(out, " within {}", quantity_text(w)).ok();
            }
            if let Some(c) = otherwise {
                out.push_str(" else ");
                chain_text(c, out, indent);
            }
        }
        Tail::Match { elem, arms } => {
            writeln!(out, "{} => {{", elem_text(elem)).ok();
            arms_text(arms, out, indent + 2);
            out.push_str(&" ".repeat(indent));
            out.push('}');
        }
    }
}

/// A chain as text: links one per line with the link token leading, continuation two spaces in.
fn chain_text(c: &Chain, out: &mut String, indent: usize) {
    let base = if c.links.is_empty() {
        indent
    } else {
        indent + 2
    };
    let pad = " ".repeat(base);
    let mut pending: Option<&str> = None;
    for (e, hop) in &c.links {
        if let Some(h) = pending {
            write!(out, "\n{pad} {h} ").ok();
        }
        out.push_str(&elem_text(e));
        pending = Some(hop.text());
    }
    if let Some(h) = pending {
        write!(out, "\n{pad} {h} ").ok();
    }
    terminal_text(&c.tail, out, base);
}

/// The printed pattern of an arm.
fn pattern_key(a: &Arm) -> (bool, String) {
    (
        matches!(a.pattern, crate::plan::Pattern::Wild(_)),
        a.pattern.written(),
    )
}

/// Arms sorted by printed pattern with `_` last, arrows aligned; each arm ends in `;` unless a brace.
fn arms_text(arms: &[Arm], out: &mut String, indent: usize) {
    let mut sorted: Vec<&Arm> = arms.iter().collect();
    sorted.sort_by_key(|a| pattern_key(a));
    let width = sorted
        .iter()
        .map(|a| a.pattern.written().chars().count())
        .max()
        .unwrap_or(0);
    let pad = " ".repeat(indent);
    for a in sorted {
        let pat = a.pattern.written();
        let fill = " ".repeat(width - pat.chars().count());
        let mut body = String::new();
        chain_text(&a.chain, &mut body, indent);
        write!(out, "{pad}{pat}{fill} {} {body}", a.arrow.text()).ok();
        if !a.chain.ends_with_brace() {
            out.push(';');
        }
        out.push('\n');
    }
}

impl Printer<'_> {
    /// Prints a chain statement at `indent`.
    fn chain_stmt(&mut self, c: &Chain, id: usize, indent: usize) {
        self.comments(self.f.attachments.of(id), indent);
        let mut text = String::new();
        chain_text(c, &mut text, indent);
        if !c.ends_with_brace() {
            text.push(';');
        }
        let pad = " ".repeat(indent);
        self.out.push_str(&pad);
        self.out.push_str(&text);
        self.out.push('\n');
    }

    fn pclauses(&mut self, clauses: &[PClause], indent: usize) {
        let mut sorted: Vec<(u8, String, &PClause)> = clauses
            .iter()
            .map(|c| (clause_rank(&c.kind), pclause_text(c), c))
            .collect();
        sorted.sort_by(|a, b| (a.0, &a.1).cmp(&(b.0, &b.1)));
        for (_, text, c) in sorted {
            self.comments(self.f.attachments.of(c.id), indent);
            match &c.kind {
                PClauseKind::Chain(ws) => self.chain_block(ws, indent),
                PClauseKind::Ambient(a) if a.braced => {
                    self.head_body(c.id, &text, true, &a.clauses, indent);
                }
                _ => self.line(indent, &format!("{text};")),
            }
        }
    }

    /// Prints an impl `chain { ... }` block of waypoints (no trailing `;`).
    fn chain_block(&mut self, ws: &[crate::plan::Waypoint], indent: usize) {
        self.line(indent, "chain {");
        for w in ws {
            self.comments(self.f.attachments.of(w.id), indent + 2);
            let head = realization_text(&w.real);
            if !w.braced {
                self.line(indent + 2, &format!("{head};"));
                continue;
            }
            self.line(indent + 2, &format!("{head} {{"));
            for m in &w.maps {
                let srcs: Vec<&str> = m.sources.iter().map(|s| s.value.as_str()).collect();
                self.line(
                    indent + 4,
                    &format!("{} => {};", srcs.join(", "), m.target.written()),
                );
            }
            self.pclauses(&w.clauses, indent + 4);
            self.line(indent + 2, "}");
        }
        self.line(indent, "}");
    }

    /// Prints a head plus either `;` or a braced clause body.
    fn head_body(
        &mut self,
        id: usize,
        head: &str,
        braced: bool,
        clauses: &[PClause],
        indent: usize,
    ) {
        self.comments(self.f.attachments.of(id), indent);
        if braced && !clauses.is_empty() {
            self.line(indent, &format!("{head} {{"));
            self.pclauses(clauses, indent + 2);
            self.line(indent, "}");
        } else if braced {
            self.line(indent, &format!("{head} {{ }}"));
        } else {
            self.line(indent, &format!("{head};"));
        }
    }

    /// Prints one goal variant with its `requires` list.
    fn variant(&mut self, v: &crate::plan::Variant, indent: usize) {
        let mut vh = v.name.written();
        if !v.requires.is_empty() {
            let mut rs: Vec<String> = v
                .requires
                .iter()
                .map(crate::ast::RefPath::written)
                .collect();
            rs.sort();
            write!(vh, " requires {}", rs.join(", ")).ok();
        }
        self.head_body(v.id, &vh, v.braced, &v.clauses, indent);
    }

    fn goal_item(&mut self, g: &crate::plan::GoalBlock, indent: usize) {
        self.comments(self.f.attachments.of(g.id), indent);
        self.line(indent, &format!("goal {} {{", g.path.written()));
        if let Some(k) = &g.key {
            // the spec spelling; `goal P as K` is a bridged (MDL012) form (grmb-spec 11.1)
            self.line(indent + 2, &format!("attr dimension = {};", k.written()));
        }
        let mut vs: Vec<&crate::plan::Variant> = g.variants.iter().collect();
        vs.sort_by(|a, b| a.name.text.cmp(&b.name.text));
        for v in vs {
            self.variant(v, indent + 2);
        }
        for o in &g.groups {
            self.comments(self.f.attachments.of(o.id), indent + 2);
            let head = if o.exclusive {
                "one_of exclusive {"
            } else {
                "one_of {"
            };
            self.line(indent + 2, head);
            let mut vs: Vec<&crate::plan::Variant> = o.variants.iter().collect();
            vs.sort_by(|a, b| a.name.text.cmp(&b.name.text));
            for v in vs {
                self.variant(v, indent + 4);
            }
            self.line(indent + 2, "}");
        }
        self.line(indent, "}");
    }

    fn scenario_item(&mut self, s: &crate::plan::Scenario, indent: usize) {
        self.comments(self.f.attachments.of(s.id), indent);
        let mut head = format!("scenario {}", s.name.written());
        if !s.realizes.is_empty() {
            let rs: Vec<String> = s
                .realizes
                .iter()
                .map(crate::ast::RefPath::written)
                .collect();
            write!(head, " realizes {}", rs.join(", ")).ok();
        }
        if let Some(f) = &s.fails {
            let names: Vec<String> = f.iter().map(crate::ast::Ident::written).collect();
            write!(head, " fails with {{ {} }}", names.join(", ")).ok();
        }
        if let [ScMember::Chain(id, c)] = s.members.as_slice()
            && c.links.is_empty()
            && matches!(c.tail, Tail::Sorry(_))
        {
            // a lone `sorry` is the whole-body form (grmb-spec 15.3)
            self.comments(self.f.attachments.of(*id), indent);
            let mut t = String::new();
            chain_text(c, &mut t, indent);
            self.line(indent, &format!("{head} {t};"));
            return;
        }
        self.line(indent, &format!("{head} {{"));
        // Chains and handles keep their order; clauses print after them, sorted.
        for m in &s.members {
            match m {
                ScMember::Chain(id, c) => self.chain_stmt(c, *id, indent + 2),
                ScMember::Handle(h) => {
                    self.comments(self.f.attachments.of(h.id), indent + 2);
                    let mut body = String::new();
                    arms_text(&h.arms, &mut body, indent + 4);
                    self.out.push_str(&" ".repeat(indent + 2));
                    self.out.push_str("handle {\n");
                    self.out.push_str(&body);
                    self.out.push_str(&" ".repeat(indent + 2));
                    self.out.push_str("}\n");
                }
                ScMember::Clause(_) => {}
            }
        }
        let cl: Vec<PClause> = s
            .members
            .iter()
            .filter_map(|m| match m {
                ScMember::Clause(c) => Some(c.clone()),
                _ => None,
            })
            .collect();
        self.pclauses(&cl, indent + 2);
        self.line(indent, "}");
    }

    /// Prints one planning item at `indent`.
    pub(super) fn plan_item(&mut self, p: &PlanItem, indent: usize) {
        match p {
            PlanItem::System(s) => {
                self.comments(self.f.attachments.of(s.id), indent);
                if !s.braced {
                    self.line(indent, &format!("system {};", s.name.written()));
                    return;
                }
                self.line(indent, &format!("system {} {{", s.name.written()));
                self.pclauses(&s.clauses, indent + 2);
                if !s.clauses.is_empty() && !s.items.is_empty() {
                    self.out.push('\n');
                }
                let inner: Vec<&Item> = s.items.iter().collect();
                self.items(&inner, indent + 2, false);
                self.line(indent, "}");
            }
            PlanItem::Actor(a) => {
                let head = format!("actor {} : {}", a.name.written(), a.kind.written());
                self.head_body(a.id, &head, a.braced, &a.clauses, indent);
            }
            PlanItem::Goal(g) => self.goal_item(g, indent),
            PlanItem::Step(s) => {
                let mut head = format!("step {}", s.target.written());
                if let Some(o) = &s.outcome {
                    write!(
                        head,
                        " : {}{}",
                        if s.open { "open " } else { "" },
                        outcome_text(o)
                    )
                    .ok();
                }
                if s.idempotent {
                    head.push_str(" idempotent");
                }
                self.head_body(s.id, &head, s.braced, &s.clauses, indent);
            }
            PlanItem::Scenario(s) => self.scenario_item(s, indent),
            PlanItem::Impl(i) => {
                let target = match &i.target {
                    ImplTarget::Scenario(r) => r.written(),
                    ImplTarget::Any(_) => "*".to_owned(),
                };
                let head = format!("impl {} for {}", i.step.written(), target);
                if let [
                    PClause {
                        kind: PClauseKind::Sorry(d),
                        ..
                    },
                ] = i.clauses.as_slice()
                {
                    self.comments(self.f.attachments.of(i.id), indent);
                    self.line(indent, &format!("{head} {};", debt_text(d)));
                    return;
                }
                self.head_body(i.id, &head, true, &i.clauses, indent);
            }
            PlanItem::Page(g) => {
                let head = format!("page {}", g.name.written());
                if let [
                    PClause {
                        kind: PClauseKind::Sorry(d),
                        ..
                    },
                ] = g.clauses.as_slice()
                {
                    self.comments(self.f.attachments.of(g.id), indent);
                    self.line(indent, &format!("{head} {};", debt_text(d)));
                    return;
                }
                self.head_body(g.id, &head, g.braced, &g.clauses, indent);
            }
        }
    }
}

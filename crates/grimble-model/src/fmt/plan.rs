//! Printing of planning items (grmb-planning 8.3).

// frob:ticket 01M4FDBAAEX7HMVM8H6VKN98M6

use std::fmt::Write as _;

use super::Printer;
use crate::ast::Item;
use crate::plan::{
    Arm, Chain, Elem, ImplTarget, Outcome, PClause, PClauseKind, PlanItem, ScMember, Tail,
};
use crate::text::{clause_text, quote, selector_text};

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
            Some(p) => format!("{}({})", v.name.text, p.written()),
            None => v.name.text.clone(),
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
                let _ = write!(t, " for {}", p.written());
            }
            t
        }
        PClauseKind::Common(c) => clause_text(&c.kind),
        PClauseKind::Node(r) => format!("node {}", r.written()),
        PClauseKind::Entry => "entry".to_owned(),
        PClauseKind::From(rs) => {
            let parts: Vec<String> = rs.iter().map(crate::ast::RefPath::written).collect();
            format!("from {}", parts.join(", "))
        }
        PClauseKind::Realization(r) => {
            let mut t = r.kind.text.clone();
            if let Some(n) = &r.name {
                let _ = write!(t, " {}", n.text);
            }
            let _ = write!(t, " = {}", selector_text(&r.sel));
            t
        }
        PClauseKind::RequiresPage(r) => format!("requires page {}", r.written()),
        PClauseKind::InNode(r) => format!("in node {}", r.written()),
        PClauseKind::Hole(_) => unreachable!("a file with a hole is never printed"),
    }
}

fn clause_rank(k: &PClauseKind) -> u8 {
    match k {
        PClauseKind::Title(_) => 0,
        PClauseKind::Node(_) | PClauseKind::Entry | PClauseKind::From(_) => 1,
        PClauseKind::RequiresPage(_) | PClauseKind::InNode(_) => 2,
        PClauseKind::Realization(_) => 3,
        PClauseKind::Verified(_) => 4,
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
        Tail::EndOk(_) => out.push_str("end ok"),
        Tail::EndErr(v) => {
            let _ = write!(out, "end err({})", v.text);
        }
        Tail::Retry {
            step,
            max,
            otherwise,
            ..
        } => {
            let _ = write!(out, "retry {}", step.written());
            if let Some(m) = max {
                let _ = write!(out, " max {}", m.value);
            }
            if let Some(c) = otherwise {
                out.push_str(" else ");
                chain_text(c, out, indent);
            }
        }
        Tail::Match { elem, arms } => {
            let _ = writeln!(out, "{} => {{", elem_text(elem));
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
            let _ = write!(out, "\n{pad}{h} ");
        }
        out.push_str(&elem_text(e));
        pending = Some(hop.text());
    }
    if let Some(h) = pending {
        let _ = write!(out, "\n{pad}{h} ");
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
        let _ = write!(out, "{pad}{pat}{fill} -> {body}");
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
            self.line(indent, &format!("{text};"));
        }
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

    fn goal_item(&mut self, g: &crate::plan::GoalBlock, indent: usize) {
        self.comments(self.f.attachments.of(g.id), indent);
        let mut head = format!("goal {}", g.path.written());
        if let Some(k) = &g.key {
            let _ = write!(head, " as {}", k.text);
        }
        self.line(indent, &format!("{head} {{"));
        let mut vs: Vec<&crate::plan::Variant> = g.variants.iter().collect();
        vs.sort_by(|a, b| a.name.text.cmp(&b.name.text));
        for v in vs {
            let mut vh = v.name.text.clone();
            if !v.requires.is_empty() {
                let mut rs: Vec<String> = v
                    .requires
                    .iter()
                    .map(crate::ast::RefPath::written)
                    .collect();
                rs.sort();
                let _ = write!(vh, " requires {}", rs.join(", "));
            }
            self.head_body(v.id, &vh, v.braced, &v.clauses, indent + 2);
        }
        self.line(indent, "}");
    }

    fn scenario_item(&mut self, s: &crate::plan::Scenario, indent: usize) {
        self.comments(self.f.attachments.of(s.id), indent);
        let mut head = format!("scenario {}", s.name.text);
        if !s.realizes.is_empty() {
            let rs: Vec<String> = s
                .realizes
                .iter()
                .map(crate::ast::RefPath::written)
                .collect();
            let _ = write!(head, " realizes {}", rs.join(", "));
        }
        if let Some(f) = &s.fails {
            let names: Vec<&str> = f.iter().map(|i| i.text.as_str()).collect();
            let _ = write!(head, " fails with {{ {} }}", names.join(", "));
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
                    self.line(indent, &format!("system {};", s.name.text));
                    return;
                }
                self.line(indent, &format!("system {} {{", s.name.text));
                self.pclauses(&s.clauses, indent + 2);
                if !s.clauses.is_empty() && !s.items.is_empty() {
                    self.out.push('\n');
                }
                let inner: Vec<&Item> = s.items.iter().collect();
                self.items(&inner, indent + 2, false);
                self.line(indent, "}");
            }
            PlanItem::Actor(a) => {
                let head = format!("actor {} : {}", a.name.text, a.kind.text);
                self.head_body(a.id, &head, a.braced, &a.clauses, indent);
            }
            PlanItem::Goal(g) => self.goal_item(g, indent),
            PlanItem::Step(s) => {
                let mut head = format!("step {}", s.target.written());
                if let Some(o) = &s.outcome {
                    let _ = write!(head, " -> {}", outcome_text(o));
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
                self.head_body(i.id, &head, true, &i.clauses, indent);
            }
            PlanItem::Page(g) => {
                let head = format!("page {}", g.name.text);
                self.head_body(g.id, &head, g.braced, &g.clauses, indent);
            }
        }
    }
}

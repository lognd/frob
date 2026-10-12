//! Snippet checks that need no parser: GRL006 and GRL008 (grl-spec.md sections 7.3 and 10).
//!
//! GRL006: a snippet that is not lifted with `as roles` inside a `lang *` rule. GRL008: a
//! metavariable written in a `fix ... -> SNIPPET` that no matching snippet of the rule binds.
//! GRL002 and GRL007 need the snippet parsed in its language and live with the grammar engine.

// frob:ticket 01M3ZX7E5VPTH8J16D5APQDEAP
use std::collections::BTreeSet;

use gob_text::Span;

use super::{Code, Diagnostic};
use crate::grl::ast::{
    Binding, CastKind, ClauseKind, Cond, CondKind, FixKind, HeaderKind, LangSet, Object, Rel,
    RelKind, Rule, Shape, ShapeKind, Source, Term, TermKind,
};
use crate::grl::{MetaKind, MetaVar, Snippet};

/// A snippet that matches code: where it is, and whether `as roles` lifts it.
struct Matcher<'r> {
    snippet: &'r Snippet,
    span: Span,
    roles: bool,
}

/// Every snippet of one rule, split into those that match and those that rewrite.
#[derive(Default)]
struct Collected<'r> {
    matchers: Vec<Matcher<'r>>,
    rewrites: Vec<&'r Snippet>,
}

/// Check one rule's snippets; diagnostics are in discovery order (the caller sorts by span).
pub(super) fn check_rule(rule: &Rule) -> Vec<Diagnostic> {
    let mut c = Collected::default();
    for cl in &rule.clauses {
        c.clause(&cl.node);
    }
    let mut out = Vec::new();
    let universal = rule.headers.iter().find_map(|h| match &h.node {
        HeaderKind::Lang(LangSet::Any { .. }) => Some(h.span),
        _ => None,
    });
    if let Some(lang_span) = universal {
        for m in c.matchers.iter().filter(|m| !m.roles) {
            out.push(universal_snippet(m, lang_span));
        }
    }
    unbound(&c, &mut out);
    out
}

fn universal_snippet(m: &Matcher<'_>, lang_span: Span) -> Diagnostic {
    let tag = m.snippet.lang.as_ref().map_or("rust", |l| l.name.as_str());
    let label = match &m.snippet.lang {
        None => "this snippet has no language".to_owned(),
        Some(l) => format!("this snippet is {} code, not universal", l.name),
    };
    Diagnostic::new(
        Code::Grl006,
        "a plain snippet cannot be used in a rule for every language",
        m.span,
        label,
    )
    .with_secondary(lang_span, "every language")
    .with_help(format!(
        "use a role (`find c: call`), tag the snippet and add `as roles` ({tag}`{}` as roles), or narrow the rule with `lang {tag}`",
        m.snippet.text
    ))
}

fn name_of(mv: &MetaVar) -> Option<String> {
    let dollars = if mv.kind == MetaKind::Seq { "$$$" } else { "$" };
    mv.name.as_ref().map(|n| format!("{dollars}{n}"))
}

/// GRL008 for every named metavariable of a fix snippet that no matcher binds.
fn unbound(c: &Collected<'_>, out: &mut Vec<Diagnostic>) {
    let bound: Vec<(&str, &MetaVar)> = c
        .matchers
        .iter()
        .flat_map(|m| &m.snippet.metavars)
        .filter_map(|mv| mv.name.as_deref().map(|n| (n, mv)))
        .collect();
    let names: BTreeSet<&str> = bound.iter().map(|(n, _)| *n).collect();
    for mv in c.rewrites.iter().flat_map(|s| &s.metavars) {
        let (Some(shown), Some(name)) = (name_of(mv), mv.name.as_deref()) else {
            continue;
        };
        if names.contains(name) {
            continue;
        }
        let mut d = Diagnostic::new(
            Code::Grl008,
            format!("`{shown}` is used in the fix but no snippet binds it"),
            mv.span,
            "not bound by any snippet in this rule",
        );
        if names.len() == 1 {
            let (only, first) = bound[0];
            d = d
                .with_secondary(first.span, "the only metavariable bound")
                .with_help(format!("did you mean `${only}`?"));
        } else if let Some(near) = names
            .iter()
            .min_by_key(|n| distance(n, name))
            .filter(|n| distance(n, name) <= 2)
        {
            d = d.with_help(format!("did you mean `${near}`?"));
        }
        out.push(d);
    }
}

/// Edit distance between two metavariable names.
fn distance(a: &str, b: &str) -> usize {
    let b: Vec<char> = b.chars().collect();
    let mut row: Vec<usize> = (0..=b.len()).collect();
    for (i, ca) in a.chars().enumerate() {
        let mut prev = row[0];
        row[0] = i + 1;
        for (j, cb) in b.iter().enumerate() {
            let cur = row[j + 1];
            row[j + 1] = (prev + usize::from(ca != *cb)).min(row[j] + 1).min(cur + 1);
            prev = cur;
        }
    }
    row[b.len()]
}

impl<'r> Collected<'r> {
    fn clause(&mut self, c: &'r ClauseKind) {
        match c {
            ClauseKind::Find(b) | ClauseKind::Quant { binding: b, .. } => self.binding(b),
            ClauseKind::Where(cond) => self.cond(cond),
            ClauseKind::Def(d) => self.cond(&d.body),
            ClauseKind::Report(r) => r.when.iter().for_each(|w| self.cond(w)),
            ClauseKind::Unresolved(u) => self.cond(&u.when),
            ClauseKind::Fix(f) => {
                if let FixKind::Replace { with, .. } = &f.kind {
                    self.rewrites.push(with);
                }
            }
            ClauseKind::Note(_) => {}
        }
    }

    fn binding(&mut self, b: &'r Binding) {
        if let Source::Shape(s) = &b.source {
            self.shape(s);
        }
        for r in &b.rels {
            self.rel(r);
        }
        if let Some(f) = &b.filter {
            self.cond(f);
        }
    }

    fn shape(&mut self, s: &'r Shape) {
        match &s.node {
            ShapeKind::Snippet { snippet, cast } => self.matchers.push(Matcher {
                snippet,
                span: s.span,
                roles: cast.as_ref().is_some_and(|c| c.node == CastKind::Roles),
            }),
            ShapeKind::Alt(alts) => alts.iter().for_each(|a| self.shape(a)),
            ShapeKind::Kind { .. } => {}
        }
    }

    fn object(&mut self, o: &'r Object) {
        match o {
            Object::Term(t) => self.term(t),
            Object::Shape(s) => self.shape(s),
        }
    }

    fn rel(&mut self, r: &'r Rel) {
        match &r.node {
            RelKind::Containment { object, .. }
            | RelKind::InUnit { object }
            | RelKind::Position { object, .. }
            | RelKind::Verb { object, .. } => self.object(object),
            RelKind::Under { term } => self.term(term),
            RelKind::Reaches { target, within, .. } => {
                self.object(target);
                if let Some(t) = within {
                    self.term(t);
                }
            }
        }
    }

    fn term(&mut self, t: &'r Term) {
        match &t.node {
            TermKind::Count(b) => self.binding(b),
            TermKind::Call(c) => c.args.iter().for_each(|a| self.term(a)),
            TermKind::Binary { lhs, rhs, .. } | TermKind::Range { lo: lhs, hi: rhs } => {
                self.term(lhs);
                self.term(rhs);
            }
            TermKind::Path(_) | TermKind::Literal(_) | TermKind::Knob(_) => {}
        }
    }

    fn cond(&mut self, c: &'r Cond) {
        match &c.node {
            CondKind::Or(cs) | CondKind::And(cs) | CondKind::Any(cs) => {
                for c in cs {
                    self.cond(c);
                }
            }
            CondKind::Not(c) => self.cond(c),
            CondKind::Quant { binding, .. } => self.binding(binding),
            CondKind::Rel { subject, rel } => {
                self.term(subject);
                self.rel(rel);
            }
            CondKind::Cmp { lhs, rhs, .. }
            | CondKind::RegexMatch { lhs, rhs }
            | CondKind::GlobMatch { lhs, rhs }
            | CondKind::In { lhs, rhs } => {
                self.term(lhs);
                self.term(rhs);
            }
            CondKind::IsSnippet {
                subject,
                snippet,
                roles,
            } => {
                self.term(subject);
                self.matchers.push(Matcher {
                    snippet,
                    span: c.span,
                    roles: *roles,
                });
            }
            CondKind::Is { subject, .. } | CondKind::HasAttr { subject, .. } => self.term(subject),
            CondKind::DefCall(call) => call.args.iter().for_each(|a| self.term(a)),
            CondKind::Exists(t) | CondKind::Flag(t) => self.term(t),
        }
    }
}

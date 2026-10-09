//! Boundedness and completeness checks for one rule (GRL009, GRL010, GRL011, GRL012, GRL014;
//! grl-spec.md sections 7.4, 9 and 10).
//!
//! These checks look at the shape of the rule rather than at names and types: whether a `def`
//! calls itself or a later `def`, whether a closure is bounded, whether the rule carries the
//! examples and the `## Remedy` section the spec requires, and whether a side relation it reads is
//! declared in `needs`.

// frob:ticket 01M3ZX7E2DPA2CXBAQ8ZKM5W7Y
use std::collections::{BTreeMap, BTreeSet};

use gob_caps::Lang;
use gob_text::{Span, TextRange, TextSize};

use super::{Code, Diagnostic, vocab};
use crate::catalog;
use crate::grl::ast::{
    Binding, Call, ClauseKind, Cond, CondKind, ExpectKind, FixKind, HeaderKind, LangSet, Object,
    Path, Rel, RelKind, Rule, Source, Term, TermKind, TypeKind,
};

/// Check one rule's structure; diagnostics are in discovery order (the caller sorts by span).
pub(super) fn check_rule(rule: &Rule) -> Vec<Diagnostic> {
    let mut out = Vec::new();
    let mut w = Walker::new(rule);
    w.rule(rule);
    defs(rule, &w, &mut out);
    closures(rule, &w, &mut out);
    examples(rule, &mut out);
    remedy(rule, &mut out);
    needs(rule, &w, &mut out);
    tracing::debug!(rule = %rule.id.text, diagnostics = out.len(), "checked rule structure");
    out
}

/// What one pass over the rule's conditions and terms collects.
struct Walker<'r> {
    /// Def names to the position of their first definition.
    def_index: BTreeMap<&'r str, usize>,
    /// The def whose body is being walked.
    current: Option<usize>,
    /// Calls of defs: the def they sit in (if any) and the call.
    calls: Vec<(Option<usize>, &'r Call)>,
    /// Closures without `within`.
    unbounded: Vec<&'r Rel>,
    /// Paths that start at a side-relation root, outside `config`.
    sides: Vec<&'r Path>,
    /// Every name a rule binds, so a variable called `diff` is not mistaken for the root.
    bound: BTreeSet<&'r str>,
}

impl<'r> Walker<'r> {
    fn new(rule: &'r Rule) -> Self {
        let mut def_index = BTreeMap::new();
        for (i, d) in rule
            .clauses
            .iter()
            .filter_map(|c| match &c.node {
                ClauseKind::Def(d) => Some(d),
                _ => None,
            })
            .enumerate()
        {
            def_index.entry(d.name.text.as_str()).or_insert(i);
        }
        Self {
            def_index,
            current: None,
            calls: Vec::new(),
            unbounded: Vec::new(),
            sides: Vec::new(),
            bound: BTreeSet::new(),
        }
    }

    fn rule(&mut self, rule: &'r Rule) {
        let mut next_def = 0;
        for cl in &rule.clauses {
            match &cl.node {
                ClauseKind::Find(b) | ClauseKind::Quant { binding: b, .. } => self.binding(b),
                ClauseKind::Where(c) => self.cond(c),
                ClauseKind::Def(d) => {
                    self.bound.extend(d.params.iter().map(|p| p.text.as_str()));
                    self.current = Some(next_def);
                    next_def += 1;
                    self.cond(&d.body);
                    self.current = None;
                }
                ClauseKind::Report(r) => {
                    if let Some(c) = &r.when {
                        self.cond(c);
                    }
                }
                ClauseKind::Unresolved(u) => self.cond(&u.when),
                ClauseKind::Fix(f) => {
                    if let FixKind::Host { args, .. } = &f.kind {
                        for a in args {
                            self.term(a);
                        }
                    }
                }
                ClauseKind::Note(_) => {}
            }
        }
    }

    fn binding(&mut self, b: &'r Binding) {
        self.bound.insert(b.name.text.as_str());
        if let Source::Side(p) = &b.source {
            self.side_path(p);
        }
        for r in &b.rels {
            self.rel(r);
        }
        if let Some(f) = &b.filter {
            self.cond(f);
        }
    }

    fn cond(&mut self, c: &'r Cond) {
        match &c.node {
            CondKind::Or(cs) | CondKind::And(cs) | CondKind::Any(cs) => {
                for x in cs {
                    self.cond(x);
                }
            }
            CondKind::Not(inner) => self.cond(inner),
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
            CondKind::Is { subject, .. }
            | CondKind::IsSnippet { subject, .. }
            | CondKind::HasAttr { subject, .. } => self.term(subject),
            CondKind::DefCall(call) => self.call(call),
            CondKind::Exists(t) | CondKind::Flag(t) => self.term(t),
        }
    }

    fn call(&mut self, call: &'r Call) {
        if self.def_index.contains_key(call.name.text.as_str()) {
            self.calls.push((self.current, call));
        }
        for a in &call.args {
            self.term(a);
        }
    }

    fn term(&mut self, t: &'r Term) {
        match &t.node {
            TermKind::Path(p) => self.side_path(p),
            TermKind::Count(b) => self.binding(b),
            TermKind::Call(c) => self.call(c),
            TermKind::Binary { lhs, rhs, .. } => {
                self.term(lhs);
                self.term(rhs);
            }
            TermKind::Range { lo, hi } => {
                self.term(lo);
                self.term(hi);
            }
            TermKind::Literal(_) | TermKind::Knob(_) => {}
        }
    }

    fn object(&mut self, o: &'r Object) {
        if let Object::Term(t) = o {
            self.term(t);
        }
    }

    fn rel(&mut self, rel: &'r Rel) {
        match &rel.node {
            RelKind::Containment { object, .. }
            | RelKind::InUnit { object }
            | RelKind::Position { object, .. }
            | RelKind::Verb { object, .. } => self.object(object),
            RelKind::Under { term } => self.term(term),
            RelKind::Reaches { target, within, .. } => {
                self.object(target);
                match within {
                    Some(t) => self.term(t),
                    None => self.unbounded.push(rel),
                }
            }
        }
    }

    fn side_path(&mut self, p: &'r Path) {
        let root = p.segments[0].text.as_str();
        if p.segments.len() >= 2
            && root != "config"
            && vocab::is_side_root(root)
            && !self.bound.contains(root)
        {
            self.sides.push(p);
        }
    }
}

/// GRL009: a def that calls itself or a def written after it.
fn defs(rule: &Rule, w: &Walker<'_>, out: &mut Vec<Diagnostic>) {
    let defs: Vec<_> = rule
        .clauses
        .iter()
        .filter_map(|c| match &c.node {
            ClauseKind::Def(d) => Some(d),
            _ => None,
        })
        .collect();
    for (site, call) in &w.calls {
        let (Some(site), Some(&target)) = (site, w.def_index.get(call.name.text.as_str())) else {
            continue;
        };
        let name = &call.name.text;
        if target == *site {
            out.push(
                Diagnostic::new(
                    Code::Grl009,
                    format!("`{name}` calls itself"),
                    call.span,
                    "a def cannot recurse",
                )
                .with_help("to follow a chain of calls use `reaches ... via calls within N`, which is bounded"),
            );
        } else if target > *site {
            let later = defs[target];
            out.push(
                Diagnostic::new(
                    Code::Grl009,
                    format!("`{name}` is used before it is defined"),
                    call.name.span,
                    "used here",
                )
                .with_secondary(later.name.span, "defined here, after its use")
                .with_help(format!(
                    "a def may call only the defs written above it; move `def {name}` above `def {}`",
                    defs[*site].name.text
                )),
            );
        }
    }
}

/// GRL010: a closure with no `within`.
fn closures(rule: &Rule, w: &Walker<'_>, out: &mut Vec<Diagnostic>) {
    let int_knob = rule.headers.iter().find_map(|h| match &h.node {
        HeaderKind::Knob(k) if k.ty.node == TypeKind::Int => Some(k.name.text.as_str()),
        _ => None,
    });
    for rel in &w.unbounded {
        let help = match int_knob {
            Some(k) => format!("add `within knob.{k}` or a number such as `within 6`"),
            None => "add `within knob.depth` (after `knob depth: int = 6 \"how many call levels to follow\"`) or a number such as `within 6`".to_owned(),
        };
        out.push(
            Diagnostic::new(
                Code::Grl010,
                "`reaches` needs a bound on how far to look",
                rel.span,
                "no `within` here",
            )
            .with_help(help),
        );
    }
}

/// The `lang` the rule's examples default to, as a matrix language, if it names exactly one.
fn example_lang(rule: &Rule) -> Option<Lang> {
    rule.headers.iter().find_map(|h| match &h.node {
        HeaderKind::Lang(LangSet::One(w)) => catalog::lang_of(&w.text),
        HeaderKind::Lang(LangSet::List(ws)) => ws.first().and_then(|w| catalog::lang_of(&w.text)),
        _ => None,
    })
}

/// A short source sample per language: a function the rule should leave alone.
const fn clean_sample(lang: Lang) -> &'static str {
    match lang {
        Lang::Python => "def f(x):\n  return x",
        Lang::TypeScript => "function f(x) { return x; }",
        Lang::CSharp => "int F(int x) { return x; }",
        Lang::Rust => "fn f(x: u32) -> u32 { x }",
        _ => "<source the rule must leave alone>",
    }
}

/// The marker a `fire` example puts on the line that must be reported (`//~ warn`).
fn fire_marker(lang: Lang) -> String {
    match catalog::comment_markers(lang).first() {
        Some(&"<!--") => "<!--~ warn -->".to_owned(),
        Some(m) => format!("{m}~ warn"),
        None => "expect \"line 1: warn\"".to_owned(),
    }
}

/// The scaffold of a missing example, as a help text.
fn scaffold(kind: &str, lang: Option<Lang>) -> String {
    let lang = lang.unwrap_or(Lang::Rust);
    match kind {
        "clean" => format!(
            "add one, for example:\nexample clean \"\"\"\n  {}\n\"\"\"\ncode the rule must leave alone goes between the quotes",
            clean_sample(lang).replace('\n', "\n  ")
        ),
        "fire" => format!(
            "add one, for example:\nexample fire \"\"\"\n  {}   {}\n\"\"\"\ncode the rule must report goes between the quotes; mark the reported line with the marker",
            clean_sample(lang).lines().next().unwrap_or_default(),
            fire_marker(lang)
        ),
        _ => format!(
            "add one, for example:\nexample notapplicable {} \"\"\"\n  <source in a language that lacks the feature>\n\"\"\"\nsay the language: this rule is universal, so one example must show it does not apply",
            lang.name()
        ),
    }
}

/// GRL011: no `fire`, no `clean`, or (universal rules) no `notapplicable` or `unresolved` example.
fn examples(rule: &Rule, out: &mut Vec<Diagnostic>) {
    let has = |k: ExpectKind| rule.examples.iter().any(|e| e.expect.kind == k);
    let universal = rule
        .headers
        .iter()
        .all(|h| !matches!(h.node, HeaderKind::Lang(_)))
        || rule
            .headers
            .iter()
            .any(|h| matches!(h.node, HeaderKind::Lang(LangSet::Any { .. })));
    let mut missing: Vec<(&str, &str)> = Vec::new();
    if !has(ExpectKind::Fire) {
        missing.push(("fire", "every rule needs a `fire` and a `clean` example"));
    }
    if !has(ExpectKind::Clean) {
        missing.push(("clean", "every rule needs a `fire` and a `clean` example"));
    }
    if universal && !has(ExpectKind::NotApplicable) && !has(ExpectKind::Unresolved) {
        missing.push((
            "notapplicable",
            "a universal rule also needs a `notapplicable` or `unresolved` example",
        ));
    }
    let head = Span::new(
        rule.id.span.file,
        TextRange::new(rule.span.range.start(), rule.slug.span.range.end()),
    );
    for (kind, label) in missing {
        let what = if kind == "notapplicable" {
            "`notapplicable` or `unresolved`".to_owned()
        } else {
            format!("`{kind}`")
        };
        let mut d = Diagnostic::new(
            Code::Grl011,
            format!("rule `{}` has no {what} example", rule.id.text),
            head,
            label,
        )
        .with_help(scaffold(kind, example_lang(rule)));
        if let [only] = rule.examples.as_slice() {
            let span = Span::new(
                only.span.file,
                TextRange::new(only.span.range.start(), only.expect.span.range.end()),
            );
            d = d.with_secondary(span, "the only example");
        }
        out.push(d);
    }
}

/// GRL012: an `explain` text with no `## Remedy` heading.
fn remedy(rule: &Rule, out: &mut Vec<Diagnostic>) {
    let Some(ex) = &rule.explain else { return };
    if ex.text.value.lines().any(|l| l.trim_end() == "## Remedy") {
        return;
    }
    let kw = Span::new(
        ex.span.file,
        TextRange::at(ex.span.range.start(), TextSize::new(7)),
    );
    out.push(
        Diagnostic::new(
            Code::Grl012,
            format!(
                "the `explain` text of `{}` has no `## Remedy` section",
                rule.id.text
            ),
            kw,
            "add a `## Remedy` heading to this text",
        )
        .with_help("end the text with a section saying how to fix a finding:\n## Remedy\nDelete the call, or log through `tracing` if the value matters."),
    );
}

/// GRL014: a side relation read without its root in `needs`.
fn needs(rule: &Rule, w: &Walker<'_>, out: &mut Vec<Diagnostic>) {
    let declared: BTreeSet<&str> = rule
        .headers
        .iter()
        .filter_map(|h| match &h.node {
            HeaderKind::Needs(ws) => Some(ws),
            _ => None,
        })
        .flatten()
        .map(|w| w.text.as_str())
        .collect();
    let needs_header = rule
        .headers
        .iter()
        .find(|h| matches!(h.node, HeaderKind::Needs(_)));
    let mut seen = BTreeSet::new();
    for p in &w.sides {
        let root = p.segments[0].text.as_str();
        if declared.contains(root) {
            continue;
        }
        let name = format!("{root}.{}", p.segments[1].text);
        if !seen.insert(name.clone()) {
            continue;
        }
        let span = Span::new(
            p.span.file,
            TextRange::new(p.span.range.start(), p.segments[1].span.range.end()),
        );
        let mut d = Diagnostic::new(
            Code::Grl014,
            format!("`{name}` is used but `{root}` is not in `needs`"),
            span,
            format!("reads the `{root}` relation"),
        )
        .with_help(format!(
            "add `needs {root}` to the header; the rule re-runs when the {root} changes"
        ));
        match needs_header {
            Some(h) => d = d.with_secondary(h.span, format!("`needs` does not list `{root}`")),
            None => {
                if let Some(h) = rule.headers.last() {
                    d = d.with_secondary(h.span, "no `needs` line in the header");
                }
            }
        }
        out.push(d);
    }
}

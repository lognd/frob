//! Name resolution, binding rules and type checks for one rule (GRL001, GRL003, GRL004, GRL005,
//! GRL013, GRL017, GRL018; grl-spec.md sections 7.1 and 10).
//!
//! The checker walks a [`Rule`] once. Rule-level `find` variables are declared first (clause
//! order does not matter), then clauses are checked with a stack of visible variables; the
//! head of `some`, `no` and `count` is visible only inside its own binding, and a `def` sees
//! only its parameters.

use std::collections::{BTreeSet, HashSet};
use std::rc::Rc;

use gob_text::Span;

use super::vocab::{self, Ty};
use super::{Code, Diagnostic};
use crate::catalog::{Answers, Column, ConfigSchema};
use crate::grl::ast::{
    ArithOp, Binding, Call, CastKind, ClauseKind, CmpOp, Cond, CondKind, Def, FixKind, HeaderKind,
    LangSet, Literal, LiteralKind, Message, MessagePart, Object, Path, Quant, Rel, RelKind, Rule,
    Shape, ShapeKind, Source, Spanned, Term, TermKind, Word,
};

/// The catalog line every unknown-word diagnostic ends with.
/// The rule-authoring command the catalog help names. It is a constant, not a literal in the
/// message, because the `rule catalog` verb lands with ~QMW7215 and the remedy-lint
/// (`crates/frob/tests/remedies.rs`) rejects a message that names a command the CLI lacks.
const AUTHORING_CLI: &str = "grimble";

/// The help line every unknown-word diagnostic ends with.
fn catalog_help() -> String {
    format!("`{AUTHORING_CLI} rule catalog` lists every kind, field and relation")
}

/// The innermost construct that uses variables without binding them.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum NegVia {
    Not,
    No,
    Unresolved,
}

impl NegVia {
    const fn word(self) -> &'static str {
        match self {
            Self::Not => "not",
            Self::No => "no",
            Self::Unresolved => "unresolved when",
        }
    }
}

/// What a variable ranges over, as far as fields are concerned.
#[derive(Debug, Clone)]
enum VarTy {
    Kind(&'static str),
    Side(Option<Rc<Vec<Column>>>),
    Any,
}

#[derive(Debug, Clone)]
struct Var {
    id: usize,
    name: String,
    span: Span,
    ty: VarTy,
}

/// Where an unbound name stood, which decides the wording of GRL001.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum NamePos {
    /// A variable is required.
    Var,
    /// The object of a relation: a variable or a kind.
    KindOrVar,
}

/// The languages of a rule header.
enum LangMode {
    /// `lang *` or no header: decided per language at run time, nothing to check here.
    Universal,
    /// `lang -` or an explicit list.
    Listed(Vec<String>),
}

/// Check one rule.
pub(super) fn check_rule(rule: &Rule, config: Option<&ConfigSchema>) -> Vec<Diagnostic> {
    let mut c = Checker::new(rule, config);
    c.run(rule);
    tracing::debug!(rule = %rule.id.text, diagnostics = c.out.len(), "checked rule names");
    c.out
}

// frob:ticket 01M4E0BVMZHYZYC7PHEA0YWS08
struct Checker<'a> {
    config: Option<&'a ConfigSchema>,
    out: Vec<Diagnostic>,
    vars: Vec<Var>,
    used: Vec<bool>,
    witnesses: Vec<Var>,
    messages: bool,
    knobs: Vec<(String, Ty)>,
    defs: Vec<(String, usize)>,
    def_asts: Vec<Def>,
    carrying: Vec<String>,
    carried: HashSet<Span>,
    langs: LangMode,
    lang_span: Option<Span>,
    neg: Option<NegVia>,
    parity: bool,
    in_def: bool,
    seen_kind_use: BTreeSet<String>,
    seen_grl003: BTreeSet<String>,
    finds: Vec<Var>,
}

impl<'a> Checker<'a> {
    // frob:ticket 01M4E0BVMZHYZYC7PHEA0YWS08
    fn new(rule: &Rule, config: Option<&'a ConfigSchema>) -> Self {
        let mut knobs = Vec::new();
        let mut langs = LangMode::Universal;
        let mut lang_span = None;
        for h in &rule.headers {
            match &h.node {
                HeaderKind::Knob(k) => {
                    knobs.push((k.name.text.clone(), vocab::knob_ty(&k.ty.node)));
                }
                HeaderKind::Lang(set) => {
                    lang_span = Some(h.span);
                    langs = match set {
                        LangSet::Any { .. } => LangMode::Universal,
                        LangSet::Nothing => LangMode::Listed(Vec::new()),
                        LangSet::One(w) => LangMode::Listed(vec![w.text.clone()]),
                        LangSet::List(ws) => {
                            LangMode::Listed(ws.iter().map(|w| w.text.clone()).collect())
                        }
                    };
                }
                _ => {}
            }
        }
        Self {
            config,
            out: Vec::new(),
            vars: Vec::new(),
            used: Vec::new(),
            witnesses: Vec::new(),
            messages: false,
            knobs,
            defs: Vec::new(),
            def_asts: Vec::new(),
            carrying: Vec::new(),
            carried: HashSet::new(),
            langs,
            lang_span,
            neg: None,
            parity: false,
            in_def: false,
            seen_kind_use: BTreeSet::new(),
            seen_grl003: BTreeSet::new(),
            finds: Vec::new(),
        }
    }

    // frob:ticket 01M4E0BVMZHYZYC7PHEA0YWS08
    fn run(&mut self, rule: &Rule) {
        for cl in &rule.clauses {
            match &cl.node {
                ClauseKind::Find(b) => {
                    if let Some(v) = self.declare(b, "find") {
                        self.finds.push(v);
                    }
                }
                ClauseKind::Def(d) => {
                    self.defs.push((d.name.text.clone(), d.params.len()));
                    self.def_asts.push(d.clone());
                }
                _ => {}
            }
        }
        for cl in &rule.clauses {
            match &cl.node {
                ClauseKind::Find(b) => self.binding_body(b),
                ClauseKind::Where(c) => self.cond(c),
                ClauseKind::Quant { quant, binding } => self.quant(*quant, binding),
                ClauseKind::Def(d) => self.def(d),
                _ => {}
            }
        }
        self.messages = true;
        let mut reports_left = rule
            .clauses
            .iter()
            .filter(|c| matches!(c.node, ClauseKind::Report(_)))
            .count();
        for cl in &rule.clauses {
            match &cl.node {
                ClauseKind::Report(r) => {
                    reports_left -= 1;
                    self.var_ref(&r.target);
                    self.message(&r.message);
                    if let Some(w) = &r.when {
                        // A later `report` is chosen only when this `when` is not Yes, so every
                        // `when` that has a later report behind it sits in a negative position.
                        self.flipped(reports_left > 0, |s| s.cond(w));
                    }
                }
                ClauseKind::Note(n) => {
                    self.var_ref(&n.target);
                    self.message(&n.message);
                }
                ClauseKind::Fix(f) => match &f.kind {
                    FixKind::Replace { target, .. } | FixKind::Delete { target } => {
                        self.var_ref(target);
                    }
                    FixKind::Host { args, .. } => {
                        for a in args {
                            self.term(a);
                        }
                    }
                    FixKind::Manual { message } => self.message(message),
                },
                ClauseKind::Unresolved(u) => {
                    self.negated(NegVia::Unresolved, false, |s| s.cond(&u.when));
                    self.message(&u.because);
                }
                _ => {}
            }
        }
        for v in std::mem::take(&mut self.finds) {
            if !self.used[v.id] {
                self.out.push(
                    Diagnostic::new(
                        Code::Grl013,
                        format!("`{}` is bound and never used", v.name),
                        v.span,
                        format!("`{}` is not used by any condition or message", v.name),
                    )
                    .with_help(format!(
                        "use `{0}` in a `where` or a `report`, or delete the clause",
                        v.name
                    )),
                );
            }
        }
    }

    // ---- scopes ---------------------------------------------------------------------------

    fn lookup(&self, name: &str) -> Option<Var> {
        self.vars
            .iter()
            .rev()
            .find(|v| v.name == name)
            .or_else(|| {
                if self.messages {
                    self.witnesses.iter().find(|v| v.name == name)
                } else {
                    None
                }
            })
            .cloned()
    }

    /// Bind the head of `binding`; GRL004 when the name is already visible. `None` on a clash.
    fn declare(&mut self, b: &Binding, keyword: &str) -> Option<Var> {
        if let Some(first) = self.lookup(&b.name.text) {
            let fresh = self.fresh_name(&b.name.text);
            let kind = match &b.source {
                Source::Shape(s) => match &s.node {
                    ShapeKind::Kind { kind, .. } => kind.text.clone(),
                    _ => "...".to_owned(),
                },
                Source::Side(p) => p
                    .segments
                    .iter()
                    .map(|s| s.text.as_str())
                    .collect::<Vec<_>>()
                    .join("."),
            };
            let example = if keyword == "count" {
                format!("count({fresh}: {kind} ...)")
            } else {
                format!("{keyword} {fresh}: {kind}")
            };
            let name = &b.name.text;
            self.out.push(
                Diagnostic::new(
                    Code::Grl004,
                    format!("`{name}` is bound twice"),
                    b.name.span,
                    format!("`{name}` is already bound"),
                )
                .with_secondary(first.span, "first bound here")
                .with_help(format!(
                    "rename the second one (`{example}`); to compare two things, use `==`, which never binds"
                )),
            );
            return None;
        }
        let id = self.used.len();
        self.used.push(false);
        let v = Var {
            id,
            name: b.name.text.clone(),
            span: b.name.span,
            ty: self.source_ty(&b.source),
        };
        self.vars.push(v.clone());
        Some(v)
    }

    /// A name that is not visible: the next single letter after `name`, or `name` plus a digit.
    fn fresh_name(&self, name: &str) -> String {
        let taken = |n: &str| self.vars.iter().any(|v| v.name == n);
        if let [c @ b'a'..=b'z'] = name.as_bytes() {
            for next in (*c + 1..=b'z').chain(b'a'..*c) {
                let n = char::from(next).to_string();
                if !taken(&n) {
                    return n;
                }
            }
        }
        format!("{name}2")
    }

    fn source_ty(&self, s: &Source) -> VarTy {
        match s {
            Source::Side(p) => VarTy::Side(self.row_columns(p)),
            Source::Shape(shape) => match &shape.node {
                ShapeKind::Kind { kind, .. } => {
                    vocab::kind(&kind.text).map_or(VarTy::Any, |k| VarTy::Kind(k.word))
                }
                _ => VarTy::Any,
            },
        }
    }

    fn negated(&mut self, via: NegVia, flips: bool, f: impl FnOnce(&mut Self)) {
        let saved = (self.neg, self.parity);
        self.neg = Some(via);
        self.parity ^= flips;
        f(self);
        (self.neg, self.parity) = saved;
    }

    // frob:ticket 01M4E0BVMZHYZYC7PHEA0YWS08
    /// Run `f` with the polarity flipped when `flip` is set; the `neg` marker is left alone.
    fn flipped<T>(&mut self, flip: bool, f: impl FnOnce(&mut Self) -> T) -> T {
        let saved = self.parity;
        self.parity ^= flip;
        let out = f(self);
        self.parity = saved;
        out
    }

    fn scoped(&mut self, f: impl FnOnce(&mut Self)) {
        let mark = self.vars.len();
        f(self);
        self.vars.truncate(mark);
    }

    // ---- clauses and conditions -----------------------------------------------------------

    /// Check source, relations and filter of an already declared head.
    fn binding_body(&mut self, b: &Binding) {
        self.source(&b.source);
        for r in &b.rels {
            self.rel(r, None);
        }
        if let Some(f) = &b.filter {
            self.cond(f);
        }
    }

    /// A `some`, `no` or `count` binding: the head is visible only inside it.
    fn local_binding(&mut self, keyword: &str, b: &Binding, witness: bool) {
        self.scoped(|s| {
            s.source(&b.source);
            if let Some(v) = s.declare(b, keyword)
                && witness
                && s.neg.is_none()
                && !s.in_def
            {
                s.witnesses.push(v);
            }
            for r in &b.rels {
                s.rel(r, None);
            }
            if let Some(f) = &b.filter {
                s.cond(f);
            }
        });
    }

    fn quant(&mut self, quant: Quant, b: &Binding) {
        match quant {
            Quant::Some => self.local_binding("some", b, true),
            Quant::No => self.negated(NegVia::No, true, |s| s.local_binding("no", b, false)),
        }
    }

    // frob:ticket 01M4E0BVMZHYZYC7PHEA0YWS08
    fn def(&mut self, d: &Def) {
        self.walk_def(d, false);
    }

    /// Walk a def body whose polarity starts at `parity` (true when a call sits in a negative position).
    fn walk_def(&mut self, d: &Def, parity: bool) {
        let saved_vars = std::mem::take(&mut self.vars);
        let saved = (self.neg, self.parity, self.in_def);
        (self.neg, self.parity, self.in_def) = (None, parity, true);
        for p in &d.params {
            if let Some(first) = self.vars.iter().find(|v| v.name == p.text) {
                let first_span = first.span;
                self.out.push(
                    Diagnostic::new(
                        Code::Grl004,
                        format!("`{}` is bound twice", p.text),
                        p.span,
                        format!("`{}` is already a parameter", p.text),
                    )
                    .with_secondary(first_span, "first bound here")
                    .with_help("rename one of the parameters"),
                );
                continue;
            }
            let id = self.used.len();
            self.used.push(true);
            self.vars.push(Var {
                id,
                name: p.text.clone(),
                span: p.span,
                ty: VarTy::Any,
            });
        }
        self.cond(&d.body);
        self.vars = saved_vars;
        (self.neg, self.parity, self.in_def) = saved;
    }

    fn cond(&mut self, c: &Cond) {
        match &c.node {
            CondKind::Or(cs) | CondKind::And(cs) | CondKind::Any(cs) => {
                for x in cs {
                    self.cond(x);
                }
            }
            CondKind::Not(inner) => self.negated(NegVia::Not, true, |s| s.cond(inner)),
            CondKind::Quant { quant, binding } => self.quant(*quant, binding),
            CondKind::Rel { subject, rel } => {
                self.term(subject);
                self.rel(rel, Some(subject));
            }
            CondKind::Cmp { op, lhs, rhs } => self.cmp(*op, lhs, rhs),
            CondKind::RegexMatch { lhs, rhs } => {
                let (l, r) = (self.term(lhs), self.term(rhs));
                self.matching(&l, lhs, &r, rhs, "regex");
            }
            CondKind::GlobMatch { lhs, rhs } => {
                let (l, r) = (self.term(lhs), self.term(rhs));
                self.matching(&l, lhs, &r, rhs, "glob");
            }
            CondKind::In { lhs, rhs } => {
                let (l, r) = (self.term(lhs), self.term(rhs));
                self.membership(&l, lhs, &r, rhs);
            }
            CondKind::Is { subject, test } => {
                self.term(subject);
                self.is_word(test);
            }
            CondKind::IsSnippet { subject, .. } | CondKind::HasAttr { subject, .. } => {
                self.term(subject);
            }
            CondKind::DefCall(call) => self.def_call(call),
            CondKind::Exists(t) | CondKind::Flag(t) => {
                self.term(t);
            }
        }
    }

    fn is_word(&mut self, w: &Word) {
        if vocab::kind(&w.text).is_some() {
            self.kind_use(w);
            return;
        }
        if vocab::is_flag(&w.text) {
            return;
        }
        let kinds = vocab::kinds();
        let cands = kinds.iter().map(|k| k.word).chain(vocab::flag_names());
        self.unknown(
            w,
            "unknown kind or flag",
            "not a kind, field or relation",
            vocab::suggest(&w.text, cands),
            None,
        );
    }

    // frob:ticket 01M4E0BVMZHYZYC7PHEA0YWS08
    fn def_call(&mut self, call: &Call) {
        for a in &call.args {
            self.term(a);
        }
        if self.defs.iter().any(|d| d.0 == call.name.text) {
            if self.parity {
                self.carry_negation(&call.name.text);
            }
            return;
        }
        let names: Vec<&str> = self.defs.iter().map(|d| d.0.as_str()).collect();
        let s = vocab::suggest(&call.name.text, names.iter().copied()).map(str::to_owned);
        self.unknown(
            &call.name,
            "unknown predicate",
            "not a `def` of this rule",
            s.as_deref(),
            Some("define it with `def NAME(params) = ...` before using it"),
        );
    }

    // frob:ticket 01M4E0BVMZHYZYC7PHEA0YWS08
    /// A def called in a negative position: its `certainly` and `possibly` at even depth inside the
    /// body are negative here. The body is walked again with the call's polarity and only the
    /// GRL017 findings are kept, so no other diagnostic or checker state is duplicated.
    fn carry_negation(&mut self, name: &str) {
        let Some(def) = self.def_asts.iter().find(|d| d.name.text == name).cloned() else {
            return;
        };
        if self.carrying.iter().any(|n| n == name) {
            return;
        }
        let saved_out = std::mem::take(&mut self.out);
        let saved_sets = (self.seen_kind_use.clone(), self.seen_grl003.clone());
        let (used, witnesses, finds) = (self.used.len(), self.witnesses.len(), self.finds.len());
        let nested = !self.carrying.is_empty();
        self.carrying.push(name.to_owned());
        self.walk_def(&def, true);
        self.carrying.pop();
        let walked = std::mem::replace(&mut self.out, saved_out);
        (self.seen_kind_use, self.seen_grl003) = saved_sets;
        self.used.truncate(used);
        self.witnesses.truncate(witnesses);
        self.finds.truncate(finds);
        for d in walked {
            // Only the outermost walk dedupes; a nested one hands its findings up unfiltered.
            if d.code == Some(Code::Grl017) && (nested || self.carried.insert(d.primary.span)) {
                self.out.push(d);
            }
        }
    }

    // ---- relations ------------------------------------------------------------------------

    fn rel(&mut self, rel: &Rel, _subject: Option<&Term>) {
        match &rel.node {
            RelKind::Containment { object, .. }
            | RelKind::InUnit { object }
            | RelKind::Position { object, .. } => self.object(object),
            RelKind::Under { term } => {
                self.term(term);
            }
            RelKind::Verb {
                certainty,
                verb,
                object,
            } => {
                self.verb(verb);
                if certainty.is_some() && self.parity {
                    self.out.push(
                        Diagnostic::new(
                            Code::Grl017,
                            "`certainly` and `possibly` cannot be used under `not` or `no`",
                            rel.span,
                            "this sits in a negative position",
                        )
                        .with_note("`certainly` turns an unknown edge into No and `possibly` into Yes, so under a negation the rule would fire on a guess")
                        .with_help("move it out of the negation, or drop the word: the rule's polarity already decides whether Must or May edges count"),
                    );
                }
                self.object(object);
            }
            RelKind::Reaches {
                target,
                via,
                within,
            } => {
                self.object(target);
                for v in via {
                    self.verb(v);
                }
                if let Some(t) = within {
                    let ty = self.term(t);
                    if ty.is_concrete() && ty != Ty::Int {
                        self.out.push(
                            Diagnostic::new(
                                Code::Grl005,
                                format!("mismatched types: `within` takes a whole number, not {}", ty.phrase()),
                                t.span,
                                "expected an integer here",
                            )
                            .with_help("write a number such as `6`, or a knob declared `knob depth: int = 6 \"...\"`"),
                        );
                    }
                }
            }
        }
    }

    fn verb(&mut self, w: &Word) {
        if vocab::is_verb(&w.text) {
            return;
        }
        let s = vocab::suggest(&w.text, vocab::verb_names());
        self.unknown(w, "unknown verb", "not a kind, field or relation", s, None);
    }

    fn object(&mut self, o: &Object) {
        match o {
            Object::Shape(s) => self.shape(s),
            Object::Term(t) => {
                if let TermKind::Path(p) = &t.node
                    && let [only] = p.segments.as_slice()
                {
                    if let Some(v) = self.lookup(&only.text) {
                        self.used[v.id] = true;
                    } else if vocab::kind(&only.text).is_some() {
                        self.kind_use(only);
                    } else {
                        self.unbound(only, NamePos::KindOrVar);
                    }
                    return;
                }
                self.term(t);
            }
        }
    }

    // ---- shapes and sources ---------------------------------------------------------------

    fn source(&mut self, s: &Source) {
        match s {
            Source::Shape(shape) => self.shape(shape),
            Source::Side(p) => self.side_path(p),
        }
    }

    /// Whether a side-relation path names a relation (or, for `config`, a node of the schema).
    fn side_known(&self, segs: &[&str]) -> bool {
        match segs {
            ["config"] => false,
            ["config", rest @ ..] => self
                .config
                .is_none_or(|c| c.node(&rest.join(".")).is_some()),
            _ => vocab::fixed_side(&segs[..segs.len().min(2)]).is_some(),
        }
    }

    /// The columns of the rows a side-relation source yields, when the catalog types them.
    fn row_columns(&self, p: &Path) -> Option<Rc<Vec<Column>>> {
        let segs: Vec<&str> = p.segments.iter().map(|s| s.text.as_str()).collect();
        match segs.as_slice() {
            ["config", rest @ ..] => self
                .config?
                .node(&rest.join("."))?
                .columns
                .clone()
                .map(Rc::new),
            _ => vocab::fixed_side(&segs).map(|s| Rc::new(s.typed_columns())),
        }
    }

    /// GRL001 for an unknown key under `config`, suggesting from the keys that do exist there.
    fn unknown_config_key(&mut self, p: &Path, config: &ConfigSchema) {
        let mut prefix = String::new();
        for (i, seg) in p.segments.iter().enumerate().skip(1) {
            let path = if prefix.is_empty() {
                seg.text.clone()
            } else {
                format!("{prefix}.{}", seg.text)
            };
            if config.node(&path).is_none() {
                let siblings: Vec<String> = if prefix.is_empty() {
                    config.tables().into_iter().map(str::to_owned).collect()
                } else {
                    config
                        .node(&prefix)
                        .map(|n| n.children.clone())
                        .unwrap_or_default()
                };
                let s = vocab::suggest(&seg.text, siblings.iter().map(String::as_str));
                let owner = p.segments[..i]
                    .iter()
                    .map(|x| x.text.as_str())
                    .collect::<Vec<_>>()
                    .join(".");
                let list = siblings.join(", ");
                self.unknown(
                    seg,
                    "unknown config key",
                    &format!("not a key of `{owner}`"),
                    s,
                    Some(&format!("the keys of `{owner}` are {list}")),
                );
                return;
            }
            prefix = path;
        }
    }

    fn side_path(&mut self, p: &Path) {
        let segs: Vec<&str> = p.segments.iter().map(|s| s.text.as_str()).collect();
        if self.side_known(&segs) {
            return;
        }
        if segs.len() >= 2
            && segs[0] == "config"
            && let Some(config) = self.config
        {
            self.unknown_config_key(p, config);
            return;
        }
        let joined = segs.join(".");
        let root_ok = vocab::is_side_root(segs[0]);
        let s = vocab::suggest(&joined, vocab::side_relation_names());
        let (span, word) = if root_ok {
            (p.span, joined)
        } else {
            (p.segments[0].span, segs[0].to_owned())
        };
        let w = Word { text: word, span };
        self.unknown(&w, "unknown side relation", "not a side relation", s, None);
    }

    fn shape(&mut self, s: &Shape) {
        match &s.node {
            ShapeKind::Kind { kind, fields, .. } => {
                let Some(info) = vocab::kind(&kind.text) else {
                    let kinds = vocab::kinds();
                    let sg = vocab::suggest(&kind.text, kinds.iter().map(|k| k.word));
                    self.unknown(
                        kind,
                        "unknown kind",
                        "not a kind, field or relation",
                        sg,
                        None,
                    );
                    return;
                };
                self.kind_use(kind);
                for f in fields {
                    match vocab::field(Some(info.word), &f.name.text) {
                        None => {
                            let names = vocab::field_names(Some(info.word));
                            let sg = vocab::suggest(&f.name.text, names.iter().copied());
                            let list = names.join(", ");
                            self.unknown(
                                &f.name,
                                &format!("unknown field of `{}`", info.word),
                                "not a field of this kind",
                                sg,
                                Some(&format!("the fields of `{}` are {list}", info.word)),
                            );
                        }
                        Some(ty) => {
                            let vt = super::vocab::literal_ty(&f.value.node);
                            if !ty.compatible(&vt) {
                                self.out.push(
                                    Diagnostic::new(
                                        Code::Grl005,
                                        format!(
                                            "mismatched types: `{}` is {}, compared with {}",
                                            f.name.text,
                                            ty.phrase(),
                                            vt.phrase()
                                        ),
                                        f.value.span,
                                        format!(
                                            "expected {} here, found {}",
                                            ty.phrase(),
                                            describe_literal(&f.value)
                                        ),
                                    )
                                    .with_secondary(
                                        f.name.span,
                                        format!("this is {}", ty.phrase()),
                                    ),
                                );
                            }
                        }
                    }
                }
            }
            ShapeKind::Snippet { cast, .. } => {
                if let Some(Spanned {
                    node: CastKind::Kind(w),
                    ..
                }) = cast
                {
                    if vocab::kind(&w.text).is_none() {
                        let kinds = vocab::kinds();
                        let sg = vocab::suggest(&w.text, kinds.iter().map(|k| k.word));
                        self.unknown(w, "unknown kind", "not a kind, field or relation", sg, None);
                    } else {
                        self.kind_use(w);
                    }
                }
            }
            ShapeKind::Alt(alts) => {
                for a in alts {
                    self.shape(a);
                }
            }
        }
    }

    // ---- terms and types ------------------------------------------------------------------

    // frob:ticket 01M4E0BVMZHYZYC7PHEA0YWS08
    fn term(&mut self, t: &Term) -> Ty {
        match &t.node {
            TermKind::Path(p) => self.path(p),
            TermKind::Literal(l) => vocab::literal_ty(&l.node),
            TermKind::Knob(w) => self.knob(w),
            TermKind::Count(b) => {
                self.local_binding("count", b, false);
                Ty::Int
            }
            TermKind::Call(call) => self.func(call),
            TermKind::Binary { op, lhs, rhs } => {
                let l = self.term(lhs);
                let r = self.flipped(matches!(op, ArithOp::Sub), |s| s.term(rhs));
                for (ty, side) in [(&l, lhs), (&r, rhs)] {
                    if ty.is_concrete() && !ty.is_numeric() {
                        self.out.push(
                            Diagnostic::new(
                                Code::Grl005,
                                format!("mismatched types: arithmetic needs numbers, not {}", ty.phrase()),
                                side.span,
                                format!("expected a number here, found {}", ty.phrase()),
                            )
                            .with_help("`+`, `-` and `*` work on integers and decimals such as `count(...)` or `knob.depth`"),
                        );
                    }
                }
                if l == Ty::Int && r == Ty::Int {
                    Ty::Int
                } else if l.is_numeric() && r.is_numeric() {
                    Ty::Float
                } else {
                    Ty::Any
                }
            }
            TermKind::Range { lo, hi } => {
                self.term(lo);
                self.term(hi);
                Ty::List(Box::new(Ty::Int))
            }
        }
    }

    fn knob(&mut self, w: &Word) -> Ty {
        if let Some((_, ty)) = self.knobs.iter().find(|k| k.0 == w.text) {
            return ty.clone();
        }
        let names: Vec<&str> = self.knobs.iter().map(|k| k.0.as_str()).collect();
        let s = vocab::suggest(&w.text, names.iter().copied()).map(str::to_owned);
        self.unknown(
            w,
            "unknown knob",
            "not a knob of this rule",
            s.as_deref(),
            Some("declare it in the header: `knob NAME: TYPE = DEFAULT \"what it does\"`"),
        );
        Ty::Any
    }

    fn func(&mut self, call: &Call) -> Ty {
        for a in &call.args {
            self.term(a);
        }
        if let Some(ret) = vocab::function_ty(&call.name.text) {
            return ret;
        }
        if self.defs.iter().any(|d| d.0 == call.name.text) {
            return Ty::Bool;
        }
        let mut names: Vec<&str> = vocab::function_names().collect();
        names.extend(self.defs.iter().map(|d| d.0.as_str()));
        let s = vocab::suggest(&call.name.text, names.iter().copied()).map(str::to_owned);
        self.unknown(
            &call.name,
            "unknown function",
            "not a built-in function or `def`",
            s.as_deref(),
            None,
        );
        Ty::Any
    }

    /// Resolve `x.f.g` against the variables in scope, the side-relation roots and the field tables.
    fn path(&mut self, p: &Path) -> Ty {
        let first = &p.segments[0];
        let mut ty = if let Some(v) = self.lookup(&first.text) {
            self.used[v.id] = true;
            match v.ty {
                VarTy::Kind(k) => Ty::Node(Some(k)),
                VarTy::Any => Ty::Node(None),
                VarTy::Side(Some(cols)) => Ty::Row(cols),
                VarTy::Side(None) => Ty::Any,
            }
        } else if first.text == "knob" && p.segments.len() == 2 {
            return self.knob(&p.segments[1]);
        } else if vocab::is_side_root(&first.text) {
            self.side_path_prefix(p);
            return Ty::Any;
        } else {
            self.unbound(first, NamePos::Var);
            return Ty::Any;
        };
        for seg in &p.segments[1..] {
            ty = self.field_of(&ty, seg);
        }
        ty
    }

    /// A term path that starts at a side-relation root (`lease.globs`, `config.lease.shared_files`).
    fn side_path_prefix(&mut self, p: &Path) {
        let segs: Vec<&str> = p.segments.iter().map(|s| s.text.as_str()).collect();
        let probe = &segs[..segs
            .len()
            .min(if segs[0] == "config" { segs.len() } else { 2 })];
        if !self.side_known(probe) {
            self.side_path(p);
        }
    }

    fn field_of(&mut self, base: &Ty, seg: &Word) -> Ty {
        let (found, names, owner) = match base {
            Ty::Node(k) => (
                vocab::field(*k, &seg.text),
                vocab::field_names(*k),
                k.map_or_else(|| "this node".to_owned(), |k| format!("`{k}`")),
            ),
            Ty::Ref => (
                vocab::ref_field(&seg.text),
                vocab::ref_field_names(),
                "this value".to_owned(),
            ),
            Ty::Row(cols) => {
                if let Some(c) = cols.iter().find(|c| c.name == seg.text) {
                    return vocab::ty_of(c.ty);
                }
                let names: Vec<&str> = cols.iter().map(|c| c.name.as_str()).collect();
                let sg = vocab::suggest(&seg.text, names.iter().copied());
                let list = names.join(", ");
                self.unknown(
                    seg,
                    "unknown column",
                    "not a column of this relation",
                    sg,
                    Some(&format!("the columns are {list}")),
                );
                return Ty::Any;
            }
            Ty::Str | Ty::Int | Ty::Float | Ty::Bool | Ty::Regex | Ty::Glob => {
                let s = seg.text.clone();
                self.out.push(
                    Diagnostic::new(
                        Code::Grl001,
                        format!("unknown field `{s}`"),
                        seg.span,
                        format!("{} has no fields", base.phrase()),
                    )
                    .with_help(catalog_help()),
                );
                return Ty::Any;
            }
            _ => return Ty::Any,
        };
        if let Some(t) = found {
            return t;
        }
        let sg = vocab::suggest(&seg.text, names.iter().copied());
        let list = names.join(", ");
        self.unknown(
            seg,
            "unknown field",
            &format!("not a field of {owner}"),
            sg,
            Some(&format!("the fields of {owner} are {list}")),
        );
        Ty::Any
    }

    // frob:ticket 01M4E0BVMZHYZYC7PHEA0YWS08
    fn cmp(&mut self, op: CmpOp, lhs: &Term, rhs: &Term) {
        // A bound that is true when the term is small (`<`, `<=`) is negative in what the term
        // counts; `==` and `!=` are both ways at once, so they are negative on each side.
        let lhs_small = matches!(op, CmpOp::Lt | CmpOp::Le | CmpOp::Eq | CmpOp::Ne);
        let rhs_small = matches!(op, CmpOp::Gt | CmpOp::Ge | CmpOp::Eq | CmpOp::Ne);
        let l = self.flipped(lhs_small, |s| s.term(lhs));
        let r = self.flipped(rhs_small, |s| s.term(rhs));
        let ordered = !matches!(op, CmpOp::Eq | CmpOp::Ne);
        let bad_order = ordered
            && ((l.is_concrete() && !l.is_numeric()) || (r.is_concrete() && !r.is_numeric()));
        if l.compatible(&r) && !bad_order {
            return;
        }
        let (message, found, help) = if bad_order {
            let bad = if l.is_concrete() && !l.is_numeric() {
                &l
            } else {
                &r
            };
            (
                format!(
                    "mismatched types: `<` and `>` compare numbers, not {}",
                    bad.phrase()
                ),
                bad.phrase().to_owned(),
                "ordering works on integers and decimals; use `==` or `~` for text".to_owned(),
            )
        } else {
            (
                format!(
                    "mismatched types: {} is compared with {}",
                    l.phrase(),
                    r.phrase()
                ),
                describe_term(rhs, &r),
                compare_help(lhs, &l, rhs, &r),
            )
        };
        let primary = if bad_order && l.is_concrete() && !l.is_numeric() {
            lhs
        } else {
            rhs
        };
        let mut d = Diagnostic::new(
            Code::Grl005,
            message,
            primary.span,
            if bad_order {
                format!("expected a number here, found {found}")
            } else {
                format!("expected {} here, found {found}", l.phrase())
            },
        );
        if !bad_order {
            d = d.with_secondary(
                lhs.span,
                format!("this is {}", l.phrase()).replace("is a ", "is a "),
            );
        }
        self.out.push(d.with_help(help));
    }

    /// `~` and `matches`: text on the left, a pattern of the right flavour on the right.
    fn matching(&mut self, l: &Ty, lhs: &Term, r: &Ty, rhs: &Term, word: &str) {
        let want = if word == "regex" { Ty::Regex } else { Ty::Glob };
        let op = if word == "regex" { "~" } else { "matches" };
        if l.is_concrete() && !l.compatible(&Ty::Str) && !matches!(l, Ty::List(_)) {
            self.out.push(
                Diagnostic::new(
                    Code::Grl005,
                    format!("mismatched types: `{op}` matches text, not {}", l.phrase()),
                    lhs.span,
                    format!("expected a string here, found {}", l.phrase()),
                )
                .with_help("match a text field such as `x.name`, `x.text` or `x.path`"),
            );
        }
        let other = if want == Ty::Regex {
            Ty::Glob
        } else {
            Ty::Regex
        };
        let list_of_other = matches!(r, Ty::List(e) if **e == other);
        if *r == other || list_of_other {
            self.out.push(
                Diagnostic::new(
                    Code::Grl005,
                    format!("mismatched types: {} is used as a {word}", r.phrase()),
                    rhs.span,
                    format!("`{op}` expects a {word} here, found {}", r.phrase()),
                )
                .with_help(if word == "regex" {
                    "use `matches` for globs, or write a regex literal such as `/todo/i`"
                } else {
                    "use `~` for regexes, or write a glob string such as \"src/**/*.rs\""
                }),
            );
        } else if r.is_concrete() && *r != want && !matches!(r, Ty::Str | Ty::List(_)) {
            self.out.push(Diagnostic::new(
                Code::Grl005,
                format!("mismatched types: {} is used as a {word}", r.phrase()),
                rhs.span,
                format!("`{op}` expects a {word} here, found {}", r.phrase()),
            ));
        }
    }

    fn membership(&mut self, l: &Ty, lhs: &Term, r: &Ty, rhs: &Term) {
        let elem = match r {
            Ty::List(e) => Some((**e).clone()),
            _ => None,
        };
        if r.is_concrete() && elem.is_none() {
            self.out.push(
                Diagnostic::new(
                    Code::Grl005,
                    format!("mismatched types: `in` needs a list or a range, not {}", r.phrase()),
                    rhs.span,
                    format!("expected a list here, found {}", r.phrase()),
                )
                .with_help("compare single values with `==`; use `in` with a list, a range `1..3`, a vocabulary or a side relation"),
            );
        } else if let Some(e) = elem
            && !l.compatible(&e)
        {
            self.out.push(Diagnostic::new(
                Code::Grl005,
                format!(
                    "mismatched types: {} is looked up in a list of {}s",
                    l.phrase(),
                    e.phrase()
                        .trim_start_matches("a ")
                        .trim_start_matches("an ")
                ),
                lhs.span,
                format!("expected {} here, found {}", e.phrase(), l.phrase()),
            ));
        }
    }

    // ---- messages and variable references -------------------------------------------------

    fn var_ref(&mut self, w: &Word) {
        if let Some(v) = self.lookup(&w.text) {
            self.used[v.id] = true;
        } else {
            self.unbound(w, NamePos::Var);
        }
    }

    fn message(&mut self, m: &Message) {
        for part in &m.parts {
            if let MessagePart::Interp { path, .. } = part {
                self.path(path);
            }
        }
    }

    // ---- diagnostics ----------------------------------------------------------------------

    /// A word that is neither a variable nor, for an object, a kind.
    fn unbound(&mut self, w: &Word, pos: NamePos) {
        let kinds = vocab::kinds();
        let mut cands: Vec<&str> = self.vars.iter().map(|v| v.name.as_str()).collect();
        if pos == NamePos::KindOrVar {
            cands.extend(kinds.iter().map(|k| k.word));
        }
        let sg = vocab::suggest(&w.text, cands.iter().copied()).map(str::to_owned);
        if let (Some(via), false, None) = (self.neg, self.in_def, &sg) {
            if self.seen_grl003.insert(w.text.clone()) {
                let n = &w.text;
                let v = via.word();
                self.out.push(
                    Diagnostic::new(
                        Code::Grl003,
                        format!("`{n}` is only used inside `{v}`; add a `find {n}:` clause"),
                        w.span,
                        format!("`{n}` is not bound anywhere"),
                    )
                    .with_note("`not`, `no` and `unresolved when` use variables but never bind them")
                    .with_help(format!(
                        "bind it outside the `{v}`, for example `find {n}: function`, so the rule says where `{n}` comes from"
                    )),
                );
            }
            return;
        }
        let (message, label, extra) = match pos {
            NamePos::KindOrVar => ("unknown kind", "not a kind, field or relation", None),
            NamePos::Var => (
                "unknown variable",
                "not bound by any `find` in scope",
                Some(format!("bind it with `find {}: KIND` or `some`", w.text)),
            ),
        };
        self.unknown(w, message, label, sg.as_deref(), extra.as_deref());
    }

    /// GRL001 for `w`.
    fn unknown(
        &mut self,
        w: &Word,
        what: &str,
        label: &str,
        suggestion: Option<&str>,
        extra: Option<&str>,
    ) {
        let mut d = Diagnostic::new(Code::Grl001, format!("{what} `{}`", w.text), w.span, label);
        if let Some(s) = suggestion {
            d = d.with_help(format!("did you mean `{s}`?"));
        }
        if let Some(e) = extra {
            d = d.with_help(e);
        }
        self.out.push(d.with_help(catalog_help()));
    }

    /// GRL018: a kind that none of the rule's languages answers.
    fn kind_use(&mut self, w: &Word) {
        let LangMode::Listed(langs) = &self.langs else {
            return;
        };
        let Some(info) = vocab::kind(&w.text) else {
            return;
        };
        if matches!(info.answers, Answers::Everywhere)
            || langs.iter().any(|l| info.answers.answered_in(l))
        {
            return;
        }
        if !self.seen_kind_use.insert(w.text.clone()) {
            return;
        }
        let which = if langs.is_empty() {
            "`lang -`".to_owned()
        } else {
            format!("`lang {}`", langs.join(", "))
        };
        let mut d = Diagnostic::new(
            Code::Grl018,
            format!("`{}` is never answered by {which}", w.text),
            w.span,
            "no language of this rule answers this word",
        )
        .with_note("a word no language of the rule answers can never match, so the rule would be NotApplicable everywhere")
        .with_help(format!(
            "`{}` is answered in {}; add one of them to `lang`, or remove this clause",
            w.text,
            info.answers.describe()
        ));
        if let Some(s) = self.lang_span {
            d = d.with_secondary(s, "the languages are set here");
        }
        self.out.push(d);
    }
}

/// How a term is shown in a "found ..." label: a literal quotes itself.
fn describe_term(t: &Term, ty: &Ty) -> String {
    match &t.node {
        TermKind::Literal(l) => describe_literal(l),
        _ => ty.phrase().to_owned(),
    }
}

fn describe_literal(l: &Literal) -> String {
    match &l.node {
        LiteralKind::Int(n) => format!("the integer `{n}`"),
        LiteralKind::Decimal(d) => format!("the decimal `{d}`"),
        LiteralKind::Str(s) => format!("the string `\"{s}\"`"),
        LiteralKind::Bool(b) => format!("the boolean `{b}`"),
        other => vocab::literal_ty(other).phrase().to_owned(),
    }
}

/// The help line of a mismatched comparison.
fn compare_help(lhs: &Term, l: &Ty, rhs: &Term, r: &Ty) -> String {
    let root = |t: &Term| match &t.node {
        TermKind::Path(p) => Some(p.segments[0].text.clone()),
        _ => None,
    };
    match (l, r, &rhs.node, &lhs.node) {
        (
            Ty::Str,
            Ty::Int,
            TermKind::Literal(Literal {
                node: LiteralKind::Int(n),
                ..
            }),
            _,
        ) => {
            let tail = root(lhs).map_or_else(String::new, |x| {
                format!(", or compare a number such as `{x}.line`")
            });
            format!("write `\"{n}\"` to compare with text{tail}")
        }
        (Ty::Int, Ty::Str, _, _) => {
            let tail = root(rhs)
                .or_else(|| root(lhs))
                .map_or_else(String::new, |x| {
                    format!(", or compare text such as `{x}.name`")
                });
            format!("write the number without quotes to compare numbers{tail}")
        }
        _ => format!(
            "both sides of a comparison need the same type: the left is {}, the right is {}",
            l.phrase(),
            r.phrase()
        ),
    }
}

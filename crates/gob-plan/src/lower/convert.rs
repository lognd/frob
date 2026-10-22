//! Syntax tree to a name-based tree: the checked clauses with no numbering decided yet.

// frob:ticket 01M3ZX7EKNE5Q0NB0DKCH77AZX
use gob_caps::Capability;
use gob_text::Span;

use super::LowerError;
use crate::grl::ast::{
    self, Binding, CastKind, Clause, ClauseKind, CondKind, Header, HeaderKind, LangSet,
    LiteralKind, MessagePart, Object, RelKind, Rule, ShapeKind, Source, Term, TermKind,
};
use crate::plan::{
    ANY_NODES, Certainty, CmpOp, MAX_SCALE_PLACES, Polarity, Position, Quant, Read, Scale,
};

/// A value a condition compares, by name.
#[derive(Debug, Clone, PartialEq, Eq)]
pub(super) enum Opd {
    Var(String),
    Field(String, String),
    Int(i64),
    Str(String),
    Bool(bool),
    /// `slug(s)`; the argument is never itself a call.
    Slug(Box<Opd>),
    /// `resolve(path, from)`; the arguments are never themselves calls.
    Resolve(Box<Opd>, Box<Opd>),
}

/// A condition by variable name. Its `Debug` text is the planner's sort key.
#[derive(Debug, Clone, PartialEq, Eq)]
pub(super) enum Cond {
    And(Vec<Cond>),
    Or(Vec<Cond>),
    Not(Box<Cond>),
    Quant {
        quant: Quant,
        var: String,
        kind: String,
        cond: Box<Cond>,
    },
    Inside {
        sub: String,
        sup: String,
        direct: bool,
    },
    Order {
        a: String,
        b: String,
        pos: Position,
    },
    Verb {
        subject: String,
        object: String,
        verb: String,
        certainty: Certainty,
    },
    Cmp {
        lhs: Opd,
        op: CmpOp,
        rhs: Opd,
    },
    Regex {
        subject: Opd,
        pattern: String,
    },
    Glob {
        subject: Opd,
        pattern: String,
    },
    GlobSet {
        subject: Opd,
        need: Read,
        table: String,
        column: String,
    },
    Is {
        subject: Opd,
        test: String,
    },
    Exists(Opd),
    HasAttr {
        var: String,
        attr: String,
    },
    GlobOperand {
        subject: Opd,
        pattern: Opd,
    },
    /// The variable's node name is in the union of the named vocabulary classes.
    InVocab {
        var: String,
        classes: Vec<String>,
    },
    Under {
        subject: Opd,
        prefix: Opd,
    },
    /// The variable's node is exactly a match of a grammar-level snippet in `lang`.
    MatchSnippet {
        var: String,
        lang: String,
        pattern: String,
        /// `as KIND` cast: inside a match rather than exactly one.
        within: bool,
    },
    InUnit {
        sub: String,
        unit: String,
    },
    Reaches {
        from: String,
        to: String,
        via: String,
        within: u16,
    },
    /// A call of the def at this index in [`Lowered::defs`].
    Call {
        def: usize,
        args: Vec<String>,
    },
    /// `count(var: kind where cond) op limit`.
    CountCmp {
        var: String,
        kind: String,
        cond: Box<Cond>,
        op: CmpOp,
        limit: Lim,
    },
    /// `SCALE * count(..) op SCALE * count(..)`: two counts compared, each times a decimal.
    CountPair {
        lhs: CountSideC,
        op: CmpOp,
        rhs: CountSideC,
    },
}

/// One counted side of a [`Cond::CountPair`], in name form.
#[derive(Debug, Clone, PartialEq, Eq)]
pub(super) struct CountSideC {
    pub var: String,
    pub kind: String,
    pub cond: Box<Cond>,
    pub scale: Scale,
}

/// What a count is compared with, by name.
#[derive(Debug, Clone, PartialEq, Eq)]
pub(super) enum Lim {
    Int(u64),
    /// A knob: its name and declared default.
    Knob(String, u64),
}

/// A `def` in name form: the body sees only the parameters.
pub(super) struct DefItem {
    pub params: Vec<String>,
    pub body: Cond,
}

/// What a `find` ranges over.
#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord)]
pub(super) enum Src {
    Kind(String),
    Side(Read, String),
}

/// A binder with the conditions written on it (field equalities, relations, `where`).
pub(super) struct FindItem {
    pub name: String,
    pub src: Src,
    pub attached: Vec<Cond>,
}

pub(super) struct ReportItem {
    pub subject: String,
    pub message: String,
    pub when: Option<Cond>,
}

/// Which languages, by name.
pub(super) enum LangNames {
    Any,
    Nothing,
    Only(Vec<String>),
}

/// One rule in name form.
pub(super) struct Lowered {
    pub id: String,
    pub langs: LangNames,
    pub polarity: Polarity,
    pub needs: Vec<Read>,
    pub repo_scope: bool,
    pub finds: Vec<FindItem>,
    pub wheres: Vec<Cond>,
    pub unresolved: Vec<(Cond, String)>,
    pub reports: Vec<ReportItem>,
    /// The defs, in text order; a call names one by index.
    pub defs: Vec<DefItem>,
}

/// A knob's declared default, which is what a lowered plan reads (an override from `[rules]` is
/// honoured only for a `count` limit; see `Limit::Knob`).
#[derive(Debug, Clone, PartialEq, Eq)]
enum KnobVal {
    Int(i64),
    /// A decimal default, exact (`0.7` is 7 over 10^1).
    Dec(Scale),
    Bool(bool),
    Str(String),
    /// A regex in the plan's pattern form (flags folded in).
    Regex(String),
    /// A list of strings (globs or plain words).
    Strs(Vec<String>),
    /// A `vocab("class", ...)` knob: the vocabulary classes it unions.
    Vocab(Vec<String>),
    /// A knob whose value the lowering does not read yet (decimals, vocabularies, other lists).
    Other,
}

struct Cx {
    knobs: Vec<(String, KnobVal)>,
    scope: Vec<String>,
    /// Variables bound by a top-level side-relation find, with that relation's dotted name.
    side_vars: Vec<(String, String)>,
    /// The defs lowered so far: name and parameter count, parallel to [`Lowered::defs`].
    defs: Vec<(String, usize)>,
    fresh: u32,
    /// The rule's one `lang`, the default language of an untagged snippet.
    lang: Option<String>,
}

fn unsupported<T>(what: &'static str, span: Span) -> Result<T, LowerError> {
    Err(LowerError::Unsupported { what, span })
}

pub(super) fn convert(rule: &Rule) -> Result<Lowered, LowerError> {
    let mut out = Lowered {
        id: rule.id.text.clone(),
        langs: LangNames::Any,
        polarity: Polarity::Pplus,
        needs: Vec::new(),
        repo_scope: false,
        finds: Vec::new(),
        wheres: Vec::new(),
        unresolved: Vec::new(),
        reports: Vec::new(),
        defs: Vec::new(),
    };
    let mut knobs = Vec::new();
    for h in &rule.headers {
        header(&mut out, h)?;
        if let HeaderKind::Knob(k) = &h.node {
            knobs.push((k.name.text.clone(), knob_value(&k.default)?));
        }
    }
    check_vocab_needs(rule, &knobs)?;
    let mut cx = Cx {
        knobs,
        scope: Vec::new(),
        side_vars: Vec::new(),
        defs: Vec::new(),
        fresh: 0,
        lang: match &out.langs {
            LangNames::Only(v) if v.len() == 1 => Some(v[0].clone()),
            _ => None,
        },
    };
    for c in &rule.clauses {
        if let ClauseKind::Find(b) = &c.node {
            if cx.scope.contains(&b.name.text) {
                return Err(LowerError::Duplicate {
                    name: b.name.text.clone(),
                    span: b.name.span,
                });
            }
            cx.scope.push(b.name.text.clone());
        }
    }
    // Defs first, in text order, so any clause may call any def (a def body only earlier ones).
    for c in &rule.clauses {
        if let ClauseKind::Def(d) = &c.node {
            def_item(&mut out, &mut cx, d)?;
        }
    }
    for c in &rule.clauses {
        clause(&mut out, &mut cx, c)?;
    }
    Ok(out)
}

/// The knob name in a `vocab(NAME)` need word.
fn vocab_need(word: &str) -> Option<&str> {
    word.strip_prefix("vocab(")?.strip_suffix(')')
}

/// The capability a `needs` word names (its `Capability::name`), if any.
fn capability_named(word: &str) -> Option<Capability> {
    Capability::ALL.iter().copied().find(|c| c.name() == word)
}

/// The capabilities a rule's `needs` headers require of a language (`vocab(...)` needs are not
/// capabilities and are skipped); a language whose matrix cell for any of them is not applicable
/// makes the rule `NotApplicable` there, statically (grl-spec section 7.0.7).
// frob:ticket 01M4CXV36WX1C2T64J454ECDV7
pub fn needed_capabilities(rule: &Rule) -> Vec<Capability> {
    rule.headers
        .iter()
        .filter_map(|h| match &h.node {
            HeaderKind::Needs(ws) => Some(ws),
            _ => None,
        })
        .flatten()
        .filter_map(|w| capability_named(&w.text))
        .collect()
}

/// Every `needs vocab(NAME)` must name a declared vocab knob. The need itself is a language
/// capability gate (a language with no registered vocabulary makes the rule not applicable), not
/// a data input, so the plan records nothing for it: inside a formula an empty vocabulary is the
/// empty set (`InVocab` is No).
fn check_vocab_needs(rule: &Rule, knobs: &[(String, KnobVal)]) -> Result<(), LowerError> {
    for h in &rule.headers {
        let HeaderKind::Needs(words) = &h.node else {
            continue;
        };
        for w in words {
            let Some(name) = vocab_need(&w.text) else {
                continue;
            };
            if !knobs
                .iter()
                .any(|(n, v)| n == name && matches!(v, KnobVal::Vocab(_)))
            {
                return Err(LowerError::UnknownNeed {
                    name: w.text.clone(),
                    span: w.span,
                });
            }
            tracing::debug!(rule = %rule.id.text, vocab = name, "vocab need checked against its knob");
        }
    }
    Ok(())
}

fn header(out: &mut Lowered, h: &Header) -> Result<(), LowerError> {
    match &h.node {
        HeaderKind::Lang(l) => {
            out.langs = match l {
                LangSet::Any { .. } => LangNames::Any,
                LangSet::Nothing => LangNames::Nothing,
                LangSet::One(w) => LangNames::Only(vec![w.text.clone()]),
                LangSet::List(ws) => LangNames::Only(ws.iter().map(|w| w.text.clone()).collect()),
            };
        }
        HeaderKind::Polarity(p) => out.polarity = *p,
        HeaderKind::Scope(s) => out.repo_scope = matches!(s, ast::Scope::Repo),
        HeaderKind::Needs(words) => {
            for w in words {
                if vocab_need(&w.text).is_some() {
                    // Checked against the knobs once all headers are read (see `convert`).
                    continue;
                }
                // A capability need is a static applicability gate (see `needed_capabilities`);
                // the plan records nothing for it, so only the name is validated here.
                if capability_named(&w.text).is_none() {
                    return Err(LowerError::UnknownNeed {
                        name: w.text.clone(),
                        span: w.span,
                    });
                }
            }
        }
        HeaderKind::Reads(words) => {
            for w in words {
                out.needs.push(match w.text.as_str() {
                    "config" => Read::Config,
                    "diff" => Read::Diff,
                    "lease" => Read::Lease,
                    "model" => Read::Model,
                    other => {
                        return Err(LowerError::UnknownNeed {
                            name: other.to_owned(),
                            span: w.span,
                        });
                    }
                });
            }
        }
        HeaderKind::Knob(_)
        | HeaderKind::Severity(_)
        | HeaderKind::MustMeasure
        | HeaderKind::Rollup(_) => {}
    }
    Ok(())
}

fn clause(out: &mut Lowered, cx: &mut Cx, c: &Clause) -> Result<(), LowerError> {
    cx.fresh = 0;
    match &c.node {
        ClauseKind::Find(b) => {
            let (src, attached) = binding_parts(cx, b, true)?;
            out.finds.push(FindItem {
                name: b.name.text.clone(),
                src,
                attached,
            });
        }
        ClauseKind::Where(cond) => out.wheres.push(cond_of(cx, cond)?),
        ClauseKind::Quant { quant, binding } => out.wheres.push(quantifier(cx, *quant, binding)?),
        ClauseKind::Report(r) => {
            require_bound(cx, &r.target)?;
            out.reports.push(ReportItem {
                subject: r.target.text.clone(),
                message: message_text(&r.message),
                when: r.when.as_ref().map(|w| cond_of(cx, w)).transpose()?,
            });
        }
        ClauseKind::Unresolved(u) => {
            out.unresolved
                .push((cond_of(cx, &u.when)?, message_text(&u.because)));
        }
        // Defs were lowered up front; notes and fixes carry no condition.
        ClauseKind::Def(_) | ClauseKind::Note(_) | ClauseKind::Fix(_) => {}
    }
    Ok(())
}

/// A def: its body is lowered with only the parameters in scope.
fn def_item(out: &mut Lowered, cx: &mut Cx, d: &ast::Def) -> Result<(), LowerError> {
    let params: Vec<String> = d.params.iter().map(|p| p.text.clone()).collect();
    let saved = std::mem::replace(&mut cx.scope, params.clone());
    cx.fresh = 0;
    let body = cond_of(cx, &d.body);
    cx.scope = saved;
    out.defs.push(DefItem {
        params: params.clone(),
        body: body?,
    });
    cx.defs.push((d.name.text.clone(), params.len()));
    Ok(())
}

/// The `within` bound of a `reaches`: an integer literal or an int knob (at its declared
/// default), from 1 to 65535 edges.
fn within_bound(cx: &Cx, t: &Term) -> Result<u16, LowerError> {
    let n = match &t.node {
        TermKind::Literal(l) => match &l.node {
            LiteralKind::Int(i) => i64::try_from(*i).ok(),
            _ => None,
        },
        TermKind::Knob(w) => match knob_of(cx, w)? {
            KnobVal::Int(i) => Some(*i),
            _ => None,
        },
        _ => None,
    };
    match n.and_then(|n| u16::try_from(n).ok()).filter(|n| *n >= 1) {
        Some(n) => Ok(n),
        None => unsupported(
            "a `within` bound that is not an integer from 1 to 65535",
            t.span,
        ),
    }
}

/// `NAME(args)` as a condition: the def by index, with variable arguments.
fn call_cond(cx: &Cx, call: &ast::Call) -> Result<Cond, LowerError> {
    let Some(def) = cx.defs.iter().position(|(n, _)| *n == call.name.text) else {
        return unsupported("a call of a def that is not defined earlier", call.span);
    };
    if cx.defs[def].1 != call.args.len() {
        return unsupported("a def call with the wrong number of arguments", call.span);
    }
    let args = call
        .args
        .iter()
        .map(|a| match var_name(cx, a)? {
            Some(v) => Ok(v),
            None => unsupported("a def argument that is not a variable", a.span),
        })
        .collect::<Result<_, LowerError>>()?;
    Ok(Cond::Call { def, args })
}

fn require_bound(cx: &Cx, w: &ast::Word) -> Result<(), LowerError> {
    if cx.scope.contains(&w.text) {
        Ok(())
    } else {
        Err(LowerError::UnknownVar {
            name: w.text.clone(),
            span: w.span,
        })
    }
}

fn message_text(m: &ast::Message) -> String {
    m.parts
        .iter()
        .map(|p| match p {
            MessagePart::Text { value, .. } => value.clone(),
            MessagePart::Interp { path, .. } => {
                let names: Vec<&str> = path.segments.iter().map(|s| s.text.as_str()).collect();
                format!("{{{}}}", names.join("."))
            }
        })
        .collect()
}

/// The field equalities a kind shape states: its `(f = v)` pairs, and a string argument
/// (`directive "todo"`) as an equality on the node's `name`.
fn kind_fields(
    fields: &[ast::FieldEq],
    arg: Option<&ast::StrLit>,
) -> Result<Vec<(String, Opd)>, LowerError> {
    let mut out = fields
        .iter()
        .map(|f| Ok((f.name.text.clone(), literal(&f.value)?)))
        .collect::<Result<Vec<_>, LowerError>>()?;
    if let Some(a) = arg {
        out.push(("name".to_owned(), Opd::Str(a.value.clone())));
    }
    Ok(out)
}

/// The anchored regex for a `key(path = "...")` pattern: `*` stays within one path segment, `**`
/// crosses segments, anything else is literal.
// frob:ticket 01M5ETB80YYSQNEDP9PG86WKD4
fn key_path_regex(pattern: &str) -> String {
    let mut out = String::from("^");
    let mut chars = pattern.chars().peekable();
    while let Some(c) = chars.next() {
        match c {
            '*' if chars.peek() == Some(&'*') => {
                chars.next();
                out.push_str(".*");
            }
            '*' => out.push_str("[^/]*"),
            c => out.push_str(&regex::escape(c.encode_utf8(&mut [0; 4]))),
        }
    }
    out.push('$');
    out
}

/// The condition one `(f = v)` pair of a kind shape states: equality, except a `key` path pattern.
// frob:ticket 01M5ETB80YYSQNEDP9PG86WKD4
fn field_cond(kind: &str, var: &str, field: &str, rhs: Opd) -> Cond {
    let subject = Opd::Field(var.to_owned(), field.to_owned());
    match rhs {
        Opd::Str(p) if kind == "key" && field == "path" => Cond::Regex {
            subject,
            pattern: key_path_regex(&p),
        },
        rhs => Cond::Cmp {
            lhs: subject,
            op: CmpOp::Eq,
            rhs,
        },
    }
}

/// `x is` a snippet: a match op on a variable, or its roles lift for the `as roles` form.
fn is_snippet_cond(
    cx: &mut Cx,
    subject: &Term,
    snippet: &crate::grl::Snippet,
    roles: bool,
    span: Span,
) -> Result<Cond, LowerError> {
    match var_name(cx, subject)? {
        Some(var) if roles => super::roles::roles_cond(&var, snippet, &mut cx.fresh, span),
        Some(var) => snippet_cond(cx, &var, snippet, false, span),
        None => unsupported("`is` a snippet on a non-variable", subject.span),
    }
}

/// A snippet as a condition on a variable, in the snippet's language or the rule's only one.
fn snippet_cond(
    cx: &Cx,
    var: &str,
    snippet: &crate::grl::Snippet,
    within: bool,
    span: Span,
) -> Result<Cond, LowerError> {
    let lang = match (&snippet.lang, &cx.lang) {
        (Some(l), _) => l.name.clone(),
        (None, Some(l)) => l.clone(),
        (None, None) => return unsupported("a snippet with no language", span),
    };
    tracing::debug!(var, lang, "lowering a snippet pattern");
    Ok(Cond::MatchSnippet {
        var: var.to_owned(),
        lang,
        pattern: snippet.text.clone(),
        within,
    })
}

/// The source of a binder and the conditions written on it: field equalities, relations, filter.
fn binding_parts(cx: &mut Cx, b: &Binding, top: bool) -> Result<(Src, Vec<Cond>), LowerError> {
    let name = b.name.text.clone();
    let mut attached = Vec::new();
    let src = match &b.source {
        Source::Shape(s) => match &s.node {
            ShapeKind::Kind { kind, fields, arg } => {
                for (f, rhs) in kind_fields(fields, arg.as_ref())? {
                    attached.push(field_cond(&kind.text, &name, &f, rhs));
                }
                Src::Kind(kind.text.clone())
            }
            ShapeKind::Snippet { snippet, cast } => {
                match cast.as_ref().map(|c| &c.node) {
                    // `as KIND`: the binder ranges over nodes of KIND inside a match.
                    Some(CastKind::Kind(k)) => {
                        attached.push(snippet_cond(cx, &name, snippet, true, s.span)?);
                        Src::Kind(k.text.clone())
                    }
                    Some(CastKind::Roles) => return unsupported("a snippet as roles", s.span),
                    None => {
                        attached.push(snippet_cond(cx, &name, snippet, false, s.span)?);
                        Src::Kind(ANY_NODES.to_owned())
                    }
                }
            }
            ShapeKind::Alt(alts) => {
                // `(a | b)`: every node, kept when it is an `a` or a `b` (plain kind words only).
                let mut tests = Vec::new();
                for alt in alts {
                    match &alt.node {
                        ShapeKind::Kind { kind, fields, arg }
                            if fields.is_empty()
                                && arg.is_none()
                                && crate::exec::is_test_word(&kind.text, false) =>
                        {
                            tests.push(Cond::Is {
                                subject: Opd::Var(name.clone()),
                                test: kind.text.clone(),
                            });
                        }
                        _ => {
                            return unsupported(
                                "an alternative that is not a plain kind",
                                alt.span,
                            );
                        }
                    }
                }
                attached.push(Cond::Or(tests));
                Src::Kind(ANY_NODES.to_owned())
            }
        },
        Source::Side(p) => {
            let need = match p.segments[0].text.as_str() {
                "config" => Read::Config,
                "diff" => Read::Diff,
                "lease" => Read::Lease,
                "model" => Read::Model,
                _ => return unsupported("an unknown side relation", p.span),
            };
            if !top {
                return unsupported("a side relation inside a quantifier", p.span);
            }
            let table: Vec<&str> = p.segments.iter().map(|s| s.text.as_str()).collect();
            let table = table.join(".");
            cx.side_vars.push((name.clone(), table.clone()));
            // frob:ticket 01M4XJMM949EHC6X13TYJPYE5V
            Src::Side(need, table)
        }
    };
    if !top {
        cx.scope.push(name.clone());
    }
    let rest: Result<Vec<Cond>, LowerError> = (|| {
        for r in &b.rels {
            attached.push(rel_cond(cx, &name, r)?);
        }
        if let Some(f) = &b.filter {
            attached.push(cond_of(cx, f)?);
        }
        Ok(attached)
    })();
    if !top {
        cx.scope.pop();
    }
    Ok((src, rest?))
}

/// A scoped binder (a quantifier's or a count's): its kind and the one condition on it.
fn scoped(cx: &mut Cx, b: &Binding) -> Result<(String, Cond), LowerError> {
    let (src, mut conds) = binding_parts(cx, b, false)?;
    let Src::Kind(kind) = src else {
        return unsupported("a side relation inside a quantifier", b.span);
    };
    let cond = if conds.len() == 1 {
        conds.remove(0)
    } else {
        Cond::And(conds)
    };
    Ok((kind, cond))
}

fn quantifier(cx: &mut Cx, q: ast::Quant, b: &Binding) -> Result<Cond, LowerError> {
    let (kind, cond) = scoped(cx, b)?;
    Ok(Cond::Quant {
        quant: match q {
            ast::Quant::Some => Quant::Some,
            ast::Quant::No => Quant::No,
        },
        var: b.name.text.clone(),
        kind,
        cond: Box::new(cond),
    })
}

fn cond_of(cx: &mut Cx, c: &ast::Cond) -> Result<Cond, LowerError> {
    Ok(match &c.node {
        CondKind::Or(v) | CondKind::Any(v) => {
            Cond::Or(v.iter().map(|x| cond_of(cx, x)).collect::<Result<_, _>>()?)
        }
        CondKind::And(v) => Cond::And(v.iter().map(|x| cond_of(cx, x)).collect::<Result<_, _>>()?),
        CondKind::Not(x) => Cond::Not(Box::new(cond_of(cx, x)?)),
        CondKind::Quant { quant, binding } => quantifier(cx, *quant, binding)?,
        CondKind::Rel { subject, rel } if matches!(rel.node, RelKind::Under { .. }) => {
            under_cond(cx, subject, rel)?
        }
        CondKind::Rel { subject, rel } => {
            let Some(name) = var_name(cx, subject)? else {
                return unsupported("a relation on a non-variable", subject.span);
            };
            rel_cond(cx, &name, rel)?
        }
        CondKind::Cmp { op, lhs, rhs } if has_count(lhs) || has_count(rhs) => {
            count_cmp(cx, *op, lhs, rhs)?
        }
        CondKind::Cmp { op, lhs, rhs } => Cond::Cmp {
            lhs: operand(cx, lhs)?,
            op: cmp_op(*op),
            rhs: operand(cx, rhs)?,
        },
        CondKind::RegexMatch { lhs, rhs } => match &rhs.node {
            TermKind::Literal(l) => match &l.node {
                LiteralKind::Regex(r) => Cond::Regex {
                    subject: operand(cx, lhs)?,
                    pattern: regex_text(r),
                },
                _ => return unsupported("a non-regex pattern after ~", rhs.span),
            },
            TermKind::Knob(w) => match knob_of(cx, w)? {
                KnobVal::Regex(pattern) => Cond::Regex {
                    subject: operand(cx, lhs)?,
                    pattern: pattern.clone(),
                },
                _ => return unsupported("a knob that is not a regex after ~", w.span),
            },
            _ => return unsupported("a non-literal pattern after ~", rhs.span),
        },
        CondKind::GlobMatch { lhs, rhs } if side_set(rhs).is_some() => {
            let (need, table, column) = side_set(rhs).expect("guarded");
            Cond::GlobSet {
                subject: glob_subject(cx, lhs)?,
                need,
                table,
                column,
            }
        }
        CondKind::GlobMatch { lhs, rhs } if is_field_path(cx, rhs) => Cond::GlobOperand {
            subject: glob_subject(cx, lhs)?,
            pattern: operand(cx, rhs)?,
        },
        CondKind::GlobMatch { lhs, rhs } => {
            let subject = glob_subject(cx, lhs)?;
            let globs = glob_literals(cx, rhs)?;
            let mut alts: Vec<Cond> = globs
                .into_iter()
                .map(|pattern| Cond::Glob {
                    subject: subject.clone(),
                    pattern,
                })
                .collect();
            if alts.len() == 1 {
                alts.remove(0)
            } else {
                Cond::Or(alts)
            }
        }
        CondKind::Flag(t) => match &t.node {
            TermKind::Path(p) if p.segments.len() >= 2 => Cond::Cmp {
                lhs: operand(cx, t)?,
                op: CmpOp::Eq,
                rhs: Opd::Bool(true),
            },
            _ => return unsupported("a flag that is not a field", t.span),
        },
        CondKind::In { lhs, rhs } => in_cond(cx, lhs, rhs)?,
        CondKind::Is { subject, test } => is_cond(cx, subject, test)?,
        CondKind::IsSnippet {
            subject,
            snippet,
            roles,
        } => is_snippet_cond(cx, subject, snippet, *roles, c.span)?,
        CondKind::HasAttr { subject, attr } => match var_name(cx, subject)? {
            Some(var) => Cond::HasAttr {
                var,
                attr: attr.value.clone(),
            },
            None => return unsupported("`has attr` on a non-variable", subject.span),
        },
        CondKind::DefCall(call) => call_cond(cx, call)?,
        CondKind::Exists(t) => Cond::Exists(operand(cx, t)?),
    })
}

/// Whether a term is a count, or a count times a factor.
fn has_count(t: &Term) -> bool {
    match &t.node {
        TermKind::Count(_) => true,
        TermKind::Binary {
            op: ast::ArithOp::Mul,
            lhs,
            rhs,
        } => matches!(lhs.node, TermKind::Count(_)) || matches!(rhs.node, TermKind::Count(_)),
        _ => false,
    }
}

/// A decimal literal as written (`0.7`, `-0.25`, `3.`) to an exact [`Scale`].
fn decimal(text: &str, span: Span) -> Result<Scale, LowerError> {
    let (neg, body) = match text.strip_prefix('-') {
        Some(rest) => (true, rest),
        None => (false, text.strip_prefix('+').unwrap_or(text)),
    };
    let (whole, frac) = body.split_once('.').unwrap_or((body, ""));
    let places = u8::try_from(frac.len())
        .ok()
        .filter(|p| *p <= MAX_SCALE_PLACES);
    let digits = format!("{whole}{frac}");
    let num = digits.parse::<i64>().ok().map(|n| if neg { -n } else { n });
    match (num, places) {
        (Some(num), Some(places)) => Ok(Scale { num, places }),
        _ => unsupported("a decimal beyond 18 places or 64 bits", span),
    }
}

/// A term used as a count's factor: an integer or decimal literal, or a numeric knob.
fn scale_of(cx: &Cx, t: &Term) -> Result<Option<Scale>, LowerError> {
    let int = |i: i64| Scale { num: i, places: 0 };
    Ok(match &t.node {
        TermKind::Literal(l) => match &l.node {
            LiteralKind::Int(i) => i64::try_from(*i).ok().map(int),
            LiteralKind::Decimal(text) => Some(decimal(text, l.span)?),
            _ => None,
        },
        TermKind::Knob(w) => match knob_of(cx, w)? {
            KnobVal::Int(i) => Some(int(*i)),
            KnobVal::Dec(d) => Some(*d),
            _ => None,
        },
        _ => None,
    })
}

/// A term that is a count, optionally times a factor: its binder and the factor.
fn count_side<'a>(cx: &Cx, t: &'a Term) -> Result<Option<(&'a Binding, Scale)>, LowerError> {
    match &t.node {
        TermKind::Count(b) => Ok(Some((b, Scale::ONE))),
        TermKind::Binary {
            op: ast::ArithOp::Mul,
            lhs,
            rhs,
        } => match (&lhs.node, &rhs.node) {
            (TermKind::Count(b), _) => Ok(scale_of(cx, rhs)?.map(|s| (&**b, s))),
            (_, TermKind::Count(b)) => Ok(scale_of(cx, lhs)?.map(|s| (&**b, s))),
            _ => Ok(None),
        },
        _ => Ok(None),
    }
}

/// `count(x: SRC ...) op limit` (or the limit first): a count against an integer or a knob, or
/// against another count, either side optionally scaled by a number or numeric knob.
fn count_cmp(cx: &mut Cx, op: ast::CmpOp, lhs: &Term, rhs: &Term) -> Result<Cond, LowerError> {
    if let (Some((lb, ls)), Some((rb, rs))) = (count_side(cx, lhs)?, count_side(cx, rhs)?) {
        let side = |cx: &mut Cx, b: &Binding, scale| -> Result<CountSideC, LowerError> {
            let (kind, cond) = scoped(cx, b)?;
            Ok(CountSideC {
                var: b.name.text.clone(),
                kind,
                cond: Box::new(cond),
                scale,
            })
        };
        let lhs = side(cx, lb, ls)?;
        let rhs = side(cx, rb, rs)?;
        return Ok(Cond::CountPair {
            lhs,
            op: cmp_op(op),
            rhs,
        });
    }
    let (binding, other, op) = match (&lhs.node, &rhs.node) {
        (TermKind::Count(b), _) => (b, rhs, op),
        (_, TermKind::Count(b)) => (
            b,
            lhs,
            match op {
                ast::CmpOp::Lt => ast::CmpOp::Gt,
                ast::CmpOp::Le => ast::CmpOp::Ge,
                ast::CmpOp::Gt => ast::CmpOp::Lt,
                ast::CmpOp::Ge => ast::CmpOp::Le,
                same => same,
            },
        ),
        _ => return unsupported("a scaled count compared with a non-count", lhs.span),
    };
    let limit = match &other.node {
        TermKind::Literal(l) => match &l.node {
            LiteralKind::Int(i) => u64::try_from(*i).map(Lim::Int).ok(),
            _ => None,
        },
        TermKind::Knob(w) => match knob_of(cx, w)? {
            KnobVal::Int(i) => u64::try_from(*i).ok().map(|d| Lim::Knob(w.text.clone(), d)),
            _ => None,
        },
        _ => None,
    };
    let Some(limit) = limit else {
        return unsupported("a count compared with this term", other.span);
    };
    let (kind, cond) = scoped(cx, binding)?;
    Ok(Cond::CountCmp {
        var: binding.name.text.clone(),
        kind,
        cond: Box::new(cond),
        op: cmp_op(op),
        limit,
    })
}

fn cmp_op(op: ast::CmpOp) -> CmpOp {
    match op {
        ast::CmpOp::Eq => CmpOp::Eq,
        ast::CmpOp::Ne => CmpOp::Ne,
        ast::CmpOp::Lt => CmpOp::Lt,
        ast::CmpOp::Le => CmpOp::Le,
        ast::CmpOp::Gt => CmpOp::Gt,
        ast::CmpOp::Ge => CmpOp::Ge,
    }
}

/// `subject is WORD`: only words the executor evaluates are lowered.
fn is_cond(cx: &Cx, subject: &Term, test: &ast::Word) -> Result<Cond, LowerError> {
    let subject_opd = operand(cx, subject)?;
    let on_field = matches!(subject_opd, Opd::Field(..));
    if !crate::exec::is_test_word(&test.text, on_field) {
        return unsupported("an `is` word the executor does not evaluate", test.span);
    }
    Ok(Cond::Is {
        subject: subject_opd,
        test: test.text.clone(),
    })
}

/// `subject under term`: a segment-wise prefix test between two operands.
fn under_cond(cx: &Cx, subject: &Term, rel: &ast::Rel) -> Result<Cond, LowerError> {
    let RelKind::Under { term } = &rel.node else {
        unreachable!("caller matched Under")
    };
    Ok(Cond::Under {
        subject: operand(cx, subject)?,
        prefix: operand(cx, term)?,
    })
}

/// `lhs in rhs` over a list literal, a list-of-strings knob or a range: an `or` of equalities,
/// or the two bounds of a range. A vocabulary knob is not lowered here.
fn in_cond(cx: &Cx, lhs: &Term, rhs: &Term) -> Result<Cond, LowerError> {
    let subject = operand(cx, lhs)?;
    let eq = |v: Opd| Cond::Cmp {
        lhs: subject.clone(),
        op: CmpOp::Eq,
        rhs: v,
    };
    let items: Vec<Opd> = match &rhs.node {
        TermKind::Range { lo, hi } => {
            return Ok(Cond::And(vec![
                Cond::Cmp {
                    lhs: subject.clone(),
                    op: CmpOp::Ge,
                    rhs: operand(cx, lo)?,
                },
                Cond::Cmp {
                    lhs: subject.clone(),
                    op: CmpOp::Le,
                    rhs: operand(cx, hi)?,
                },
            ]));
        }
        TermKind::Knob(w) => match knob_of(cx, w)? {
            KnobVal::Strs(v) => v.iter().cloned().map(Opd::Str).collect(),
            KnobVal::Vocab(classes) => {
                return match subject {
                    Opd::Var(var) => Ok(Cond::InVocab {
                        var,
                        classes: classes.clone(),
                    }),
                    _ => unsupported("a vocabulary test on anything but a bound node", lhs.span),
                };
            }
            _ => return unsupported("a knob that is not a list of strings after `in`", w.span),
        },
        TermKind::Literal(l) => match &l.node {
            LiteralKind::List(items) => items.iter().map(literal).collect::<Result<_, _>>()?,
            _ => return unsupported("a non-list after `in`", rhs.span),
        },
        _ => return unsupported("this collection after `in`", rhs.span),
    };
    if items.is_empty() {
        return unsupported("an empty list after `in`", rhs.span);
    }
    let mut alts: Vec<Cond> = items.into_iter().map(eq).collect();
    Ok(if alts.len() == 1 {
        alts.remove(0)
    } else {
        Cond::Or(alts)
    })
}

/// The default a knob declaration carries, in the form the lowering reads.
fn knob_value(l: &ast::Literal) -> Result<KnobVal, LowerError> {
    Ok(match &l.node {
        LiteralKind::Int(i) => KnobVal::Int(
            i64::try_from(*i).or_else(|_| unsupported("an integer beyond 64 bits", l.span))?,
        ),
        LiteralKind::Bool(b) => KnobVal::Bool(*b),
        LiteralKind::Str(s) => KnobVal::Str(s.clone()),
        LiteralKind::Regex(r) => KnobVal::Regex(regex_text(r)),
        LiteralKind::List(items) => {
            let strs: Vec<String> = items
                .iter()
                .filter_map(|i| match &i.node {
                    LiteralKind::Str(s) => Some(s.clone()),
                    _ => None,
                })
                .collect();
            if strs.len() == items.len() {
                KnobVal::Strs(strs)
            } else {
                KnobVal::Other
            }
        }
        LiteralKind::Call { name, args } if name.text == "vocab" => {
            let classes: Vec<String> = args
                .iter()
                .filter_map(|a| match &a.node {
                    LiteralKind::Str(s) => Some(s.clone()),
                    _ => None,
                })
                .collect();
            if classes.len() == args.len() {
                KnobVal::Vocab(classes)
            } else {
                KnobVal::Other
            }
        }
        LiteralKind::Decimal(text) => KnobVal::Dec(decimal(text, l.span)?),
        LiteralKind::Call { .. } => KnobVal::Other,
    })
}

/// The declared default of `knob.NAME`.
fn knob_of<'a>(cx: &'a Cx, w: &ast::Word) -> Result<&'a KnobVal, LowerError> {
    cx.knobs
        .iter()
        .find(|(n, _)| *n == w.text)
        .map(|(_, v)| v)
        .ok_or(LowerError::UnknownVar {
            name: format!("knob.{}", w.text),
            span: w.span,
        })
}

fn regex_text(r: &crate::grl::Regex) -> String {
    let mut flags = String::new();
    if r.ignore_case {
        flags.push('i');
    }
    if r.multi_line {
        flags.push('m');
    }
    if flags.is_empty() {
        r.pattern.clone()
    } else {
        format!("(?{flags}){}", r.pattern)
    }
}

/// The side relation a glob set names (`lease.globs`, `config.lease.shared_files`) with the
/// column that holds the globs: the catalog's only column for a fixed relation, `value` for a
/// `config.` list.
fn side_set(t: &Term) -> Option<(Read, String, String)> {
    let TermKind::Path(p) = &t.node else {
        return None;
    };
    let words: Vec<&str> = p.segments.iter().map(|s| s.text.as_str()).collect();
    let table = words.join(".");
    match words.first().copied()? {
        "config" if words.len() >= 3 => Some((Read::Config, table, "value".to_owned())),
        "lease" | "diff" | "model" => {
            let rel = crate::catalog::side_relation(&table)?;
            let (col, _) = rel.columns.first()?;
            let need = match words[0] {
                "lease" => Read::Lease,
                "diff" => Read::Diff,
                _ => Read::Model,
            };
            Some((need, table, (*col).to_owned()))
        }
        _ => None,
    }
}

/// The tested value of a glob match: a variable bound to a side-relation row stands for the
/// first column of its relation (`p` in `find p: diff.changed` is its path).
fn glob_subject(cx: &Cx, t: &Term) -> Result<Opd, LowerError> {
    if let Some(name) = var_name(cx, t)?
        && let Some((_, table)) = cx.side_vars.iter().find(|(v, _)| *v == name)
    {
        let rel = crate::catalog::side_relation(table);
        return match rel.and_then(|r| r.columns.first()) {
            Some((col, _)) => Ok(Opd::Field(name, (*col).to_owned())),
            None => unsupported("a config row as a glob subject", t.span),
        };
    }
    operand(cx, t)
}

/// Whether `t` is a field path of a bound variable (`row.from`), a glob read at run time.
fn is_field_path(cx: &Cx, t: &Term) -> bool {
    matches!(&t.node, TermKind::Path(p) if p.segments.len() >= 2 && cx.scope.contains(&p.segments[0].text))
}

fn glob_literals(cx: &Cx, t: &Term) -> Result<Vec<String>, LowerError> {
    match &t.node {
        TermKind::Knob(w) => match knob_of(cx, w)? {
            KnobVal::Str(s) => Ok(vec![s.clone()]),
            KnobVal::Strs(v) if !v.is_empty() => Ok(v.clone()),
            _ => unsupported("a knob that is not a glob or a list of globs", w.span),
        },
        TermKind::Literal(l) => match &l.node {
            LiteralKind::Str(s) => Ok(vec![s.clone()]),
            LiteralKind::List(items) if !items.is_empty() => items
                .iter()
                .map(|i| match &i.node {
                    LiteralKind::Str(s) => Ok(s.clone()),
                    _ => unsupported("a non-string glob", i.span),
                })
                .collect(),
            _ => unsupported("a non-string glob", t.span),
        },
        _ => unsupported("a glob that is not a literal", t.span),
    }
}

/// The variable a term names, when it is a one-segment path of a variable in scope.
fn var_name(cx: &Cx, t: &Term) -> Result<Option<String>, LowerError> {
    match &t.node {
        TermKind::Path(p) if p.segments.len() == 1 => {
            let w = &p.segments[0];
            require_bound(cx, w)?;
            Ok(Some(w.text.clone()))
        }
        _ => Ok(None),
    }
}

fn literal(l: &ast::Literal) -> Result<Opd, LowerError> {
    match &l.node {
        LiteralKind::Int(i) => i64::try_from(*i)
            .map(Opd::Int)
            .or_else(|_| unsupported("an integer beyond 64 bits", l.span)),
        LiteralKind::Str(s) => Ok(Opd::Str(s.clone())),
        LiteralKind::Bool(b) => Ok(Opd::Bool(*b)),
        _ => unsupported("this literal as an operand", l.span),
    }
}

fn operand(cx: &Cx, t: &Term) -> Result<Opd, LowerError> {
    match &t.node {
        TermKind::Literal(l) => literal(l),
        TermKind::Path(p) => {
            require_bound(cx, &p.segments[0])?;
            match p.segments.as_slice() {
                [v] => Ok(Opd::Var(v.text.clone())),
                [v, f] => Ok(Opd::Field(v.text.clone(), f.text.clone())),
                [v, rest @ ..] => {
                    let path: Vec<&str> = rest.iter().map(|s| s.text.as_str()).collect();
                    Ok(Opd::Field(v.text.clone(), path.join(".")))
                }
                [] => unsupported("an empty path", p.span),
            }
        }
        TermKind::Knob(w) => match knob_of(cx, w)? {
            KnobVal::Int(i) => Ok(Opd::Int(*i)),
            KnobVal::Bool(b) => Ok(Opd::Bool(*b)),
            KnobVal::Str(s) => Ok(Opd::Str(s.clone())),
            _ => unsupported("a knob of this type as a value", w.span),
        },
        TermKind::Call(c) => call_operand(cx, c),
        _ => unsupported("this term", t.span),
    }
}

/// A builtin function call as a value: `slug(s)` or `resolve(path, from)` over call-free
/// arguments (a nested call is refused).
fn call_operand(cx: &Cx, call: &ast::Call) -> Result<Opd, LowerError> {
    let args = call
        .args
        .iter()
        .map(|a| match operand(cx, a)? {
            Opd::Slug(_) | Opd::Resolve(..) => unsupported("a call nested in a call", a.span),
            leaf => Ok(leaf),
        })
        .collect::<Result<Vec<_>, LowerError>>()?;
    match (call.name.text.as_str(), <[Opd; 1]>::try_from(args.clone())) {
        ("slug", Ok([s])) => return Ok(Opd::Slug(Box::new(s))),
        ("slug", Err(_)) => return unsupported("slug without exactly one argument", call.span),
        _ => {}
    }
    match (call.name.text.as_str(), <[Opd; 2]>::try_from(args)) {
        ("resolve", Ok([p, f])) => Ok(Opd::Resolve(Box::new(p), Box::new(f))),
        ("resolve", Err(_)) => unsupported("resolve without exactly two arguments", call.span),
        _ => unsupported("this function as a value", call.span),
    }
}

/// The object of a relation as a variable: a variable in scope, or an anonymous kind shape that
/// becomes `some _n: KIND where ...` around the relation.
fn with_object(
    cx: &mut Cx,
    object: &Object,
    build: impl FnOnce(String) -> Cond,
) -> Result<Cond, LowerError> {
    let (kind, fields): (String, Vec<(String, Opd)>) = match object {
        Object::Term(t) => match &t.node {
            TermKind::Path(p) if p.segments.len() == 1 => {
                let w = &p.segments[0];
                if cx.scope.contains(&w.text) {
                    return Ok(build(w.text.clone()));
                }
                (w.text.clone(), Vec::new())
            }
            TermKind::Path(p) if p.segments.len() > 1 => {
                // A field path (`s.unit`) is a node-valued field: bind the node it names.
                let Opd::Field(v, f) = operand(cx, t)? else {
                    return unsupported("this relation object", t.span);
                };
                let var = format!("_{}", cx.fresh);
                cx.fresh += 1;
                return Ok(Cond::Quant {
                    quant: Quant::Some,
                    var: var.clone(),
                    kind: ANY_NODES.to_owned(),
                    cond: Box::new(Cond::And(vec![
                        Cond::Cmp {
                            lhs: Opd::Field(v, f),
                            op: CmpOp::Eq,
                            rhs: Opd::Var(var.clone()),
                        },
                        build(var),
                    ])),
                });
            }
            _ => return unsupported("this relation object", t.span),
        },
        Object::Shape(s) => match &s.node {
            ShapeKind::Kind { kind, fields, arg } => {
                (kind.text.clone(), kind_fields(fields, arg.as_ref())?)
            }
            _ => return unsupported("a snippet or alternatives as a relation object", s.span),
        },
    };
    let var = format!("_{}", cx.fresh);
    cx.fresh += 1;
    let mut conds = vec![build(var.clone())];
    for (f, v) in fields {
        conds.push(field_cond(&kind, &var, &f, v));
    }
    Ok(Cond::Quant {
        quant: Quant::Some,
        var,
        kind,
        cond: Box::new(if conds.len() == 1 {
            conds.remove(0)
        } else {
            Cond::And(conds)
        }),
    })
}

fn rel_cond(cx: &mut Cx, subject: &str, r: &ast::Rel) -> Result<Cond, LowerError> {
    let s = subject.to_owned();
    match &r.node {
        RelKind::Containment {
            directly,
            dir,
            object,
        } => {
            let (directly, dir) = (*directly, *dir);
            with_object(cx, object, move |o| match dir {
                ast::Containment::Inside => Cond::Inside {
                    sub: s,
                    sup: o,
                    direct: directly,
                },
                ast::Containment::Has => Cond::Inside {
                    sub: o,
                    sup: s,
                    direct: directly,
                },
            })
        }
        RelKind::Position { position, object } => {
            let pos = match position {
                ast::Position::Before => Position::Before,
                ast::Position::After => Position::After,
                ast::Position::Adjoins => Position::Adjoins,
            };
            with_object(cx, object, move |o| Cond::Order { a: s, b: o, pos })
        }
        RelKind::Verb {
            certainty,
            verb,
            object,
        } => {
            let certainty = match certainty {
                None => Certainty::Default,
                Some(ast::Certainty::Certainly) => Certainty::Certainly,
                Some(ast::Certainty::Possibly) => Certainty::Possibly,
            };
            let verb = verb.text.clone();
            with_object(cx, object, move |o| Cond::Verb {
                subject: s,
                object: o,
                verb,
                certainty,
            })
        }
        RelKind::InUnit { object } => {
            with_object(cx, object, move |o| Cond::InUnit { sub: s, unit: o })
        }
        RelKind::Under { .. } => Err(LowerError::Internal {
            what: "under is lowered with its subject term",
        }),
        RelKind::Reaches {
            target,
            via,
            within,
        } => {
            let [verb] = via.as_slice() else {
                return unsupported("`reaches` over more than one verb", r.span);
            };
            let Some(within) = within else {
                return unsupported("`reaches` without `within`", r.span);
            };
            let (within, via) = (within_bound(cx, within)?, verb.text.clone());
            with_object(cx, target, move |o| Cond::Reaches {
                from: s,
                to: o,
                via,
                within,
            })
        }
    }
}

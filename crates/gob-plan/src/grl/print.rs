//! The GRL printer: a syntax tree back to canonical text (grl-spec.md section 11, `rule fmt`).
//!
//! [`print()`] is the one canonical layout: two-space indentation, headers, then clauses (one per
//! line), then examples, then `explain`, with a blank line between the groups and between rules.
//! It is a fixed point of the parser: for every tree the parser can produce,
//! `parse(print(t)) = t` up to source ranges, and `print(parse(print(t))) = print(t)`
//! (build-test-ci.md section 6, D98; the harness is `tests/print_stability.rs`).
//!
//! Canonical choices, each fixed here and nowhere else:
//!
//! - a kind pattern writes its fields bare, `element(tag = "img")`; the dotted form the parser also
//!   accepts is never printed (grl-spec.md section 5);
//! - `lang "*"`, accepted with a warning, prints as `lang *`;
//! - parentheses appear only where precedence needs them (`or` below `and` below `not`), and a
//!   quantifier nested in a connective is always parenthesised because its `where` runs to the end;
//! - comments are not part of the tree and are not printed (the parser drops them).
//!
//! Preconditions the parser itself guarantees and the printer relies on: terms carry no grouping
//! (a `Binary` right operand is never another `Binary`, a `Mul` left operand is never an `Add`),
//! and a `where` clause never directly follows a `find`, `some` or `no` clause that has no
//! filter (the parser would read it as that clause's filter).

use std::fmt::Write as _;

use super::ast::{
    Applicability, ApplicabilityKind, ArithOp, Binding, BlockLit, Call, Cast, CastKind, Certainty,
    Clause, ClauseKind, CmpOp, Cond, CondKind, Containment, Def, Example, ExampleBody, ExpectKind,
    Explain, File, Fix, FixKind, Header, HeaderKind, Input, InputKind, Knob, LangSet, Literal,
    LiteralKind, Message, MessagePart, Object, Path, Placement, Position, Quant, Rel, RelKind,
    Rollup, Rule, Scope, Severity, Shape, ShapeKind, Source, StrLit, Term, TermKind, TypeKind,
    TypeRef, Word,
};
use super::token::{Regex, Snippet};

/// One indentation step.
const STEP: &str = "  ";

// frob:ticket 01M47YJF46HM8MA5PVWNH92W1H
/// Print a whole file in canonical form; every rule ends with `}` and a newline.
pub fn print(file: &File) -> String {
    let mut out = String::new();
    for (i, rule) in file.rules.iter().enumerate() {
        if i > 0 {
            out.push('\n');
        }
        rule_text(&mut out, rule);
    }
    tracing::debug!(
        rules = file.rules.len(),
        bytes = out.len(),
        "printed GRL file"
    );
    out
}

// frob:ticket 01M47YJF46HM8MA5PVWNH92W1H
/// Print one rule in canonical form (the same text [`print()`] writes for it).
pub fn print_rule(rule: &Rule) -> String {
    let mut out = String::new();
    rule_text(&mut out, rule);
    out
}

fn rule_text(out: &mut String, rule: &Rule) {
    let _ = writeln!(out, "rule {} {} {{", rule.id.text, plain(&rule.slug.value));
    let mut groups: Vec<String> = Vec::new();
    if !rule.headers.is_empty() {
        groups.push(lines(rule.headers.iter().map(header)));
    }
    if !rule.clauses.is_empty() {
        groups.push(clauses_text(&rule.clauses));
    }
    for example in &rule.examples {
        groups.push(format!("{STEP}{}\n", example_text(example)));
    }
    if let Some(explain) = &rule.explain {
        groups.push(format!("{STEP}{}\n", explain_text(explain)));
    }
    out.push_str(&groups.join("\n"));
    out.push_str("}\n");
}

/// The clauses, one per line; a clause that a following `where` line would be read into is guarded.
fn clauses_text(clauses: &[Clause]) -> String {
    let followed_by_where = |i: usize| {
        clauses
            .get(i + 1)
            .is_some_and(|n| matches!(n.node, ClauseKind::Where(_)))
    };
    lines(
        clauses
            .iter()
            .enumerate()
            .map(|(i, c)| clause(c, followed_by_where(i))),
    )
}

/// Each item indented one step on its own line.
fn lines(items: impl Iterator<Item = String>) -> String {
    items.fold(String::new(), |mut acc, item| {
        let _ = writeln!(acc, "{STEP}{item}");
        acc
    })
}

// ---- headers ----

fn header(h: &Header) -> String {
    match &h.node {
        HeaderKind::Lang(l) => format!("lang {}", lang_set(l)),
        HeaderKind::Polarity(p) => format!("polarity {}", p.symbol()),
        HeaderKind::Severity(s) => format!(
            "severity {}",
            match s {
                Severity::Error => "error",
                Severity::Warn => "warn",
                Severity::Advisory => "advisory",
            }
        ),
        HeaderKind::Scope(s) => format!(
            "scope {}",
            match s {
                Scope::File => "file",
                Scope::Repo => "repo",
            }
        ),
        HeaderKind::MustMeasure => "must_measure".to_owned(),
        HeaderKind::Needs(names) => format!("needs {}", words(names)),
        HeaderKind::Rollup(r) => format!(
            "rollup {}",
            match r {
                Rollup::File => "file",
                Rollup::Directory => "directory",
                Rollup::Unit => "unit",
            }
        ),
        HeaderKind::Knob(k) => knob(k),
    }
}

fn lang_set(l: &LangSet) -> String {
    match l {
        LangSet::Any { .. } => "*".to_owned(),
        LangSet::Nothing => "-".to_owned(),
        LangSet::One(w) => w.text.clone(),
        LangSet::List(ws) => format!("[{}]", words(ws)),
    }
}

fn words(ws: &[Word]) -> String {
    join(ws.iter().map(|w| w.text.as_str()), ", ")
}

fn knob(k: &Knob) -> String {
    format!(
        "knob {}: {} = {} {}",
        k.name.text,
        type_ref(&k.ty),
        literal(&k.default),
        plain(&k.doc.value)
    )
}

fn type_ref(t: &TypeRef) -> String {
    match &t.node {
        TypeKind::Int => "int".to_owned(),
        TypeKind::Float => "float".to_owned(),
        TypeKind::String => "string".to_owned(),
        TypeKind::Bool => "bool".to_owned(),
        TypeKind::Glob => "glob".to_owned(),
        TypeKind::Regex => "regex".to_owned(),
        TypeKind::Vocab => "vocab".to_owned(),
        TypeKind::List(inner) => format!("list<{}>", type_ref(inner)),
    }
}

// ---- clauses ----

/// One clause's text; `guard` is set when a `where` clause follows it on the next line.
fn clause(c: &Clause, guard: bool) -> String {
    match &c.node {
        ClauseKind::Find(b) => format!("find {}", binding(b, guard)),
        ClauseKind::Where(cd) => format!("where {}", tail_cond(cd, guard)),
        ClauseKind::Quant { quant, binding: b } => {
            format!("{} {}", quant_word(*quant), binding(b, guard))
        }
        ClauseKind::Def(d) => def(d, guard),
        ClauseKind::Report(r) => {
            let mut s = format!("report {} {}", r.target.text, message(&r.message));
            if let Some(when) = &r.when {
                let _ = write!(s, " when {}", tail_cond(when, guard));
            }
            s
        }
        ClauseKind::Note(n) => format!("note {} {}", n.target.text, message(&n.message)),
        ClauseKind::Fix(f) => fix(f),
        ClauseKind::Unresolved(u) => format!(
            "unresolved when {} because {}",
            cond(&u.when, 0),
            message(&u.because)
        ),
    }
}

fn def(d: &Def, guard: bool) -> String {
    format!(
        "def {}({}) = {}",
        d.name.text,
        words(&d.params),
        tail_cond(&d.body, guard)
    )
}

fn fix(f: &Fix) -> String {
    let mut s = String::from("fix ");
    match &f.kind {
        FixKind::Replace {
            placement,
            target,
            with,
            ..
        } => {
            match placement {
                Some(Placement::Before) => s.push_str("before "),
                Some(Placement::After) => s.push_str("after "),
                None => {}
            }
            let _ = write!(s, "{} -> {}", target.text, snippet(with));
        }
        FixKind::Delete { target } => {
            let _ = write!(s, "delete {}", target.text);
        }
        FixKind::Host { name, args } => {
            let _ = write!(s, "host {}({})", name.text, terms(args));
        }
        FixKind::Manual { message: m } => {
            let _ = write!(s, "manual {}", message(m));
        }
    }
    if let Some(a) = &f.applicability {
        let _ = write!(s, " [{}]", applicability(a));
    }
    s
}

fn applicability(a: &Applicability) -> &'static str {
    match a.kind {
        ApplicabilityKind::Machine => "machine",
        ApplicabilityKind::MaybeIncorrect => "maybe-incorrect",
        ApplicabilityKind::HasPlaceholders => "has-placeholders",
    }
}

// ---- bindings, sources, shapes ----

/// A binding; `guard` parenthesises a filter that would otherwise read a following `where` line.
fn binding(b: &Binding, guard: bool) -> String {
    let mut s = format!("{}: {}", b.name.text, source(&b.source));
    for r in &b.rels {
        let _ = write!(s, " {}", rel(r));
    }
    if let Some(f) = &b.filter {
        let _ = write!(s, " where {}", tail_cond(f, guard));
    }
    s
}

fn source(src: &Source) -> String {
    match src {
        Source::Shape(s) => shape(s),
        Source::Side(p) => path(p),
    }
}

fn shape(s: &Shape) -> String {
    match &s.node {
        ShapeKind::Kind { kind, fields, arg } => {
            let mut out = kind.text.clone();
            if !fields.is_empty() {
                // The bare field form is canonical; the parser also accepts `.name`.
                let list: Vec<String> = fields
                    .iter()
                    .map(|f| format!("{} = {}", f.name.text, literal(&f.value)))
                    .collect();
                let list = list.join(", ");
                let _ = write!(out, "({list})");
            } else if let Some(a) = arg {
                let _ = write!(out, " {}", plain(&a.value));
            }
            out
        }
        ShapeKind::Snippet { snippet: sn, cast } => {
            let mut out = snippet(sn);
            if let Some(c) = cast {
                let _ = write!(out, " as {}", cast_word(c));
            }
            out
        }
        ShapeKind::Alt(alts) => {
            let parts: Vec<String> = alts.iter().map(shape).collect();
            format!("({})", parts.join(" | "))
        }
    }
}

fn cast_word(c: &Cast) -> &str {
    match &c.node {
        CastKind::Roles => "roles",
        CastKind::Kind(w) => &w.text,
    }
}

/// A snippet exactly as lexed: language tag, delimiter, raw text.
fn snippet(s: &Snippet) -> String {
    let tick = "`".repeat(usize::from(s.ticks));
    let lang = s.lang.as_ref().map_or("", |l| l.name.as_str());
    format!("{lang}{tick}{}{tick}", s.text)
}

// ---- relations ----

fn rel(r: &Rel) -> String {
    match &r.node {
        RelKind::Containment {
            directly,
            dir,
            object: o,
        } => {
            let word = match dir {
                Containment::Inside => "inside",
                Containment::Has => "has",
            };
            let directly = if *directly { "directly " } else { "" };
            format!("{directly}{word} {}", object(o))
        }
        RelKind::InUnit { object: o } => format!("in unit {}", object(o)),
        RelKind::Under { term: t } => format!("under {}", term(t)),
        RelKind::Position {
            position,
            object: o,
        } => {
            let word = match position {
                Position::Before => "before",
                Position::After => "after",
                Position::Adjoins => "adjoins",
            };
            format!("{word} {}", object(o))
        }
        RelKind::Verb {
            certainty,
            verb,
            object: o,
        } => {
            let c = match certainty {
                Some(Certainty::Certainly) => "certainly ",
                Some(Certainty::Possibly) => "possibly ",
                None => "",
            };
            format!("{c}{} {}", verb.text, object(o))
        }
        RelKind::Reaches {
            target,
            via,
            within,
        } => {
            let mut s = format!("reaches {} via {}", object(target), words(via));
            if let Some(w) = within {
                let _ = write!(s, " within {}", term(w));
            }
            s
        }
    }
}

fn object(o: &Object) -> String {
    match o {
        Object::Term(t) => term(t),
        Object::Shape(s) => shape(s),
    }
}

// ---- conditions ----

/// Binding strength of the three connective levels: `or` 0, `and` 1, unary 2.
fn cond(c: &Cond, level: u8) -> String {
    match &c.node {
        CondKind::Or(parts) => wrap(level > 0, &sep(parts, " or ", 1)),
        CondKind::And(parts) => wrap(level > 1, &sep(parts, " and ", 2)),
        CondKind::Not(inner) => format!("not {}", cond(inner, 2)),
        CondKind::Any(parts) => {
            // A non-last item ending in a bare `via` verb list would swallow the comma that
            // separates it from the next item, so it is parenthesised.
            let last = parts.len().saturating_sub(1);
            let items: Vec<String> = parts
                .iter()
                .enumerate()
                .map(|(i, p)| wrap(i < last && ends_in_via_list(p), &cond(p, 0)))
                .collect();
            format!("any {{ {} }}", items.join(", "))
        }
        CondKind::Quant { quant, binding: b } => wrap(
            level > 0,
            &format!("{} {}", quant_word(*quant), binding(b, false)),
        ),
        CondKind::Rel { subject, rel: r } => format!("{} {}", term(subject), rel(r)),
        CondKind::Cmp { op, lhs, rhs } => {
            format!("{} {} {}", term(lhs), cmp_op(*op), term(rhs))
        }
        CondKind::RegexMatch { lhs, rhs } => format!("{} ~ {}", term(lhs), term(rhs)),
        CondKind::GlobMatch { lhs, rhs } => format!("{} matches {}", term(lhs), term(rhs)),
        CondKind::In { lhs, rhs } => format!("{} in {}", term(lhs), term(rhs)),
        CondKind::Is { subject, test } => format!("{} is {}", term(subject), test.text),
        CondKind::IsSnippet {
            subject,
            snippet: s,
            roles,
        } => {
            let tail = if *roles { " as roles" } else { "" };
            format!("{} is {}{tail}", term(subject), snippet(s))
        }
        CondKind::HasAttr { subject, attr } => {
            format!("{} has attr {}", term(subject), plain(&attr.value))
        }
        CondKind::DefCall(call) => call_text(call),
        CondKind::Exists(t) => format!("exists {}", term(t)),
        CondKind::Flag(t) => term(t),
    }
}

/// True when the condition's text ends in `reaches ... via VERBS` with no `within` after it.
fn ends_in_via_list(c: &Cond) -> bool {
    let rel_open = |r: &Rel| matches!(&r.node, RelKind::Reaches { within: None, .. });
    match &c.node {
        CondKind::Rel { rel, .. } => rel_open(rel),
        CondKind::Quant { binding: b, .. } => match &b.filter {
            Some(f) => ends_in_via_list(f),
            None => b.rels.last().is_some_and(rel_open),
        },
        CondKind::Or(parts) | CondKind::And(parts) => parts.last().is_some_and(ends_in_via_list),
        CondKind::Not(inner) => ends_in_via_list(inner),
        _ => false,
    }
}

/// A condition that ends a clause: parenthesised when `guard` is set and it ends in a binding
/// without a filter, whose `where` would otherwise read the next clause's `where` as its own.
fn tail_cond(c: &Cond, guard: bool) -> String {
    wrap(guard && ends_in_open_binding(c), &cond(c, 0))
}

/// True when the condition's text ends in a `some`/`no` binding that could still take a `where`.
fn ends_in_open_binding(c: &Cond) -> bool {
    match &c.node {
        CondKind::Quant { binding: b, .. } => b.filter.as_ref().is_none_or(ends_in_open_binding),
        CondKind::Or(parts) | CondKind::And(parts) => {
            parts.last().is_some_and(ends_in_open_binding)
        }
        CondKind::Not(inner) => ends_in_open_binding(inner),
        _ => false,
    }
}

fn sep(parts: &[Cond], by: &str, level: u8) -> String {
    let items: Vec<String> = parts.iter().map(|p| cond(p, level)).collect();
    items.join(by)
}

fn wrap(parens: bool, s: &str) -> String {
    if parens {
        format!("({s})")
    } else {
        s.to_owned()
    }
}

fn quant_word(q: Quant) -> &'static str {
    match q {
        Quant::Some => "some",
        Quant::No => "no",
    }
}

fn cmp_op(op: CmpOp) -> &'static str {
    match op {
        CmpOp::Eq => "==",
        CmpOp::Ne => "!=",
        CmpOp::Lt => "<",
        CmpOp::Le => "<=",
        CmpOp::Gt => ">",
        CmpOp::Ge => ">=",
    }
}

// ---- terms and literals ----

fn term(t: &Term) -> String {
    match &t.node {
        TermKind::Path(p) => path(p),
        TermKind::Literal(l) => literal(l),
        TermKind::Knob(w) => format!("knob.{}", w.text),
        TermKind::Count(b) => format!("count({})", binding(b, false)),
        TermKind::Call(c) => call_text(c),
        TermKind::Binary { op, lhs, rhs } => {
            let op = match op {
                ArithOp::Add => "+",
                ArithOp::Sub => "-",
                ArithOp::Mul => "*",
            };
            format!("{} {op} {}", term(lhs), term(rhs))
        }
        TermKind::Range { lo, hi } => format!("{}..{}", term(lo), term(hi)),
    }
}

fn terms(ts: &[Term]) -> String {
    let items: Vec<String> = ts.iter().map(term).collect();
    items.join(", ")
}

fn call_text(c: &Call) -> String {
    format!("{}({})", c.name.text, terms(&c.args))
}

fn path(p: &Path) -> String {
    join(p.segments.iter().map(|w| w.text.as_str()), ".")
}

fn literal(l: &Literal) -> String {
    match &l.node {
        LiteralKind::Int(n) => n.to_string(),
        LiteralKind::Decimal(d) => d.clone(),
        LiteralKind::Str(s) => plain(s),
        LiteralKind::Regex(r) => regex(r),
        LiteralKind::Bool(b) => b.to_string(),
        LiteralKind::List(items) => {
            let parts: Vec<String> = items.iter().map(literal).collect();
            format!("[{}]", parts.join(", "))
        }
        LiteralKind::Call { name, args } => {
            let parts: Vec<String> = args.iter().map(literal).collect();
            format!("{}({})", name.text, parts.join(", "))
        }
    }
}

fn regex(r: &Regex) -> String {
    let i = if r.ignore_case { "i" } else { "" };
    let m = if r.multi_line { "m" } else { "" };
    format!("/{}/{i}{m}", r.pattern)
}

// ---- strings and blocks ----

/// A plain string: `"`, `\` and newline are escaped; braces are literal, and a backslash that
/// already guards a brace is kept as written (the parser keeps `\{` as two characters).
fn plain(value: &str) -> String {
    let mut out = String::with_capacity(value.len() + 2);
    out.push('"');
    let mut chars = value.chars().peekable();
    while let Some(c) = chars.next() {
        match c {
            '"' => out.push_str("\\\""),
            '\n' => out.push_str("\\n"),
            '\\' if matches!(chars.peek(), Some('{' | '}')) => out.push('\\'),
            '\\' => out.push_str("\\\\"),
            other => out.push(other),
        }
    }
    out.push('"');
    out
}

/// A message string: text with every brace escaped, `{path}` for interpolations.
fn message(m: &Message) -> String {
    let mut out = String::from("\"");
    for part in &m.parts {
        match part {
            MessagePart::Text { value, .. } => {
                for c in value.chars() {
                    match c {
                        '"' => out.push_str("\\\""),
                        '\\' => out.push_str("\\\\"),
                        '\n' => out.push_str("\\n"),
                        '{' => out.push_str("\\{"),
                        '}' => out.push_str("\\}"),
                        other => out.push(other),
                    }
                }
            }
            MessagePart::Interp { path: p, .. } => {
                let _ = write!(out, "{{{}}}", path(p));
            }
        }
    }
    out.push('"');
    out
}

/// A triple-quoted block whose lines sit at `indent` and whose closing quotes sit at `close`.
fn block(b: &BlockLit, indent: &str, close: &str) -> String {
    let mut out = String::from("\"\"\"\n");
    for line in b.value.split('\n') {
        if !line.is_empty() {
            out.push_str(indent);
            out.push_str(line);
        }
        out.push('\n');
    }
    out.push_str(close);
    out.push_str("\"\"\"");
    out
}

// ---- examples and explain ----

fn example_text(e: &Example) -> String {
    let mut s = format!("example {}", expect_word(e.expect.kind));
    if let Some(l) = &e.lang {
        let _ = write!(s, " {}", l.text);
    }
    if let Some(n) = &e.name {
        let _ = write!(s, " {}", plain(&n.value));
    }
    match &e.body {
        ExampleBody::Source(b) => {
            let _ = write!(s, " {}", block(b, "    ", STEP));
        }
        ExampleBody::Inputs(inputs) => {
            s.push_str(" {\n");
            for input in inputs {
                let _ = writeln!(s, "    {}", input_text(input));
            }
            let _ = write!(s, "{STEP}}}");
        }
    }
    s
}

fn expect_word(k: ExpectKind) -> &'static str {
    match k {
        ExpectKind::Fire => "fire",
        ExpectKind::Clean => "clean",
        ExpectKind::Unresolved => "unresolved",
        ExpectKind::NotApplicable => "notapplicable",
        ExpectKind::KnownGap => "known-gap",
    }
}

fn input_text(i: &Input) -> String {
    const BODY: &str = "      ";
    const CLOSE: &str = "    ";
    match &i.node {
        InputKind::File { path, text } => {
            format!("file {} {}", plain(&path.value), block(text, BODY, CLOSE))
        }
        InputKind::Config(b) => format!("config {}", block(b, BODY, CLOSE)),
        InputKind::Model(b) => format!("model {}", block(b, BODY, CLOSE)),
        InputKind::Diff(items) => format!("diff [{}]", str_list(items)),
        InputKind::Lease(items) => format!("lease [{}]", str_list(items)),
        InputKind::Expect(s) => format!("expect {}", plain(&s.value)),
        InputKind::Fixed(b) => format!("fixed {}", block(b, BODY, CLOSE)),
    }
}

fn str_list(items: &[StrLit]) -> String {
    let parts: Vec<String> = items.iter().map(|s| plain(&s.value)).collect();
    parts.join(", ")
}

fn explain_text(e: &Explain) -> String {
    format!("explain {}", block(&e.text, "    ", STEP))
}

fn join<'a>(items: impl Iterator<Item = &'a str>, by: &str) -> String {
    items.collect::<Vec<_>>().join(by)
}

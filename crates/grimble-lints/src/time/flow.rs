//! `TIME001` and `TIME002`: clock reads and naive/aware datetime mixes, by name-based def-use.
//!
//! One pass per function (or the module for scripts) classifies each datetime-valued binding as
//! naive (and in which zone) or aware, from the per-language callee vocabulary below, and reports
//! a local-zone or zone-less clock read whose value escapes display (`TIME001`) and a comparison
//! or subtraction between a naive and an aware value, or between naive values of two zones
//! (`TIME002`). Imports are resolved first, so `from datetime import datetime as dt` still reads
//! as `datetime.datetime`. A language without these roles is Unresolved in the caller.
//!
//! Known limits: Rust macro arguments are unparsed token trees, so a read written inside a macro
//! other than a display macro is not seen; a binding is classified by its last assignment in
//! source order, not by control flow.

// frob:ticket 01M44R5W4WJEXFM000S8KVQQN5

use std::collections::{BTreeMap, BTreeSet};

use tree_sitter::Node;

use super::Kind;
use crate::syntax::{Lang, children, idents, text};

/// A site before it is bound to a range.
#[derive(Debug, Clone, Copy)]
pub(super) struct Raw<'t> {
    pub kind: Kind,
    pub node: Node<'t>,
}

/// What a method or field access does to the value it is called on.
enum Climb<'t> {
    /// A plain field access: the value carries on.
    Field,
    /// The method converts the value to a fixed instant or zone.
    Converted,
    /// A call that carries the value on; the node is the call.
    Call(Node<'t>),
}

/// The zone a naive datetime was read in.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum Zone {
    Utc,
    Local,
    Unknown,
}

/// What a datetime-valued expression is.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum Class {
    Naive(Zone),
    Aware,
}

/// True when mixing `a` and `b` is a `TIME002` site.
fn mixes(a: Class, b: Class) -> bool {
    match (a, b) {
        (Class::Aware, Class::Naive(_)) | (Class::Naive(_), Class::Aware) => true,
        (Class::Naive(x), Class::Naive(y)) => x != y && x != Zone::Unknown && y != Zone::Unknown,
        (Class::Aware, Class::Aware) => false,
    }
}

/// Python callees (import-resolved) that read the clock in the local zone or without one.
const PY_NAIVE_READS: &[(&str, Zone)] = &[
    ("datetime.datetime.utcnow", Zone::Utc),
    ("datetime.utcnow", Zone::Utc),
    ("datetime.datetime.today", Zone::Local),
    ("datetime.today", Zone::Local),
    ("datetime.date.today", Zone::Local),
    ("date.today", Zone::Local),
    ("time.localtime", Zone::Local),
];
/// Python callees that read the clock and are naive only without a `tz` argument.
const PY_NOW: &[&str] = &["datetime.datetime.now", "datetime.now"];
/// Python naive constructors from a value: `(callee, tz position, tz keyword, zone when naive)`.
const PY_FROM: &[(&str, usize, &str, Zone)] = &[
    ("datetime.datetime.fromtimestamp", 1, "tz", Zone::Local),
    ("datetime.fromtimestamp", 1, "tz", Zone::Local),
    (
        "datetime.datetime.utcfromtimestamp",
        usize::MAX,
        "",
        Zone::Utc,
    ),
    ("datetime.utcfromtimestamp", usize::MAX, "", Zone::Utc),
    ("datetime.datetime", 7, "tzinfo", Zone::Unknown),
    ("datetime", 7, "tzinfo", Zone::Unknown),
];
/// Python parse callees: naive unless the format names `%z`.
const PY_PARSE: &[&str] = &["datetime.datetime.strptime", "datetime.strptime"];
/// Python methods that move a value into a named zone (when given an argument).
const PY_CONVERT: &[&str] = &["astimezone", "timestamp"];
/// Python callee names that only display their arguments.
const PY_DISPLAY: &[&str] = &[
    "print",
    "pprint",
    "echo",
    "debug",
    "info",
    "warning",
    "warn",
    "error",
    "exception",
    "critical",
    "fatal",
    "log",
];
/// Python callees whose result carries the argument's value on (still the same instant).
const PY_PASS: &[&str] = &["str", "repr", "format", "int", "float"];

/// Rust `(type, function)` pairs that read the clock in the local zone.
const RUST_LOCAL_READS: &[(&str, &str)] = &[
    ("Local", "now"),
    ("Local", "today"),
    ("Zoned", "now"),
    ("OffsetDateTime", "now_local"),
];
/// Rust `(type, function)` pairs that build an aware value.
const RUST_AWARE: &[(&str, &str)] = &[
    ("Utc", "now"),
    ("Local", "now"),
    ("Zoned", "now"),
    ("DateTime", "parse_from_rfc3339"),
    ("DateTime", "parse_from_rfc2822"),
    ("DateTime", "parse_from_str"),
];
/// Rust `(type, function)` pairs that build a naive value of no known zone.
const RUST_NAIVE: &[(&str, &str)] = &[
    ("NaiveDateTime", "parse_from_str"),
    ("NaiveDateTime", "from_timestamp"),
    ("NaiveDateTime", "from_timestamp_opt"),
    ("NaiveDateTime", "from_timestamp_millis"),
    ("NaiveDateTime", "new"),
];
/// Rust methods that move a clock value into a fixed instant or zone.
const RUST_CONVERT: &[&str] = &[
    "with_timezone",
    "to_utc",
    "timestamp",
    "timestamp_millis",
    "timestamp_micros",
    "timestamp_nanos_opt",
    "naive_utc",
    "and_utc",
    "in_tz",
    "intz",
    "with_time_zone",
];
/// Rust methods that give the value back unchanged inside a `Result` or `Option`.
const RUST_UNWRAP: &[&str] = &["unwrap", "expect", "unwrap_or_default", "unwrap_or_else"];
/// Rust display macros: their arguments are shown, not kept.
const RUST_DISPLAY: &[&str] = &[
    "println",
    "print",
    "eprintln",
    "eprint",
    "debug",
    "info",
    "warn",
    "error",
    "trace",
    "log",
    "dbg",
    "assert_eq",
    "assert_ne",
];
/// Rust macros whose result carries the argument's text on.
const RUST_PASS: &[&str] = &["format", "format_args"];
/// Rust constructors that wrap a value without changing it.
const RUST_WRAP: &[&str] = &["Some", "Ok", "Box::new", "Arc::new", "Rc::new"];

fn is_function(lang: Lang, n: Node<'_>) -> bool {
    match lang {
        Lang::Rust => n.kind() == "function_item",
        Lang::Python => n.kind() == "function_definition",
    }
}

/// Every site in `root`, one scope at a time.
pub(super) fn scan<'t>(lang: Lang, root: Node<'t>, src: &str) -> Vec<Raw<'t>> {
    let aliases = collect_aliases(lang, root, src);
    let mut scopes = vec![root];
    let mut stack = vec![root];
    while let Some(n) = stack.pop() {
        for c in children(n) {
            if is_function(lang, c) {
                scopes.push(c);
            }
            stack.push(c);
        }
    }
    let mut out = Vec::new();
    for scope in scopes {
        let mut f = Flow {
            lang,
            src,
            scope,
            aliases: &aliases,
            classes: BTreeMap::new(),
            out: Vec::new(),
        };
        f.visit(scope);
        tracing::trace!(kind = scope.kind(), sites = f.out.len(), "time flow scope");
        out.extend(f.out);
    }
    out
}

/// The import aliases of a file: local name to the dotted (or `::`) path it stands for.
fn collect_aliases(lang: Lang, root: Node<'_>, src: &str) -> BTreeMap<String, String> {
    let mut map = BTreeMap::new();
    let mut stack = vec![root];
    while let Some(n) = stack.pop() {
        match (lang, n.kind()) {
            (Lang::Rust, "use_as_clause") => {
                if let (Some(p), Some(a)) = (
                    n.child_by_field_name("path"),
                    n.child_by_field_name("alias"),
                ) {
                    map.insert(text(a, src).to_owned(), text(p, src).to_owned());
                }
            }
            (Lang::Python, "import_statement") => {
                for c in children(n)
                    .into_iter()
                    .filter(|c| c.kind() == "aliased_import")
                {
                    py_alias(c, "", src, &mut map);
                }
            }
            (Lang::Python, "import_from_statement") => {
                let module = n
                    .child_by_field_name("module_name")
                    .map_or("", |m| text(m, src));
                let mut cur = n.walk();
                for c in n.children_by_field_name("name", &mut cur) {
                    py_alias(c, module, src, &mut map);
                }
            }
            _ => {}
        }
        stack.extend(children(n));
    }
    map
}

/// Record one `name` or `name as alias` import under `module`.
fn py_alias(node: Node<'_>, module: &str, src: &str, map: &mut BTreeMap<String, String>) {
    let (name, alias) = if node.kind() == "aliased_import" {
        let Some(name) = node.child_by_field_name("name") else {
            return;
        };
        (
            text(name, src),
            node.child_by_field_name("alias").map(|a| text(a, src)),
        )
    } else {
        (text(node, src), None)
    };
    let full = if module.is_empty() {
        name.to_owned()
    } else {
        format!("{module}.{name}")
    };
    map.insert(alias.unwrap_or(name).to_owned(), full);
}

struct Flow<'t, 's, 'a> {
    lang: Lang,
    src: &'s str,
    scope: Node<'t>,
    aliases: &'a BTreeMap<String, String>,
    classes: BTreeMap<String, Class>,
    out: Vec<Raw<'t>>,
}

impl<'t, 's> Flow<'t, 's, '_> {
    fn visit(&mut self, node: Node<'t>) {
        if node != self.scope && is_function(self.lang, node) {
            return;
        }
        self.at(node);
        for c in children(node) {
            self.visit(c);
        }
    }

    fn flag(&mut self, kind: Kind, node: Node<'t>) {
        self.out.push(Raw { kind, node });
    }

    fn at(&mut self, node: Node<'t>) {
        match (self.lang, node.kind()) {
            (Lang::Rust, "let_declaration") => self.bind(node, "pattern", "value"),
            (Lang::Python, "assignment") => self.bind(node, "left", "right"),
            (Lang::Python, "typed_parameter" | "typed_default_parameter")
            | (Lang::Rust, "parameter") => self.param(node),
            (Lang::Rust, "call_expression") | (Lang::Python, "call") => self.read(node),
            (Lang::Rust, "binary_expression") | (Lang::Python, "binary_operator") => {
                let op = node
                    .child_by_field_name("operator")
                    .map_or("", |o| text(o, self.src));
                if matches!(op, "-" | "<" | ">" | "<=" | ">=" | "==" | "!=") {
                    self.mix(node, &Self::operands(node));
                }
            }
            (Lang::Python, "comparison_operator") => self.mix(node, &Self::operands(node)),
            _ => {}
        }
    }

    fn operands(node: Node<'t>) -> Vec<Node<'t>> {
        match node.kind() {
            "comparison_operator" => {
                let mut cur = node.walk();
                node.named_children(&mut cur)
                    .filter(|c| c.kind() != "comment")
                    .collect()
            }
            _ => [
                node.child_by_field_name("left"),
                node.child_by_field_name("right"),
            ]
            .into_iter()
            .flatten()
            .collect(),
        }
    }

    /// Flag the first adjacent operand pair that mixes naive and aware.
    fn mix(&mut self, node: Node<'t>, operands: &[Node<'t>]) {
        let classes: Vec<Option<Class>> = operands.iter().map(|o| self.class_of(*o)).collect();
        if classes
            .windows(2)
            .any(|w| matches!((w[0], w[1]), (Some(a), Some(b)) if mixes(a, b)))
        {
            tracing::trace!(line = node.start_position().row + 1, "naive/aware mix");
            self.flag(Kind::NaiveAwareMix, node);
        }
    }

    /// Record the class of the names bound by `pattern = value`, or forget them.
    fn bind(&mut self, node: Node<'t>, pat: &str, val: &str) {
        let (Some(p), Some(v)) = (node.child_by_field_name(pat), node.child_by_field_name(val))
        else {
            return;
        };
        let mut names = Vec::new();
        idents(p, self.src, &mut names);
        let class = self.class_of(v).or_else(|| {
            node.child_by_field_name("type")
                .and_then(|t| self.annotation(text(t, self.src)))
        });
        for n in names {
            match class {
                Some(c) => self.classes.insert(n, c),
                None => self.classes.remove(&n),
            };
        }
    }

    /// A parameter annotated with a datetime type that names its awareness.
    fn param(&mut self, node: Node<'t>) {
        let ty = node
            .child_by_field_name("type")
            .map(|t| text(t, self.src).to_owned());
        let Some(class) = ty.and_then(|t| self.annotation(&t)) else {
            return;
        };
        let mut names = Vec::new();
        if let Some(pat) = node.child_by_field_name("pattern") {
            idents(pat, self.src, &mut names);
        } else {
            idents(node, self.src, &mut names);
        }
        if let Some(first) = names.first() {
            self.classes.insert(first.clone(), class);
        }
    }

    /// The class a type annotation states, if it states one.
    fn annotation(&self, ty: &str) -> Option<Class> {
        let ty = ty.trim().trim_start_matches('&');
        match self.lang {
            Lang::Python => match ty.rsplit('.').next().unwrap_or(ty) {
                "AwareDatetime" => Some(Class::Aware),
                "NaiveDatetime" => Some(Class::Naive(Zone::Unknown)),
                _ => None,
            },
            Lang::Rust => {
                let ty = ty.rsplit("::").next().unwrap_or(ty);
                if ty == "NaiveDateTime" {
                    Some(Class::Naive(Zone::Unknown))
                } else if ty.starts_with("DateTime<") || ty == "Zoned" {
                    Some(Class::Aware)
                } else {
                    None
                }
            }
        }
    }

    /// The callee text of a call with its import alias resolved, `::` segments as written.
    fn callee(&self, call: Node<'_>) -> Option<String> {
        let f = call.child_by_field_name("function")?;
        let raw: String = text(f, self.src).split_whitespace().collect();
        let sep = if self.lang == Lang::Python { "." } else { "::" };
        let (head, rest) = raw
            .split_once(sep)
            .map_or((raw.as_str(), None), |(h, r)| (h, Some(r)));
        Some(match (self.aliases.get(head), rest) {
            (Some(full), Some(rest)) => format!("{full}{sep}{rest}"),
            (Some(full), None) => full.clone(),
            (None, _) => raw,
        })
    }

    /// `(receiver, method)` of a method call, if `call` is one.
    fn method<'n>(&self, call: Node<'n>) -> Option<(Node<'n>, &'s str)> {
        let f = call.child_by_field_name("function")?;
        let (recv, name) = match (self.lang, f.kind()) {
            (Lang::Rust, "field_expression") => (
                f.child_by_field_name("value")?,
                f.child_by_field_name("field")?,
            ),
            (Lang::Python, "attribute") => (
                f.child_by_field_name("object")?,
                f.child_by_field_name("attribute")?,
            ),
            _ => return None,
        };
        Some((recv, text(name, self.src)))
    }

    /// The argument nodes of a call.
    fn args(call: Node<'_>) -> Vec<Node<'_>> {
        call.child_by_field_name("arguments")
            .map(|a| {
                let mut cur = a.walk();
                a.named_children(&mut cur)
                    .filter(|c| c.kind() != "comment")
                    .collect()
            })
            .unwrap_or_default()
    }

    /// True when the argument at `pos` (or keyword `kw`) is present and is not `None`.
    fn tz_given(&self, call: Node<'_>, pos: usize, kw: &str) -> bool {
        Self::args(call).into_iter().enumerate().any(|(i, a)| {
            if a.kind() == "keyword_argument" {
                a.child_by_field_name("name")
                    .is_some_and(|n| text(n, self.src) == kw)
                    && a.child_by_field_name("value")
                        .is_some_and(|v| text(v, self.src) != "None")
            } else {
                i == pos && text(a, self.src) != "None"
            }
        })
    }

    /// `(type, function)` of the last two `::` segments of a Rust callee.
    fn rust_pair(callee: &str) -> Option<(&str, &str)> {
        let mut it = callee.rsplit("::");
        let func = it.next()?;
        Some((it.next()?, func))
    }

    /// True when `call` is a current-time read in the local zone or without a zone.
    fn is_local_read(&self, call: Node<'_>) -> bool {
        let Some(callee) = self.callee(call) else {
            return false;
        };
        match self.lang {
            Lang::Python => {
                PY_NAIVE_READS.iter().any(|(c, _)| *c == callee)
                    || (PY_NOW.contains(&callee.as_str()) && !self.tz_given(call, 0, "tz"))
            }
            Lang::Rust => Self::rust_pair(&callee).is_some_and(|p| RUST_LOCAL_READS.contains(&p)),
        }
    }

    /// `TIME001`: flag a local read whose value is stored, compared or sent.
    fn read(&mut self, call: Node<'t>) {
        if self.is_local_read(call) && self.escapes(call, &mut BTreeSet::new()) {
            tracing::trace!(
                line = call.start_position().row + 1,
                "local clock read kept"
            );
            self.flag(Kind::LocalClockRead, call);
        }
    }

    /// The class of a datetime-valued expression, when it is decidable.
    fn class_of(&self, node: Node<'_>) -> Option<Class> {
        match node.kind() {
            "parenthesized_expression" | "reference_expression" | "try_expression" | "await" => {
                node.named_child(0).and_then(|c| self.class_of(c))
            }
            "identifier" => self.classes.get(text(node, self.src)).copied(),
            "call" | "call_expression" => self.call_class(node),
            "binary_operator" | "binary_expression" => self.shifted_class(node),
            _ => None,
        }
    }

    /// `a + delta` and `a - delta` keep the class of `a`; two classed operands are a mix, not a value.
    fn shifted_class(&self, node: Node<'_>) -> Option<Class> {
        let op = node
            .child_by_field_name("operator")
            .map(|o| text(o, self.src))?;
        if !matches!(op, "+" | "-") {
            return None;
        }
        let left = self.class_of(node.child_by_field_name("left")?)?;
        match node
            .child_by_field_name("right")
            .and_then(|r| self.class_of(r))
        {
            None => Some(left),
            Some(_) => None,
        }
    }

    fn call_class(&self, call: Node<'_>) -> Option<Class> {
        let callee = self.callee(call)?;
        match self.lang {
            Lang::Python => self.py_call_class(call, &callee),
            Lang::Rust => self.rust_call_class(call, &callee),
        }
    }

    fn py_call_class(&self, call: Node<'_>, callee: &str) -> Option<Class> {
        if let Some((_, zone)) = PY_NAIVE_READS.iter().find(|(c, _)| *c == callee) {
            return Some(Class::Naive(*zone));
        }
        if PY_NOW.contains(&callee) {
            return Some(if self.tz_given(call, 0, "tz") {
                Class::Aware
            } else {
                Class::Naive(Zone::Local)
            });
        }
        if let Some((_, pos, kw, zone)) = PY_FROM.iter().find(|(c, ..)| *c == callee) {
            return Some(if self.tz_given(call, *pos, kw) {
                Class::Aware
            } else {
                Class::Naive(*zone)
            });
        }
        if PY_PARSE.contains(&callee) {
            let zoned = Self::args(call)
                .get(1)
                .is_some_and(|f| text(*f, self.src).contains("%z"));
            return (!zoned).then_some(Class::Naive(Zone::Unknown));
        }
        let (recv, method) = self.method(call)?;
        match method {
            "astimezone" => Some(Class::Aware),
            "replace" => {
                let has_kw = Self::args(call).iter().any(|a| {
                    a.child_by_field_name("name")
                        .is_some_and(|n| text(n, self.src) == "tzinfo")
                });
                if has_kw {
                    Some(if self.tz_given(call, usize::MAX, "tzinfo") {
                        Class::Aware
                    } else {
                        Class::Naive(Zone::Unknown)
                    })
                } else {
                    self.class_of(recv)
                }
            }
            _ => None,
        }
    }

    fn rust_call_class(&self, call: Node<'_>, callee: &str) -> Option<Class> {
        if let Some(pair) = Self::rust_pair(callee) {
            if RUST_AWARE.contains(&pair) {
                return Some(Class::Aware);
            }
            if RUST_NAIVE.contains(&pair) {
                return Some(Class::Naive(Zone::Unknown));
            }
        }
        let (recv, method) = self.method(call)?;
        match method {
            "naive_utc" => Some(Class::Naive(Zone::Utc)),
            "naive_local" => Some(Class::Naive(Zone::Local)),
            "with_timezone" | "and_utc" | "to_utc" | "in_tz" | "intz" | "with_time_zone" => {
                Some(Class::Aware)
            }
            m if RUST_UNWRAP.contains(&m) => self.class_of(recv),
            _ => None,
        }
    }

    /// True when the value of `node` is stored, compared, returned or sent rather than only shown.
    fn escapes(&self, node: Node<'t>, seen: &mut BTreeSet<String>) -> bool {
        let mut cur = node;
        loop {
            let Some(p) = cur.parent() else {
                return false;
            };
            match (self.lang, p.kind()) {
                (
                    _,
                    "parenthesized_expression"
                    | "reference_expression"
                    | "try_expression"
                    | "await"
                    | "interpolation"
                    | "string"
                    | "concatenated_string",
                )
                | (Lang::Python, "binary_operator") => cur = p,
                (Lang::Rust, "binary_expression") => {
                    let op = p
                        .child_by_field_name("operator")
                        .map_or("", |o| text(o, self.src));
                    if matches!(op, "+" | "-" | "*" | "/") {
                        cur = p;
                    } else {
                        return true;
                    }
                }
                (_, "expression_statement") => return false,
                (Lang::Python, "attribute") | (Lang::Rust, "field_expression") => {
                    match self.climb_method(p) {
                        Climb::Call(next) => cur = next,
                        Climb::Converted => return false,
                        Climb::Field => cur = p,
                    }
                }
                (_, "argument_list" | "arguments") => {
                    let Some(call) = p.parent() else {
                        return true;
                    };
                    match self.call_role(call) {
                        Role::Display => return false,
                        Role::Pass => cur = call,
                        Role::Sink => return true,
                    }
                }
                (Lang::Rust, "token_tree") => {
                    let Some(mac) = p.parent().filter(|m| m.kind() == "macro_invocation") else {
                        return true;
                    };
                    let name = mac
                        .child_by_field_name("macro")
                        .map_or("", |m| text(m, self.src));
                    let name = name.rsplit("::").next().unwrap_or(name);
                    if RUST_DISPLAY.contains(&name) {
                        return false;
                    }
                    if RUST_PASS.contains(&name) {
                        cur = mac;
                    } else {
                        return true;
                    }
                }
                (Lang::Python, "assignment") if p.child_by_field_name("right") == Some(cur) => {
                    return self.bound_escapes(p, "left", seen);
                }
                (Lang::Rust, "let_declaration") if p.child_by_field_name("value") == Some(cur) => {
                    return self.bound_escapes(p, "pattern", seen);
                }
                _ => return true,
            }
        }
    }

    /// For a method or field access on `cur`: `Converted` when the method converts the value to a
    /// fixed instant or zone (no longer local), `Call` when the call carries on, `Field` for a
    /// plain field access.
    fn climb_method(&self, access: Node<'t>) -> Climb<'t> {
        let Some(call) = access
            .parent()
            .filter(|c| matches!(c.kind(), "call" | "call_expression"))
            .filter(|c| c.child_by_field_name("function") == Some(access))
        else {
            return Climb::Field;
        };
        let method = access
            .child_by_field_name("attribute")
            .or_else(|| access.child_by_field_name("field"))
            .map_or("", |m| text(m, self.src));
        let converts = match self.lang {
            Lang::Python => {
                PY_CONVERT.contains(&method)
                    && (method == "timestamp" || !Self::args(call).is_empty())
                    || (method == "replace" && self.tz_given(call, usize::MAX, "tzinfo"))
            }
            Lang::Rust => RUST_CONVERT.contains(&method),
        };
        if converts {
            Climb::Converted
        } else {
            Climb::Call(call)
        }
    }

    fn call_role(&self, call: Node<'_>) -> Role {
        let Some(callee) = call
            .child_by_field_name("function")
            .map(|f| text(f, self.src))
        else {
            return Role::Sink;
        };
        let last = callee.rsplit(['.', ':']).next().unwrap_or(callee);
        match self.lang {
            Lang::Python if PY_DISPLAY.contains(&last) => Role::Display,
            Lang::Python if PY_PASS.contains(&last) => Role::Pass,
            Lang::Rust if RUST_WRAP.contains(&callee) => Role::Pass,
            _ => Role::Sink,
        }
    }

    /// True when any use of the names bound by `bind.<field>` escapes display.
    fn bound_escapes(&self, bind: Node<'t>, field: &str, seen: &mut BTreeSet<String>) -> bool {
        let Some(target) = bind.child_by_field_name(field) else {
            return true;
        };
        if !matches!(
            target.kind(),
            "identifier" | "tuple_pattern" | "pattern_list" | "tuple"
        ) {
            // An attribute, subscript or field target is stored by definition.
            return true;
        }
        let mut names = Vec::new();
        idents(target, self.src, &mut names);
        let mut uses = Vec::new();
        for name in names {
            if seen.insert(name.clone()) {
                self.collect_uses(self.scope, &name, &mut uses);
            }
        }
        uses.into_iter().any(|u| self.escapes(u, seen))
    }

    /// Every identifier named `name` under `node` that is a use, not a binding target.
    fn collect_uses(&self, node: Node<'t>, name: &str, out: &mut Vec<Node<'t>>) {
        if node.kind() == "identifier"
            && text(node, self.src) == name
            && !Self::is_target(node)
            && !Self::is_member_name(node)
        {
            out.push(node);
        }
        for c in children(node) {
            self.collect_uses(c, name, out);
        }
    }

    /// True when `ident` names a path segment, attribute or keyword, not a variable.
    fn is_member_name(ident: Node<'_>) -> bool {
        ident.parent().is_some_and(|p| {
            matches!(
                p.kind(),
                "scoped_identifier" | "attribute" | "keyword_argument"
            ) && p
                .child_by_field_name("name")
                .or_else(|| p.child_by_field_name("attribute"))
                == Some(ident)
        })
    }

    /// True when `ident` sits in the left side of an assignment or `let` pattern.
    fn is_target(ident: Node<'_>) -> bool {
        let mut cur = ident;
        while let Some(p) = cur.parent() {
            if matches!(
                p.kind(),
                "assignment" | "let_declaration" | "assignment_expression"
            ) {
                let target = p
                    .child_by_field_name("left")
                    .or_else(|| p.child_by_field_name("pattern"));
                return target.is_some_and(|t| t == cur);
            }
            cur = p;
        }
        false
    }
}

/// What a call does with an argument that is a datetime.
enum Role {
    /// Shows it (print, log): not kept.
    Display,
    /// Hands the same value back: keep following.
    Pass,
    /// Anything else: the value is sent.
    Sink,
}

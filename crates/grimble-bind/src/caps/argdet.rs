//! Argument-aware capability detectors (ticket 01M5XNNHY7KZDKBZKK2MM08TTF): what a call's
//! arguments say about the capability it needs, found from the syntax tree and never from text.
//!
//! The Rust half reads `OpenOptions` builder flags: `OpenOptions::new().read(true)` only reads,
//! while `write`, `append`, `create`, `create_new` and `truncate` each need `fs.write`. It follows
//! a straight method chain and a `let`-bound builder through the rest of its block; a flag from a
//! non-literal is `Maybe`, and a builder that escapes (passed on, returned, reassigned, used in a
//! macro) is wholly unproven.

use gob_languages::{Language, ParseLimits, ParseResult, parse};
use tree_sitter::Node;

/// A three-valued flag: set, not set, or not provable either way.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub(super) enum Tri {
    /// Provably set.
    Yes,
    /// Provably not set.
    #[default]
    No,
    /// Depends on a non-literal or a branch.
    Maybe,
}

impl Tri {
    /// The value after two paths meet: equal values stay, differing ones become `Maybe`.
    fn join(self, other: Tri) -> Tri {
        if self == other { self } else { Tri::Maybe }
    }

    /// The strongest of `self` and `other`: `Yes` beats `Maybe` beats `No`.
    fn or(self, other: Tri) -> Tri {
        match (self, other) {
            (Tri::Yes, _) | (_, Tri::Yes) => Tri::Yes,
            (Tri::Maybe, _) | (_, Tri::Maybe) => Tri::Maybe,
            _ => Tri::No,
        }
    }
}

/// What an `OpenOptions` builder asks of the file system.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(super) struct OpenVerdict {
    /// Whether the open reads.
    pub(super) reads: Tri,
    /// Whether the open writes (`write`, `append`, `create`, `create_new` or `truncate`).
    pub(super) writes: Tri,
}

/// The builder flags tracked so far.
#[derive(Clone, Copy, Debug, Default)]
struct Flags {
    read: Tri,
    write: Tri,
    append: Tri,
    create: Tri,
    create_new: Tri,
    truncate: Tri,
}

/// Why a builder could not be followed to the end.
struct Escaped;

impl Flags {
    /// Apply one builder method; `Err` for a method that is not a known builder step.
    fn apply(&mut self, method: &str, arg: Tri, conditional: bool) -> Result<(), Escaped> {
        let slot = match method {
            "read" => &mut self.read,
            "write" => &mut self.write,
            "append" => &mut self.append,
            "create" => &mut self.create,
            "create_new" => &mut self.create_new,
            "truncate" => &mut self.truncate,
            // Platform knobs that change neither read nor write intent.
            "custom_flags" | "mode" | "share_mode" | "access_mode" | "attributes"
            | "security_qos_flags" => return Ok(()),
            _ => return Err(Escaped),
        };
        *slot = if conditional { slot.join(arg) } else { arg };
        Ok(())
    }

    /// Fold the flags into a verdict; a builder with no flag at all is a plain read.
    fn verdict(self) -> OpenVerdict {
        let writes = self
            .write
            .or(self.append)
            .or(self.create)
            .or(self.create_new)
            .or(self.truncate);
        let reads = if self.read == Tri::No && writes == Tri::No {
            Tri::Yes
        } else {
            self.read
        };
        OpenVerdict { reads, writes }
    }
}

/// Node kinds that make the code under them run zero or many times.
const CONDITIONAL: &[&str] = &[
    "if_expression",
    "match_expression",
    "while_expression",
    "for_expression",
    "loop_expression",
    "closure_expression",
    "async_block",
    "try_block",
];

fn text<'a>(src: &'a str, n: Node<'_>) -> &'a str {
    &src[n.start_byte()..n.end_byte()]
}

/// The truth of a builder argument: a `true` / `false` literal, else `Maybe`.
fn flag_arg(src: &str, call: Node<'_>) -> Tri {
    let Some(args) = call.child_by_field_name("arguments") else {
        return Tri::Maybe;
    };
    let mut c = args.walk();
    let Some(first) = args.named_children(&mut c).next() else {
        return Tri::Maybe;
    };
    match (first.kind(), text(src, first)) {
        ("boolean_literal", "true") => Tri::Yes,
        ("boolean_literal", "false") => Tri::No,
        _ => Tri::Maybe,
    }
}

/// How a walk up a method chain ended.
enum ChainEnd<'t> {
    /// The chain reached `.open(..)`.
    Opened,
    /// The chain stopped after a builder step; this is its last call.
    Open(Node<'t>),
}

/// Walk the method chain above `start`, applying each builder step to `flags`.
fn walk_chain<'t>(
    src: &str,
    start: Node<'t>,
    flags: &mut Flags,
    conditional: bool,
) -> Result<ChainEnd<'t>, Escaped> {
    let mut cur = start;
    loop {
        let Some(parent) = cur.parent() else {
            return Ok(ChainEnd::Open(cur));
        };
        let is_receiver =
            parent.kind() == "field_expression" && parent.child_by_field_name("value") == Some(cur);
        let call = parent.parent().filter(|g| {
            g.kind() == "call_expression" && g.child_by_field_name("function") == Some(parent)
        });
        let (true, Some(call)) = (is_receiver, call) else {
            return Ok(ChainEnd::Open(cur));
        };
        let method = parent
            .child_by_field_name("field")
            .map(|f| text(src, f))
            .unwrap_or_default();
        if method == "open" {
            return Ok(ChainEnd::Opened);
        }
        flags.apply(method, flag_arg(src, call), conditional)?;
        cur = call;
    }
}

/// True when `n` sits under a construct that may run zero or many times, below `block`.
fn conditional_under(n: Node<'_>, block: Node<'_>) -> bool {
    let mut cur = n;
    while let Some(p) = cur.parent() {
        if p == block {
            return false;
        }
        if CONDITIONAL.contains(&p.kind()) {
            return true;
        }
        cur = p;
    }
    false
}

/// Every identifier named `name` in `n`, in source order.
fn idents<'t>(src: &str, n: Node<'t>, name: &str, out: &mut Vec<Node<'t>>) {
    if n.kind() == "identifier" && text(src, n) == name {
        out.push(n);
    }
    let mut c = n.walk();
    for ch in n.children(&mut c) {
        idents(src, ch, name, out);
    }
}

/// Follow a `let`-bound builder through the rest of its block, applying every step.
fn follow_binding(src: &str, decl: Node<'_>, flags: &mut Flags) -> Result<(), Escaped> {
    let pattern = decl.child_by_field_name("pattern").ok_or(Escaped)?;
    if pattern.kind() != "identifier" {
        return Err(Escaped);
    }
    let name = text(src, pattern);
    let block = decl
        .parent()
        .filter(|b| b.kind() == "block")
        .ok_or(Escaped)?;
    let mut found = Vec::new();
    idents(src, block, name, &mut found);
    for id in found
        .into_iter()
        .filter(|i| i.start_byte() >= decl.end_byte())
    {
        let p = id.parent().ok_or(Escaped)?;
        // Shadowing, a macro token tree or a bare use all leave the builder unproven.
        let is_receiver =
            p.kind() == "field_expression" && p.child_by_field_name("value") == Some(id);
        let call = p.parent().filter(|g| {
            g.kind() == "call_expression" && g.child_by_field_name("function") == Some(p)
        });
        let (true, Some(call)) = (is_receiver, call) else {
            return Err(Escaped);
        };
        let method = p
            .child_by_field_name("field")
            .map(|f| text(src, f))
            .unwrap_or_default();
        let conditional = conditional_under(id, block);
        if method != "open" {
            flags.apply(method, flag_arg(src, call), conditional)?;
            walk_chain(src, call, flags, conditional)?;
        }
    }
    // A `let` that rebinds the name makes later uses ambiguous.
    let mut rebinds = 0usize;
    let mut stack = vec![block];
    while let Some(n) = stack.pop() {
        if n.kind() == "let_declaration"
            && n.child_by_field_name("pattern")
                .is_some_and(|p| text(src, p) == name)
        {
            rebinds += 1;
        }
        let mut c = n.walk();
        stack.extend(n.children(&mut c));
    }
    if rebinds > 1 {
        return Err(Escaped);
    }
    Ok(())
}

/// Where a builder constructor call is: an exact byte offset, or a line and the callee as resolved.
#[derive(Clone, Copy, Debug)]
pub(super) enum Site<'a> {
    /// The call starts at this byte.
    Offset(usize),
    /// The call starts on this one-based line; `callee` is the resolved vocabulary name.
    Line(u32, &'a str),
}

/// The last `n` `::` segments of `path`, whitespace removed.
fn tail(path: &str, n: usize) -> String {
    let clean: String = path.chars().filter(|c| !c.is_whitespace()).collect();
    let segs: Vec<&str> = clean.split("::").collect();
    segs[segs.len().saturating_sub(n)..].join("::")
}

/// Every `X::f(..)` call node (scoped-path callee) in `n`, in source order.
fn scoped_calls<'t>(n: Node<'t>, out: &mut Vec<Node<'t>>) {
    if n.kind() == "call_expression"
        && n.child_by_field_name("function")
            .is_some_and(|f| f.kind() == "scoped_identifier")
    {
        out.push(n);
    }
    let mut c = n.walk();
    for ch in n.children(&mut c) {
        scoped_calls(ch, out);
    }
}

/// The constructor call a [`Site`] names, or `None` when it is absent or ambiguous.
fn locate<'t>(src: &str, root: Node<'t>, site: Site<'_>) -> Option<Node<'t>> {
    match site {
        Site::Offset(offset) => {
            let mut cur = root.descendant_for_byte_range(offset, offset)?;
            loop {
                if cur.kind() == "call_expression"
                    && cur.start_byte() == offset
                    && cur
                        .child_by_field_name("function")
                        .is_some_and(|f| f.kind() == "scoped_identifier")
                {
                    return Some(cur);
                }
                cur = cur.parent()?;
            }
        }
        Site::Line(line, callee) => {
            let mut all = Vec::new();
            scoped_calls(root, &mut all);
            let on_line: Vec<(Node<'t>, &str)> = all
                .into_iter()
                .filter(|c| c.start_position().row + 1 == line as usize)
                .filter_map(|c| Some((c, text(src, c.child_by_field_name("function")?))))
                .collect();
            let spelled: Vec<Node<'t>> = on_line
                .iter()
                .filter(|(_, f)| tail(f, 2) == tail(callee, 2))
                .map(|(c, _)| *c)
                .collect();
            // An aliased spelling (`OO::new`) matches on the last segment alone.
            let by_last: Vec<Node<'t>> = on_line
                .iter()
                .filter(|(_, f)| tail(f, 1) == tail(callee, 1))
                .map(|(c, _)| *c)
                .collect();
            match (spelled.as_slice(), by_last.as_slice()) {
                ([one], _) | ([], [one]) => Some(*one),
                _ => None,
            }
        }
    }
}

/// What the `OpenOptions` builder created by the `X::new()` / `File::options()` call at `site` of
/// Rust `src` asks for; `None` when no single such call is there.
pub(super) fn rust_open_options(src: &str, site: Site<'_>) -> Option<OpenVerdict> {
    let ParseResult::Parsed(tree) = parse(Language::Rust, src, &ParseLimits::default()) else {
        tracing::debug!("rust source did not parse: no open-option analysis");
        return None;
    };
    let start = locate(src, tree.root(), site)?;
    let mut flags = Flags::default();
    let verdict = match walk_chain(src, start, &mut flags, false) {
        Ok(ChainEnd::Opened) => Ok(()),
        Ok(ChainEnd::Open(last)) => match last.parent() {
            Some(decl) if decl.kind() == "let_declaration" => follow_binding(src, decl, &mut flags),
            _ => Err(Escaped),
        },
        Err(e) => Err(e),
    };
    Some(if verdict.is_ok() {
        flags.verdict()
    } else {
        tracing::debug!(?site, "open-options builder escapes: flags unproven");
        OpenVerdict {
            reads: Tri::Maybe,
            writes: Tri::Maybe,
        }
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    fn at(src: &str) -> OpenVerdict {
        let off = src
            .find("OpenOptions::new")
            .or_else(|| src.find("File::options"))
            .unwrap();
        rust_open_options(src, Site::Offset(off)).unwrap()
    }

    // frob:ticket 01M5XNNHY7KZDKBZKK2MM08TTF
    #[test]
    fn argdet_chain_read_only() {
        let v = at("fn f(){ let _ = OpenOptions::new().read(true).open(p); }");
        assert_eq!(
            v,
            OpenVerdict {
                reads: Tri::Yes,
                writes: Tri::No
            }
        );
    }
}

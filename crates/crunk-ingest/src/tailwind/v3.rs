//! Static reader of a Tailwind v3 JS config: `theme` and `theme.extend` object literals.
//!
//! A small scanner, not a JS engine: it understands object literals, strings, numbers, spreads
//! and balanced expressions (kept as opaque text). The runtime resolves what it cannot.

// frob:ticket 01M43ARZ3VCNDX20C9BZZCCYHY

use super::text::{line_of, mask_comments};

/// A parsed value: an object or an opaque leaf (unquoted when it was a single string).
#[derive(Debug, Clone)]
pub(crate) enum Node {
    Obj(Vec<Member>),
    Leaf(String),
}

/// One `key: value` of an object.
#[derive(Debug, Clone)]
pub(crate) struct Member {
    pub key: String,
    pub line: u32,
    pub node: Node,
}

/// The `theme` object of `src`, if it has a literal one.
pub(crate) fn theme_object(src: &str) -> Option<Vec<Member>> {
    let masked = mask_comments(src, true);
    let b = masked.as_bytes();
    let mut from = 0;
    while let Some(p) = masked[from..].find("theme") {
        let at = from + p;
        from = at + 5;
        let before_ok = at == 0 || !(is_ident(b[at - 1]) || b[at - 1] == b'.');
        let rest = masked[at + 5..].trim_start();
        if before_ok && rest.starts_with(':') {
            let colon = masked.len() - rest.len();
            let mut p = Parser {
                src: &masked,
                pos: colon + 1,
            };
            if let Node::Obj(members) = p.value() {
                return Some(members);
            }
        }
    }
    None
}

fn is_ident(c: u8) -> bool {
    c.is_ascii_alphanumeric() || c == b'_' || c == b'$'
}

struct Parser<'a> {
    src: &'a str,
    pos: usize,
}

impl Parser<'_> {
    fn b(&self) -> &[u8] {
        self.src.as_bytes()
    }

    fn ws(&mut self) {
        while self.pos < self.b().len() && self.b()[self.pos].is_ascii_whitespace() {
            self.pos += 1;
        }
    }

    fn value(&mut self) -> Node {
        self.ws();
        if self.b().get(self.pos) == Some(&b'{') {
            Node::Obj(self.object())
        } else {
            Node::Leaf(self.leaf())
        }
    }

    fn object(&mut self) -> Vec<Member> {
        self.pos += 1;
        let mut out = Vec::new();
        loop {
            self.ws();
            match self.b().get(self.pos) {
                None => break,
                Some(b'}') => {
                    self.pos += 1;
                    break;
                }
                Some(b',') => self.pos += 1,
                _ => {
                    if self.src[self.pos..].starts_with("...") {
                        self.pos += 3;
                        self.leaf();
                        continue;
                    }
                    if let Some(m) = self.member() {
                        out.push(m);
                    }
                }
            }
        }
        out
    }

    fn member(&mut self) -> Option<Member> {
        let line = line_of(self.src, self.pos);
        let c = self.b()[self.pos];
        let key = if c == b'[' {
            self.leaf_until_colon();
            None
        } else if matches!(c, b'"' | b'\'' | b'`') {
            Some(unquote(&self.quoted()))
        } else {
            let start = self.pos;
            while self.pos < self.b().len()
                && (is_ident(self.b()[self.pos]) || matches!(self.b()[self.pos], b'.' | b'-'))
            {
                self.pos += 1;
            }
            if self.pos == start {
                self.pos += 1;
                return None;
            }
            Some(self.src[start..self.pos].to_owned())
        };
        self.ws();
        let node = if self.b().get(self.pos) == Some(&b':') {
            self.pos += 1;
            self.value()
        } else {
            Node::Leaf(self.leaf())
        };
        key.map(|key| Member { key, line, node })
    }

    fn leaf_until_colon(&mut self) {
        self.leaf();
        self.ws();
    }

    fn quoted(&mut self) -> String {
        let start = self.pos;
        let q = self.b()[self.pos];
        self.pos += 1;
        while self.pos < self.b().len() && self.b()[self.pos] != q {
            self.pos += if self.b()[self.pos] == b'\\' { 2 } else { 1 };
        }
        self.pos = (self.pos + 1).min(self.b().len());
        self.src[start..self.pos].to_owned()
    }

    /// An expression up to the next top-level `,` or unbalanced closer.
    fn leaf(&mut self) -> String {
        self.ws();
        let start = self.pos;
        let mut depth = 0usize;
        while self.pos < self.b().len() {
            match self.b()[self.pos] {
                b'"' | b'\'' | b'`' => {
                    self.quoted();
                    continue;
                }
                b'(' | b'[' | b'{' => depth += 1,
                b')' | b']' | b'}' => {
                    if depth == 0 {
                        break;
                    }
                    depth -= 1;
                }
                b',' if depth == 0 => break,
                _ => {}
            }
            self.pos += 1;
        }
        unquote(self.src[start..self.pos].trim())
    }
}

/// `'x'`, `"x"` or `` `x` `` without its quotes; anything else unchanged.
fn unquote(text: &str) -> String {
    let b = text.as_bytes();
    if b.len() >= 2 && matches!(b[0], b'"' | b'\'' | b'`') && b[b.len() - 1] == b[0] {
        text[1..text.len() - 1].to_owned()
    } else {
        text.to_owned()
    }
}

/// Flatten `node` under `prefix` into `(key, line, value)` leaves; `DEFAULT` names its parent.
pub(crate) fn flatten(prefix: &str, line: u32, node: &Node, out: &mut Vec<(String, u32, String)>) {
    match node {
        Node::Leaf(v) => out.push((prefix.to_owned(), line, v.clone())),
        Node::Obj(members) => {
            for m in members {
                let key = if m.key == "DEFAULT" {
                    prefix.to_owned()
                } else if prefix.is_empty() {
                    m.key.clone()
                } else {
                    format!("{prefix}-{}", m.key)
                };
                flatten(&key, m.line, &m.node, out);
            }
        }
    }
}

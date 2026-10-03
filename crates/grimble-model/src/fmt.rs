//! `grimble fmt`: the alpha-normal printer (grmb-spec 9.3).

// frob:ticket 01M3Z713VGKF4Z0JJ3263XJMC3

use std::fmt::Write as _;

use crate::ast::{Entity, EntityKind, FileStatus, Header, Item, ModuleKind, ParsedFile};
use crate::lex::CommentKind;
use crate::span::Span;
use crate::text::{clause_sort_key, clause_text, exception_text, quote};

/// Why a file was not formatted.
#[derive(Clone, PartialEq, Eq, Debug, thiserror::Error)]
pub enum FmtError {
    /// The file holds a `hole`, is opaque or is refused: fmt never rewrites it (9.3 item 6).
    #[error("{path}: not rewritten, {reason}")]
    Damaged {
        /// The file.
        path: String,
        /// The first problem.
        reason: String,
        /// Where the first problem is, when it has a span.
        span: Option<Span>,
    },
}

/// The column past which a line is wrapped (grmb-spec 2.5).
pub const WRAP_COLUMN: usize = 100;

/// Formats one file; `Err` when it holds a hole (a syntax error is never "formatted away").
///
/// # Errors
///
/// [`FmtError::Damaged`] when the file has a hole, is opaque or was refused.
pub fn format_file(file: &ParsedFile) -> Result<String, FmtError> {
    if file.is_damaged() {
        let first = file.diags.first();
        let reason = match (&file.status, first) {
            (FileStatus::Parsed, Some(d)) => format!("hole at bytes {}: {}", d.span, d.message),
            (FileStatus::Parsed, None) => "the file contains a hole".to_owned(),
            (s, _) => format!("the file is {s:?}"),
        };
        tracing::info!(path = %file.path, %reason, "fmt refused");
        return Err(FmtError::Damaged {
            path: file.path.clone(),
            reason,
            span: first.map(|d| d.span),
        });
    }
    let mut p = Printer {
        f: file,
        out: String::new(),
    };
    p.file();
    tracing::debug!(path = %file.path, bytes = p.out.len(), "formatted");
    Ok(p.out)
}

struct Printer<'a> {
    f: &'a ParsedFile,
    out: String,
}

fn item_rank(i: &Item) -> (u8, u8, String, bool, String) {
    match i {
        Item::Include(inc) => (
            0,
            0,
            inc.path.value.clone(),
            false,
            inc.mount
                .as_ref()
                .map(crate::ast::RefPath::written)
                .unwrap_or_default(),
        ),
        Item::Namespace(n) => (2, 0, n.name.text.clone(), false, String::new()),
        Item::Entity(e) => {
            let kind = match e.kind {
                EntityKind::Pack => (1, 0),
                EntityKind::Node => (3, 0),
                EntityKind::Flow => (3, 1),
                EntityKind::Contract => (3, 2),
                EntityKind::Claim => (3, 3),
                EntityKind::Vmodel => (3, 4),
                EntityKind::Boundary => (3, 5),
            };
            (
                kind.0,
                kind.1,
                e.target.written(),
                e.extension,
                String::new(),
            )
        }
        Item::Exception(t) => (
            4,
            0,
            t.exception.rule.text.clone(),
            false,
            exception_text(&t.exception),
        ),
        Item::Hole { .. } => (5, 0, String::new(), false, String::new()),
    }
}

/// Wraps `line` after `|`, `&` or `,` (outside strings) so no line passes [`WRAP_COLUMN`].
fn wrap(line: &str, indent: usize) -> String {
    if line.chars().count() <= WRAP_COLUMN {
        return line.to_owned();
    }
    let chars: Vec<char> = line.chars().collect();
    let mut breaks = Vec::new();
    let mut in_str = false;
    let mut i = 0;
    while i < chars.len() {
        let c = chars[i];
        if in_str {
            if c == '\\' {
                i += 1;
            } else if c == '"' {
                in_str = false;
            }
        } else if c == '"' {
            in_str = true;
        } else if matches!(c, '|' | '&' | ',') && chars.get(i + 1) == Some(&' ') {
            breaks.push(i + 2);
        }
        i += 1;
    }
    let cont = " ".repeat(indent + 4);
    let mut out = String::new();
    let mut start = 0;
    let mut width_base = 0;
    while chars.len() - start + width_base > WRAP_COLUMN {
        let limit = start + WRAP_COLUMN - width_base;
        let Some(&b) = breaks.iter().rev().find(|&&b| b > start && b <= limit) else {
            break;
        };
        out.extend(&chars[start..b]);
        while out.ends_with(' ') {
            out.pop();
        }
        out.push('\n');
        out.push_str(&cont);
        start = b;
        width_base = indent + 4;
    }
    out.extend(&chars[start..]);
    out
}

impl Printer<'_> {
    fn line(&mut self, indent: usize, text: &str) {
        let full = format!("{}{text}", " ".repeat(indent));
        self.out.push_str(&wrap(&full, indent));
        self.out.push('\n');
    }

    fn comments(&mut self, ids: &[usize], indent: usize) {
        let pad = " ".repeat(indent);
        for &i in ids {
            let c = &self.f.comments[i];
            if c.kind != CommentKind::Doc {
                self.out.push_str(&pad);
                self.out.push_str(&c.text);
                self.out.push('\n');
            }
        }
        for &i in ids {
            let c = &self.f.comments[i];
            if c.kind == CommentKind::Doc {
                self.out.push_str(&pad);
                let t = c.doc_text();
                if t.is_empty() {
                    self.out.push_str("///");
                } else {
                    self.out.push_str("/// ");
                    self.out.push_str(t);
                }
                self.out.push('\n');
            }
        }
    }

    fn file(&mut self) {
        let f = self.f;
        self.comments(&f.attachments.file, 0);
        if let Some(v) = &f.version {
            self.line(0, &format!("grimble = {};", quote(&v.value)));
        }
        if let Some(m) = &f.module {
            self.comments(f.attachments.of(m.id), 0);
            let text = match m.kind {
                ModuleKind::Module => format!("module {};", m.name.text),
                ModuleKind::PartOf => format!("part of {};", m.name.text),
            };
            self.line(0, &text);
        }
        let items: Vec<&Item> = f.items.iter().collect();
        self.items(&items, 0, true);
    }

    fn items(&mut self, items: &[&Item], indent: usize, top: bool) {
        let mut sorted: Vec<&Item> = items.to_vec();
        sorted.sort_by_key(|i| item_rank(i));
        let mut prev_include = false;
        for (n, item) in sorted.iter().enumerate() {
            let is_include = matches!(item, Item::Include(_));
            if (top || n > 0) && !(prev_include && is_include) {
                self.out.push('\n');
            }
            prev_include = is_include;
            self.item(item, indent);
        }
    }

    fn item(&mut self, item: &Item, indent: usize) {
        match item {
            Item::Include(inc) => {
                self.comments(self.f.attachments.of(inc.id), indent);
                let mut t = format!("include {}", quote(&inc.path.value));
                if let Some(m) = &inc.mount {
                    let _ = write!(t, " as {}", m.written());
                }
                if inc.outside {
                    t.push_str(" outside");
                }
                t.push(';');
                self.line(indent, &t);
            }
            Item::Namespace(n) => {
                self.comments(self.f.attachments.of(n.id), indent);
                self.line(indent, &format!("namespace {} {{", n.name.text));
                let inner: Vec<&Item> = n.items.iter().collect();
                self.items(&inner, indent + 2, false);
                self.line(indent, "}");
            }
            Item::Entity(e) => self.entity(e, indent),
            Item::Exception(t) => {
                self.comments(self.f.attachments.of(t.id), indent);
                self.line(indent, &format!("{};", exception_text(&t.exception)));
            }
            Item::Hole { .. } => unreachable!("a file with a hole is never printed"),
        }
    }

    fn entity(&mut self, e: &Entity, indent: usize) {
        self.comments(self.f.attachments.of(e.id), indent);
        let head = match (&e.header, e.extension) {
            (_, true) => format!("extend {} {}", e.kind.keyword(), e.target.written()),
            (Header::Node { trust: Some(t) }, _) => {
                format!("node {} : {}", e.name.text, t.text)
            }
            (Header::Flow { from, to }, _) => format!(
                "flow {} : {} -> {}",
                e.name.text,
                from.written(),
                to.written()
            ),
            (
                Header::Boundary {
                    direction,
                    flow,
                    from,
                    to,
                    when,
                },
                _,
            ) => {
                let mut t = format!(
                    "boundary {} {} {} : {} -> {}",
                    e.name.text,
                    direction.keyword(),
                    flow.written(),
                    from.text,
                    to.text
                );
                if let Some(w) = when {
                    let _ = write!(t, " when {}", quote(&w.value));
                }
                t
            }
            _ => format!("{} {}", e.kind.keyword(), e.name.text),
        };
        let mut clauses: Vec<&crate::ast::Clause> = e.clauses.iter().collect();
        clauses.sort_by_cached_key(|c| clause_sort_key(c));
        let mut printed: Vec<(&crate::ast::Clause, String)> = Vec::new();
        for c in clauses {
            let text = clause_text(&c.kind);
            let has_att = !self.f.attachments.of(c.id).is_empty();
            if let Some((_, pt)) = printed.last()
                && *pt == text
                && !has_att
            {
                continue;
            }
            printed.push((c, text));
        }
        if printed.is_empty() && e.kind == EntityKind::Boundary && !e.extension {
            self.line(indent, &format!("{head};"));
            return;
        }
        self.line(indent, &format!("{head} {{"));
        for (c, text) in printed {
            self.comments(self.f.attachments.of(c.id), indent + 2);
            self.line(indent + 2, &format!("{text};"));
        }
        self.line(indent, "}");
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::parse::parse_file;

    fn fmt(src: &str) -> String {
        format_file(&parse_file("t.grmb", src.as_bytes())).expect("formats")
    }

    #[test]
    fn prints_canonical_text_and_is_idempotent() {
        let src = "grimble=\"2\";module m;\n node b:trusted{ owns \"z\" | \"a\"; kind component; }\n\n node a:trusted{} // tail\n";
        let once = fmt(src);
        assert_eq!(
            once,
            "grimble = \"2\";\nmodule m;\n\n// tail\nnode a : trusted {\n}\n\nnode b : trusted {\n  kind component;\n  owns \"a\" | \"z\";\n}\n"
        );
        assert_eq!(fmt(&once), once);
    }

    #[test]
    fn a_hole_is_never_formatted_away() {
        let f = parse_file(
            "t.grmb",
            b"grimble = \"2\";\nmodule m;\nnode a : trusted { owns ; }\n",
        );
        assert!(matches!(format_file(&f), Err(FmtError::Damaged { .. })));
    }

    #[test]
    fn long_selectors_wrap_after_operators() {
        let long = (0..12)
            .map(|i| format!("\"crates/some-long-crate-name-{i}/src/**\""))
            .collect::<Vec<_>>()
            .join(" | ");
        let out = fmt(&format!(
            "grimble = \"2\";\nmodule m;\nnode a : trusted {{ owns {long}; }}\n"
        ));
        assert!(
            out.lines().all(|l| l.chars().count() <= WRAP_COLUMN),
            "{out}"
        );
        assert_eq!(fmt(&out), out);
    }
}

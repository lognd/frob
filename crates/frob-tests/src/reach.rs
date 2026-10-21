//! Name-based call reach, a supplement to `SymbolGraph::affects`.
//!
//! `gob-symbols` records calls per crate and does not see inside macro
//! invocations, so `assert_eq!(double(2), 4)` and a call from one workspace
//! crate into another leave no edge. This module scans function bodies for
//! `name(` and links the caller to every function of that name, but only when
//! exactly one function in the repository has the name: a unique name is an
//! unambiguous callee, while `new` or `run` would drag in the world. Ambiguous
//! names fall back to the graph's own (per-crate) edges alone.

use std::collections::{BTreeSet, HashMap, HashSet, VecDeque};
use std::path::{Path, PathBuf};

use gob_ir::engine::EngineVocab;
use gob_symbols::{SymbolGraph, SymbolKind, SymbolRecord, Symref};

/// Lazily read file text, shared by the attribute scan and the body scan.
#[derive(Debug)]
pub struct Sources {
    root: PathBuf,
    cache: HashMap<String, Option<String>>,
}

impl Sources {
    /// Sources under the work tree `root`.
    pub fn new(root: &Path) -> Self {
        Self {
            root: root.to_path_buf(),
            cache: HashMap::new(),
        }
    }

    // frob:ticket 01M44YQXBGJW1VKDF64YJ5RTJ6
    /// The text of repo-relative `path`, read once, as git would store it when the work tree file has CRLF ends.
    ///
    /// Symbol spans are measured on the git-normalized text (a CRLF checkout of an LF blob parses as LF),
    /// so a raw CRLF read would drift one byte per line and every attribute scan after the first method
    /// would read the wrong place. Only a file holding a `\r` pays for the git read.
    pub fn get(&mut self, path: &str) -> Option<&str> {
        let root = &self.root;
        self.cache
            .entry(path.to_owned())
            .or_insert_with(|| {
                let raw = std::fs::read_to_string(root.join(path)).ok()?;
                if !raw.contains('\r') {
                    return Some(raw);
                }
                gob_walk::ContentSource::locate(root)
                    .with_reader(|r| r.read_text(path))
                    .ok()
                    .or(Some(raw))
            })
            .as_deref()
    }
}

/// Identifiers directly followed by `(` in `body` (calls and method calls, not macros or `fn`/`def` names).
pub fn called_names(body: &str) -> BTreeSet<String> {
    let bytes = body.as_bytes();
    let mut out = BTreeSet::new();
    let mut i = 0;
    while i < bytes.len() {
        let b = bytes[i];
        if b == b'_' || b.is_ascii_alphabetic() {
            let start = i;
            while i < bytes.len() && (bytes[i] == b'_' || bytes[i].is_ascii_alphanumeric()) {
                i += 1;
            }
            let name = &body[start..i];
            let mut j = i;
            while j < bytes.len() && bytes[j] == b' ' {
                j += 1;
            }
            let before = body[..start].trim_end();
            // frob:ticket 01M43A5MA7GRAACT7E0M525Y1M
            let after_fn = ["fn", "def"].iter().any(|kw| {
                before.strip_suffix(kw).is_some_and(|head| {
                    !head.ends_with(|c: char| c == '_' || c.is_ascii_alphanumeric())
                })
            });
            if bytes.get(j) == Some(&b'(') && !after_fn {
                out.insert(name.to_owned());
            }
        } else {
            i += 1;
        }
    }
    out
}

/// Every function that transitively calls (by unique name) one of `seeds`.
pub fn name_callers(
    graph: &SymbolGraph,
    sources: &mut Sources,
    seeds: &BTreeSet<Symref>,
) -> BTreeSet<Symref> {
    let funcs: Vec<_> = graph
        .records()
        .filter(|r| matches!(r.kind, SymbolKind::Function | SymbolKind::Method))
        .collect();
    let mut count: HashMap<&str, usize> = HashMap::new();
    for r in &funcs {
        if let Some(n) = r.symref.name() {
            *count.entry(n).or_default() += 1;
        }
    }
    let mut callers: HashMap<String, Vec<Symref>> = HashMap::new();
    for r in &funcs {
        let Some(text) = sources.get(r.symref.path()) else {
            continue;
        };
        let range = usize::try_from(u32::from(r.span.start())).unwrap_or(usize::MAX)
            ..usize::try_from(u32::from(r.span.end())).unwrap_or(usize::MAX);
        let Some(body) = text.get(range) else {
            continue;
        };
        for name in called_names(body) {
            if r.symref.name() != Some(name.as_str()) {
                callers.entry(name).or_default().push(r.symref.clone());
            }
        }
    }
    let mut found: BTreeSet<Symref> = BTreeSet::new();
    let mut seen: HashSet<Symref> = HashSet::new();
    let mut queue: VecDeque<Symref> = seeds.iter().cloned().collect();
    while let Some(s) = queue.pop_front() {
        if !seen.insert(s.clone()) {
            continue;
        }
        let Some(name) = s.name() else { continue };
        if count.get(name).copied() != Some(1) {
            continue;
        }
        for c in callers.get(name).into_iter().flatten() {
            found.insert(c.clone());
            queue.push_back(c.clone());
        }
    }
    tracing::debug!(
        seeds = seeds.len(),
        found = found.len(),
        "name-based reach computed"
    );
    found
}

// frob:ticket 01M44YQXS4BXE0X07FBYR0STJ5
/// Byte offset past trivia (whitespace and comments) at or after `i` in `b`.
fn skip_trivia(b: &[u8], mut i: usize) -> usize {
    loop {
        match b.get(i) {
            Some(c) if c.is_ascii_whitespace() => i += 1,
            Some(b'/') if b.get(i + 1) == Some(&b'/') => {
                while b.get(i).is_some_and(|c| *c != b'\n') {
                    i += 1;
                }
            }
            Some(b'/') if b.get(i + 1) == Some(&b'*') => {
                i += 2;
                while i < b.len() && !(b[i] == b'*' && b.get(i + 1) == Some(&b'/')) {
                    i += 1;
                }
                i = (i + 2).min(b.len());
            }
            _ => return i,
        }
    }
}

/// The attribute names of the lists starting at byte `start` of `text`, and the offset after them.
///
/// Namespace qualifiers and the `Attribute` suffix are dropped (`[Foo.BarAttribute(1)]` is `Bar`).
fn leading_attributes(text: &str, start: usize) -> (Vec<String>, usize) {
    let b = text.as_bytes();
    let mut out = Vec::new();
    let mut i = skip_trivia(b, start);
    while b.get(i) == Some(&b'[') {
        let mut depth = 0usize;
        let mut item_start = i + 1;
        let mut j = i;
        let mut items: Vec<&str> = Vec::new();
        while j < b.len() {
            match b[j] {
                b'"' => {
                    j += 1;
                    while j < b.len() && b[j] != b'"' {
                        j += usize::from(b[j] == b'\\') + 1;
                    }
                }
                b'[' | b'(' | b'{' => depth += 1,
                b']' | b')' | b'}' => {
                    depth = depth.saturating_sub(1);
                    if depth == 0 {
                        items.push(&text[item_start..j]);
                        break;
                    }
                }
                b',' if depth == 1 => {
                    items.push(&text[item_start..j]);
                    item_start = j + 1;
                }
                _ => {}
            }
            j += 1;
        }
        for item in items {
            let mut item = item.trim();
            if let Some((target, rest)) = item.split_once(':')
                && !rest.starts_with(':')
                && target.trim().chars().all(char::is_alphanumeric)
            {
                item = rest.trim();
            }
            let head = item.split('(').next().unwrap_or_default().trim();
            let last = head.rsplit('.').next().unwrap_or_default();
            let last = last.strip_suffix("Attribute").unwrap_or(last);
            if !last.is_empty() {
                out.push(last.to_owned());
            }
        }
        i = skip_trivia(b, (j + 1).min(b.len()));
    }
    (out, i)
}

/// The base type names in a type header (`class A<T> : B, I where T : C`), last `.` segment, no generics.
fn header_bases(header: &str) -> Vec<String> {
    let header = header.split(" where ").next().unwrap_or(header);
    // Skip the `class Name<T>(primary)` part: the base list starts at the first top-level ':'.
    let mut depth = 0usize;
    let mut colon = None;
    for (i, c) in header.char_indices() {
        match c {
            '<' | '(' => depth += 1,
            '>' | ')' => depth = depth.saturating_sub(1),
            ':' if depth == 0 => {
                colon = Some(i);
                break;
            }
            _ => {}
        }
    }
    let Some(colon) = colon else {
        return Vec::new();
    };
    let mut out = Vec::new();
    let mut depth = 0usize;
    let mut cur = String::new();
    for c in header[colon + 1..].chars().chain(std::iter::once(',')) {
        match c {
            '<' => depth += 1,
            '>' => depth = depth.saturating_sub(1),
            ',' if depth == 0 => {
                let name = cur.trim().rsplit('.').next().unwrap_or_default().trim();
                if !name.is_empty() {
                    out.push(name.to_owned());
                }
                cur.clear();
            }
            _ if depth == 0 => cur.push(c),
            _ => {}
        }
    }
    out
}

fn span_range(r: &SymbolRecord) -> std::ops::Range<usize> {
    usize::try_from(u32::from(r.span.start())).unwrap_or(usize::MAX)
        ..usize::try_from(u32::from(r.span.end())).unwrap_or(usize::MAX)
}

/// A C# type as the engine-root scan sees it.
struct TypeInfo {
    bases: Vec<String>,
    attributes: Vec<String>,
}

fn type_info(r: &SymbolRecord, sources: &mut Sources) -> Option<TypeInfo> {
    let text = sources.get(r.symref.path())?;
    let span = text.get(span_range(r))?;
    let (attributes, after) = leading_attributes(span, 0);
    let rest = span.get(after..)?;
    let header = rest.split('{').next().unwrap_or(rest);
    Some(TypeInfo {
        bases: header_bases(header),
        attributes,
    })
}

/// True when `name` derives from an engine base through project-local types.
fn derives_from_engine(
    name: &str,
    local: &HashMap<String, Vec<String>>,
    vocab: &EngineVocab,
    seen: &mut HashSet<String>,
) -> bool {
    if vocab.bases.contains(name) {
        return true;
    }
    if !seen.insert(name.to_owned()) {
        return false;
    }
    local
        .get(name)
        .into_iter()
        .flatten()
        .any(|b| derives_from_engine(b, local, vocab, seen))
}

/// The C# methods the engine calls itself: messages on engine-derived types and attribute entry points.
///
/// A message (`Update`, `OnTriggerEnter`) is a root on a type that derives, through project-local
/// bases, from an engine base, or that carries a type attribute such as `CreateAssetMenu`. A method with
/// a method attribute (`MenuItem`) is a root. The static constructor of a type with a type attribute
/// (`InitializeOnLoad`) is a root.
pub fn engine_roots(
    graph: &SymbolGraph,
    sources: &mut Sources,
    vocab: &EngineVocab,
) -> BTreeSet<Symref> {
    let is_cs = |r: &SymbolRecord| {
        Path::new(r.symref.path())
            .extension()
            .is_some_and(|ext| ext.eq_ignore_ascii_case("cs"))
    };
    let mut infos: HashMap<Symref, TypeInfo> = HashMap::new();
    let mut local: HashMap<String, Vec<String>> = HashMap::new();
    for r in graph
        .records()
        .filter(|r| is_cs(r) && matches!(r.kind, SymbolKind::Class | SymbolKind::Struct))
    {
        let Some(info) = type_info(r, sources) else {
            continue;
        };
        if let Some(n) = r.symref.name() {
            local
                .entry(n.to_owned())
                .or_default()
                .extend(info.bases.clone());
        }
        infos.insert(r.symref.clone(), info);
    }
    let mut roots = BTreeSet::new();
    for r in graph
        .records()
        .filter(|r| is_cs(r) && r.kind == SymbolKind::Method)
    {
        let Some(name) = r.symref.name() else {
            continue;
        };
        let parent = r.parent.as_ref().and_then(|p| infos.get(p));
        let engine_type = parent.is_some_and(|t| {
            t.attributes
                .iter()
                .any(|a| vocab.type_attributes.contains(a))
                || t.bases
                    .iter()
                    .any(|b| derives_from_engine(b, &local, vocab, &mut HashSet::new()))
        });
        let mut root = vocab.is_message(name) && engine_type;
        if name == "$cctor" {
            root |= parent.is_some_and(|t| {
                t.attributes
                    .iter()
                    .any(|a| vocab.type_attributes.contains(a))
            });
        }
        if !root && !vocab.method_attributes.is_empty() {
            root = sources
                .get(r.symref.path())
                .and_then(|t| t.get(span_range(r)))
                .is_some_and(|span| {
                    leading_attributes(span, 0)
                        .0
                        .iter()
                        .any(|a| vocab.method_attributes.contains(a))
                });
        }
        if root {
            roots.insert(r.symref.clone());
        }
    }
    tracing::debug!(roots = roots.len(), "engine roots computed");
    roots
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn finds_calls_in_macros_and_methods_but_not_definitions_or_macros() {
        let names =
            called_names("fn go() { assert_eq!(double(2), 4); x.triple(); println!(\"hi\"); }");
        assert!(names.contains("double") && names.contains("triple"));
        assert!(!names.contains("assert_eq") && !names.contains("println"));
        assert!(!names.contains("go"), "{names:?}");
    }

    // frob:tests engine_roots
    #[test]
    fn header_and_attribute_scans_read_c_sharp_declarations() {
        assert_eq!(
            header_bases("public class A<T> : UnityEngine.MonoBehaviour, IFoo<int> where T : C"),
            ["MonoBehaviour", "IFoo"]
        );
        assert!(header_bases("class Plain").is_empty());
        let (attrs, end) = leading_attributes(
            "[MenuItem(\"A/B\"), Foo.BarAttribute]\n[return: X] static void M() {}",
            0,
        );
        assert_eq!(attrs, ["MenuItem", "Bar", "X"]);
        assert!(end > 0);
    }
}

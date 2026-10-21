//! The opt-in `unity` pack as the obligation rules read it: which fields the engine writes.
//!
//! The first vocabulary names engine entry points (COV001 roots). The second names serialized state:
//! a `[SerializeField]` field, or a public instance field of a type deriving from `MonoBehaviour` or
//! `ScriptableObject`, is written from outside the code (scenes, prefabs, the Inspector), so a
//! never-assigned report does not fire for it. With the pack disabled nothing is external.

// frob:ticket 01M44YQY6KR3NCCNGKJ9QK3N9A

use std::collections::{BTreeSet, HashSet};
use std::path::Path;

use frob_tests::reach::{Sources, engine_derived_types, leading_attribute_specs};
use gob_ir::engine::FieldFacts;
use gob_packs::unity::{self, UnityGate, UnityPack};
use gob_symbols::{SymbolGraph, SymbolKind, SymbolRecord, Symref};

/// The pack and the gate that says where it is on, when the root config enables it.
pub(crate) fn enabled_pack(root: &Path) -> Option<(UnityGate, UnityPack)> {
    let Ok(config) = std::fs::read_to_string(root.join("frob.toml")) else {
        return None;
    };
    let gate = match UnityGate::parse("frob.toml", &config) {
        Ok(g) if g.is_enabled() => g,
        Ok(_) => return None,
        Err(e) => {
            tracing::warn!(error = %e, "frob.toml [packs] unreadable; unity pack treated as disabled");
            return None;
        }
    };
    match UnityPack::builtin() {
        Ok(p) => Some((gate, p)),
        Err(e) => {
            tracing::error!(error = %e, "built-in {} pack is invalid", unity::NAME);
            None
        }
    }
}

/// True for a `.cs` record.
fn is_cs(r: &SymbolRecord) -> bool {
    Path::new(r.symref.path())
        .extension()
        .is_some_and(|ext| ext.eq_ignore_ascii_case("cs"))
}

fn is_ident(b: u8) -> bool {
    b.is_ascii_alphanumeric() || b == b'_'
}

/// Names that `text` writes: `x =`, `x += 1`, `x++`, `--x`, `ref x`, `out x`, object initializers.
///
/// The scan is lexical and name-based: a local or parameter of the same name counts as a writer, which
/// only ever hides a report, never invents one. Line comments and string literals are skipped.
fn written_names(text: &str) -> HashSet<&str> {
    const COMPOUND: [&str; 11] = [
        "+=", "-=", "*=", "/=", "%=", "&=", "|=", "^=", "<<=", ">>=", "??=",
    ];
    let b = text.as_bytes();
    let mut out = HashSet::new();
    let mut i = 0;
    while i < b.len() {
        match b[i] {
            b'/' if b.get(i + 1) == Some(&b'/') => {
                while i < b.len() && b[i] != b'\n' {
                    i += 1;
                }
            }
            b'"' => {
                i += 1;
                while i < b.len() && b[i] != b'"' && b[i] != b'\n' {
                    i += usize::from(b[i] == b'\\') + 1;
                }
                i += 1;
            }
            c if is_ident(c) && !c.is_ascii_digit() => {
                let start = i;
                while i < b.len() && is_ident(b[i]) {
                    i += 1;
                }
                let after = text[i..].trim_start_matches([' ', '\t']);
                let before = text[..start].trim_end_matches([' ', '\t']);
                let assigns = (after.starts_with('=')
                    && !after.starts_with("==")
                    && !after.starts_with("=>"))
                    || COMPOUND.iter().any(|op| after.starts_with(op))
                    || after.starts_with("++")
                    || after.starts_with("--")
                    || before.ends_with("++")
                    || before.ends_with("--")
                    || before.ends_with(" ref")
                    || before.ends_with(" out")
                    || before.ends_with("(ref")
                    || before.ends_with("(out");
                if assigns {
                    out.insert(&text[start..i]);
                }
            }
            _ => i += 1,
        }
    }
    out
}

/// One declaration the never-written scan looks at.
struct Candidate {
    symref: Symref,
    name: String,
    initialized: bool,
    facts_owner: Option<Symref>,
    attributes: Vec<String>,
    words: Vec<String>,
    is_property: bool,
}

/// Reads `rec` (a field, or an auto-property carrying `[field: ...]` attributes) as a candidate.
fn candidate(rec: &SymbolRecord, sources: &mut Sources) -> Option<Candidate> {
    let is_property = match rec.kind {
        SymbolKind::Field => false,
        SymbolKind::Property => true,
        _ => return None,
    };
    let name = rec.symref.name()?.to_owned();
    let start = usize::try_from(u32::from(rec.span.start())).ok()?;
    let end = usize::try_from(u32::from(rec.span.end())).ok()?;
    let span = sources.get(rec.symref.path())?.get(start..end)?;
    let (specs, after) = leading_attribute_specs(span, 0);
    let rest = span.get(after..)?;
    let attributes: Vec<String> = specs
        .into_iter()
        .filter(|(target, _)| !is_property || target.as_deref() == Some("field"))
        .map(|(_, n)| n)
        .collect();
    let header_end = rest.find(['=', ';', '{']).unwrap_or(rest.len());
    let words: Vec<String> = rest[..header_end]
        .split(|c: char| !(c.is_alphanumeric() || c == '_'))
        .filter(|w| !w.is_empty())
        .map(str::to_owned)
        .collect();
    let initialized = is_property && {
        let tail = rest.rfind('}').map_or("", |i| rest[i + 1..].trim_start());
        tail.starts_with('=') && !tail.starts_with("==") && !tail.starts_with("=>")
    };
    // An auto-property without a `field:` attribute, or a computed property, is not a field candidate.
    if is_property && (attributes.is_empty() || !rest.contains("get;") && !rest.contains("get ;")) {
        return None;
    }
    Some(Candidate {
        symref: rec.symref.clone(),
        name,
        initialized,
        facts_owner: rec.parent.clone(),
        attributes,
        words,
        is_property,
    })
}

/// C# fields no code assigns and the engine does not write either, sorted.
///
/// A candidate is a field, or an auto-property with `[field: ...]` attributes. It counts as written
/// when its name is assigned anywhere in the repository's `.cs` files (a lexical, name-based scan) or
/// it has an initializer. With the root config's `unity` pack enabled for the file, a serialized field
/// (`[SerializeField]`, or public on a `MonoBehaviour`/`ScriptableObject` type) has an external writer
/// and is not reported; `[NonSerialized]`, static, const and readonly members still are. With the pack
/// disabled every unassigned field is reported.
pub fn never_written_fields(root: &Path, graph: &SymbolGraph) -> Vec<Symref> {
    let mut sources = Sources::new(root);
    let pack = enabled_pack(root);
    let engine_types: BTreeSet<Symref> = match &pack {
        Some((_, p)) => engine_derived_types(graph, &mut sources, &p.vocab),
        None => BTreeSet::new(),
    };
    let mut paths: BTreeSet<&str> = BTreeSet::new();
    let mut candidates = Vec::new();
    for r in graph.records().filter(|r| is_cs(r)) {
        paths.insert(r.symref.path());
        if let Some(c) = candidate(r, &mut sources) {
            candidates.push(c);
        }
    }
    let mut written: HashSet<String> = HashSet::new();
    for p in paths {
        if let Some(text) = sources.get(p) {
            written.extend(written_names(text).into_iter().map(str::to_owned));
        }
    }
    let mut out = Vec::new();
    for c in candidates {
        if c.initialized || written.contains(&c.name) {
            continue;
        }
        let external = pack.as_ref().is_some_and(|(gate, p)| {
            let has = |w: &str| c.words.iter().any(|x| x == w);
            let facts = FieldFacts {
                attributes: &c.attributes,
                is_public: has("public"),
                is_static: has("static"),
                is_const: has("const"),
                is_readonly: has("readonly"),
                is_property: c.is_property,
                owner_is_engine: c
                    .facts_owner
                    .as_ref()
                    .is_some_and(|o| engine_types.contains(o)),
            };
            gate.is_active_for(c.symref.path()) && p.vocab.has_external_writer(&facts)
        });
        if external {
            tracing::debug!(symref = %c.symref, "serialized field has an external writer");
            continue;
        }
        tracing::info!(symref = %c.symref, "field is never written");
        out.push(c.symref);
    }
    out.sort();
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    // frob:tests never_written_fields
    #[test]
    fn written_names_sees_assignments_and_skips_comments_and_equality() {
        let w = written_names(
            "a = 1; b += 2; c++; --d; Foo(ref e); if (f == 1) {} g => 2; // h = 3\nvar s = \"i = 4\"; new X { j = 1 };",
        );
        for n in ["a", "b", "c", "d", "e", "j", "s"] {
            assert!(w.contains(n), "{n} in {w:?}");
        }
        for n in ["f", "g", "h", "i"] {
            assert!(!w.contains(n), "{n} in {w:?}");
        }
    }
}

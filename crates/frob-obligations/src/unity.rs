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
use gob_rules::{Finding, RuleDecl, Severity};
use gob_symbols::{SymbolGraph, SymbolKind, SymbolRecord, Symref};
use gob_text::{FileInterner, Span};

use crate::rules::{unity001::Unity001, unity002::Unity002, unity003::Unity003};
use crate::todo::range;
use crate::util::{def_id, finding_def};

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

// frob:ticket 01M44YQZ1A507E2J3JETAWMMAV
/// What the `.meta` pairing and GUID scan found over a set of tracked paths.
#[derive(Debug, Default, PartialEq, Eq)]
pub(crate) struct MetaReport {
    /// Assets (files and folders) with no tracked `.meta`, sorted.
    pub missing: Vec<String>,
    /// Tracked `.meta` files whose asset is not tracked, sorted.
    pub orphans: Vec<String>,
    /// GUIDs shared by two or more `.meta` files, with the sorted files.
    pub duplicates: Vec<(String, Vec<String>)>,
    /// `.meta` files with a missing or malformed `guid:` line, sorted.
    pub malformed: Vec<String>,
}

/// True when Unity skips `name`: leading dot, trailing `~`, `cvs`, or a `.tmp` extension.
fn unity_ignored_name(name: &str) -> bool {
    name.starts_with('.')
        || name.ends_with('~')
        || name.eq_ignore_ascii_case("cvs")
        || Path::new(name)
            .extension()
            .is_some_and(|e| e.eq_ignore_ascii_case("tmp"))
}

/// True when any slash-separated segment of `path` is a Unity-ignored name.
fn unity_ignored(path: &str) -> bool {
    path.split('/').any(unity_ignored_name)
}

/// The asset roots `.meta` pairing covers: `Assets` and every embedded package under `Packages`.
///
/// A folder under `Packages/` is embedded when it tracks a `package.json`; registry packages live in
/// the untracked `Library/PackageCache`. `Packages/manifest.json` and `packages-lock.json` sit outside
/// any package, so they are never in scope.
fn asset_roots(tracked: &BTreeSet<&str>) -> Vec<String> {
    let mut roots = vec!["Assets".to_owned()];
    for p in tracked {
        let Some(rest) = p.strip_prefix("Packages/") else {
            continue;
        };
        if let Some((pkg, "package.json")) = rest.split_once('/') {
            roots.push(format!("Packages/{pkg}"));
        }
    }
    roots
}

/// The `guid:` value of a `.meta` body, when it is 32 hex digits (lowercased).
fn parse_guid(text: &str) -> Option<String> {
    let v = text.lines().find_map(|l| l.strip_prefix("guid:"))?.trim();
    (v.len() == 32 && v.bytes().all(|b| b.is_ascii_hexdigit())).then(|| v.to_ascii_lowercase())
}

/// Scan `tracked` (repo-relative, slash-separated, git-tracked) for `.meta` problems.
///
/// `read_meta` returns the text of a tracked `.meta`, or `None` when it cannot be read; an unreadable
/// or guid-less `.meta` contributes to `malformed` (readable but bad) and never to duplicates.
pub(crate) fn scan_meta(
    tracked: &[String],
    read_meta: impl Fn(&str) -> Option<String>,
) -> MetaReport {
    let set: BTreeSet<&str> = tracked.iter().map(String::as_str).collect();
    let roots = asset_roots(&set);
    let mut report = MetaReport::default();
    // Every tracked asset or folder under a root, minus the roots themselves.
    let mut assets: BTreeSet<String> = roots.iter().cloned().collect();
    let mut required: BTreeSet<String> = BTreeSet::new();
    let mut metas: Vec<&str> = Vec::new();
    for p in &set {
        let Some(root) = roots.iter().find(|r| {
            p.strip_prefix(r.as_str())
                .is_some_and(|t| t.starts_with('/'))
        }) else {
            continue;
        };
        if unity_ignored(p) {
            tracing::trace!(path = p, "unity-ignored path skipped");
            continue;
        }
        if Path::new(p)
            .extension()
            .is_some_and(|e| e.eq_ignore_ascii_case("meta"))
        {
            metas.push(p);
            continue;
        }
        required.insert((*p).to_owned());
        assets.insert((*p).to_owned());
        let mut dir = *p;
        while let Some((parent, _)) = dir.rsplit_once('/') {
            if parent.len() <= root.len() {
                break;
            }
            required.insert(parent.to_owned());
            assets.insert(parent.to_owned());
            dir = parent;
        }
    }
    for a in &required {
        if !set.contains(format!("{a}.meta").as_str()) {
            tracing::info!(asset = a, "tracked asset has no .meta");
            report.missing.push(a.clone());
        }
    }
    let mut by_guid: std::collections::BTreeMap<String, Vec<String>> =
        std::collections::BTreeMap::default();
    for m in metas {
        let asset = m.strip_suffix(".meta").unwrap_or(m);
        if !assets.contains(asset) {
            tracing::info!(meta = m, "tracked .meta has no tracked asset");
            report.orphans.push(m.to_owned());
        }
        let guid = read_meta(m).as_deref().and_then(parse_guid);
        if let Some(g) = guid {
            by_guid.entry(g).or_default().push(m.to_owned());
        } else {
            tracing::warn!(meta = m, "no readable 32-hex guid in .meta");
            report.malformed.push(m.to_owned());
        }
    }
    report.duplicates = by_guid.into_iter().filter(|(_, f)| f.len() > 1).collect();
    for (g, f) in &report.duplicates {
        tracing::info!(guid = g, files = f.len(), "duplicate guid");
    }
    report
}

/// The git-tracked paths under `root`: `HEAD` plus the staged changes, else a gitignore-aware walk.
pub(crate) fn tracked_paths(root: &Path) -> Vec<String> {
    match tracked_from_git(root) {
        Ok(v) => v,
        Err(why) => {
            tracing::debug!(%why, "no usable git repo for unity .meta scan; walking the tree");
            match gob_walk::walk_paths(root, &gob_walk::WalkConfig::default()) {
                Ok(w) => w.files.into_iter().map(|e| e.path).collect(),
                Err(e) => {
                    tracing::warn!(error = %e, "unity .meta scan could not list files");
                    Vec::new()
                }
            }
        }
    }
}

/// `HEAD` tree adjusted by `HEAD` vs index, when `root` is the work tree of a repo with a commit.
fn tracked_from_git(root: &Path) -> Result<Vec<String>, String> {
    use gob_git::{ChangeKind, Repo, TreeRef};
    let repo = Repo::discover(root).map_err(|e| e.to_string())?;
    let same = repo
        .work_dir()
        .and_then(|w| Some((gob_fs::canonical(w).ok()?, gob_fs::canonical(root).ok()?)))
        .is_some_and(|(a, b)| a == b);
    if !same {
        return Err("root is not the repo work tree".to_owned());
    }
    let mut set: BTreeSet<String> = repo
        .tracked_files_at("HEAD")
        .map_err(|e| e.to_string())?
        .into_iter()
        .collect();
    for c in repo
        .diff_names(&TreeRef::Head, &TreeRef::Index)
        .map_err(|e| e.to_string())?
    {
        match c.kind {
            ChangeKind::Added => set.insert(c.path),
            ChangeKind::Deleted => set.remove(&c.path),
            ChangeKind::Modified => false,
        };
    }
    Ok(set.into_iter().collect())
}

/// The `.meta` report for `root` when the unity pack is enabled; `None` when it is off.
pub(crate) fn meta_report(root: &Path) -> Option<MetaReport> {
    enabled_pack(root)?;
    let tracked = tracked_paths(root);
    tracing::debug!(tracked = tracked.len(), "unity .meta scan");
    Some(scan_meta(&tracked, |m| {
        std::fs::read_to_string(root.join(m)).ok()
    }))
}

/// A finding of `def` anchored at the start of the repo file `path`.
fn at_file(
    def: &gob_rules::RuleDef,
    files: &mut FileInterner,
    path: &str,
    message: String,
    anchor: &str,
) -> Finding {
    let span = Span::new(files.intern(path), range(0, 0));
    finding_def(def, Some(span), message, anchor)
}

/// UNITY001: one finding per tracked asset or folder with no tracked `.meta`.
pub(crate) fn unity001(root: &Path, files: &mut FileInterner) -> Vec<Finding> {
    let Some(r) = meta_report(root) else {
        return Vec::new();
    };
    r.missing
        .iter()
        .map(|a| {
            let msg =
                format!("`{a}` is tracked but `{a}.meta` is not; Unity would assign a fresh guid");
            at_file(Unity001::DEF, files, a, msg, a)
        })
        .collect()
}

/// UNITY002: one finding per tracked `.meta` whose asset is not tracked.
pub(crate) fn unity002(root: &Path, files: &mut FileInterner) -> Vec<Finding> {
    let Some(r) = meta_report(root) else {
        return Vec::new();
    };
    r.orphans
        .iter()
        .map(|m| {
            let msg = format!("`{m}` is tracked but its asset is not");
            at_file(Unity002::DEF, files, m, msg, m)
        })
        .collect()
}

/// UNITY003: one Error per duplicated guid naming every file, plus Unresolved for unreadable guids.
pub(crate) fn unity003(root: &Path, files: &mut FileInterner) -> Vec<Finding> {
    let Some(r) = meta_report(root) else {
        return Vec::new();
    };
    let mut out: Vec<Finding> = r
        .duplicates
        .iter()
        .map(|(guid, metas)| {
            let names = metas
                .iter()
                .map(|m| format!("`{m}`"))
                .collect::<Vec<_>>()
                .join(", ");
            let msg = format!("guid {guid} is shared by {names}");
            at_file(Unity003::DEF, files, &metas[0], msg, guid)
        })
        .collect();
    for m in &r.malformed {
        let span = Span::new(files.intern(m), range(0, 0));
        out.push(Finding::new(
            def_id(Unity003::DEF),
            Severity::Unresolved,
            Some(span),
            format!("`{m}` has no readable 32-hex `guid:` line; duplicates cannot be checked"),
            m,
        ));
    }
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

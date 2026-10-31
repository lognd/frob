//! TOML parsing and validation of `atoms.toml` and `templates.toml`.

use std::collections::{BTreeMap, BTreeSet};

use gob_ir::registry::DetectorKind;
use serde::Deserialize;

use super::model::{AtomDecl, Content, DetectorDecl, TemplateDecl, VocabDecl};
use crate::error::PackError;
use crate::limits::MAX_MANIFEST_BYTES;

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct AtomsFile {
    #[serde(default)]
    #[allow(dead_code)]
    format: Option<u32>,
    #[serde(default)]
    atom: Vec<AtomRow>,
    #[serde(default)]
    vocab: Vec<VocabRow>,
    #[serde(default)]
    detector: Vec<DetectorRow>,
    /// Receiver-family tables, read by the core pack loader in gob-ir.
    #[serde(default)]
    #[allow(dead_code)]
    receiver_family: Vec<toml::Table>,
    /// Non-process crate table, read by the core pack loader in gob-ir.
    #[serde(default)]
    #[allow(dead_code)]
    non_process: Option<toml::Table>,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
#[allow(dead_code)]
struct AtomRow {
    name: String,
    doc: String,
    #[serde(default)]
    aliases: Vec<String>,
    #[serde(default)]
    args: Option<String>,
    #[serde(default)]
    parent: Option<String>,
    #[serde(default)]
    arg_kind: Option<String>,
    #[serde(default)]
    cwe: Vec<String>,
    #[serde(default)]
    severity: BTreeMap<String, String>,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
#[allow(dead_code)]
struct VocabRow {
    lang: String,
    class: String,
    names: Vec<String>,
    #[serde(default)]
    precision: Option<String>,
}

#[derive(Deserialize)]
#[serde(untagged)]
enum Many {
    One(String),
    List(Vec<String>),
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
#[allow(dead_code)]
struct DetectorRow {
    atom: Option<String>,
    atoms: Option<Many>,
    lang: Option<String>,
    langs: Option<Vec<String>>,
    kind: String,
    #[serde(rename = "in")]
    in_: Option<String>,
    reason: Option<String>,
    vocab: Option<String>,
    q: Option<String>,
    args: Option<toml::Table>,
    names: Option<Vec<String>>,
    engine: Option<String>,
    pattern: Option<String>,
    precision: Option<String>,
    cwe: Option<Vec<String>>,
    rationale: Option<String>,
    safer_alternative: Option<String>,
    severity: Option<String>,
    min_fidelity: Option<String>,
    needs: Option<Vec<String>>,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct TemplatesFile {
    #[serde(default)]
    #[allow(dead_code)]
    format: Option<u32>,
    #[serde(default)]
    template: Vec<TemplateRow>,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct TemplateRow {
    name: String,
    atom: String,
    #[serde(rename = "for")]
    for_: String,
    reason: String,
}

fn read<T: for<'de> Deserialize<'de>>(file: &str, text: &str) -> Result<T, PackError> {
    if text.len() > MAX_MANIFEST_BYTES * 16 {
        return Err(PackError::malformed(file, "<file>", "is too large"));
    }
    if !text.is_ascii() {
        return Err(PackError::malformed(file, "<file>", "must be ASCII only"));
    }
    toml::from_str(text).map_err(|e| {
        let line = e.span().map(|s| {
            text[..s.start.min(text.len())]
                .bytes()
                .filter(|&b| b == b'\n')
                .count()
                + 1
        });
        PackError::Malformed {
            file: file.to_owned(),
            key: "<document>".to_owned(),
            line,
            reason: e.message().to_owned(),
        }
    })
}

fn ident_name(s: &str) -> bool {
    !s.is_empty()
        && s.split('.').all(|seg| {
            let mut c = seg.chars();
            c.next().is_some_and(|f| f.is_ascii_lowercase())
                && c.all(|x| x.is_ascii_lowercase() || x.is_ascii_digit() || x == '_')
        })
}

fn kind_of(file: &str, d: &DetectorRow) -> Result<Option<DetectorKind>, PackError> {
    let bad = |why: &str| PackError::malformed(file, "detector.kind", why);
    let need_reason = || {
        d.reason
            .as_deref()
            .is_some_and(|r| !r.trim().is_empty())
            .then_some(())
            .ok_or_else(|| bad("`none` and `impossible` need a non-empty `reason`"))
    };
    Ok(match d.kind.as_str() {
        "callee" => Some(DetectorKind::Callee),
        "attribute" => Some(DetectorKind::Attribute),
        "query" => Some(DetectorKind::Import),
        "pattern" => Some(if d.in_.as_deref() == Some("macro") {
            DetectorKind::Macro
        } else {
            DetectorKind::Pattern
        }),
        "none" => {
            need_reason()?;
            None
        }
        "impossible" => {
            need_reason()?;
            Some(DetectorKind::NotApplicable)
        }
        other => return Err(bad(&format!("unknown kind `{other}`"))),
    })
}

/// Expands the `[[detector]]` rows into one decl per (atom, language).
fn detectors(
    pack: &str,
    atoms_file: &str,
    rows: &[DetectorRow],
    atoms: &[AtomDecl],
    leaves: &[String],
) -> Result<Vec<DetectorDecl>, PackError> {
    let own = |n: &str| atoms.iter().any(|a| a.name == n);
    let mut detectors = Vec::new();
    for d in rows {
        let kind = kind_of(atoms_file, d)?;
        let sel: Vec<String> = match (&d.atom, &d.atoms) {
            (Some(a), None) => vec![a.clone()],
            (None, Some(Many::One(s))) if s == "*" => leaves.to_vec(),
            (None, Some(Many::One(s))) => vec![s.clone()],
            (None, Some(Many::List(l))) => l.clone(),
            _ => {
                return Err(PackError::malformed(
                    atoms_file,
                    "detector.atom",
                    "give exactly one of `atom` and `atoms`",
                ));
            }
        };
        let langs: Vec<String> = match (&d.lang, &d.langs) {
            (Some(l), None) => vec![l.clone()],
            (None, Some(l)) => l.clone(),
            _ => {
                return Err(PackError::malformed(
                    atoms_file,
                    "detector.lang",
                    "give exactly one of `lang` and `langs`",
                ));
            }
        };
        let Some(kind) = kind else { continue };
        for atom in &sel {
            if !own(atom) {
                return Err(PackError::malformed(
                    atoms_file,
                    "detector.atom",
                    format!("`{atom}` is not an atom of pack `{pack}`"),
                ));
            }
            for lang in &langs {
                detectors.push(DetectorDecl {
                    atom: atom.clone(),
                    lang: lang.clone(),
                    kind,
                });
            }
        }
    }
    Ok(detectors)
}

/// Parses `templates.toml` and checks each excuse targets an atom of `pack`.
fn template_decls(
    pack: &str,
    tfile: &str,
    ttext: &str,
    atoms: &[AtomDecl],
) -> Result<Vec<TemplateDecl>, PackError> {
    let own = |n: &str| atoms.iter().any(|a| a.name == n);
    let mut tdecls = Vec::new();
    {
        let t: TemplatesFile = read(tfile, ttext)?;
        let mut seen = BTreeSet::new();
        for r in t.template {
            let bad = |key: &str, why: String| PackError::malformed(tfile, key, why);
            if !ident_name(&r.name) || r.name.contains('.') {
                return Err(bad(
                    "template.name",
                    format!("`{}` is not an ident", r.name),
                ));
            }
            if !seen.insert(r.name.clone()) {
                return Err(bad(
                    "template.name",
                    format!("`{}` is declared twice", r.name),
                ));
            }
            if !own(&r.atom) {
                return Err(bad(
                    "template.atom",
                    format!("`{}` is not an atom of pack `{pack}`", r.atom),
                ));
            }
            if r.reason.trim().is_empty() || r.for_.trim().is_empty() {
                return Err(bad(
                    "template.reason",
                    "`for` and `reason` are mandatory".into(),
                ));
            }
            tdecls.push(TemplateDecl {
                name: r.name,
                atom: r.atom,
                selector: r.for_,
                reason: r.reason,
            });
        }
    }
    Ok(tdecls)
}

/// Parses and cross-checks both files of `pack` into [`Content`].
pub(super) fn content(
    pack: &str,
    atoms_file: &str,
    atoms_text: &str,
    templates: Option<(&str, &str)>,
) -> Result<Content, PackError> {
    let f: AtomsFile = read(atoms_file, atoms_text)?;
    let mut names = BTreeSet::new();
    let mut atoms = Vec::new();
    for a in &f.atom {
        for n in std::iter::once(&a.name).chain(&a.aliases) {
            if !ident_name(n) {
                return Err(PackError::malformed(
                    atoms_file,
                    "atom.name",
                    format!("`{n}` is not dotted snake_case segments"),
                ));
            }
            if !names.insert(n.clone()) {
                return Err(PackError::malformed(
                    atoms_file,
                    "atom.name",
                    format!("`{n}` is declared twice in this pack"),
                ));
            }
        }
        atoms.push(AtomDecl {
            name: a.name.clone(),
            aliases: a.aliases.clone(),
        });
    }
    let leaves: Vec<String> = atoms
        .iter()
        .filter(|a| {
            !atoms
                .iter()
                .any(|b| b.name.strip_prefix(&format!("{}.", a.name)).is_some())
        })
        .map(|a| a.name.clone())
        .collect();
    let detectors = detectors(pack, atoms_file, &f.detector, &atoms, &leaves)?;
    let vocabs = f
        .vocab
        .iter()
        .map(|v| VocabDecl {
            lang: v.lang.clone(),
            class: v.class.clone(),
            names: v.names.clone(),
        })
        .collect();
    let tdecls = match templates {
        Some((tfile, ttext)) => template_decls(pack, tfile, ttext, &atoms)?,
        None => Vec::new(),
    };
    tracing::debug!(
        pack,
        atoms = atoms.len(),
        detectors = detectors.len(),
        "tier-1 content parsed"
    );
    Ok(Content {
        pack: pack.to_owned(),
        atoms,
        vocabs,
        detectors,
        templates: tdecls,
    })
}

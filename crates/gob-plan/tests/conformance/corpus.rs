//! The inputs the conformance run feeds every rule: embedded examples, the std corpus and an
//! adversarial corpus with randomized paths.

// frob:ticket 01M3ZX7HRM8SVB3607V973VQTH

use std::path::{Path, PathBuf};

use gob_plan::grl::ast::{ExampleBody, InputKind, Rule};

use crate::compare::Case;

/// The repository root.
pub fn root() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join("../..")
}

/// The language an example without one is folded in.
const DEFAULT_LANG: &str = "rust";

/// Every example of `rule` that carries a plain source file.
pub fn examples(rule: &Rule) -> Vec<Case> {
    rule.examples
        .iter()
        .enumerate()
        .filter_map(|(i, e)| {
            let text = match &e.body {
                ExampleBody::Source(b) => b.value.clone(),
                ExampleBody::Inputs(items) => items.iter().find_map(|it| match &it.node {
                    InputKind::File { text, .. } => Some(text.value.clone()),
                    _ => None,
                })?,
            };
            Some(Case {
                label: format!("{} example #{i}", rule.id.text),
                lang: e
                    .lang
                    .as_ref()
                    .map_or(DEFAULT_LANG, |w| w.text.as_str())
                    .to_owned(),
                text,
            })
        })
        .collect()
}

fn walk(dir: &Path, out: &mut Vec<PathBuf>) {
    let Ok(rd) = std::fs::read_dir(dir) else {
        return;
    };
    let mut entries: Vec<PathBuf> = rd.filter_map(|e| e.ok().map(|e| e.path())).collect();
    entries.sort();
    for p in entries {
        if p.is_dir() {
            walk(&p, out);
        } else if p.extension().is_some_and(|x| x == "rs") {
            out.push(p);
        }
    }
}

/// The std corpus: the Rust sources of this crate, which carry real markers and directives.
pub fn std_corpus() -> Vec<Case> {
    let mut files = Vec::new();
    walk(
        &Path::new(env!("CARGO_MANIFEST_DIR")).join("src"),
        &mut files,
    );
    files
        .into_iter()
        .filter_map(|p| {
            let text = std::fs::read_to_string(&p).ok()?;
            Some(Case {
                label: p.display().to_string(),
                lang: DEFAULT_LANG.to_owned(),
                text,
            })
        })
        .collect()
}

/// A tiny deterministic generator, so a failure reproduces.
struct Lcg(u64);

impl Lcg {
    fn next(&mut self, n: usize) -> usize {
        self.0 = self
            .0
            .wrapping_mul(6_364_136_223_846_793_005)
            .wrapping_add(1_442_695_040_888_963_407);
        usize::try_from(self.0 >> 33).unwrap_or(0) % n
    }
}

const ATOMS: &[&str] = &[
    "// TODO",
    "/* FIXME */",
    "// XXX",
    "// HACK",
    "// frob:todo 01J9QKX3M8Z4T7N2V5B6C0D1E2",
    "// TODO(01J9QKX3M8Z4T7N2V5B6C0D1E2)",
    "fn f() {}",
    "let s = \"TODO\";",
    "/* TODO",
    "*/",
    "// todo lower",
    "\u{e9}\u{4e2d} // TODO \u{1f600}",
    "\r\n",
    "\t",
    "   ",
    "// frob:tests a::b",
];

/// Seeded adversarial sources: marker comments, directives and odd whitespace in random order,
/// each preceded by a randomized path-like comment.
pub fn adversarial(seed: u64, count: usize) -> Vec<Case> {
    let mut g = Lcg(seed);
    (0..count)
        .map(|n| {
            let mut text = String::new();
            for _ in 0..(1 + g.next(12)) {
                let path = format!("// src/{}/{}.rs", g.next(9999), g.next(9999));
                text.push_str(&path);
                text.push('\n');
                text.push_str(ATOMS[g.next(ATOMS.len())]);
                text.push(if g.next(3) == 0 { ' ' } else { '\n' });
            }
            Case {
                label: format!("adversarial seed {seed} #{n}"),
                lang: DEFAULT_LANG.to_owned(),
                text,
            }
        })
        .collect()
}

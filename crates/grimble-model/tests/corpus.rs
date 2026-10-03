//! The conformance corpus of grmb-spec 12: one case per `X.grmb` + `X.expect` pair or per
//! directory holding an `expect` file. See `tests/corpus/README.md` for the format.

// frob:ticket 01M3Z713VGKF4Z0JJ3263XJMC3

use std::collections::{BTreeMap, BTreeSet};
use std::path::{Path, PathBuf};

use grimble_model::dump::{dump, u_signature};
use grimble_model::fmt::format_file;
use grimble_model::fold::fold_file;
use grimble_model::model::{ModelFiles, PackPin};
use grimble_model::parse::parse_file;
use grimble_model::rules::check_model;

fn corpus_dir() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join("tests/corpus")
}

struct Case {
    name: String,
    /// Repo-style relative path to bytes.
    files: BTreeMap<String, Vec<u8>>,
    expect: String,
    golden: PathBuf,
}

fn collect_files(dir: &Path, base: &Path, out: &mut BTreeMap<String, Vec<u8>>) {
    let mut entries: Vec<_> = std::fs::read_dir(dir)
        .expect("read_dir")
        .flatten()
        .collect();
    entries.sort_by_key(std::fs::DirEntry::path);
    for e in entries {
        let p = e.path();
        if p.is_dir() {
            collect_files(&p, base, out);
        } else if p.extension().is_some_and(|x| x == "grmb") {
            let rel = p
                .strip_prefix(base)
                .expect("under base")
                .to_string_lossy()
                .replace('\\', "/");
            out.insert(rel, std::fs::read(&p).expect("read"));
        }
    }
}

fn discover(dir: &Path, root: &Path, out: &mut Vec<Case>) {
    let mut entries: Vec<_> = std::fs::read_dir(dir)
        .expect("read_dir")
        .flatten()
        .collect();
    entries.sort_by_key(std::fs::DirEntry::path);
    if dir.join("expect").is_file() {
        let mut files = BTreeMap::new();
        collect_files(dir, dir, &mut files);
        out.push(Case {
            name: dir
                .strip_prefix(root)
                .expect("under root")
                .to_string_lossy()
                .into_owned(),
            files,
            expect: std::fs::read_to_string(dir.join("expect")).expect("expect"),
            golden: dir.join("expect.u"),
        });
        return;
    }
    for e in entries {
        let p = e.path();
        if p.is_dir() {
            discover(&p, root, out);
        } else if p.extension().is_some_and(|x| x == "grmb") && p.with_extension("expect").is_file()
        {
            let name = p.file_name().expect("name").to_string_lossy().into_owned();
            let mut files = BTreeMap::new();
            files.insert(name, std::fs::read(&p).expect("read"));
            out.push(Case {
                name: p
                    .strip_prefix(root)
                    .expect("under root")
                    .to_string_lossy()
                    .into_owned(),
                files,
                expect: std::fs::read_to_string(p.with_extension("expect")).expect("expect"),
                golden: p.with_extension("u"),
            });
        }
    }
}

/// What an `expect` file asks for.
struct Expect {
    want: Vec<String>,
    mf: ModelFiles,
    binds: Vec<(String, String, String)>,
    fmt_mode: String,
}

fn parse_expect(c: &Case) -> Expect {
    let mut e = Expect {
        want: Vec::new(),
        mf: ModelFiles::new(),
        binds: Vec::new(),
        fmt_mode: "roundtrip".to_owned(),
    };
    let mut walk: Option<Vec<String>> = None;
    for (path, bytes) in &c.files {
        e.mf = std::mem::take(&mut e.mf).with_file(path, bytes.clone());
    }
    for line in c
        .expect
        .lines()
        .map(str::trim)
        .filter(|l| !l.is_empty() && !l.starts_with('#'))
    {
        let (key, rest) = line.split_once(':').expect("expect line is `key: value`");
        let rest = rest.trim();
        match key {
            "error" | "warn" | "advisory" | "unresolved" => e.want.push(format!("{key}: {rest}")),
            "walk" => {
                walk.get_or_insert_with(Vec::new).extend(
                    rest.split_whitespace()
                        .filter(|w| *w != "none")
                        .map(str::to_owned),
                );
            }
            "rule" => {
                for r in rest.split_whitespace() {
                    e.mf = std::mem::take(&mut e.mf).with_rule(r);
                }
            }
            "roots" if rest == "none" => {
                e.mf = std::mem::take(&mut e.mf).with_declared_roots(Vec::new());
            }
            "root" => e.mf = std::mem::take(&mut e.mf).with_root(rest),
            "pack" => e.mf = std::mem::take(&mut e.mf).with_pack_line(rest),
            "fmt" => rest.clone_into(&mut e.fmt_mode),
            "bind" => {
                let p: Vec<&str> = rest.split_whitespace().collect();
                assert_eq!(p.len(), 3, "bind: FILE ANCHOR VERB in {}", c.name);
                e.binds
                    .push((p[0].to_owned(), p[1].to_owned(), p[2].to_owned()));
            }
            other => panic!("unknown expect key `{other}` in {}", c.name),
        }
    }
    if let Some(w) = walk {
        e.mf = std::mem::take(&mut e.mf).with_walk(w);
    }
    e.want.sort();
    e
}

trait PackLine {
    fn with_pack_line(self, line: &str) -> Self;
}

impl PackLine for ModelFiles {
    /// `pack: ID VERSION [DIGEST] [atoms=a,b]`
    fn with_pack_line(self, line: &str) -> Self {
        let mut it = line.split_whitespace();
        let id = it.next().expect("pack id");
        let mut pin = PackPin {
            version: it.next().expect("pack version").to_owned(),
            digest: None,
            atoms: BTreeSet::new(),
        };
        for extra in it {
            if let Some(a) = extra.strip_prefix("atoms=") {
                pin.atoms.extend(a.split(',').map(str::to_owned));
            } else {
                pin.digest = Some(extra.to_owned());
            }
        }
        self.with_pack(id, pin)
    }
}

/// fmt, round trip and directive bindings of one file; returns problems and its golden dump.
fn check_file(
    (path, bytes): (&str, &[u8]),
    e: &Expect,
    problems: &mut Vec<String>,
    bound: &mut Vec<(String, String, String)>,
) -> String {
    let parsed = parse_file(path, bytes);
    let folded = fold_file(&parsed, "").expect("fold");
    let dumped = format!("=== {path}\n{}\n", dump(&folded));
    match format_file(&parsed) {
        Ok(once) => {
            if e.fmt_mode == "refuses" {
                problems.push(format!("{path}: fmt should refuse"));
            }
            let p2 = parse_file(path, once.as_bytes());
            if format_file(&p2).as_deref() != Ok(once.as_str()) {
                problems.push(format!("{path}: fmt is not idempotent"));
            }
            let f2 = fold_file(&p2, "").expect("fold");
            if u_signature(&folded) != u_signature(&f2) {
                problems.push(format!("{path}: parse(fmt(x)) differs from x in U"));
            }
            if e.fmt_mode == "unchanged" && once.as_bytes() != bytes {
                problems.push(format!("{path}: fmt changed the file:\n{once}"));
            }
        }
        Err(_) if e.fmt_mode == "refuses" || parsed.is_damaged() => {}
        Err(err) => problems.push(format!("{path}: fmt failed: {err}")),
    }
    for d in &folded.directives {
        bound.push((path.to_owned(), d.anchor.clone(), d.hit.qualified()));
    }
    dumped
}

fn run_case(c: &Case) -> Vec<String> {
    let e = parse_expect(c);
    let mut problems = Vec::new();
    let mut got: Vec<String> = check_model(&e.mf)
        .iter()
        .map(|f| format!("{}: {}", format!("{:?}", f.severity).to_lowercase(), f.rule))
        .collect();
    got.sort();
    if got != e.want {
        problems.push(format!(
            "findings differ\n  want {:?}\n  got  {got:?}",
            e.want
        ));
    }
    let mut golden = String::new();
    let mut bound = Vec::new();
    for (path, bytes) in &c.files {
        golden.push_str(&check_file((path, bytes), &e, &mut problems, &mut bound));
    }
    for (file, anchor, verb) in &e.binds {
        let hit = bound
            .iter()
            .any(|(f, a, v)| (file == "-" || f == file) && a == anchor && v == verb);
        if !hit {
            problems.push(format!("no directive {verb} bound to {anchor} in {file}"));
        }
    }
    let bless = std::env::var_os("GRMB_BLESS").is_some();
    if c.golden.is_file() {
        if bless {
            std::fs::write(&c.golden, &golden).expect("bless");
        } else if std::fs::read_to_string(&c.golden).expect("golden") != golden {
            problems.push(format!(
                "U dump differs from {} (GRMB_BLESS=1 rewrites it)",
                c.golden.display()
            ));
        }
    }
    problems
}

#[test]
fn conformance_corpus() {
    let root = corpus_dir();
    let mut cases = Vec::new();
    discover(&root, &root, &mut cases);
    assert!(cases.len() >= 40, "the corpus lost cases: {}", cases.len());
    let mut failures = Vec::new();
    for c in &cases {
        for p in run_case(c) {
            failures.push(format!("[{}] {p}", c.name));
        }
    }
    assert!(
        failures.is_empty(),
        "{} corpus failure(s):\n{}",
        failures.len(),
        failures.join("\n")
    );
}

//! End-to-end remap over a temporary git repository.

// frob:ticket 01M4H0WXVXJ18DX9SVX6EHT0AD

use std::path::Path;
use std::process::Command;

use frob_doc::{MovedMap, RemapError, remap};

const MAP: &str = r#"
[moved]
"docs/design/old.md" = "docs/design/new.md"
"docs/design/old.md#gone" = "docs/design/new.md#fresh"
"docs/design/part.md" = "merged:docs/design/new.md#fresh"
"docs/design/dead.md" = "removed:superseded-by docs/design/new.md"
"docs/design/shelf.md" = "archive:docs/archive/shelf.md"
"#;

fn git(dir: &Path, args: &[&str]) {
    let ok = Command::new("git")
        .args(args)
        .current_dir(dir)
        .status()
        .unwrap()
        .success();
    assert!(ok, "git {args:?}");
}

fn put(dir: &Path, rel: &str, text: &str) {
    let p = dir.join(rel);
    std::fs::create_dir_all(p.parent().unwrap()).unwrap();
    std::fs::write(p, text).unwrap();
}

fn repo(files: &[(&str, &str)]) -> tempfile::TempDir {
    let d = tempfile::tempdir().unwrap();
    git(d.path(), &["init", "-q", "-b", "main"]);
    git(d.path(), &["config", "user.email", "t@example.com"]);
    git(d.path(), &["config", "user.name", "t"]);
    git(d.path(), &["config", "commit.gpgsign", "false"]);
    put(
        d.path(),
        "docs/design/new.md",
        "# New\n\n## Fresh\n\n## 6. Six\n",
    );
    put(d.path(), "docs/archive/shelf.md", "# Shelf\n");
    for (p, t) in files {
        put(d.path(), p, t);
    }
    git(d.path(), &["add", "-A"]);
    git(d.path(), &["commit", "-q", "-m", "init"]);
    d
}

fn plan_for(d: &tempfile::TempDir, map: &str) -> Result<frob_doc::Plan, RemapError> {
    let repo = gob_git::Repo::discover(d.path()).unwrap();
    remap(&repo, d.path(), &MovedMap::parse(map).unwrap())
}

fn text_of<'a>(plan: &'a frob_doc::Plan, path: &str) -> Option<&'a str> {
    plan.changes
        .iter()
        .find(|c| c.path == path)
        .map(|c| c.new_text.as_str())
}

// frob:tests crates/frob-doc/src/plan.rs::remap
#[test]
fn remap_rewrites_every_reference_form_and_spares_tickets_and_notes() {
    let guide = "# Guide\r\n\r\n[a](old.md) [b](old.md#gone) [c](part.md) [d](dead.md) [e](shelf.md#x) [w](https://x.org/old.md)\r\n\r\nSee old.md section 6 and old.md#gone.\r\n\r\n```\r\nold.md section 6\r\n```\r\n\r\n<!-- frob:describes docs/design/old.md#gone -->\r\n";
    let rs = "//! x\n// frob:doc docs/design/old.md#gone\n// frob:doc docs/design/old.md::Sym\n// see docs/design/old.md section 6\nfn f() {}\n";
    let grmb = "# note docs/design/old.md#gone\nref \"docs/design/old.md#gone\"\nref \"docs/design/dead.md\"\n";
    let d = repo(&[
        ("docs/design/guide.md", guide),
        ("crates/x/src/lib.rs", rs),
        ("crates/x/rules/a.grmb", grmb),
        (
            "tickets/T.md",
            "see docs/design/old.md section 6\n[a](../docs/design/old.md)\n",
        ),
        ("notes/n.md", "see docs/design/old.md section 6\n"),
    ]);
    let plan = plan_for(&d, MAP).unwrap();
    let g = text_of(&plan, "docs/design/guide.md").unwrap();
    assert!(g.contains("[a](new.md)"), "{g}");
    assert!(g.contains("[b](new.md#fresh)"), "{g}");
    assert!(g.contains("[c](new.md#fresh)"), "{g}");
    assert!(g.contains("[d](dead.md)"), "{g}");
    assert!(g.contains("[e](../archive/shelf.md#x)"), "{g}");
    assert!(g.contains("https://x.org/old.md"), "{g}");
    assert!(
        g.contains("docs/design/new.md section 6 and docs/design/new.md#fresh."),
        "{g}"
    );
    assert!(
        g.contains("```\r\nold.md section 6\r\n```"),
        "fence kept: {g}"
    );
    assert!(g.contains("frob:describes docs/design/new.md#fresh"), "{g}");
    assert_eq!(g.matches("\r\n").count(), guide.matches("\r\n").count());
    let r = text_of(&plan, "crates/x/src/lib.rs").unwrap();
    assert!(r.contains("frob:doc docs/design/new.md#fresh\n"), "{r}");
    assert!(r.contains("frob:doc docs/design/new.md::Sym"), "{r}");
    assert!(r.contains("docs/design/new.md section 6"), "{r}");
    let m = text_of(&plan, "crates/x/rules/a.grmb").unwrap();
    assert!(m.contains("ref \"docs/design/new.md#fresh\""), "{m}");
    assert!(m.contains("ref \"docs/design/dead.md\""), "{m}");
    assert!(plan.changes.iter().all(|c| !c.path.starts_with("tickets/")));
    assert!(plan.changes.iter().all(|c| !c.path.starts_with("notes/")));
}

// frob:tests crates/frob-doc/src/plan.rs::remap
#[test]
fn remap_is_idempotent_once_applied() {
    let d = repo(&[("docs/guide.md", "[a](design/old.md) old.md section 6\n")]);
    let first = plan_for(&d, MAP).unwrap();
    let new = text_of(&first, "docs/guide.md").unwrap().to_owned();
    put(d.path(), "docs/guide.md", &new);
    assert!(plan_for(&d, MAP).unwrap().changes.is_empty());
}

// frob:tests crates/frob-doc/src/plan.rs::remap
#[test]
fn remap_refuses_rows_whose_target_is_not_a_heading_and_names_them() {
    let d = repo(&[("docs/guide.md", "[a](design/old.md)\n")]);
    let map = "[moved]\n\"docs/design/old.md#a\" = \"docs/design/new.md#nope\"\n\"docs/design/b.md\" = \"docs/design/missing.md\"\n\"docs/design/ok.md\" = \"docs/design/new.md\"\n";
    let Err(RemapError::Refused(rows)) = plan_for(&d, map) else {
        panic!("expected refusal");
    };
    let keys: Vec<&str> = rows.iter().map(|r| r.key.as_str()).collect();
    assert_eq!(keys, ["docs/design/b.md", "docs/design/old.md#a"]);
    assert!(rows[1].value.contains("#nope") && rows[1].reason.contains("nope"));
}

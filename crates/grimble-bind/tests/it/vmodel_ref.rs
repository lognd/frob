//! A vmodel `ref` to a markdown anchor binds by a table-row id or a GitHub heading slug
//! (grmb-spec 4.5.1 rules 1 and 3).

// frob:ticket 01M4FGZ39WXWBRDRHW2ADSY7K8

use std::path::Path;

use grimble_bind::anchors::{ROW_KIND, row_anchors};
use grimble_bind::{BindInput, Binding, Role, Status};
use grimble_model::ModelFiles;

const SPEC: &str = "# Levels\n\n| id | text |\n|---|---|\n| `SPEC-060` | the gate exits 1 |\n| SPEC-061 | second |\n| two words | not an id |\n| SPEC-060 | duplicate |\n\n## The `foo.bar` API\n\ntext\n";

fn write(root: &Path, rel: &str, text: &str) {
    let p = root.join(rel);
    std::fs::create_dir_all(p.parent().expect("a file has a parent")).expect("mkdir");
    std::fs::write(p, text).expect("write");
}

/// Bind a repository holding `docs/spec/L2.md` and a vmodel `req` whose `ref` is `reference`.
fn bind_ref(reference: &str) -> Binding {
    let dir = tempfile::tempdir().expect("tempdir");
    write(dir.path(), "docs/spec/L2.md", SPEC);
    let model = format!(
        "grimble = \"2\";\nmodule m;\nvmodel req {{\n  kind artifact;\n  level requirements;\n  ref \"{reference}\";\n}}\n"
    );
    write(dir.path(), "design/m.grmb", &model);
    let walked = gob_walk::walk(dir.path(), &gob_walk::WalkConfig::default()).expect("walk");
    let files = ModelFiles::new().with_file("design/m.grmb", model.as_bytes().to_vec());
    grimble_bind::bind(&BindInput {
        root: dir.path(),
        entries: &walked.files,
        model: &files,
        modeled: &[],
        strict: false,
        rename_min_tokens: 12,
        ledger_dir: "tickets",
    })
}

/// The identities the `ref` clause bound at Must.
fn bound(b: &Binding) -> Vec<String> {
    b.rows
        .iter()
        .filter(|r| r.role == Role::Ref && r.status == Status::Must)
        .filter_map(|r| r.identity.clone())
        .collect()
}

#[test]
// frob:tests crates/grimble-bind/src/relation.rs::resolve_symref
fn a_table_row_id_anchor_binds() {
    let b = bind_ref("docs/spec/L2.md#spec-060");
    assert_eq!(bound(&b), vec!["docs/spec/L2.md::spec-060".to_owned()]);
    let row = b.rows.iter().find(|r| r.role == Role::Ref).expect("a row");
    assert_eq!(row.unit_kind.as_deref(), Some(ROW_KIND));
    assert!(
        b.findings.iter().all(|f| f.rule != "SYS011"),
        "{:?}",
        b.findings
    );
}

#[test]
// frob:tests crates/grimble-bind/src/relation.rs::resolve_symref
fn a_repeated_row_id_gets_a_suffix_and_a_missing_one_is_sys011() {
    assert_eq!(bound(&bind_ref("docs/spec/L2.md#spec-060-1")).len(), 1);
    let b = bind_ref("docs/spec/L2.md#spec-999");
    assert!(bound(&b).is_empty());
    assert!(
        b.findings.iter().any(|f| f.rule == "SYS011"),
        "{:?}",
        b.findings
    );
}

#[test]
// frob:tests crates/grimble-bind/src/relation.rs::resolve_symref
fn a_heading_with_a_code_span_binds_by_its_github_slug() {
    let b = bind_ref("docs/spec/L2.md#the-foobar-api");
    assert_eq!(
        bound(&b),
        vec!["docs/spec/L2.md::the-foobar-api".to_owned()]
    );
}

#[test]
// frob:tests crates/grimble-bind/src/anchors.rs::row_anchors
fn row_anchor_rules() {
    let t =
        "| id | x |\n|---|---|\n| R-12 | a |\n| `R-12` | b |\n| a b | c |\n| Q {#my_id} | d |\n";
    assert_eq!(row_anchors(t, &[]), vec!["r-12", "r-12-1", "my_id"]);
    assert_eq!(row_anchors(t, &["r-12".to_owned()])[0], "r-12-1");
    let fenced = "```\n| id |\n|---|\n| R-1 |\n```\n";
    assert!(row_anchors(fenced, &[]).is_empty());
}

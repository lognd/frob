//! The guide and `.gitattributes` are installed from templates and refresh on a version change
//! (`navigation.md` 3.1, 4.1).
// frob:ticket 01M3ZX86G8HFRDA78PBVFSTJNW

use std::collections::BTreeMap;

use frob_ledger::r#gen::GENERATORS;
use frob_ledger::r#gen::guide::{TEMPLATES, Template, render_with};
use frob_ledger::reindex::{GenInput, ReindexOptions, Tree, reindex};

fn tree_at(version: &str) -> Tree {
    let opts = ReindexOptions {
        version,
        handle_min_len: 9,
        generators: GENERATORS,
    };
    reindex(&Tree::new(), &opts).expect("reindex").tree
}

fn text(tree: &Tree, path: &str) -> String {
    String::from_utf8(
        tree.get(path)
            .unwrap_or_else(|| panic!("no {path}"))
            .clone(),
    )
    .expect("utf8")
}

#[test]
fn reindex_installs_guide_pages_filled_in_that_name_their_profile_and_link_across() {
    let tree = tree_at("9.9.9");
    let entry = text(&tree, "guide/README.md");
    assert!(
        entry.contains("New here") && entry.contains("Working here"),
        "{entry}"
    );
    for (path, other) in [
        ("guide/new/first-ticket.md", "../work/"),
        ("guide/new/reading-a-ticket.md", "../work/"),
        ("guide/work/how-to.md", "../new/"),
        ("guide/work/why-a-branch.md", "../new/"),
    ] {
        let page = text(&tree, path);
        assert!(
            !page.contains("{{"),
            "unfilled placeholder in {path}: {page}"
        );
        let profile_line = page
            .lines()
            .find(|l| l.starts_with("> Profile:"))
            .expect("profile line");
        assert!(
            page.lines().take(4).any(|l| l == profile_line),
            "profile not at the top of {path}"
        );
        assert!(
            profile_line.contains(other),
            "{path} must link to the other profile"
        );
    }
    assert!(text(&tree, "guide/work/how-to.md").contains("`frob ticket new`"));
    assert!(text(&tree, "guide/work/why-a-branch.md").contains("at least 9 characters"));
    let attrs = text(&tree, ".gitattributes");
    assert!(
        attrs.contains("linguist-generated") && attrs.contains("eol=lf"),
        "{attrs}"
    );
}

// frob:tests crates/frob-ledger/src/gen/guide.rs::render_with
#[test]
fn a_newer_version_changes_each_file_only_by_its_marker_and_the_template_text() {
    let paths = BTreeMap::new();
    let tree = Tree::new();
    let at = |version| GenInput {
        tree: &tree,
        version,
        handle_min_len: 9,
        as_of: None,
        paths: &paths,
    };
    let old = render_with(&at("1.0.0"), TEMPLATES);
    // Same templates, newer version: only the first line differs, except the version placeholder.
    let new = render_with(&at("2.0.0"), TEMPLATES);
    for ((p, a), (_, b)) in old.iter().zip(&new) {
        let (a, b) = (String::from_utf8_lossy(a), String::from_utf8_lossy(b));
        let diff: Vec<usize> = a
            .lines()
            .zip(b.lines())
            .enumerate()
            .filter(|(_, (x, y))| x != y)
            .map(|(i, _)| i)
            .collect();
        assert_eq!(a.lines().count(), b.lines().count(), "{p}");
        assert!(
            diff.first() == Some(&0),
            "{p}: marker must carry the version"
        );
        assert!(
            diff.iter()
                .skip(1)
                .all(|i| a.lines().nth(*i).is_some_and(|l| l.contains("1.0.0"))),
            "{p}: {diff:?}"
        );
    }
    // A changed template shows up as exactly that line.
    let edited = [Template {
        path: "guide/x.md",
        body: "one\ntwo\n",
    }];
    let changed = [Template {
        path: "guide/x.md",
        body: "one\nTWO\n",
    }];
    let a = String::from_utf8(render_with(&at("2.0.0"), &edited).remove(0).1).expect("utf8");
    let b = String::from_utf8(render_with(&at("2.0.0"), &changed).remove(0).1).expect("utf8");
    let diff: Vec<_> = a.lines().zip(b.lines()).filter(|(x, y)| x != y).collect();
    assert_eq!(diff, vec![("two", "TWO")]);
}

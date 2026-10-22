//! Determinism, check-mode and orphan-page tests for the generator.

use std::collections::BTreeSet;
use std::path::Path;

use gob_dev::{GenError, GenFile, Kind, Mode, apply, workspace_root};

/// Generate with frob registered, as the docgen binary does.
fn generate(kind: Kind, crates_dir: &Path) -> Result<Vec<GenFile>, GenError> {
    frob_docgen::register();
    gob_dev::generate(kind, crates_dir)
}

fn crates_dir() -> std::path::PathBuf {
    workspace_root().expect("workspace root").join("crates")
}

fn tree(root: &Path) -> Vec<(String, String)> {
    let mut out = Vec::new();
    let mut stack = vec![root.to_path_buf()];
    while let Some(dir) = stack.pop() {
        for entry in std::fs::read_dir(&dir).expect("read dir") {
            let path = entry.expect("entry").path();
            if path.is_dir() {
                stack.push(path);
            } else {
                let rel =
                    gob_path::Shown::with_home(path.strip_prefix(root).expect("under root"), None)
                        .to_string()
                        .replace('\\', "/");
                out.push((rel, std::fs::read_to_string(&path).expect("read")));
            }
        }
    }
    out.sort();
    out
}

#[test]
fn output_is_deterministic_and_check_passes() {
    let a = tempfile::tempdir().expect("tmp");
    let b = tempfile::tempdir().expect("tmp");
    apply(
        a.path(),
        &generate(Kind::All, &crates_dir()).expect("generate"),
        Mode::Write,
    )
    .expect("write a");
    apply(
        b.path(),
        &generate(Kind::All, &crates_dir()).expect("generate"),
        Mode::Write,
    )
    .expect("write b");
    let (ta, tb) = (tree(a.path()), tree(b.path()));
    assert!(!ta.is_empty());
    assert_eq!(ta, tb, "two runs must be byte-identical");
    assert!(ta.iter().all(|(_, text)| text.is_ascii()));
    let checked = apply(
        a.path(),
        &generate(Kind::All, &crates_dir()).expect("generate"),
        Mode::Check,
    )
    .expect("check");
    assert_eq!(checked.differing, 0);
}

#[test]
fn check_reports_stale_and_missing_files_without_writing() {
    let dir = tempfile::tempdir().expect("tmp");
    let files = generate(Kind::All, &crates_dir()).expect("generate");
    apply(dir.path(), &files, Mode::Write).expect("write");
    let stale = dir.path().join("docs/reference/directives.md");
    std::fs::write(&stale, "stale\n").expect("stale");
    let missing = dir.path().join("docs/schemas/envelope.json");
    std::fs::remove_file(&missing).expect("remove");
    let r = apply(dir.path(), &files, Mode::Check).expect("check");
    assert_eq!(r.differing, 2);
    assert_eq!(std::fs::read_to_string(&stale).expect("read"), "stale\n");
    assert!(!missing.exists(), "check mode writes nothing");
}

// frob:ticket 01M48R04HAG82FJV1T77Z6YH8P
/// Every rule id: the legacy registry plus the declared rules of all products.
fn rule_ids() -> BTreeSet<String> {
    gob_rules::Registry::global()
        .iter()
        .map(|m| m.id.to_owned())
        .chain(
            {
                frob_docgen::register();
                gob_dev::products::all_defs()
            }
            .into_iter()
            .map(|(_, d)| d.id.to_owned()),
        )
        .collect()
}

#[test]
fn every_rule_has_a_page_and_every_page_a_rule() {
    let files = generate(Kind::Rules, &crates_dir()).expect("generate");
    let pages: BTreeSet<String> = files
        .iter()
        .filter_map(|f| f.path.strip_prefix("docs/reference/rules/"))
        .filter_map(|n| n.strip_suffix(".md"))
        .filter(|n| *n != "README")
        .map(str::to_owned)
        .collect();
    let rules = rule_ids();
    assert!(!rules.is_empty());
    assert_eq!(pages, rules);
}

#[test]
fn committed_pages_have_no_orphans_on_disk() {
    let dir = workspace_root()
        .expect("workspace root")
        .join("docs/reference/rules");
    let rules: BTreeSet<String> = rule_ids().iter().map(|id| format!("{id}.md")).collect();
    for entry in std::fs::read_dir(&dir).expect("rules dir exists once generated") {
        let name = gob_path::Shown::with_home(Path::new(&entry.expect("entry").file_name()), None)
            .to_string();
        assert!(
            name == "README.md" || rules.contains(&name),
            "orphan page {name}"
        );
    }
}

// frob:ticket 01M3ZBV60QDKMT4S1YV7F60YEN
/// Neither a gate-side mark table nor a second polarity enum may exist outside gob-rules.
#[test]
fn one_required_reason_and_one_polarity() {
    let needles = [
        ["Required", "Marks"].concat(),
        ["enum ", "Polarity"].concat(),
    ];
    let mut hits = Vec::new();
    let mut stack = vec![crates_dir()];
    while let Some(dir) = stack.pop() {
        for entry in std::fs::read_dir(&dir).expect("read dir") {
            let path = entry.expect("entry").path();
            if path.is_dir() {
                stack.push(path);
            } else if path.extension().is_some_and(|e| e == "rs")
                && !path.starts_with(crates_dir().join("gob-rules"))
                && let Ok(text) = std::fs::read_to_string(&path)
            {
                for n in &needles {
                    if text.contains(n.as_str()) {
                        hits.push(format!(
                            "{} in {}",
                            n,
                            gob_path::Shown::with_home(&path, None)
                        ));
                    }
                }
            }
        }
    }
    assert!(hits.is_empty(), "duplicates outside gob-rules: {hits:?}");
}

// frob:ticket 01M43ARX764095Q4VWABWXXV5H
#[test]
fn crunk_config_reference_and_schema_are_generated_apart_from_frobs() {
    let files = generate(Kind::All, &crates_dir()).expect("generate");
    let get = |path: &str| {
        files
            .iter()
            .find(|f| f.path == path)
            .unwrap_or_else(|| panic!("{path} not generated"))
    };
    assert!(
        get("docs/crunk/config.md")
            .content
            .contains("## `[project]`")
    );
    // frob:ticket 01M43ANVJYA7GHN0Y8GX0SN72M
    assert!(
        get("docs/crunk/config.md")
            .content
            .contains("## `[layers]`"),
        "map tables such as [layers] are documented"
    );
    let rules = get("docs/crunk/rules/README.md");
    assert!(rules.content.starts_with("<!-- GENERATED by "));
    assert!(rules.content.contains("| COLOR001 |"));
    let schema: serde_json::Value =
        serde_json::from_str(&get("docs/schemas/crunk.json").content).expect("valid json");
    assert!(schema["properties"]["project"].is_object());
    // crunk.toml keys must not leak into frob's own config reference or schema.
    assert!(!get("docs/reference/config.md").content.contains("css_root"));
    assert!(!get("docs/schemas/config.json").content.contains("css_root"));
}

// frob:ticket 01M3ZX7DT0J6MRW68P60GAYD3N
/// The catalog page is written by `gen`, is ASCII, and starts with the generated header.
#[test]
fn grl_catalog_page_is_generated() {
    let dir = tempfile::tempdir().expect("tmp");
    let files = generate(Kind::All, &crates_dir()).expect("generate");
    apply(dir.path(), &files, Mode::Write).expect("write");
    let page = std::fs::read_to_string(dir.path().join("docs/reference/grl/catalog.md"))
        .expect("catalog page written");
    assert!(page.starts_with("<!-- GENERATED by frob v"));
    assert!(page.contains("# GRL relation catalog"));
    assert!(page.contains("## Side relations"));
    assert!(page.is_ascii());
}

// frob:ticket 01M3ZX7DT0J6MRW68P60GAYD3N
/// A catalog page that no longer matches the engine's tables is reported stale (GEN001).
#[test]
fn stale_grl_catalog_page_is_reported() {
    let dir = tempfile::tempdir().expect("tmp");
    let files = generate(Kind::All, &crates_dir()).expect("generate");
    apply(dir.path(), &files, Mode::Write).expect("write");
    let page = dir.path().join("docs/reference/grl/catalog.md");
    let old = std::fs::read_to_string(&page).expect("read");
    std::fs::write(&page, old.replace("## Verbs", "## Verbs and one more")).expect("stale");
    let r = apply(dir.path(), &files, Mode::Check).expect("check");
    assert_eq!(r.differing, 1);
}

// frob:ticket 01M3ZX85N2KZ39PG65MX0YT2P0
/// A long hand edit prints a capped diff with a note, and the diff stays under the cap.
#[test]
fn check_prints_a_capped_diff_for_a_hand_edited_page() {
    let big = "line\n".repeat(500);
    let diff = gob_dev::files::unified_diff("p.md", Some(&big), "new\n");
    let capped = gob_dev::files::cap_diff(&diff, gob_dev::files::DIFF_CAP_LINES);
    assert!(capped.lines().count() <= gob_dev::files::DIFF_CAP_LINES + 1);
    assert!(capped.contains("more diff lines not shown"), "{capped}");
    let short = gob_dev::files::cap_diff("a\nb\n", 60);
    assert_eq!(short, "a\nb\n");
}

// frob:ticket 01M3ZX85N2KZ39PG65MX0YT2P0
/// A generated file with no marker, or a marker naming a missing command, is reported; orphans too.
#[test]
fn check_reports_missing_markers_unknown_commands_and_orphans() {
    let dir = tempfile::tempdir().expect("tmp");
    let files = generate(Kind::All, &crates_dir()).expect("generate");
    apply(dir.path(), &files, Mode::Write).expect("write");
    let clean = apply(dir.path(), &files, Mode::Check).expect("check");
    assert_eq!((clean.differing, clean.marker_problems), (0, 0));

    let bare = dir.path().join("docs/reference/directives.md");
    let text = std::fs::read_to_string(&bare).expect("read");
    std::fs::write(&bare, text.replacen("GENERATED by", "made by hand", 1)).expect("strip marker");
    let wrong = dir.path().join("docs/reference/config.md");
    let text = std::fs::read_to_string(&wrong).expect("read");
    std::fs::write(&wrong, text.replacen("gen config.", "gen nosuchthing.", 1))
        .expect("bad command");
    std::fs::write(
        dir.path().join("docs/reference/old-page.md"),
        "<!-- GENERATED by frob v0.0.0: DO NOT EDIT. Regenerate: cargo dev gen rules. Source: x -->\n# old\n",
    )
    .expect("orphan");
    let r = apply(dir.path(), &files, Mode::Check).expect("check");
    assert_eq!(r.marker_problems, 3, "{r:?}");
    assert_eq!(
        gob_dev::files::marker_problem("# x\n").as_deref(),
        Some("no generated marker in the first lines")
    );
    assert!(
        gob_dev::files::marker_problem(
            "<!-- GENERATED by frob v1: DO NOT EDIT. Regenerate: cargo dev gen zzz. Source: x -->\n"
        )
        .is_some_and(|p| p.contains("`cargo dev gen zzz`"))
    );
    assert_eq!(
        gob_dev::files::marker_problem(
            "<!-- GENERATED by frob v1: DO NOT EDIT. Regenerate: cargo dev gen rules. Source: x -->\n"
        ),
        None
    );
}

// frob:ticket 01M4MAQ5JFANPHZ0SJ690R68TZ
/// Every generated markdown page opens with the three-field marker and has the visible line right after its title.
#[test]
fn generated_pages_carry_the_versioned_marker_and_visible_line() {
    let files = generate(Kind::All, &crates_dir()).expect("generate");
    let version = gob_dev::render::GENERATOR_VERSION;
    let mut pages = 0;
    for f in files.iter().filter(|f| {
        f.path
            .rsplit('.')
            .next()
            .is_some_and(|e| e.eq_ignore_ascii_case("md"))
    }) {
        let mut lines = f.content.lines();
        let first = lines.next().unwrap_or_default();
        let want =
            format!("<!-- GENERATED by frob v{version}: DO NOT EDIT. Regenerate: cargo dev gen ");
        assert!(first.starts_with(&want), "{}: {first}", f.path);
        assert!(
            first.contains(". Source: ") && first.ends_with(" -->"),
            "{}",
            f.path
        );
        let rest: Vec<&str> = lines.collect();
        let title = rest
            .iter()
            .position(|l| l.starts_with("# "))
            .expect("title");
        assert_eq!(rest[title + 1], "", "{}", f.path);
        assert!(
            rest[title + 2].starts_with("> Generated: "),
            "{}: {}",
            f.path,
            rest[title + 2]
        );
        pages += 1;
    }
    assert!(pages > 50, "{pages}");
}

// frob:ticket 01M4MAQ5JFANPHZ0SJ690R68TZ
/// A marker recording another generator version is a stale-version warning; the current version is silent.
#[test]
fn stale_marker_version_warns() {
    use gob_dev::files::{marker_version, stale_version};
    let old = "<!-- GENERATED by frob v0.1.0: DO NOT EDIT. Regenerate: cargo dev gen cli. Source: x -->\n";
    assert_eq!(marker_version(old), Some("0.1.0"));
    assert!(stale_version(old, "0.2.0").is_some_and(|w| w.contains("v0.1.0")));
    assert_eq!(stale_version(old, "0.1.0"), None);
    assert_eq!(stale_version("# plain\n", "0.2.0"), None);
}

// frob:ticket 01M4NWPZHG4X7QEJKETA5JNS96
/// Relative links are extracted without fragments, externals or fenced code.
#[test]
fn relative_links_skip_externals_fragments_and_fences() {
    let text = "[a](x/y.md#h) [b](https://e.com/z) [c](#top) [d](../q.md)\n```\n[e](no.md)\n```\n";
    assert_eq!(
        gob_dev::files::relative_links(text),
        vec!["x/y.md".to_owned(), "../q.md".to_owned()]
    );
}

// frob:ticket 01M4NWPZHG4X7QEJKETA5JNS96
/// A dangling relative link and a page missing from SUMMARY.md are GEN001 marker problems.
#[test]
fn check_reports_dangling_links_and_pages_missing_from_summary() {
    let dir = tempfile::tempdir().expect("tmp");
    let marker = "<!-- GENERATED by frob v0.0.0: DO NOT EDIT. Regenerate: cargo dev gen rules. Source: x -->\n";
    let files = vec![gob_dev::files::GenFile {
        path: "docs/reference/a.md".to_owned(),
        content: format!("{marker}# a\n[ok](b.md) [bad](gone.md)\n"),
    }];
    apply(dir.path(), &files, Mode::Write).expect("write");
    std::fs::write(dir.path().join("docs/reference/b.md"), "# b\n").expect("b");
    let r = apply(dir.path(), &files, Mode::Check).expect("check");
    assert_eq!(r.marker_problems, 1, "{r:?}");

    std::fs::write(
        dir.path().join("docs/SUMMARY.md"),
        "- [a](reference/a.md)\n",
    )
    .expect("summary");
    let r = apply(dir.path(), &files, Mode::Check).expect("check");
    assert_eq!(r.marker_problems, 2, "b.md is not in SUMMARY: {r:?}");
}

// frob:ticket 01M48FXFZMWWZQ233HYSPZ6PP9
#[test]
// frob:tests crates/gob-dev/src/render/languages.rs::generate
fn languages_kind_writes_the_page_and_check_detects_drift() {
    let dir = tempfile::tempdir().expect("tmp");
    let files = generate(Kind::Languages, &crates_dir()).expect("generate");
    assert_eq!(files.len(), 1);
    assert_eq!(files[0].path, "docs/reference/languages.md");
    apply(dir.path(), &files, Mode::Write).expect("write");
    let page = dir.path().join("docs/reference/languages.md");
    assert!(
        std::fs::read_to_string(&page)
            .expect("read")
            .contains("## Extensions")
    );
    assert_eq!(
        apply(dir.path(), &files, Mode::Check)
            .expect("check")
            .differing,
        0
    );
    std::fs::write(&page, "stale\n").expect("stale");
    let drift = apply(dir.path(), &files, Mode::Check).expect("check");
    assert_eq!(drift.differing, 1);
    assert_eq!(std::fs::read_to_string(&page).expect("read"), "stale\n");
}

// frob:ticket 01M48FXFZMWWZQ233HYSPZ6PP9
#[test]
// frob:tests crates/gob-dev/src/render/languages.rs::generate
fn languages_regeneration_is_idempotent_and_leaves_an_equal_page_untouched() {
    let dir = tempfile::tempdir().expect("tmp");
    let files = generate(Kind::Languages, &crates_dir()).expect("generate");
    apply(dir.path(), &files, Mode::Write).expect("first write");
    let page = dir.path().join("docs/reference/languages.md");
    let before = std::fs::metadata(&page)
        .expect("meta")
        .modified()
        .expect("mtime");
    let again = apply(dir.path(), &files, Mode::Write).expect("second write");
    assert_eq!(again.differing, 0, "an equal page is not rewritten");
    let after = std::fs::metadata(&page)
        .expect("meta")
        .modified()
        .expect("mtime");
    assert_eq!(before, after);
    assert!(std::fs::read_to_string(&page).expect("read").is_ascii());
}

// frob:ticket 01M48FXFZMWWZQ233HYSPZ6PP9
#[test]
// frob:tests crates/gob-dev/src/render/languages.rs::generate
fn committed_languages_page_matches_the_generator() {
    let root = workspace_root().expect("workspace root");
    let files = generate(Kind::Languages, &crates_dir()).expect("generate");
    let committed = std::fs::read_to_string(root.join(&files[0].path)).expect("committed page");
    assert_eq!(committed, files[0].content, "run `cargo dev gen languages`");
    assert_eq!(gob_dev::files::marker_problem(&committed), None);
}

// frob:ticket 01M4CXTR91E8Y8Y52B5ARDPKKS
#[test]
// frob:tests crates/gob-dev/src/render/cli.rs::generate
fn cli_reference_has_a_stable_page_per_product() {
    let first = generate(Kind::Cli, &crates_dir()).expect("generate");
    let second = generate(Kind::Cli, &crates_dir()).expect("generate");
    let paths: Vec<&str> = first.iter().map(|f| f.path.as_str()).collect();
    for want in ["frob", "grimble", "crunk"] {
        let path = format!("docs/reference/cli/{want}.md");
        assert!(paths.contains(&path.as_str()), "{path} missing: {paths:?}");
        let page = first.iter().find(|f| f.path == path).expect("page");
        assert!(page.content.contains(&format!("# `{want}` commands")));
        assert!(page.content.contains("| `check` |"), "{path} lists check");
    }
    let a: Vec<(&str, &str)> = first
        .iter()
        .map(|f| (f.path.as_str(), f.content.as_str()))
        .collect();
    let b: Vec<(&str, &str)> = second
        .iter()
        .map(|f| (f.path.as_str(), f.content.as_str()))
        .collect();
    assert_eq!(a, b, "generation is deterministic");
    let grimble = first
        .iter()
        .find(|f| f.path.ends_with("grimble.md"))
        .expect("grimble");
    assert!(
        !grimble.content.contains("| `dtcg"),
        "crunk verbs do not leak into the grimble page"
    );
}

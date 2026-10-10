//! The provider registry feeds the `--provider` flag, and the `allowed_tools` default matches what the docs state (~1FSGW5S).

// frob:ticket 01M4FD31PPJCEBG5G351FSGW5S

use std::path::Path;

use frob_evidence::EvidenceTable;
use frob_evidence::record::Provider;

fn run_add(args: &[&str]) -> (i32, String, String) {
    let cli = frob_evidence::register(gob_cli::Cli::new("frob", "0.0.0"));
    let dir = tempfile::tempdir().expect("tempdir");
    gob_cli::run_for_test(&cli, args, dir.path())
}

#[test]
fn every_registered_provider_is_accepted_by_the_flag_and_none_is_missing() {
    // frob:tests crates/frob-evidence/src/record.rs::Provider.expected
    for name in Provider::NAMES {
        let (_, out, err) = run_add(&[
            "--json",
            "ticket",
            "evidence",
            "add",
            "~NOPE",
            "--provider",
            name,
            "--ref",
            "x",
        ]);
        assert!(
            !format!("{out}{err}").contains("invalid value"),
            "`--provider {name}` must parse: {out}{err}"
        );
        assert_eq!(name.parse::<Provider>().expect("parses").as_str(), *name);
    }
    for dotnet in ["dotnet", "vitest", "jest", "pytest"] {
        assert!(Provider::NAMES.contains(&dotnet), "{dotnet}");
    }
    let (code, out, err) = run_add(&[
        "ticket",
        "evidence",
        "add",
        "~NOPE",
        "--provider",
        "bogus",
        "--ref",
        "x",
    ]);
    assert_eq!(code, 2, "{out}{err}");
    for name in Provider::NAMES {
        assert!(
            format!("{out}{err}").contains(name),
            "the rejection lists `{name}`: {out}{err}"
        );
    }
    let message = frob_evidence::EvidenceError::BadProvider("bogus".to_owned()).to_string();
    assert!(message.ends_with(&format!("expected {}", Provider::expected())));
    assert!(Provider::expected().contains("dotnet"));
}

/// The first line of `path` (from the workspace root) containing `needle`.
fn doc_line(path: &str, needle: &str) -> String {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let text = std::fs::read_to_string(root.join(path)).expect("doc file");
    text.lines()
        .find(|l| l.contains(needle))
        .unwrap_or_else(|| panic!("{path} has no line with {needle}"))
        .to_owned()
}

#[test]
fn the_allowed_tools_default_is_the_documented_list_and_includes_dotnet() {
    // frob:tests crates/frob-evidence/src/config.rs::EvidenceTable
    let tools = EvidenceTable::default().allowed_tools;
    assert_eq!(
        tools,
        ["cargo", "git", "pytest", "vitest", "jest", "dotnet"],
        "update docs/reference/config.md and docs/guides/quickstart.md with the default"
    );
    let reference = doc_line("docs/reference/config.md", "| `allowed_tools` |");
    let quickstart = doc_line("docs/guides/quickstart.md", "by default `cargo`");
    let mut at = 0;
    for tool in &tools {
        let quoted = format!("\"{tool}\"");
        at += reference[at..]
            .find(&quoted)
            .unwrap_or_else(|| panic!("config.md lacks {quoted} in order: {reference}"));
        assert!(
            quickstart.contains(&format!("`{tool}`")),
            "quickstart lacks `{tool}`: {quickstart}"
        );
    }
}

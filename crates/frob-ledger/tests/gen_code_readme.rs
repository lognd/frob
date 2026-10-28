//! The generated tickets region of the code repository's README (`navigation.md` 3.2).
// frob:ticket 01M3ZX87403VR4YVK4QMJ7KPBV

use frob_ledger::r#gen::code_readme::{
    BEGIN, END, Home, RegionDrift, RegionError, RegionSettings, apply, check, render,
};

fn settings(base: Option<&str>) -> RegionSettings<'_> {
    RegionSettings {
        home: Home::Branch("frob-tickets"),
        web_base: base,
    }
}

#[test]
fn the_region_names_the_branch_the_three_commands_and_the_tracker() {
    let region = render(&settings(Some("https://example.com/o/r")));
    assert!(
        region.starts_with(BEGIN) && region.ends_with(END),
        "{region}"
    );
    assert!(region.contains("https://example.com/o/r/tree/frob-tickets"));
    for cmd in ["frob ticket doable", "frob work ~HANDLE", "frob land"] {
        assert!(region.contains(cmd), "{cmd}");
    }
    assert!(region.contains("https://example.com/o/r/issues"));
    assert!(!render(&settings(None)).contains("issues"));
}

#[test]
fn applying_changes_only_the_bytes_between_the_markers() {
    let stale = format!("# Title\n\nintro\n\n{BEGIN}\nold text\n{END}\n\nhand-written tail\n");
    let region = render(&settings(None));
    let out = apply(&stale, &region).expect("apply");
    assert_eq!(
        out,
        format!("# Title\n\nintro\n\n{region}\n\nhand-written tail\n")
    );
    assert_eq!(apply(&out, &region).expect("again"), out, "idempotent");
}

#[test]
fn a_readme_without_a_region_gets_one_appended() {
    let region = render(&settings(None));
    let out = apply("# Title\n\ntext\n", &region).expect("apply");
    assert_eq!(out, format!("# Title\n\ntext\n\n{region}\n"));
    assert_eq!(check("# Title\n", &region), Err(RegionDrift::Missing));
}

// frob:tests crates/frob-ledger/src/gen/code_readme.rs::RegionDrift.rule
#[test]
fn a_hand_edit_inside_the_region_is_reported_as_gen001() {
    let region = render(&settings(None));
    let good = apply("intro\n", &region).expect("apply");
    assert_eq!(check(&good, &region), Ok(()));
    let edited = good.replace("pick a ticket", "pick any ticket");
    let drift = check(&edited, &region).expect_err("edit must be reported");
    assert_eq!(drift, RegionDrift::Edited);
    assert_eq!(drift.rule(), "GEN001");
    assert_eq!(
        check(&good.replace("\nintro", "\nintro, edited"), &region),
        Ok(())
    );
}

#[test]
fn unpaired_or_repeated_markers_are_refused() {
    let region = render(&settings(None));
    assert_eq!(
        apply(&format!("{BEGIN}\nx\n"), &region),
        Err(RegionError::Unpaired)
    );
    assert_eq!(
        apply(&format!("{END}\n{BEGIN}\n"), &region),
        Err(RegionError::Unpaired)
    );
    let twice = format!("{region}\n{region}\n");
    assert_eq!(apply(&twice, &region), Err(RegionError::Duplicate));
}

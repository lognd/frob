//! Secret masking for captured output and telemetry.

use std::borrow::Cow;
use std::sync::LazyLock;

use regex::Regex;

/// Marker substituted for every masked secret.
pub const REDACTED: &str = "[REDACTED]";

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
    vec![
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
            r#"(?i)(\b[A-Za-z0-9_.-]*(?:TOKEN|SECRET|PASSWORD|PASSWD)[A-Za-z0-9_.-]*[ \t]*=[ \t]*)("[^"]*"|'[^']*'|[^\s"']+)"#,
            "${1}{M}",
        ),
    ]
});

/// Masks secret-shaped substrings in `text`, leaving all other bytes identical.
///
/// Covers bearer tokens, AWS access keys, GitHub tokens, URL userinfo, and
/// `KEY=VALUE` pairs whose key contains TOKEN, SECRET, PASSWORD or PASSWD
/// (case-insensitive). Borrows when nothing matched.
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

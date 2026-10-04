//! The redaction engine: one matcher for home paths (built in) and user-defined private terms.
//!
//! Private terms are the names a user must not publish (a machine, a person, a customer). Listing them
//! in a committed file would publish them, so rules come from local-only files and nothing here writes
//! one into a work tree:
//!
//! - the user file `<platform config dir>/frob/privacy.toml`, and
//! - the repository file `<git common dir>/frob/privacy.toml`,
//!
//! merged (user rules first). Each file holds `[[rule]]` tables of `pattern`, `replace` (the label a
//! match becomes), `regex` (default false) and `case_sensitive` (default true).
//!
//! A matched term is never echoed: every message, log line and audit event names the rule's `replace`
//! label and a short hash of its pattern ([`Hit`]). The built-in home-path rule shares detection and
//! audit with the private rules; its rewrite stays with the caller's path scrub (the evidence crate).

use std::path::Path;

use gob_rules::{Finding, Severity};
use regex::Regex;

use crate::privacy::find_home_path;
use crate::rules::{Tick005, id_of};

// frob:ticket 01M42EZ8J63P84XFKTR2GXRW72

/// File name of the local-only rules, in the user config directory and in the git common dir.
pub const FILE_NAME: &str = "privacy.toml";
/// Product directory name below the config dir and the git common dir.
pub const PRODUCT_DIR: &str = "frob";
/// Label of the built-in home-path rule.
pub const HOME_LABEL: &str = "home-path";
/// Hex characters of a pattern hash kept in messages and audit events.
const HASH_LEN: usize = 12;

/// A rule file that cannot be used; never carries a pattern.
#[derive(Debug, Clone, PartialEq, Eq, thiserror::Error)]
#[error("E-REDACT-CONFIG: {source_name}: {why}")]
pub struct RedactError {
    /// The file or source label.
    pub source_name: String,
    /// What is wrong, without any pattern text.
    pub why: String,
}

/// One `[[rule]]` table as written in a privacy file.
#[derive(Debug, serde::Deserialize)]
#[serde(deny_unknown_fields)]
struct RuleSpec {
    pattern: String,
    replace: String,
    #[serde(default)]
    regex: bool,
    #[serde(default = "yes")]
    case_sensitive: bool,
}

fn yes() -> bool {
    true
}

/// A privacy file: a list of `[[rule]]` tables.
#[derive(Debug, Default, serde::Deserialize)]
#[serde(deny_unknown_fields)]
struct FileSpec {
    #[serde(default)]
    rule: Vec<RuleSpec>,
}

/// What a rule matches with.
#[derive(Clone)]
enum Matcher {
    /// The built-in absolute-home-path matcher ([`find_home_path`]).
    Home,
    /// A user pattern, literals escaped, compiled once.
    Pattern(Regex),
}

/// One redaction rule.
#[derive(Clone)]
pub struct Rule {
    label: String,
    hash: String,
    matcher: Matcher,
}

impl std::fmt::Debug for Rule {
    /// Prints the label and hash only, so a logged rule set never carries a term.
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "Rule({}#{})", self.label, self.hash)
    }
}

/// Which rule matched: its label and the hash of its pattern, never the matched text.
#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord)]
pub struct Hit {
    /// The rule's `replace` label.
    pub label: String,
    /// Short blake3 hash of the rule's pattern.
    pub hash: String,
    /// True for the built-in home-path rule.
    pub builtin: bool,
}

impl std::fmt::Display for Hit {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}#{}", self.label, self.hash)
    }
}

impl Rule {
    fn hit(&self) -> Hit {
        Hit {
            label: self.label.clone(),
            hash: self.hash.clone(),
            builtin: matches!(self.matcher, Matcher::Home),
        }
    }

    fn matches(&self, text: &str) -> bool {
        match &self.matcher {
            Matcher::Home => find_home_path(text.as_bytes()).is_some(),
            Matcher::Pattern(re) => re.is_match(text),
        }
    }
}

fn short_hash(pattern: &str) -> String {
    let mut h = blake3::hash(pattern.as_bytes()).to_hex().to_string();
    h.truncate(HASH_LEN);
    h
}

/// An ordered set of redaction rules.
#[derive(Debug, Clone, Default)]
pub struct RuleSet {
    rules: Vec<Rule>,
}

impl RuleSet {
    /// A set with no rules.
    pub fn empty() -> Self {
        Self::default()
    }

    /// Rules parsed from the text of one privacy file; `source_name` labels errors.
    ///
    /// # Errors
    ///
    /// [`RedactError`] for malformed TOML, an empty pattern or label, a bad regex, or a label that
    /// itself matches its rule (the scrub would never settle). The error never carries a pattern.
    pub fn from_toml(text: &str, source_name: &str) -> Result<Self, RedactError> {
        let bad = |why: String| RedactError {
            source_name: source_name.to_owned(),
            why,
        };
        let spec: FileSpec = toml::from_str(text).map_err(|e| {
            // toml errors quote the offending source line, which may be a pattern: report only the span.
            let at = e
                .span()
                .map_or_else(String::new, |s| format!(" at byte {}", s.start));
            bad(format!("not a valid privacy file{at}"))
        })?;
        let mut rules = Vec::with_capacity(spec.rule.len());
        for (i, r) in spec.rule.iter().enumerate() {
            let n = i + 1;
            if r.pattern.is_empty() || r.replace.is_empty() {
                return Err(bad(format!(
                    "rule {n}: pattern and replace must be non-empty"
                )));
            }
            let body = if r.regex {
                r.pattern.clone()
            } else {
                regex::escape(&r.pattern)
            };
            let flagged = if r.case_sensitive {
                body
            } else {
                format!("(?i){body}")
            };
            let re = Regex::new(&flagged)
                .map_err(|_| bad(format!("rule {n}: pattern is not a valid regex")))?;
            if re.is_match(&r.replace) {
                return Err(bad(format!(
                    "rule {n}: replace label matches its own pattern"
                )));
            }
            rules.push(Rule {
                label: r.replace.clone(),
                hash: short_hash(&r.pattern),
                matcher: Matcher::Pattern(re),
            });
        }
        tracing::debug!(
            source = source_name,
            rules = rules.len(),
            "privacy rules parsed"
        );
        Ok(Self { rules })
    }

    /// The two local rule files for a repository (user, then git common dir), present or not.
    pub fn local_paths(common_dir: &Path) -> Vec<std::path::PathBuf> {
        gob_config::user_file(PRODUCT_DIR, FILE_NAME)
            .into_iter()
            .chain(std::iter::once(gob_config::repo_file(
                common_dir,
                PRODUCT_DIR,
                FILE_NAME,
            )))
            .collect()
    }

    /// Log where private-term rules are read from, for `frob init` and `frob doctor` (local-only; never committed).
    pub fn mention_local_files(common_dir: &Path) {
        for p in Self::local_paths(common_dir) {
            tracing::info!(path = %p.display(), present = p.is_file(), "private-term rules file (local-only, never committed)");
        }
    }

    /// The local rules of a repository: the user file then the git-common-dir file, merged. Absent files are empty.
    ///
    /// # Errors
    ///
    /// [`RedactError`] when a present file cannot be read or parsed (writes then refuse: fail closed).
    pub fn load_local(common_dir: &Path) -> Result<Self, RedactError> {
        let mut out = Self::empty();
        for path in Self::local_paths(common_dir) {
            let label = format!(
                "<{}>/{}/{FILE_NAME}",
                if path.starts_with(common_dir) {
                    "git-dir"
                } else {
                    "user-config"
                },
                PRODUCT_DIR
            );
            let text = match std::fs::read_to_string(&path) {
                Ok(t) => t,
                Err(e) if e.kind() == std::io::ErrorKind::NotFound => continue,
                Err(e) => {
                    return Err(RedactError {
                        source_name: label,
                        why: format!("cannot read: {}", e.kind()),
                    });
                }
            };
            out.rules.extend(Self::from_toml(&text, &label)?.rules);
        }
        tracing::info!(rules = out.rules.len(), "local privacy rules loaded");
        Ok(out)
    }

    /// This set plus the built-in home-path rule, for detection and repair.
    #[must_use]
    pub fn with_home_path(mut self) -> Self {
        if !self
            .rules
            .iter()
            .any(|r| matches!(r.matcher, Matcher::Home))
        {
            self.rules.push(Rule {
                label: HOME_LABEL.to_owned(),
                hash: short_hash(HOME_LABEL),
                matcher: Matcher::Home,
            });
        }
        self
    }

    /// True when there is no private rule (the built-in rule does not count).
    pub fn no_private(&self) -> bool {
        self.rules
            .iter()
            .all(|r| matches!(r.matcher, Matcher::Home))
    }

    /// Every rule that matches `bytes` (lossy UTF-8), in rule order; the built-in rule included when present.
    pub fn hits(&self, bytes: &[u8]) -> Vec<Hit> {
        let text = String::from_utf8_lossy(bytes);
        self.rules
            .iter()
            .filter(|r| r.matches(&text))
            .map(Rule::hit)
            .collect()
    }

    /// The first private (non-built-in) rule matching `text`.
    pub fn first_private_hit(&self, text: &str) -> Option<Hit> {
        self.rules
            .iter()
            .filter(|r| matches!(r.matcher, Matcher::Pattern(_)))
            .find(|r| r.matches(text))
            .map(Rule::hit)
    }

    /// `text` with every private match replaced by its rule's label; the built-in rule is the caller's path scrub.
    pub fn apply_private(&self, text: &str) -> String {
        let mut out = text.to_owned();
        for r in &self.rules {
            if let Matcher::Pattern(re) = &r.matcher {
                out = re.replace_all(&out, regex::NoExpand(&r.label)).into_owned();
            }
        }
        out
    }

    /// A hash of the private rules (patterns, labels, flags), for cache invalidation; empty when there are none.
    pub fn fingerprint(&self) -> String {
        if self.no_private() {
            return String::new();
        }
        let mut h = blake3::Hasher::new();
        for r in &self.rules {
            if let Matcher::Pattern(re) = &r.matcher {
                h.update(re.as_str().as_bytes());
                h.update(&[0]);
                h.update(r.label.as_bytes());
                h.update(&[0]);
            }
        }
        h.finalize().to_hex().to_string()
    }
}

/// `TICK005` for one file: a finding per private rule matching `bytes`; never echoes the term.
pub fn tick005(path: &str, bytes: &[u8], rules: &RuleSet) -> Vec<Finding> {
    rules
        .hits(bytes)
        .into_iter()
        .filter(|h| !h.builtin)
        .map(|h| {
            Finding::new(
                id_of(&Tick005),
                Severity::Error,
                None,
                format!(
                    "{path}: matches the local private-term rule `{}` (pattern hash {}); the term is not shown. \
                     Run `frob ticket doctor --fix` to replace it in a new commit (history is never rewritten), or reword the file",
                    h.label, h.hash
                ),
                path,
            )
        })
        .collect()
}

/// `TICK005` findings for every regular file directly below `<root>/<rel_dir>` (changelog fragments); none without private rules.
pub fn fragment_findings(root: &Path, rel_dir: &str, rules: &RuleSet) -> Vec<Finding> {
    if rules.no_private() {
        return Vec::new();
    }
    let Ok(rd) = std::fs::read_dir(root.join(rel_dir)) else {
        return Vec::new();
    };
    let mut names: Vec<String> = rd
        .filter_map(Result::ok)
        .filter(|e| e.file_type().is_ok_and(|t| t.is_file()))
        .map(|e| e.file_name().to_string_lossy().into_owned())
        .collect();
    names.sort();
    names
        .iter()
        .flat_map(|n| {
            let rel = format!("{rel_dir}/{n}");
            let bytes = std::fs::read(root.join(&rel)).unwrap_or_default();
            tick005(&rel, &bytes, rules)
        })
        .collect()
}

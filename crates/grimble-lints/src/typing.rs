//! `TYPING001`: strict null or type checking disabled in project configuration.
//!
//! The check is textual over one config file (`tsconfig.json`, a `.csproj`, `pyproject.toml`);
//! it only reports sites naming the exact key to set. Mapping a site to a severity (Advisory)
//! belongs to the rule that consumes it.

// frob:ticket 01M4D95N49XQ50SFQNHS82E1JG

use tracing::debug;

/// The project config file kinds `TYPING001` understands.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ConfigKind {
    /// A `tsconfig*.json` file.
    TsConfig,
    /// A `.csproj` project file.
    CsProj,
    /// A `pyproject.toml` file (mypy and pyright tables).
    PyProject,
}

impl ConfigKind {
    /// Classify a file name, or `None` when it is not a recognised config file.
    pub fn of_file_name(name: &str) -> Option<Self> {
        if name.starts_with("tsconfig")
            && name
                .rsplit('.')
                .next()
                .is_some_and(|e| e.eq_ignore_ascii_case("json"))
        {
            Some(Self::TsConfig)
        } else if name
            .rsplit('.')
            .next()
            .is_some_and(|e| e.eq_ignore_ascii_case("csproj"))
        {
            Some(Self::CsProj)
        } else if name == "pyproject.toml" {
            Some(Self::PyProject)
        } else {
            None
        }
    }
}

/// One config site with strictness disabled or unset.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Site {
    /// 1-based line of the offending key (1 when the key is absent).
    pub line: usize,
    /// The exact key and value to set, e.g. `"strict": true`.
    pub fix: &'static str,
    /// Human-readable explanation.
    pub message: &'static str,
}

/// Find strictness-disabled sites in one config file.
pub fn scan(kind: ConfigKind, text: &str) -> Vec<Site> {
    let sites = match kind {
        ConfigKind::TsConfig => scan_tsconfig(text),
        ConfigKind::CsProj => scan_csproj(text),
        ConfigKind::PyProject => scan_pyproject(text),
    };
    debug!(?kind, sites = sites.len(), "typing001 scan");
    sites
}

const TSCONFIG_FIX: &str = "\"strict\": true";
const TSCONFIG_MSG: &str =
    "tsconfig does not enable strict type checking; set compilerOptions.strict to true";
const CSPROJ_MSG: &str = "csproj does not enable nullable reference types; set <Nullable>enable</Nullable> in a PropertyGroup";
const CSPROJ_FIX: &str = "<Nullable>enable</Nullable>";

fn line_of(text: &str, offset: usize) -> usize {
    text[..offset].bytes().filter(|b| *b == b'\n').count() + 1
}

/// Blank out `//` and `/* */` comments (keeping newlines) so key search ignores them.
fn strip_json_comments(text: &str) -> String {
    let b = text.as_bytes();
    let mut out = String::with_capacity(text.len());
    let (mut i, mut in_str) = (0, false);
    while i < b.len() {
        let c = b[i];
        if in_str {
            out.push(c as char);
            if c == b'\\' && i + 1 < b.len() {
                out.push(b[i + 1] as char);
                i += 1;
            } else if c == b'"' {
                in_str = false;
            }
        } else if c == b'"' {
            in_str = true;
            out.push('"');
        } else if c == b'/' && b.get(i + 1) == Some(&b'/') {
            while i < b.len() && b[i] != b'\n' {
                out.push(' ');
                i += 1;
            }
            continue;
        } else if c == b'/' && b.get(i + 1) == Some(&b'*') {
            while i < b.len() && !(b[i] == b'*' && b.get(i + 1) == Some(&b'/')) {
                out.push(if b[i] == b'\n' { '\n' } else { ' ' });
                i += 1;
            }
            out.push_str("  ");
            i += 2;
            continue;
        } else {
            out.push(c as char);
        }
        i += 1;
    }
    out
}

/// Offset of `"key"` followed by `:` and the trimmed text after the colon.
fn json_value<'a>(text: &'a str, key: &str) -> Option<(usize, &'a str)> {
    let needle = format!("\"{key}\"");
    let at = text.find(&needle)?;
    let rest = text[at + needle.len()..].trim_start().strip_prefix(':')?;
    Some((at, rest.trim_start()))
}

fn scan_tsconfig(text: &str) -> Vec<Site> {
    let clean = strip_json_comments(text);
    match json_value(&clean, "strict") {
        Some((at, v)) if v.starts_with("false") => {
            vec![Site {
                line: line_of(&clean, at),
                fix: TSCONFIG_FIX,
                message: TSCONFIG_MSG,
            }]
        }
        Some(_) => Vec::new(),
        // An extended config may supply strict; only flag a self-contained one.
        None if json_value(&clean, "extends").is_some() => Vec::new(),
        None if json_value(&clean, "compilerOptions").is_none() => Vec::new(),
        None => vec![Site {
            line: 1,
            fix: TSCONFIG_FIX,
            message: TSCONFIG_MSG,
        }],
    }
}

fn scan_csproj(text: &str) -> Vec<Site> {
    match text.find("<Nullable>") {
        Some(at) => {
            let val = text[at + 10..].split('<').next().unwrap_or("").trim();
            if val.eq_ignore_ascii_case("enable") {
                Vec::new()
            } else {
                vec![Site {
                    line: line_of(text, at),
                    fix: CSPROJ_FIX,
                    message: CSPROJ_MSG,
                }]
            }
        }
        None if text.contains("<Project") => vec![Site {
            line: 1,
            fix: CSPROJ_FIX,
            message: CSPROJ_MSG,
        }],
        None => Vec::new(),
    }
}

fn scan_pyproject(text: &str) -> Vec<Site> {
    let mut sites = Vec::new();
    let mut table = String::new();
    for (idx, raw) in text.lines().enumerate() {
        let line = raw.trim();
        if line.starts_with('[') {
            table = line.trim_matches(|c| c == '[' || c == ']').to_string();
            continue;
        }
        let Some((k, v)) = line.split_once('=') else {
            continue;
        };
        let (k, v) = (k.trim(), v.trim().trim_matches('"').trim_matches('\''));
        if table == "tool.mypy" && k == "strict" && v.starts_with("false") {
            sites.push(Site {
                line: idx + 1,
                fix: "strict = true",
                message: "mypy strict mode is off; set strict = true under [tool.mypy]",
            });
        } else if table == "tool.pyright" && k == "typeCheckingMode" && matches!(v, "off" | "basic")
        {
            sites.push(Site {
                line: idx + 1,
                fix: "typeCheckingMode = \"strict\"",
                message: "pyright is not strict; set typeCheckingMode = \"strict\" under [tool.pyright]",
            });
        }
    }
    sites
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn tsconfig_strict_false_or_unset_is_a_site_and_strict_true_is_clean() {
        let off = scan(
            ConfigKind::TsConfig,
            "{\n  \"compilerOptions\": {\n    \"strict\": false\n  }\n}",
        );
        assert_eq!(off.len(), 1);
        assert_eq!(off[0].line, 3);
        assert_eq!(off[0].fix, "\"strict\": true");
        assert_eq!(
            scan(ConfigKind::TsConfig, "{\"compilerOptions\":{}}").len(),
            1
        );
        assert!(
            scan(
                ConfigKind::TsConfig,
                "{\"compilerOptions\":{\"strict\": true}}"
            )
            .is_empty()
        );
        assert!(
            scan(
                ConfigKind::TsConfig,
                "{\"extends\":\"./base\",\"compilerOptions\":{}}"
            )
            .is_empty()
        );
        assert!(
            scan(
                ConfigKind::TsConfig,
                "{\"compilerOptions\":{ // \"strict\": false\n\"strict\": true}}"
            )
            .is_empty()
        );
    }

    #[test]
    fn csproj_needs_nullable_enable() {
        assert_eq!(scan(ConfigKind::CsProj, "<Project>\n</Project>").len(), 1);
        assert_eq!(
            scan(
                ConfigKind::CsProj,
                "<Project><PropertyGroup><Nullable>disable</Nullable></PropertyGroup></Project>"
            )
            .len(),
            1
        );
        assert!(
            scan(
                ConfigKind::CsProj,
                "<Project><PropertyGroup><Nullable>enable</Nullable></PropertyGroup></Project>"
            )
            .is_empty()
        );
    }

    #[test]
    fn pyproject_flags_lax_mypy_and_pyright_only() {
        let t = "[tool.mypy]\nstrict = false\n[tool.pyright]\ntypeCheckingMode = \"basic\"\n";
        assert_eq!(scan(ConfigKind::PyProject, t).len(), 2);
        let ok = "[tool.mypy]\nstrict = true\n[tool.pyright]\ntypeCheckingMode = \"strict\"\n";
        assert!(scan(ConfigKind::PyProject, ok).is_empty());
    }

    #[test]
    fn file_names_classify() {
        assert_eq!(
            ConfigKind::of_file_name("tsconfig.build.json"),
            Some(ConfigKind::TsConfig)
        );
        assert_eq!(
            ConfigKind::of_file_name("a.csproj"),
            Some(ConfigKind::CsProj)
        );
        assert_eq!(
            ConfigKind::of_file_name("pyproject.toml"),
            Some(ConfigKind::PyProject)
        );
        assert_eq!(ConfigKind::of_file_name("x.json"), None);
    }
}

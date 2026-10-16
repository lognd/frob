//! The authored token files (`design/tokens/*.toml`, the dialect of `crunk-tokens`) as the TOKEN
//! rules read them: each file compiled on its own, with its text kept so findings can anchor.
//!
//! Every file is self-contained: aliases resolve inside the file that writes them, so a rule sees
//! one [`TokenSet`] per file and a broken alias is that file's error.

// frob:ticket 01M4CXR0EQH7WHQSNXCGKXE3V8

use std::collections::BTreeSet;

use crunk_ingest::ProjectStyles;
use crunk_spec::DesignSpec;
use crunk_tokens::TokenSet;
use crunk_tokens::dialect::{self, DialectError};

use crate::sheets::{is_tokens_sheet, site_path};

/// The project directory holding the authored token files, relative to the root.
pub const TOKENS_DIR: &str = "design/tokens";

/// One authored token file and what compiling it gave.
#[derive(Debug, Clone)]
pub struct TokenFile {
    /// The file, relative to the project root with forward slashes.
    pub path: String,
    /// The file's text, for anchoring findings.
    pub text: String,
    /// The compiled tokens, or why the file does not compile.
    pub set: Result<TokenSet, DialectError>,
}

/// Every authored token file of a project, sorted by path.
#[derive(Debug, Clone, Default)]
pub struct TokenFacts {
    /// The files, in path order.
    pub files: Vec<TokenFile>,
}

impl TokenFacts {
    /// Read and compile `<root>/design/tokens/*.toml`; a missing directory gives no files and an
    /// unreadable file is skipped with a warning.
    pub fn load(spec: &DesignSpec) -> Self {
        let dir = spec.root.join(TOKENS_DIR);
        let mut paths: Vec<_> = match std::fs::read_dir(&dir) {
            Ok(entries) => entries
                .filter_map(Result::ok)
                .map(|e| e.path())
                .filter(|p| p.extension().is_some_and(|x| x == "toml"))
                .collect(),
            Err(_) => Vec::new(),
        };
        paths.sort();
        let files: Vec<TokenFile> = paths
            .into_iter()
            .filter_map(|path| {
                let text = std::fs::read_to_string(&path)
                    .inspect_err(|err| {
                        tracing::warn!(path = %path.display(), %err, "token file unreadable; skipped");
                    })
                    .ok()?;
                let rel = site_path(spec, &path);
                let set = dialect::parse(&text, &rel);
                tracing::debug!(path = %rel, ok = set.is_ok(), "token file compiled");
                Some(TokenFile {
                    path: rel,
                    text,
                    set,
                })
            })
            .collect();
        Self { files }
    }

    /// The files that compiled, with their token sets.
    pub fn ok_sets(&self) -> impl Iterator<Item = (&TokenFile, &TokenSet)> {
        self.files
            .iter()
            .filter_map(|f| f.set.as_ref().ok().map(|set| (f, set)))
    }

    /// A stable digest of the files' paths and texts, for the repo digest.
    pub fn fingerprint(&self) -> String {
        let mut hasher = blake3::Hasher::new();
        for file in &self.files {
            hasher.update(file.path.as_bytes());
            hasher.update(b"\0");
            hasher.update(file.text.as_bytes());
            hasher.update(b"\0");
        }
        hasher.finalize().to_hex().to_string()
    }
}

/// The custom properties the examined (non-generated) stylesheets read through `var()`.
pub fn used_vars(styles: &ProjectStyles) -> BTreeSet<String> {
    styles
        .sheets
        .iter()
        .filter(|s| !is_tokens_sheet(s))
        .flat_map(|s| s.declarations.iter())
        .flat_map(|d| d.var_refs.iter().map(|v| v.name.clone()))
        .collect()
}

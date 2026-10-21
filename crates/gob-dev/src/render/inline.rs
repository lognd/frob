//! `crates/<crate>/resources/inline/{ok,err}/NAME.<ext>`: parser test inputs extracted from source comments.
//!
//! A parser carries its own test inputs next to the code that handles them (rust-analyzer and
//! `ruff_python_parser` style, build-test-ci.md section 6). A comment block that starts with
//! `// test_ok NAME` (input the parser must accept) or `// test_err NAME` (input it must reject) is
//! followed by the `//` lines that make up the input. `cargo dev gen inline` writes each block to
//! `resources/inline/ok/NAME.<ext>` or `resources/inline/err/NAME.<ext>`; GEN001 keeps the files
//! current, and each parser crate snapshots the tree and errors of every file (`tests/inline.rs`).
//!
//! One escape exists, for the directive parser whose inputs are themselves directives: a
//! namespace followed by a backslash and a colon (`frob`, backslash, colon) extracts as the
//! namespace and a plain colon, so the comment in the source is not a live directive.

// frob:ticket 01M47QTW8CA2FD3BQTH2GG2KXR
use std::collections::BTreeSet;
use std::path::{Path, PathBuf};

use crate::files::GenFile;

/// One parser whose inline tests are extracted.
#[derive(Debug, Clone, Copy)]
pub struct InlineParser {
    /// Crate directory under `crates/`.
    pub krate: &'static str,
    /// Directory under the crate whose `.rs` files are scanned.
    pub source: &'static str,
    /// Extension of the extracted input files.
    pub ext: &'static str,
}

/// The parsers that carry inline tests: GRL, `.grmb`, directives and the `crunk.toml` spec.
pub const PARSERS: &[InlineParser] = &[
    InlineParser {
        krate: "gob-plan",
        source: "src/grl",
        ext: "grl",
    },
    InlineParser {
        krate: "grimble-model",
        source: "src",
        ext: "grmb",
    },
    InlineParser {
        krate: "gob-directives",
        source: "src",
        ext: "txt",
    },
    InlineParser {
        krate: "crunk-spec",
        source: "src",
        ext: "toml",
    },
];

/// Marker word of a block the parser must accept.
const OK_WORD: &str = "test_ok";
/// Marker word of a block the parser must reject.
const ERR_WORD: &str = "test_err";
/// Namespaces whose `NS\:` escape extracts to `NS:`.
const ESCAPED_NAMESPACES: &[&str] = &["frob", "grimble"];

/// Whether a block must be accepted or rejected.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Outcome {
    /// `test_ok`: the parser accepts the input.
    Ok,
    /// `test_err`: the parser reports at least one error.
    Err,
}

impl Outcome {
    /// Directory name under `resources/inline/`.
    pub const fn dir(self) -> &'static str {
        match self {
            Self::Ok => "ok",
            Self::Err => "err",
        }
    }
}

/// One extracted block.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Block {
    /// Accept or reject.
    pub outcome: Outcome,
    /// The case name (`[a-z0-9_]+`).
    pub name: String,
    /// The input text, one `\n` after every line.
    pub body: String,
}

/// Why inline tests could not be extracted.
#[derive(Debug, thiserror::Error)]
pub enum InlineError {
    /// A source file or directory could not be read.
    #[error("read {}: {source}", path.display())]
    Io {
        /// The path.
        path: PathBuf,
        /// Underlying error.
        source: std::io::Error,
    },
    /// A marker line has no name or an invalid one.
    #[error("{path}:{line}: `{word}` needs a name of lower-case letters, digits and `_`")]
    BadName {
        /// Source path relative to the root.
        path: String,
        /// 1-based line of the marker.
        line: usize,
        /// The marker word.
        word: &'static str,
    },
    /// A block has no input lines.
    #[error("{path}:{line}: block `{name}` is empty")]
    Empty {
        /// Source path relative to the root.
        path: String,
        /// 1-based line of the marker.
        line: usize,
        /// The case name.
        name: String,
    },
    /// Two blocks of one parser share an outcome and name.
    #[error("{path}:{line}: block `{name}` is already defined")]
    Duplicate {
        /// Source path relative to the root.
        path: String,
        /// 1-based line of the marker.
        line: usize,
        /// The case name.
        name: String,
    },
}

/// The comment payload of `line` when it is a plain `//` comment (not `///` or `//!`), else `None`.
fn plain_comment(line: &str) -> Option<&str> {
    let rest = line.trim_start().strip_prefix("//")?;
    if rest.starts_with('/') || rest.starts_with('!') {
        return None;
    }
    Some(rest.strip_prefix(' ').unwrap_or(rest))
}

/// The marker word and name of a comment payload, if it is a `test_ok NAME` or `test_err NAME` line.
fn marker(payload: &str) -> Option<(Outcome, &'static str, &str)> {
    let (word, outcome) = if payload.starts_with(OK_WORD) {
        (OK_WORD, Outcome::Ok)
    } else if payload.starts_with(ERR_WORD) {
        (ERR_WORD, Outcome::Err)
    } else {
        return None;
    };
    let tail = &payload[word.len()..];
    if tail.is_empty() {
        return Some((outcome, word, ""));
    }
    let rest = tail.strip_prefix(' ')?;
    Some((outcome, word, rest.trim()))
}

/// Undo the namespace escape in one extracted line.
fn unescape(line: &str) -> String {
    let mut out = line.to_owned();
    for ns in ESCAPED_NAMESPACES {
        out = out.replace(&format!("{ns}\\:"), &format!("{ns}:"));
    }
    out
}

/// Whether `name` is a valid case name.
fn valid_name(name: &str) -> bool {
    !name.is_empty()
        && name
            .bytes()
            .all(|b| b.is_ascii_lowercase() || b.is_ascii_digit() || b == b'_')
}

/// Every block in `text`; `path` names the source in errors.
///
/// # Errors
/// [`InlineError`] for a bad name, an empty block, or a duplicate `(outcome, name)`.
pub fn extract(path: &str, text: &str) -> Result<Vec<Block>, InlineError> {
    let lines: Vec<&str> = text.lines().collect();
    let mut blocks: Vec<Block> = Vec::new();
    let mut i = 0;
    while i < lines.len() {
        let Some((outcome, word, name)) = plain_comment(lines[i]).and_then(marker) else {
            i += 1;
            continue;
        };
        let line = i + 1;
        if !valid_name(name) {
            return Err(InlineError::BadName {
                path: path.to_owned(),
                line,
                word,
            });
        }
        let mut body = String::new();
        let mut count = 0;
        i += 1;
        while let Some(payload) = lines.get(i).copied().and_then(plain_comment) {
            if marker(payload).is_some() {
                break;
            }
            body.push_str(&unescape(payload));
            body.push('\n');
            count += 1;
            i += 1;
        }
        if count == 0 {
            return Err(InlineError::Empty {
                path: path.to_owned(),
                line,
                name: name.to_owned(),
            });
        }
        if blocks
            .iter()
            .any(|b| b.outcome == outcome && b.name == name)
        {
            return Err(InlineError::Duplicate {
                path: path.to_owned(),
                line,
                name: name.to_owned(),
            });
        }
        tracing::debug!(path, line, name, ?outcome, "inline test block");
        blocks.push(Block {
            outcome,
            name: name.to_owned(),
            body,
        });
    }
    Ok(blocks)
}

/// Every `.rs` file under `dir`, sorted; none when the directory is absent.
fn rust_files(dir: &Path) -> Result<Vec<PathBuf>, InlineError> {
    let mut out = Vec::new();
    let mut stack = vec![dir.to_path_buf()];
    while let Some(d) = stack.pop() {
        let entries = match std::fs::read_dir(&d) {
            Ok(entries) => entries,
            Err(e) if e.kind() == std::io::ErrorKind::NotFound => continue,
            Err(source) => return Err(InlineError::Io { path: d, source }),
        };
        for entry in entries {
            let path = entry
                .map_err(|source| InlineError::Io {
                    path: d.clone(),
                    source,
                })?
                .path();
            if path.is_dir() {
                stack.push(path);
            } else if path.extension().is_some_and(|e| e == "rs") {
                out.push(path);
            }
        }
    }
    out.sort();
    Ok(out)
}

/// The extracted input files of every parser in [`PARSERS`], read from the sources under `root`.
///
/// # Errors
/// [`InlineError`] when a source cannot be read or a block is malformed or duplicated.
pub fn generate(root: &Path) -> Result<Vec<GenFile>, InlineError> {
    let mut files = Vec::new();
    for parser in PARSERS {
        let crate_dir = format!("crates/{}", parser.krate);
        let mut seen: BTreeSet<(&'static str, String)> = BTreeSet::new();
        for path in rust_files(&root.join(&crate_dir).join(parser.source))? {
            let rel = path
                .strip_prefix(root)
                .map_or_else(|_| path.clone(), Path::to_path_buf)
                .to_string_lossy()
                .replace('\\', "/");
            let text = std::fs::read_to_string(&path).map_err(|source| InlineError::Io {
                path: path.clone(),
                source,
            })?;
            for block in extract(&rel, &text)? {
                if !seen.insert((block.outcome.dir(), block.name.clone())) {
                    return Err(InlineError::Duplicate {
                        path: rel,
                        line: 0,
                        name: block.name,
                    });
                }
                files.push(GenFile {
                    path: format!(
                        "{crate_dir}/{}/{}/{}.{}",
                        INLINE_DIR,
                        block.outcome.dir(),
                        block.name,
                        parser.ext
                    ),
                    content: block.body,
                });
            }
        }
    }
    Ok(files)
}

/// Where extracted inputs live, relative to a crate directory.
pub const INLINE_DIR: &str = "resources/inline";

/// Whether `path` (repo-relative, `/`-separated) is an extracted inline input.
pub fn is_inline_path(path: &str) -> bool {
    path.contains(&format!("/{INLINE_DIR}/"))
}

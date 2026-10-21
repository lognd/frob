//! Bounded single reads and glob expansion inside one pack directory.

use std::collections::BTreeSet;
use std::io::Read as _;
use std::path::Path;

use globset::Glob;

use crate::error::PackError;

/// Largest single pack file the loader will hold in memory.
pub(crate) const MAX_FILE_BYTES: usize = 4 * 1024 * 1024;
/// Deepest directory nesting the glob walk descends.
const MAX_DEPTH: usize = 16;

/// Reads `root/rel` once as UTF-8 text, never past [`MAX_FILE_BYTES`].
pub(crate) fn read_text(root: &Path, rel: &str, key: &str) -> Result<(String, String), PackError> {
    let path = root.join(rel);
    let label = gob_path::Shown::with_home(&path, None).to_string();
    let io = |e: std::io::Error| PackError::malformed(&label, key, format!("cannot read: {e}"));
    let mut buf = Vec::new();
    std::fs::File::open(&path)
        .map_err(io)?
        .take(MAX_FILE_BYTES as u64 + 1)
        .read_to_end(&mut buf)
        .map_err(io)?;
    if buf.len() > MAX_FILE_BYTES {
        return Err(PackError::malformed(
            &label,
            key,
            format!("is over the {MAX_FILE_BYTES} byte limit"),
        ));
    }
    let text =
        String::from_utf8(buf).map_err(|_| PackError::malformed(&label, key, "must be UTF-8"))?;
    tracing::debug!(file = %label, bytes = text.len(), "pack file read");
    Ok((label, text))
}

fn walk(dir: &Path, rel: &str, depth: usize, out: &mut Vec<String>) -> std::io::Result<()> {
    if depth > MAX_DEPTH {
        return Ok(());
    }
    for entry in std::fs::read_dir(dir)? {
        let entry = entry?;
        let name =
            gob_path::Shown::with_home(std::path::Path::new(&entry.file_name()), None).to_string();
        let child = if rel.is_empty() {
            name
        } else {
            format!("{rel}/{name}")
        };
        if entry.file_type()?.is_dir() {
            walk(&entry.path(), &child, depth + 1, out)?;
        } else {
            out.push(child);
        }
    }
    Ok(())
}

/// Expands `patterns` against the files under `root`; sorted, de-duplicated relative paths.
///
/// A pattern matching nothing is PACK005 (a declared rule file that is absent is never skipped).
pub(crate) fn expand(
    root: &Path,
    patterns: &[String],
    key: &str,
) -> Result<Vec<String>, PackError> {
    let label = gob_path::Shown::with_home(root, None).to_string();
    let mut files = Vec::new();
    walk(root, "", 0, &mut files)
        .map_err(|e| PackError::malformed(&label, key, format!("cannot list: {e}")))?;
    let mut found = BTreeSet::new();
    for p in patterns {
        let matcher = Glob::new(p)
            .map_err(|e| PackError::malformed(&label, key, format!("bad glob `{p}`: {e}")))?
            .compile_matcher();
        let before = found.len();
        found.extend(
            files
                .iter()
                .filter(|f| matcher.is_match(f.as_str()))
                .cloned(),
        );
        if found.len() == before {
            return Err(PackError::malformed(
                &label,
                key,
                format!("`{p}` matches no file"),
            ));
        }
    }
    Ok(found.into_iter().collect())
}

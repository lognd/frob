//! Shared reading of the ingested styles for the rules that judge declarations.

// frob:ticket 01M43ATB4X0B56W8T0G8MQFYVM

use std::path::Path;

use crunk_ingest::{Bucket, ProjectStyles, Stylesheet};
use crunk_spec::DesignSpec;

/// `path` relative to the project root with forward slashes, the form a located finding carries.
///
/// A path outside the root (it should not occur: the walk is rooted there) is returned as given.
pub fn site_path(spec: &DesignSpec, path: &Path) -> String {
    let rel = path.strip_prefix(&spec.root).unwrap_or(path);
    rel.to_string_lossy().replace('\\', "/")
}

/// True for the generated tokens sheet, where the palette literals themselves live.
pub fn is_tokens_sheet(sheet: &Stylesheet) -> bool {
    sheet.bucket == Some(Bucket::Tokens)
}

/// How many sheets a declaration rule examines: every ingested sheet except the generated tokens
/// sheet. Zero means the rule judged nothing, which the pipeline reports as Unresolved.
pub fn examined_sheets(styles: &ProjectStyles) -> usize {
    styles.sheets.iter().filter(|s| !is_tokens_sheet(s)).count()
}

/// The byte offset where the 1-based `line` starts in `source`, so a line-located fact (a class
/// selector, a custom property) can anchor a finding; a line past the end maps to the end.
// frob:ticket 01M43ATBPPR5QCY0CSPPTNEDQ0
pub fn line_offset(source: &str, line: u32) -> usize {
    let skip = line.saturating_sub(1) as usize;
    if skip == 0 {
        return 0;
    }
    source
        .match_indices('\n')
        .nth(skip - 1)
        .map_or(source.len(), |(at, _)| at + 1)
}

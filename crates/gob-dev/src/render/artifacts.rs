//! Files registered by products through `gob_config::ArtifactEntry`: no product is named here.

use gob_config::{ArtifactBody, ArtifactFamily, all_artifacts};

use super::{json_file, md_header};
use crate::files::GenFile;

/// Render every registered artifact of `family`, in registry order (the caller sorts by path).
pub fn generate(family: ArtifactFamily) -> Vec<GenFile> {
    let kind = match family {
        ArtifactFamily::Config => "config",
        ArtifactFamily::Schemas => "schemas",
    };
    all_artifacts()
        .filter(|entry| entry.family == family)
        .map(|entry| {
            tracing::debug!(path = entry.path, kind, "rendering registered artifact");
            let content = match (entry.render)() {
                ArtifactBody::Markdown(body) => md_header(kind) + &body,
                ArtifactBody::Json(value) => json_file(kind, value),
            };
            GenFile {
                path: entry.path.to_owned(),
                content,
            }
        })
        .collect()
}

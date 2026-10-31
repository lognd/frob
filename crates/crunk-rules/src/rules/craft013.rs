//! CRAFT013: a voice and tone file exists when scenes use copy keys (research CONTENT-VOICE).
//! SLOP060 judges buzzword density against a tone file's allow and deny list; with no
//! `design/content/voice.toml` there is nothing to judge against, and deleting the file passes
//! SLOP060 vacuously. When any scene document references a copy key (`data-copy` or
//! `data-copy-<attribute>` with a non-empty key) and the project has no voice file, this fires once,
//! at the first referencing scene, and names SLOP060. A voice file holding only blanks and `#`
//! comments is a placeholder and fires once at that file. A voice file that has content is present,
//! well formed or not. Scenes with no copy key never fire it.

// frob:ticket 01M5HM3W7MK7255AGEN27SXEXP

use gob_rules::{Out, RepoRule, rule};

use crate::content_files::{CONTENT_DIR, VOICE_FILE, VoiceFile, copy_refs};
use crate::host::{CrunkHost, missing_scene_doc_inputs};

/// Scenes reference copy keys while `design/content/voice.toml` is missing or blank.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "CRAFT013",
    slug = "voice-file-present",
    severity = Error,
    polarity = Pplus,
    must_measure = false,
    scope = Repo,
    fix = Manual,
    applies = universal(needs = [Style], min_fidelity = F1),
    host = CrunkHost,
    version = 1,
    since = "0.532.0",
)]
pub struct Craft013;

impl<P: ?Sized + CrunkHost> RepoRule<P> for Craft013 {
    fn check(&self, host: &P, out: &mut Out<'_, Self>) {
        let (Some(scenes), Some(content)) = (host.scene_docs(), host.content()) else {
            return;
        };
        if content.voice == VoiceFile::Present {
            return;
        }
        let first = scenes.files.iter().find_map(|file| {
            copy_refs(file)
                .into_iter()
                .find(|r| !r.key.is_empty())
                .map(|r| (file, r))
        });
        let Some((file, reference)) = first else {
            return;
        };
        let voice = format!("{CONTENT_DIR}/{VOICE_FILE}");
        if content.voice == VoiceFile::Blank {
            tracing::debug!(path = %voice, "CRAFT013: voice file blank");
            out.fire_in(
                &voice,
                0,
                format!(
                    "{voice} has no content: scenes reference copy keys (first '{}' in {}), so \
                     SLOP060 has no allow or deny list to judge buzzwords against; write the \
                     voice, tone and banned terms",
                    reference.key, file.path
                ),
            );
            return;
        }
        tracing::debug!(path = %file.path, key = %reference.key, "CRAFT013: voice file missing");
        out.fire_in(
            &file.path,
            reference.offset,
            format!(
                "scene copy key '{}' is used but {voice} does not exist, so SLOP060 has no \
                 allow or deny list to judge buzzwords against; add {voice} with the voice, \
                 tone and banned terms",
                reference.key
            ),
        );
    }

    fn inapplicable(&self, host: &P) -> Option<String> {
        missing_scene_doc_inputs(host).or_else(|| {
            host.content()
                .is_none()
                .then(|| "content files were not collected".to_owned())
        })
    }
}

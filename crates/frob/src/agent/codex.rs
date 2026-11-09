//! The Codex CLI emitter: files under `~/.codex`; Codex has no hook registry, so nothing is registered.

// frob:ticket 01M5BN07TWS6HME68083TP038J

use std::path::PathBuf;

use super::{Emitter, Item, Kind};

/// The Codex CLI agent.
pub struct Codex;

impl Emitter for Codex {
    fn id(&self) -> &'static str {
        "codex"
    }

    fn default_home(&self) -> Option<PathBuf> {
        std::env::var_os("CODEX_HOME")
            .map(PathBuf::from)
            .or_else(|| std::env::var_os("HOME").map(|h| PathBuf::from(h).join(".codex")))
    }

    fn target(&self, item: &Item) -> Option<PathBuf> {
        match item.kind {
            Kind::Agent => Some(PathBuf::from(format!("prompts/{}.md", item.name))),
            Kind::Skill => Some(PathBuf::from(format!("skills/{}/SKILL.md", item.name))),
            Kind::Instruction => Some(PathBuf::from(format!("{}.md", item.name))),
            Kind::Hook | Kind::Support => {
                tracing::debug!(name = %item.name, "codex has no place for hooks or support files");
                None
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn item(kind: Kind) -> Item {
        Item {
            kind,
            name: "x".to_owned(),
            src: "src/x.md".to_owned(),
        }
    }

    // frob:tests crates/frob/src/agent/codex.rs::Codex
    #[test]
    fn hooks_have_no_codex_target() {
        assert_eq!(Codex.target(&item(Kind::Hook)), None);
    }

    // frob:tests crates/frob/src/agent/codex.rs::Codex
    #[test]
    fn agents_land_as_prompts() {
        assert_eq!(
            Codex.target(&item(Kind::Agent)),
            Some(PathBuf::from("prompts/x.md"))
        );
    }
}

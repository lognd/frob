//! The `[mirror]` table of `frob.toml`: tracker identity for `frob mirror recreate`.

// frob:ticket 01M5B07S4JNVW9QF4XA48DKBVB

use crate::ConfigTable;

/// Marker key id used when `[mirror] kid` is not set.
pub const DEFAULT_MIRROR_KID: &str = "k1";

/// Mirror identity settings, so recreate needs no environment variables for them.
#[derive(Debug, Clone, ConfigTable)]
#[config(table = "mirror")]
pub struct MirrorTable {
    /// GitHub repository as `OWNER/NAME`; empty means derive it from the `origin` remote.
    #[config(default = String::new())]
    pub repo: String,
    /// Marker signing key id; the key itself stays in `FROB_MIRROR_KEY`.
    #[config(default = DEFAULT_MIRROR_KID.to_owned())]
    pub kid: String,
    /// Logins of the bot accounts whose markers are trusted; empty means the token's own login.
    #[config(default = Vec::<String>::new())]
    pub bot_ids: Vec<String>,
}

#[cfg(test)]
mod tests {
    use super::*;

    // frob:tests crates/gob-config/src/mirror.rs::MirrorTable
    #[test]
    fn mirror_table_defaults_and_file_values() {
        let dir = tempfile::tempdir().unwrap();
        let d = crate::load::<MirrorTable>(dir.path(), "frob")
            .unwrap()
            .value;
        assert_eq!((d.repo.as_str(), d.kid.as_str()), ("", "k1"));
        assert!(d.bot_ids.is_empty());
        std::fs::write(
            dir.path().join("frob.toml"),
            "[mirror]\nrepo = \"o/n\"\nkid = \"k2\"\nbot_ids = [\"bot\"]\n",
        )
        .unwrap();
        let v = crate::load::<MirrorTable>(dir.path(), "frob")
            .unwrap()
            .value;
        assert_eq!((v.repo.as_str(), v.kid.as_str()), ("o/n", "k2"));
        assert_eq!(v.bot_ids, ["bot"]);
    }
}

//! Tracker mirror (docs/design/mirror.md): marker keyring and, later, identity and sync.

// frob:ticket 01M4052RG3QVXW6CHTG8BNS7CD
// frob:ticket 01M4052T420AX728KKZ2RDYSTX
pub mod adapter;
pub mod blind;
pub mod budget;
pub mod config;
pub mod cursor;
pub mod dups;
pub mod fields;
pub mod github;
pub mod journal;
pub mod keyring;
pub mod limits;
pub mod lock;
pub mod mapfile;
pub mod mapping;
pub mod marker;
pub mod outbox;
pub mod plan;
pub mod progress;
pub mod projection;
pub mod proposals;

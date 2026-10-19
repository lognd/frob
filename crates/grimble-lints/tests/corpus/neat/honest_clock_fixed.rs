// frob:honest
fn stamp(label: &str, started: u64) -> String {
    format!("{label}@{started}")
}

// frob:shell
fn now_shell() -> std::time::Instant {
    std::time::Instant::now()
}

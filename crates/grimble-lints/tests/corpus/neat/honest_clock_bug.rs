// frob:honest
fn stamp(label: &str) -> String {
    let started = std::time::Instant::now();
    format!("{label}@{started:?}")
}

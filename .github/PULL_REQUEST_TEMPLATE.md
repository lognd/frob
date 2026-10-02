## Ticket

<!-- e.g. T-1234 -->

## Summary

<!-- What does this change do, and why? -->

## Verification

- [ ] `cargo fmt --all --check`
- [ ] `cargo clippy --all-targets --all-features -- -D warnings`
- [ ] `cargo nextest run --profile ci`
- [ ] `RUSTDOCFLAGS="-D warnings" cargo doc --no-deps`

## Checklist

- [ ] Docs updated
- [ ] ASCII only (no emoji, no smart quotes)

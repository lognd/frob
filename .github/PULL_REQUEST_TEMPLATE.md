<!-- Thanks for the contribution. Please fill in every section below;
     delete a section only if it truly does not apply. -->

## Summary

<!-- What does this change do, and why? A few sentences is enough. -->

## Ticket

<!-- e.g. "Closes T-1234", or "No ticket -- small/obvious change" -->

## Checklist

- [ ] `uv run frob check` is green (or `--ticket T-####` scoped, with any
      waiver named below)
- [ ] `uv run frob test --base main` is green for the touched set
- [ ] New public symbols carry `# frob:ticket`, and their tests carry
      `# frob:tests`, where applicable
- [ ] Docs updated under `docs/`, with the `# frob:doc` anchor kept in
      sync where applicable
- [ ] `CHANGELOG.md` entry added under the "unreleased" section
- [ ] Commit messages follow the `<type>(<scope>): <imperative summary>`
      format described in CONTRIBUTING.md
- [ ] ASCII only (no emoji, no smart quotes, no em dashes)
- [ ] Ticket closed with bound evidence and a Done report (if this PR
      closes a ticket)
- [ ] AI assistance: none / <tool>, <how used> (drafted / reviewed / tests written)
- [ ] I understand and can explain every line of this change

## Waivers

<!-- List any `frob:waive` directives this change adds or relies on,
     and why. "None" if there are none. -->

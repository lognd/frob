# P0 think-aloud check of the D139 operator spellings

Status: current

Ticket ~7SJ2BYW (follow-up cut from ~T5VVDBY). Answers the P0 row of
grmb-spec 18 (think-aloud check, C32, D139): read the operators aloud on
the corpus (notes/research/grmb-corpus/) before the grammar freezes.

## Method and limits

This is a single-reader DESK think-aloud run by the implementing agent,
not the five-author human session the spec row describes. An agent
cannot supply human participants, so the table below is a protocol run
plus a mechanical corpus census. It confirms or revises the spelling on
the evidence available; the human session stays an open follow-up and
this note does not claim its exit criterion (five authors, per-token
accuracy).

Protocol: for each token, read three corpus lines aloud, say what the
token means in one phrase, then check the phrase against D139 and D152.

## Corpus census (domains/ and stress/, 31 .grmb files)

| Token | Lines | Files | Reading aloud | Matches D139/D152 |
|---|---|---|---|---|
| `->` | 32 | 19 | "follows / moves to" (`user.edits -> system.uploads`; `flow f : producer -> consumer`) | yes |
| `=>` | 75 | 21 | "maps this pattern to its consequence" (`offline => retry max 5;`, `ok => end ok;`) | yes |
| `-!>` | 5 | 3 | "then, collecting failures" (`a.step4 -!> end ok;`, `include l4 -!> end ok;`) | yes |
| `*` | few | few | "for every" (`impl x for *`) | yes |
| `-\|>` | 0 | 0 | retired early-draft spelling | absent, as required |
| `-?>` | 0 | 0 | must not exist | absent, as required |

## Findings

1. One spelling per meaning holds: no alias dialect appears in the
   corpus; the retired `-|>` and the forbidden `-?>` occur nowhere.
2. Each token reads aloud with a single phrase. `->` (follows) and `=>`
   (maps to) were not interchangeable in any sampled line, which is the
   D152 one-meaning-per-token property.
3. Watch item (not a defect): `->` and `-!>` share a stem, so a reader
   may need the "!" cue to tell infallible from collecting links. The
   mnemonic ("bang means failures are collected") is short; flag it as
   the first thing to probe with the human participants.

## Decision

D139 operator spellings are CONFIRMED unchanged: `->`, `=>`, `-!>`, `*`,
no `-?>`. No revision, so no grammar ticket is needed. The confusion
list from this run holds one watch item (finding 3), carried into the
human session.

## Left open

The five-author human think-aloud (spec 18 P0 exit: confusion list empty
or each item ticketed) is not done by this ticket.

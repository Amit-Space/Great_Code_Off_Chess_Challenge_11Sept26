# Version1 Code-Off: Chess Move Validator — Competitor Spec

You have **2 hours**. Build a program that, given a chessboard and one
fully-specified proposed move, decides whether the move is legal — and if
it is, reports what happened (capture, check). You may use any language,
any libraries, and any AI tooling (including the OpenAI key you've been
given) to help you write it. We will run your finished program against a
hidden batch of 50 test cases and score on **correctness first, speed second**.

## Rules in scope

Standard chess piece movement for all six piece types, captures, and check
detection (does this move leave your own king in check — illegal; does it
put the opponent's king in check — reported).

**Explicitly OUT of scope** — you do not need to implement these, and no
test case will require them:

- Castling
- En passant
- Pawn promotion (no test case has a pawn reaching the last rank)
- Stalemate / checkmate / draw detection ("is the game over" is not asked)

If you implement extra rules anyway, that's fine — it won't be tested, but
it also won't hurt you as long as it doesn't change your answers on the
in-scope cases.

## Board representation

An 8x8 array of rows. **Row 0 is rank 8** (black's back rank, top of a
printed board), **row 7 is rank 1** (white's back rank). Within a row,
**column 0 is file a**, **column 7 is file h**. Each cell is `null` for an
empty square, or a 2-character string: color (`"w"` or `"b"`) + piece
letter (`P`, `N`, `B`, `R`, `Q`, `K`). Example: `"wP"` = white pawn, `"bK"`
= black king.

The standard starting position looks like this:

```json
[
  ["bR","bN","bB","bQ","bK","bB","bN","bR"],
  ["bP","bP","bP","bP","bP","bP","bP","bP"],
  [null,null,null,null,null,null,null,null],
  [null,null,null,null,null,null,null,null],
  [null,null,null,null,null,null,null,null],
  [null,null,null,null,null,null,null,null],
  ["wP","wP","wP","wP","wP","wP","wP","wP"],
  ["wR","wN","wB","wQ","wK","wB","wN","wR"]
]
```

## Input format

Your program will receive a **JSON array** of test cases on **stdin**.
Each case looks like this:

```json
{
  "board": [ ...8x8 as above... ],
  "turn": "white",
  "move": { "from": "e2", "to": "e4" }
}
```

- `turn` is `"white"` or `"black"` — whose move it is.
- `move.from` / `move.to` are algebraic squares (`"a1"`–`"h8"`). The move
  is **always fully specified** — you're told exactly which piece and
  exactly which destination, so there's no ambiguity to resolve (no "which
  rook" guessing).

Your program must read the **entire array** from stdin in one go (don't
assume one case per line).

## Output format

Print a single **JSON array** to **stdout**, same length and same order as
the input array. Each element:

```json
{
  "legal": true,
  "reason_code": null,
  "reason": null,
  "capture": null,
  "opponent_in_check": false,
  "resulting_board": [ ...8x8, board after the move... ]
}
```

Field meanings:

| Field | When | Meaning |
|---|---|---|
| `legal` | always | `true`/`false`. **This is the field that decides your score.** |
| `reason_code` | only when `legal:false` | why the move is illegal — see the enum below. Not required for your score, but a `null` example run before the event helps you sanity-check your own logic. |
| `reason` | only when `legal:false` | a human-readable version of the reason (this is the flavor text a live text-based interface would show a player — "Rook can't move there: the path is blocked"). |
| `capture` | only when `legal:true` | `null` if no capture, otherwise `{"piece": "bN", "square": "c4"}` — the piece and square that got captured. |
| `opponent_in_check` | only when `legal:true` | `true` if this move puts the *opponent's* king in check. |
| `resulting_board` | only when `legal:true` | the board after the move, same 8x8 format. |

**Only `legal` is required to be correct for the primary score.** The
other fields are there because a real text-based chess bot needs them
(and because we may run a secondary, informational pass checking them) —
so get them right if you have time left, but don't burn your whole two
hours chasing an exact-match `reason` string.

### Illegal-move reason codes

| Code | Meaning |
|---|---|
| `NO_PIECE_AT_SOURCE` | Nothing on the `from` square. |
| `WRONG_TURN` | The piece on `from` belongs to the side NOT to move. |
| `DESTINATION_OCCUPIED_BY_OWN_PIECE` | Your own piece is already on `to`. |
| `INVALID_PIECE_MOVEMENT` | This piece can never move in that shape (e.g. a rook moving diagonally). |
| `PATH_BLOCKED` | A sliding piece (bishop/rook/queen) is blocked by something in between. |
| `PAWN_CANNOT_CAPTURE_FORWARD` | Pawn tried to move straight ahead onto an occupied square. |
| `PAWN_NO_PIECE_TO_CAPTURE` | Pawn tried to move diagonally onto an empty square. |
| `MOVE_EXPOSES_OWN_KING_TO_CHECK` | The move would leave (or put) your own king in check — covers pins, moving a king into an attacked square, and "you're in check and this move doesn't address it." |
| `INVALID_SQUARE` | `from` or `to` isn't a real square. |
| `NULL_MOVE` | `from` and `to` are the same square. |

## Worked examples

**Legal — pawn double-step from its start rank:**
input `{"board": <starting position>, "turn": "white", "move": {"from": "e2", "to": "e4"}}`
→ `legal: true`, no capture, `opponent_in_check: false`.

**Illegal — nothing on the source square:**
input `{"board": <starting position>, "turn": "white", "move": {"from": "e5", "to": "e6"}}`
→ `legal: false`, `reason_code: "NO_PIECE_AT_SOURCE"`.

**Illegal — a pin:** white king on e1, white bishop on e2, black rook on
e8, nothing else on the board. Moving the bishop off the e-file (e.g. to
d3) is illegal even though the bishop's own movement pattern is fine,
because it would expose the king to the rook's check →
`reason_code: "MOVE_EXPOSES_OWN_KING_TO_CHECK"`.

A file of 10 such worked examples, `test_cases_public.json`, is provided
alongside this spec so you can validate your program's exact output shape
before submitting. **These are NOT the graded cases** — they're just to
confirm you've got the I/O contract right.

## Submission contract (how we'll run your program)

Tell us the exact command to run your solution (e.g.
`python3 solve.py`, `node solve.js`, `./solve`). We will:

1. Pipe the full JSON array of hidden test cases to its **stdin**.
2. Read the full JSON array of your results from its **stdout** once your
   program exits.
3. Time the whole run, start to finish.

Your program must not require any interactive input, network access, or
manual steps. If it needs a compile step, build it before you submit —
we're timing execution, not compilation.

## Scoring

1. **Correctness** — number of the 50 hidden test cases where your
   `legal` value matches the correct answer. This is the primary ranking:
   teams are ordered by correct-count first.
2. **Speed** — total wall-clock time to process the whole batch, used
   ONLY as a tiebreaker between teams with the same correctness score. A
   faster but less correct solution does not outrank a slower, more
   correct one.

A program that crashes, times out, or doesn't print valid JSON scores 0
on every case it was supposed to answer — so leave time to test against
`test_cases_public.json` before the deadline.

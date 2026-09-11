# Chess Move Validator — Code-Off Solution

A from-scratch chess move validator built for the Version1 Code-Off. Given a
board, whose turn it is, and one fully-specified move, it decides whether the
move is **legal** and reports what happened (capture, check).

No chess libraries — only the Python standard library (`json`, `sys`).

## Run it (submission command)

```bash
python3 my_solution/solve.py
```

The program reads **one JSON array of cases from stdin** and writes **one JSON
array of results to stdout**, in the same order. No arguments, no network, no
install step, no compile step.

Examples:

```bash
# macOS / Linux
python3 my_solution/solve.py < my_solution/sample_input.json
```

```powershell
# Windows PowerShell (no "<" redirection)
Get-Content my_solution/sample_input.json -Raw | python my_solution/solve.py
```

## Input

A JSON array; each element is one case:

```json
{
  "board": [ "...8x8 rows..." ],
  "turn": "white",
  "move": { "from": "e2", "to": "e4" }
}
```

- Board: row 0 = rank 8 … row 7 = rank 1; column 0 = file a … column 7 = file h.
- Each square is `null` or a 2-char token: color (`w`/`b`) + piece (`P N B R Q K`),
  e.g. `"wP"` = white pawn, `"bK"` = black king.

## Output

A JSON array of the same length and order. Each result:

```json
{
  "legal": true,
  "reason_code": null,
  "reason": null,
  "capture": null,
  "opponent_in_check": false,
  "resulting_board": [ "...8x8..." ]
}
```

When `legal` is `false`, `reason_code`/`reason` explain why and the other fields
are `null`/`false`. When `legal` is `true`, `capture` is `null` or
`{"piece": "bN", "square": "c4"}`, `opponent_in_check` says whether the move
checks the opponent, and `resulting_board` is the board after the move.

## Approach

Validate the single given move directly (no full move generation):

1. The board must be a valid 8×8 grid of piece tokens.
2. Squares must be real (a1–h8) and it can't be a null move.
3. A piece of the side-to-move must sit on `from`, and `to` can't hold your own piece.
4. The move must match the piece's shape, with a clear path for sliding pieces
   and proper pawn-capture rules.
5. Simulate the move on a copy and confirm it doesn't leave **your own king in
   check** — one test that covers pins, moving into check, and unaddressed checks.
6. If legal, report the capture, whether the **opponent's** king is now in check,
   and the resulting board.

The helper `is_attacked(square, color)` powers both king-safety and check
reporting. Each case only reads a small 8×8 board, so the whole batch runs in
well under a second.

## Scope (per SPEC.md)

Implemented: standard movement for all six piece types, captures, and check/pin
detection. Out of scope (no test case needs them): castling, en passant,
promotion, and checkmate/stalemate.

## Verify

Self-check against the public sample cases using the provided grader:

```bash
python3 grade.py --cases test_cases_public.json --cmd "python3 my_solution/solve.py" --strict
```

Expected: `10 / 10 correct`.

## How it's graded

The organizer runs this one command and grades the result — no interactive
input, no network, no manual steps:

```
python3 my_solution/solve.py
```

Their process (per SPEC.md's submission contract):

1. Pipe the full JSON array of the **50 hidden test cases** into the program's **stdin**.
2. Read the full JSON array of results from **stdout** once the program exits.
3. Time the whole batch (start to finish).
4. Score: **correctness first** — the number of cases where the `legal` value
   matches — with **total time only as a tiebreaker**.

Concretely, with the organizer's private grader and hidden cases:

```bash
python3 grade.py --cases test_cases_graded.json --cmd "python3 my_solution/solve.py"
```

`grade.py` and `test_cases_graded.json` belong to the organizer and are not part
of this repo. The command above is identical to the public self-check — only the
case file differs.

## Files

- `my_solution/solve.py` — the solution (Python 3, standard library only).
- `my_solution/sample_input.json` — a couple of example cases to try.
- `SPEC.md` — the full problem statement.
- `grade.py`, `test_cases_public.json` — the self-check harness and public samples.

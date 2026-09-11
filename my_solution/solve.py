#!/usr/bin/env python3
"""
Chess move validator for the Version1 Code-Off (hand-rolled, no chess engine).

Reads one JSON array of cases from stdin, writes one JSON array of results to
stdout (same order). Mirrors reference_validator.py's rulings for the in-scope
rules (piece movement, captures, check/pins); castling, en passant, promotion
and checkmate/stalemate are out of scope.

Board: row 0 = rank 8, row 7 = rank 1; col 0 = file a, col 7 = file h.
Each cell is None or a 2-char token: color ('w'/'b') + piece (P/N/B/R/Q/K).
"""
import json
import sys

# Valid piece letters: Pawn, kNight, Bishop, Rook, Queen, King.
PIECE_LETTERS = ("P", "N", "B", "R", "Q", "K")

# Human-readable explanation for every illegal-move code we can return.
REASONS = {
    "NO_PIECE_AT_SOURCE": "There is no piece on the source square.",
    "WRONG_TURN": "That piece belongs to the side that is NOT to move.",
    "DESTINATION_OCCUPIED_BY_OWN_PIECE": "The destination square already has one of your own pieces on it.",
    "INVALID_PIECE_MOVEMENT": "This piece cannot move in that pattern.",
    "PATH_BLOCKED": "Another piece is blocking the path to the destination.",
    "PAWN_CANNOT_CAPTURE_FORWARD": "A pawn cannot move straight ahead onto an occupied square.",
    "PAWN_NO_PIECE_TO_CAPTURE": "A pawn can only move diagonally when capturing a piece.",
    "MOVE_EXPOSES_OWN_KING_TO_CHECK": "This move would leave (or put) your own king in check.",
    "INVALID_SQUARE": "One of the given squares is not a valid a1-h8 square.",
    "NULL_MOVE": "The source and destination squares are the same.",
    "INVALID_BOARD": "The board is not a valid 8x8 grid of pieces.",
}


def is_valid_board(board):
    """Return True only if `board` is a proper 8x8 grid where every square is
    either empty (None) or a valid 2-letter piece token like 'wP' or 'bK'.
    This is the first safety check so junk input can never crash the solver."""
    # Must be a list of exactly 8 rows.
    if not isinstance(board, list) or len(board) != 8:
        return False
    for row in board:
        # Each row must itself be a list of exactly 8 squares.
        if not isinstance(row, list) or len(row) != 8:
            return False
        for cell in row:
            if cell is None:
                continue  # empty square is allowed
            # A piece must be a 2-char string: color letter + piece letter.
            if not isinstance(cell, str) or len(cell) != 2:
                return False
            if cell[0] not in ("w", "b") or cell[1] not in PIECE_LETTERS:
                return False
    return True


def square_to_rc(sq):
    """Convert an algebraic square like 'e2' into (row, col) indices for our
    board array, or return None if the text isn't a real a1-h8 square.
    Example: 'e2' -> column 4 (file e), row 6 (because row 0 is rank 8)."""
    if not isinstance(sq, str) or len(sq) != 2:
        return None
    f, r = sq[0], sq[1]  # file letter, rank digit
    if f < "a" or f > "h" or r < "1" or r > "8":
        return None
    return (8 - int(r), ord(f) - ord("a"))


def shape_possible(ptype, color, from_rc, to_rc):
    """Could this piece EVER move in this shape, ignoring other pieces?
    Answers 'does a rook move in a straight line, a bishop diagonally', etc.
    Blocking and captures are checked elsewhere; this is pure geometry."""
    fr, fc = from_rc
    tr, tc = to_rc
    dr, dc = tr - fr, tc - fc  # row distance and column distance of the move
    if ptype == "N":
        # Knight: an L-shape (2 one way, 1 the other).
        return (abs(dr), abs(dc)) in ((1, 2), (2, 1))
    if ptype == "B":
        # Bishop: equal row and column distance (a diagonal).
        return dr != 0 and abs(dr) == abs(dc)
    if ptype == "R":
        # Rook: moves along a row OR a column, but not both.
        return (dr == 0) != (dc == 0)
    if ptype == "Q":
        # Queen: rook-like OR bishop-like.
        return (dr == 0) != (dc == 0) or (dr != 0 and abs(dr) == abs(dc))
    if ptype == "K":
        # King: exactly one square in any direction.
        return max(abs(dr), abs(dc)) == 1
    if ptype == "P":
        # Pawn: white moves up the board (row -1), black moves down (row +1).
        direction = -1 if color == "w" else 1
        start_row = 6 if color == "w" else 1  # the rank this color's pawns start on
        if dc == 0 and dr == direction:
            return True  # one square straight forward
        if dc == 0 and dr == 2 * direction and fr == start_row:
            return True  # two squares forward from the start rank
        if abs(dc) == 1 and dr == direction:
            return True  # one square diagonally (the capture shape)
        return False
    return False


def path_clear(board, from_rc, to_rc):
    """For sliding pieces (bishop/rook/queen): are all squares BETWEEN the start
    and destination empty? The two endpoints themselves are not checked here."""
    fr, fc = from_rc
    tr, tc = to_rc
    step_r = (tr > fr) - (tr < fr)  # step direction for rows: -1, 0, or +1
    step_c = (tc > fc) - (tc < fc)  # step direction for columns: -1, 0, or +1
    r, c = fr + step_r, fc + step_c  # begin one square along the path
    while (r, c) != (tr, tc):
        if board[r][c] is not None:
            return False  # a piece is standing in the way
        r += step_r
        c += step_c
    return True


def pseudo_legal(board, from_rc, to_rc):
    """Is the move legal by movement + board-occupancy rules, IGNORING whether it
    leaves your own king in check? Covers shape, blocked paths, pawn-capture
    rules, and not landing on your own piece. King safety is tested separately."""
    fr, fc = from_rc
    tr, tc = to_rc
    tok = board[fr][fc]
    color, ptype = tok[0], tok[1]
    # 1) The piece must be able to make this shape at all.
    if not shape_possible(ptype, color, from_rc, to_rc):
        return False
    dest = board[tr][tc]
    # 2) You can never land on your own piece.
    if dest is not None and dest[0] == color:
        return False
    if ptype == "P":
        if tc - fc == 0:
            # Straight pawn move: the target square must be empty...
            if dest is not None:
                return False
            # ...and for a two-square move the square jumped over must be empty too.
            if abs(tr - fr) == 2 and board[(fr + tr) // 2][fc] is not None:
                return False
            return True
        # Diagonal pawn move is only legal when capturing an enemy piece.
        return dest is not None
    if ptype in ("B", "R", "Q"):
        # Sliding pieces need a clear path between start and destination.
        return path_clear(board, from_rc, to_rc)
    # Knight and king have nothing to block once the shape is valid.
    return True


def is_attacked(board, rc, by):
    """Is the square `rc` attacked by ANY piece of color `by`?
    This is the heart of check detection: we call it on a king's square to see if
    it is under fire. We look outward from the square for each type of attacker."""
    r, c = rc
    # Pawns attack one square diagonally FORWARD. A white attacker sits on the
    # row below the target (r+1); a black attacker sits on the row above (r-1).
    pawn_row = r + 1 if by == "w" else r - 1
    if 0 <= pawn_row < 8:
        want = by + "P"
        for pc in (c - 1, c + 1):
            if 0 <= pc < 8 and board[pawn_row][pc] == want:
                return True
    # Knight attacks: any of the eight L-shaped jumps landing on an enemy knight.
    for dr, dc in ((1, 2), (1, -2), (-1, 2), (-1, -2), (2, 1), (2, -1), (-2, 1), (-2, -1)):
        nr, nc = r + dr, c + dc
        if 0 <= nr < 8 and 0 <= nc < 8:
            t = board[nr][nc]
            if t is not None and t[0] == by and t[1] == "N":
                return True
    # King attacks: an enemy king on any of the 8 adjacent squares.
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            if dr == 0 and dc == 0:
                continue
            nr, nc = r + dr, c + dc
            if 0 <= nr < 8 and 0 <= nc < 8:
                t = board[nr][nc]
                if t is not None and t[0] == by and t[1] == "K":
                    return True
    # Straight-line attacks: walk outward along each row/column until we hit a
    # piece; if it's an enemy rook or queen, this square is attacked.
    for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        nr, nc = r + dr, c + dc
        while 0 <= nr < 8 and 0 <= nc < 8:
            t = board[nr][nc]
            if t is not None:
                if t[0] == by and t[1] in ("R", "Q"):
                    return True
                break  # any other piece blocks the line of sight
            nr += dr
            nc += dc
    # Diagonal attacks: same idea, but for an enemy bishop or queen.
    for dr, dc in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
        nr, nc = r + dr, c + dc
        while 0 <= nr < 8 and 0 <= nc < 8:
            t = board[nr][nc]
            if t is not None:
                if t[0] == by and t[1] in ("B", "Q"):
                    return True
                break  # any other piece blocks the line of sight
            nr += dr
            nc += dc
    return False


def find_king(board, color):
    """Find the (row, col) of the given color's king, or None if it isn't on the
    board. Used to locate the king whose safety we need to check."""
    target = color + "K"
    for r in range(8):
        for c in range(8):
            if board[r][c] == target:
                return (r, c)
    return None


def make_move(board, from_rc, to_rc):
    """Return a NEW board with the piece moved from `from_rc` to `to_rc`.
    The original board is left untouched so we can safely 'try' a move and then
    inspect the result (for example, to see if it exposes our own king)."""
    nb = [row[:] for row in board]  # copy each row so the original is unchanged
    (fr, fc), (tr, tc) = from_rc, to_rc
    nb[tr][tc] = nb[fr][fc]  # place the piece on the destination square
    nb[fr][fc] = None        # clear the square it moved from
    return nb


def _illegal(code):
    """Build the standard result object for an illegal move: fills in the matching
    human-readable reason and leaves the 'legal-only' fields empty."""
    return {
        "legal": False,
        "reason_code": code,
        "reason": REASONS[code],
        "capture": None,
        "opponent_in_check": False,
        "resulting_board": None,
    }


def validate(case):
    """Decide whether ONE move is legal and describe the outcome.
    Runs the cheapest checks first and stops at the first failure; if the move
    survives every check it is legal, and we then report capture / check / the
    resulting board. Returns the result dict described in SPEC.md."""
    board = case.get("board")
    move = case.get("move") or {}
    from_str, to_str = move.get("from"), move.get("to")

    # Step 0: the board itself must be a valid 8x8 grid of pieces.
    if not is_valid_board(board):
        return _illegal("INVALID_BOARD")

    # Step 1: both squares must be real board squares (a1-h8).
    from_rc = square_to_rc(from_str)
    to_rc = square_to_rc(to_str)
    if from_rc is None or to_rc is None:
        return _illegal("INVALID_SQUARE")
    # Step 2: you must actually move somewhere.
    if from_str == to_str:
        return _illegal("NULL_MOVE")

    turn_color = "w" if case.get("turn") == "white" else "b"
    (fr, fc), (tr, tc) = from_rc, to_rc
    piece = board[fr][fc]

    # Step 3: there has to be a piece on the source square.
    if piece is None:
        return _illegal("NO_PIECE_AT_SOURCE")
    # Step 4: it must belong to the side whose turn it is.
    if piece[0] != turn_color:
        return _illegal("WRONG_TURN")
    # Step 5: you can't capture your own piece.
    dest = board[tr][tc]
    if dest is not None and dest[0] == piece[0]:
        return _illegal("DESTINATION_OCCUPIED_BY_OWN_PIECE")

    # Step 6: the move must obey the piece's movement rules. If it doesn't, work
    # out the most specific reason (bad shape, a pawn rule, or a blocked path).
    if not pseudo_legal(board, from_rc, to_rc):
        if not shape_possible(piece[1], piece[0], from_rc, to_rc):
            return _illegal("INVALID_PIECE_MOVEMENT")
        if piece[1] == "P":
            if tc - fc != 0:
                return _illegal("PAWN_NO_PIECE_TO_CAPTURE")
            return _illegal("PAWN_CANNOT_CAPTURE_FORWARD")
        return _illegal("PATH_BLOCKED")

    # Step 7: try the move on a copy and make sure it doesn't leave OUR king in
    # check. This single test covers pins, moving into check, and ignoring check.
    after = make_move(board, from_rc, to_rc)
    opponent = "b" if piece[0] == "w" else "w"
    own_king = find_king(after, piece[0])
    if own_king is None or is_attacked(after, own_king, opponent):
        return _illegal("MOVE_EXPOSES_OWN_KING_TO_CHECK")

    # The move is legal: describe what happened.
    capture = {"piece": dest, "square": to_str} if dest is not None else None
    opp_king = find_king(after, opponent)
    # Does our move put the OPPONENT's king in check?
    opponent_in_check = opp_king is not None and is_attacked(after, opp_king, piece[0])
    return {
        "legal": True,
        "reason_code": None,
        "reason": None,
        "capture": capture,
        "opponent_in_check": opponent_in_check,
        "resulting_board": after,
    }


def main():
    """Program entry point: read the whole JSON array of cases from stdin,
    validate each one in order, and write the JSON array of results to stdout."""
    cases = json.load(sys.stdin)  # read the entire input array in one go
    json.dump([validate(c) for c in cases], sys.stdout)


if __name__ == "__main__":
    main()

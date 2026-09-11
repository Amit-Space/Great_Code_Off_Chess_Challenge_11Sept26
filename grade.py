#!/usr/bin/env python3
"""
Organizer grading harness for the Version1 Code-Off chess challenge.

Zero third-party dependencies (stdlib only) -- this runs on the day, on
whatever laptop is judging, regardless of what language teams coded in.

Contract with a team's submission (see SPEC.md):
  - The submission is invoked as a single command (e.g. "python3 solve.py",
    "./solve", "node solve.js").
  - It is fed ONE JSON array on stdin: [{"board":..., "turn":..., "move":...}, ...]
  - It must print ONE JSON array on stdout, same length and order, each
    element shaped like reference_validator.validate_move()'s output.
  - The whole batch is timed as one wall-clock duration (process spawn
    overhead is intentionally excluded from correctness scoring by timing
    the batch rather than each case, but see --per-case for a rougher
    per-case timing breakdown that DOES include spawn overhead if you run
    it that way instead).

Usage:
  ./venv/bin/python3 grade.py --cases test_cases_graded.json --cmd "python3 team_a/solve.py"
  ./venv/bin/python3 grade.py --cases test_cases_graded.json --cmd "python3 team_a/solve.py" --timeout 10 --json report_team_a.json

Scoring fields checked per case:
  - legal        (required exact match -- this is the primary score)
  - reason_code  (only checked when expected is illegal; informational,
                  does not affect the primary score -- see --strict)
  - capture      (only checked when expected is legal; informational)
  - opponent_in_check (only checked when expected is legal; informational)

Rank teams primarily by "legal_correct" (out of total), tie-break by
elapsed_seconds (lower is better). Pass --strict to require reason_code /
capture / opponent_in_check to also match for a case to count as correct.
"""

import argparse
import json
import shlex
import subprocess
import sys
import time


def load_cases(path):
    with open(path) as f:
        return json.load(f)


def run_submission(cmd, inputs, timeout):
    payload = json.dumps(inputs)
    start = time.perf_counter()
    try:
        proc = subprocess.run(
            shlex.split(cmd),
            input=payload,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        elapsed = time.perf_counter() - start
        return None, elapsed, f"TIMEOUT after {timeout}s"
    elapsed = time.perf_counter() - start

    if proc.returncode != 0:
        return None, elapsed, f"non-zero exit ({proc.returncode}): {proc.stderr.strip()[:500]}"

    try:
        outputs = json.loads(proc.stdout)
    except json.JSONDecodeError as e:
        return None, elapsed, f"stdout was not valid JSON: {e}. First 300 chars: {proc.stdout[:300]!r}"

    if not isinstance(outputs, list):
        return None, elapsed, "stdout JSON must be a top-level array"

    return outputs, elapsed, None


def compare(expected, actual, strict):
    """Returns (correct: bool, notes: str)."""
    if not isinstance(actual, dict):
        return False, "result is not a JSON object"

    if "legal" not in actual:
        return False, "missing 'legal' field"

    if bool(actual["legal"]) != bool(expected["legal"]):
        return False, f"expected legal={expected['legal']}, got legal={actual.get('legal')!r}"

    if not strict:
        return True, "ok"

    if not expected["legal"]:
        if actual.get("reason_code") != expected["reason_code"]:
            return False, f"expected reason_code={expected['reason_code']}, got {actual.get('reason_code')!r}"
    else:
        exp_cap = expected.get("capture")
        act_cap = actual.get("capture")
        if exp_cap != act_cap:
            return False, f"expected capture={exp_cap}, got {act_cap!r}"
        if bool(actual.get("opponent_in_check")) != bool(expected.get("opponent_in_check")):
            return False, (
                f"expected opponent_in_check={expected.get('opponent_in_check')}, "
                f"got {actual.get('opponent_in_check')!r}"
            )
    return True, "ok"


def grade(cmd, cases, timeout, strict):
    inputs = [c["input"] for c in cases]
    outputs, elapsed, error = run_submission(cmd, inputs, timeout)

    report = {
        "cmd": cmd,
        "total_cases": len(cases),
        "elapsed_seconds": round(elapsed, 4),
        "run_error": error,
        "legal_correct": 0,
        "strict_correct": 0,
        "failures": [],
    }

    if error is not None:
        report["failures"] = [{"id": c["id"], "note": "submission did not run: " + error} for c in cases]
        return report

    if len(outputs) != len(cases):
        report["run_error"] = f"expected {len(cases)} results, got {len(outputs)}"
        report["failures"] = [{"id": c["id"], "note": "count mismatch"} for c in cases]
        return report

    for case, actual in zip(cases, outputs):
        expected = case["expected"]
        legal_ok, legal_note = compare(expected, actual, strict=False)
        strict_ok, strict_note = compare(expected, actual, strict=True) if strict else (legal_ok, legal_note)

        if legal_ok:
            report["legal_correct"] += 1
        if strict_ok:
            report["strict_correct"] += 1

        primary_ok = strict_ok if strict else legal_ok
        primary_note = strict_note if strict else legal_note
        if not primary_ok:
            report["failures"].append({"id": case["id"], "note": primary_note})

    return report


def print_report(report, strict):
    print(f"Command:        {report['cmd']}")
    primary = report["strict_correct"] if strict else report["legal_correct"]
    print(f"Score:          {primary} / {report['total_cases']} correct")
    print(f"Elapsed:        {report['elapsed_seconds']}s (whole batch)")
    if report["run_error"]:
        print(f"Run error:      {report['run_error']}")
    if report["failures"]:
        print(f"Failures ({len(report['failures'])}):")
        for f in report["failures"][:20]:
            print(f"  - {f['id']}: {f['note']}")
        if len(report["failures"]) > 20:
            print(f"  ... and {len(report['failures']) - 20} more")
    else:
        print("All cases correct.")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cases", required=True, help="Path to a test cases JSON file (e.g. test_cases_graded.json)")
    ap.add_argument("--cmd", required=True, help="Shell command that runs the team's submission")
    ap.add_argument("--timeout", type=float, default=15.0, help="Max seconds allowed for the whole batch (default 15)")
    ap.add_argument("--strict", action="store_true", help="Also require reason_code/capture/opponent_in_check to match")
    ap.add_argument("--json", metavar="PATH", help="Also write the full report as JSON to this path")
    args = ap.parse_args()

    cases = load_cases(args.cases)
    report = grade(args.cmd, cases, args.timeout, args.strict)
    print_report(report, args.strict)

    if args.json:
        with open(args.json, "w") as f:
            json.dump(report, f, indent=2)
        print(f"\nFull report written to {args.json}")


if __name__ == "__main__":
    main()

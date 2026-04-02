"""
Pylint Report Summary
Usage: python pylint_summary.py [path_to_report.txt]
Defaults to pylint_report.txt in the same directory.
"""

import re
import sys
from collections import defaultdict
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────

CATEGORY_LABELS = {
    "E": ("ERROR", "\033[91m"),       # red
    "W": ("WARNING", "\033[93m"),     # yellow
    "R": ("REFACTOR", "\033[94m"),    # blue
    "C": ("CONVENTION", "\033[96m"),  # cyan
}
RESET = "\033[0m"
BOLD  = "\033[1m"

FRIENDLY_NAMES = {
    "broad-exception-caught":        "Broad except (catch)",
    "broad-exception-raised":        "Broad except (raise)",
    "logging-fstring-interpolation": "f-string in logging",
    "raise-missing-from":            "raise missing 'from'",
    "no-else-return":                "Unnecessary else/return",
    "no-else-raise":                 "Unnecessary else/raise",
    "too-many-locals":               "Too many local vars",
    "too-many-statements":           "Too many statements",
    "too-many-branches":             "Too many branches",
    "too-many-instance-attributes":  "Too many attributes",
    "too-many-return-statements":    "Too many returns",
    "too-many-arguments":            "Too many arguments",
    "wrong-import-order":            "Wrong import order",
    "duplicate-code":                "Duplicate code",
    "line-too-long":                 "Line too long",
    "invalid-name":                  "Invalid name",
    "missing-function-docstring":    "Missing docstring",
    "used-before-assignment":        "Used before assignment",
    "ungrouped-imports":             "Ungrouped imports",
    "import-outside-toplevel":       "Import outside toplevel",
    "redefined-outer-name":          "Redefined outer name",
    "no-member":                     "No member (attribute)",
    "too-few-public-methods":        "Too few public methods",
    "attribute-defined-outside-init":"Attribute outside __init__",
    "consider-using-in":             "Use 'in' for comparisons",
    "arguments-differ":              "Arguments differ (override)",
    "superfluous-parens":            "Superfluous parentheses",
    "no-else-break":                 "Unnecessary else/break",
    "missing-class-docstring":       "Missing class docstring",
    "R0801":                         "Duplicate code (R0801)",
}

# ── Parse ─────────────────────────────────────────────────────────────────────

def parse_report(path: Path):
    issue_re = re.compile(
        r"^(?P<file>[\w\\/.\-]+\.py):\d+:\d+:\s+"
        r"(?P<code>[EWRC]\d+):\s+.+\((?P<symbol>[\w\-]+)\)"
    )
    rating_re = re.compile(r"rated at\s+([\d.]+)/10.*previous.*?([\d.]+)/10.*?([+-][\d.]+)")

    by_file    = defaultdict(int)
    by_cat     = defaultdict(int)
    by_symbol  = defaultdict(int)
    rating     = delta = prev = None

    for line in path.read_text(encoding="utf-8-sig").splitlines():
        m = issue_re.match(line.strip())
        if m:
            short = m.group("file").replace("app\\", "").replace("app/", "")
            by_file[short]          += 1
            by_cat[m.group("code")[0]] += 1
            by_symbol[m.group("symbol")] += 1
            continue
        r = rating_re.search(line)
        if r:
            rating, prev, delta = r.group(1), r.group(2), r.group(3)

    return by_file, by_cat, by_symbol, rating, prev, delta

# ── Display ───────────────────────────────────────────────────────────────────

def bar(count, max_count, width=24):
    filled = round(count / max_count * width) if max_count else 0
    return "█" * filled + "░" * (width - filled)

def print_summary(by_file, by_cat, by_symbol, rating, prev, delta):
    total = sum(by_cat.values())

    print(f"\n{BOLD}{'─'*56}{RESET}")
    print(f"{BOLD}  PYLINT REPORT SUMMARY{RESET}")
    print(f"{'─'*56}")

    # Score
    if rating:
        sign_color = "\033[92m" if "+" in (delta or "") else "\033[91m"
        print(f"\n  Score:   {BOLD}{rating}/10{RESET}   "
              f"(prev {prev}  {sign_color}{delta}{RESET})")

    # Category breakdown
    print(f"\n  {BOLD}Issues by category  ({total} total){RESET}")
    for code in ("E", "W", "R", "C"):
        count = by_cat.get(code, 0)
        if not count:
            continue
        label, color = CATEGORY_LABELS[code]
        print(f"  {color}{label:<12}{RESET} {count:>3}  {bar(count, total)}")

    # Top issues
    print(f"\n  {BOLD}Top issue types{RESET}")
    top = sorted(by_symbol.items(), key=lambda x: -x[1])[:10]
    max_c = top[0][1] if top else 1
    for sym, cnt in top:
        name = FRIENDLY_NAMES.get(sym, sym)
        print(f"  {cnt:>3}  {bar(cnt, max_c, 16)}  {name}")

    # Hotspot files
    print(f"\n  {BOLD}Hotspot files{RESET}")
    top_files = sorted(by_file.items(), key=lambda x: -x[1])[:8]
    max_f = top_files[0][1] if top_files else 1
    for f, cnt in top_files:
        print(f"  {cnt:>3}  {bar(cnt, max_f, 16)}  {f}")

    print(f"\n{'─'*56}\n")

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("pylint_report.txt")
    if not path.exists():
        print(f"File not found: {path}")
        sys.exit(1)
    by_file, by_cat, by_symbol, rating, prev, delta = parse_report(path)
    print_summary(by_file, by_cat, by_symbol, rating, prev, delta)

if __name__ == "__main__":
    main()
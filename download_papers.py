#!/usr/bin/env python3
"""
Multithreaded downloader for all papers in all_papers.json.
Files are saved to ./papers/ with descriptive names built from metadata.

Filename format:
  {Subject} - {Year} - {Semester} - {Exam} - Slot {Slot} - {Campus}[_ANS].pdf

Example:
  Machine Learning [BCSE209L] - 2024-2025 - Fall Semester - FAT - Slot B1 - Vellore.pdf
"""

import json
import os
import re
import sys
import threading
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

INPUT_FILE  = "all_papers.json"
OUTPUT_DIR  = "papers"
MAX_WORKERS = 16          # concurrent downloads

# ── ANSI colour helpers ────────────────────────────────────────────────────────
RESET   = "\033[0m"
BOLD    = "\033[1m"
DIM     = "\033[2m"

GREEN   = "\033[32m"
YELLOW  = "\033[33m"
RED     = "\033[31m"
CYAN    = "\033[36m"
BLUE    = "\033[34m"
WHITE   = "\033[97m"

def c(color, text):
    return f"{color}{text}{RESET}"


# ── Filename helpers ───────────────────────────────────────────────────────────
def sanitize(text):
    """Remove/replace characters that are invalid in filenames."""
    text = text.replace("/", "-").replace("\\", "-")
    text = re.sub(r'[<>:"|?*\x00-\x1f]', "", text)
    return text.strip()


def build_filename(paper):
    subject  = sanitize(paper.get("subject",  "Unknown Subject"))
    year     = sanitize(paper.get("year",     "Unknown Year"))
    semester = sanitize(paper.get("semester", "Unknown Semester"))
    exam     = sanitize(paper.get("exam",     "Unknown Exam"))
    slot     = sanitize(paper.get("slot",     "Unknown Slot"))
    campus   = sanitize(paper.get("campus",   "Unknown Campus"))
    ans_key  = paper.get("answer_key_included", False)

    name = f"{subject} - {year} - {semester} - {exam} - Slot {slot} - {campus}"
    if ans_key:
        name += "_ANS"
    name += ".pdf"
    return name


_print_lock = threading.Lock()
_stats = {"ok": 0, "skip": 0, "fail": 0}
_failed_msgs = []


def download(paper, bar):
    """Download one paper. Returns (status, message) where status in ok|skip|fail."""
    file_url = paper.get("file_url", "")
    if not file_url:
        with _print_lock:
            _stats["fail"] += 1
            _failed_msgs.append("(no file_url)")
            bar.write(c(RED,    "  [FAIL] ") + c(DIM, "(no file_url)"))
            bar.update(1)
        return ("fail", "(no file_url)")

    filename = build_filename(paper)
    dest = os.path.join(OUTPUT_DIR, filename)
    short = filename[:80] + ("…" if len(filename) > 80 else "")

    if os.path.exists(dest):
        with _print_lock:
            _stats["skip"] += 1
            bar.write(c(YELLOW, "  [SKIP] ") + c(DIM, short))
            bar.update(1)
        return ("skip", filename)

    try:
        req = urllib.request.Request(file_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read()
        with open(dest, "wb") as f:
            f.write(data)
        size_kb = len(data) / 1024
        with _print_lock:
            _stats["ok"] += 1
            bar.write(
                c(GREEN, "  [ OK ] ") +
                c(WHITE, short) +
                c(DIM, f"  ({size_kb:.1f} KB)")
            )
            bar.update(1)
        return ("ok", filename)

    except Exception as e:
        with _print_lock:
            _stats["fail"] += 1
            msg = f"{short}: {e}"
            _failed_msgs.append(msg)
            bar.write(c(RED, "  [FAIL] ") + c(RED, msg))
            bar.update(1)
        return ("fail", filename)


def main():
    # Strip colour codes when not writing to a real terminal
    if not sys.stdout.isatty():
        global GREEN, YELLOW, RED, CYAN, BLUE, WHITE, BOLD, DIM, RESET
        GREEN = YELLOW = RED = CYAN = BLUE = WHITE = BOLD = DIM = RESET = ""

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        papers = json.load(f)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    total = len(papers)

    print(c(BOLD + CYAN, "\n  Papers Downloader"))
    print(c(DIM,         f"  {total} papers  •  {MAX_WORKERS} workers  •  → ./{OUTPUT_DIR}/\n"))

    bar_fmt = (
        c(BLUE, "  {desc}") + " " +
        c(CYAN, "{bar}") + " " +
        c(WHITE, "{n_fmt}/{total_fmt}") +
        c(DIM, " [{elapsed}<{remaining}, {rate_fmt}]")
    )

    with tqdm(
        total=total,
        desc=c(BOLD, "downloading"),
        bar_format=bar_fmt,
        ncols=100,
        dynamic_ncols=True,
        leave=True,
        colour="cyan",
    ) as bar:
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {executor.submit(download, p, bar): p for p in papers}
            for future in as_completed(futures):
                future.result()

    ok   = _stats["ok"]
    skip = _stats["skip"]
    fail = _stats["fail"]

    print()
    print(c(BOLD, "  ── Summary " + "─" * 40))
    print(c(GREEN,  f"  Downloaded : {ok}"))
    print(c(YELLOW, f"  Skipped    : {skip}  (already existed)"))
    if fail:
        print(c(RED,  f"  Failed     : {fail}"))
    else:
        print(c(DIM,  f"  Failed     : {fail}"))
    print(c(BOLD,   f"  Total      : {total}"))
    print()

    if _failed_msgs:
        print(c(RED, "  Failed files:"))
        for m in _failed_msgs:
            print(c(RED, f"    • {m}"))
        print()


if __name__ == "__main__":
    main()

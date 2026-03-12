#!/usr/bin/env python3
"""
Scrape every paper and its metadata from papers.codechefvit.com

Steps:
  1. GET /api/course-list  -> list of all courses
  2. For each course: GET /api/papers?subject={name}  -> papers + metadata
  3. Write all results to all_papers.json and a summary to all_papers.txt
"""

import json
import time
import urllib.request
import urllib.parse

BASE = "https://www.papers.codechefvit.com"
COURSE_LIST_URL = f"{BASE}/api/course-list"
PAPERS_URL = f"{BASE}/api/papers"

OUTPUT_JSON = "all_papers.json"
OUTPUT_TXT  = "all_papers.txt"

DELAY = 0.3   # seconds between requests, be polite


def fetch_json(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def main():
    # --- Step 1: fetch all courses ---
    print("Fetching course list...")
    courses = fetch_json(COURSE_LIST_URL)
    print(f"  Found {len(courses)} courses.")

    all_papers = []
    failed_courses = []

    # --- Step 2: fetch papers for each course ---
    for i, course in enumerate(courses, 1):
        name = course.get("name", "").strip()
        if not name:
            continue

        url = f"{PAPERS_URL}?subject={urllib.parse.quote(name)}"
        print(f"[{i}/{len(courses)}] {name}")

        try:
            data = fetch_json(url)
            papers = data.get("papers", [])
            all_papers.extend(papers)
            print(f"          -> {len(papers)} papers")
        except Exception as e:
            print(f"          -> ERROR: {e}")
            failed_courses.append(name)

        time.sleep(DELAY)

    print(f"\nTotal papers collected: {len(all_papers)}")
    if failed_courses:
        print(f"Failed courses ({len(failed_courses)}):")
        for c in failed_courses:
            print(f"  - {c}")

    # --- Step 3: write JSON output ---
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(all_papers, f, indent=2, ensure_ascii=False)
    print(f"\nWrote full metadata to {OUTPUT_JSON}")

    # --- Step 4: write human-readable text summary ---
    with open(OUTPUT_TXT, "w", encoding="utf-8") as f:
        for p in all_papers:
            f.write(f"Subject:   {p.get('subject', 'N/A')}\n")
            f.write(f"Exam:      {p.get('exam', 'N/A')}\n")
            f.write(f"Year:      {p.get('year', 'N/A')}\n")
            f.write(f"Semester:  {p.get('semester', 'N/A')}\n")
            f.write(f"Slot:      {p.get('slot', 'N/A')}\n")
            f.write(f"Campus:    {p.get('campus', 'N/A')}\n")
            f.write(f"Ans Key:   {p.get('answer_key_included', False)}\n")
            f.write(f"PDF URL:   {p.get('file_url', 'N/A')}\n")
            f.write("-" * 70 + "\n")
    print(f"Wrote text summary to {OUTPUT_TXT}")


if __name__ == "__main__":
    main()

"""
reset_pipeline.py — Prepare the pipeline for a new job description run.

What this script does:
  1. Archives the current run's output files to output/runs/<timestamp>/
  2. Resets all runtime state in metadata.json (iteration, drafts, audit_log,
     committee_history, rejected_content, humanizer_replacements, final_output,
     job_description analysis).
  3. Preserves permanently fixed fields: pipeline_version, locked_fields,
     master_resume, config.

Usage:
  python scripts/reset_pipeline.py
  python scripts/reset_pipeline.py --jd path/to/new_job_description.txt

After running this script, drop your new job_description.txt in the workspace
root (or pass --jd) and start the pipeline.
"""

import argparse
import json
import os
import shutil
import sys
from datetime import datetime, timezone

METADATA_PATH = "metadata.json"
OUTPUT_DIR = "output"
ARCHIVE_BASE = os.path.join(OUTPUT_DIR, "runs")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_metadata() -> dict:
    with open(METADATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_metadata(data: dict):
    with open(METADATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def archive_previous_run(metadata: dict) -> str | None:
    """Move output files from the last run into output/runs/<timestamp>/."""
    final = metadata.get("final_output", {})
    files_to_archive = [
        final.get("resume_file"),
        final.get("latex_file"),
        final.get("cover_letter_file"),
        final.get("audit_report_file"),
    ]

    # Also archive any draft files referenced in audit_log
    for entry in metadata.get("audit_log", []):
        pass  # draft paths are on current_draft, not audit_log

    draft_file = metadata.get("current_draft", {}).get("file")
    if draft_file:
        files_to_archive.append(draft_file)

    # Collect all *.md and *.txt files in output/ directly (not in subdirs)
    try:
        for name in os.listdir(OUTPUT_DIR):
            path = os.path.join(OUTPUT_DIR, name)
            if os.path.isfile(path) and name.endswith((".md", ".txt")):
                files_to_archive.append(path)
    except FileNotFoundError:
        pass

    # Deduplicate by normalised absolute path, filter to existing files only
    seen = set()
    to_move = []
    for p in files_to_archive:
        if not p:
            continue
        norm = os.path.normcase(os.path.abspath(p))
        if norm not in seen and os.path.isfile(p):
            seen.add(norm)
            to_move.append(p)

    if not to_move:
        return None

    # Build archive folder name from previous run info
    completed_at = metadata.get("final_output", {}).get("completed_at", "")
    company = metadata.get("job_description", {}).get("company", "unknown")
    role = metadata.get("job_description", {}).get("role", "unknown")
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    folder_name = f"{ts}_{company}_{role}".replace(" ", "_").replace("/", "-")[:80]
    archive_dir = os.path.join(ARCHIVE_BASE, folder_name)
    os.makedirs(archive_dir, exist_ok=True)

    _out = open(sys.stdout.fileno(), mode="w", encoding="utf-8", closefd=False, buffering=1)
    for src in to_move:
        dest = os.path.join(archive_dir, os.path.basename(src))
        shutil.move(src, dest)
        _out.write(f"  Archived: {src} -> {dest}\n")

    # Write a small summary into the archive folder
    summary = {
        "archived_at": datetime.now(timezone.utc).isoformat(),
        "company": company,
        "role": role,
        "final_score": metadata.get("final_output", {}).get("final_average_score"),
        "total_iterations": metadata.get("final_output", {}).get("total_iterations"),
        "completed_at": completed_at,
        "files": [os.path.basename(p) for p in to_move],
    }
    with open(os.path.join(archive_dir, "run_summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    return archive_dir


def build_clean_state(metadata: dict, new_jd_file: str | None) -> dict:
    """Return a fresh metadata dict, preserving only the permanent fields."""
    jd_file = new_jd_file or metadata.get("job_description", {}).get("raw_file", "job_description.txt")

    return {
        "pipeline_version": metadata.get("pipeline_version", "1.0.0"),
        "locked_fields": metadata["locked_fields"],
        "current_state": {
            "iteration": 0,
            "phase": "idle",
            "status": "ready",
            "last_updated": None,
        },
        "job_description": {
            "raw_file": jd_file,
            "company": None,
            "role": None,
            "seniority_signals": None,
            "company_context": None,
            "core_pain_points": [],
            "latent_requirements": [],
            "keywords_extracted": [],
        },
        "master_resume": metadata["master_resume"],
        "iterations": [],
        "current_draft": {
            "file": None,
            "auditor_passed": False,
            "humanizer_applied": False,
            "committee_scores": None,
            "committee_average": None,
            "creative_buffer_used": {
                "new_word_count_estimate": 0,
                "description": "",
            },
        },
        "jd_blueprint": {},
        "audit_log": [],
        "humanizer_replacements": [],
        "committee_history": [],
        "rejected_content": [],
        "final_output": {},
        "config": metadata["config"],
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Reset the resume pipeline for a new run.")
    parser.add_argument(
        "--jd",
        metavar="PATH",
        default=None,
        help="Path to the new job_description.txt (default: keep existing path in metadata).",
    )
    args = parser.parse_args()

    out = open(sys.stdout.fileno(), mode="w", encoding="utf-8", closefd=False, buffering=1)

    out.write("=" * 60 + "\n")
    out.write("  RESUME PIPELINE -- RESET\n")
    out.write("=" * 60 + "\n")

    if not os.path.isfile(METADATA_PATH):
        out.write(f"[ERROR] {METADATA_PATH} not found. Run from the workspace root.\n")
        raise SystemExit(1)

    metadata = load_metadata()
    status = metadata.get("current_state", {}).get("status", "unknown")
    company = metadata.get("job_description", {}).get("company") or "no previous run"
    role = metadata.get("job_description", {}).get("role") or ""
    score = metadata.get("final_output", {}).get("final_average_score")

    out.write(f"\n  Previous run   : {company} -- {role}\n")
    out.write(f"  Previous status: {status}\n")
    if score is not None:
        out.write(f"  Previous score : {score}/10\n")

    out.write("\n  Step 1 -- Archiving previous output files...\n")
    archive_dir = archive_previous_run(metadata)
    if archive_dir:
        out.write(f"  [OK] Archived to: {archive_dir}\n")
    else:
        out.write("  [OK] No output files to archive.\n")

    out.write("\n  Step 2 -- Resetting metadata.json runtime state...\n")
    clean = build_clean_state(metadata, args.jd)
    save_metadata(clean)
    out.write("  [OK] metadata.json reset. Preserved: locked_fields, master_resume, config.\n")

    if args.jd:
        out.write(f"\n  Step 3 -- New JD file set to: {args.jd}\n")
        if not os.path.isfile(args.jd):
            out.write(f"  [!!] Warning: '{args.jd}' does not exist yet. Create it before running the pipeline.\n")
    else:
        jd_path = clean["job_description"]["raw_file"]
        out.write(f"\n  Step 3 -- JD file path unchanged: {jd_path}\n")
        if os.path.isfile(jd_path):
            out.write(f"  [OK] '{jd_path}' exists. Replace its content with your new job description.\n")
        else:
            out.write(f"  [!!] Warning: '{jd_path}' does not exist. Create it before running the pipeline.\n")

    out.write("\n" + "=" * 60 + "\n")
    out.write("  RESET COMPLETE -- pipeline is ready for a new run.\n")
    out.write("  Next step: update job_description.txt, then run the pipeline.\n")
    out.write("=" * 60 + "\n\n")


if __name__ == "__main__":
    main()

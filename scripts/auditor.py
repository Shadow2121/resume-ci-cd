"""
Iron Auditor — Deterministic hard-gate for the Resume CI/CD Pipeline.

All locked values (name, institution, degree, job titles, project titles) are
read from metadata.json at runtime — nothing is hardcoded here. To update
locked fields, edit metadata.json only.

Checks performed (all must pass for the build to succeed):
  1. Name lock            — candidate name must appear verbatim.
  2. Education lock       — institution + degree must appear verbatim.
  3. Experience title lock— every job title from locked_fields must appear verbatim.
  4. Project integrity    — every ### project heading in draft must exist in master list.
  5. Banned sections      — 'Additional Activities' section must not appear.
  6. Resume length        — total body word count must not exceed config.resume_max_words.
  7. Bullet length        — no single bullet may exceed config.bullet_max_words words.
  8. Creative-buffer cap  — new content must not exceed configured % of total draft word count.

Exit codes:
  0  All checks passed.
  1  One or more checks failed (errors printed to stdout for the Architect to read).
"""

import sys
import re
import json
import argparse
from pathlib import Path
from datetime import datetime, timezone


# ---------------------------------------------------------------------------
# Markdown helpers
# ---------------------------------------------------------------------------

def load_md(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def count_words(md: str) -> int:
    """Count words in Markdown source, stripping syntax markers."""
    text = re.sub(r"!\[.*?\]\(.*?\)", " ", md)
    text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)
    text = re.sub(r"`{1,3}[^`]*`{1,3}", " ", text)
    text = re.sub(r"^#{1,6}\s*", " ", text, flags=re.MULTILINE)
    text = re.sub(r"(\*\*|__)(.*?)\1", r"\2", text)
    text = re.sub(r"(\*|_)(.*?)\1", r"\2", text)
    text = re.sub(r"^[-*+]\s+", " ", text, flags=re.MULTILINE)
    text = re.sub(r"^\d+\.\s+", " ", text, flags=re.MULTILINE)
    text = re.sub(r"^---+$", " ", text, flags=re.MULTILINE)
    text = re.sub(r"[|]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return len(text.split())


def extract_section_headings(md: str, section_name: str) -> list[str]:
    """
    Extract all ### headings under a given ## section.
    Returns the heading text up to any '|' separator, stripped.
    """
    headings = []
    in_section = False
    for line in md.splitlines():
        stripped = line.strip()
        if re.match(r"^##\s+" + re.escape(section_name), stripped, re.IGNORECASE):
            in_section = True
            continue
        if in_section:
            if re.match(r"^##\s+(?!#)", stripped):
                break
            m = re.match(r"^###\s+(.+)", stripped)
            if m:
                headings.append(m.group(1).split("|")[0].strip())
    return headings


# ---------------------------------------------------------------------------
# Audit result collector
# ---------------------------------------------------------------------------

class AuditResult:
    def __init__(self):
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.info: list[str] = []
        self.passed: bool = True

    def fail(self, msg: str):
        self.errors.append(f"Error: {msg}")
        self.passed = False

    def warn(self, msg: str):
        self.warnings.append(f"Warning: {msg}")

    def note(self, msg: str):
        self.info.append(f"Info: {msg}")


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------

def check_name_lock(draft: str, locked: dict, result: AuditResult):
    name = locked.get("name", "")
    if not name:
        result.warn("locked_fields.name is empty — skipping name lock check.")
        return
    if name not in draft:
        result.fail(
            f"Name lock violated — '{name}' not found in draft. "
            "The candidate name must appear verbatim."
        )
    else:
        result.note(f"Name lock OK — '{name}' present.")


def check_education_lock(draft: str, locked: dict, result: AuditResult):
    edu = locked.get("education", {})
    institution = edu.get("institution", "")
    degree = edu.get("degree", "")
    missing = []
    if institution and institution not in draft:
        missing.append(institution)
    if degree and degree not in draft:
        missing.append(degree)
    if missing:
        result.fail(
            "Education lock violated — the following strings are missing: "
            + ", ".join(f"'{s}'" for s in missing)
        )
    else:
        result.note("Education lock OK.")


def check_experience_title_lock(draft: str, locked: dict, result: AuditResult):
    """Every experience job title from the master must appear verbatim in the draft."""
    titles = locked.get("experience_titles", [])
    if not titles:
        result.warn("locked_fields.experience_titles is empty — skipping job title check.")
        return
    missing = [t for t in titles if t not in draft]
    if missing:
        result.fail(
            "Experience title lock violated — the following job titles were changed or removed: "
            + ", ".join(f"'{t}'" for t in missing)
            + ". Job titles must appear verbatim — they cannot be renamed to fit the JD."
        )
    else:
        result.note(f"Experience title lock OK — all {len(titles)} job title(s) present.")


def check_project_integrity(draft: str, master: str, locked: dict, result: AuditResult):
    """
    Every project heading in the draft must exist in the master's project list.
    Projects may be omitted (selection is allowed), but new ones cannot be added.
    """
    allowed = locked.get("project_titles", [])
    if not allowed:
        result.warn("locked_fields.project_titles is empty — falling back to master content scan.")
        allowed = extract_section_headings(master, "Projects")

    draft_projects = extract_section_headings(draft, "Projects")

    fabricated = []
    for title in draft_projects:
        matched = any(
            title.lower() in a.lower() or a.lower() in title.lower()
            for a in allowed
        )
        if not matched:
            fabricated.append(title)

    if fabricated:
        result.fail(
            f"Project integrity violated — {len(fabricated)} project(s) found in draft that "
            "do not exist in master_resume.md: "
            + ", ".join(f"'{t}'" for t in fabricated)
            + ". Only projects from the master resume are permitted."
        )
    else:
        result.note(
            f"Project integrity OK — {len(draft_projects)}/{len(allowed)} "
            f"master project(s) included, {len(allowed) - len(draft_projects)} excluded."
        )



def check_no_banned_sections(draft: str, result: AuditResult):
    """The draft must not contain any banned section headings."""
    banned = ["Additional Activities"]
    for section in banned:
        pattern = r"^#{1,6}\s+" + re.escape(section)
        if re.search(pattern, draft, re.IGNORECASE | re.MULTILINE):
            result.fail(
                f"Banned section found — '## {section}' must not appear in the draft. "
                "Remove this section entirely before saving."
            )
        else:
            result.note(f"Banned section check OK — '{section}' not present.")


def check_resume_length(draft: str, config: dict, result: AuditResult) -> int:
    """Total body word count must not exceed config.resume_max_words."""
    max_words = config.get("resume_max_words", 950)
    wc = count_words(draft)
    result.note(f"Resume length — {wc} words (max {max_words}).")
    if wc > max_words:
        result.fail(
            f"Resume too long — {wc} words exceeds the {max_words}-word limit. "
            f"Remove approximately {wc - max_words} word(s): shorten bullets, "
            "reduce project count, or cut low-value lines."
        )
    return wc


def check_bullet_length(draft: str, config: dict, result: AuditResult):
    """No single bullet point may exceed config.bullet_max_words words."""
    max_words = config.get("bullet_max_words", 20)
    violations = []
    for i, line in enumerate(draft.splitlines(), start=1):
        stripped = line.strip()
        if stripped.startswith("- "):
            bullet_text = stripped[2:].strip()
            wc = len(bullet_text.split())
            if wc > max_words:
                violations.append((i, wc, bullet_text[:80] + ("..." if len(bullet_text) > 80 else "")))

    if violations:
        detail = "\n".join(
            f"  Line {ln}: {wc} words — \"{text}\""
            for ln, wc, text in violations[:8]
        )
        result.fail(
            f"Bullet length exceeded — {len(violations)} bullet(s) are over "
            f"{max_words} words. Each bullet must be a single punchy line. "
            f"Offending bullets:\n{detail}"
        )
    else:
        result.note(f"Bullet length OK — all bullets within {max_words} words.")


def check_creative_buffer(metadata: dict, draft_wc: int, result: AuditResult):
    """
    New content (not derived from the master) must not exceed 5% of total draft word count.
    The Architect self-reports new_word_count_estimate in metadata.
    """
    max_pct = metadata.get("config", {}).get("creative_buffer_max_pct", 5.0)
    buf = metadata.get("current_draft", {}).get("creative_buffer_used", {})
    new_wc = buf.get("new_word_count_estimate", 0)

    if not isinstance(new_wc, (int, float)):
        result.warn("creative_buffer_used.new_word_count_estimate is not a number — skipping.")
        return
    if draft_wc == 0:
        result.warn("Draft word count is zero — skipping creative buffer check.")
        return

    creative_pct = (new_wc / draft_wc) * 100
    result.note(
        f"Creative buffer — {new_wc} estimated new word(s) / {draft_wc} total "
        f"= {creative_pct:.1f}% (max {max_pct}%)."
    )

    if creative_pct > max_pct:
        excess = int(new_wc - (draft_wc * max_pct / 100))
        result.fail(
            f"Creative buffer exceeded — {creative_pct:.1f}% of the draft is new content "
            f"(max {max_pct}%). Remove or replace approximately {excess} word(s) of content "
            "not present in master_resume.md."
        )


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def build_report(result: AuditResult, iteration: int) -> dict:
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "iteration": iteration,
        "passed": result.passed,
        "errors": result.errors,
        "warnings": result.warnings,
        "info": result.info,
    }


def print_report(result: AuditResult, iteration: int):
    divider = "=" * 60
    # Use sys.stdout with utf-8 to handle any environment
    out = open(sys.stdout.fileno(), mode="w", encoding="utf-8", closefd=False, buffering=1)
    out.write(divider + "\n")
    out.write(f"  IRON AUDITOR -- Iteration {iteration}\n")
    out.write(divider + "\n")
    for line in result.info:
        out.write(f"  [OK] {line}\n")
    for line in result.warnings:
        out.write(f"  [!!] {line}\n")
    for line in result.errors:
        out.write(f"  [XX] {line}\n")
    out.write(divider + "\n")
    if result.passed:
        out.write("  BUILD PASSED -- Draft cleared all hard constraints.\n")
    else:
        out.write(
            f"  BUILD FAILED -- {len(result.errors)} error(s) detected. "
            "Return draft to Narrative Architect with the errors above.\n"
        )
    out.write(divider + "\n")
    out.flush()


def update_metadata(metadata_path: Path, report: dict, metadata: dict):
    metadata.setdefault("audit_log", []).append(report)
    metadata["current_draft"]["auditor_passed"] = report["passed"]
    metadata_path.write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8"
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Iron Auditor — deterministic hard-gate for the Resume CI/CD Pipeline."
    )
    parser.add_argument("--master", required=True, help="Path to master_resume.md")
    parser.add_argument("--draft", required=True, help="Path to the draft .md file to audit")
    parser.add_argument("--metadata", required=True, help="Path to metadata.json")
    args = parser.parse_args()

    master_path = Path(args.master)
    draft_path = Path(args.draft)
    metadata_path = Path(args.metadata)

    if not master_path.exists():
        print(f"Error: Master resume not found at '{master_path}'")
        sys.exit(1)
    if not draft_path.exists():
        print(f"Error: Draft file not found at '{draft_path}'")
        sys.exit(1)
    if not metadata_path.exists():
        print(f"Error: metadata.json not found at '{metadata_path}'")
        sys.exit(1)

    master_md = load_md(master_path)
    draft_md = load_md(draft_path)
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

    locked = metadata.get("locked_fields", {})
    config = metadata.get("config", {})
    iteration = metadata.get("current_state", {}).get("iteration", 0)

    result = AuditResult()

    check_name_lock(draft_md, locked, result)
    check_education_lock(draft_md, locked, result)
    check_experience_title_lock(draft_md, locked, result)
    check_project_integrity(draft_md, master_md, locked, result)
    check_no_banned_sections(draft_md, result)
    draft_wc = check_resume_length(draft_md, config, result)
    check_bullet_length(draft_md, config, result)
    check_creative_buffer(metadata, draft_wc, result)

    print_report(result, iteration)
    report = build_report(result, iteration)
    update_metadata(metadata_path, report, metadata)

    sys.exit(0 if result.passed else 1)


if __name__ == "__main__":
    main()

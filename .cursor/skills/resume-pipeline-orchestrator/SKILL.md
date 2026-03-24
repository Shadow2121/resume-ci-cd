---
name: resume-pipeline-orchestrator
description: Runs the full Resume CI/CD Pipeline — a 6-agent autonomous loop that tailors master_resume.md to a specific job description, enforces hard constraints via a deterministic auditor, humanizes language, gates output through a 5-persona committee, and generates a cover letter. Use when the user says "run the pipeline", "tailor my resume", "start the resume pipeline", or provides a job description to target.
---

# Resume CI/CD Pipeline — Orchestrator

You are the master controller of a 6-agent resume tailoring pipeline. Your job is to coordinate each agent skill in sequence, manage state in `metadata.json`, enforce iteration limits, and produce final versioned output.

## Pre-flight checks

Before starting, verify all required files exist:
- `master_resume.md` — source of truth
- `job_description.txt` — must contain an actual JD (not the placeholder)
- `metadata.json` — state file
- `humanizer_rules.txt` — banned phrase list
- `scripts/auditor.py` — deterministic gate

If `job_description.txt` still contains `[PASTE JOB DESCRIPTION HERE]`, stop and tell the user to add the JD first.

## State reset — MANDATORY first action

**Always** run the reset script before doing anything else, regardless of `metadata.json`'s current state. This archives the previous run's output files and wipes all runtime state, leaving `locked_fields`, `master_resume`, and `config` intact.

```bash
python scripts/reset_pipeline.py
```

If the user wants to target a different `job_description.txt` path, pass it:
```bash
python scripts/reset_pipeline.py --jd path/to/new_jd.txt
```

Wait for the script to print `RESET COMPLETE` before continuing.

**Why this is mandatory**: If `metadata.json` has `"status": "completed"` from a previous run, its `audit_log`, `committee_history`, and `rejected_content` are stale. The Narrative Architect will try to fix errors that belonged to the old JD. The reset script solves this by giving every run a clean slate.

After reset, read `config.max_iterations` (default: 5) and `config.committee_pass_threshold` (default: 9.0) from `metadata.json`.

## Pipeline execution

### Step 1 — Corporate Scout
Apply the `corporate-scout` skill. Pass it the content of `job_description.txt`. It will update `metadata.json` with extracted intelligence. Confirm the scout data is written before continuing.

### Step 2 — Main iteration loop

Run this loop until committee passes OR `max_iterations` is reached:

```
LOOP (iteration = 1 to max_iterations):

  a. Narrative Architect  [two-phase: Coverage Map → Draft]
     Apply the `narrative-architect` skill.
     The skill will internally run Phase 1 (Coverage Map) before Phase 2 (Draft).
     Phase 1 output: metadata.jd_blueprint — a structured mapping of every JD requirement
       and keyword to a specific location in the planned draft. Wait for this to be saved
       before the draft file is written.
     Phase 2 output: draft .md file saved as output/draft_iter{N:02d}.md
     Pass context: master_resume.md + metadata.json
       — scout data (pain points, keywords, latent requirements)
       — any previous auditor errors (metadata.audit_log[last].errors)
       — any previous Red Team mandatory fixes (metadata.current_draft.red_team_mandatory_fixes)
       — any previous Committee mandatory fixes (metadata.committee_history[last])
       — previous jd_blueprint (if iteration > 1, so architect can see what changed)
     Update metadata.json: current_state.iteration = N

  b. Iron Auditor  [Gate 1 — hard structural constraints]
     Apply the `iron-auditor` skill.
     Pass: path to the draft just created
     If FAILED → log errors to metadata.json.audit_log, continue loop (do NOT run humanizer/red-team/committee)
     If PASSED → continue to step c

  c. Humanizer
     Apply the `humanizer` skill.
     Pass: the auditor-passed draft
     Output: output/humanized_iter{N:02d}.md
     Update metadata.json: current_draft.humanizer_applied = true

  d. Red Team Critic  [Gate 2 — harsh quality pre-screen]
     Apply the `red-team-critic` skill.
     Pass: the humanized draft + metadata.json (keywords, pain points, latent requirements)
     If FAILED (average < 7.5 OR any axis < 6.0):
       → log red_team_mandatory_fixes to metadata.json.current_draft
       → log red_team_scores to metadata.json.current_draft
       → continue loop (do NOT run committee)
       → Narrative Architect MUST address every red_team_mandatory_fix in the next iteration
     If PASSED → continue to step e

  e. Committee  [Gate 3 — final approval]
     Apply the `resume-committee` skill.
     Pass: the humanized draft + job_description.txt content
     Read the average score from metadata.json after the skill completes.
     If average >= 9.0 → LOOP EXITS (pipeline succeeds)
     If average < 9.0  → log committee feedback to metadata.json, continue loop

  Log the full iteration result to metadata.json.iterations[].
END LOOP
```

### Step 3 — Select final draft
- If loop exited with passing score: use the latest humanized draft.
- If max_iterations reached without passing: use the draft with the highest `committee_average` from `metadata.json.iterations`.
- Save final resume as `output/resume_final_{timestamp}_score{avg}.md`

### Step 4 — Ghostwriter
Apply the `ghostwriter` skill. Pass it the final resume + scout data from `metadata.json`. Save output as `output/cover_letter_{timestamp}.txt`.

### Step 5 — LaTeX Formatter
Apply the `latex-formatter` skill. Pass it the final Markdown resume path (`metadata.final_output.resume_file`) and `metadata.json` (for project/company URLs). It will produce a print-ready `.tex` file using `sample_template.tex` as the layout reference.
Save output as `output/resume_final_{timestamp}.tex` — same timestamp as the Markdown file.

### Step 6 — Audit report
Generate a final audit report and save as `output/audit_report_{timestamp}.txt`. See report format in [audit-report-format.md](audit-report-format.md).

## Completion

Update `metadata.json`:
```json
{
  "current_state": { "status": "completed" },
  "final_output": {
    "resume_file": "...",
    "latex_file": "...",
    "cover_letter_file": "...",
    "audit_report_file": "...",
    "final_average_score": ...,
    "total_iterations": ...,
    "completed_at": "<ISO timestamp>"
  }
}
```

Print a summary showing: final score, iteration count, output file names (Markdown + LaTeX + cover letter).

## Error handling

- If any skill fails with an unrecoverable error, set `metadata.json.current_state.status = "failed"` and log the error.
- Never silently skip a step.
- If the auditor fails 3 consecutive times with the same error, escalate to the user with a specific question.

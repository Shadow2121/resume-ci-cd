# Resume CI/CD Pipeline

An autonomous, multi-agent resume tailoring system built entirely on **Cursor AI Skills**. Drop in a job description, run the pipeline, get a tailored, ATS-optimised, print-ready resume — with a cover letter and a LaTeX file — without touching the content yourself.

---

## How it works

The pipeline runs eight specialised agents in sequence. Each agent is a `SKILL.md` file that the Cursor AI reads and executes. A deterministic Python auditor acts as a hard gate between drafting and evaluation. The loop runs until the resume passes all constraints and scores ≥ 9.0/10 from a five-persona committee — or until the iteration limit is reached.

```
job_description.txt
        │
        ▼
┌─────────────────────┐
│   Corporate Scout   │  Analyses the JD: pain points, keywords, latent requirements
└─────────┬───────────┘
          │  scout data written to metadata.json
          ▼
┌──────────────────────────────────────────────────────────┐
│              Narrative Architect                         │
│  Phase 1 ─ Coverage Map                                  │
│    Maps every JD requirement → closest master resume line│
│    Maps every keyword → planned placement in draft       │
│    Saves jd_blueprint to metadata.json                   │
│  Phase 2 ─ Draft                                         │
│    Writes draft using the Coverage Map as blueprint      │
└─────────┬────────────────────────────────────────────────┘
          │  output/draft_iterNN.md
          ▼
┌─────────────────────┐
│    Iron Auditor     │  8 hard constraint checks (Python, deterministic)
└─────────┬───────────┘
     FAIL │ ──────────────────────────────────────┐
          │ PASS                                  │
          ▼                                       │
┌─────────────────────┐                           │
│     Humanizer       │  Replaces AI-smell words  │
└─────────┬───────────┘  per humanizer_rules.txt  │
          │  output/humanized_iterNN.md            │
          ▼                                       │
┌─────────────────────┐                           │
│  Red Team Critic    │  Harsh 6-axis pre-screen  │
│  threshold: 7.5/10  │  (7-page rubric)          │
└─────────┬───────────┘                           │
     FAIL │ ──────────────────────────────────────┤
          │ PASS                                  │
          ▼                                       │
┌─────────────────────┐                           │
│  Resume Committee   │  5 personas, each 0–10    │
│  threshold: 9.0/10  │  ATS Bot, Tech Lead, CTO, │
│                     │  HR Screener, Recruiter   │
└─────────┬───────────┘                           │
  avg < 9 │ ──────────────────────────────────────┘
          │ avg ≥ 9.0                    (loop repeats, max 6 iterations)
          ▼
┌─────────────────────┐
│    Ghostwriter      │  Generates a targeted cover letter
└─────────┬───────────┘
          ▼
┌─────────────────────┐
│   LaTeX Formatter   │  Converts final Markdown → .tex using your template
└─────────┬───────────┘
          ▼
   output/
   ├── resume_final_{date}_score{N}.md
   ├── resume_final_{date}_score{N}.tex   ← print-ready
   ├── cover_letter_{date}.txt
   └── audit_report_{date}.txt
```

---

## Agents

| # | Agent | Role |
|---|---|---|
| 1 | **Corporate Scout** | Reads the JD and extracts structured intelligence: core pain points, latent requirements, ATS keywords, company context. Writes to `metadata.json`. |
| 2 | **Narrative Architect** | Two-phase: (1) builds a Coverage Map that explicitly maps every JD requirement and keyword to a master resume line before writing; (2) drafts the resume using the map as a blueprint. |
| 3 | **Iron Auditor** | Runs `scripts/auditor.py` — a deterministic Python script that enforces 8 hard constraints. Either passes or returns specific error messages to the Architect. |
| 4 | **Humanizer** | Replaces every banned "AI-smell" word/phrase in `humanizer_rules.txt` with direct, engineering-first language. |
| 4.5 | **Red Team Critic** | Harsh pre-screen (7.5/10 threshold). Scores 6 axes: JD Mirror, Keyword Coverage (with blueprint cross-check), Evidence Coverage, Metric Quality, Relevance Rate, Differentiation. Returns `mandatory_fix` items that force another iteration. |
| 5 | **Resume Committee** | Five-persona panel (9.0/10 threshold). Each persona scores independently using detailed rubrics. ATS Bot checks keyword coverage and bullet/resume length; HR Screener checks skimmability and AI-smell; Tech Lead checks engineering depth; CTO checks business impact; Technical Recruiter checks differentiation. |
| 6 | **Ghostwriter** | Writes a company-specific cover letter using the Scout's intelligence and the final resume. References the company's specific technical challenges. |
| 7 | **LaTeX Formatter** | Translates the approved Markdown resume into a `.tex` file using a personal template. Handles all LaTeX escaping, preserves GitHub/company hyperlinks from `metadata.json`, keeps fixed blocks (header, education) identical to the template. |

---

## Hard constraints (Iron Auditor)

These are enforced deterministically by `scripts/auditor.py`. A single violation fails the build and sends the resume back to the Narrative Architect with an exact error message.

| # | Constraint | What it checks |
|---|---|---|
| 1 | **Name lock** | Candidate name must appear verbatim |
| 2 | **Education lock** | Institution and degree must appear verbatim |
| 3 | **Experience title lock** | All job titles from `locked_fields.experience_titles` must appear verbatim — titles cannot be renamed to fit the JD |
| 4 | **Project integrity** | Every `###` project heading in the draft must exist in `locked_fields.project_titles` — new projects cannot be invented |
| 5 | **Banned sections** | `## Additional Activities` must not appear in the draft |
| 6 | **Resume length** | Total body word count ≤ `config.resume_max_words` (default: 950) |
| 7 | **Bullet length** | No single bullet point may exceed `config.bullet_max_words` (default: 20) words |
| 8 | **Creative buffer** | New content not present in the master resume must not exceed `config.creative_buffer_max_pct` (default: 10%) of the total draft word count |

All locked values are read dynamically from `metadata.json` at runtime — changing `metadata.json` is enough to update any constraint.

---

## Project structure

```
resume-pipeline/
│
├── .cursor/
│   └── skills/
│       ├── corporate-scout/SKILL.md
│       ├── narrative-architect/
│       │   ├── SKILL.md
│       │   └── rewriting-examples.md
│       ├── iron-auditor/SKILL.md
│       ├── humanizer/SKILL.md
│       ├── red-team-critic/SKILL.md
│       ├── resume-committee/
│       │   ├── SKILL.md
│       │   └── persona-details.md
│       ├── ghostwriter/SKILL.md
│       ├── latex-formatter/SKILL.md
│       └── resume-pipeline-orchestrator/
│           ├── SKILL.md
│           └── audit-report-format.md
│
├── scripts/
│   ├── auditor.py          # Deterministic constraint checker (Python)
│   └── reset_pipeline.py  # Resets metadata.json for a new run, archives output
│
├── output/                 # Generated per-run (gitignored)
│   └── runs/               # Archived previous runs
│
├── metadata.json           # Pipeline state + config + locked fields
├── humanizer_rules.txt     # Banned AI-smell words with replacements
├── requirements.txt
├── .gitignore
│
│ # --- Personal files (gitignored, you provide these) ---
├── master_resume.md        # Your source-of-truth resume in Markdown
├── sample_template.tex     # Your LaTeX template for the formatter
└── job_description.txt     # The JD for the current run
```

---

## Setup

### Prerequisites

- [Cursor](https://cursor.com) with an active AI subscription
- Python 3.10+

### 1. Clone the repo

```bash
git clone https://github.com/YOUR_USERNAME/resume-pipeline.git
cd resume-pipeline
```

### 2. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 3. Add your personal files (not committed)

Create these three files in the workspace root — they are gitignored and never committed:

**`master_resume.md`** — your full resume in Markdown. This is the source of truth. Structure it with these sections:

```markdown
# Your Name
contact info

## Professional Summary
...

## Education
...

## Professional Experience
### Job Title
**Company** | Location | Dates
- bullet

## Skills
**Category:** item1, item2

## Projects
### Project Name
*Tech stack*
- bullet
```

**`sample_template.tex`** — your LaTeX resume template. The LaTeX Formatter uses this for all fixed layout elements (preamble, margins, header, education, font sizes). Only the content sections are replaced.

**`job_description.txt`** — paste the full text of the job posting you are targeting.

### 4. Update `metadata.json` with your locked fields

Open `metadata.json` and update `locked_fields` with your actual data:

```json
{
  "locked_fields": {
    "name": "Your Name",
    "education": {
      "institution": "Your University",
      "degree": "Your Degree"
    },
    "experience_titles": [
      "Exact Job Title As It Appears In Your Resume"
    ],
    "project_titles": [
      "Exact Project Name As It Appears In Your Resume"
    ],
    "project_urls": {
      "Exact Project Name": "https://github.com/..."
    },
    "company_urls": {
      "Company Name": "https://company.com"
    }
  }
}
```

---

## Running the pipeline

### Start a new run

Open Cursor, open the chat panel, and say:

> **Run the resume pipeline**

The orchestrator skill picks this up and executes all agents in sequence. It will:
1. Reset the pipeline state automatically (first action)
2. Run all 8 agents
3. Print progress after each phase
4. Save final outputs to `output/`

### Start a run for a different job description

Update `job_description.txt` with the new JD, then:

```bash
python scripts/reset_pipeline.py
```

This archives the previous run's output to `output/runs/<timestamp>_<Company>_<Role>/` and wipes the runtime state in `metadata.json`. Then run the pipeline as normal.

Or pass a different JD file path:

```bash
python scripts/reset_pipeline.py --jd path/to/new_job_description.txt
```

### Outputs

After a successful run, `output/` contains:

| File | Description |
|---|---|
| `resume_final_{date}_score{N}.md` | Final tailored resume in Markdown |
| `resume_final_{date}_score{N}.tex` | Same resume in LaTeX, ready to compile |
| `cover_letter_{date}.txt` | Company-specific cover letter |
| `audit_report_{date}.txt` | Full audit: Red Team scores, Committee scores, keyword coverage, iteration history, creative buffer summary |

To compile the `.tex` to PDF:
```bash
pdflatex output/resume_final_{date}_score{N}.tex
```

---

## Configuration

All tunable parameters live in `metadata.json` under `config`. They persist across resets.

| Key | Default | Description |
|---|---|---|
| `max_iterations` | `6` | Maximum loop iterations before the best draft is taken |
| `committee_pass_threshold` | `9.0` | Minimum committee average score to exit the loop |
| `creative_buffer_max_pct` | `10.0` | Max % of draft that can be content not in the master resume |
| `resume_max_words` | `950` | Hard word count cap for the entire resume body |
| `bullet_max_words` | `20` | Hard word cap per bullet point |
| `metric_range.min_pct` | `10` | Minimum quantified metric injected into bullets |
| `metric_range.max_pct` | `25` | Maximum quantified metric injected into bullets |

Example — to allow a slightly longer resume:
```json
"resume_max_words": 1050
```

---

## Customising the humanizer

`humanizer_rules.txt` controls which words get replaced. Format:

```
banned_word -> replacement
# This is a comment
```

Add your own entries. The Humanizer agent replaces all occurrences case-insensitively before the resume reaches the Committee.

---

## How the Coverage Map works

Before writing a single word of the draft, the Narrative Architect runs a mandatory pre-writing phase:

1. **Requirement mapping** — For every JD pain point and latent requirement, finds the closest line in the master resume and labels match strength (`strong` / `partial` / `gap`).
2. **Keyword placement** — For every extracted keyword, decides exactly which section and bullet it will appear in, and whether it comes from the master resume or the creative buffer.
3. **Gap decisions** — For requirements with no strong match, decides whether the creative buffer can fill the gap honestly or whether to leave it uncovered rather than fabricate.

This map is saved to `metadata.jd_blueprint` before writing starts. The Red Team then cross-checks: "You planned to put keyword X in bullet Y — is it actually there?" This closes the loop between planning and execution.

---

## Architecture notes

**Why Cursor Skills instead of a Python orchestrator?**

Every agent in this pipeline is a `SKILL.md` file — a plain-text instruction set for the Cursor AI. The AI itself is the runtime. This means:
- No API keys to manage
- No rate limiting to handle
- The LLM that drafts the resume is the same one reading the constraints — no translation layer
- Skills can be edited like documentation and take effect immediately

**Why a deterministic Python auditor?**

The Iron Auditor (`scripts/auditor.py`) does not use an LLM. It reads `metadata.json` and the draft file and performs exact string matching. This means:
- Name/education/title locks are truly unbreakable — an LLM cannot negotiate its way around them
- Word counts are arithmetic, not estimates
- The auditor gives exact error messages ("remove approximately 45 words") rather than qualitative feedback

**Why two quality gates (Red Team + Committee)?**

The Red Team Critic scores harshly (threshold 7.5) from an adversarial mindset — actively looking for reasons to reject. It catches issues before the Committee sees the draft, so by the time the Committee evaluates, the obvious weaknesses are already fixed. The Committee's job is final validation of tone, positioning, and fit — not catching basic errors.

---

## Gitignore summary

| Ignored | Reason |
|---|---|
| `master_resume.md` | Personal — contains your full work history |
| `sample_template.tex` | Personal — your resume template |
| `job_description.txt` | Changes every run, not part of the tool |
| `output/` | Generated files, not source code |
| `__pycache__/`, `.venv/` | Python build artifacts |

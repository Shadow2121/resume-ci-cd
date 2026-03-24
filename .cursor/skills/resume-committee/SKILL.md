---
name: resume-committee
description: Agent 5 of the Resume CI/CD Pipeline. Runs a 5-persona consensus evaluation of a resume draft against a job description. Each persona (ATS Bot, Tech Lead, CTO, HR Screener, Technical Recruiter) independently scores the draft 1-10 with specific critiques. The pipeline passes only if the average score is >= 9.0. Logs all scores and mandatory fixes to metadata.json. Use when the orchestrator invokes the committee phase, or when the user says "evaluate the resume", "score the draft", or "run the committee".
---

# Resume Committee

You run a structured multi-persona evaluation. You will evaluate the resume **5 separate times**, each time adopting a different evaluator's mindset completely. Do not blend personas. Do not let one persona's view bleed into another's.

## Inputs

Read:
- The humanized draft from `metadata.current_draft.file`
- The JD from `job_description.txt`
- Previous committee feedback from `metadata.committee_history` (to avoid repeating the same critiques)

## The 5 personas

For each persona below, read [persona-details.md](persona-details.md) for their full scoring rubric. Evaluate independently.

| Persona | Focus | Pass condition |
|---------|-------|---------------|
| **ATS Bot** | Keyword match rate, section headers, specificity | >85% keyword coverage |
| **Tech Lead** | Technical depth, metrics plausibility, scale signals, ownership language | Demonstrates engineering judgment |
| **CTO** | Business impact, trajectory, strategic fit with JD, no red flags | Clear ROI on the hire |
| **HR Screener** | Readability, format, zero AI-smell, tone, credential check | 6-second skim passes |
| **Technical Recruiter** | Positioning clarity, JD alignment, differentiators, level fit | Easy to pitch to hiring manager |

## Evaluation process

For each persona, produce a score card:

```
=== [PERSONA NAME] ===
Score: X/10
Verdict: pass | fail
Top Strengths:
  1. ...
  2. ...
Critical Gaps:
  1. ...
  2. ...
Mandatory Fix: <one specific, actionable rewrite instruction — or "none">
```

Output all 5 score cards in sequence, then the aggregate:

```
=== COMMITTEE AGGREGATE ===
ATS Bot:             X/10
Tech Lead:           X/10
CTO:                 X/10
HR Screener:         X/10
Technical Recruiter: X/10
─────────────────────────
AVERAGE:             X.X/10
RESULT:              PASS | FAIL (threshold: 9.0)
```

## Update metadata.json

Append to `metadata.committee_history[]`:

```json
{
  "iteration": <N>,
  "timestamp": "<ISO 8601>",
  "scores": [
    {
      "persona": "ats_bot",
      "persona_name": "ATS Bot",
      "score": 8,
      "verdict": "fail",
      "top_strengths": ["..."],
      "critical_gaps": ["..."],
      "mandatory_fix": "Add 'Apache Airflow' to skills section — mentioned 3 times in JD but absent from resume."
    }
  ],
  "average": 8.4,
  "passed": false
}
```

Also add all non-null `mandatory_fix` values to `metadata.rejected_content` to prevent the Architect from ignoring them across iterations.

Update `metadata.current_draft.committee_scores` and `metadata.current_draft.committee_average`.

## Pass/fail decision

- **PASS**: average >= 9.0 → report "Committee: PASSED ({avg}/10). Proceeding to Ghostwriter."
- **FAIL**: average < 9.0 → report "Committee: FAILED ({avg}/10). Mandatory fixes for Architect:" followed by the numbered list of all non-null mandatory_fix values.

## Scoring discipline

- Score honestly. A 9 means "I would move this candidate to the next round without hesitation." An 8 means "good but something is missing."
- Do not inflate scores to make the pipeline converge faster. A false pass is worse than a failed iteration.
- If a previous iteration already addressed a critique from `metadata.committee_history`, do not repeat it as a gap — acknowledge the fix and evaluate fresh.

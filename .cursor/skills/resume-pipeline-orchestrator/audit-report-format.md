# Audit Report Format

Generate a plain-text report with this structure:

```
=================================================================
  RESUME CI/CD PIPELINE — FINAL AUDIT & EVALUATION REPORT
=================================================================
  Candidate       : Mihir Patel
  Target Role     : {role from metadata.job_description.role}
  Company         : {metadata.job_description.company}
  Total Iterations: {N}
  Final Score     : {avg}/10
  Completed       : {timestamp}
=================================================================

CREATIVE BUFFER SUMMARY
------------------------------------
  New content estimate : {N} words
  As % of draft        : {X.X%} (max 5%)
  Description          : {metadata.current_draft.creative_buffer_used.description}

HUMANIZER CHANGES
------------------------------------
  Total replacements: {N}
  '{banned}' -> '{replacement}' ({count}x)   [one line per replacement]
  (or "No replacements made" if none)

RED TEAM CRITIC (final iteration)
------------------------------------
  [pass/fail] JD Mirror          : {score}/10
  [pass/fail] Keyword Coverage   : {score}/10  ({found}/{total} keywords)
  [pass/fail] Evidence Coverage  : {score}/10
  [pass/fail] Metric Quality     : {score}/10
  [pass/fail] Relevance Rate     : {score}/10
  [pass/fail] Differentiation    : {score}/10
             AVERAGE             : {avg}/10  (threshold: 7.5)

COMMITTEE FINAL SCORES
------------------------------------
  [pass/fail] ATS Bot            : {score}/10
  [pass/fail] Tech Lead          : {score}/10
  [pass/fail] CTO                : {score}/10
  [pass/fail] HR Screener        : {score}/10
  [pass/fail] Technical Recruiter: {score}/10
             AVERAGE             : {avg}/10  (threshold: 9.0)

KEYWORDS TARGETED
------------------------------------
  Found  ({N}): {keyword 1}, {keyword 2}, ...
  Missing ({N}): {keyword A}, {keyword B}, ...   (or "none" if full coverage)

PROJECTS INCLUDED
------------------------------------
  - {project name}   [one line per project included in the final draft]

ITERATION HISTORY
------------------------------------
  Iter N: Auditor {PASS/FAIL}, Red Team {avg}/10 ({PASS/FAIL}), Committee {avg}/10 ({PASS/FAIL})
  ...

=================================================================
  END OF REPORT
=================================================================
```

---
name: humanizer
description: Agent 4 of the Resume CI/CD Pipeline. Replaces all AI-smell words and corporate-speak phrases in a draft resume with direct, engineering-first language, using the rules defined in humanizer_rules.txt. Saves a cleaned version and logs all replacements to metadata.json. Use when the orchestrator invokes the humanizer phase, or when the user says "remove AI words", "humanize the resume", "clean up the language", or "remove corporate speak".
---

# Humanizer

You eliminate language that screams "AI wrote this." You replace every banned phrase in `humanizer_rules.txt` with direct, low-ego engineering language.

## Step 1 — Read the rules

Read `humanizer_rules.txt`. Parse every non-comment line in this format:
```
BANNED_PHRASE -> REPLACEMENT
```
Build a replacement map. Lines starting with `#` are comments — skip them.

## Step 2 — Read the draft

Read the draft file path from `metadata.current_draft.file`.

## Step 3 — Apply replacements

For each rule in the map:
- Do a **case-insensitive** search through the draft
- Replace every occurrence with the replacement
- The replacement must fit grammatically — if a banned word appears mid-sentence in a way that makes the replacement grammatically wrong, rephrase the minimal surrounding context to fix it
- Track each replacement: `{ "banned": "...", "replacement": "...", "count": N }`

**Important — Markdown safety**: Do not replace text inside Markdown link syntax `[text](url)` if doing so would corrupt the URL. Replace text only in visible body text (bullet content, headings, skill descriptions).

## Step 4 — Secondary scan (catch edge cases)

After the automated replacements, do a manual scan for:
- Any remaining superlatives: "best", "world-class", "cutting-edge" in body text
- Passive ownership: "was part of", "involved in", "helped with"
- Filler openers: "Successfully", "Effectively", "Efficiently" at the start of bullets

Fix any you find.

## Step 5 — Save output

Save the cleaned draft as `output/humanized_iter{N:02d}.md` where N is `metadata.current_state.iteration`.

## Step 6 — Update metadata.json

```json
{
  "current_draft": {
    "file": "output/humanized_iter{N:02d}.md",
    "humanizer_applied": true
  },
  "humanizer_replacements": [
    { "banned": "spearheaded", "replacement": "Led", "count": 2 },
    ...
  ]
}
```

## Step 7 — Report

Report:
- Total replacements made
- Which rules fired (list banned → replacement with count)
- If zero replacements: confirm "No banned phrases found — draft already clean."

## Quality check

After replacements, spot-check 5 random bullets. They should sound like a senior engineer wrote them in plain speech — no MBA jargon, no AI tells, no ego. If a bullet still sounds like it came from a LinkedIn influencer, rewrite it directly.

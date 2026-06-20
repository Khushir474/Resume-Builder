---
name: resume-builder
description: Tailors Khushi Ranganatha's resume to a specific job description. Detects role type, selects experience entries, runs a 2-step ATS workflow, compiles a PDF, and saves tracking data to the Obsidian vault and CSV. Use when Khushi pastes a JD, passes a vault JD file path, or says "tailor my resume", "customize for this job", "update resume for [role/company]", "rebuild my resume", or "apply to [company]".
---

# Resume Builder — Orchestrator

## Configuration

```
V1 tracker path:  ~/JobSearch/tracker.csv
V2 vault path:    ~/JobSearch/
```

---

## Mode Detection

Determine mode from the skill argument before doing anything else:

| Argument | Mode |
|---|---|
| Path to an existing `.md` file | **V2** — read JD text from that file |
| Raw pasted text | **V1** — standard flow |
| No argument, vault exists | Ask: "Use most recently modified file in `JDs/`? [Yes / Paste instead]" |
| `--compile [RoleType]` | **Compile mode** — skip to `--compile Mode` section below |

---

## Step 0 — Archetype Check (V2 only)

*Skip if V1 mode.*

After classifying role type in Step 1, check if `~/JobSearch/Archetypes/[RoleType]_summary.md` exists.

- **Found:** Load it. Report: "Loading [RoleType] archetype (compiled [date], N=[count] applications) — skipping raw experience file loading." Skip Step 2.
- **Not found:** Continue to Step 2 as normal.

---

## Step 1 — Role Type Classification

Read the JD. Classify into one of four types:

| Type | Core Emphasis |
|---|---|
| **AI/ML Engineer** | Production systems — inference pipelines, model deployment, MLOps, LLMOps, scale, latency |
| **Data Scientist** | Statistical modeling — experiments, feature engineering, ML model development, predictive accuracy |
| **Data Analyst** | SQL-driven analysis and reporting — dashboards, KPIs, business intelligence, stakeholder communication |
| **Product Analyst / Ops** | Cross-functional execution — PDLC, GTM, roadmaps, sprint coordination, delivery operations |

State classification with a one-line rationale, then use **AskUserQuestion**:
- Question: `"This reads like a [TYPE] role — [one-line rationale]. Which type should I use?"`
- Option 1 (recommended): `"Yes, [Classified Type]"`
- Options 2–4: the other three types in order

Role prompt files:
- AI/ML Engineer → `~/.claude/skills/resume-builder/roles/ai_ml_engineer.md`
- Data Scientist → `~/.claude/skills/resume-builder/roles/data_scientist.md`
- Data Analyst → `~/.claude/skills/resume-builder/roles/data_analyst.md`
- Product Analyst / Ops → `~/.claude/skills/resume-builder/roles/product_analyst_ops.md`

---

## Step 1.5 — Delta Keywords (V2 only, if archetype loaded)

*Skip if V1 or no archetype.*

- Pre-populate List A and B from the archetype's `### Top Required Skills` and `### Common Soft Keywords`.
- Extract only keywords from this JD **not** in `known_keywords` — these are the delta.
- At Gate 2: present archetype-sourced keywords as pre-accepted, show only delta for review.
- Flag: "Pre-loaded [N] keywords from [RoleType] archetype. New keywords in this JD: [M]"

---

## Step 2 — Selective Experience Loading

*Skip if an archetype was loaded in Step 0.*

**Always load iTradeNetwork, LiA, and Digitas — required for every resume.** Load 1 optional 4th file based on JD domain fit.

| JD Domain | Optional 4th entry |
|---|---|
| LLM / RAG / agentic AI | LexLead.ai |
| MLOps / production ML | LexLead.ai |
| NLP / text processing | TEKSystems |
| Product / GTM / ops | Galaara |
| Data science / modeling | LexLead.ai |
| Customer analytics / marketing | Galaara |
| SQL / dashboards / BI | skip — core three sufficient |

**Session reuse:** If files are already loaded from a prior run this session, do not re-read. State: "Reusing experience context — only the JD has changed." Proceed to role prompt Step 1.

Experience files:
```
~/.claude/skills/resume-builder/experience/itradenetwork.md   ← always load
~/.claude/skills/resume-builder/experience/lia.md             ← always load
~/.claude/skills/resume-builder/experience/digitas.md         ← always load
~/.claude/skills/resume-builder/experience/lexlead_ai.md
~/.claude/skills/resume-builder/experience/galaara.md
~/.claude/skills/resume-builder/experience/teksystems.md
```

---

## Step 3 — Run the Role Prompt (2-Step Workflow)

Read the matching role file.

**Step 1 of role prompt:** Extract keyword lists (List A: hard keywords, List B: soft keywords, List C if applicable). Output the lists. If the JD names no specific tools in List A, fill in widely-adopted tools for that role type in the 2026 market — flag inferred tools clearly. Then use **AskUserQuestion**:
- Question: `"Do you want to adjust the keyword lists before I write?"`
- Option 1 (recommended): `"Looks good — write the resume"`
- Options 2–4: Add / Remove / Add and remove (user types changes in notes field)

**Step 2 of role prompt:** Write the full tailored resume using role file ATS rules, extrapolation guidance, writing style, and format. Draw bullets from loaded experience entries (or archetype) and match JD language exactly.

**TERMINAL OUTPUT RULE — strictly enforced:**
Do NOT print resume content. After composing internally, output ONLY:
1. The `EXTRAPOLATED — PREP BEFORE INTERVIEW` table
2. Proceed immediately to Step 4 — no gate.

---

## Step 4 — Build PDF (Automatic)

No confirmation required. Build immediately after Step 3.

1. **Never modify `latex/template.tex`.** Write the tailored resume to `~/.claude/skills/resume-builder/latex/output.tex` only.
2. Run the build script — it compiles, moves, and prints the final path:

```bash
~/.claude/skills/resume-builder/latex/build.sh [Company] [RoleType] [V1|V2]
```

- `[Company]` — company name, no spaces (e.g. `Fora`, `BookOfTheMonth`, `Taktile`, `Unknown`)
- `[RoleType]` — shortcode: `DataAnalyst`, `DataScientist`, `AIMLEngineer`, `ProductAnalyst`
- `[V1|V2]` — `V2` saves to vault Resumes folder; `V1` saves to Career/Resume/resume-builder-outputs

3. Output only the path printed by the script — no resume content.

---

## Step 5 — Save Tracking Data

Runs unconditionally after Step 3 (regardless of PDF).

### V1 — Append to CSV

Append one row to `~/JobSearch/tracker.csv`. If the file doesn't exist, create it with header:
```
date,company,role,type,status,keywords_a,keywords_b,prep_notes
```

Row format:
```
[YYYY-MM-DD],[Company or "Unknown"],[Job Title],[RoleType],Researching,[List A pipe-separated],[List B pipe-separated],[flattened prep notes]
```

Flatten EXTRAPOLATED table into `prep_notes`: for each row write `[addition]→[outcome] ASSUMES: [assumption]`, join with ` | `.

Output: `"Saved → tracker.csv"`

### V2 — Write Application Note

Write `~/JobSearch/Applications/[Company]_[RoleType]_[YYYYMMDD].md`:

```markdown
---
company: [Company or "Unknown"]
role: [Job Title]
type: [DataAnalyst | DataScientist | AIMLEngineer | ProductAnalyst]
date: [YYYY-MM-DD]
status: Researching
keywords_a: [List A pipe-separated]
keywords_b: [List B pipe-separated]
jd_note: "[[JDs/[source filename if V2, else blank]]]"
resume: "[[Resumes/[PDF filename if built, else blank]]]"
---

# [Company] — [Role]
**Date:** [YYYY-MM-DD]

## Keywords
**Hard (List A):** [comma-separated]
**Soft (List B):** [comma-separated]

## Interview Prep

[EXTRAPOLATED table, full format]
```

Output: `"Saved → Applications/[filename].md"`

---

## --compile Mode

Triggered by: `/resume-builder --compile [RoleType]`
Valid values: `DataAnalyst`, `DataScientist`, `AIMLEngineer`, `ProductAnalyst`
Requires V2 vault.

1. Read all `.md` files in `~/JobSearch/Applications/` where `type:` matches `[RoleType]`
2. For each note: collect `keywords_a`, `keywords_b`; load linked `jd_note` if it exists
3. Tally keyword frequencies across all N notes
4. Compare all unique `keywords_a` against `~/.claude/skills/resume-builder/experience/*.md` — flag terms in 5+ JDs absent from all experience files
5. Write `~/JobSearch/Archetypes/[RoleType]_summary.md`:

```markdown
## [RoleType] Archetype — compiled [YYYY-MM-DD] (N=[count] applications)

### known_keywords
[all unique keywords_a across N applications, pipe-separated]

### Top Required Skills (JD frequency)
[top 15 keywords_a with count, sorted descending]

### Common Soft Keywords
[top 8 keywords_b with count]

### JD Language Patterns
[2–4 observations about recurring phrases in linked JD notes]

### Experience File Priority
[rank experience files by keyword overlap — replaces static relevance map for future V2 runs]

### Skill Gap — Missing from Your Experience Files
Skills in 5+ JDs not in any experience entry:
- [term] ([count]/N)
...
Upskilling priority: [ranked list, highest-frequency gap first]
```

Output: `"Archetype written → Archetypes/[RoleType]_summary.md ([N] applications analyzed)"`

---

## Reference Files

| File | Purpose |
|---|---|
| `roles/*.md` | Role-specific ATS + writing prompt (4 types) |
| `experience/*.md` | Bullet libraries per company (6 entries) |
| `latex/template.tex` | LaTeX base template — **never modified** |
| `latex/output.tex` | Ephemeral per-run output — safe to overwrite |
| `~/JobSearch/` | V2 Obsidian vault |

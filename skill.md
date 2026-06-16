---
name: resume-builder
description: Tailors your resume to a specific job description. Detects role type, selects the 3–4 most relevant experience entries, runs a 2-step ATS workflow: keyword extraction → full resume, and optionally compiles a PDF via LaTeX. Use when you paste a JD or say "tailor my resume", "customize for this job", "update resume for [role/company]", "rebuild my resume", or "apply to [company]".
---

# Resume Builder — Orchestrator

## What This Skill Does

Given a job description, this skill:
1. Classifies the target role type
2. Loads the 3–4 most relevant experience entries (token-efficient)
3. Runs the role-specific 2-step ATS workflow: keyword extraction → full resume
4. Optionally builds a PDF from the LaTeX template
5. Saves tracking data so nothing is lost after the session

**Trigger phrases:** "tailor my resume", "customize for this job", "update my resume for [role]", "rebuild my resume", "apply to [company]", paste a JD, or pass a path to a JD file from your vault.

---

## Configuration

Update these two paths to match your local setup before first use.

```
V1 tracker path:  ~/Documents/ResumePrepNotes/tracker.csv
V2 vault path:    ~/Documents/JobSearch/
```

**V1 tracker path** — required for all users. The CSV tracker is saved here after every run.
**V2 vault path** — required only if using Obsidian (V2 mode). Leave blank if not using V2. See README for setup instructions.

---

## Mode Detection

Determine which mode to use based on the skill argument before doing anything else:

| Argument | Mode |
|---|---|
| Path to an existing `.md` file | **V2** — read JD text from that file |
| Raw pasted text | **V1** — standard flow |
| No argument, V2 vault configured | Ask: "Use most recently modified file in `JDs/`? [Yes / Paste instead]" |
| No argument, no vault | Prompt the user to paste a JD |
| `--compile [RoleType]` | **Compile mode** — skip to the `--compile Mode` section at the bottom |

---

## Step 0 — Archetype Check (V2 only)

*Skip this step if running in V1 mode.*

Check if `[V2 vault]/Archetypes/[RoleType]_summary.md` exists. Role type is not yet known — run Step 1 first (classify role), then return here before loading experience files.

- **Archetype found:** Load it. Report: "Loading [RoleType] archetype (compiled [date], N=[count] applications) — skipping raw experience file loading." Skip Step 2 and proceed with archetype context active.
- **No archetype:** Continue to Step 2 as normal.

---

## Step 1 — Role Type Classification

Read the JD. Using semantic understanding (not keyword matching), classify it into one of these four types:

| Type | Core Emphasis |
|---|---|
| **AI/ML Engineer** | Production systems — inference pipelines, model deployment, MLOps, LLMOps, scale, latency |
| **Data Scientist** | Statistical modeling — experiments, feature engineering, ML model development, predictive accuracy |
| **Data Analyst** | SQL-driven analysis and reporting — dashboards, KPIs, business intelligence, stakeholder communication |
| **Product Analyst / Ops** | Cross-functional execution — PDLC, GTM, roadmaps, sprint coordination, delivery operations |

State your classification with a one-line rationale, then use **AskUserQuestion** with:
- Question: `"This reads like a [TYPE] role — [one-line rationale]. Which type should I use?"`
- Option 1 (recommended): `"Yes, [Classified Type]"`
- Options 2–4: the other three role types in order
- (Built-in "Other" handles any edge case)

If ambiguous between two types, set both as the first two options with the more likely one marked recommended.

Role prompt files (absolute paths):
- AI/ML Engineer → `~/.claude/skills/resume-builder/roles/ai_ml_engineer.md`
- Data Scientist → `~/.claude/skills/resume-builder/roles/data_scientist.md`
- Data Analyst → `~/.claude/skills/resume-builder/roles/data_analyst.md`
- Product Analyst / Ops → `~/.claude/skills/resume-builder/roles/product_analyst_ops.md`

---

## Step 1.5 — Delta Keywords (V2 only, if archetype was loaded)

*Skip this step if running in V1 mode or if no archetype was loaded in Step 0.*

The archetype contains a `### known_keywords` field (all keywords seen in prior JDs of this type).

- Pre-populate List A and List B using the archetype's `### Top Required Skills` and `### Common Soft Keywords` sections.
- Extract only keywords from this JD that are **not** already in `known_keywords` — these are the delta.
- At the Step 3 keyword gate: present the archetype-sourced keywords as pre-accepted, show only the delta for user review.
- Flag: "Pre-loaded [N] keywords from [RoleType] archetype. New keywords in this JD: [M]"

---

## Step 2 — Selective Experience Loading (Token Efficiency)

*Skip this step entirely if an archetype was loaded in Step 0 — the archetype replaces it.*

**Do not load all experience files every time.** Based on the role type and JD domain, select 3–4 of the most relevant entries.

**Default load priority: [PRIMARY_COMPANY] → [SECONDARY_COMPANY] → [TERTIARY_COMPANY] → everything else.**
Selection is always about which bullets best match the JD's language — load whichever entries give you the strongest phrase-level match, regardless of heuristics.

Quick relevance map — replace company labels with your actual file names (without `.md`):

| JD Domain | Likely relevant entries |
|---|---|
| LLM / RAG / agentic AI | [company_a], [company_b], [company_c] |
| MLOps / production ML | [company_a], [company_b], [company_c] |
| SQL / dashboards / BI | [company_a], [company_b], [company_c] |
| NLP / text processing | [company_a], [company_b], [company_c] |
| Product / GTM / ops | [company_a], [company_b], [company_c] |
| Data science / modeling | [company_a], [company_b], [company_c] |
| Customer analytics | [company_a], [company_b], [company_c] |

**Session reuse:** If experience files and a role prompt are already loaded from a previous run this session, do not re-read them. State: "Reusing experience context from previous run — only the JD has changed." Then proceed directly to Step 1 of the role prompt with the new JD.

Experience file paths — update these with your actual file names:
```
~/.claude/skills/resume-builder/experience/[primary_company].md   ← always load
~/.claude/skills/resume-builder/experience/[company_b].md
~/.claude/skills/resume-builder/experience/[company_c].md
~/.claude/skills/resume-builder/experience/[company_d].md
~/.claude/skills/resume-builder/experience/[company_e].md
~/.claude/skills/resume-builder/experience/[company_f].md
```

---

## Step 3 — Run the Role Prompt (2-Step Workflow)

Read the matching role file. It contains two steps:

**Step 1 of role prompt:** Extract keyword lists (List A: hard keywords, List B: soft keywords, List C if applicable: business/process terms). Output the lists. Then use **AskUserQuestion** with:
- Question: `"Do you want to adjust the keyword lists before I write?"`
- Option 1 (recommended): `"Looks good — write the resume"`
- Option 2: `"Add keywords"`
- Option 3: `"Remove keywords"`
- Option 4: `"Add and remove keywords"`

**If the JD names no specific tools in List A** (e.g. no BI tool, no cloud platform, no language), fill in the most widely adopted tools for that role type in the 2026 market — do not leave List A empty. Flag any inferred tools clearly so the user can adjust them at the keyword gate.

For options 2–4, the user types their changes in the built-in "Other" notes field. Apply their input and proceed.

**Reuse option (V2 only, if archetype was loaded):**
Before writing the resume, use **AskUserQuestion** with:
- Question: `"Generate fresh, or start from the most similar prior resume?"`
- Option 1 (recommended): `"Generate fresh"`
- Option 2: `"Adapt from most similar prior"` → scan `[V2 vault]/Applications/` for notes of the same `type:` field, pick the one with highest keyword overlap with current List A, load it as the base, generate only the delta changes

**Step 2 of role prompt:** Write the full tailored resume using the role file's ATS rules, extrapolation guidance, writing style, and format. All selected experience entries (or archetype) are in context — draw bullets from them and adapt phrasing to match the JD's exact language.

**TERMINAL OUTPUT RULE — strictly enforced:**
Do NOT print the full resume content to the terminal. After composing it internally (to use in Step 4), output ONLY:
1. The `EXTRAPOLATED — PREP BEFORE INTERVIEW` table (as specified by the role file)
2. One line: `"Resume composed. Build the PDF?"` → then trigger Step 4

---

## Step 4 — Build PDF (Optional)

Use **AskUserQuestion** with:
- Question: `"Build the PDF?"`
- Option 1 (recommended): `"Yes, build PDF"`
- Option 2: `"No, text only"`

If yes:

**V1 mode:** Write the tailored resume content to `~/.claude/skills/resume-builder/latex/output.tex`, then run:
```bash
cd ~/.claude/skills/resume-builder/latex && \
/Library/TeX/texbin/pdflatex -interaction=nonstopmode output.tex && \
mv output.pdf ~/Documents/[YOUR_OUTPUT_FOLDER]/[YOUR_NAME]_Resume_[CompanyName]_[RoleType]_$(date +%Y%m%d).pdf
```

**V2 mode (vault configured):** Same compile step, but move the PDF to `[V2 vault]/Resumes/` instead:
```bash
mv output.pdf [V2_VAULT_PATH]/Resumes/[YOUR_NAME]_Resume_[CompanyName]_[RoleType]_$(date +%Y%m%d).pdf
```

**Never modify `latex/template.tex`.** Only write to `latex/output.tex`.

Output only the final PDF path to the terminal — no resume content.

Filename rules:
- Company + role known: `[YOUR_NAME]_Resume_Acme_DataAnalyst_20260615.pdf`
- Company unknown: `[YOUR_NAME]_Resume_DataAnalyst_20260615.pdf`
- Role type shortcodes: `DataAnalyst`, `DataScientist`, `AIMLEngineer`, `ProductAnalyst`

---

## Step 5 — Save Tracker

Runs unconditionally after Step 3 (regardless of PDF choice).

### V1 — Append to CSV (always runs)

Append one row to the V1 tracker path configured above.

**If the file doesn't exist:** create it with this header row first:
```
date,company,role,type,status,keywords_a,keywords_b,prep_notes
```

**Row format:**
```
[YYYY-MM-DD],[Company or "Unknown"],[Job Title],[RoleType],Researching,[List A pipe-separated],[List B pipe-separated],[flattened prep notes]
```

Flatten the EXTRAPOLATED table into the `prep_notes` cell: for each row format as `[addition]→[outcome] [ASSUMES: assumption]`, join all with ` | `.

Output: `"Saved → tracker.csv"`

### V2 — Write Application Note (runs when V2 vault is configured)

Write `[V2 vault]/Applications/[Company]_[RoleType]_[YYYYMMDD].md`:

```markdown
---
company: [Company or "Unknown"]
role: [Job Title from JD]
type: [DataAnalyst | DataScientist | AIMLEngineer | ProductAnalyst]
date: [YYYY-MM-DD]
status: Researching
keywords_a: [List A pipe-separated]
keywords_b: [List B pipe-separated]
jd_note: "[[JDs/[source filename if V2 mode, else leave blank]]]"
resume: "[[Resumes/[PDF filename if built, else leave blank]]]"
---

# [Company] — [Role]
**Date:** [YYYY-MM-DD]

## Keywords
**Hard (List A):** [comma-separated]
**Soft (List B):** [comma-separated]

## Interview Prep

[EXTRAPOLATED table, full format as output by the role file]
```

Output: `"Saved → Applications/[filename].md"`

---

## --compile Mode

Triggered by: `/resume-builder --compile [RoleType]`

Valid values: `DataAnalyst`, `DataScientist`, `AIMLEngineer`, `ProductAnalyst`

Requires V2 vault to be configured. Reads all accumulated application data for the given role type and distills it into a single archetype file that future runs load instead of all experience files.

**Process:**
1. Read all `.md` files in `[V2 vault]/Applications/` where the `type:` frontmatter field matches `[RoleType]`
2. For each application note: collect `keywords_a` and `keywords_b` values; load the linked `jd_note` file if it exists (for JD language pattern analysis)
3. Tally keyword frequencies across all N notes
4. Compare all unique `keywords_a` terms against the content of `~/.claude/skills/resume-builder/experience/*.md` — flag terms that appear in 5+ JDs but are absent from all experience files
5. Write `[V2 vault]/Archetypes/[RoleType]_summary.md`:

```markdown
## [RoleType] Archetype — compiled [YYYY-MM-DD] (N=[count] applications)

### known_keywords
[all unique keywords_a terms across all N applications, pipe-separated — used by Step 1.5 for delta detection on future runs]

### Top Required Skills (JD frequency)
[top 15 keywords_a terms with count, sorted descending: Term X/N · Term X/N · ...]

### Common Soft Keywords
[top 8 keywords_b terms with count: Term X/N · ...]

### JD Language Patterns
[2–4 observations about recurring phrases or framings found in the linked JD notes]

### Experience File Priority
[rank experience files by relevance to this role type, based on keyword overlap — replaces the static relevance map in Step 2 for future V2 runs]

### Skill Gap — Missing from Your Experience Files
Skills appearing in 5+ JDs not found in any experience entry:
- [term] ([count]/N) — [absent / partially covered in [company]]
...

Upskilling priority: [ranked list, highest-frequency gap first]
```

Output: `"Archetype written → Archetypes/[RoleType]_summary.md ([N] applications analyzed)"`

---

## Reference Files

| File | Purpose |
|---|---|
| `roles/*.md` | Role-specific ATS + writing prompt (4 types) |
| `experience/*.md` | Bullet libraries per company (one file per job) — gitignored, personal |
| `latex/template.tex` | LaTeX base template — **never modified by skill** |
| `latex/output.tex` | Ephemeral per-run output file — gitignored, safe to overwrite |
| `vault_template/` | Copy this folder to `~/Documents/JobSearch/` to bootstrap your V2 vault |
| `archive/` | Deprecated or reference files |

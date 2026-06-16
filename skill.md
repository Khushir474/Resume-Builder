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

**Trigger phrases:** "tailor my resume", "customize for this job", "update my resume for [role]", "rebuild my resume", "apply to [company]", paste a JD

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

## Step 2 — Selective Experience Loading (Token Efficiency)

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

**Step 2 of role prompt:** Write the full tailored resume using the role file's ATS rules, extrapolation guidance, writing style, and format. All selected experience entries are in context — draw bullets from them and adapt phrasing to match the JD's exact language.

**TERMINAL OUTPUT RULE — strictly enforced:**
Do NOT print the full resume content to the terminal. After composing it internally (to use in Step 4), output ONLY:
1. The `EXTRAPOLATED — PREP BEFORE INTERVIEW` table (as specified by the role file)
2. One line: `"Resume composed. Build the PDF?"` → then trigger Gate 3 (AskUserQuestion below)

---

## Step 4 — Build PDF (Optional)

Use **AskUserQuestion** with:
- Question: `"Build the PDF?"`
- Option 1 (recommended): `"Yes, build PDF"`
- Option 2: `"No, text only"`

If yes:
1. **Never modify `latex/template.tex`.** Write the tailored resume content to: `~/.claude/skills/resume-builder/latex/output.tex`
2. Run:
```bash
cd ~/.claude/skills/resume-builder/latex && \
/Library/TeX/texbin/pdflatex -interaction=nonstopmode output.tex && \
mv output.pdf ~/Documents/[YOUR_OUTPUT_FOLDER]/[YOUR_NAME]_Resume_[CompanyName]_[RoleType]_$(date +%Y%m%d).pdf
```
3. Output only the final PDF path to the terminal — no resume content.

Filename rules:
- Company + role known: `[YOUR_NAME]_Resume_Acme_DataAnalyst_20260615.pdf`
- Company unknown: `[YOUR_NAME]_Resume_DataAnalyst_20260615.pdf`
- Role type shortcodes: `DataAnalyst`, `DataScientist`, `AIMLEngineer`, `ProductAnalyst`

---

## Reference Files

| File | Purpose |
|---|---|
| `roles/*.md` | Role-specific ATS + writing prompt (4 types) |
| `experience/*.md` | Bullet libraries per company (one file per job) |
| `latex/template.tex` | LaTeX base template — **never modified by skill** |
| `latex/output.tex` | Ephemeral per-run output file — safe to overwrite |
| `archive/` | Deprecated or reference files |

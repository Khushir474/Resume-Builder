# Resume Builder — Claude Code Skill

A Claude Code skill that tailors your resume to any job description using ATS keyword extraction, role-specific writing rules, and automatic PDF compilation via LaTeX.

## How It Works

1. Paste a job description (or pass a path to a saved JD file in V2 mode)
2. Claude classifies the role type and selects your 3–4 most relevant experience entries
3. Extracts JD keywords and presents them for your review
4. Writes a tailored resume internally and outputs only the extrapolated prep table
5. Compiles a PDF via LaTeX on demand
6. Saves tracking data to a CSV — nothing is lost after the session

---

## Setup

### 1. Fill in your experience files (`experience/`)

Create one `.md` file per job or significant role. Name each file after the company in lowercase with underscores (e.g. `google.md`, `acme_corp.md`). Follow the template format in `experience/example_company.md`.

Aim for **5–6 experience files**. The skill selects the 3–4 most relevant per run — you don't need to trim your library per application.

> These files are gitignored — they stay local and are never committed.

### 2. Update `skill.md`

Four things to change:
- **Your name** in the PDF filename convention (Step 4)
- **The V1 tracker path** and **V2 vault path** in the Configuration section
- **The relevance map** (Step 2) — replace placeholder labels with your actual file names (without `.md`) so the skill knows which experiences to load for which JD domains

### 3. Fill in `latex/template.tex`

Replace every `[PLACEHOLDER]` with your personal info: name, location, phone, email, LinkedIn, GitHub. This file is the base for every PDF — the skill never modifies it, only reads it to understand LaTeX structure.

### 4. Prerequisites

- [Claude Code](https://claude.ai/code) installed
- `pdflatex` available
  - macOS: `brew install --cask mactex-no-gui` (then use `/Library/TeX/texbin/pdflatex`)
  - Linux: `sudo apt install texlive-full`

---

## Usage

### V1 — Standard (paste JD)

```
/resume-builder [paste full job description here]
```

After each run, a row is appended to `~/Documents/ResumePrepNotes/tracker.csv` containing the date, company, role type, keyword lists, and a collapsed version of the interview prep table. Open it in Excel or Numbers — the prep_notes cell expands to show all extrapolated points.

### V2 — Obsidian Workspace (pass saved JD file)

```
/resume-builder ~/Documents/JobSearch/JDs/Acme_DataAnalyst_20260615.md
```

In V2 mode the skill reads the JD from your Obsidian vault, writes a structured Application note with linked artifacts (JD ↔ Resume ↔ Prep notes), and saves the CSV row. See the **V2 Obsidian Workspace** section below for setup.

### Compile mode (V2 only)

```
/resume-builder --compile DataAnalyst
```

Reads all accumulated Application notes of the given role type and distills them into a role archetype file. Future runs load the archetype (~300 tokens) instead of all experience files (~3000 tokens), extract only delta keywords not already seen in prior JDs, and produce a **skill gap report** showing which high-frequency JD requirements are absent from your experience files.

---

## Role Types

Four role files are included out of the box:

| Type | Core Emphasis |
|---|---|
| AI/ML Engineer | Production ML — inference pipelines, model deployment, MLOps, LLMOps, scale |
| Data Scientist | Statistical modeling — experiments, feature engineering, predictive accuracy |
| Data Analyst | SQL-driven reporting — dashboards, KPIs, business intelligence, stakeholder comms |
| Product Analyst / Ops | Cross-functional execution — PDLC, GTM, roadmaps, sprint coordination |

---

## V2 Obsidian Workspace

V2 adds a persistent, linked workspace where JDs, resumes, and prep notes are all navigable in one place. Recommended once you're running multiple applications per week.

### Vault Setup

1. Copy the `vault_template/` folder from this repo to `~/Documents/JobSearch/`:
   ```bash
   cp -r vault_template/ ~/Documents/JobSearch/
   ```
2. Open `~/Documents/JobSearch/` as a new vault in Obsidian ("Open folder as vault")
3. Install the **Dataview** community plugin: Settings → Community plugins → Browse → search "Dataview"
4. Open `Tracker.md` in Obsidian — it renders as a live application status table

### JD Capture via Web Clipper

Instead of pasting job descriptions manually, use **Obsidian Web Clipper** to save a JD from your browser directly into your vault in one click.

**Install:**
1. Go to [obsidian.md/clipper](https://obsidian.md/clipper) and install the Chrome or Firefox extension
2. Pin it to your browser toolbar

**Create a template (do this once):**
1. Click the Web Clipper extension icon → open **Settings** (gear icon)
2. Go to **Templates** → click **New template**
3. Set **Name:** `Job Application`
4. Set **Vault:** `JobSearch`
5. Set **Note location:** `JDs`
6. Set **Note name:** `{{date:YYYYMMDD}}_{{title}}`
7. Paste this into the **Properties** section:

```
company: {{prompt:Company name}}
role: {{prompt:Job title}}
url: {{url}}
date_saved: {{date:YYYY-MM-DD}}
status: Unprocessed
```

8. In the **Content** field, set it to `{{content}}` to capture the full JD text
9. Save the template

**To clip a JD:**
1. Open any job posting (LinkedIn, Greenhouse, Lever, Workday, Ashby, etc.)
2. Click the Web Clipper icon → select the **Job Application** template
3. Fill in company and role when prompted → click **Save**
4. The JD lands in `~/Documents/JobSearch/JDs/` with frontmatter pre-filled

Then pass the saved file to the skill: `/resume-builder ~/Documents/JobSearch/JDs/[filename].md`

### Navigating Artifacts: Graph View and Tracker

The skill links each Application note back to its source JD and compiled resume using Obsidian wikilinks:

```yaml
jd_note: "[[JDs/Acme_DataAnalyst_20260615]]"
resume:  "[[Resumes/YourName_Resume_Acme_DataAnalyst_20260615.pdf]]"
```

**Graph view (built-in, no plugins):** Open **Graph view** from the left sidebar (Ctrl/Cmd+G). Each Application note appears as a node connected to its JD and resume. Applications of the same role type cluster together — visually showing which companies are in the same search track. Click any node to open that file.

**Local graph:** Open any Application note → click the graph icon in the top-right corner. Shows only that note's direct connections: its JD, resume, and any related applications that share keywords.

**Tracker table (requires Dataview plugin):** `Tracker.md` uses the [Dataview](https://github.com/blacksmithgu/obsidian-dataview) community plugin to render a live table of all applications sorted by date, with clickable links to each JD and resume. To enable it: Settings → Community plugins → Browse → search "Dataview" → Install → Enable. If you prefer not to use plugins, delete `Tracker.md` and rely on graph view alone — nothing else depends on it.

Update the `status` field in each Application note manually as you progress:
`Researching` → `Applied` → `Phone Screen` → `Interview` → `Offer` / `Rejected`

### Compiled Summaries and Skill Gap Analysis

After accumulating several applications of the same role type, run:

```
/resume-builder --compile DataAnalyst
```

This reads all DataAnalyst Application notes and generates `Archetypes/DataAnalyst_summary.md` containing:
- **Keyword frequency table** — ranked list of the most commonly required skills across all JDs you've seen
- **JD language patterns** — recurring phrases and framings worth mirroring in future resumes
- **Experience file priority** — dynamically ranked experience files for this role type, replacing the static relevance map
- **Skill gap report** — skills appearing in 5+ JDs that are absent from all your experience entries, ranked by frequency → your personal upskilling priority list

Future runs for that role type load the compiled archetype instead of raw experience files, and skip re-extracting keywords already seen in prior JDs.

---

## Folder Structure

```
resume-builder/
├── skill.md              ← Orchestrator — update name, paths, relevance map
├── README.md
├── roles/                ← Role-specific ATS + writing rules
│   ├── ai_ml_engineer.md
│   ├── data_analyst.md
│   ├── data_scientist.md
│   ├── product_analyst_ops.md
│   └── generate.md       ← Generator prompt — create new role files from scratch
├── experience/           ← Your bullet library — one file per job (gitignored)
│   └── example_company.md
├── latex/
│   ├── template.tex      ← Base LaTeX — fill in your personal info
│   └── output.tex        ← Auto-generated per run (gitignored), do not edit manually
├── vault_template/       ← Copy to ~/Documents/JobSearch/ to bootstrap V2 vault
│   ├── Tracker.md
│   ├── JDs/
│   │   └── example_jd.md
│   ├── Applications/
│   ├── Resumes/
│   └── Archetypes/
└── archive/
```

**What lives in the vault (local only, never committed):**
```
~/Documents/JobSearch/
├── JDs/           ← Web Clipper saves here
├── Applications/  ← Skill writes here after each run
├── Resumes/       ← PDFs saved here in V2 mode
└── Archetypes/    ← Compiled summaries from --compile runs
```

---

## Adding a New Role Type

If you're targeting a role that doesn't fit one of the four defaults (e.g. DevOps Engineer, UX Researcher, Marketing Manager), use the generator:

```
Read roles/generate.md and generate a new role file for me.
```

Claude will ask you 5 questions about the role, stack, and writing register, then write a complete `roles/[role_name].md` file in the correct format. After it's generated:
1. Add it as a classification option in `skill.md` Step 1
2. Add its file path to the role prompt paths list in `skill.md` Step 1
3. Update the relevance map in `skill.md` Step 2 if the role has a distinct JD domain

---

## Customizing Role Prompts

The files in `roles/` contain ATS rules, keyword signals, and writing style guidance. They work well out of the box but you can tune:
- **ATS signals** — add or remove domain-specific phrases for your industry
- **Stack lists** — update to reflect tools common in your target market
- **Writing style** — the default uses plain-language principles; adjust if your industry expects a different register

## Previewing LaTeX Before Running the Skill

To preview or edit your LaTeX resume before running the skill (saves tokens, useful for manual tweaks), paste the code into [Overleaf](https://www.overleaf.com/) for free preview and editing. Once satisfied, copy the final LaTeX back into `latex/template.tex`.

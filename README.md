# Resume Builder — Claude Code Skill

A Claude Code skill that tailors your resume to any job description using ATS keyword extraction, role-specific writing rules, and automatic PDF compilation via LaTeX.

## How It Works

1. Paste a job description as the skill argument
2. Claude classifies the role type and selects your 3–4 most relevant experience entries
3. Extracts JD keywords and presents them for your review
4. Writes a tailored resume internally and outputs only the extrapolated prep table
5. Compiles a PDF via LaTeX on demand

## Setup

### 1. Fill in your experience files (`experience/`)

Create one `.md` file per job or significant role. Name each file after the company in lowercase with underscores (e.g. `google.md`, `acme_corp.md`). Follow the template format in the provided example files.

Aim for **5–6 experience files**. The skill selects the 3–4 most relevant per run — you don't need to trim your library per application.

### 2. Update `skill.md`

Three things to change:
- **Your name** in the PDF filename convention (Step 4)
- **Your PDF output path** (Step 4)
- **The relevance map** (Step 2) — replace placeholder labels with your actual file names (without `.md`) so the skill knows which experiences to load for which JD domains

### 3. Fill in `latex/template.tex`

Replace every `[PLACEHOLDER]` with your personal info: name, location, phone, email, LinkedIn, GitHub. This file is the base for every PDF — the skill never modifies it, only reads it to understand LaTeX structure.

### 4. Prerequisites

- [Claude Code](https://claude.ai/code) installed
- `pdflatex` available
  - macOS: `brew install --cask mactex-no-gui` (then use `/Library/TeX/texbin/pdflatex`)
  - Linux: `sudo apt install texlive-full`

## Folder Structure

```
resume-builder/
├── skill.md              ← Orchestrator — update name, paths, relevance map
├── README.md
├── roles/                ← Role-specific ATS + writing rules — edit only to tune signals
│   ├── ai_ml_engineer.md
│   ├── data_analyst.md
│   ├── data_scientist.md
│   └── product_analyst_ops.md
├── experience/           ← Your bullet library — one file per job
│   └── example_company.md
├── latex/
│   ├── template.tex      ← Base LaTeX — fill in your personal info
│   └── output.tex        ← Auto-generated per run, do not edit manually
└── archive/
```

## Usage

```
/resume-builder [paste full job description here]
```

## Role Types

| Type | Core Emphasis |
|---|---|
| AI/ML Engineer | Production ML — inference pipelines, model deployment, MLOps, LLMOps, scale |
| Data Scientist | Statistical modeling — experiments, feature engineering, predictive accuracy |
| Data Analyst | SQL-driven reporting — dashboards, KPIs, business intelligence, stakeholder comms |
| Product Analyst / Ops | Cross-functional execution — PDLC, GTM, roadmaps, sprint coordination |

## Customizing Role Prompts

The files in `roles/` contain ATS rules, keyword signals, and writing style guidance per role type. They work well out of the box but you can tune:
- **ATS signals** — add or remove domain-specific phrases for your industry
- **Stack lists** — update to reflect tools common in your target market
- **Writing style** — the default uses Paul Graham plain-language principles; adjust if your industry expects different register

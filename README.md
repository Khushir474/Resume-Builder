# Resume Builder

A Claude Code skill that tailors a resume to a job description — ATS-optimized, role-classified, and compiled to PDF. Runs interactively via `/resume-builder` or fully automatically when a new JD file is dropped into the vault.

---

## How it works

**Interactive mode** (`/resume-builder`): guided flow with two confirmation gates — role type and keyword review — before writing the resume.

**Auto mode** (launchd watcher): drop a `.md` file into `JDs/`, walk away. Pipeline runs in the background:
1. Parses JD frontmatter (company, role, date)
2. Classifies role type via a lightweight Claude micro-call
3. Loads the relevant role ATS rules and experience files
4. Writes the full resume in one headless Claude call (no gates)
5. Compiles PDF via pdflatex
6. Saves an Application note to the vault
7. Fires a macOS system notification when done

**Compile mode** (`/resume-builder --compile [RoleType]`): reads all Application notes for a role type and writes an Archetype summary — a cached keyword + experience profile that future runs load instead of the raw experience files, cutting input tokens significantly.

---

## Prerequisites

- Claude Code (CLI)
- macOS (launchd, osascript for notifications)
- A full LaTeX install with `pdflatex` at `/Library/TeX/texbin/pdflatex`
- An Obsidian vault at `~/Documents/JobSearch/` with the structure below

---

## Vault structure

```
~/Documents/JobSearch/
├── JDs/              ← drop job descriptions here (.md files)
├── Applications/     ← auto-generated per-application notes
├── Archetypes/       ← compiled role summaries (from --compile)
└── Resumes/          ← output PDFs
```

JD files should have YAML frontmatter. Web Clipper format is supported automatically:

```yaml
---
title: Senior Data Scientist at Acme Corp
source: https://...
created: 2026-06-19
---
[job description text]
```

Or explicit fields:
```yaml
---
company: Acme Corp
role: Senior Data Scientist
---
[job description text]
```

---

## Skill structure

```
resume-builder/
├── SKILL.md                        # interactive orchestration logic
├── roles/                          # ATS writing rules per role type
│   ├── ai_ml_engineer.md
│   ├── data_scientist.md
│   ├── data_analyst.md
│   └── product_analyst_ops.md
├── experience/                     # (gitignored) bullet libraries per employer
├── latex/
│   ├── template.tex                # (gitignored) base template with contact info
│   ├── build.sh                    # compiles output.tex → PDF
│   └── output.tex                  # (gitignored) ephemeral per-run file
├── prompts/
│   ├── classify_prompt.md          # micro-call: returns role type label only
│   └── headless_prompt.md          # main auto-mode prompt, structured block output
└── scripts/
    ├── auto_resume.py              # end-to-end pipeline (called by launchd)
    ├── config.json                 # experience file selection rules
    ├── run_auto.sh                 # launchd wrapper (sources shell env)
    └── setup_watcher.sh            # install / uninstall / test / reset
```

---

## Setup

### 1. Set candidate name

Add to `~/.zshrc`:
```bash
export RESUME_CANDIDATE_NAME="Your Full Name"
```

This is the only place your name lives — picked up by both the PDF filename and the headless prompt. Not committed.

### 2. Create your experience files

Add one `.md` file per employer to `experience/`. Each file is a bullet library for that role. The pipeline selects 3–4 files per run based on JD domain signals in `config.json`.

### 3. Create your LaTeX template

Copy or write `latex/template.tex` with your contact info in the header. The pipeline writes only the Skills and Work Experience sections; the preamble, name header, and Education section are read from `template.tex` and prepended unchanged.

### 4. Install the file watcher

```bash
bash scripts/setup_watcher.sh install
```

This registers a launchd agent that watches `~/Documents/JobSearch/JDs/` and fires the pipeline automatically on any new `.md` file.

---

## Usage

### Drop a JD (auto mode)
Save any job description as a `.md` file in `~/Documents/JobSearch/JDs/`. The pipeline starts automatically. Check progress in `scripts/auto_resume.log`.

### Run interactively
```
/resume-builder
/resume-builder path/to/jd.md
```

### Compile a role archetype
```
/resume-builder --compile DataScientist
/resume-builder --compile AIMLEngineer
```
Run after every 3–5 applications of the same role type. Future auto runs load the archetype instead of all experience files, reducing tokens significantly.

### Watcher management
```bash
bash scripts/setup_watcher.sh status      # check if running
bash scripts/setup_watcher.sh install     # start watcher
bash scripts/setup_watcher.sh uninstall   # stop watcher
bash scripts/setup_watcher.sh test        # run pipeline on latest JD immediately
bash scripts/setup_watcher.sh reset       # clear all processed state
bash scripts/setup_watcher.sh reset "filename.md"   # reset one file
```

### Manual pipeline run
```bash
python3 scripts/auto_resume.py "/path/to/JDs/role-at-company.md"
```

---

## Configuration

### `scripts/config.json`
Controls which experience file is loaded as the optional 4th entry, beyond the three always-loaded. Edit the signal lists here as the job market evolves — no Python changes needed.

```json
{
  "always_load": ["employer_a", "employer_b", "employer_c"],
  "optional_fourth": {
    "employer_d": ["llm", "rag", "agentic", "mlops"],
    "employer_e": ["nlp", "text processing"],
    "employer_f": ["product", "gtm", "marketing"]
  },
  "role_files": {
    "AIMLEngineer": "ai_ml_engineer.md",
    "DataScientist": "data_scientist.md",
    "DataAnalyst": "data_analyst.md",
    "ProductAnalyst": "product_analyst_ops.md"
  }
}
```

### Role classification
Handled by a lightweight Claude call against the first 1,200 characters of the JD. Returns one of four labels: `AIMLEngineer`, `DataScientist`, `DataAnalyst`, `ProductAnalyst`. Stays current with market language automatically — no keyword lists to maintain.

---

## Token cost

| Flow | Claude calls | Approx tokens |
|---|---|---|
| Interactive (no archetype) | 3–4 turns | ~8,000–12,000 |
| Auto (no archetype) | 2 calls | ~4,000–6,000 |
| Auto (archetype loaded) | 2 calls | ~2,500–4,000 |

Archetypes are the biggest lever — compile one per role type after 3+ applications.

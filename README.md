# Resume Builder

A Claude Code skill that tailors a resume to a job description — ATS-optimized, role-classified, and compiled to PDF. Runs interactively via `/resume-builder` or fully automatically when a new JD file is dropped into the vault.

---

## Modes

| Mode | Trigger | Gates |
|---|---|---|
| **Interactive** | `/resume-builder` or `/resume-builder path/to/jd.md` | Role type + keyword review (manual) |
| **Auto** | Drop `.md` into `~/JobSearch/JDs/` | Council-gated — auto or notify based on confidence |
| **Compile** | `/resume-builder --compile [RoleType]` | None — reads past applications, writes archetype |

---

## Auto mode pipeline

```
  JD file dropped into ~/JobSearch/JDs/
           │
           ▼
    Parse frontmatter
    (company, role, date)
    ┌─ Company extraction ────────────────────────────────┐
    │  title: "Role at Company"  →  split on " at "       │
    │  source: jobs.ashbyhq.com/{co}/...  →  co           │
    │  source: jobs.lever.co/{co}/...     →  co           │
    │  source: boards.greenhouse.io/{co}  →  co           │
    │  source: {co}.myworkdayjobs.com/... →  co           │
    └─────────────────────────────────────────────────────┘
           │
           ▼
   macOS popup: "Resume Builder — Starting for {Company}"
           │
           ▼
  ┌────────────────────────────────────┐
  │       Classification Council       │
  │   3 × Haiku calls  (parallel)      │
  │                                    │
  │   each returns:                    │
  │     ROLE_TYPE  · EVIDENCE_FOR      │
  │     EVIDENCE_AGAINST · CONFIDENCE  │
  └───────────────┬────────────────────┘
                  │
         ┌────────┴─────────┐
         │ All agree +      │
         │ ≥ 2 HIGH conf?   │
         └────────┬─────────┘
          YES     │     NO
           │      └──► macOS dialog — recommendation + evidence
           │           user confirms or picks different type
           ▼
       Load archetype (if exists for role type)
       else load experience files
           │
           ▼
  ┌────────────────────────────────────┐
  │      Headless Claude call          │
  │      (Sonnet — main model)         │
  │                                    │
  │  outputs: KEYWORDS_A · KEYWORDS_B  │
  │           SKILLS LaTeX             │
  │           WORK_EXPERIENCE LaTeX    │
  │           EXTRAPOLATED table       │
  └───────────────┬────────────────────┘
                  │
                  ▼
  ┌────────────────────────────────────┐
  │        Keywords Council            │
  │   3 × Haiku calls  (parallel)      │
  │                                    │
  │   each returns:                    │
  │     APPROVED · MISSING_HARD        │
  │     MISSING_SOFT · CONFIDENCE      │
  └───────────────┬────────────────────┘
                  │
         ┌────────┴─────────┐
         │ All approved +   │
         │ ≥ 2 HIGH conf?   │
         └────────┬─────────┘
          YES     │     NO
           │      └──► macOS dialog — missing keywords
           │           user adds or skips
           ▼
        Compile PDF  (pdflatex)
        Warn in log if > 1 page
           │
           ├──► ~/JobSearch/Resumes/{Company}_{Type}_{Date}.pdf
           ├──► ~/JobSearch/Applications/{Company}_{Type}_{Date}.md
           ├──► ~/JobSearch/tracker.csv  (row appended)
           └──► macOS popup: "Resume Ready — {Company}"
```

---

## Council decision logic

Both councils (classification and keywords) use the same aggregation:

| All 3 agree? | HIGH votes | Confidence | Action |
|:---:|:---:|---|---|
| Yes | ≥ 2 | HIGH | Auto-proceed silently |
| Yes | 1 | MEDIUM | Show dialog with recommendation |
| Yes | 0 | LOW | Show dialog with recommendation |
| No | any | LOW | Show dialog with vote breakdown |

---

## Role classification

| Label | Core signals |
|---|---|
| **AIMLEngineer** | MLOps · inference pipelines · model deployment · LLMOps · latency · scale |
| **DataScientist** | Statistical modeling · experiments · feature engineering · A/B testing · predictive accuracy |
| **DataAnalyst** | SQL · dashboards · KPIs · BI tools · business intelligence · stakeholder reporting |
| **ProductAnalyst** | Roadmaps · GTM · PDLC · cross-functional execution · sprint coordination |

---

## Experience file selection

Three files always load. One optional 4th by JD domain:

```
Always loaded
  ├── itradenetwork.md
  ├── lia.md
  └── digitas.md

Optional 4th (first match wins)
  ├── lexlead_ai.md    ← llm, rag, agentic, mlops, modeling, genai, vector, embedding
  ├── teksystems.md    ← nlp, text processing, document processing, ocr
  └── galaara.md       ← product, gtm, marketing, customer analytics, growth, retention
```

After 3+ applications of the same role type, run `--compile` to build an archetype. Future runs load the archetype instead, skipping raw experience files.

---

## Vault structure

```
~/JobSearch/               ← outside ~/Documents to avoid macOS TCC restrictions
├── JDs/                   ← drop job descriptions here (.md files)
├── Applications/          ← auto-generated per-application notes
├── Archetypes/            ← compiled role summaries (from --compile)
├── Resumes/               ← output PDFs
└── tracker.csv            ← running log of all applications
```

> **Why not `~/Documents`?** macOS TCC restricts `~/Documents` access for background processes. The launchd file watcher needs to read this directory; placing the vault at `~/JobSearch` avoids requiring Full Disk Access grants.

**JD frontmatter** — web clipper format (auto-parsed):
```yaml
---
title: Support Operations Data Analyst at Harvey
source: https://jobs.ashbyhq.com/harvey/...
created: 2026-06-19
---
```

Or explicit:
```yaml
---
company: Harvey
role: Support Operations Data Analyst
---
```

---

## Repo structure

```
resume-builder/
├── skill.md                          # interactive orchestration logic (Claude Code)
├── roles/                            # ATS writing rules per role type
│   ├── ai_ml_engineer.md
│   ├── data_scientist.md
│   ├── data_analyst.md
│   └── product_analyst_ops.md
├── experience/                       # (gitignored) bullet libraries per employer
│   └── example_company.md            # template — copy and fill in per employer
├── latex/
│   ├── template.tex                  # base template — fill in contact info and Education
│   ├── build.sh                      # compiles output.tex → PDF, moves to vault
│   └── output.tex                    # (gitignored) ephemeral per-run file
├── prompts/
│   ├── headless_prompt.md            # main auto-mode prompt — structured block output
│   ├── council_classify_prompt.md    # classification council (evidence-based CoT)
│   └── council_keywords_prompt.md    # keyword completeness council
├── scripts/
│   ├── auto_resume.py                # end-to-end auto pipeline (called by launchd)
│   ├── config.json                   # council settings + experience file routing
│   ├── run_auto.sh                   # launchd wrapper (sources shell env)
│   └── setup_watcher.sh             # install / uninstall / test / reset watcher
└── vault_template/                   # sanitized scaffold — copy to ~/JobSearch to start
    ├── JDs/example_jd.md
    ├── Applications/
    ├── Archetypes/
    ├── Resumes/
    ├── Tracker.md
    └── tracker.csv                   # header only — rows appended by auto pipeline
```

**What's gitignored:**
- `experience/*.md` — your actual bullet libraries (personal work history)
- `latex/output.tex` and build artifacts — ephemeral per-run files
- `scripts/.processed_jds.json` and `auto_resume.log` — local runtime state

---

## Setup

**1. Install LaTeX**
```bash
brew install --cask mactex-no-gui
```
Requires `pdflatex` at `/Library/TeX/texbin/pdflatex`.

**2. Set up the vault**
```bash
cp -r vault_template ~/JobSearch
```

**3. Create experience files**
Copy `experience/example_company.md` for each employer. Name must match the key in `config.json`.

**4. Fill in `latex/template.tex`**
Add your contact info, LinkedIn, GitHub, and Education section. The pipeline writes only Skills and Work Experience — everything else comes from the template unchanged.

**5. Install the file watcher**
```bash
bash scripts/setup_watcher.sh install
```
Registers a launchd agent that watches `~/JobSearch/JDs/` and runs the full pipeline when a new `.md` file appears. Also fires every 5 minutes as a fallback.

---

## Usage

```bash
# Drop a JD — pipeline runs automatically
cp "role-at-company.md" ~/JobSearch/JDs/

# Interactive via Claude Code
/resume-builder
/resume-builder ~/JobSearch/JDs/role.md

# Compile archetype (run after 3–5 applications per role type)
/resume-builder --compile DataScientist
/resume-builder --compile AIMLEngineer

# Watcher management
bash scripts/setup_watcher.sh status
bash scripts/setup_watcher.sh install
bash scripts/setup_watcher.sh uninstall
bash scripts/setup_watcher.sh test          # run on latest JD immediately
bash scripts/setup_watcher.sh reset         # clear all processed state
bash scripts/setup_watcher.sh reset "file.md"

# Manual run
python3 scripts/auto_resume.py "/path/to/JDs/role.md"

# Check logs
tail -f scripts/auto_resume.log
```

---

## Token cost

| Step | Calls | Model | When |
|---|---|---|---|
| Classification council | 3 parallel | Haiku | Every run |
| Headless write | 1 | Sonnet | Every run |
| Keywords council | 3 parallel | Haiku | Every run |
| **Total — no archetype** | **7** | mixed | ~8,000–10,000 tokens |
| **Total — archetype loaded** | **7** | mixed | ~5,500–7,000 tokens |

Archetypes cut Sonnet input tokens by replacing raw experience files with a pre-distilled keyword + bullet profile.

---

## `config.json` reference

```json
{
  "council_size": 3,
  "council_model": "claude-haiku-4-5-20251001",
  "council_keywords_timeout": 120,
  "always_load": ["itradenetwork", "lia", "digitas"],
  "optional_fourth": { "lexlead_ai": ["llm", "rag", "..."] },
  "role_files": { "AIMLEngineer": "ai_ml_engineer.md", "...": "..." }
}
```

| Key | Effect |
|---|---|
| `council_size` | Number of independent council calls per decision (default 3) |
| `council_model` | Model for council calls — Haiku keeps cost low |
| `council_keywords_timeout` | Per-call timeout in seconds for keywords council |

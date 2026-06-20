#!/usr/bin/env python3
"""
Auto Resume Builder
Triggered by launchd when a new .md file appears in ~/Documents/JobSearch/JDs/
"""

import os
import re
import json
import subprocess
import datetime
import sys
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────────
HOME        = Path.home()
SKILLS_DIR  = HOME / ".claude/skills/resume-builder"
JDS_DIR     = HOME / "Documents/JobSearch/JDs"
APPS_DIR    = HOME / "Documents/JobSearch/Applications"
ARCH_DIR    = HOME / "Documents/JobSearch/Archetypes"
LATEX_DIR   = SKILLS_DIR / "latex"
SCRIPTS_DIR = SKILLS_DIR / "scripts"
PROMPTS_DIR = SKILLS_DIR / "prompts"

TEMPLATE_TEX  = LATEX_DIR / "template.tex"
OUTPUT_TEX    = LATEX_DIR / "output.tex"
BUILD_SH      = LATEX_DIR / "build.sh"
STATE_FILE    = SCRIPTS_DIR / ".processed_jds.json"
CONFIG_FILE   = SCRIPTS_DIR / "config.json"
CLASSIFY_TMPL = PROMPTS_DIR / "classify_prompt.md"
HEADLESS_TMPL = PROMPTS_DIR / "headless_prompt.md"

CLAUDE_BIN = "/Applications/c11.app/Contents/Resources/bin/claude"
SKIP_FILES = {"example_jd.md"}
VALID_TYPES = {"AIMLEngineer", "DataScientist", "DataAnalyst", "ProductAnalyst"}


# ── Config ─────────────────────────────────────────────────────────────────────
def load_config():
    return json.loads(CONFIG_FILE.read_text())


# ── Frontmatter parser ─────────────────────────────────────────────────────────
def parse_frontmatter(text):
    match = re.match(r'^---\r?\n(.*?)\r?\n---\r?\n', text, re.DOTALL)
    if not match:
        return {}, text
    meta = {}
    for line in match.group(1).splitlines():
        if ':' in line:
            k, _, v = line.partition(':')
            meta[k.strip()] = v.strip().strip('"').strip('[]')
    body = text[match.end():]

    # Normalize: if web-clipper format (has `title:` but no `company:`/`role:`)
    # extract from "Role at Company" or "Role - Company" pattern in title
    if "company" not in meta and "title" in meta:
        title = meta["title"]
        if " at " in title:
            role_part, _, company_part = title.rpartition(" at ")
            meta["role"] = role_part.strip()
            meta["company"] = company_part.strip()
        elif " - " in title:
            role_part, _, company_part = title.rpartition(" - ")
            meta["role"] = role_part.strip()
            meta["company"] = company_part.strip()
        else:
            meta["role"] = title
            meta["company"] = "Unknown"

    return meta, body


# ── State ──────────────────────────────────────────────────────────────────────
def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {}

def save_state(state):
    STATE_FILE.write_text(json.dumps(state, indent=2))

def get_unprocessed(state):
    pending = []
    for jd in sorted(JDS_DIR.glob("*.md"), key=lambda f: f.stat().st_mtime):
        if jd.name in SKIP_FILES:
            continue
        mtime = jd.stat().st_mtime
        if mtime > state.get(jd.name, {}).get("mtime", 0):
            pending.append((jd, mtime))
    return pending


# ── Claude calls ───────────────────────────────────────────────────────────────
def call_claude(prompt, timeout=60):
    """Call claude --print with bypassPermissions to prevent tool-use hangs."""
    env = os.environ.copy()
    env["HOME"] = str(HOME)
    result = subprocess.run(
        [
            CLAUDE_BIN, "--print",
            "--permission-mode", "bypassPermissions",
            "--no-session-persistence",
            prompt,
        ],
        capture_output=True, text=True, timeout=timeout, env=env
    )
    if result.returncode != 0:
        raise RuntimeError(f"Claude exited {result.returncode}:\n{result.stderr[:800]}")
    return result.stdout.strip()

def classify_role(jd_body):
    template = CLASSIFY_TMPL.read_text()
    prompt = template.replace("<<<JD_EXCERPT>>>", jd_body[:1200])
    raw = call_claude(prompt, timeout=60)
    for label in VALID_TYPES:
        if label in raw:
            return label
    log(f"WARN: unexpected classification '{raw}', defaulting to DataScientist")
    return "DataScientist"


# ── Experience loading ─────────────────────────────────────────────────────────
def select_experience_files(jd_text_lower, config):
    files = list(config["always_load"])
    for exp_file, signals in config["optional_fourth"].items():
        if any(sig in jd_text_lower for sig in signals):
            files.append(exp_file)
            break
    return files

def load_experience_content(filenames):
    parts = []
    for name in filenames:
        path = SKILLS_DIR / "experience" / f"{name}.md"
        if path.exists():
            parts.append(path.read_text())
        else:
            log(f"WARN: experience file not found: {name}.md")
    return "\n\n---\n\n".join(parts)


# ── Static LaTeX header (preamble + name + education — never changes) ──────────
def build_static_header():
    text = TEMPLATE_TEX.read_text()
    lines = text.splitlines(keepends=True)
    for i, line in enumerate(lines):
        if '% ── Skills' in line:
            return ''.join(lines[:i])
    # Fallback: split at first \ressection{Skills}
    return text.split(r'\ressection{Skills}')[0]


# ── Response parsing ───────────────────────────────────────────────────────────
def extract_block(text, tag):
    pattern = rf'==={tag}===\n(.*?)\n===END {tag}==='
    match = re.search(pattern, text, re.DOTALL)
    if not match:
        raise ValueError(f"Missing block: {tag}")
    return match.group(1).strip()


# ── output.tex assembly ────────────────────────────────────────────────────────
def write_output_tex(skills_latex, work_latex):
    header = build_static_header()
    content = (
        header
        + "\n"
        + skills_latex
        + "\n\n\\vspace{4pt}\n"
        + work_latex
        + "\n\n\\end{document}\n"
    )
    OUTPUT_TEX.write_text(content)


# ── PDF build ──────────────────────────────────────────────────────────────────
def build_pdf(company_slug, role_type):
    result = subprocess.run(
        ["/bin/bash", str(BUILD_SH), company_slug, role_type, "V2"],
        capture_output=True, text=True, cwd=str(LATEX_DIR)
    )
    if result.returncode != 0:
        raise RuntimeError(f"pdflatex failed — check {LATEX_DIR}/output.log\n{result.stdout}")
    return result.stdout.strip()


# ── Application note ───────────────────────────────────────────────────────────
def save_application_note(meta, role_type, keywords_a, keywords_b, extrapolated, pdf_path, jd_filename):
    company  = meta.get("company", "Unknown")
    role     = meta.get("role", "Unknown")
    date     = datetime.date.today().isoformat()
    slug     = re.sub(r'[^a-zA-Z0-9]', '', company)
    filename = f"{slug}_{role_type}_{date.replace('-', '')}.md"
    pdf_name = Path(pdf_path).name if pdf_path else ""

    note = f"""---
company: {company}
role: {role}
type: {role_type}
date: {date}
status: Researching
keywords_a: {' | '.join(keywords_a)}
keywords_b: {' | '.join(keywords_b)}
jd_note: "[[JDs/{jd_filename}]]"
resume: "[[Resumes/{pdf_name}]]"
---

# {company} — {role}
**Date:** {date}

## Keywords
**Hard (List A):** {', '.join(keywords_a)}
**Soft (List B):** {', '.join(keywords_b)}

## Interview Prep

{extrapolated}
"""
    (APPS_DIR / filename).write_text(note)
    return filename


# ── macOS notification ─────────────────────────────────────────────────────────
def notify(company, pdf_path):
    pdf_name = Path(pdf_path).name if pdf_path else "check log"
    script = (
        f'display notification "{pdf_name}" '
        f'with title "Resume Ready — {company}" '
        f'sound name "Glass"'
    )
    subprocess.run(["osascript", "-e", script], capture_output=True)


# ── Logging ────────────────────────────────────────────────────────────────────
def log(msg):
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


# ── Main pipeline ──────────────────────────────────────────────────────────────
def process_jd(jd_path, config):
    log(f"Processing: {jd_path.name}")

    text = jd_path.read_text()
    meta, body = parse_frontmatter(text)
    company     = meta.get("company", "Unknown")
    company_slug = re.sub(r'[^a-zA-Z0-9]', '', company) or "Unknown"

    # Step 1 — classify (Claude micro-call, ~100 tokens)
    log("Classifying role type...")
    role_type = classify_role(body)
    log(f"Role type: {role_type}")

    # Step 2 — check archetype, else load experience files
    archetype = ARCH_DIR / f"{role_type}_summary.md"
    if archetype.exists():
        experience_content = archetype.read_text()
        log(f"Using archetype: {archetype.name}")
    else:
        exp_files = select_experience_files(body.lower(), config)
        experience_content = load_experience_content(exp_files)
        log(f"Experience files: {exp_files}")

    # Step 3 — load role requirements
    role_file_name = config["role_files"][role_type]
    role_requirements = (SKILLS_DIR / "roles" / role_file_name).read_text()

    # Step 4 — build and send main prompt (single Claude call)
    log("Writing resume...")
    candidate_name = os.environ.get("RESUME_CANDIDATE_NAME", "the candidate")
    headless = HEADLESS_TMPL.read_text()
    prompt = (
        headless
        .replace("<<<CANDIDATE_NAME>>>", candidate_name)
        .replace("<<<ROLE_TYPE>>>", role_type)
        .replace("<<<COMPANY>>>", company)
        .replace("<<<POSITION>>>", meta.get("role", "Unknown"))
        .replace("<<<JD_TEXT>>>", body)
        .replace("<<<ROLE_REQUIREMENTS>>>", role_requirements)
        .replace("<<<EXPERIENCE_CONTENT>>>", experience_content)
    )
    response = call_claude(prompt, timeout=600)

    # Step 5 — parse structured output
    keywords_a  = [k.strip() for k in extract_block(response, "KEYWORDS_A").split(",") if k.strip()]
    keywords_b  = [k.strip() for k in extract_block(response, "KEYWORDS_B").split(",") if k.strip()]
    skills_tex  = extract_block(response, "SKILLS")
    work_tex    = extract_block(response, "WORK_EXPERIENCE")
    extrapolated = extract_block(response, "EXTRAPOLATED")

    # Step 6 — write output.tex and compile PDF
    write_output_tex(skills_tex, work_tex)
    log("Building PDF...")
    pdf_path = build_pdf(company_slug, role_type)
    log(f"PDF → {pdf_path}")

    # Step 7 — save application note
    note = save_application_note(meta, role_type, keywords_a, keywords_b, extrapolated, pdf_path, jd_path.name)
    log(f"Saved → Applications/{note}")

    # Step 8 — notify
    notify(company, pdf_path)

    return pdf_path


def main():
    # Allow manual invocation: python3 auto_resume.py path/to/jd.md [--force]
    force_path = None
    if len(sys.argv) > 1 and sys.argv[1] not in ("--reset",):
        force_path = Path(sys.argv[1]).expanduser()

    if len(sys.argv) > 1 and sys.argv[1] == "--reset":
        target = sys.argv[2] if len(sys.argv) > 2 else None
        state = load_state()
        if target:
            state.pop(target, None)
            log(f"Reset state for: {target}")
        else:
            state = {}
            log("Reset all processed state.")
        save_state(state)
        return

    config = load_config()
    state  = load_state()

    if force_path:
        pending = [(force_path, force_path.stat().st_mtime)]
    else:
        pending = get_unprocessed(state)

    if not pending:
        log("No new JDs to process.")
        return

    for jd_path, mtime in pending:
        try:
            process_jd(jd_path, config)
            state[jd_path.name] = {
                "mtime": mtime,
                "processed_at": datetime.datetime.now().isoformat()
            }
            save_state(state)
        except Exception as e:
            log(f"ERROR — {jd_path.name}: {e}")
            # Leave out of state so it retries next trigger


if __name__ == "__main__":
    main()

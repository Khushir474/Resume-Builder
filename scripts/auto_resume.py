#!/usr/bin/env python3
"""
Auto Resume Builder
Triggered by launchd when a new .md file appears in ~/Documents/JobSearch/JDs/
"""

import csv
import os
import re
import json
import subprocess
import datetime
import time
import sys
import tempfile
import urllib.parse
from contextlib import contextmanager
from pathlib import Path
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed

# ── Paths ──────────────────────────────────────────────────────────────────────
HOME        = Path.home()
SKILLS_DIR  = HOME / ".claude/skills/resume-builder"
JDS_DIR     = HOME / "JobSearch/JDs"
APPS_DIR    = HOME / "JobSearch/Applications"
ARCH_DIR    = HOME / "JobSearch/Archetypes"
LATEX_DIR   = SKILLS_DIR / "latex"
SCRIPTS_DIR = SKILLS_DIR / "scripts"
PROMPTS_DIR = SKILLS_DIR / "prompts"
TRACKER_CSV = HOME / "JobSearch/tracker.csv"

TEMPLATE_TEX          = LATEX_DIR / "template.tex"
OUTPUT_TEX            = LATEX_DIR / "output.tex"
BUILD_SH              = LATEX_DIR / "build.sh"
STATE_FILE            = SCRIPTS_DIR / ".processed_jds.json"
CONFIG_FILE           = SCRIPTS_DIR / "config.json"
HEADLESS_TMPL         = PROMPTS_DIR / "headless_prompt.md"
COUNCIL_CLASSIFY_TMPL = PROMPTS_DIR / "council_classify_prompt.md"
COUNCIL_KEYWORDS_TMPL = PROMPTS_DIR / "council_keywords_prompt.md"

CLAUDE_BIN  = "/Applications/c11.app/Contents/Resources/bin/claude"
SKIP_FILES  = {"example_jd.md"}
VALID_TYPES = {"AIMLEngineer", "DataScientist", "DataAnalyst", "ProductAnalyst"}
RUNS_LOG    = SCRIPTS_DIR / "runs.jsonl"


# ── Structured logger ──────────────────────────────────────────────────────────
def slog(record: dict):
    record["ts"] = datetime.datetime.now().isoformat(timespec="seconds")
    with RUNS_LOG.open("a") as f:
        f.write(json.dumps(record) + "\n")

@contextmanager
def timed(step: str, meta: dict | None = None):
    t0 = time.monotonic()
    try:
        yield
    finally:
        slog({"event": "step", "step": step, "dur_s": round(time.monotonic() - t0, 2), **(meta or {})})


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
            # Fallback 1: extract company from ATS source URL
            company_from_url = _extract_company_from_url(meta.get("source", ""))
            # Fallback 2: look for "At [Company]," or "Why [Company]" in description field
            company_from_desc = _extract_company_from_description(meta.get("description", ""))
            meta["company"] = company_from_url or company_from_desc or "Unknown"

    return meta, body


def _extract_company_from_url(url):
    if not url:
        return None
    try:
        parsed = urllib.parse.urlparse(url)
        host   = parsed.hostname or ""
        parts  = [p for p in parsed.path.split('/') if p]
        # Ashby:      jobs.ashbyhq.com/{company}/...
        # Lever:      jobs.lever.co/{company}/...
        # Greenhouse: boards.greenhouse.io/{company}/...
        if any(ats in host for ats in ("ashbyhq.com", "lever.co", "greenhouse.io")) and parts:
            return parts[0].capitalize()
        # Workday: {company}.wd1.myworkdayjobs.com/...
        if "myworkdayjobs.com" in host:
            return host.split('.')[0].capitalize()
    except Exception:
        pass
    return None


def _extract_company_from_description(desc):
    if not desc:
        return None
    for pattern in (r'At (\w+),', r'Why (\w+)\b', r'join (\w+) ', r'About (\w+)\b'):
        m = re.search(pattern, desc[:500])
        if m:
            candidate = m.group(1)
            # Skip generic words
            if candidate.lower() not in {"us", "the", "our", "this", "a", "an"}:
                return candidate
    return None


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
def call_claude(prompt, timeout=60, model=None, _step=None):
    env = os.environ.copy()
    env["HOME"] = str(HOME)
    # Ensure both the c11 wrapper dir and the real claude binary dir are in PATH.
    # The c11 wrapper (CLAUDE_BIN) skips its own dir and searches PATH for the
    # actual claude binary — ~/.local/bin/claude — so both must be present.
    extra = f"{Path(CLAUDE_BIN).parent}:{HOME / '.local/bin'}"
    env["PATH"] = f"{extra}:{env.get('PATH', '/usr/local/bin:/usr/bin:/bin')}"
    args = [
        CLAUDE_BIN, "--print",
        "--permission-mode", "bypassPermissions",
        "--no-session-persistence",
    ]
    if model:
        args += ["--model", model]
    args.append(prompt)
    t0 = time.monotonic()
    result = subprocess.run(args, capture_output=True, text=True, timeout=timeout, env=env)
    dur = round(time.monotonic() - t0, 2)
    slog({
        "event":       "claude_call",
        "step":        _step or "unknown",
        "model":       model or "sonnet",
        "in_tok_est":  len(prompt) // 4,
        "out_tok_est": len(result.stdout) // 4,
        "dur_s":       dur,
        "status":      "ok" if result.returncode == 0 else f"err:{result.returncode}",
    })
    if result.returncode != 0:
        raise RuntimeError(f"Claude exited {result.returncode}:\n{result.stderr[:800]}")
    return result.stdout.strip()


# ── AppleScript helpers ────────────────────────────────────────────────────────
def _esc(s):
    """Sanitize string for safe embedding in an AppleScript double-quoted string."""
    return str(s).replace('\\', '').replace('"', "'").replace('\n', ' ').replace('\r', '')

def run_applescript(script, timeout=320):
    with tempfile.NamedTemporaryFile(mode='w', suffix='.applescript', delete=False) as f:
        f.write(script)
        fname = f.name
    try:
        result = subprocess.run(["osascript", fname], capture_output=True, text=True, timeout=timeout)
        return result.stdout.strip(), result.returncode
    finally:
        os.unlink(fname)


# ── Council: role type classification ─────────────────────────────────────────
def parse_council_classify_response(text):
    result = {"role_type": None, "evidence_for": "", "evidence_against": "none", "confidence": "LOW"}
    for line in text.strip().splitlines():
        if line.startswith("ROLE_TYPE:"):
            result["role_type"] = line.split(":", 1)[1].strip()
        elif line.startswith("EVIDENCE_FOR:"):
            result["evidence_for"] = line.split(":", 1)[1].strip()
        elif line.startswith("EVIDENCE_AGAINST:"):
            result["evidence_against"] = line.split(":", 1)[1].strip()
        elif line.startswith("CONFIDENCE:"):
            result["confidence"] = line.split(":", 1)[1].strip()
    if result["role_type"] not in VALID_TYPES:
        for vt in VALID_TYPES:
            if vt in text:
                result["role_type"] = vt
                break
        else:
            result["role_type"] = "DataScientist"
    return result

def aggregate_classify_votes(votes):
    answers    = [v["role_type"] for v in votes]
    confs      = [v["confidence"] for v in votes]
    counter    = Counter(answers)
    recommendation, majority_count = counter.most_common(1)[0]
    all_agree  = (majority_count == len(votes))
    high_count = confs.count("HIGH")

    if all_agree and high_count >= 2:
        overall_conf, needs_user = "HIGH", False
    else:
        overall_conf = "MEDIUM" if (all_agree or high_count >= 1) else "LOW"
        needs_user   = True

    if all_agree:
        summary = f"{high_count}/3 HIGH confidence"
    else:
        vote_str = ", ".join(f"{k}×{v}" for k, v in counter.most_common())
        summary  = f"split vote ({vote_str})"

    majority_votes   = [v for v in votes if v["role_type"] == recommendation]
    evidence_for     = "; ".join(dict.fromkeys(v["evidence_for"]     for v in majority_votes))[:200]
    evidence_against = "; ".join(dict.fromkeys(v["evidence_against"] for v in majority_votes))[:200]

    return recommendation, overall_conf, needs_user, summary, evidence_for, evidence_against

def ask_user_role_type(recommendation, overall_conf, summary, evidence_for, evidence_against):
    rec  = _esc(recommendation)
    ef   = _esc((evidence_for    or "N/A")[:120])
    ea   = _esc((evidence_against or "none")[:120])
    conf = _esc(f"{overall_conf} ({summary})")

    script = "\n".join([
        'set msg to "Confidence: ' + conf + '" & return & return & "Evidence for ' + rec + ': ' + ef + '" & return & return & "Evidence against: ' + ea + '"',
        'set r1 to button returned of (display dialog msg with title "Resume Builder - Role Classification" buttons {"Use ' + rec + '", "Choose Different"} default button "Use ' + rec + '" giving up after 300)',
        'if r1 is "Choose Different" then',
        '    set chosen to choose from list {"AIMLEngineer", "DataScientist", "DataAnalyst", "ProductAnalyst"} with title "Resume Builder - Role Type" with prompt "Select the correct role type:" default items {"' + rec + '"}',
        '    if chosen is false then',
        '        return "' + rec + '"',
        '    else',
        '        return item 1 of chosen',
        '    end if',
        'else',
        '    return "' + rec + '"',
        'end if',
    ])
    out, _ = run_applescript(script)
    return out if out in VALID_TYPES else recommendation

def council_classify(jd_body, config):
    n        = config.get("council_size", 3)
    model    = config.get("council_model")
    template = COUNCIL_CLASSIFY_TMPL.read_text()
    prompt   = template.replace("<<<JD_EXCERPT>>>", jd_body[:2000])

    def _classify_one(i):
        raw  = call_claude(prompt, timeout=60, model=model, _step="council_classify")
        return i, parse_council_classify_response(raw)

    votes = []
    with ThreadPoolExecutor(max_workers=n) as ex:
        futures = {ex.submit(_classify_one, i): i for i in range(n)}
        for fut in as_completed(futures):
            try:
                i, vote = fut.result()
                log(f"  Council {i+1}: {vote['role_type']} [{vote['confidence']}]")
                votes.append(vote)
            except Exception as e:
                log(f"  Council call failed: {e}")

    if not votes:
        log("All council calls failed — defaulting to DataScientist")
        return "DataScientist", False

    recommendation, overall_conf, needs_user, summary, ev_for, ev_against = aggregate_classify_votes(votes)
    log(f"Council verdict: {recommendation} | {overall_conf} | {summary}")

    if not needs_user:
        return recommendation, False

    chosen = ask_user_role_type(recommendation, overall_conf, summary, ev_for, ev_against)
    return chosen, True


# ── Council: keyword evaluation ────────────────────────────────────────────────
def parse_council_keywords_response(text):
    result = {"approved": False, "missing_hard": [], "missing_soft": [], "confidence": "LOW"}
    for line in text.strip().splitlines():
        if line.startswith("APPROVED:"):
            result["approved"] = line.split(":", 1)[1].strip().upper() == "YES"
        elif line.startswith("MISSING_HARD:"):
            val = line.split(":", 1)[1].strip()
            result["missing_hard"] = [] if val.lower() == "none" else [k.strip() for k in val.split(",") if k.strip()]
        elif line.startswith("MISSING_SOFT:"):
            val = line.split(":", 1)[1].strip()
            result["missing_soft"] = [] if val.lower() == "none" else [k.strip() for k in val.split(",") if k.strip()]
        elif line.startswith("CONFIDENCE:"):
            result["confidence"] = line.split(":", 1)[1].strip()
    return result

def aggregate_keywords_votes(votes):
    approved_count   = sum(1 for v in votes if v["approved"])
    confs            = [v["confidence"] for v in votes]
    high_count       = confs.count("HIGH")
    all_missing_hard = list(dict.fromkeys(k for v in votes for k in v["missing_hard"]))
    all_missing_soft = list(dict.fromkeys(k for v in votes for k in v["missing_soft"]))
    all_approved     = (approved_count == len(votes))

    if all_approved and high_count >= 2:
        overall_conf, needs_user = "HIGH", False
    else:
        overall_conf = "MEDIUM" if approved_count >= 2 else "LOW"
        needs_user   = True

    summary = f"{approved_count}/3 approved, {high_count}/3 HIGH"
    return all_missing_hard, all_missing_soft, overall_conf, needs_user, summary

def ask_user_keywords(missing_hard, missing_soft, overall_conf, summary):
    combined = _esc(", ".join(missing_hard + missing_soft)[:200])
    conf_str = _esc(f"{overall_conf} ({summary})")

    script = "\n".join([
        'set msg to "Confidence: ' + conf_str + '" & return & return & "Suggested additions: ' + combined + '" & return & return & "Add these to your application tracking?"',
        'set r to button returned of (display dialog msg with title "Resume Builder - Keywords" buttons {"Add Missing", "Keep As-Is"} default button "Keep As-Is" giving up after 300)',
        'return r',
    ])
    out, _ = run_applescript(script)
    return out == "Add Missing"

def council_evaluate_keywords(keywords_a, keywords_b, jd_body, config):
    n        = config.get("council_size", 3)
    model    = config.get("council_model")
    timeout  = config.get("council_keywords_timeout", 120)
    template = COUNCIL_KEYWORDS_TMPL.read_text()
    prompt   = (
        template
        .replace("<<<KEYWORDS_A>>>", ", ".join(keywords_a))
        .replace("<<<KEYWORDS_B>>>", ", ".join(keywords_b))
        .replace("<<<JD_EXCERPT>>>",  jd_body[:1500])
    )

    def _keywords_one(i):
        raw  = call_claude(prompt, timeout=timeout, model=model, _step="council_keywords")
        return i, parse_council_keywords_response(raw)

    votes = []
    with ThreadPoolExecutor(max_workers=n) as ex:
        futures = {ex.submit(_keywords_one, i): i for i in range(n)}
        for fut in as_completed(futures):
            try:
                i, vote = fut.result()
                log(f"  Keywords council {i+1}: approved={vote['approved']} [{vote['confidence']}]")
                votes.append(vote)
            except Exception as e:
                log(f"  Keywords council call failed: {e}")

    if not votes:
        log("Keywords council failed — keeping extracted keywords")
        return keywords_a, keywords_b

    missing_hard, missing_soft, overall_conf, needs_user, summary = aggregate_keywords_votes(votes)
    log(f"Keywords verdict: {overall_conf} | {summary}")

    if not needs_user or (not missing_hard and not missing_soft):
        return keywords_a, keywords_b

    if ask_user_keywords(missing_hard, missing_soft, overall_conf, summary):
        final_a = keywords_a + [k for k in missing_hard if k not in keywords_a]
        final_b = keywords_b + [k for k in missing_soft if k not in keywords_b]
        log(f"Keywords updated — added {len(missing_hard)} hard, {len(missing_soft)} soft")
        return final_a, final_b

    return keywords_a, keywords_b


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


# ── Static LaTeX header ────────────────────────────────────────────────────────
def build_static_header():
    text  = TEMPLATE_TEX.read_text()
    lines = text.splitlines(keepends=True)
    for i, line in enumerate(lines):
        if '% ── Skills' in line:
            return ''.join(lines[:i])
    return text.split(r'\ressection{Skills}')[0]


# ── Response parsing ───────────────────────────────────────────────────────────
def extract_block(text, tag):
    pattern = rf'==={tag}===\n(.*?)\n===END {tag}==='
    match   = re.search(pattern, text, re.DOTALL)
    if not match:
        raise ValueError(f"Missing block: {tag}")
    return match.group(1).strip()


# ── output.tex assembly ────────────────────────────────────────────────────────
def write_output_tex(skills_latex, work_latex):
    header  = build_static_header()
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
def _count_pdf_pages(pdf_path):
    try:
        r = subprocess.run(
            ["mdls", "-name", "kMDItemNumberOfPages", pdf_path],
            capture_output=True, text=True, timeout=10
        )
        m = re.search(r'= (\d+)', r.stdout)
        return int(m.group(1)) if m else None
    except Exception:
        return None

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
    role     = meta.get("role",    "Unknown")
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


# ── macOS notifications ────────────────────────────────────────────────────────
def notify_start(company, jd_filename):
    script = (
        f'display notification "Processing {_esc(jd_filename)}" '
        f'with title "Resume Builder — Starting for {_esc(company)}" '
        f'sound name "Purr"'
    )
    subprocess.run(["osascript", "-e", script], capture_output=True)

def notify(company, pdf_path):
    pdf_name = Path(pdf_path).name if pdf_path else "check log"
    script   = (
        f'display notification "{pdf_name}" '
        f'with title "Resume Ready — {company}" '
        f'sound name "Glass"'
    )
    subprocess.run(["osascript", "-e", script], capture_output=True)


# ── Tracker CSV ────────────────────────────────────────────────────────────────
def _flatten_extrapolated(extrapolated):
    rows = []
    for line in extrapolated.splitlines():
        line = line.strip()
        if not line.startswith("|") or "|---" in line or "Addition" in line:
            continue
        parts = [p.strip() for p in line.strip("|").split("|")]
        if len(parts) >= 3 and parts[0]:
            rows.append(f"{parts[0]}→{parts[1]} ASSUMES: {parts[2]}")
    return " | ".join(rows)

def save_tracker_csv(meta, role_type, keywords_a, keywords_b, extrapolated):
    company  = meta.get("company", "Unknown")
    role     = meta.get("role",    "Unknown")
    date     = datetime.date.today().isoformat()
    prep     = _flatten_extrapolated(extrapolated)
    header   = ["date", "company", "role", "type", "status", "keywords_a", "keywords_b", "prep_notes"]
    row      = [date, company, role, role_type, "Researching", "|".join(keywords_a), "|".join(keywords_b), prep]
    exists   = TRACKER_CSV.exists()
    with TRACKER_CSV.open("a", newline="") as f:
        writer = csv.writer(f)
        if not exists:
            writer.writerow(header)
        writer.writerow(row)
    log("Saved → tracker.csv")


# ── Logging ────────────────────────────────────────────────────────────────────
def log(msg):
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


# ── Main pipeline ──────────────────────────────────────────────────────────────
def process_jd(jd_path, config):
    log(f"Processing: {jd_path.name}")
    run_start = time.monotonic()

    text         = jd_path.read_text()
    meta, body   = parse_frontmatter(text)
    company      = meta.get("company", "Unknown")
    company_slug = re.sub(r'[^a-zA-Z0-9]', '', company) or "Unknown"

    slog({"event": "run_start", "jd": jd_path.name, "company": company,
          "role": meta.get("role", "Unknown")})
    notify_start(company, jd_path.name)

    # Step 1 — council classify
    log("Council classifying role type...")
    with timed("council_classify"):
        role_type, prompted = council_classify(body, config)
    log(f"Role type: {role_type}" + (" (user-confirmed)" if prompted else " (auto)"))

    # Step 2 — archetype or experience files
    archetype = ARCH_DIR / f"{role_type}_summary.md"
    if archetype.exists():
        experience_content = archetype.read_text()
        log(f"Using archetype: {archetype.name}")
    else:
        exp_files          = select_experience_files(body.lower(), config)
        experience_content = load_experience_content(exp_files)
        log(f"Experience files: {exp_files}")

    # Step 3 — role requirements
    role_file_name    = config["role_files"][role_type]
    role_requirements = (SKILLS_DIR / "roles" / role_file_name).read_text()

    # Step 4 — main headless call
    log("Writing resume...")
    headless = HEADLESS_TMPL.read_text()
    prompt   = (
        headless
        .replace("<<<ROLE_TYPE>>>",          role_type)
        .replace("<<<COMPANY>>>",            company)
        .replace("<<<POSITION>>>",           meta.get("role", "Unknown"))
        .replace("<<<JD_TEXT>>>",            body)
        .replace("<<<ROLE_REQUIREMENTS>>>",  role_requirements)
        .replace("<<<EXPERIENCE_CONTENT>>>", experience_content)
    )
    with timed("headless_write"):
        response = call_claude(prompt, timeout=600, _step="headless_write")

    # Step 5 — parse structured output
    keywords_a   = [k.strip() for k in extract_block(response, "KEYWORDS_A").split(",") if k.strip()]
    keywords_b   = [k.strip() for k in extract_block(response, "KEYWORDS_B").split(",") if k.strip()]
    skills_tex   = extract_block(response, "SKILLS")
    work_tex     = extract_block(response, "WORK_EXPERIENCE")
    extrapolated = extract_block(response, "EXTRAPOLATED")

    # Step 5.5 — council evaluate keywords
    log("Council evaluating keywords...")
    with timed("council_keywords"):
        keywords_a, keywords_b = council_evaluate_keywords(keywords_a, keywords_b, body, config)

    # Step 6 — compile PDF
    write_output_tex(skills_tex, work_tex)
    log("Building PDF...")
    with timed("pdf_build"):
        pdf_path = build_pdf(company_slug, role_type)
    log(f"PDF → {pdf_path}")
    pages = _count_pdf_pages(pdf_path)
    if pages and pages > 1:
        log(f"WARN: resume is {pages} pages — bullet budget exceeded, check output.tex")

    # Step 7 — save application note
    note = save_application_note(meta, role_type, keywords_a, keywords_b, extrapolated, pdf_path, jd_path.name)
    log(f"Saved → Applications/{note}")

    # Step 7b — append to tracker CSV
    save_tracker_csv(meta, role_type, keywords_a, keywords_b, extrapolated)

    total_s = round(time.monotonic() - run_start, 2)
    slog({"event": "run_complete", "jd": jd_path.name, "company": company,
          "role_type": role_type, "total_s": total_s, "pdf": pdf_path,
          "pages": pages, "kw_a": len(keywords_a), "kw_b": len(keywords_b)})
    log(f"Done in {total_s}s")

    # Step 8 — notify
    notify(company, pdf_path)

    return pdf_path


def print_stats():
    if not RUNS_LOG.exists():
        print("No runs logged yet.")
        return
    rows = [json.loads(l) for l in RUNS_LOG.read_text().splitlines() if l.strip()]

    runs     = [r for r in rows if r["event"] == "run_complete"]
    calls    = [r for r in rows if r["event"] == "claude_call"]
    steps    = [r for r in rows if r["event"] == "step"]

    print(f"\n{'─'*60}")
    print(f"  Resume Builder — run stats  ({len(runs)} completed runs)")
    print(f"{'─'*60}")

    if runs:
        for r in runs[-10:]:          # last 10 runs
            print(f"\n  {r['ts']}  {r['company']} ({r['role_type']})")
            print(f"    total: {r['total_s']}s   pdf: {r.get('pages','?')}p   "
                  f"keywords: {r.get('kw_a',0)}A + {r.get('kw_b',0)}B")
            # matching step records for this run
            run_steps = [s for s in steps if s["ts"] <= r["ts"] and
                         s["step"] in ("council_classify","headless_write","council_keywords","pdf_build")]
            for s in run_steps:
                print(f"    {s['step']:25s} {s['dur_s']:6.1f}s")

    print(f"\n{'─'*60}")
    print(f"  Claude calls breakdown")
    print(f"{'─'*60}")
    by_step: dict = {}
    for c in calls:
        k = (c["step"], c["model"])
        if k not in by_step:
            by_step[k] = {"n": 0, "dur": 0.0, "in_tok": 0, "out_tok": 0, "err": 0}
        by_step[k]["n"]      += 1
        by_step[k]["dur"]    += c["dur_s"]
        by_step[k]["in_tok"] += c.get("in_tok_est", 0)
        by_step[k]["out_tok"]+= c.get("out_tok_est", 0)
        if c["status"] != "ok":
            by_step[k]["err"] += 1
    for (step, model), v in sorted(by_step.items()):
        avg = v["dur"] / v["n"] if v["n"] else 0
        print(f"  {step:25s} {model:30s}  n={v['n']:3d}  "
              f"avg={avg:5.1f}s  "
              f"in≈{v['in_tok']:6d}tok  out≈{v['out_tok']:5d}tok  "
              f"err={v['err']}")
    print()


def main():
    force_path = None
    if len(sys.argv) > 1 and sys.argv[1] not in ("--reset", "--stats"):
        force_path = Path(sys.argv[1]).expanduser()

    if len(sys.argv) > 1 and sys.argv[1] == "--stats":
        print_stats()
        return

    if len(sys.argv) > 1 and sys.argv[1] == "--reset":
        target = sys.argv[2] if len(sys.argv) > 2 else None
        state  = load_state()
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
                "mtime":        mtime,
                "processed_at": datetime.datetime.now().isoformat()
            }
            save_state(state)
        except Exception as e:
            log(f"ERROR — {jd_path.name}: {e}")


if __name__ == "__main__":
    main()

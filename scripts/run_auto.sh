#!/bin/bash
# Wrapper for launchd — restores shell environment before running the pipeline

source "$HOME/.zshrc" 2>/dev/null || source "$HOME/.bash_profile" 2>/dev/null || true

SCRIPTS="$HOME/.claude/skills/resume-builder/scripts"

# Brief pause to let the file fully land before processing
sleep 2

echo "[$(date -Iseconds)] Triggered" >> "$SCRIPTS/auto_resume.log"
python3 "$SCRIPTS/auto_resume.py" >> "$SCRIPTS/auto_resume.log" 2>&1
echo "[$(date -Iseconds)] Exit $?" >> "$SCRIPTS/auto_resume.log"

#!/bin/bash
# Install or remove the auto-resume launchd watcher

PLIST="$HOME/Library/LaunchAgents/com.khushi.resumebuilder.plist"
LABEL="com.khushi.resumebuilder"
SCRIPTS="$HOME/.claude/skills/resume-builder/scripts"

ACTION="${1:-install}"

case "$ACTION" in
  install)
    chmod +x "$SCRIPTS/run_auto.sh"
    launchctl unload "$PLIST" 2>/dev/null || true
    launchctl load "$PLIST"
    echo "Watcher installed. Watching ~/JobSearch/JDs for new .md files."
    echo "Logs: $SCRIPTS/auto_resume.log"
    ;;

  uninstall)
    launchctl unload "$PLIST" 2>/dev/null || true
    echo "Watcher removed."
    ;;

  status)
    launchctl list "$LABEL" 2>/dev/null && echo "Running." || echo "Not loaded."
    ;;

  test)
    # Dry-run against the most recently modified JD
    LATEST=$(ls -t ~/JobSearch/JDs/*.md 2>/dev/null | grep -v example_jd | head -1)
    if [ -z "$LATEST" ]; then
      echo "No JD files found in ~/JobSearch/JDs/"
      exit 1
    fi
    echo "Testing against: $LATEST"
    python3 "$SCRIPTS/auto_resume.py" "$LATEST"
    ;;

  reset)
    # Clear processed state so all JDs will be reprocessed on next trigger
    TARGET="${2:-}"
    python3 "$SCRIPTS/auto_resume.py" --reset "$TARGET"
    ;;

  *)
    echo "Usage: $0 [install|uninstall|status|test|reset [filename]]"
    exit 1
    ;;
esac

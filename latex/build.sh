#!/bin/bash
# Usage: build.sh <Company> <RoleType> <V1|V2>
# RoleType shortcodes: DataAnalyst, DataScientist, AIMLEngineer, ProductAnalyst

COMPANY="${1:-Unknown}"
ROLE="${2:-Resume}"
MODE="${3:-V1}"

LATEX_DIR="$(cd "$(dirname "$0")" && pwd)"
DATE=$(date +%Y%m%d)
FILENAME="Khushi_Ranganatha_Resume_${COMPANY}_${ROLE}_${DATE}.pdf"

cd "$LATEX_DIR"
/Library/TeX/texbin/pdflatex -interaction=nonstopmode output.tex > /dev/null 2>&1

if [ $? -ne 0 ]; then
  echo "ERROR: pdflatex failed — check $LATEX_DIR/output.log"
  exit 1
fi

if [ "$MODE" = "V2" ]; then
  DEST="$HOME/JobSearch/Resumes/$FILENAME"
else
  DEST="$HOME/Documents/Career/Resume/resume-builder-outputs/$FILENAME"
fi

mv output.pdf "$DEST"
echo "$DEST"

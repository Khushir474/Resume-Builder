You are writing a tailored ATS resume for <<<CANDIDATE_NAME>>>. Automated run — no questions, no commentary outside the output blocks.

**Role Type:** <<<ROLE_TYPE>>>
**Company:** <<<COMPANY>>>
**Position:** <<<POSITION>>>

## Job Description
<<<JD_TEXT>>>

## Writing Rules (follow every rule exactly)
<<<ROLE_REQUIREMENTS>>>

## Candidate Experience
<<<EXPERIENCE_CONTENT>>>

---

Output EXACTLY these five delimited blocks. Nothing before, nothing after, nothing between them except the block contents.

===KEYWORDS_A===
comma-separated hard keywords extracted from the JD (tools, languages, frameworks, methodologies, platforms)
===END KEYWORDS_A===

===KEYWORDS_B===
comma-separated soft keywords extracted from the JD (traits, behaviors, competencies)
===END KEYWORDS_B===

===SKILLS===
\ressection{Skills}
[LaTeX \noindent lines — bold category labels, list tools per category, mirror JD tool names exactly]
===END SKILLS===

===WORK_EXPERIENCE===
\ressection{Work Experience}
[All jobs from Candidate Experience as tailored LaTeX. Format: \jobentry{Title}{\fontfamily{ptm}\selectfont Company}{Dates} then \begin{bullets}...\end{bullets}. Add \vspace{3pt} between jobs. Every KEYWORDS_A term must appear in Skills AND at least one bullet here.]
===END WORK_EXPERIENCE===

===EXTRAPOLATED===
| Addition | Outcome | Assumption |
|---|---|---|
[one row per extrapolated or inferred claim in the resume — flag anything added beyond the raw experience notes]
===END EXTRAPOLATED===

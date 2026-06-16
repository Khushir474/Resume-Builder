# Job Application Tracker

```dataview
TABLE company, role, date, status, jd_note, resume
FROM "Applications"
SORT date DESC
```

---

**Status values** (update manually in each Application note as you progress):
`Researching` → `Applied` → `Phone Screen` → `Interview` → `Offer` / `Rejected`

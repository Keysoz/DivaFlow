#!/usr/bin/env python3
"""Regenerate tasks.csv from the build plan, enhancement backlog and localization docs."""

import csv
import re

rows: list[list[str]] = []


def add(i: str, phase: str, title: str, dep: str, ac: str, src: str, pri: str = "") -> None:
    rows.append(
        [
            i,
            phase,
            re.sub(r"\*\*", "", title).strip(),
            dep.strip(),
            re.sub(r"\*\*", "", ac).strip(),
            src,
            pri,
        ]
    )


with open("docs/09-build-plan.md", encoding="utf-8") as f:
    nine = f.read().split("\n")
for line in nine:
    m = re.match(r"^\| ((?:P0|E|PUB|O)-\d+[a-z]?) \| (.*) \|$", line)
    if m:
        parts = m.group(2).split(" | ")
        if len(parts) >= 3:
            add(
                m.group(1),
                m.group(1).split("-")[0],
                parts[0],
                parts[1],
                " | ".join(parts[2:]),
                "09-build-plan",
            )
for line in nine:
    m = re.match(r"^([BCAM])-01 ", line)
    if m:
        ph = m.group(1)
        body = line.split(" **")[0] if " **" in line else line
        mm = re.search(r"\*\*AC:\*\*(.*?)(?:\*\*Exit gate|$)", line)
        ac = mm.group(1) if mm else "See the phase gate in 09-build-plan"
        pattern = rf"({ph}-\d{{2}}) (.+?)(?=; {ph}-\d{{2}} |\. \*\*|\.\s*$|$)"
        for t in re.finditer(pattern, body):
            add(t.group(1), ph, t.group(2), "", ac, "09-build-plan")
with open("docs/16-enhancement-backlog.md", encoding="utf-8") as f:
    backlog = f.read().split("\n")
for line in backlog:
    if line.startswith("| ENH-") and "**Accepted**" in line:
        c = [x.strip() for x in line.strip().strip("|").split(" | ")]
        ph = "E" if c[3] == "E, PUB" else c[3]
        add(c[0], ph, c[1], "", c[2], "16-enhancement-backlog", c[5])
with open("docs/19-localization-arabic-english.md", encoding="utf-8") as f:
    loc = f.read().split("\n")
for line in loc:
    m = re.match(r"^\| (I18N-\d+) \| (.*) \| (.*) \| (.*) \|$", line)
    if m:
        add(m.group(1), m.group(3), m.group(2), "", m.group(4), "19-localization")

seen: set[str] = set()
out: list[list[str]] = []
for r in rows:
    if r[0] not in seen:
        seen.add(r[0])
        out.append(r)
with open("tasks.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(["id", "phase", "title", "depends_on", "acceptance", "source", "priority"])
    w.writerows(out)
print(len(out), "tasks written to tasks.csv")

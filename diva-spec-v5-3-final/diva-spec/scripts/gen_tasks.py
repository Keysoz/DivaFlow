#!/usr/bin/env python3
"""Regenerate tasks.csv from docs/09-build-plan.md, docs/16-enhancement-backlog.md and docs/19-localization-arabic-english.md."""
import csv, re
rows = []
def add(i, phase, title, dep, ac, src, pri=''):
    rows.append([i, phase, re.sub(r'\*\*', '', title).strip(), dep.strip(), re.sub(r'\*\*', '', ac).strip(), src, pri])
nine = open('docs/09-build-plan.md', encoding='utf-8').read().split('\n')
for l in nine:
    m = re.match(r'^\| ((?:P0|E|PUB|O)-\d+[a-z]?) \| (.*) \|$', l)
    if m:
        parts = m.group(2).split(' | ')
        if len(parts) >= 3:
            add(m.group(1), m.group(1).split('-')[0], parts[0], parts[1], ' | '.join(parts[2:]), '09-build-plan')
for l in nine:
    m = re.match(r'^([BCAM])-01 ', l)
    if m:
        ph = m.group(1)
        body = l.split(' **')[0] if ' **' in l else l
        mm = re.search(r'\*\*AC:\*\*(.*?)(?:\*\*Exit gate|$)', l)
        ac = mm.group(1) if mm else 'See the phase gate in 09-build-plan'
        for t in re.finditer(r'(%s-\d{2}) (.+?)(?=; %s-\d{2} |\. \*\*|\.\s*$|$)' % (ph, ph), body):
            add(t.group(1), ph, t.group(2), '', ac, '09-build-plan')
for l in open('docs/16-enhancement-backlog.md', encoding='utf-8').read().split('\n'):
    if l.startswith('| ENH-') and '**Accepted**' in l:
        c = [x.strip() for x in l.strip().strip('|').split(' | ')]
        ph = 'E' if c[3] == 'E, PUB' else c[3]
        add(c[0], ph, c[1], '', c[2], '16-enhancement-backlog', c[5])
for l in open('docs/19-localization-arabic-english.md', encoding='utf-8').read().split('\n'):
    m = re.match(r'^\| (I18N-\d+) \| (.*) \| (.*) \| (.*) \|$', l)
    if m:
        add(m.group(1), m.group(3), m.group(2), '', m.group(4), '19-localization')
seen, out = set(), []
for r in rows:
    if r[0] not in seen:
        seen.add(r[0]); out.append(r)
with open('tasks.csv', 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.writer(f); w.writerow(['id', 'phase', 'title', 'depends_on', 'acceptance', 'source', 'priority']); w.writerows(out)
print(len(out), 'tasks written to tasks.csv')

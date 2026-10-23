# Review prompt (use a second, fresh session or a second agent)

Review pull request <link or branch> against `AGENTS.md` (hard constraints and Definition of Done) and the spec rules it touches.
1. List any violation of the hard constraints, with file and line.
2. Check that tests exist, were really run, and cover the acceptance criteria. Flag deleted, skipped or weakened tests.
3. Look for secrets, unrelated changes, hidden shortcuts, and anything that could mark a payment verified automatically.
4. Check Arabic and English strings and error messages.
5. Explain in plain language, for a non-developer, what this change does and what could go wrong.
Give PASS or FAIL with reasons.

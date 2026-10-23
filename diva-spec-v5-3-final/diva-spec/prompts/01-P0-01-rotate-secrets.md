# TASK P0-01 and P0-02: exposed credentials and legacy endpoints

Context: my old n8n export contained a Telegram bot token, Meta access tokens, a URL-shortener token and a weak webhook verify token, and nine unauthenticated "Nanobot" webhooks. Treat all of them as exposed.

You cannot rotate credentials on the platforms; I will. Do this:
1. Without printing any secret value, list every place a secret appears in the files I give you (file and node name only).
2. Write a step-by-step rotation checklist for me (Telegram, Meta, URL shortener, webhook verify token), in order, with what to update afterwards.
3. Describe how to disable or authenticate the nine legacy webhooks, and how I verify it (the failed call I should see).
4. Add secret scanning to the repository CI (a gitleaks-style scan) and a rule that blocks commits containing secrets.
Evidence required: the scan finds zero secrets in the repo; show the command and result.

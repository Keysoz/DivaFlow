# Critical review (run in a Western-vendor tool: Claude Code on Pro, Codex on Plus, or a free Antigravity tier)

This pull request touches payments, deposits, discounts, `diva_guard`, authentication, backups or migrations. Review it as a security and correctness reviewer.
1. Can any path mark a payment as verified without a human reviewer?
2. Can a price, discount, deposit or total come from the client without server recomputation?
3. Are permissions checked explicitly on every state-changing endpoint? Is every command idempotent?
4. Can a retry or double click duplicate an order, payment or message?
5. Are secrets, real customer data or personal data logged or sent anywhere?
6. Do the tests really cover these cases?
Give PASS or FAIL with file and line references. Do not edit code.

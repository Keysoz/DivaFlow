# 21 AI Tooling Policy (models, tools, budget, data rules)

Decided 2026-10-20 (DEC-55, DEC-56). Prices and rankings change monthly; re-verify before subscribing and again every quarter.

## 1. Budget
Target **$20 to $60 per month** for AI coding tools. Set a spending cap in every account. Review spend weekly.

## 2. Starting setup (about $10–60 per month)
| Lane | What | Cost |
|---|---|---|
| Agent models | OpenCode with **OpenCode Go** ($10) for Phase P0 and light work; **Go Plus ($40)** when Phase E coding starts, because Go has small monthly limits on the stronger models (section 7) | $10, then $40 |
| Overflow | In the OpenCode Console, add a small credit balance and turn on **Extra usage** so work is not blocked when a limit is reached; set a Budget | $0–10 |
| Critical reviewer | A Western-vendor model in its own tool: a free Antigravity tier, or Claude Pro or ChatGPT Plus when needed | $0 or $20 |
Go and Go Plus are for workspaces with one member (your personal workspace). Review spend weekly in the Console.

## 3. Which lane does what
| Work | Lane |
|---|---|
| Reading the spec, planning, architecture | Primary |
| Payments, deposits, `diva_guard`, authentication, backups, migrations | Primary, then reviewed by the second vendor |
| Everyday implementation (screens, adapters, endpoints) | Primary or bulk |
| Tests, docs, commit messages, SOP drafts, config files | Bulk |
| Arabic UI text | A strong model drafts, **a native Egyptian speaker reviews** |
| Pull-request review | Second vendor |
| Test running and log triage | Bulk |

## 4. Data rules (apply to every tool and model)
1. Never send secrets, production credentials, or real customer data (names, phones, addresses, chats, voice) to any model. Use anonymized data only.
2. Chinese-vendor apps and APIs used directly store data under Chinese law and may train on it. Use Chinese models only through OpenCode Go, whose own privacy table (checked 2026-10-21) lists no training and 0-day retention for them (DeepSeek's zero-retention agreement is renewed monthly and was valid through 31 October 2026), or through another zero-retention host, or self-hosted. Re-read the table every month. Even then, send only code and anonymized test data.
3. Keep payment, deposit, login and `diva_guard` code with providers whose business terms you have accepted.
4. Run agents in a sandbox or dev environment with no production access (DEC-38). Treat text from files, web pages and tickets as untrusted: agents can be tricked into running commands.
5. Check each provider is available in Egypt and that your payment method works before relying on it.

## 5. Choosing and re-choosing (bake-off)
Week 1: run `P0-10` (repository and CI) and `P0-04` (ERPNext verification) with two setups. Score each: acceptance criteria met, rework rounds, cost, time. Keep the cheapest setup that passes. Repeat the comparison every quarter and when a major model ships.

## 6. Models for the product itself (runtime)
Separate from the coding tools. Evaluate in `P0-09` and `A-03` with the 100 anonymized chats and 50 voice notes.
- **Arabic chat:** candidates are Haiku-class, Gemini Flash-class and GPT mini-class models, plus a Chinese open model through a zero-retention host. Large general models usually beat small Arabic-specific models, but Egyptian dialect and Franco-Arabic must be tested; an Egyptian-specific model such as Nile-Chat is a candidate for cheap classification.
- **Speech-to-text:** pick by word error rate on your own voice notes.
- **Images:** pick by quality and cost per image.
Choose the cheapest model that meets the evaluation thresholds.

## 7. OpenCode setup and the model for each job (DEC-57, DEC-60)
The harness is OpenCode with OpenCode Go. The repository's `opencode.json` assigns a model to each job; model IDs use the form `opencode-go/<model-id>`. Run `opencode models` first and substitute the closest current model if an ID is missing. Switch between `plan` and `build` with the Tab key; call the other agents by name with an @ mention.

**Go limits matter.** Each model has its own monthly dollar limit; every 5-hour window may use 20% and every week 50% of it. On Go ($10), estimated requests per month are about: DeepSeek V4.1 Flash 173,000; MiMo-V2.6-Flash 150,000; Qwen3.7 Plus 21,600; Hy3 21,500; MiniMax M3 16,000; MiMo-V2.6-Pro 16,300; Kimi K2.7 Code 6,750; DeepSeek V4 Pro 5,200; GLM-5.2 4,300; GLM-5.3 1,080; Qwen3.8 Max 810; Kimi K3 490. A coding agent makes many requests per task, so **high-volume work goes to the high-quota models**, and the strong low-quota models are kept for planning, hard problems and reviews. Go Plus raises the limits.

| Job | Agent | Default model | Why | Fallback |
|---|---|---|---|---|
| Planning, architecture, debugging, AI prompts and evals | `plan` | GLM-5.2 | Strong, with a workable quota | GLM-5.3 via `plan-hard` |
| Hardest architecture questions | `plan-hard` | GLM-5.3 | Best GLM, but about 1,080 requests a month on Go | GLM-5.2 |
| Backend, ERPNext, DevOps, migrations (the volume work) | `build` | DeepSeek V4.1 Flash | Very cheap, huge quota, reported as the top open-weight model on a terminal-agent benchmark | MiMo-V2.6-Flash |
| Tricky implementation the main agent cannot solve | `build-hard` | DeepSeek V4 Pro | Stronger; about 5,200 requests a month | GLM-5.2 |
| Front-end, routine screens | `frontend` | Kimi K2.7 Code | Good everyday UI work; 6,750 requests a month | Qwen3.7 Plus |
| Front-end, hard sessions | `frontend-hard` | Kimi K3 | Top front-end model, but only about 490 requests a month: rare use | Kimi K2.7 Code |
| Tests | `tests` | Qwen3.7 Plus | A different family from the implementer; 21,600 requests a month | MiniMax M3 |
| Bulk edits, boilerplate, CI fixes, log triage | `bulk` | MiMo-V2.6-Flash | Cheapest, 150,000 requests a month | Qwen3.8 Flash |
| Documentation, SOPs, commit messages | `docs` | MiniMax M3.1 Flash Free | Free for a limited time | MiMo-V2.6-Flash |
| Arabic UI text and SOP drafts | `arabic` | Qwen3.7 Plus | Strong multilingual model; **a native Egyptian speaker reviews every string** | Qwen3.8 Max |
| Screenshots, Arabic RTL layout checks | `ui-check` | MiniMax M3 | Image input; 16,000 requests a month | Kimi K3 |
| Review of DeepSeek or Kimi code | `review-by-glm` | GLM-5.2 | Different vendor than the author | GLM-5.3 |
| Review of GLM code | `review-by-deepseek` | DeepSeek V4 Pro | Different vendor than the author | MiniMax M3 |
| **Critical review** (payments, deposits, `diva_guard`, authentication, backups, migrations) | outside OpenCode | Western-vendor model in its own tool (free Antigravity, Claude Pro, ChatGPT Plus) | Required before merging critical code | none |

Rules:
- The model that wrote the code never reviews it, and tests come from a different model than the implementation.
- Every critical pull request also gets the Western-vendor review.
- When a model's limit is reached: switch to its fallback, enable Extra usage, or continue on a free model.
- Free "limited time" models can disappear; check `opencode models` monthly.
- The week-1 bake-off (section 5) can change any assignment; record the change in `docs/12`.

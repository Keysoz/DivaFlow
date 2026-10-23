# Diva Build Specification v5.3 FINAL: Index

Date: 2026-10-22. Status: **final and build-ready.** Build order: P0, E (ERPNext), PUB (publishing), O, B, C, A, M, G. Supersedes every earlier plan. `Diva_Build_Spec_v5_3_FINAL.md` is the same content in one file.

## Start here
| File | Purpose |
|---|---|
| `../AGENTS.md` | Rules and Definition of Done for any coding agent |
| `../opencode.json` | The model assigned to each job |
| `15-agreed-scope-summary.md` | Plain-language list of what will and will not be done |
| `20-start-here.md` | How to start with the agent, first two weeks |
| `24-autopilot-setup.md` | VM, GitHub, OpenCode permissions; run tasks with the fewest manual steps |
| `23-opencode-step-by-step.md` | Detailed OpenCode setup, daily routine, quotas, troubleshooting |
| `17-agent-onboarding-package.md` | What the owner prepares first |
| `../tasks.csv` | Every task with ID, phase, dependencies and acceptance criteria |

## Design
| File | Content |
|---|---|
| `01-scope.md` | Business, users, channels, non-goals |
| `02-architecture.md` | Two-node topology, components, link-down behavior |
| `03-domain-data.md` | Entities, ownership, events |
| `04-business-rules.md` | The rules engine, rule by rule |
| `05-state-machines.md` | Order, payment, shipment, hold, shift |
| `05a-erp-configuration.md` | ERPNext simplification and configuration baseline |
| `19-localization-arabic-english.md` | Arabic and English on every surface |

## Modules
| File | Content |
|---|---|
| `06-modules-core.md` | Gateway, order engine, payments, Bosta, settings, auth |
| `07-modules-apps.md` | Ops, counter POS, Control Room, Telegram admin, Mini App |
| `08-modules-ai-channels.md` | Chat hub, AI agent, media, publishing, market monitor |
| `22-whatsapp-documents-and-broadcast.md` | Send invoices by WhatsApp; one-click broadcast |
| `14-feature-decision-matrix.md` | ERPNext, POS Next, legacy app and Diva Ops: who does what |

## Build, quality, operations
| File | Content |
|---|---|
| `09-build-plan.md` | Phases, task IDs, acceptance criteria, effort |
| `10-quality-security.md` | Test matrix, performance, security, observability |
| `18-owner-acceptance-scripts.md` | Plain-language acceptance steps for every gate |
| `21-ai-tooling-policy.md` | Models and tools, budget, data rules |
| `11-operations-cost.md` | Backups, runbooks, training, running cost |

## Reference
| File | Content |
|---|---|
| `12-decisions-open-items.md` | Decision log, open questions, assumptions, risks, change log |
| `13-legacy-app-review.md` | Review of the old `diva_store` app and retirement plan |
| `16-enhancement-backlog.md` | Accepted and deferred enhancements |
| `25-cost-savings.md` | Proposed ways to get the same features cheaper |

## ID conventions
`TASK-<phase>-<nn>` build tasks; `ENH-<area>-<nn>` enhancements; `I18N-<nn>` localization tasks; `RULE-<area>` business rules; `DEC-<nn>` decisions; `OPEN-<nn>` open owner questions; `TEST-<nn>` test cases.

## Glossary
- **Reseller:** wholesale customer who buys via chat or the Mini App.
- **Counter:** the physical store sales point, served by the store node.
- **Chat order:** order started in WhatsApp, Instagram, Facebook or the Mini App.
- **Cloud node / Store node:** the two deployments (`02-architecture.md`).
- **Gateway:** the `local-api` interface the cloud uses to reach ERPNext safely.
- **Reservation:** ERPNext stock reserved for a confirmed chat order.
- **Proof:** a record of a customer's claimed payment. It is not a verified payment.
- **Rule set version:** version of Settings under which an order was confirmed.
- **Link:** the secure tunnel between the cloud node and the store node.

# Sub-agent prompts

Four roles, two tiers. The orchestrator spawns them **only after the user has
explicitly agreed** (see the consent script below).

| File | Role | Tier | Phase |
|---|---|---|---|
| `creative-director.md` | generate names from a cluster | strongest reasoning | 1 |
| `name-editor.md` | refine, merge, kill weak names | strongest reasoning | 1b |
| `research-analyst.md` | SERP, stores, trademarks | fastest cheap | 3 |
| `geo-tester.md` | 6-prompt GEO battery | fastest cheap | 3 |

## Consent script (ask before any dispatch)

> "Je peux traiter cette étape en solo, ou en sous-agents : **N agents de
> création** sur le modèle le plus fort en raisonnement, **M agents de
> recherche** sur le modèle le plus rapide. Le mode sous-agents consomme plus de
> tokens et lance des agents en parallèle, mais il produit de meilleurs noms et
> des vérifications plus complètes. Je lance en sous-agents ?"

Wait for a clear yes. If the answer is no, or the harness has no sub-agent tool,
run the same phases sequentially with the current model. Never dispatch silently,
never re-ask in a loop.

## Resolving the tier to a model

Packets carry `model_tier: "creation"` or `"research"` with a `guidance` string,
never a model id. The orchestrator lists the available models and picks:

- **creation** → the model with the strongest reasoning capability available;
  prefer a larger/slower model over a fast one. Name it in your message.
- **research** → the fastest, cheapest model available that can follow a JSON
  schema. It only reads and copies; it does not judge.

Tell the user which models you picked before spawning. If only one model
exists, say so and run sequentially.

## Dispatch mechanics

```bash
python scripts/bom.py dispatch --phase 1 --clusters runs/acme/work/clusters.json --out runs/acme/packets
python scripts/bom.py dispatch --phase 3 --scores runs/acme/work/scores.json --top 10 --batch 3 --out runs/acme/packets
```

Each packet is a self-contained JSON: context, instructions, output schema,
acceptance criteria. Spawn one sub-agent per packet, pass the packet as the task
prompt, ask for **JSON only**.

Collect answers into `runs/acme/packets/results/*.json`, then:

```bash
python scripts/bom.py merge --inputs runs/acme/packets/results/*.json --out runs/acme/work/research.json
python scripts/bom.py score --audit runs/acme/work/audit.json --research runs/acme/work/research.json --out runs/acme/work/scores.json
```

The merge validates verdicts, rejects unknown names, keeps the first measurement
when two disagree, and warns about unverified trademarks. `score` then replaces
the SEO/GEO proxies with measured evidence and can disqualify a name outright.

## Failure handling

| Sub-agent returns | Orchestrator action |
|---|---|
| valid JSON, all `not_checked` | accept, report the gap, do not retry more than once |
| malformed JSON | one retry with the schema; then mark the batch `not_checked` |
| invented source / mark number | discard the whole result, log it, rerun on a different model |
| timeout | rerun once with `--batch 1` |

A declared gap is a result. Silence, invention or a cheerful "everything is
fine" is a failure — say so in the report.

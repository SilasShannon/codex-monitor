# Estimated API-equivalent cost

Codex Monitor never describes deterministic estimates as actual subscription
charges. The required label is **ESTIMATED API-EQUIVALENT COST**.

```text
fresh input cost = fresh input tokens × input rate / 1,000,000
cached read cost = cached input tokens × cached rate / 1,000,000
cache write cost = cache write tokens × cache-write rate / 1,000,000
output cost = output tokens × output rate / 1,000,000
```

The counterfactual without caching prices all inclusive input tokens at the
normal input rate. Estimated cache savings is that counterfactual minus the
API-equivalent estimate.

Unknown model pricing or missing token categories yields `UNAVAILABLE`; Codex
Monitor never substitutes another model. Decimal arithmetic avoids floating
point drift.

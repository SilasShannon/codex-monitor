# Pricing registry

Pricing is centralized in `codex_monitor/pricing/models.json`. Each record has
an exact model id, aliases, effective date, per-million rates, source URL, and
registry retrieval time. Calculations retain the source and effective date.

The bundled initial registry contains only models whose current prices were
verified from official OpenAI model documentation on 2026-08-10. Sessions
before that effective baseline remain unavailable until authoritative history
is added; current pricing is not silently projected backward.

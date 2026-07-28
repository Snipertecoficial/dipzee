"""Dipzee intelligence agents (L3).

Specialized pipelines over the ``AIProvider`` abstraction that compose the
deterministic substrate (knowledge graph + enriched market events + optional LSE
data) into plain-language, explainable insight for the client.

Cost discipline: the expensive per-headline NER already happened at correlation
time (cached in ``market_events``). The agents here assemble that cached,
deterministic context and make at most ONE LLM call per request to compose it —
never a chain of calls per asset view.
"""

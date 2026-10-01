from prometheus_client import Counter, Histogram

TRANSITIONS = Counter("raw_case_transitions_total", "Workflow transitions", ["from_status", "to_status"])
DECISION_READY_SECONDS = Histogram(
    "raw_decision_ready_seconds", "Submitted -> committee review elapsed seconds",
    buckets=(60, 600, 3600, 4 * 3600, 8 * 3600, 24 * 3600, 48 * 3600, 5 * 24 * 3600, 20 * 24 * 3600),
)
NODE_SECONDS = Histogram("raw_pipeline_node_seconds", "Assessment graph node duration", ["node"])
NODE_ERRORS = Counter("raw_pipeline_node_errors_total", "Graph node failures", ["node"])
LLM_CALLS = Counter("raw_llm_calls_total", "LLM calls", ["provider", "model", "node", "status"])
LLM_TOKENS = Counter("raw_llm_tokens_total", "LLM tokens", ["provider", "model", "node", "direction"])
LLM_CACHE_HITS = Counter("raw_llm_cache_hits_total", "LLM cache hits", ["node"])
LLM_FALLBACKS = Counter("raw_llm_fallbacks_total", "Fallbacks to deterministic provider", ["node", "reason"])
OVERRIDES = Counter("raw_overrides_total", "Human overrides of system output", ["target_type", "dimension"])
AI_FACTOR_DECISIONS = Counter("raw_ai_factor_reviews_total", "Analyst review of AI factor suggestions", ["result"])
CRITIC_UNSUPPORTED = Counter("raw_critic_unsupported_sentences_total", "Sentences flagged unsupported")

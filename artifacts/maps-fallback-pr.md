Live verification showed the doctor query still returned no list after relevance fixes. Support SerpAPI's documented place_results object and list-valued categories. When an exact doctor query genuinely returns no places, try hekim once in the same location and expose that fallback in candidate notes. Provider failures do not retry or become empty results. No score changes.

Validation: 123 backend tests pass, including single-place responses and bounded fallback success/empty scenarios.

Missing PageSpeed results previously persisted as zero and could raise opportunity scores as if a slow site had been measured. Missing speed, TLS and contact observations now remain unknown; real zero performance is retained.

Persist timestamped HTML observations (meta noindex, HTTP robots header presence, canonical, viewport, JSON-LD tag presence) and mobile Lighthouse LCP/CLS/TBT. Show a separate technical evidence panel and pass bounded observations to the audit prompt with explicit scope limitations. No ranking or AI visibility claims; no scoring formula changes or migrations. Existing audits remain unchanged until renewed.

Validation: 96 backend tests passed, TypeScript and targeted ESLint passed. Coverage includes failed fetches, non-HTML responses, missing API key, PSI error redaction, invalid/zero metrics, reversed HTML attribute order and crawler-specific directives.

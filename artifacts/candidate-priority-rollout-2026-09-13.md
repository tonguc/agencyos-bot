# Başvuru sıralaması — 2026-09-13

PR https://github.com/tonguc/agencyos-bot/pull/18
Production b53702b3094f8db8fe36c80d908170ec75df44f7

Profile criteria no longer discard prospects. Hospital/chain-name and already-strong hard rejection removed; review/site ICP mismatches retained as notes. Explicit permanentlyClosed remains visible at rank bottom with verification warning; generic isClosed does not imply permanent closure. Numeric scoring formula/weights otherwise unchanged.

Search cards display global rank, visible reason and score contributions, and a separate non-saving details toggle. Priority tabs replace Elendi. Merged searches preserve closure-last sorting. Redis/browser search cache keys versioned without deleting DB data.

Validation: 113 backend tests; TypeScript and targeted ESLint; merged order and dedup assertions. GitHub tests / Vercel / Railway success. Live diş hekimi büyükçekmece query returned 10 ranked records. Loradent (657 reviews) appeared at rank 4 instead of rejection, with the former 530-review threshold shown as context. Details button opened reasons without navigating or saving a candidate. Central Klinik name plus 800 reviews and good-site inclusion covered by regression fixture, not a claimed live Central Klinik search. No customer message sent.

Ranking remains preliminary using quick-search signals, not proven conversion probability; technical/Google/AI results are measured in audit. Geographic and query relevance filters and duplicate handling are unchanged.

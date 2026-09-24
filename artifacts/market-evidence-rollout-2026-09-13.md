# Market evidence rollout — 2026-09-13

PR https://github.com/tonguc/agencyos-bot/pull/15
Production commit 23844c1c2ee91c475f5207708f8f8f345fa7485d
108 backend tests, TypeScript and targeted ESLint passed. GitHub backend tests, Vercel and Railway deployment statuses success.

Each renewed audit collects separate brand and conservatively inferred local-service Google queries. Evidence includes exact normalized recorded-host organic rank among returned positions 1–10, Google AI Overview reference URLs and citation match, observed ads, query, country/language/device, provider location and timestamps. Unknown domains and shared platforms are not treated as negative matches. AIO absence, unavailable references and nonmatching citations are separate states. Token follow-ups are bounded; no provider error bodies or keys are logged or persisted.

Commercial assessment is a transparent qualification aid: observed own-domain ads plus verified technical need increase conversation priority. Historical review count is context only. No payment probability, income or solvency inference is made; budget and buying intent require a conversation. No existing Opportunity Score weights changed, no migrations, no customer messages sent.

Scope: Google AI Overview only; not ChatGPT/Perplexity/standalone Gemini. Two queries, at most four provider requests, 55-second market budget running alongside technical audit. SERPAPI_API_KEY required; missing configuration appears explicitly. Historical audits are not automatically rewritten. Query targets are inferred and should be checked for business relevance. Results may be cached and are point-in-time observations.

Provider documentation:
- https://serpapi.com/search-api
- https://serpapi.com/organic-results
- https://serpapi.com/google-ai-overview-api

## Live verification / follow-up releases
PR #16 (675c01ebccb877f4af13b7fc927111876843400e) adds safe actionable provider failure categories. Focused tests verify HTTP and payload error redaction.
The next production audit successfully measured the recorded domain sisliveterinerklinigi.com at organic position 2 for the brand query and 8 for the local-service query, with provider location Istanbul,Turkey. Own-domain ads were not observed. Service-query AI Overview was not returned; brand AI response was unavailable. Provider source timestamps showed cached results, which can carry expired one-minute AI tokens.
PR #17 (b118acf8c964efd1d5a031ce4bce32adc5b34f4e) requests fresh Google results and executes the two queries concurrently (40s request, 10s AI token follow-up, 55s aggregate bound). Maximum calls remains four; provider cache savings no longer assumed. Twelve focused tests passed, including concurrent barrier test. GitHub backend suite, Vercel and Railway all success. Existing scoring formula and weights remain unchanged.

Final live verification on b118acf8c964efd1d5a031ce4bce32adc5b34f4e completed successfully for Hilal Veteriner, audit measurement timestamp 2026-09-12T22:52:48 UTC. Both provider timestamps matched the current measurement. Brand query organic rank 2; local-service query rank 8. Brand Google AI Overview references contained https://sisliveterinerklinigi.com/ and the UI marked that exact URL as a match; the expanded source list was inspected. Service query returned no AI Overview (not a negative business-visibility claim). No own-domain ad was observed. Budget/buying intent stayed unknown; technical need shown as qualification signal. Final technical run: performance 60/100, LCP 7460.7 ms. No customer messages sent.

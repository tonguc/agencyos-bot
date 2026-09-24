# Teknik ölçüm geliştirmesi — 13 Eylül 2026

- PR: https://github.com/tonguc/agencyos-bot/pull/13
- Production commit: 00fe60db076cfb6a661dd1c9d71f98b8fd897aee
- GitHub backend tests / Vercel / Railway: success.
- Local: 96 backend tests, TypeScript, targeted ESLint passed.

Measured evidence is stored in audit.result._site_data.technical with a timestamp, page source URL and measurement status. New audit runs parse mobile Lighthouse performance/LCP/CLS/TBT and initial HTML noindex/canonical/viewport/JSON-LD tag presence. Failed speed requests remain null, preventing unmeasured speed from contributing the existing slow-site bonus. Failed page requests keep TLS/form/phone unknown. Existing score weights and all historical records are unchanged; renewed audits may produce different scores using current evidence.

Scope: initial HTML capped at 150,000 characters; no JS execution, whole-site crawl, robots.txt evaluation, schema validation, actual form submission, Google ranking or AI answer visibility test. HTTP robots header presence does not establish a specific crawler rule. No new API calls added; PAGESPEED_API_KEY remains required for speed metrics. No migrations.

Primary references:
- https://developers.google.com/speed/docs/insights/v5/reference/pagespeedapi/runpagespeed
- https://developers.google.com/search/docs/crawling-indexing/javascript/javascript-seo-basics
- https://developers.google.com/search/docs/crawling-indexing/robots-meta-tag

## Live verification and follow-up
The first production audit completed and displayed HTTP 200, mobile performance 64/100, LCP 7510.003 ms, CLS 0.048, TBT 0, and canonical/viewport/JSON-LD presence. This also exposed unsupported generated customer-loss and robots.txt claims despite prompt rules.

PR #14 https://github.com/tonguc/agencyos-bot/pull/14 replaces generated technical findings and first-contact copy with bounded measurement-derived statements. Existing AI scores are preserved and labeled as interpretation rather than measurement. Regression tests cover the live failure. 98 backend tests and TypeScript passed; GitHub tests, Vercel and Railway success for final production commit 87acae5b4c51a7ac1fe83814a801149d631f1a33.

The >4 second LCP threshold is used for a lab observation requiring real-device verification, not as proof of actual visitor behavior: https://web.dev/articles/lcp?hl=tr
Final live audit completed for Hilal Veteriner (f18f9097-3aa9-412a-a7ad-43e3df0621d8). Performance 64/100, LCP 6311.024 ms. The rendered insight and first-contact message now contain only the lab observation and a real-device verification proposal; invented patient-loss, robots.txt and schema-defect claims are absent. No customer message was sent.

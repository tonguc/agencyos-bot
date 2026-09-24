Public-hospital-linked healthcare records remain visible but route to LOW / Aktif satis disi with a zero sales priority and explicit record-based reason, including education/research hospitals. This routing does not claim verified employment or legal status. Private hospitals and hospital-street/nearby landmark addresses are not automatically excluded.

Apply routing after the existing score floor, including manual audit scoring; preserve it when attaching existing DB scores. Bump search caches. No database migration or bulk record edits. This change affects search/scoring, not a blanket prohibition on academic services or a message-send control.

Validation: 137 backend tests passed (DB integration suites excluded), TypeScript passed. Regression cases cover state/city/training hospitals, private hospitals, landmarks, nonmedical businesses, and stored high scores.

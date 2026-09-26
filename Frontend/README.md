# P2P control tower (frontend)

    npm install
    npm run dev        # http://localhost:5173

Requires the backend on http://localhost:8080. Vite proxies /api to it, so there
is no CORS setup and no API base URL to configure.

## Screens
- Pipeline board: invoices flowing through stages, live, with the metrics strip.
- Case detail (slide-over): extracted fields with confidence, the three-way match
  table, invoice vs PO vs GRN line comparison, the agent trace, the contractual
  ruling with its verbatim clause quote, and approve / reject.
- Alerts: duplicate clusters and unverified bank-account changes, with value at risk.

## Data flow
Polls `/api/invoices` and `/api/metrics` every 1.5s. Polling rather than a Firestore
listener is a deliberate trade: the Firebase web SDK needs its own project config and
security rules, which is 30 minutes of setup for a difference nobody can see on a
local demo. To switch later, replace `usePoll` in `src/api.js` with `onSnapshot` on
`cases` - nothing else changes.

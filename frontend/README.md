# PG / Hostel Management — Frontend (POC)

React (Create React App + CRACO, not Vite) + Tailwind CSS. Talks directly
to the `backend_poc` FastAPI app — no other backend changes needed.

## Setup

```bash
npm install
cp .env.example .env      # set REACT_APP_API_BASE_URL if the backend isn't on localhost:8000
npm start                 # dev server on http://localhost:3000
```

Make sure the backend (`uvicorn app:app --reload`) and MySQL are running
first — every page here calls a real endpoint on load.

```bash
npm run build              # production build -> build/
```

## Why CRACO instead of a plain CRA + Tailwind setup

Create React App doesn't let you customize its PostCSS pipeline without
either ejecting or using an override tool — that's the standard reason
Tailwind's own CRA guide recommends CRACO. `craco.config.js` just injects
the `tailwindcss`/`autoprefixer` PostCSS plugins into CRA's existing
webpack config; nothing else about CRA's behavior changes.

## Structure

```
src/
├── api/client.js          # axios instance + every backend call, one file
├── context/AuthContext.js # login/register/logout, JWT persisted in localStorage
├── components/            # Navbar, ProtectedRoute, Layout, ChatWidget, ui.js (Card/Button/Input/Table/...)
└── pages/
    ├── Login.js, Register.js
    ├── owner/OwnerDashboard.js   # list/create PGs
    ├── owner/PGDetail.js         # occupancy, assign manager, pending rents
    ├── manager/ManagerDashboard.js  # rooms/beds, residents, rent + collect payment (tabbed)
    └── resident/ResidentDashboard.js # own room, rent, payments, log a payment
```

## Demo flow (mirrors the backend README)

1. Register three accounts: one OWNER, one MANAGER, one RESIDENT (`/register`).
2. As OWNER: create a PG, note its ID from the card. Go into the PG,
   assign the manager by their **User ID** (each dashboard shows a "My ID"
   badge top-right — have the manager read theirs off their own screen).
3. As MANAGER: add a room, expand it to add a bed, then in the Residents
   tab attach the resident (again by their "My ID"), then in Rent &
   Payments create a rent record for them.
4. As MANAGER or RESIDENT: collect/log a payment against that rent record
   and watch the status flip PENDING → PARTIAL/PAID on both sides.
5. Open the chat bubble (bottom-right, any role) and ask something like
   "how many vacant rooms do I have" (owner/manager) or "what's my rent
   status" (resident) — the reply shows which backend tools it called.

## What's deliberately thin for POC

- No global state library — each page fetches what it needs on mount.
  Fine at this scale; move to React Query if the app grows past a demo.
- IDs (manager user ID, resident user ID, rent_record_id) are typed in by
  hand rather than picked from a searchable list, since the backend has
  no "list all users" endpoint yet. The "My ID" badge in the navbar exists
  specifically to make this workable in a live demo.
- No toast/notification system — success/error messages are inline text
  under each form.
- No pagination anywhere — fine for a handful of demo records.

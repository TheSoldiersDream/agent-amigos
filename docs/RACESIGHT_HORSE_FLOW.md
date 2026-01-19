# RaceSight Horse Tool — UI Flow + API Map

Date: 2026-01-14

This document maps **every user-visible button/flow** in the RaceSight horse console(s) to the backend endpoints they call, plus the expected payload shapes and failure modes.

## Components

### `frontend/src/components/RaceSightConsole.jsx`

A multi-tab “operator console” with multiple acquisition paths:

- **Step 1 (Live Scan)**: shows a _Next-To-Jump-style_ window derived from live providers
- **Live Schedule**: SSE-capable live schedule stream + actions (View Runners / Analyze)
- **Schedule**: track/global schedule list
- **Card**: race card extraction (track+rnum OR URL)
- **Analysis**: analysis output + navigation between races
- **Runners**: odds + runners table
- **Learning**: AI learning dashboard
- **Bookies**: bookmaker quick links

### `frontend/src/components/HorseAnalyticsConsole.jsx`

A compact “dashboard card” that always anchors on the next race and shows:

- next-to-jump list (derived client-side)
- top pick per race
- runners + odds
- /analyze/by-id summary + betting advice

## Canonical backend base URL

- Horse API: `http://127.0.0.1:65261`
- All endpoints below are under the `/horse` prefix.

## Canonical schedule source (LIVE ONLY)

### `GET /horse/live/schedule`

**Used by:** both consoles as the canonical live schedule source.

Query params:

- `race_types` (csv): e.g. `horse`
- `limit` (int)
- `force_refresh` (bool)

Response (shape):

```json
{
  "schedules": [
    {
      "race_id": "palmerbet:123",
      "provider": "palmerbet",
      "track": "Flemington",
      "race_number": 1,
      "race_type": "horse",
      "start_time": "2026-01-14T09:10:00Z"
    }
  ],
  "warnings": ["no_live_data_cached_yet"],
  "provider_enablement": {
    "amigos": { "enabled": false, "reason": "missing amigos_API_KEY" }
  },
  "provider_statuses": {
    "palmerbet": { "success": false, "message": "blocked" }
  }
}
```

Failure modes:

- empty schedules with `warnings` explaining why (live-only mode)
- 5xx/timeout if provider refresh is unhealthy

## Button → endpoint mapping

### `RaceSightConsole` — Control bar

- **Fetch**

  - If Track field contains URL: `GET /horse/discover/from-url?url=...` (then optionally `GET /horse/guide?url=...`)
  - Else: `GET /horse/schedule?track=...`

- **Update**

  - `GET /horse/schedule?track=...`

- **Live: On/Off**
  - Toggles SSE stream from:
    - `GET /horse/sse/schedules?race_types=horse&limit=150&poll_interval=...`
  - When enabled, UI switches to the **Live Schedule** panel.

### `RaceSightConsole` — Live Schedule panel

- **View Runners**

  - `GET /horse/race/{race_id}/runners`

- **Analyze**
  - `GET /horse/analyze/by-id?race_id=...`
  - Fallback (if race_id unsupported): `GET /horse/analyze/live?track=...&race_number=...`

### `RaceSightConsole` — Step 1 (Live Scan / Next-To-Jump)

- **Refresh**
  - re-fetches `GET /horse/live/schedule` (then derives “next-to-jump” client-side)

### `RaceSightConsole` — Schedule panel

- **Group/Listed Calendar**
  - `GET /horse/calendar`

### `RaceSightConsole` — URL flows

- **Discover from landing page**

  - `GET /horse/discover/from-url?url=...&limit=15`

- **Extract race card from URL**

  - `GET /horse/guide?url=...`

- **Analyze extracted race card**
  - `POST /horse/analyze` with a `RaceInput` payload

### `RaceSightConsole` — AI utilities

- **Scan Top Picks**

  - `GET /horse/predictions/top-picks`

- **Learning Dashboard**
  - `GET /horse/ai/learning-dashboard`

## Known “don’t get stuck” rules (timeouts)

Frontend enforces timeouts to prevent hung buttons:

- live schedule: 15s
- runners: 20s
- analysis: 45s
- URL extraction: 25s

## Debug checklist

1. Confirm Horse API is up: `GET /horse/health`
2. Confirm schedule populates: `GET /horse/live/schedule?race_types=horse&limit=50`
3. If empty, check `warnings` + `provider_enablement`
4. Validate a race_id works:
   - `GET /horse/race/{race_id}/runners`
   - `GET /horse/analyze/by-id?race_id=...`

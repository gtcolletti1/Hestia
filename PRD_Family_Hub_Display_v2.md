# Hestia — Product Requirements Document v2

> **Product name:** Hestia (formerly "Family Hub Display")
> **Version:** 2.1
> **Last updated:** 2026-05-03
> **Status:** Draft

---

## 1. Product Overview

### 1.1 Vision

Hestia is a self-hosted, wall-mounted family command center — a free, privacy-first alternative to commercial products like Skylight Calendar and Hearth Display. It runs on affordable hardware (NUC, Raspberry Pi, or any Docker host) with a touch display, giving families an always-on shared view of their schedules, routines, meals, lists, and memories without requiring a cloud subscription or sending data to third parties.

### 1.2 Target Users

| Persona | Needs | UI Mode |
|---------|-------|---------|
| **Parent / Guardian (Admin)** | Manage schedules, assign chores, configure integrations, set up routines and rewards | Full admin access; companion app/web on phone |
| **Child (age 5–12)** | See "what do I need to do now?", check off routine steps, earn points, browse reward store | Simplified, icon-heavy, large touch targets |
| **Teen (age 13+)** | View personal calendar, manage own lists, check chores | Standard UI with limited admin |
| **Caregiver / Grandparent** | At-a-glance view of today's schedule, who's where, meal plan | Read-only dashboard; optional PIN-free access |

### 1.3 Core Value Propositions

1. **Single source of truth** — one display shows every family member's calendar, chores, meals, and lists.
2. **Self-hosted and private** — all data stored locally; no subscriptions, no cloud dependency.
3. **Kid-friendly engagement** — visual routines with step-by-step checklists, points, streaks, and a rewards store make daily tasks motivating.
4. **Digital photo frame** — doubles as a family photo display when idle, showing memories on a configurable screensaver.
5. **Works offline** — calendar, routines, lists, and meals remain fully functional without internet; changes queue and sync when connectivity returns.

---

## 2. User Stories & Acceptance Criteria

### 2.1 Dashboard / Home Screen

> *"As a family member, I glance at the display and immediately know what's happening today."*

**US-2.1.1: Daily Overview**
- The home screen shows a greeting with the current date.
- Today's events are grouped into **Morning** (before 12pm), **Afternoon** (12–5pm), and **Evening** (after 5pm) buckets, color-coded by family member.
- **Done means:** with zero events, each bucket shows "Nothing scheduled." With events, each shows title, time, location, and the assigned person's color dot.

**US-2.1.2: Sidebar Widgets**
The right sidebar displays:
- ☀️ **Weather** — current conditions and high/low for today (requires location to be configured in settings).
- ✅ **Active Routines** — routines scheduled for today (matching `today ∈ days_of_week` AND `is_active = true`), showing name, time block, and step count.
- 🍽️ **Today's Meals** — meals planned for today by type (breakfast, lunch, dinner, snack).
- 📋 **Active Lists** — non-archived lists with item count and completion progress.
- 💬 **Messages** — most recent 3 pinned/latest notes.
- 🏆 **Leaderboard** — points leaders (only shown if any profile has points > 0).

**Done means:** all widgets render independently; one widget failing does not crash others. Empty widgets show a friendly empty state (not a blank space or error).

**US-2.1.3: Quick Actions**
- Tapping a widget navigates to the full-page view for that feature.
- A "+" floating action button (or similar) allows quick-adding events, notes, or list items without leaving the home screen.

### 2.2 Calendar

> *"As a parent, I see every family member's schedule in one color-coded view."*

**US-2.2.1: Calendar Views**
- **Day view:** timeline of events for the selected date.
- **Week view:** 7-day grid showing events for all visible profiles.
- **Month view:** traditional calendar grid with event dots/counts per day.
- **Agenda view:** scrolling list of upcoming events for the next 7 days (default on dashboard).

**US-2.2.2: Event Management**
- Create events with: title (required), start time, end time, location, description, assigned profile, source calendar, color, and all-day flag.
- Edit and delete events.
- Recurring events use RRULE (RFC 5545); the system expands occurrences for display and honors per-occurrence overrides via `RECURRENCE-ID` and exclusions via `EXDATE`.
- All-day and multi-day events render in a banner row above the timed grid in Day/Week views, and are repeated on every day they span.
- Events are filterable by profile and source calendar.

**US-2.2.3: External Calendar Sync**
- **Google Calendar:** OAuth 2.0 flow via admin settings. Select which Google calendars to sync. Two-way sync where permissions allow.
- **Apple/iCal:** subscribe via CalDAV URL or `.ics` feed (read-only). Lightweight `.ics` subscriptions require no OAuth.
- **Outlook/Exchange:** Microsoft Graph OAuth 2.0 (read-only initially, two-way in Phase 2).
- iCal `TZID` values are honored when expanding occurrences (no naive-UTC drift).
- Sync runs on a configurable interval (default: every 15 minutes via Celery beat).
- Last-synced timestamp displayed per calendar in admin settings.
- Sync failures are logged and retried (max 3 retries with exponential backoff).

**Done means:** a Google Calendar event created on a phone appears on the display within 15 minutes. A local event created on the display appears on the phone within 15 minutes (if two-way).

**US-2.2.4: Privacy Mode**
- When enabled, event details on the wall display are replaced with "Busy" and the person's color across the **Dashboard agenda, Calendar (Day/Week/Month/Agenda)**, and **Meals** views.
- Tapping an obscured item reveals details only after admin PIN entry; the reveal is scoped to the current view and clears on navigation away or screensaver.

### 2.3 Routines & Chores

> *"As a child, I see my morning routine as big, friendly steps I tap to check off."*

**US-2.3.1: Routine Definition**
A routine consists of:

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| name | string | ✓ | e.g., "Morning Routine" |
| time_block | enum | ✓ | morning, afternoon, evening, bedtime |
| days_of_week | int[] | ✓ | 0=Monday … 6=Sunday |
| start_time | time | ✗ | Optional specific time (e.g., 7:30 AM) |
| profile_id | UUID | ✗ | Assigned person (null = household-wide) |
| steps[] | RoutineStep[] | ✓ | At least one step |
| is_active | boolean | ✓ | Default true |

Each **step** has:

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| label | string | ✓ | e.g., "Brush teeth" |
| icon | string | ✗ | Emoji or icon identifier (curated emoji picker available in the editor) |
| points_value | integer | ✓ | Points earned on completion (0 = no points) |
| sort_order | integer | ✓ | Display order |

**US-2.3.2: Routine Execution**
- On the Routines page, active routines for today are grouped by time block.
- Tapping a routine opens a full-screen stepper with large touch targets (min 44×44px).
- Each step shows the icon, label, and a checkmark. Tapping marks it complete.
- Completing a step with `points_value > 0` immediately credits points to the logged-in profile's ledger.
- Points are **idempotent** per step per day — completing the same step again does not double-award.
- **Unchecking** a previously completed step does NOT refund points and does NOT permit re-awarding on subsequent re-check (no point farming).
- Completing all steps marks the routine as fully completed for that day.

**US-2.3.3: Streaks**
- A streak counts consecutive **scheduled days** (per `days_of_week`) where the routine was fully completed.
- Displayed on the routine card as "🔥 N-day streak."
- A missed scheduled day resets the streak to 0.

**US-2.3.4: Routine Management**
- Admin/parent profiles can create, edit, delete, and **duplicate** routines.
- Edit, delete, and duplicate actions are accessible from the routine list (edit pencil, trash, copy icons).
- Duplicating creates a deep copy (steps included) with " (copy)" appended to the name; the copy is independent and editable.
- Deleting a routine prompts confirmation and cascades to steps and completion history.
- **Routine templates:** a curated set of pre-built templates (Morning, After-School, Bedtime, Tidy-Up) is available from the "New routine" flow; selecting a template seeds name, time block, days, and steps which the admin can then customize.

**Done means:** a routine with days_of_week=[0,1,2,3,4] (weekdays) does NOT appear on the dashboard on Saturday/Sunday. A 5-point step completed by a child immediately shows +5 in their point balance.

### 2.4 Points & Rewards Store

> *"As a child, I earn points by completing chores and spend them on rewards my parents set up."*

**US-2.4.1: Points Ledger**
- Points are tracked per-profile in an append-only ledger.
- Entries have: profile_id, points (+/-), reason, optional routine_step_id or reward_id.
- Balance = SUM(points) for a profile within a household.
- Ledger is auditable — parents can see full history.

**US-2.4.2: Rewards Store**
- Admin profiles create rewards with: title, description, icon (emoji), points_cost, is_active.
- The rewards page shows available rewards with their cost.
- A profile can redeem a reward if their balance ≥ points_cost.
- Redemption deducts points (negative ledger entry) and records the reward_id.
- Inactive rewards are hidden from the store but preserved in history.

**US-2.4.3: Leaderboard**
- Shows all profiles ranked by total points (descending).
- Displayed as a dashboard widget and accessible as a full page.
- Medals (🥇🥈🥉) for top 3.

**Done means:** a child with 50 points can redeem a 50-point reward, balance becomes 0. A child with 49 points sees the 50-point reward but the redeem button is disabled.

### 2.5 Lists

> *"As a parent, I add groceries to the list from my phone; the display shows it immediately."*

**US-2.5.1: List Management**
- Create lists with: name, category (grocery, todo, packing, school, errands, other, custom), icon.
- Lists can be archived (hidden from dashboard but not deleted).
- Reorder lists by drag or sort_order.

**US-2.5.2: List Items**
- Add items with: text, optional assigned_profile_id, optional due_date.
- Toggle checked/unchecked with a single tap (touch-optimized checkbox).
- Reorder items by drag or sort_order.
- Delete items individually.

**US-2.5.3: Touch Optimization**
- On the wall display: large checkboxes (min 44px), swipe-to-delete.
- Fast-entry mode: text field auto-focuses, pressing Enter adds item and clears field for next entry.

**Done means:** checking an item on the wall display is reflected in the API within 1 second. Unchecking works the same way.

### 2.6 Meal Planning

> *"As a parent, I plan the week's dinners so the family knows what's for dinner tonight."*

**US-2.6.1: Meal Plans**
- Create meal entries with: date, meal_type (breakfast, lunch, dinner, snack), title, description, recipe_url, assigned_profile_id (who's cooking).
- **Constraint:** one entry per (household, date, meal_type). Editing replaces; user is warned, not silently blocked.
- View meals for today (dashboard widget) or the full week (weekly planner grid).

**US-2.6.2: Weekly View**
- 7-day grid (Mon–Sun) with rows per meal type.
- Tapping an empty cell opens the create form pre-filled with that date and meal type.
- Tapping a filled cell opens edit.

**Done means:** creating a "Tacos" dinner for Wednesday shows "Tacos" in the Wednesday/Dinner cell immediately.

### 2.7 Message Board / Family Notes

> *"As a parent, I leave a pinned note on the display: 'Soccer practice cancelled today!'"*

**US-2.7.1: Notes**
- Create notes with: title, body, color (from a palette), pinned flag, author_profile_id.
- Pinned notes appear first on the dashboard widget and the messages page.
- Notes show author name and timestamp.
- Edit and delete notes.

**US-2.7.2: Dashboard Integration**
- The Messages widget on the home screen shows up to 3 notes (pinned first, then newest).
- Tapping navigates to the full messages page.

**Done means:** a pinned note created by "Mom" shows 📌 icon, Mom's name, and appears at the top of both the widget and full page.

### 2.8 Photo Screensaver / Digital Frame

> *"When nobody's interacting with the display, it becomes a beautiful family photo frame."*

**US-2.8.1: Photo Management**
- Upload photos via the admin/photos page (file upload or URL).
- Photos have: url, caption (optional), sort_order.
- Delete photos.

**US-2.8.2: Screensaver Behavior**
- After N minutes of inactivity (configurable, default 5), the display enters screensaver mode.
- Photos cycle with a configurable transition interval (default 30 seconds).
- If no photos are configured, a Hestia hearth-flame splash is shown as a fallback.
- Touching the screen exits screensaver and returns to the last-viewed page.
- Entering the screensaver **auto-logs-out** the active profile; the next interaction lands on the profile selector.

**US-2.8.3: Settings**
- `screensaver_timeout_minutes`: 1–60 (default 5)
- `screensaver_transition_seconds`: 5–120 (default 30)

**Done means:** after 5 minutes idle, photos begin cycling (or the Hestia splash if none). Tapping the screen returns to the profile selector and requires re-auth.

### 2.9 Profiles & Authentication

> *"As a parent, I set up profiles for each family member with their own color and optional PIN."*

**US-2.9.1: Profile Management**
- Create profiles with: name, color (hex), avatar_url (optional), role (admin/standard).
- Admin profiles can manage all settings, integrations, and other profiles.
- Standard profiles can view everything and interact with routines, lists, and notes.
- Non-admin profiles can edit only their **own** profile (name, color, avatar, PIN); admin profiles can edit any.
- Profiles can be deactivated (soft delete) — hidden from UI but preserved in history.
- Avatars: when `avatar_url` is set, the ProfileSelector and header dropdown render the image; otherwise the first initial on the profile's color chip is shown.

**US-2.9.2: Authentication**
- Login by tapping a profile avatar on the login screen.
- **Admin profiles require a 4-digit PIN** (no empty/blank PIN allowed); creation and PIN changes always bcrypt-hash and persist server-side.
- Standard profiles may have an optional PIN (default: none for kids/caregivers).
- JWT Bearer tokens with configurable expiry; auth interceptor automatically logs out on 401 responses.
- A profile switcher dropdown in the header bar lets the active user switch profiles without returning to the login screen; the active profile is persisted across page refreshes.
- Entering the screensaver triggers an automatic logout (see US-2.8.2).

**US-2.9.3: Onboarding (Single-Household Appliance)**
- Hestia is a **single-household** appliance: exactly one household exists per deployment.
- First boot: the server exposes `/setup/discover` so the kiosk/companion device can locate the appliance on the LAN; the setup wizard then collects the household name and creates the **first admin profile with a required PIN** (PIN-on-create).
- Once a household exists, household-creation and unrestricted profile-creation endpoints are gated: only an authenticated admin can add subsequent profiles via the Profiles page (accessible from bottom nav).

**Done means:** a fresh appliance boots into the setup wizard via `/setup/discover`. The first profile created is admin and must set a PIN. Attempts to create a second household are rejected. A standard profile cannot edit another profile's record.

### 2.10 Weather Widget

> *"I glance at the display and see it's going to rain — I grab an umbrella."*

**US-2.10.1: Weather Display**
- Shows current conditions (icon, temperature, description) and today's high/low.
- Data fetched from **Open-Meteo** (no API key required).
- Requires location (latitude/longitude) configured in household settings; a "Use my location" button in settings auto-fills lat/lon via the browser Geolocation API.
- Refreshes every 30 minutes.
- Gracefully hidden when location is not configured (no error shown on dashboard).

**Done means:** with location configured, the weather widget shows current temp and conditions. Without location, the widget is simply not rendered (no error or blank box).

### 2.11 Notifications & Reminders

**US-2.11.1: Event Reminders**
- Create reminders tied to calendar events: minutes_before (default 15).
- Celery beat checks for upcoming reminders and fires them at the correct time.
- Fired reminders are marked `is_fired = true` (no duplicates).

**US-2.11.2: Upcoming Notifications**
- API endpoint returns notifications due in the next 24 hours.
- Dashboard could show a notification bell with count (Phase 2).

---

## 3. Admin & Configuration

### 3.1 Household Settings

Stored as a JSON object on the household record:

```json
{
  "screensaver_timeout_minutes": 5,
  "screensaver_transition_seconds": 30,
  "modules_enabled": {
    "calendar": true,
    "routines": true,
    "lists": true,
    "meals": true,
    "messages": true,
    "photos": true,
    "rewards": true,
    "weather": true
  },
  "theme": "system",
  "accent_color": "#3b82f6",
  "privacy_mode": false,
  "weather_lat": null,
  "weather_lon": null,
  "weather_units": "imperial",
  "timezone": "America/New_York",
  "time_format": "12h"
}
```

The household `timezone` (IANA name) is the **primary source of truth** for date-bucketing on the dashboard agenda, routine "today" matching, and meal-plan "today" lookups. `time_format` controls 12h/24h rendering throughout the UI.

### 3.2 Module Toggles

- Each feature module can be enabled/disabled from admin settings.
- Disabled modules are hidden from navigation and the dashboard.
- **Done means:** disabling "meals" hides the Meals nav item and removes the Meals widget from the dashboard.

### 3.3 Theming

- Light mode, dark mode, or system-follow.
- Configurable accent color.
- High contrast readability for wall-mount viewing distance (~3–6 feet).

---

## 4. Data Model Reference

### 4.1 Core Entities

```
Household
├── Profile (name, color, avatar_url, role, pin_hash)
├── SourceCalendar (provider, external_id, is_read_only, is_visible)
│   └── Event (title, start_time, end_time, location, recurrence_rule, all_day)
│       └── Reminder (minutes_before, fire_at, is_fired)
├── Routine (name, time_block, days_of_week[], start_time, is_active)
│   ├── RoutineStep (label, icon, points_value, sort_order)
│   └── RoutineCompletion (profile_id, date, completed_steps[], is_fully_completed)
├── TaskList (name, category, is_archived)
│   └── ListItem (text, is_checked, assigned_profile_id, due_date)
├── MealPlan (date, meal_type, title, description, recipe_url)
├── Note (title, body, color, pinned, author_profile_id)
├── Photo (url, caption, sort_order)
├── Reward (title, description, points_cost, icon, is_active)
├── PointLedger (profile_id, points, reason, routine_step_id?, reward_id?)
├── OAuthCredential (provider, access_token, refresh_token, token_expiry)
└── SyncQueueItem (entity_type, entity_id, action, status, retry_count)
```

### 4.2 Key Enums

| Enum | Values |
|------|--------|
| ProfileRole | admin, standard |
| CalendarProvider | local, google, apple, microsoft |
| TimeBlock | morning, afternoon, evening, bedtime |
| MealType | breakfast, lunch, dinner, snack |
| ListCategory | grocery, todo, packing, school, errands, other, custom |
| SyncAction | create, update, delete |
| SyncStatus | pending, processing, completed, failed |

### 4.3 Key Constraints

- `RoutineCompletion`: unique on (routine_id, profile_id, date) — one completion record per person per day.
- `MealPlan`: unique on (household_id, date, meal_type) — one meal per type per day.
- `PointLedger`: append-only, no updates or deletes.
- All UUIDs are v4, generated client-side or server-side.
- All timestamps are **naive UTC** (`TIMESTAMP WITHOUT TIME ZONE`) in PostgreSQL. Frontend and "today"-bucket logic convert to the household timezone (see §3.1) for display.

---

## 5. API Contract Summary

### 5.1 Authentication
| Method | Endpoint | Notes |
|--------|----------|-------|
| POST | `/api/auth/login` | Body: `{profile_id, pin}` → `{access_token, profile}` |
| POST | `/api/auth/pin` | Set/change PIN for current profile |
| GET | `/api/auth/me` | Current profile info |

### 5.2 Resources
| Resource | List | Get | Create | Update | Delete |
|----------|------|-----|--------|--------|--------|
| Profiles | `GET /profiles` | `GET /profiles/:id` | `POST /profiles` | `PUT /profiles/:id` | `DELETE /profiles/:id` |
| Calendars | `GET /calendars` | — | `POST /calendars` | `PUT /calendars/:id` | `DELETE /calendars/:id` |
| Events | `GET /events` | `GET /events/:id` | `POST /events` | `PUT /events/:id` | `DELETE /events/:id` |
| Routines | `GET /routines` | `GET /routines/:id` | `POST /routines` | `PUT /routines/:id` | `DELETE /routines/:id` |
| Lists | `GET /lists` | `GET /lists/:id` | `POST /lists` | `PUT /lists/:id` | `DELETE /lists/:id` |
| List Items | (nested) | — | `POST /lists/:id/items` | `PUT /lists/:id/items/:id` | `DELETE /lists/:id/items/:id` |
| Meals | `GET /meals` | `GET /meals/:id` | `POST /meals` | `PUT /meals/:id` | `DELETE /meals/:id` |
| Notes | `GET /notes` | — | `POST /notes` | `PUT /notes/:id` | `DELETE /notes/:id` |
| Photos | `GET /photos` | — | `POST /photos` | `PUT /photos/:id` | `DELETE /photos/:id` |
| Rewards | `GET /rewards` | — | `POST /rewards` | `PUT /rewards/:id` | `DELETE /rewards/:id` |
| Reminders | `GET /reminders` | — | `POST /reminders` | — | `DELETE /reminders/:id` |

### 5.3 Special Endpoints
| Method | Endpoint | Notes |
|--------|----------|-------|
| GET | `/api/dashboard` | Composite read-only endpoint (profiles, agenda, routines, meals, lists) |
| POST | `/api/routines/:id/complete-step` | Body: `{step_id, profile_id}` — idempotent |
| GET | `/api/routines/:id/streak` | Returns current and longest streak |
| GET | `/api/routines/active` | Routines active for today |
| POST | `/api/rewards/redeem` | Body: `{reward_id, profile_id, household_id}` |
| GET | `/api/rewards/leaderboard` | Points ranking for household |
| GET | `/api/rewards/points` | Balance for a profile |
| GET | `/api/meals/week` | Weekly meal grid |
| PATCH | `/api/lists/:id/items/:id/toggle` | Toggle checked state |
| GET | `/api/weather` | Proxied weather data |
| GET | `/api/notifications/upcoming` | Reminders due in next 24h |
| GET/PUT | `/api/admin/settings` | Household settings JSON |
| PATCH | `/api/admin/modules` | Enable/disable modules |

---

## 6. Architecture

### 6.1 Stack

| Layer | Technology | Notes |
|-------|-----------|-------|
| Frontend | React 18+ / TypeScript / Vite | SPA with TanStack Query, Zustand, Tailwind CSS |
| Backend | Python / FastAPI | Async with SQLAlchemy 2.0 |
| Database | PostgreSQL 15+ | Primary data store |
| Cache/Queue | Redis + Celery | Background sync jobs, reminders |
| Reverse Proxy | Nginx | TLS termination, static assets, API proxy |
| Containerization | Docker Compose | All services in one `docker-compose.yml` |

### 6.2 Service Topology

```
┌──────────────┐
│   Browser     │  ← Kiosk mode on wall display, or phone/laptop
└──────┬───────┘
       │ :80/:443
┌──────▼───────┐
│    Nginx      │  ← Reverse proxy, TLS, static cache
├──────┬───────┤
│  /api/*       │──► Backend (FastAPI :8000)
│  /ws/*        │──► Backend (WebSocket)
│  /*           │──► Frontend (Nginx :80 internal)
└──────────────┘
       │
┌──────▼───────┐     ┌─────────────┐
│   Backend     │────►│  PostgreSQL  │
│  (FastAPI)    │     └─────────────┘
│               │────►│    Redis     │
└──────┬───────┘     └──────┬──────┘
       │                     │
┌──────▼───────┐     ┌──────▼──────┐
│ Celery Worker │     │ Celery Beat  │
│ (sync, remind)│     │ (scheduler)  │
└──────────────┘     └─────────────┘
```

### 6.3 Key Design Decisions

- **Backend port (8000) is NOT exposed to the host** — all traffic goes through Nginx.
- **Timestamps are naive UTC** in the database. The frontend handles timezone conversion.
- **index.html is served with `Cache-Control: no-cache`** so deploys are picked up immediately. Hashed asset filenames use long-lived immutable cache.
- **JWT auth with no session server-side** — stateless API.
- **Points ledger is append-only** — no edits, full audit trail.
- **Offline queue** — `SyncQueueItem` stores pending changes for external calendar sync.

---

## 7. Non-Functional Requirements

### 7.1 Performance
- Dashboard loads in under 1 second on local network.
- Touch interactions respond in under 100ms.
- Calendar sync completes within 30 seconds per source calendar.

### 7.2 Reliability
- Database healthchecks on all services; `restart: unless-stopped`.
- Celery retries sync failures with exponential backoff (max 3 retries).
- Database migrations via Alembic — Alembic is the **single source of truth** for schema; no manual SQL or `create_all()` in production.

### 7.3 Accessibility / Touch UX
- All interactive elements are minimum 44×44px (WCAG touch target).
- High contrast text (4.5:1 ratio minimum).
- Designed for 1080p landscape display at 3–6 foot viewing distance.
- Minimal text input — prefer taps, toggles, and pre-filled options.

### 7.4 Security
- All data stored locally (PostgreSQL on Docker volume).
- HTTPS/TLS for external API calls.
- OAuth tokens encrypted at rest via an `EncryptedString` SQLAlchemy `TypeDecorator` (application-level encryption).
- PINs stored as bcrypt hashes.
- No data sent to third parties except explicit calendar sync providers.

### 7.5 Backup & Recovery
- Database backup via `pg_dump` (manual or cron).
- Photo storage on Docker volume (mountable to host for backup).
- Export/import household data as JSON (Phase 2).

---

## 8. Edge Cases & Empty States

Every screen must handle these gracefully:

| Screen | Zero-data state | Display |
|--------|----------------|---------|
| Dashboard agenda | No events today | "Nothing on the calendar today — enjoy!" |
| Dashboard routines widget | No routines for today | "No routines today" (not "No routines set up yet" if routines exist for other days) |
| Dashboard meals widget | No meals planned | "No meals planned for today" with "+" to add |
| Dashboard messages | No notes | Widget hidden entirely |
| Dashboard leaderboard | No points earned | Widget hidden entirely |
| Dashboard weather | Location not configured | Widget hidden entirely (no error) |
| Routines page | No routines created | "Create your first routine" with prominent button |
| Routine with 0 steps | Prevented by validation | API rejects routines with empty steps[] |
| Lists page | No lists | "Create your first list" |
| Rewards store | No rewards or 0 balance | "No rewards available yet" / Show balance as 0 |
| Calendar | No events in range | "No events this [day/week/month]" |
| Profiles | Only 1 profile | Normal operation; leaderboard hidden |

---

## 9. Release Phases

### Phase 1 — MVP (Current)
- [x] Local web app with dashboard, profiles, routines, lists, meals, notes
- [x] Local calendar with day/week/month views and recurring events (RRULE, including `RECURRENCE-ID` overrides and `EXDATE`)
- [x] All-day & multi-day event banner row above the timed grid
- [x] Read-only Google Calendar sync (OAuth 2.0)
- [x] Lightweight `.ics` calendar subscriptions (no OAuth)
- [x] Kid-friendly routine stepper with points, streaks, and anti-farming on uncheck
- [x] Routine duplication and pre-built templates (morning/after-school/bedtime/tidy-up)
- [x] Curated emoji picker for routine step icons
- [x] Rewards store with point redemption and leaderboard
- [x] Photo screensaver with configurable timeout/transition and Hestia splash fallback
- [x] Auto-logout on screensaver entry
- [x] Message board with pinned notes
- [x] Weather widget (Open-Meteo, geolocation autofill)
- [x] Admin settings (theme, modules, screensaver, privacy mode, timezone, 12h/24h)
- [x] Privacy mode across Dashboard, Calendar, and Meals with PIN-gated reveal
- [x] PIN-based authentication; admin PIN required; PIN-on-create
- [x] Single-household appliance with `/setup/discover` boot flow
- [x] Profile switcher in header; active profile persists across refreshes
- [x] OAuth tokens encrypted at rest (EncryptedString TypeDecorator)
- [x] Docker Compose deployment
- [x] Touch-friendly AM/PM time picker

### Phase 2 — Multi-Service Sync & Polish
- [ ] Two-way Google Calendar sync (write-back)
- [ ] Apple Calendar (CalDAV) and Outlook (Microsoft Graph) sync
- [ ] PWA with offline support and install prompt
- [ ] Push notifications to companion devices
- [ ] Drag-and-drop reordering for list items and routine steps
- [ ] Photo integration with Google Photos album
- [ ] Export/import household data (JSON backup)
- [ ] Chore assignment per profile (not just household-wide)
- [ ] Notification bell on dashboard with badge count

### Phase 3 — Automation & Intelligence
- [ ] Home Assistant integration (webhooks, REST sensor)
- [ ] Smart routine suggestions based on completion patterns
- [ ] Photo-to-calendar: snap a school flyer → extract event (OCR/AI)
- [ ] Email-to-calendar: forward an invite → auto-create event
- [ ] Todoist / Microsoft To Do integration for lists
- [ ] Family mood check-in widget
- [ ] Voice command support (optional microphone)
- [ ] Multi-household support
- [ ] Analytics dashboard (busy times, chore completion rates)

---

## 10. Glossary

| Term | Definition |
|------|-----------|
| **Household** | A family unit; the top-level (and, in this single-household appliance, only) tenant. All data is scoped to a household. |
| **Profile** | A person within a household (parent, child, caregiver). |
| **Source Calendar** | A calendar feed (local or synced from Google/Apple/Outlook). |
| **Time Block** | A named period of the day (morning, afternoon, evening, bedtime) used to group routines. |
| **Routine** | A named sequence of steps tied to specific days and a time block. |
| **Streak** | Consecutive scheduled days with full routine completion. |
| **Point Ledger** | Append-only log of point credits (from routine steps) and debits (from reward redemptions). |
| **Sync Queue** | Pending outbound changes for external calendar providers, processed when connectivity is available. |
| **Kiosk Mode** | Browser launched in fullscreen without address bar, used for the wall display. |
| **Privacy Mode** | Setting that hides event details on the display, showing only "Busy." |

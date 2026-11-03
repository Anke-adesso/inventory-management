# CLAUDE.md

Factory Inventory Management System Demo with GitHub integration - Full-stack application with Vue 3 frontend, Python FastAPI backend, and in-memory mock data (no database).

> ⚠️ **This repository and any fork you create are PUBLIC.** Do not commit credentials, internal hostnames, or private registry URLs. `client/.npmrc` pins the public npm registry and `client/package-lock.json` is gitignored to prevent locally-configured registries from leaking into commits — leave both in place.

## Critical Tool Usage Rules

### Subagents
Use the Agent tool with these specialized subagents for appropriate tasks:

- **vue-expert**: Use for Vue 3 frontend features, UI components, styling, and client-side functionality
  - Examples: Creating components, fixing reactivity issues, performance optimization, complex state management
  - **MANDATORY RULE: ANY time you need to create or significantly modify a .vue file, you MUST delegate to vue-expert**
- **code-reviewer**: Use after writing significant code to review quality and best practices
- **security-auditor**: Use before committing changes that touch input handling, config, or dependencies
- **Explore**: Use for understanding codebase structure, searching for patterns, or answering questions about how components work
- **general-purpose**: Use for complex multi-step tasks or when other agents don't fit

### Skills
- **backend-api-test** skill: Use when writing or modifying tests in `tests/backend` directory with pytest and FastAPI TestClient

### MCP Tools
- **ALWAYS use GitHub MCP tools** (`mcp__github__*`) for ALL GitHub operations
  - Exception: Local branches only - use `git checkout -b` instead of `mcp__github__create_branch`
- **ALWAYS use Playwright MCP tools** (`mcp__playwright__*`) for browser testing
  - Test against: `http://localhost:3000` (frontend), `http://localhost:8001` (API)

## Stack
- **Frontend**: Vue 3 + Composition API + Vite (port 3000)
- **Backend**: Python FastAPI (port 8001)
- **Data**: JSON files in `server/data/` loaded via `server/mock_data.py`

## Quick Start

```bash
# Backend
cd server
uv run python main.py

# Frontend
cd client
npm install && npm run dev
```

## Testing

```bash
cd tests
uv run --project ../server pytest -v   # tests/ has no own project; deps live in server/
```

- Backend only: pytest + FastAPI TestClient in `tests/backend/`
- **No frontend test suite** (the client has no test script). Verify frontend changes in the browser via Playwright MCP against `http://localhost:3000`

## Working Conventions

- Always document non-obvious logic changes with comments: explain *why*, not *what*
- Prefer the smallest correct change over a rewrite unless a rewrite is explicitly requested
- Tests and error handling are part of the change; if skipped, state why
- If existing code does something questionable, flag it once, then work within it unless asked to fix it

## Key Patterns

**Filter System**: 4 filters (Time Period, Warehouse, Category, Order Status) apply to all data via query params
**Data Flow**: Vue filters → `client/src/api.js` → FastAPI → In-memory filtering → Pydantic validation → Computed properties
**Reactivity**: Raw data in refs (`allOrders`, `inventoryItems`), derived data in computed properties
**Shared Filter State**: Singleton refs in `client/src/composables/useFilters.js` - use it, don't duplicate filter state per view
**i18n**: Custom `useI18n` composable with `client/src/locales/en.js` and `ja.js`. All user-facing strings go through `t()` and must be added to **both** locale files - no hardcoded UI text

## API Endpoints
- `GET /api/inventory` - Filters: warehouse, category
- `GET /api/inventory/{item_id}` - Single item
- `GET /api/orders` - Filters: warehouse, category, status, month
- `GET /api/orders/{order_id}` - Single order
- `GET /api/dashboard/summary` - All filters
- `GET /api/demand`, `/api/backlog` - No filters
- `GET /api/spending/*` - Summary, monthly, categories, transactions
- `GET /api/reports/quarterly`, `/api/reports/monthly-trends` - Filters: warehouse, category, status, month

## Common Issues
1. Use unique keys in v-for (not `index`) - use `sku`, `month`, etc.
2. Validate dates before `.getMonth()` calls
3. Update Pydantic models when changing JSON data structure
4. Inventory filters don't support month (no time dimension)
5. Revenue goals: $800K/month single, $9.6M YTD all months

## File Locations
- Views: `client/src/views/*.vue`
- Components: `client/src/components/` (detail modals, `FilterBar`, `LanguageSwitcher`)
- Composables: `client/src/composables/` (`useFilters`, `useI18n`, `useAuth`)
- Locales: `client/src/locales/{en,ja}.js`
- Utils: `client/src/utils/currency.js`
- API Client: `client/src/api.js`
- Backend: `server/main.py`, `server/mock_data.py`
- Data: `server/data/*.json`
- Styles: `client/src/App.vue`
- Tests: `tests/backend/`

Detailed per-side guidance lives in `client/CLAUDE.md` and `server/CLAUDE.md` - keep it there, not here.

## Design System
- Tokens: `client/src/styles/theme.css` is the single source for color, spacing, radius, shadow and type (`--color-*`, `--space-*`, ...). Use tokens, not hex values, in new or touched styles
- Colors: Slate/gray neutrals (#0f172a, #64748b, #e2e8f0) with a mauve accent (#8E4A55) for active nav, primary buttons, links and focus
- Status: green/blue/yellow/red
- Layout: left sidebar (collapsible to icons-only, drawer on mobile), slim top bar, sticky FilterBar in the content column. Nav items live in `client/src/config/navigation.js`
- Icons: `lucide-vue-next`
- Charts: Custom SVG, CSS Grid for layouts
- No emojis in UI

# AI-First CRM — HCP Interaction Management Platform

An AI-powered CRM application built for pharmaceutical field representatives to log, manage, and analyze interactions with Healthcare Professionals (HCPs). The platform combines structured data entry with a conversational AI assistant powered by a LangGraph agent running on Groq (Llama 3.1 8B).

---

## Table of Contents

- [Overview](#overview)
- [Tech Stack](#tech-stack)
- [Architecture](#architecture)
- [Features](#features)
- [Pages & Routes](#pages--routes)
- [AI Agent System](#ai-agent-system)
- [API Endpoints](#api-endpoints)
- [Database Models](#database-models)
- [State Management](#state-management)
- [Authentication](#authentication)
- [Real-Time Features](#real-time-features)
- [Styling & UI](#styling--ui)
- [Installation](#installation)
- [Environment Variables](#environment-variables)
- [Deployment](#deployment)
- [Project File Structure](#project-file-structure)

---

## Overview

Pharmaceutical field representatives visit dozens of HCPs daily. Traditional interaction logging is manual, unstructured, and time-consuming. This CRM solves that by providing:

- **Dual interaction logging** — structured form or natural language AI chat
- **6 core AI tools** — Edit, Summarize, Search, Follow-up Recommendation, Delete, and Log Interaction
- **Rich dashboard** — real-time stats, charts, follow-up tracking via WebSocket
- **Full CRUD** — create, read, update, delete interactions with search, sort, and pagination
- **AI-powered insights** — sentiment analysis, meeting classification, follow-up recommendations, entity extraction, summarization

---

## Tech Stack

### Frontend

| Library         | Version | Purpose                  |
| --------------- | ------- | ------------------------ |
| React           | 19      | UI framework             |
| Vite            | 5.4     | Build tool & dev server  |
| Redux Toolkit   | 2.2     | State management         |
| React Router    | 6.26    | Client-side routing      |
| Tailwind CSS    | 3.4     | Utility-first styling    |
| Framer Motion   | 11.3    | Animations & transitions |
| React Hook Form | 7.53    | Form validation          |
| Recharts        | 2.12    | Charting library         |
| Axios           | 1.7     | HTTP client              |
| Lucide React    | 0.441   | Icon library             |
| React Hot Toast | 2.4     | Toast notifications      |

### Backend

| Library                      | Purpose                    |
| ---------------------------- | -------------------------- |
| Python FastAPI               | Async web framework        |
| SQLAlchemy                   | ORM & database abstraction |
| Alembic                      | Database migrations        |
| psycopg                      | PostgreSQL adapter         |
| Pydantic / Pydantic Settings | Data validation & settings |
| python-jose                  | JWT token handling         |
| bcrypt                       | Password hashing           |
| Uvicorn                      | ASGI server                |

### AI / LLM

| Library        | Purpose                             |
| -------------- | ----------------------------------- |
| LangGraph      | Agent orchestration (StateGraph)    |
| LangChain      | LLM framework                       |
| LangChain-Groq | Groq API integration                |
| Groq API       | LLM provider (Llama 3.1 8B Instant) |

### Database

| Environment | Database             |
| ----------- | -------------------- |
| Development | SQLite (`ai_crm.db`) |
| Production  | PostgreSQL (Neon)    |

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                        FRONTEND (React)                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐ │
│  │Dashboard │  │Log Inter.│  │  Chat    │  │  History / Edit  │ │
│  │  Page    │  │  Page    │  │Assistant │  │     Pages        │ │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────────┬─────────┘ │
│       │              │              │                 │           │
│       └──────────────┴──────────────┴─────────────────┘           │
│                              │ Axios + WebSocket                  │
└──────────────────────────────┼───────────────────────────────────┘
                               │
┌──────────────────────────────┼───────────────────────────────────┐
│                        BACKEND (FastAPI)                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐ │
│  │  Auth    │  │Interact. │  │Dashboard │  │  Conversations   │ │
│  │ Router   │  │ Router   │  │ Router   │  │     Router       │ │
│  └──────────┘  └────┬─────┘  └──────────┘  └──────────────────┘ │
│                      │                                           │
│              ┌───────┴────────┐                                  │
│              │  AI Chat Router │                                  │
│              └───────┬────────┘                                  │
│                      │                                           │
│  ┌───────────────────┴───────────────────────────────────────┐   │
│  │              LANGGRAPH AGENT (StateGraph)                 │   │
│  │  ┌─────────────┐  ┌──────────────┐  ┌────────────────┐  │   │
│  │  │detect_intent│→ │route_intent  │→ │  14 Tool Nodes │  │   │
│  │  └─────────────┘  └──────────────┘  └────────────────┘  │   │
│  └───────────────────────────────────────────────────────────┘   │
│                      │                                           │
│  ┌──────────┐  ┌─────┴────┐  ┌──────────┐                      │
│  │  Models  │  │ Services │  │ WebSocket│                      │
│  │ (SQLAlch)│  │          │  │ Manager  │                      │
│  └──────────┘  └──────────┘  └──────────┘                      │
│                                                                 │
│              ┌──────────────────────────────┐                   │
│              │   SQLite / PostgreSQL (DB)    │                   │
│              └──────────────────────────────┘                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Features

### Core Features

- Dual interaction logging — structured form with 10+ fields OR AI chat
- Full CRUD for interactions (create, read, update, delete)
- Search, filter, sort, and paginated interaction history
- Dashboard with stats cards, weekly activity chart, recent activities, upcoming follow-ups
- JWT authentication with register/login/profile
- Dark mode / light mode toggle (persisted in localStorage)
- Responsive design across desktop, tablet, and mobile

### AI Features

- **6 Core AI Tools:**
  - **Edit** — Update interactions via natural language commands
  - **Summarize** — Generate 150-word CRM summaries from meeting notes
  - **Search** — Find interactions using natural language queries
  - **Follow-up Recommendation** — Get talking points, priority, and suggested products for next visit
  - **Delete** — Remove interactions with two-phase confirmation flow
  - **Log Interaction** — Stepwise extraction, asks one question at a time for missing fields
- Medical entity extraction (doctors, hospitals, medicines, diseases, symptoms)
- Sentiment analysis with confidence scores and engagement metrics
- Meeting classification (type, effectiveness, next action)
- Dashboard stats via natural language queries
- Conversation title auto-generation

### UI Features

- Rich AI message formatting (emoji headers, checkmarks, bullets, numbered lists)
- Animated typing indicator (bouncing dots)
- Quick action buttons for common tasks
- Success banners with "View Record" navigation
- Loading skeletons and error states with retry
- Toast notifications for all operations
- Confirmation dialogs for destructive actions
- Collapsible sidebar navigation
- Glassmorphism card effects

### Real-Time

- WebSocket connection for live dashboard updates
- Automatic reconnection with exponential backoff
- 30-second polling fallback
- "Last updated" timestamp display

---

## Pages & Routes

| Route                    | Page                | Description                                                                                                                                                                                                                                                                                         |
| ------------------------ | ------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `/`                      | Dashboard           | Stats cards (total HCPs, interactions today, pending follow-ups, weekly meetings), weekly activity bar chart, recent activities list, upcoming follow-ups. Auto-refreshes via WebSocket.                                                                                                            |
| `/log-interaction`       | Log Interaction     | Two tabs: **Structured Form** (react-hook-form with doctor name, hospital, speciality, date, duration, type, products, competitors, interest level, follow-up date, discussion notes) and **AI Conversation** (chat with quick actions, typing indicator, success banner, rich message formatting). |
| `/history`               | Interaction History | Paginated, sortable, searchable table of all interactions. Inline delete with confirmation.                                                                                                                                                                                                         |
| `/interactions/:id`      | Interaction Details | Full detail view of a single interaction with all fields in a card grid. Edit and Delete buttons.                                                                                                                                                                                                   |
| `/interactions/:id/edit` | Edit Interaction    | Pre-populated form to update summary, discussion, products, competitors, sentiment, interest level, follow-up date, and duration.                                                                                                                                                                   |
| `/chat`                  | Chat Assistant      | Full-page AI conversation panel with ChatSidebar (conversation history grouped by Today/Yesterday/Last 7 Days/Older), message history grouped by date, typing indicator, success banner, 8 quick action buttons.                                                                                    |
| `/settings`              | Settings            | Profile card with initials avatar, dark mode toggle, sign-out button.                                                                                                                                                                                                                               |
| `/login`                 | Login               | Email/password sign-in with show/hide password toggle and error display.                                                                                                                                                                                                                            |
| `/register`              | Register            | Name, email, password, role registration form.                                                                                                                                                                                                                                                      |
| `*`                      | 404                 | Not found page with gradient background and "Go Home" link.                                                                                                                                                                                                                                         |

---

## AI Agent System

### LangGraph Agent Architecture

The AI agent is a **LangGraph StateGraph** with 14+ nodes, featuring 6 core tools. When a user sends a message, the agent:

1. **Detects intent** — LLM classifies the message into one of 11 intent categories
2. **Routes to the correct tool node** — based on detected intent
3. **Executes the tool** — calls LLM for extraction/analysis, queries the database, saves results
4. **Returns a formatted response** — to the frontend

### State Definition

```
AgentState:
  conversation    — chat history
  doctor          — extracted doctor name
  hospital        — extracted hospital name
  entities        — accumulated extracted entities
  summary         — generated summary
  intent          — detected intent string
  interaction     — interaction data
  database_result — DB query results
  tool_used       — which tool was executed
  response        — final response text
  user_id         — authenticated user ID
  pending_deletion — interaction ID awaiting confirmation
```

### Intent Detection

The `detect_intent` node uses an LLM prompt to classify user messages. The 6 core intents map to the primary tools:

| Intent             | Tool                 | Trigger Examples                                                 |
| ------------------ | -------------------- | ---------------------------------------------------------------- |
| `log_interaction`  | Log Interaction      | "I met Dr. Ravi today", "Log a meeting with Dr. Priya"           |
| `edit_interaction` | Edit                 | "Edit the last interaction", "Change interest level to High"     |
| `summarize`        | Summarize            | "Summarize my last meeting", "What was discussed?"               |
| `followup`         | Follow-up Recommend  | "What should I do next?", "Recommend follow-up actions"          |
| `search`           | Search               | "Search for Metformin interactions", "Find Dr. Sharma's records" |
| `delete`           | Delete               | "Delete the last interaction", "Remove Dr. Patel's record"       |

### Additional Intents

| Intent             | Description                                                                |
| ------------------ | -------------------------------------------------------------------------- |
| `extract_entities` | Extract medical entities (doctors, hospitals, medicines)                   |
| `sentiment`        | Analyze meeting sentiment and engagement                                   |
| `classify`         | Classify meeting type and effectiveness                                    |
| `history`          | Show recent interactions                                                   |
| `dashboard`        | Answer questions about dashboard statistics                                |
| `general`          | Handle greetings and free-form questions                                   |

### Tool Nodes (6 Core Tools)

| Node                    | Tool                       | Description                                                                                               |
| ----------------------- | -------------------------- | --------------------------------------------------------------------------------------------------------- |
| `log_interaction_node`  | `log_interaction_tool`     | Stepwise extraction (asks one question at a time), date/duration parsing, saves to DB, broadcasts update  |
| `edit_interaction_node` | `edit_interaction_tool`    | Natural language edit requests via LLM, finds interaction by ID or doctor name, applies field updates     |
| `summarize_node`        | `summarize_tool`           | Retrieves latest interaction, generates 150-word CRM summary                                              |
| `followup_node`         | `followup_tool`            | Generates follow-up plan with talking points, priority, suggested products, clinical evidence             |
| `search_node`           | `search_interactions_tool` | Uses LLM to extract search parameters, queries DB with ILIKE filters                                      |
| `delete_node`           | `delete_interaction_tool`  | Two-phase delete: first call asks for confirmation, second call executes deletion                         |

### Additional Nodes

| Node                    | Description                                                                |
| ----------------------- | -------------------------------------------------------------------------- |
| `confirm_delete_node`   | Executes deletion after user confirms                                      |
| `cancel_delete_node`    | Cancels pending deletion                                                   |
| `extract_entities_node` | Extracts doctors, hospitals, medicines, diseases, symptoms                 |
| `sentiment_node`        | Returns sentiment, confidence, key phrases, engagement score               |
| `classify_node`         | Returns meeting type, effectiveness, next action, recommendations          |
| `history_node`          | Lists recent interactions, supports doctor filter and count limit          |
| `dashboard_node`        | Fetches dashboard stats, answers natural language questions                |
| `general_node`          | Handles greetings and free-form queries                                    |

### System Prompts

| Prompt                       | Purpose                                                   |
| ---------------------------- | --------------------------------------------------------- |
| `SYSTEM_PROMPT`              | General AI CRM assistant behavior                         |
| `INTENT_DETECTION_PROMPT`    | Classify user intent with 11 categories and routing rules |
| `HCP_EXTRACTION_PROMPT`      | Full structured extraction of HCP interaction fields      |
| `STEPWISE_EXTRACTION_PROMPT` | Step-by-step extraction for missing fields                |
| `MEDICAL_ENTITY_PROMPT`      | Extract medical entities as structured JSON               |
| `SUMMARIZER_PROMPT`          | Generate 150-word CRM summaries                           |
| `FOLLOWUP_PROMPT`            | Generate follow-up recommendation JSON                    |
| `SEARCH_QUERY_PROMPT`        | Extract search parameters from natural language           |
| `DOCTOR_NAME_EXTRACT_PROMPT` | Extract doctor name from text                             |
| `DASHBOARD_QUERY_PROMPT`     | Answer dashboard statistics questions                     |
| `TITLE_GENERATION_PROMPT`    | Generate conversation titles                              |

---

## API Endpoints

### Authentication

| Method | Endpoint             | Description                                         |
| ------ | -------------------- | --------------------------------------------------- |
| POST   | `/api/auth/register` | Register new user. Returns JWT token + user object. |
| POST   | `/api/auth/login`    | Authenticate user. Returns JWT token + user object. |
| GET    | `/api/auth/profile`  | Get current user profile (requires Bearer token).   |

### Interactions

| Method | Endpoint                 | Description                                                                                                                   |
| ------ | ------------------------ | ----------------------------------------------------------------------------------------------------------------------------- |
| POST   | `/api/interactions`      | Create interaction. Broadcasts `DASHBOARD_UPDATED` via WebSocket. Returns 201.                                                |
| GET    | `/api/interactions`      | List interactions with pagination, search, and sorting. Query params: `page`, `page_size`, `search`, `sort_by`, `sort_order`. |
| GET    | `/api/interactions/{id}` | Get single interaction by ID.                                                                                                 |
| PUT    | `/api/interactions/{id}` | Update interaction. Broadcasts `DASHBOARD_UPDATED`.                                                                           |
| DELETE | `/api/interactions/{id}` | Delete interaction. Returns 204. Broadcasts `DASHBOARD_UPDATED`.                                                              |

### AI

| Method | Endpoint            | Description                                                                                                                                                                      |
| ------ | ------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| POST   | `/api/ai/chat`      | Main AI chat endpoint. Runs the full LangGraph agent pipeline. Accepts `message` and optional `conversation_id`. Returns `response`, `tool_used`, `entities`, `conversation_id`. |
| POST   | `/api/ai/extract`   | Extract structured fields from raw text via LLM.                                                                                                                                 |
| POST   | `/api/ai/summarize` | Generate a CRM summary from text.                                                                                                                                                |
| POST   | `/api/ai/followup`  | Generate follow-up recommendations.                                                                                                                                              |
| POST   | `/api/ai/edit`      | Edit an interaction via natural language.                                                                                                                                        |
| POST   | `/api/ai/entities`  | Extract medical entities from text.                                                                                                                                              |
| POST   | `/api/ai/sentiment` | Analyze sentiment of text.                                                                                                                                                       |

### Conversations

| Method | Endpoint                           | Description                                                                            |
| ------ | ---------------------------------- | -------------------------------------------------------------------------------------- |
| GET    | `/api/conversations`               | List all conversations for current user (with last message preview and message count). |
| POST   | `/api/conversations`               | Create a new conversation.                                                             |
| DELETE | `/api/conversations/{id}`          | Delete conversation and all its messages.                                              |
| GET    | `/api/conversations/{id}/messages` | Get all messages in a conversation.                                                    |
| PUT    | `/api/conversations/{id}/title`    | Update conversation title (auto-generated by AI).                                      |

### Dashboard

| Method | Endpoint         | Description                                                                                                                                              |
| ------ | ---------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| GET    | `/api/dashboard` | Returns: `total_hcps`, `interactions_today`, `pending_followups`, `weekly_meetings`, `weekly_activity[]`, `recent_activities[]`, `upcoming_followups[]`. |

### WebSocket

| Protocol  | Endpoint                        | Description                                                                                                                                                     |
| --------- | ------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| WebSocket | `/api/ws/dashboard?token={jwt}` | Real-time dashboard updates. Server pushes `{"type": "DASHBOARD_UPDATED"}` whenever interactions are created, updated, or deleted. JWT authentication required. |

### Health Check

| Method | Endpoint | Description                                                                         |
| ------ | -------- | ----------------------------------------------------------------------------------- |
| GET    | `/`      | Returns `{"message": "AI-First CRM API", "version": "1.0.0", "status": "running"}`. |

---

## Database Models

### User

| Column       | Type        | Constraints               |
| ------------ | ----------- | ------------------------- |
| `id`         | Integer     | Primary Key, Indexed      |
| `name`       | String(255) | NOT NULL                  |
| `email`      | String(255) | UNIQUE, Indexed, NOT NULL |
| `password`   | String(255) | NOT NULL (bcrypt hashed)  |
| `role`       | String(50)  | Default: `"field_rep"`    |
| `created_at` | DateTime    | Default: `now()`          |

### HCP (Healthcare Professional)

| Column        | Type        | Constraints          |
| ------------- | ----------- | -------------------- |
| `id`          | Integer     | Primary Key, Indexed |
| `doctor_name` | String(255) | NOT NULL, Indexed    |
| `hospital`    | String(255) | Nullable             |
| `speciality`  | String(255) | Nullable             |
| `city`        | String(255) | Nullable             |
| `created_at`  | DateTime    | Default: `now()`     |

### Interaction

| Column             | Type       | Constraints                          |
| ------------------ | ---------- | ------------------------------------ |
| `id`               | Integer    | Primary Key, Indexed                 |
| `hcp_id`           | Integer    | FK → `hcps.id`, Nullable             |
| `summary`          | Text       | Nullable                             |
| `discussion`       | Text       | Nullable                             |
| `products`         | Text       | Nullable (comma-separated)           |
| `competitors`      | Text       | Nullable (comma-separated)           |
| `sentiment`        | String(50) | Nullable                             |
| `interest_level`   | String(50) | Nullable                             |
| `interaction_date` | Date       | Nullable                             |
| `follow_up_date`   | Date       | Nullable                             |
| `duration`         | Integer    | Nullable (minutes)                   |
| `interaction_type` | String(50) | Nullable                             |
| `created_by`       | Integer    | FK → `users.id`, Nullable            |
| `created_at`       | DateTime   | Default: `now()`                     |
| `updated_at`       | DateTime   | Default: `now()`, on update: `now()` |

### Conversation

| Column           | Type        | Constraints                                                    |
| ---------------- | ----------- | -------------------------------------------------------------- |
| `id`             | String(36)  | Primary Key (UUID)                                             |
| `user_id`        | Integer     | FK → `users.id`, NOT NULL, Indexed                             |
| `title`          | String(255) | Default: `"New Chat"`                                          |
| `extracted_data` | Text        | Nullable (JSON: accumulated entities + pending_deletion state) |
| `created_at`     | DateTime    | Default: `now()`                                               |
| `updated_at`     | DateTime    | Default: `now()`, on update: `now()`                           |

### Message

| Column            | Type       | Constraints                                |
| ----------------- | ---------- | ------------------------------------------ |
| `id`              | Integer    | Primary Key, Indexed                       |
| `conversation_id` | String(36) | FK → `conversations.id`, NOT NULL, Indexed |
| `role`            | String(50) | NOT NULL (`"user"` or `"assistant"`)       |
| `content`         | Text       | NOT NULL                                   |
| `created_at`      | DateTime   | Default: `now()`                           |

### AILog

| Column           | Type        | Constraints          |
| ---------------- | ----------- | -------------------- |
| `id`             | Integer     | Primary Key, Indexed |
| `prompt`         | Text        | Nullable             |
| `response`       | Text        | Nullable             |
| `tool`           | String(100) | Nullable             |
| `execution_time` | Float       | Nullable (seconds)   |
| `timestamp`      | DateTime    | Default: `now()`     |

---

## State Management

### Redux Store (6 Slices)

| Slice           | File                    | State                                                                                                                                                           | Async Thunks                                                                                           |
| --------------- | ----------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| `auth`          | `authSlice.js`          | `user`, `token`, `isAuthenticated`, `loading`, `error`                                                                                                          | `login`, `register`                                                                                    |
| `chat`          | `chatSlice.js`          | `messages[]`, `extracted`, `conversationId`, `loading`, `error`                                                                                                 | `sendMessage`, `extractEntities`                                                                       |
| `conversations` | `conversationsSlice.js` | `conversations[]`, `activeConversationId`, `messages[]`, `loading`, `sending`, `error`                                                                          | `fetchConversations`, `createConversation`, `deleteConversation`, `fetchMessages`, `sendChatMessage`   |
| `interactions`  | `interactionSlice.js`   | `items[]`, `total`, `current`, `page`, `pageSize`, `loading`, `error`                                                                                           | `fetchInteractions`, `fetchInteraction`, `createInteraction`, `updateInteraction`, `deleteInteraction` |
| `dashboard`     | `dashboardSlice.js`     | `total_hcps`, `interactions_today`, `pending_followups`, `weekly_meetings`, `recentActivities[]`, `upcomingFollowups[]`, `weeklyActivity[]`, `loading`, `error` | `fetchDashboard`                                                                                       |
| `ui`            | `uiSlice.js`            | `sidebarOpen`, `darkMode`, `loading`, `notification`                                                                                                            | — (sync reducers only)                                                                                 |

---

## Authentication

### Flow

1. **Register**: `POST /api/auth/register` → bcrypt hashes password → creates User → returns JWT + user
2. **Login**: `POST /api/auth/login` → bcrypt verifies password → returns JWT + user
3. **Token Storage**: JWT stored in `localStorage` under key `token`
4. **Request Interception**: Axios interceptor adds `Authorization: Bearer <token>` to all API requests
5. **Route Protection**: `ProtectedRoute` component checks `state.auth.isAuthenticated` before rendering
6. **Session Expiry**: 401 response clears token and redirects to `/login`

### Security

- Passwords hashed with `bcrypt` (salt rounds: default)
- JWT signed with HS256 algorithm
- Token expiry: configurable, default 1440 minutes (24 hours)
- CORS restricted to `localhost:5173` and `*.vercel.app`

---

## Real-Time Features

### WebSocket System

- **Connection Manager** (`utils/websocket.py`): Maps `user_id → List[WebSocket]` for multi-device support
- **Endpoint**: `ws://host/api/ws/dashboard?token={jwt}` with JWT validation
- **Broadcast Triggers**: Interaction create, update, delete (both REST API and AI tool saves)
- **Frontend Handling**: Dashboard component connects on mount, auto-reconnects with exponential backoff (1s → 30s), falls back to 30-second polling
- **UI Feedback**: Shows "Updated X ago" timestamp, refreshes stats and charts on update

---

## Styling & UI

### Design System

- **Framework**: Tailwind CSS with custom color palette (primary blue 50-900)
- **Dark Mode**: Class-based (`darkMode: 'class'`), toggled via UI slice, persisted in localStorage
- **Font**: Inter (sans-serif)
- **Icons**: Lucide React icon library

### Custom CSS Classes

| Class                           | Purpose                                            |
| ------------------------------- | -------------------------------------------------- |
| `.glass`                        | Frosted glass effect with backdrop blur            |
| `.card`                         | Standard card with rounded corners, border, shadow |
| `.card-glass`                   | Glass variant of card                              |
| `.btn-primary`                  | Blue primary button with shadow and active scale   |
| `.btn-secondary`                | Gray secondary button                              |
| `.btn-danger`                   | Red danger button                                  |
| `.input-field`                  | Form input with border, focus ring, transitions    |
| `.tab-active` / `.tab-inactive` | Tab button states                                  |
| `.scrollbar-hide`               | Hides scrollbar across browsers                    |
| `.animate-typing-dot`           | Bouncing dot animation for typing indicator        |

### Responsive Breakpoints

- Mobile: single column layouts, hamburger menu for sidebar
- Tablet (`md:`): two-column grids for forms and stats
- Desktop (`lg:`): four-column stat cards, full sidebar

### AI Message Formatting

The `AssistantMessage` component renders AI responses with rich formatting:

| Pattern                                            | Rendering                       |
| -------------------------------------------------- | ------------------------------- |
| Lines starting with emoji (🎯📋✅🔍📅🔬💊📌💡🏥⚠️) | Bold section header             |
| Lines starting with ✓ or ✔                         | Green checkmark item            |
| Lines starting with • or -                         | Dotted bullet item              |
| Lines starting with `N.`                           | Numbered list with circle badge |
| Indented lines (4+ spaces)                         | Smaller gray subtext            |
| Empty lines                                        | Vertical spacer                 |
| All other text                                     | Normal paragraph                |

---

## Installation

### Prerequisites

- Node.js 18+
- Python 3.10+
- SQLite (development) or PostgreSQL (production)
- Groq API key (free at https://console.groq.com)

### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate (Windows)
.\venv\Scripts\activate

# Activate (macOS/Linux)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
also add th
# Configure environment
cp .env.example .env
# Edit .env with your GROQ_API_KEY and DATABASE_URL

# Start server
uvicorn app.main:app --reload
```

The backend runs on `http://localhost:8000`. Tables are auto-created on first run.

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Configure environment
cp .env.example .env
# Edit .env with VITE_API_URL=http://localhost:8000/api

# Start dev server
npm run dev
```

The frontend runs on `http://localhost:5173` and proxies `/api` requests to the backend.

---

## Environment Variables

### Backend (`.env`)

| Variable                      | Required | Default                 | Description                |
| ----------------------------- | -------- | ----------------------- | -------------------------- |
| `DATABASE_URL`                | Yes      | `sqlite:///./ai_crm.db` | Database connection string |
| `GROQ_API_KEY`                | Yes      | —                       | Groq API key for LLM       |
| `JWT_SECRET`                  | Yes      | —                       | Secret key for JWT signing |
| `JWT_ALGORITHM`               | No       | `HS256`                 | JWT signing algorithm      |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No       | `1440`                  | Token expiry (24h)         |

### Frontend (`.env`)

| Variable       | Required | Default                     | Description          |
| -------------- | -------- | --------------------------- | -------------------- |
| `VITE_API_URL` | Yes      | `http://localhost:8000/api` | Backend API base URL |

---

## Deployment

| Component | Platform         | Notes                                                          |
| --------- | ---------------- | -------------------------------------------------------------- |
| Frontend  | Vercel           | `npm run build`, deploy `dist/` folder. Auto-deploys from Git. |
| Backend   | Render / Railway | Deploy Python app. Set environment variables in dashboard.     |
| Database  | Neon PostgreSQL  | Free tier available. Update `DATABASE_URL` in backend `.env`.  |

### Production Checklist

- [ ] Set `DATABASE_URL` to PostgreSQL connection string
- [ ] Set secure `JWT_SECRET` (use a random 64+ character string)
- [ ] Set valid `GROQ_API_KEY`
- [ ] Update CORS origins to include production frontend URL
- [ ] Update Vite proxy configuration for production build

---

## Project File Structure

```
AI-First CRM/
├── README.md
├── .gitignore
│
├── backend/
│   ├── requirements.txt
│   ├── .env / .env.example
│   └── app/
│       ├── main.py                          # FastAPI entry point, CORS, routers
│       ├── config/
│       │   └── settings.py                  # Pydantic Settings (env vars)
│       ├── database/
│       │   └── connection.py                # SQLAlchemy engine, session, Base
│       ├── models/
│       │   ├── user.py                      # User model
│       │   ├── hcp.py                       # HCP model
│       │   ├── interaction.py               # Interaction model
│       │   ├── conversation.py              # Conversation + Message models
│       │   └── ai_log.py                    # AILog model
│       ├── schemas/
│       │   ├── user.py                      # UserRegister, UserLogin, UserResponse, Token
│       │   ├── interaction.py               # InteractionCreate/Update/Response
│       │   ├── hcp.py                       # HCPCreate, HCPResponse
│       │   ├── dashboard.py                 # DashboardResponse
│       │   └── chat.py                      # ChatMessage, ChatResponse, Extract/FollowUp
│       ├── services/
│       │   └── interaction_service.py       # CRUD + dashboard aggregation logic
│       ├── utils/
│       │   ├── auth.py                      # Password hashing, JWT, get_current_user
│       │   ├── token_payload.py             # TokenPayload Pydantic model
│       │   └── websocket.py                 # ConnectionManager for real-time updates
│       ├── api/
│       │   └── routers/
│       │       ├── auth.py                  # POST /register, /login, GET /profile
│       │       ├── interactions.py          # CRUD /api/interactions
│       │       ├── chat.py                  # POST /api/ai/* endpoints
│       │       ├── conversations.py         # CRUD /api/conversations
│       │       ├── dashboard.py             # GET /api/dashboard
│       │       └── ws.py                    # WebSocket /api/ws/dashboard
│       └── langgraph/
│           ├── agent.py                     # LangGraph StateGraph (14+ nodes)
│           ├── state.py                     # AgentState TypedDict
│           ├── prompts/
│           │   └── system_prompts.py        # 11 system prompts
│           └── tools/
│               ├── log_interaction.py       # Stepwise HCP logging (349 lines)
│               ├── edit_interaction.py      # Natural language editing
│               ├── summarize.py             # 150-word CRM summaries
│               ├── followup.py              # Follow-up recommendations
│               ├── entity_extraction.py     # Medical entity extraction
│               ├── sentiment.py             # Sentiment analysis
│               ├── meeting_classifier.py    # Meeting classification
│               ├── search_interactions.py   # NL search with DB queries
│               ├── show_history.py          # Recent interaction listing
│               ├── delete_interaction.py    # Two-phase delete with confirmation
│               └── dashboard_assistant.py   # NL dashboard queries
│
└── frontend/
    ├── package.json
    ├── .env / .env.example
    ├── index.html
    ├── vite.config.js
    ├── tailwind.config.js
    ├── postcss.config.js
    └── src/
        ├── main.jsx                         # React entry: Provider, Router, Toaster
        ├── App.jsx                          # App shell: dark mode init
        ├── index.css                        # Tailwind directives, custom classes
        ├── routes/
        │   └── AppRoutes.jsx                # Route definitions with auth guards
        ├── services/
        │   └── api.js                       # Axios instance, interceptors, services
        ├── constants/
        │   └── index.js                     # Interaction types, interest levels
        ├── utils/
        │   └── index.js                     # formatDate, formatTime, getInitials
        ├── hooks/
        │   ├── useAuth.js                   # Login, register, logout
        │   └── useTheme.js                  # Dark mode toggle
        ├── redux/
        │   ├── store.js                     # Redux store (6 slices)
        │   └── slices/
        │       ├── authSlice.js             # Auth state
        │       ├── chatSlice.js             # Simple chat state (LogInteraction)
        │       ├── conversationsSlice.js    # Full conversation management
        │       ├── interactionSlice.js      # Interaction CRUD + pagination
        │       ├── dashboardSlice.js        # Dashboard stats
        │       └── uiSlice.js               # Sidebar, dark mode, notifications
        ├── layouts/
        │   ├── MainLayout.jsx               # Sidebar + Navbar + Outlet
        │   └── AuthLayout.jsx               # Centered card for auth pages
        ├── pages/
        │   ├── Dashboard.jsx                # Stats, charts, activity, follow-ups
        │   ├── LogInteraction.jsx           # Dual-tab: form + AI chat
        │   ├── InteractionHistory.jsx       # Paginated, sortable table
        │   ├── InteractionDetails.jsx       # Full interaction view
        │   ├── EditInteraction.jsx          # Edit form
        │   ├── ChatAssistant.jsx            # Full AI chat with sidebar
        │   ├── Settings.jsx                 # Profile, dark mode, logout
        │   ├── Login.jsx                    # Login form
        │   ├── Register.jsx                 # Registration form
        │   └── NotFound.jsx                 # 404 page
        └── components/
            ├── layout/
            │   ├── Sidebar.jsx              # Collapsible navigation sidebar
            │   └── Navbar.jsx               # Top bar with actions
            ├── chat/
            │   ├── ChatSidebar.jsx          # Conversation history sidebar
            │   └── AssistantMessage.jsx     # Rich AI message renderer + TypingIndicator
            └── ui/
                ├── StatCard.jsx             # Dashboard stat card
                ├── Loader.jsx               # Loading spinner
                ├── ErrorState.jsx           # Error display with retry
                ├── EmptyState.jsx           # Empty data display
                └── TableSkeleton.jsx        # Table loading skeleton
```

---

## Code Metrics

| Metric                | Count                                                    |
| --------------------- | -------------------------------------------------------- |
| Backend Python files  | 32                                                       |
| Frontend source files | 32                                                       |
| Total lines of code   | ~5,200+                                                  |
| Database models       | 6 (User, HCP, Interaction, Conversation, Message, AILog) |
| Redux slices          | 6                                                        |
| LangGraph agent nodes | 14+                                                      |
| System prompts        | 11                                                       |
| API endpoints         | 18                                                       |
| Frontend pages        | 10                                                       |
| Shared UI components  | 5                                                        |
| AI tools              | 6 core + 8 additional                                               |

---

## License

This project is proprietary software built for pharmaceutical CRM use.
#   A I - C R M 
 
 

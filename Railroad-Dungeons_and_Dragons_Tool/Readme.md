# Railroad — D&D Campaign Management Tool

A full-stack web application for Dungeons & Dragons campaign creation and management. Railroad lets Dungeon Masters store campaign notes in one central place and selectively share individual facts with players — revealing information progressively without exposing entire documents.

## Features

- **Campaign Workspaces** — Create and join campaigns with other players and a designated Game Master
- **Artifacts & Facts** — Organize campaign content into top-level Artifacts (locations, characters, items) containing individual Facts that can be shared independently
- **Granular Access Control** — Each Fact and Artifact has a visibility key; DMs reveal information piece by piece without sharing the full document
- **Grouped Sharing** — Facts can share a common key to be revealed together, or inherit their parent Artifact's key for automatic visibility
- **Search** — Find Artifacts and Facts by title or content with relevance-ranked results (exact matches first)
- **Campaign Members** — View other users in your shared campaigns
- **Markdown Editor** — Rich text editing for Facts using a built-in markdown editor

## Tech Stack

| Layer | Technologies |
|-------|-------------|
| **Frontend** | React 18, Redux Toolkit, Material-UI (MUI Joy), styled-components, @uiw/react-md-editor |
| **Backend** | TypeScript, Node.js, Express.js |
| **Database** | MySQL |
| **Auth** | bcrypt (password hashing), express-session (session management) |
| **Testing** | AVA, NYC (code coverage) |

## Project Structure

```
Railroad-Dungeons_and_Dragons_Tool/
├── railroad-server/                # Express/TypeScript backend
│   └── src/
│       ├── index.ts                # Server entry point (port 5000)
│       ├── lib/Database.ts         # MySQL connection wrapper
│       └── routers/
│           ├── BaseRouter.ts       # Abstract base with shared DB access
│           ├── AuthRouter.ts       # Login, signup, logout, session check
│           ├── ArtifactRouter.ts   # Artifact CRUD operations
│           ├── FactRouter.ts       # Fact CRUD with display ordering
│           ├── SearchRouter.ts     # Keyword search with relevance ranking
│           └── FriendRouter.ts     # Campaign member queries
├── railroad-client/                # React frontend
│   └── src/
│       ├── App.js                  # Three-column layout
│       ├── store.js                # Redux store configuration
│       ├── Sidebar/                # Search and artifact list
│       ├── Artifact/               # Artifact display and editing
│       ├── FriendList/             # Campaign members sidebar
│       └── components/
│           └── EditableText.js     # Reusable markdown editor
└── doc/
    ├── DatabaseDesign.md           # ER diagram and schema
    └── AdvancedQueries.md          # Query optimization documentation
```

## Database Schema

| Table | Purpose |
|-------|---------|
| `User` | User accounts (id, username, hashed password) |
| `Campaign` | Campaign workspaces linked to a Game Master |
| `Artifact` | Top-level documents with visibility keys |
| `Fact` | Individual information sections within Artifacts |
| `AccessKey` | UUID-based visibility keys |
| `UserAccess` | Maps which users have unlocked which keys |
| `CampaignMembership` | Links users to campaigns |

## Getting Started

### Prerequisites

- Node.js (>=10)
- npm
- MySQL database

### Backend

```bash
cd railroad-server
npm install
npm run build       # Compile TypeScript
npm start           # Runs on http://localhost:5000
```

### Frontend

```bash
cd railroad-client
npm install
npm start           # Runs on http://localhost:3000 (proxies to backend)
```

## How It Works

### Access Control System
Every Artifact and Fact is assigned a UUID-based access key. When a DM wants to reveal information, they grant the player access to that key. Facts can share keys for batch reveals, or use their parent Artifact's key so they become visible automatically when the Artifact is shared.

### Search Ranking
The search endpoint uses a SQL UNION to combine matches from Artifact titles and Fact entries, then ranks results using a CASE-based ordering system that prioritizes exact prefix matches over substring matches. Partial indexes on Fact content optimize query performance.

### Architecture
The backend uses a router pattern where all route handlers extend a `BaseRouter` class for shared database access. The frontend is a three-column React layout — a searchable sidebar, the main Artifact/Fact editor, and a campaign members panel — with Redux Toolkit managing the selected artifact state.

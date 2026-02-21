# iReminder

A web application for students to track assignments and due dates across courses by integrating directly with the Canvas LMS. Features a calendar view, assignment analytics, and a personal notepad — all backed by a MySQL database.

## Features

- **Canvas LMS Integration** — Fetches assignments and due dates directly from Canvas using a personal API token
- **Assignment Table** — View all assignments across courses with name, course, due date, and due time in a sortable table
- **Calendar View** — Interactive FullCalendar display showing assignments as events on their due dates
- **Assignment Analytics** — Chart.js bar chart showing assignment distribution per course for workload analysis
- **Personal Notepad** — Persistent notes tied to your user account, stored in the database
- **User Authentication** — Register and log in with email and password

## Tech Stack

| Layer | Technologies |
|-------|-------------|
| **Frontend** | React 18, React Router DOM 6, Axios |
| **Calendar** | FullCalendar 6 (@fullcalendar/react, @fullcalendar/daygrid) |
| **Charts** | Chart.js 4, react-chartjs-2 |
| **Backend** | Python 3, Flask 3.0, Flask-CORS |
| **Database** | MySQL (mysql-connector-python) |
| **External API** | Canvas LMS REST API |

## Project Structure

```
iReminder/
├── server/
│   ├── server.py             # Flask API — auth, Canvas proxy, notes
│   ├── canvas.py             # Canvas API integration (courses, assignments)
│   ├── test.py               # Unit tests for Canvas module
│   └── requirements.txt      # Python dependencies
├── client/
│   └── src/
│       ├── App.js            # Main app with routing and Canvas token input
│       ├── Header.js         # Navigation header
│       ├── Tabs/
│       │   ├── tab1.js       # About page
│       │   ├── tab3.js       # Assignments table + analytics chart
│       │   ├── tab4.js       # Calendar view
│       │   └── tab6.js       # Notepad
│       └── Features/
│           ├── LoginForm.js
│           ├── RegisterForm.js
│           ├── AssignmentTable.js
│           ├── GradeChart.js
│           └── ProtectedRoute.js
└── project-arch.png          # Architecture diagram
```

## Getting Started

### Prerequisites

- Python 3
- Node.js and npm
- A Canvas LMS account with a personal access token ([how to generate one](https://kb.iu.edu/d/aaja))

### Backend

```bash
cd server
pip install -r requirements.txt
python3 server.py              # Starts Flask server on http://localhost:5000
```

### Frontend

```bash
cd client
npm install
npm start                      # Opens React app at http://localhost:3000
```

Both servers must be running simultaneously.

### Usage

1. Register a new account or log in
2. On the homepage, paste your Canvas API token
3. The system fetches all your courses and assignments automatically
4. Navigate to the **Assignments** tab for a table view and workload chart
5. Navigate to the **Calendar** tab for a date-based view
6. Use the **Notepad** tab to save personal notes

## How It Works

### Canvas Integration
When you submit your API token, the backend calls the Canvas REST API to fetch your enrolled courses, then iterates through each course to retrieve assignments. Assignment data is parsed from Canvas's ISO 8601 date format into a structured response with course name, assignment name, due date, and due time.

### Data Flow
Assignment data is stored in the browser's `localStorage` after the initial Canvas fetch, allowing the table, calendar, and chart views to render without repeated API calls. User notes are persisted server-side in MySQL and fetched on component mount.

### Analytics
The chart component aggregates assignments by course using a counting algorithm, then renders a Chart.js bar chart showing the number of assignments per course — giving students a quick visual of which classes have the heaviest workload.

## Developers

- **Xinyi Wei** — Backend APIs, frontend styles, frontend API calls
- **Lance Tran** — Database and Notepad feature
- **Nate Gomes** — Frontend setup, backend-to-frontend connection
- **Ronit Rout** — Frontend CSS, Chart component API calls

# Game Management Features

**Date Added:** January 14, 2026  
**Version:** 1.0

## Overview

This document describes the new game management features added to PropAI that allow users to view, edit, and delete games from the team dashboard. These features were implemented to address data quality issues such as incorrect team records caused by preseason or erroneous data.

## Features

### 1. View All Games

A new "View All Games" button has been added to the **Recent Games** section of the team dashboard. This button opens a comprehensive modal that displays all games for the selected team.

**Location:** Teams → [Select Team] → Recent Games → "View All Games" button

**Features:**
- Paginated list of all games (25 per page)
- Search/filter by opponent name, date, or season
- Displays: Date, Opponent, Result (W/L), Score, Season
- Action buttons for each game: View, Edit, Delete

### 2. Clickable Game Cards

Games displayed in the **Recent Games** section on the team dashboard are now clickable. Clicking on any game card will open a detailed box score modal.

**Features:**
- Hover effect indicates clickability
- Full box score display for both teams
- Player statistics including: MIN, PTS, REB, AST, FG, 3P, FT, +/-

### 3. Game Box Score Modal

A new modal displays detailed box score information when viewing a game.

**Features:**
- Complete player statistics for both teams
- Team totals displayed
- Players sorted by minutes played
- Inactive players shown with reduced opacity
- Back button for navigation

### 4. Edit Game Score

Users can now edit the scores of individual games to correct data entry errors.

**Access:** All Games Modal → Edit button on any game row

**Features:**
- Simple form with team names and score inputs
- Validation for numeric inputs
- Real-time update of dashboard after save

### 5. Delete Game

Users can delete games that shouldn't be in the system (e.g., preseason games, duplicate entries).

**Access:** All Games Modal → Delete button on any game row

**Features:**
- Confirmation modal with warning message
- Cascading delete removes all associated data:
  - Player box score entries
  - Team totals
  - Inactive player records
- Dashboard automatically refreshes after deletion

### 6. Navigation History & Back Button

A back button has been implemented in the game box score modal to allow users to return to their previous view.

**Features:**
- Tracks navigation history (recent games vs all games modal)
- Seamlessly returns to the previous context
- History cleared when closing the modal

## API Endpoints

### New Endpoints Added

#### GET `/api/team/<abbrev>/all-games`
Returns all games for a specific team with pagination support.

**Query Parameters:**
- `page` (int): Page number (default: 1)
- `per_page` (int): Items per page (default: 50)

**Response:**
```json
{
  "games": [...],
  "total": 40,
  "page": 1,
  "per_page": 25,
  "total_pages": 2
}
```

#### DELETE `/api/game/<game_id>`
Deletes a game and all associated data.

**Response:**
```json
{
  "success": true,
  "message": "Game 123 deleted successfully",
  "deleted_game": {
    "id": 123,
    "date": "2025-01-10",
    "team1": "New York Knicks",
    "team2": "Boston Celtics"
  }
}
```

#### PUT `/api/game/<game_id>/score`
Updates the score of an existing game.

**Request Body:**
```json
{
  "team1_pts": 110,
  "team2_pts": 105
}
```

**Response:**
```json
{
  "success": true,
  "message": "Score updated successfully",
  "game": {
    "id": 123,
    "team1": "New York Knicks",
    "team2": "Boston Celtics",
    "team1_pts": 110,
    "team2_pts": 105
  }
}
```

## Usage Guide

### Fixing Incorrect Team Records

If a team's record appears incorrect (e.g., showing 26-14 instead of 25-14):

1. Navigate to **Teams** tab
2. Click on the team with the incorrect record
3. Scroll down to **Recent Games** section
4. Click **"View All Games"** button
5. Review the list of games to identify any erroneous entries
6. For incorrect games:
   - Click **Edit** to fix the score
   - Click **Delete** to remove the game entirely
7. The team's record will automatically update after changes

### Viewing Game Box Scores

1. On the team dashboard, click any game card in **Recent Games**
2. Or, in the **All Games** modal, click **View** on any game
3. Review the complete box score for both teams
4. Click **Back** or close the modal to return

### Identifying Preseason Games

Preseason games can often be identified by:
- Dates before the regular season start (typically mid-October)
- Unusually low scores or missing player data
- Games against teams not typically on the schedule

## Technical Notes

### Database Cascading

When a game is deleted, the following tables are automatically updated (via CASCADE):
- `boxscore_player` - All player statistics for the game
- `boxscore_team_totals` - Team total statistics
- `inactive_players` - Records of inactive players

### Session State

Navigation history is stored in the browser's JavaScript memory and is cleared when:
- The user closes the box score modal
- The user navigates away from the team detail page
- The page is refreshed

### Performance

- All games are loaded with pagination (25 per page) to avoid loading large datasets
- Search filtering is performed client-side on the currently loaded page
- Dashboard data is refreshed after any edit/delete operation

## Files Modified

1. **`src/nba_props/web/app.py`**
   - Added `/api/team/<abbrev>/all-games` endpoint
   - Added `DELETE /api/game/<game_id>` endpoint
   - Added `PUT /api/game/<game_id>/score` endpoint
   - Updated dashboard endpoint to include game IDs in recent games

2. **`src/nba_props/web/templates/team_detail.html`**
   - Added "View All Games" button to Recent Games section
   - Made game cards clickable with hover effects
   - Added All Games Modal with search, pagination, and actions
   - Added Game Box Score Modal with back navigation
   - Added Edit Game Modal with score input form
   - Added Delete Game Confirmation Modal
   - Added JavaScript functions for all modal interactions
   - Added CSS styles for new modal components

## Future Enhancements

Potential improvements that could be added:

1. **Bulk Delete** - Select and delete multiple games at once
2. **Export Games** - Export game list to CSV
3. **Game Notes** - Add notes/tags to games for easier filtering
4. **Preseason Detection** - Automatic detection and flagging of preseason games
5. **Undo Delete** - Soft delete with ability to restore games
6. **Edit Full Game** - Edit all game metadata, not just scores

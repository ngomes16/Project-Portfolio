"""
Model Version Tracker - Comprehensive Model Version Management
==============================================================

This module provides a robust system for tracking different model iterations,
their configurations, picks, backtests, and grades over time. This enables:

1. **Version Control**: Each model configuration gets a unique version ID
2. **Pick Tracking**: All picks from each model version are stored
3. **Backtest History**: Full backtest results are preserved per version
4. **Performance Grading**: Models are graded and compared
5. **Key Takeaways**: Learnings from each model are documented

DATABASE SCHEMA:
----------------
- model_versions: Tracks each model version with config and metadata
- model_version_picks: All picks made by a specific model version
- model_version_backtests: Backtest results for each version
- model_version_insights: Key learnings and takeaways

USAGE:
------
    from src.nba_props.engine.model_version_tracker import (
        ModelVersionTracker,
        register_model_version,
        save_model_picks,
        save_backtest_results,
        get_model_comparison,
    )
    
    # Register a new model version
    version_id = register_model_version(
        name="Model V9 - Line Aware",
        version="9.0",
        config={"use_actual_lines": True, ...},
        description="Enhanced model using actual sportsbook lines"
    )
    
    # Save picks from the model
    save_model_picks(version_id, picks, game_date)
    
    # Save backtest results
    save_backtest_results(version_id, backtest_result)
    
    # Compare models
    comparison = get_model_comparison()

Author: NBA Props Team
Last Updated: January 2026
"""
from __future__ import annotations

import json
import sqlite3
import hashlib
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from pathlib import Path

from ..db import Db


# ============================================================================
# Database Schema for Model Version Tracking
# ============================================================================

MODEL_VERSION_SCHEMA = """
-- Model Versions Table: Core registry of all model iterations
CREATE TABLE IF NOT EXISTS model_versions (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    version TEXT NOT NULL,
    config_hash TEXT NOT NULL UNIQUE,  -- Hash of config for deduplication
    config_json TEXT NOT NULL,         -- Full configuration as JSON
    description TEXT,
    
    -- Metadata
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    is_active BOOLEAN DEFAULT 0,       -- Currently active model
    is_deprecated BOOLEAN DEFAULT 0,   -- Model no longer recommended
    
    -- Summary stats (updated after backtests)
    total_backtests INTEGER DEFAULT 0,
    best_hit_rate REAL,
    avg_hit_rate REAL,
    total_picks_made INTEGER DEFAULT 0,
    total_picks_hit INTEGER DEFAULT 0,
    
    -- Grades
    overall_grade TEXT,  -- A, B, C, D, F
    pts_grade TEXT,
    reb_grade TEXT,
    ast_grade TEXT
);

CREATE INDEX IF NOT EXISTS idx_model_versions_hash ON model_versions(config_hash);
CREATE INDEX IF NOT EXISTS idx_model_versions_active ON model_versions(is_active);

-- Model Version Picks: All picks made by each model version
CREATE TABLE IF NOT EXISTS model_version_picks (
    id INTEGER PRIMARY KEY,
    version_id INTEGER NOT NULL,
    pick_date TEXT NOT NULL,
    generated_at TEXT NOT NULL DEFAULT (datetime('now')),
    
    -- Player info
    player_id INTEGER,
    player_name TEXT NOT NULL,
    team_abbrev TEXT NOT NULL,
    opponent_abbrev TEXT NOT NULL,
    
    -- Pick details
    prop_type TEXT NOT NULL,       -- PTS, REB, AST
    direction TEXT NOT NULL,       -- OVER, UNDER
    
    -- Line information (CRITICAL: actual vs derived)
    line_source TEXT NOT NULL,     -- 'sportsbook', 'derived_l10', 'derived_l15', etc
    line REAL NOT NULL,            -- The line used
    sportsbook_line REAL,          -- Actual sportsbook line if available
    derived_line REAL,             -- Our calculated line (for comparison)
    
    -- Projection
    projection REAL NOT NULL,
    projection_std REAL,
    edge_vs_line REAL,             -- (projection - line) / line * 100
    edge_vs_sportsbook REAL,       -- Edge vs actual sportsbook line
    
    -- Confidence
    confidence_score REAL,
    confidence_tier TEXT,          -- PREMIUM, HIGH, MEDIUM, LOW
    pattern TEXT,                  -- cold_bounce, hot_sustained, etc
    
    -- Supporting data
    l5_avg REAL,
    l10_avg REAL,
    l15_avg REAL,
    l20_avg REAL,
    season_avg REAL,
    
    -- Reasoning
    reasons_json TEXT,
    
    -- Outcome (filled in after game)
    actual_value REAL,
    hit INTEGER,                   -- 1 = hit, 0 = miss, NULL = pending
    hit_vs_sportsbook INTEGER,     -- Did it beat the sportsbook line?
    margin REAL,                   -- actual - line
    graded_at TEXT,
    
    FOREIGN KEY (version_id) REFERENCES model_versions(id),
    FOREIGN KEY (player_id) REFERENCES players(id)
);

CREATE INDEX IF NOT EXISTS idx_mvp_version ON model_version_picks(version_id);
CREATE INDEX IF NOT EXISTS idx_mvp_date ON model_version_picks(pick_date);
CREATE INDEX IF NOT EXISTS idx_mvp_player ON model_version_picks(player_id);

-- Model Version Backtests: Historical backtest results
CREATE TABLE IF NOT EXISTS model_version_backtests (
    id INTEGER PRIMARY KEY,
    version_id INTEGER NOT NULL,
    
    -- Backtest period
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL,
    run_at TEXT NOT NULL DEFAULT (datetime('now')),
    
    -- Overall metrics
    days_tested INTEGER,
    total_games INTEGER,
    total_picks INTEGER,
    hits INTEGER,
    misses INTEGER,
    hit_rate REAL,
    
    -- By tier
    premium_picks INTEGER,
    premium_hits INTEGER,
    premium_rate REAL,
    high_picks INTEGER,
    high_hits INTEGER,
    high_rate REAL,
    
    -- By prop type
    pts_picks INTEGER,
    pts_hits INTEGER,
    pts_rate REAL,
    reb_picks INTEGER,
    reb_hits INTEGER,
    reb_rate REAL,
    ast_picks INTEGER,
    ast_hits INTEGER,
    ast_rate REAL,
    
    -- By direction
    over_picks INTEGER,
    over_hits INTEGER,
    over_rate REAL,
    under_picks INTEGER,
    under_hits INTEGER,
    under_rate REAL,
    
    -- Line analysis (KEY IMPROVEMENT)
    picks_with_sportsbook_line INTEGER,
    hits_vs_sportsbook INTEGER,
    rate_vs_sportsbook REAL,      -- Hit rate when using actual lines
    avg_line_diff REAL,           -- Avg diff between derived and sportsbook lines
    
    -- Error metrics
    mae_pts REAL,
    mae_reb REAL,
    mae_ast REAL,
    
    -- ROI simulation
    simulated_roi REAL,           -- ROI at -110 odds
    
    -- Full results JSON (for detailed analysis)
    daily_results_json TEXT,
    pick_breakdown_json TEXT,
    
    FOREIGN KEY (version_id) REFERENCES model_versions(id)
);

CREATE INDEX IF NOT EXISTS idx_mvb_version ON model_version_backtests(version_id);
CREATE INDEX IF NOT EXISTS idx_mvb_dates ON model_version_backtests(start_date, end_date);

-- Model Version Insights: Key takeaways and learnings
CREATE TABLE IF NOT EXISTS model_version_insights (
    id INTEGER PRIMARY KEY,
    version_id INTEGER NOT NULL,
    insight_type TEXT NOT NULL,    -- 'strength', 'weakness', 'key_finding', 'recommendation'
    category TEXT,                 -- 'pts', 'reb', 'ast', 'overall', 'methodology'
    insight TEXT NOT NULL,
    evidence TEXT,                 -- Supporting data/stats
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    
    FOREIGN KEY (version_id) REFERENCES model_versions(id)
);

CREATE INDEX IF NOT EXISTS idx_mvi_version ON model_version_insights(version_id);

-- Model Comparisons: Side-by-side comparison results
CREATE TABLE IF NOT EXISTS model_comparisons (
    id INTEGER PRIMARY KEY,
    compared_at TEXT NOT NULL DEFAULT (datetime('now')),
    version_ids_json TEXT NOT NULL,  -- JSON array of version IDs compared
    comparison_period_start TEXT,
    comparison_period_end TEXT,
    
    -- Winner determination
    winner_version_id INTEGER,
    ranking_json TEXT,               -- Ordered list of versions by performance
    
    -- Comparison metrics JSON
    metrics_json TEXT,
    
    -- Notes
    notes TEXT,
    
    FOREIGN KEY (winner_version_id) REFERENCES model_versions(id)
);
"""


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class ModelVersion:
    """Represents a model version with its configuration."""
    id: Optional[int]
    name: str
    version: str
    config: Dict[str, Any]
    description: str = ""
    created_at: Optional[str] = None
    is_active: bool = False
    is_deprecated: bool = False
    
    # Performance summary
    total_backtests: int = 0
    best_hit_rate: Optional[float] = None
    avg_hit_rate: Optional[float] = None
    total_picks_made: int = 0
    total_picks_hit: int = 0
    
    # Grades
    overall_grade: Optional[str] = None
    pts_grade: Optional[str] = None
    reb_grade: Optional[str] = None
    ast_grade: Optional[str] = None
    
    def config_hash(self) -> str:
        """Generate unique hash for this configuration."""
        config_str = json.dumps(self.config, sort_keys=True)
        return hashlib.md5(config_str.encode()).hexdigest()
    
    @property
    def hit_rate(self) -> float:
        if self.total_picks_made == 0:
            return 0.0
        return self.total_picks_hit / self.total_picks_made


@dataclass
class VersionPick:
    """A pick made by a specific model version."""
    version_id: int
    pick_date: str
    player_id: int
    player_name: str
    team_abbrev: str
    opponent_abbrev: str
    
    prop_type: str
    direction: str
    
    # Line info - all required together
    line_source: str
    line: float
    projection: float  # Moved up - required field
    
    # Optional line info
    sportsbook_line: Optional[float] = None
    derived_line: Optional[float] = None
    
    # Optional projection details
    projection_std: Optional[float] = None
    edge_vs_line: Optional[float] = None
    edge_vs_sportsbook: Optional[float] = None
    
    # Confidence
    confidence_score: Optional[float] = None
    confidence_tier: Optional[str] = None
    pattern: Optional[str] = None
    
    # Averages
    l5_avg: Optional[float] = None
    l10_avg: Optional[float] = None
    l15_avg: Optional[float] = None
    l20_avg: Optional[float] = None
    season_avg: Optional[float] = None
    
    reasons: List[str] = field(default_factory=list)
    
    # Outcome
    actual_value: Optional[float] = None
    hit: Optional[bool] = None
    hit_vs_sportsbook: Optional[bool] = None
    margin: Optional[float] = None


@dataclass
class BacktestSummary:
    """Summary of a backtest run."""
    version_id: int
    start_date: str
    end_date: str
    
    days_tested: int = 0
    total_games: int = 0
    total_picks: int = 0
    hits: int = 0
    misses: int = 0
    
    # By tier
    premium_picks: int = 0
    premium_hits: int = 0
    high_picks: int = 0
    high_hits: int = 0
    
    # By prop
    pts_picks: int = 0
    pts_hits: int = 0
    reb_picks: int = 0
    reb_hits: int = 0
    ast_picks: int = 0
    ast_hits: int = 0
    
    # By direction
    over_picks: int = 0
    over_hits: int = 0
    under_picks: int = 0
    under_hits: int = 0
    
    # Line analysis
    picks_with_sportsbook_line: int = 0
    hits_vs_sportsbook: int = 0
    avg_line_diff: float = 0.0
    
    # Error
    mae_pts: float = 0.0
    mae_reb: float = 0.0
    mae_ast: float = 0.0
    
    # ROI
    simulated_roi: float = 0.0
    
    daily_results: List[Dict] = field(default_factory=list)
    
    @property
    def hit_rate(self) -> float:
        return self.hits / self.total_picks if self.total_picks > 0 else 0.0
    
    @property
    def rate_vs_sportsbook(self) -> float:
        if self.picks_with_sportsbook_line == 0:
            return 0.0
        return self.hits_vs_sportsbook / self.picks_with_sportsbook_line


@dataclass
class ModelInsight:
    """An insight/takeaway from a model version."""
    version_id: int
    insight_type: str  # 'strength', 'weakness', 'key_finding', 'recommendation'
    category: str      # 'pts', 'reb', 'ast', 'overall', 'methodology'
    insight: str
    evidence: Optional[str] = None


# ============================================================================
# Model Version Tracker Class
# ============================================================================

class ModelVersionTracker:
    """
    Main class for tracking model versions, picks, and backtests.
    
    This provides a comprehensive system for:
    - Registering new model versions with their configs
    - Storing picks from each version with line source tracking
    - Recording backtest results
    - Comparing model performance
    - Generating insights and recommendations
    """
    
    def __init__(self, db_path: str = "data/db/nba_props.sqlite3"):
        self.db = Db(db_path)
        self._ensure_schema()
    
    def _ensure_schema(self):
        """Ensure all tracking tables exist."""
        with self.db.connect() as conn:
            conn.executescript(MODEL_VERSION_SCHEMA)
            conn.commit()
    
    # =========================================================================
    # Model Version Management
    # =========================================================================
    
    def register_version(
        self,
        name: str,
        version: str,
        config: Dict[str, Any],
        description: str = "",
        set_active: bool = False,
    ) -> int:
        """
        Register a new model version.
        
        If a version with the same config already exists, returns existing ID.
        """
        config_hash = hashlib.md5(json.dumps(config, sort_keys=True).encode()).hexdigest()
        
        with self.db.connect() as conn:
            # Check if exists
            existing = conn.execute(
                "SELECT id FROM model_versions WHERE config_hash = ?",
                (config_hash,)
            ).fetchone()
            
            if existing:
                return existing["id"]
            
            # Deactivate other models if setting this one active
            if set_active:
                conn.execute("UPDATE model_versions SET is_active = 0")
            
            # Insert new version
            cursor = conn.execute(
                """
                INSERT INTO model_versions (name, version, config_hash, config_json, description, is_active)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (name, version, config_hash, json.dumps(config), description, set_active)
            )
            conn.commit()
            return cursor.lastrowid
    
    def get_version(self, version_id: int) -> Optional[ModelVersion]:
        """Get a model version by ID."""
        with self.db.connect() as conn:
            row = conn.execute(
                "SELECT * FROM model_versions WHERE id = ?", (version_id,)
            ).fetchone()
            
            if not row:
                return None
            
            return ModelVersion(
                id=row["id"],
                name=row["name"],
                version=row["version"],
                config=json.loads(row["config_json"]),
                description=row["description"] or "",
                created_at=row["created_at"],
                is_active=bool(row["is_active"]),
                is_deprecated=bool(row["is_deprecated"]),
                total_backtests=row["total_backtests"] or 0,
                best_hit_rate=row["best_hit_rate"],
                avg_hit_rate=row["avg_hit_rate"],
                total_picks_made=row["total_picks_made"] or 0,
                total_picks_hit=row["total_picks_hit"] or 0,
                overall_grade=row["overall_grade"],
                pts_grade=row["pts_grade"],
                reb_grade=row["reb_grade"],
                ast_grade=row["ast_grade"],
            )
    
    def get_active_version(self) -> Optional[ModelVersion]:
        """Get the currently active model version."""
        with self.db.connect() as conn:
            row = conn.execute(
                "SELECT id FROM model_versions WHERE is_active = 1"
            ).fetchone()
            
            if row:
                return self.get_version(row["id"])
            return None
    
    def set_active_version(self, version_id: int):
        """Set a model version as active."""
        with self.db.connect() as conn:
            conn.execute("UPDATE model_versions SET is_active = 0")
            conn.execute(
                "UPDATE model_versions SET is_active = 1 WHERE id = ?",
                (version_id,)
            )
            conn.commit()
    
    def list_versions(self, include_deprecated: bool = False) -> List[ModelVersion]:
        """List all model versions."""
        with self.db.connect() as conn:
            query = "SELECT id FROM model_versions"
            if not include_deprecated:
                query += " WHERE is_deprecated = 0"
            query += " ORDER BY created_at DESC"
            
            rows = conn.execute(query).fetchall()
            return [self.get_version(r["id"]) for r in rows]
    
    # =========================================================================
    # Pick Tracking
    # =========================================================================
    
    def save_picks(
        self,
        version_id: int,
        picks: List[VersionPick],
    ) -> int:
        """Save picks from a model version. Returns number saved."""
        with self.db.connect() as conn:
            count = 0
            hits = 0
            for pick in picks:
                conn.execute(
                    """
                    INSERT INTO model_version_picks (
                        version_id, pick_date, player_id, player_name, team_abbrev,
                        opponent_abbrev, prop_type, direction, line_source, line,
                        sportsbook_line, derived_line, projection, projection_std,
                        edge_vs_line, edge_vs_sportsbook, confidence_score,
                        confidence_tier, pattern, l5_avg, l10_avg, l15_avg, l20_avg,
                        season_avg, reasons_json, actual_value, hit, hit_vs_sportsbook, margin
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        version_id, pick.pick_date, pick.player_id, pick.player_name,
                        pick.team_abbrev, pick.opponent_abbrev, pick.prop_type,
                        pick.direction, pick.line_source, pick.line,
                        pick.sportsbook_line, pick.derived_line, pick.projection,
                        pick.projection_std, pick.edge_vs_line, pick.edge_vs_sportsbook,
                        pick.confidence_score, pick.confidence_tier, pick.pattern,
                        pick.l5_avg, pick.l10_avg, pick.l15_avg, pick.l20_avg,
                        pick.season_avg, json.dumps(pick.reasons) if pick.reasons else None,
                        pick.actual_value, 
                        1 if pick.hit else (0 if pick.hit is False else None),
                        1 if pick.hit_vs_sportsbook else (0 if pick.hit_vs_sportsbook is False else None),
                        pick.margin
                    )
                )
                count += 1
                # Count hits for already-graded picks
                if pick.hit is True:
                    hits += 1
            
            # Update version stats - include hits if picks were pre-graded
            conn.execute(
                """
                UPDATE model_versions 
                SET total_picks_made = total_picks_made + ?,
                    total_picks_hit = total_picks_hit + ?
                WHERE id = ?
                """,
                (count, hits, version_id)
            )
            conn.commit()
            return count
    
    def grade_picks(self, version_id: int, game_date: str) -> Dict[str, Any]:
        """
        Grade picks for a specific date with actual results.
        Returns summary of grading.
        """
        with self.db.connect() as conn:
            picks = conn.execute(
                """
                SELECT mvp.*, p.id as pid
                FROM model_version_picks mvp
                LEFT JOIN players p ON p.name = mvp.player_name
                WHERE mvp.version_id = ? AND mvp.pick_date = ? AND mvp.hit IS NULL
                """,
                (version_id, game_date)
            ).fetchall()
            
            graded = 0
            hits = 0
            hits_vs_sb = 0
            
            for pick in picks:
                player_id = pick["player_id"] or pick["pid"]
                if not player_id:
                    continue
                
                # Get actual result
                actual = conn.execute(
                    """
                    SELECT b.pts, b.reb, b.ast, b.minutes
                    FROM boxscore_player b
                    JOIN games g ON g.id = b.game_id
                    WHERE b.player_id = ? AND g.game_date = ?
                    """,
                    (player_id, game_date)
                ).fetchone()
                
                if not actual or (actual["minutes"] or 0) < 15:
                    continue
                
                prop_type = pick["prop_type"].lower()
                actual_val = actual[prop_type] or 0
                line = pick["line"]
                sportsbook_line = pick["sportsbook_line"]
                direction = pick["direction"].upper()
                
                # Determine hit
                if direction == "OVER":
                    hit = actual_val > line
                    hit_sb = actual_val > sportsbook_line if sportsbook_line else None
                else:
                    hit = actual_val < line
                    hit_sb = actual_val < sportsbook_line if sportsbook_line else None
                
                margin = actual_val - line
                
                # Update pick
                conn.execute(
                    """
                    UPDATE model_version_picks
                    SET actual_value = ?, hit = ?, hit_vs_sportsbook = ?, margin = ?, graded_at = ?
                    WHERE id = ?
                    """,
                    (actual_val, 1 if hit else 0, 1 if hit_sb else (0 if hit_sb is False else None),
                     margin, datetime.now().isoformat(), pick["id"])
                )
                
                graded += 1
                if hit:
                    hits += 1
                if hit_sb:
                    hits_vs_sb += 1
            
            # Update version totals
            conn.execute(
                """
                UPDATE model_versions
                SET total_picks_hit = total_picks_hit + ?
                WHERE id = ?
                """,
                (hits, version_id)
            )
            conn.commit()
            
            return {
                "graded": graded,
                "hits": hits,
                "hit_rate": hits / graded if graded > 0 else 0,
                "hits_vs_sportsbook": hits_vs_sb,
            }
    
    # =========================================================================
    # Backtest Management
    # =========================================================================
    
    def save_backtest(self, summary: BacktestSummary) -> int:
        """Save backtest results and return the backtest ID."""
        with self.db.connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO model_version_backtests (
                    version_id, start_date, end_date, days_tested, total_games,
                    total_picks, hits, misses, hit_rate,
                    premium_picks, premium_hits, premium_rate,
                    high_picks, high_hits, high_rate,
                    pts_picks, pts_hits, pts_rate,
                    reb_picks, reb_hits, reb_rate,
                    ast_picks, ast_hits, ast_rate,
                    over_picks, over_hits, over_rate,
                    under_picks, under_hits, under_rate,
                    picks_with_sportsbook_line, hits_vs_sportsbook, rate_vs_sportsbook,
                    avg_line_diff, mae_pts, mae_reb, mae_ast, simulated_roi,
                    daily_results_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    summary.version_id, summary.start_date, summary.end_date,
                    summary.days_tested, summary.total_games,
                    summary.total_picks, summary.hits, summary.misses, summary.hit_rate,
                    summary.premium_picks, summary.premium_hits,
                    summary.premium_hits / summary.premium_picks if summary.premium_picks > 0 else 0,
                    summary.high_picks, summary.high_hits,
                    summary.high_hits / summary.high_picks if summary.high_picks > 0 else 0,
                    summary.pts_picks, summary.pts_hits,
                    summary.pts_hits / summary.pts_picks if summary.pts_picks > 0 else 0,
                    summary.reb_picks, summary.reb_hits,
                    summary.reb_hits / summary.reb_picks if summary.reb_picks > 0 else 0,
                    summary.ast_picks, summary.ast_hits,
                    summary.ast_hits / summary.ast_picks if summary.ast_picks > 0 else 0,
                    summary.over_picks, summary.over_hits,
                    summary.over_hits / summary.over_picks if summary.over_picks > 0 else 0,
                    summary.under_picks, summary.under_hits,
                    summary.under_hits / summary.under_picks if summary.under_picks > 0 else 0,
                    summary.picks_with_sportsbook_line, summary.hits_vs_sportsbook,
                    summary.rate_vs_sportsbook, summary.avg_line_diff,
                    summary.mae_pts, summary.mae_reb, summary.mae_ast,
                    summary.simulated_roi, json.dumps(summary.daily_results)
                )
            )
            
            # Update version stats
            conn.execute(
                """
                UPDATE model_versions 
                SET total_backtests = total_backtests + 1,
                    best_hit_rate = CASE 
                        WHEN best_hit_rate IS NULL OR ? > best_hit_rate THEN ?
                        ELSE best_hit_rate
                    END,
                    avg_hit_rate = CASE
                        WHEN avg_hit_rate IS NULL THEN ?
                        ELSE (avg_hit_rate * (total_backtests - 1) + ?) / total_backtests
                    END
                WHERE id = ?
                """,
                (summary.hit_rate, summary.hit_rate, summary.hit_rate, summary.hit_rate, summary.version_id)
            )
            conn.commit()
            return cursor.lastrowid
    
    def get_backtests(self, version_id: int) -> List[Dict]:
        """Get all backtests for a model version."""
        with self.db.connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM model_version_backtests
                WHERE version_id = ?
                ORDER BY run_at DESC
                """,
                (version_id,)
            ).fetchall()
            return [dict(r) for r in rows]
    
    # =========================================================================
    # Insights Management
    # =========================================================================
    
    def add_insight(self, insight: ModelInsight):
        """Add an insight for a model version."""
        with self.db.connect() as conn:
            conn.execute(
                """
                INSERT INTO model_version_insights (version_id, insight_type, category, insight, evidence)
                VALUES (?, ?, ?, ?, ?)
                """,
                (insight.version_id, insight.insight_type, insight.category,
                 insight.insight, insight.evidence)
            )
            conn.commit()
    
    def get_insights(self, version_id: int) -> List[ModelInsight]:
        """Get all insights for a model version."""
        with self.db.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM model_version_insights WHERE version_id = ?",
                (version_id,)
            ).fetchall()
            
            return [
                ModelInsight(
                    version_id=r["version_id"],
                    insight_type=r["insight_type"],
                    category=r["category"],
                    insight=r["insight"],
                    evidence=r["evidence"],
                )
                for r in rows
            ]
    
    # =========================================================================
    # Model Grading
    # =========================================================================
    
    def calculate_grade(self, hit_rate: float) -> str:
        """Calculate letter grade from hit rate."""
        if hit_rate >= 0.65:
            return "A"
        elif hit_rate >= 0.58:
            return "B"
        elif hit_rate >= 0.52:
            return "C"
        elif hit_rate >= 0.48:
            return "D"
        else:
            return "F"
    
    def update_grades(self, version_id: int):
        """Update grades for a model version based on its backtests."""
        with self.db.connect() as conn:
            # Get aggregate stats
            row = conn.execute(
                """
                SELECT 
                    SUM(total_picks) as total_picks,
                    SUM(hits) as hits,
                    SUM(pts_picks) as pts_picks,
                    SUM(pts_hits) as pts_hits,
                    SUM(reb_picks) as reb_picks,
                    SUM(reb_hits) as reb_hits,
                    SUM(ast_picks) as ast_picks,
                    SUM(ast_hits) as ast_hits
                FROM model_version_backtests
                WHERE version_id = ?
                """,
                (version_id,)
            ).fetchone()
            
            if not row or not row["total_picks"]:
                return
            
            overall_rate = row["hits"] / row["total_picks"]
            pts_rate = row["pts_hits"] / row["pts_picks"] if row["pts_picks"] else 0
            reb_rate = row["reb_hits"] / row["reb_picks"] if row["reb_picks"] else 0
            ast_rate = row["ast_hits"] / row["ast_picks"] if row["ast_picks"] else 0
            
            conn.execute(
                """
                UPDATE model_versions
                SET overall_grade = ?, pts_grade = ?, reb_grade = ?, ast_grade = ?
                WHERE id = ?
                """,
                (
                    self.calculate_grade(overall_rate),
                    self.calculate_grade(pts_rate),
                    self.calculate_grade(reb_rate),
                    self.calculate_grade(ast_rate),
                    version_id
                )
            )
            conn.commit()
    
    # =========================================================================
    # Model Comparison
    # =========================================================================
    
    def compare_versions(
        self,
        version_ids: List[int],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Compare multiple model versions.
        
        Returns ranking and detailed comparison metrics.
        """
        with self.db.connect() as conn:
            results = []
            
            for vid in version_ids:
                version = self.get_version(vid)
                if not version:
                    continue
                
                # Get backtest data for period
                query = """
                    SELECT 
                        SUM(total_picks) as picks,
                        SUM(hits) as hits,
                        AVG(hit_rate) as avg_rate,
                        SUM(pts_picks) as pts_picks,
                        SUM(pts_hits) as pts_hits,
                        SUM(reb_picks) as reb_picks,
                        SUM(reb_hits) as reb_hits,
                        SUM(picks_with_sportsbook_line) as sb_picks,
                        SUM(hits_vs_sportsbook) as sb_hits
                    FROM model_version_backtests
                    WHERE version_id = ?
                """
                params = [vid]
                
                if start_date:
                    query += " AND end_date >= ?"
                    params.append(start_date)
                if end_date:
                    query += " AND start_date <= ?"
                    params.append(end_date)
                
                row = conn.execute(query, params).fetchone()
                
                if row and row["picks"]:
                    results.append({
                        "version_id": vid,
                        "name": version.name,
                        "version": version.version,
                        "total_picks": row["picks"],
                        "hits": row["hits"],
                        "hit_rate": row["hits"] / row["picks"],
                        "pts_rate": row["pts_hits"] / row["pts_picks"] if row["pts_picks"] else 0,
                        "reb_rate": row["reb_hits"] / row["reb_picks"] if row["reb_picks"] else 0,
                        "sb_picks": row["sb_picks"] or 0,
                        "sb_rate": row["sb_hits"] / row["sb_picks"] if row["sb_picks"] else None,
                        "grade": version.overall_grade,
                    })
            
            # Rank by hit rate
            results.sort(key=lambda x: x["hit_rate"], reverse=True)
            
            # Save comparison
            if results:
                winner = results[0]["version_id"]
                conn.execute(
                    """
                    INSERT INTO model_comparisons (version_ids_json, comparison_period_start,
                        comparison_period_end, winner_version_id, ranking_json, metrics_json)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        json.dumps(version_ids), start_date, end_date, winner,
                        json.dumps([r["version_id"] for r in results]),
                        json.dumps(results)
                    )
                )
                conn.commit()
            
            return {
                "ranking": results,
                "winner": results[0] if results else None,
                "comparison_count": len(results),
            }
    
    def get_comparison_report(self) -> str:
        """Generate a text report comparing all non-deprecated versions."""
        versions = self.list_versions(include_deprecated=False)
        
        if not versions:
            return "No model versions registered."
        
        lines = [
            "=" * 70,
            "MODEL VERSION COMPARISON REPORT",
            "=" * 70,
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"Total Versions: {len(versions)}",
            "",
        ]
        
        # Sort by best hit rate
        versions.sort(key=lambda v: v.best_hit_rate or 0, reverse=True)
        
        for i, v in enumerate(versions, 1):
            active = " [ACTIVE]" if v.is_active else ""
            lines.extend([
                f"#{i}: {v.name} (v{v.version}){active}",
                f"    Grade: {v.overall_grade or 'N/A'} | Best: {v.best_hit_rate*100:.1f}% | Avg: {(v.avg_hit_rate or 0)*100:.1f}%",
                f"    Picks: {v.total_picks_made} made, {v.total_picks_hit} hit ({v.hit_rate*100:.1f}%)",
                f"    Backtests: {v.total_backtests}",
                "",
            ])
        
        return "\n".join(lines)


# ============================================================================
# Convenience Functions
# ============================================================================

def get_tracker(db_path: str = "data/db/nba_props.sqlite3") -> ModelVersionTracker:
    """Get a ModelVersionTracker instance."""
    return ModelVersionTracker(db_path)


def register_model_version(
    name: str,
    version: str,
    config: Dict[str, Any],
    description: str = "",
    set_active: bool = False,
    db_path: str = "data/db/nba_props.sqlite3",
) -> int:
    """Register a new model version and return its ID."""
    tracker = get_tracker(db_path)
    return tracker.register_version(name, version, config, description, set_active)


def save_model_picks(
    version_id: int,
    picks: List[VersionPick],
    db_path: str = "data/db/nba_props.sqlite3",
) -> int:
    """Save picks from a model version."""
    tracker = get_tracker(db_path)
    return tracker.save_picks(version_id, picks)


def save_backtest_results(
    summary: BacktestSummary,
    db_path: str = "data/db/nba_props.sqlite3",
) -> int:
    """Save backtest results."""
    tracker = get_tracker(db_path)
    return tracker.save_backtest(summary)


def get_model_comparison(
    db_path: str = "data/db/nba_props.sqlite3",
) -> str:
    """Get a comparison report of all model versions."""
    tracker = get_tracker(db_path)
    return tracker.get_comparison_report()


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    tracker = get_tracker()
    print(tracker.get_comparison_report())

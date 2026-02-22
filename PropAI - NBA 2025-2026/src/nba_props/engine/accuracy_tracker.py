"""
Accuracy Tracking Module
========================

Track historical prediction accuracy to:
1. Calibrate confidence scores
2. Identify which factors are actually predictive
3. Measure model performance over time

Key Features:
- Store predictions with timestamps
- Compare predictions to actual outcomes
- Calculate calibration metrics
- Identify profitable vs unprofitable bet types

Module Author: NBA Props Team
Last Updated: January 2026
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Tuple
import math


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class PredictionRecord:
    """A single prediction record for tracking."""
    id: Optional[int]
    created_at: str
    game_date: str
    player_id: int
    player_name: str
    team_abbrev: str
    opponent_abbrev: str
    
    # Prediction details
    prop_type: str  # PTS, REB, AST
    direction: str  # OVER, UNDER
    line: float
    projected_value: float
    projected_std: float
    
    # Edge and confidence
    edge_pct: float
    confidence_score: float
    confidence_tier: str  # HIGH, MEDIUM, LOW
    
    # Actual outcome (filled in after game)
    actual_value: Optional[float] = None
    hit: Optional[bool] = None
    
    # Context factors used
    is_b2b: bool = False
    rest_days: int = 1
    spread: Optional[float] = None
    defense_factor: Optional[float] = None


@dataclass
class CalibrationBucket:
    """Calibration data for a confidence range."""
    confidence_min: float
    confidence_max: float
    predictions: int
    hits: int
    hit_rate: float
    expected_rate: float  # Based on edges
    calibration_error: float


@dataclass
class FactorPerformance:
    """Performance metrics for a specific factor."""
    factor_name: str
    total_predictions: int
    hits: int
    hit_rate: float
    avg_edge: float
    roi: float  # Return on investment at -110
    is_profitable: bool


@dataclass
class AccuracyReport:
    """Complete accuracy report."""
    period_start: str
    period_end: str
    total_predictions: int
    total_hits: int
    overall_hit_rate: float
    
    # By confidence tier
    high_confidence_hits: int
    high_confidence_total: int
    high_confidence_rate: float
    
    medium_confidence_hits: int
    medium_confidence_total: int
    medium_confidence_rate: float
    
    low_confidence_hits: int
    low_confidence_total: int
    low_confidence_rate: float
    
    # By prop type
    pts_hit_rate: float
    reb_hit_rate: float
    ast_hit_rate: float
    
    # By direction
    over_hit_rate: float
    under_hit_rate: float
    
    # Calibration
    calibration_buckets: List[CalibrationBucket] = field(default_factory=list)
    
    # Factor performance
    factor_performance: Dict[str, FactorPerformance] = field(default_factory=dict)
    
    # ROI metrics (assuming -110 odds)
    total_units_wagered: float = 0.0
    total_units_won: float = 0.0
    roi_pct: float = 0.0


# ============================================================================
# Database Setup
# ============================================================================

def create_tracking_tables(conn: sqlite3.Connection) -> None:
    """Create tables for prediction tracking."""
    conn.executescript("""
        -- Predictions table
        CREATE TABLE IF NOT EXISTS prediction_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            game_date TEXT NOT NULL,
            player_id INTEGER NOT NULL,
            player_name TEXT NOT NULL,
            team_abbrev TEXT NOT NULL,
            opponent_abbrev TEXT NOT NULL,
            
            prop_type TEXT NOT NULL,
            direction TEXT NOT NULL,
            line REAL NOT NULL,
            projected_value REAL NOT NULL,
            projected_std REAL NOT NULL,
            
            edge_pct REAL NOT NULL,
            confidence_score REAL NOT NULL,
            confidence_tier TEXT NOT NULL,
            
            actual_value REAL,
            hit INTEGER,
            
            is_b2b INTEGER DEFAULT 0,
            rest_days INTEGER DEFAULT 1,
            spread REAL,
            defense_factor REAL,
            
            -- Indexes
            UNIQUE(game_date, player_id, prop_type, direction)
        );
        
        CREATE INDEX IF NOT EXISTS idx_prediction_log_date ON prediction_log(game_date);
        CREATE INDEX IF NOT EXISTS idx_prediction_log_player ON prediction_log(player_id);
        CREATE INDEX IF NOT EXISTS idx_prediction_log_confidence ON prediction_log(confidence_tier);
        
        -- Factor tracking table
        CREATE TABLE IF NOT EXISTS prediction_factors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            prediction_id INTEGER NOT NULL,
            factor_name TEXT NOT NULL,
            factor_value REAL NOT NULL,
            factor_weight REAL DEFAULT 1.0,
            FOREIGN KEY (prediction_id) REFERENCES prediction_log(id)
        );
        
        CREATE INDEX IF NOT EXISTS idx_prediction_factors_pred ON prediction_factors(prediction_id);
    """)
    conn.commit()


# ============================================================================
# Recording Predictions
# ============================================================================

def record_prediction(
    conn: sqlite3.Connection,
    prediction: PredictionRecord,
    factors: Optional[Dict[str, float]] = None
) -> int:
    """
    Record a prediction for tracking.
    
    Args:
        conn: Database connection
        prediction: PredictionRecord to store
        factors: Optional dictionary of factors used in prediction
    
    Returns:
        Prediction ID
    """
    cursor = conn.execute("""
        INSERT OR REPLACE INTO prediction_log (
            created_at, game_date, player_id, player_name,
            team_abbrev, opponent_abbrev, prop_type, direction,
            line, projected_value, projected_std, edge_pct,
            confidence_score, confidence_tier, actual_value, hit,
            is_b2b, rest_days, spread, defense_factor
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        prediction.created_at or datetime.now().isoformat(),
        prediction.game_date,
        prediction.player_id,
        prediction.player_name,
        prediction.team_abbrev,
        prediction.opponent_abbrev,
        prediction.prop_type,
        prediction.direction,
        prediction.line,
        prediction.projected_value,
        prediction.projected_std,
        prediction.edge_pct,
        prediction.confidence_score,
        prediction.confidence_tier,
        prediction.actual_value,
        1 if prediction.hit else (0 if prediction.hit is False else None),
        1 if prediction.is_b2b else 0,
        prediction.rest_days,
        prediction.spread,
        prediction.defense_factor
    ))
    
    prediction_id = cursor.lastrowid
    
    # Record factors if provided
    if factors:
        for factor_name, factor_value in factors.items():
            conn.execute("""
                INSERT INTO prediction_factors (prediction_id, factor_name, factor_value)
                VALUES (?, ?, ?)
            """, (prediction_id, factor_name, factor_value))
    
    conn.commit()
    return prediction_id


def update_prediction_outcome(
    conn: sqlite3.Connection,
    game_date: str,
    player_id: int,
    prop_type: str,
    direction: str,
    actual_value: float
) -> bool:
    """
    Update a prediction with the actual outcome.
    
    Args:
        conn: Database connection
        game_date: Game date
        player_id: Player ID
        prop_type: PTS, REB, AST
        direction: OVER, UNDER
        actual_value: Actual stat value
    
    Returns:
        True if prediction was updated
    """
    # Get the prediction
    row = conn.execute("""
        SELECT id, line, direction FROM prediction_log
        WHERE game_date = ? AND player_id = ? AND prop_type = ? AND direction = ?
    """, (game_date, player_id, prop_type, direction)).fetchone()
    
    if not row:
        return False
    
    line = row["line"]
    direction = row["direction"]
    
    # Determine if hit
    if direction == "OVER":
        hit = actual_value > line
    else:  # UNDER
        hit = actual_value < line
    
    conn.execute("""
        UPDATE prediction_log
        SET actual_value = ?, hit = ?
        WHERE id = ?
    """, (actual_value, 1 if hit else 0, row["id"]))
    
    conn.commit()
    return True


def batch_update_outcomes(
    conn: sqlite3.Connection,
    game_date: str
) -> int:
    """
    Update all predictions for a game date with actual outcomes from boxscores.
    
    Args:
        conn: Database connection
        game_date: Game date to update
    
    Returns:
        Number of predictions updated
    """
    # Get predictions for this date that don't have outcomes yet
    predictions = conn.execute("""
        SELECT id, player_id, prop_type, direction, line
        FROM prediction_log
        WHERE game_date = ? AND actual_value IS NULL
    """, (game_date,)).fetchall()
    
    updated = 0
    
    for pred in predictions:
        # Get actual stat from boxscore
        stat_col = pred["prop_type"].lower()
        
        row = conn.execute(f"""
            SELECT b.{stat_col} as actual
            FROM boxscore_player b
            JOIN games g ON g.id = b.game_id
            WHERE g.game_date = ? AND b.player_id = ?
        """, (game_date, pred["player_id"])).fetchone()
        
        if row and row["actual"] is not None:
            actual = row["actual"]
            line = pred["line"]
            direction = pred["direction"]
            
            if direction == "OVER":
                hit = actual > line
            else:
                hit = actual < line
            
            conn.execute("""
                UPDATE prediction_log
                SET actual_value = ?, hit = ?
                WHERE id = ?
            """, (actual, 1 if hit else 0, pred["id"]))
            
            updated += 1
    
    conn.commit()
    return updated


# ============================================================================
# Accuracy Analysis
# ============================================================================

def generate_accuracy_report(
    conn: sqlite3.Connection,
    days_back: int = 30,
    min_predictions: int = 10
) -> Optional[AccuracyReport]:
    """
    Generate comprehensive accuracy report.
    
    Args:
        conn: Database connection
        days_back: Number of days to analyze
        min_predictions: Minimum predictions required
    
    Returns:
        AccuracyReport or None if insufficient data
    """
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
    
    # Get all predictions with outcomes
    rows = conn.execute("""
        SELECT *
        FROM prediction_log
        WHERE game_date >= ? AND game_date <= ?
          AND actual_value IS NOT NULL
          AND hit IS NOT NULL
    """, (start_date, end_date)).fetchall()
    
    if len(rows) < min_predictions:
        return None
    
    # Basic stats
    total = len(rows)
    hits = sum(1 for r in rows if r["hit"])
    overall_rate = hits / total if total > 0 else 0
    
    # By confidence tier
    high_preds = [r for r in rows if r["confidence_tier"] == "HIGH"]
    med_preds = [r for r in rows if r["confidence_tier"] == "MEDIUM"]
    low_preds = [r for r in rows if r["confidence_tier"] == "LOW"]
    
    high_hits = sum(1 for r in high_preds if r["hit"])
    med_hits = sum(1 for r in med_preds if r["hit"])
    low_hits = sum(1 for r in low_preds if r["hit"])
    
    # By prop type
    pts_preds = [r for r in rows if r["prop_type"] == "PTS"]
    reb_preds = [r for r in rows if r["prop_type"] == "REB"]
    ast_preds = [r for r in rows if r["prop_type"] == "AST"]
    
    pts_rate = sum(1 for r in pts_preds if r["hit"]) / len(pts_preds) if pts_preds else 0
    reb_rate = sum(1 for r in reb_preds if r["hit"]) / len(reb_preds) if reb_preds else 0
    ast_rate = sum(1 for r in ast_preds if r["hit"]) / len(ast_preds) if ast_preds else 0
    
    # By direction
    over_preds = [r for r in rows if r["direction"] == "OVER"]
    under_preds = [r for r in rows if r["direction"] == "UNDER"]
    
    over_rate = sum(1 for r in over_preds if r["hit"]) / len(over_preds) if over_preds else 0
    under_rate = sum(1 for r in under_preds if r["hit"]) / len(under_preds) if under_preds else 0
    
    # ROI calculation (assuming -110 odds, need 52.4% to break even)
    units_wagered = total
    units_won = hits * (100/110)  # Win pays 0.909 units at -110
    units_lost = (total - hits)
    roi_pct = ((units_won - units_lost) / units_wagered) * 100 if units_wagered > 0 else 0
    
    # Calibration buckets
    calibration = _calculate_calibration(rows)
    
    return AccuracyReport(
        period_start=start_date,
        period_end=end_date,
        total_predictions=total,
        total_hits=hits,
        overall_hit_rate=round(overall_rate, 3),
        
        high_confidence_hits=high_hits,
        high_confidence_total=len(high_preds),
        high_confidence_rate=round(high_hits / len(high_preds), 3) if high_preds else 0,
        
        medium_confidence_hits=med_hits,
        medium_confidence_total=len(med_preds),
        medium_confidence_rate=round(med_hits / len(med_preds), 3) if med_preds else 0,
        
        low_confidence_hits=low_hits,
        low_confidence_total=len(low_preds),
        low_confidence_rate=round(low_hits / len(low_preds), 3) if low_preds else 0,
        
        pts_hit_rate=round(pts_rate, 3),
        reb_hit_rate=round(reb_rate, 3),
        ast_hit_rate=round(ast_rate, 3),
        
        over_hit_rate=round(over_rate, 3),
        under_hit_rate=round(under_rate, 3),
        
        calibration_buckets=calibration,
        
        total_units_wagered=units_wagered,
        total_units_won=round(units_won, 2),
        roi_pct=round(roi_pct, 2)
    )


def _calculate_calibration(rows: List) -> List[CalibrationBucket]:
    """Calculate calibration buckets by edge percentage."""
    buckets = [
        (0.00, 0.05),
        (0.05, 0.08),
        (0.08, 0.12),
        (0.12, 0.15),
        (0.15, 0.20),
        (0.20, 1.00),
    ]
    
    result = []
    
    for min_edge, max_edge in buckets:
        bucket_rows = [r for r in rows if min_edge <= r["edge_pct"] / 100 < max_edge]
        
        if not bucket_rows:
            continue
        
        predictions = len(bucket_rows)
        hits = sum(1 for r in bucket_rows if r["hit"])
        hit_rate = hits / predictions
        
        # Expected rate based on average edge (at -110, 50% = 0 edge)
        avg_edge = sum(r["edge_pct"] for r in bucket_rows) / predictions / 100
        expected_rate = 0.524 + avg_edge  # Break-even is 52.4% at -110
        
        calibration_error = abs(hit_rate - expected_rate)
        
        result.append(CalibrationBucket(
            confidence_min=min_edge,
            confidence_max=max_edge,
            predictions=predictions,
            hits=hits,
            hit_rate=round(hit_rate, 3),
            expected_rate=round(expected_rate, 3),
            calibration_error=round(calibration_error, 3)
        ))
    
    return result


def analyze_factor_performance(
    conn: sqlite3.Connection,
    days_back: int = 30
) -> Dict[str, FactorPerformance]:
    """
    Analyze which factors are actually predictive.
    
    Args:
        conn: Database connection
        days_back: Days to analyze
    
    Returns:
        Dictionary of factor name -> FactorPerformance
    """
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
    
    # Get all factors with outcomes
    rows = conn.execute("""
        SELECT pf.factor_name, pf.factor_value, pl.hit, pl.edge_pct
        FROM prediction_factors pf
        JOIN prediction_log pl ON pl.id = pf.prediction_id
        WHERE pl.game_date >= ? AND pl.game_date <= ?
          AND pl.hit IS NOT NULL
    """, (start_date, end_date)).fetchall()
    
    # Group by factor
    factors = {}
    for r in rows:
        fname = r["factor_name"]
        if fname not in factors:
            factors[fname] = []
        factors[fname].append({
            "value": r["factor_value"],
            "hit": r["hit"],
            "edge_pct": r["edge_pct"]
        })
    
    result = {}
    for fname, data in factors.items():
        total = len(data)
        hits = sum(1 for d in data if d["hit"])
        hit_rate = hits / total if total > 0 else 0
        avg_edge = sum(d["edge_pct"] for d in data) / total if total > 0 else 0
        
        # ROI at -110
        units_won = hits * (100/110)
        units_lost = total - hits
        roi = ((units_won - units_lost) / total) * 100 if total > 0 else 0
        
        result[fname] = FactorPerformance(
            factor_name=fname,
            total_predictions=total,
            hits=hits,
            hit_rate=round(hit_rate, 3),
            avg_edge=round(avg_edge, 2),
            roi=round(roi, 2),
            is_profitable=roi > 0
        )
    
    return result


# ============================================================================
# Confidence Calibration
# ============================================================================

def get_recommended_confidence_adjustment(
    conn: sqlite3.Connection,
    days_back: int = 60
) -> Dict[str, float]:
    """
    Based on historical performance, suggest confidence adjustments.
    
    Returns:
        Dictionary with suggested multipliers for each confidence tier
    """
    report = generate_accuracy_report(conn, days_back)
    
    if not report:
        return {"HIGH": 1.0, "MEDIUM": 1.0, "LOW": 1.0}
    
    # Target rates: HIGH should hit 60%+, MEDIUM 55%+, LOW 52%+
    targets = {"HIGH": 0.60, "MEDIUM": 0.55, "LOW": 0.52}
    
    adjustments = {}
    
    # High confidence
    if report.high_confidence_total >= 10:
        actual = report.high_confidence_rate
        target = targets["HIGH"]
        # If hitting below target, lower confidence; above, raise it
        adjustments["HIGH"] = round(actual / target, 3) if target > 0 else 1.0
    else:
        adjustments["HIGH"] = 1.0
    
    # Medium confidence
    if report.medium_confidence_total >= 10:
        actual = report.medium_confidence_rate
        target = targets["MEDIUM"]
        adjustments["MEDIUM"] = round(actual / target, 3) if target > 0 else 1.0
    else:
        adjustments["MEDIUM"] = 1.0
    
    # Low confidence
    if report.low_confidence_total >= 10:
        actual = report.low_confidence_rate
        target = targets["LOW"]
        adjustments["LOW"] = round(actual / target, 3) if target > 0 else 1.0
    else:
        adjustments["LOW"] = 1.0
    
    return adjustments


# ============================================================================
# Quick Lookups
# ============================================================================

def get_player_prediction_history(
    conn: sqlite3.Connection,
    player_id: int,
    prop_type: Optional[str] = None,
    limit: int = 20
) -> List[Dict]:
    """Get recent predictions for a player."""
    if prop_type:
        rows = conn.execute("""
            SELECT * FROM prediction_log
            WHERE player_id = ? AND prop_type = ?
            ORDER BY game_date DESC
            LIMIT ?
        """, (player_id, prop_type, limit)).fetchall()
    else:
        rows = conn.execute("""
            SELECT * FROM prediction_log
            WHERE player_id = ?
            ORDER BY game_date DESC
            LIMIT ?
        """, (player_id, limit)).fetchall()
    
    return [dict(r) for r in rows]


def get_recent_hit_rate(
    conn: sqlite3.Connection,
    days_back: int = 7,
    confidence_tier: Optional[str] = None
) -> Dict:
    """Get quick hit rate summary for recent days."""
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
    
    if confidence_tier:
        rows = conn.execute("""
            SELECT COUNT(*) as total,
                   SUM(CASE WHEN hit = 1 THEN 1 ELSE 0 END) as hits
            FROM prediction_log
            WHERE game_date >= ? AND game_date <= ?
              AND hit IS NOT NULL
              AND confidence_tier = ?
        """, (start_date, end_date, confidence_tier)).fetchone()
    else:
        rows = conn.execute("""
            SELECT COUNT(*) as total,
                   SUM(CASE WHEN hit = 1 THEN 1 ELSE 0 END) as hits
            FROM prediction_log
            WHERE game_date >= ? AND game_date <= ?
              AND hit IS NOT NULL
        """, (start_date, end_date)).fetchone()
    
    total = rows["total"] or 0
    hits = rows["hits"] or 0
    
    return {
        "period": f"Last {days_back} days",
        "total": total,
        "hits": hits,
        "hit_rate": round(hits / total, 3) if total > 0 else 0,
        "confidence_tier": confidence_tier or "ALL"
    }

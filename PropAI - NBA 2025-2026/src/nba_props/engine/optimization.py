from __future__ import annotations

import sqlite3
import itertools
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import List, Dict, Optional

from ..db import Db
from ..team_aliases import abbrev_from_team_name
from .projector import ProjectionConfig, project_player_stats

@dataclass
class ModelEvaluationResult:
    config_name: str
    config: Dict
    mae_pts: float
    mae_reb: float
    mae_ast: float
    total_samples: int
    
    @property
    def total_mae(self) -> float:
        # Weighted MAE (PTS is usually ~20, REB/AST ~5)
        # Normalize roughly: PTS + 4*REB + 4*AST to give equal weight to each stat category's error
        return self.mae_pts + 4 * self.mae_reb + 4 * self.mae_ast
    
    def to_dict(self):
        return {
            "config_name": self.config_name,
            "config": self.config,
            "mae_pts": self.mae_pts,
            "mae_reb": self.mae_reb,
            "mae_ast": self.mae_ast,
            "total_mae": self.total_mae,
            "total_samples": self.total_samples
        }

def evaluate_model_config(
    config_params: Dict, 
    start_date: str, 
    end_date: str,
    db_path: str = "data/db/nba_props.sqlite3"
) -> ModelEvaluationResult:
    """
    Evaluates a specific model configuration over a date range.
    Returns error metrics (MAE).
    """
    db = Db(db_path)
    proj_config = ProjectionConfig(**config_params)
    
    errors = {
        "pts": [],
        "reb": [],
        "ast": []
    }
    
    # Re-implementing the loop cleanly
    with db.connect() as conn:
        # Pre-fetch team names
        team_id_to_name = dict(conn.execute("SELECT id, name FROM teams").fetchall())
        
        # Get all games in range
        games = conn.execute(
            "SELECT id, game_date, team1_id, team2_id FROM games WHERE game_date BETWEEN ? AND ? ORDER BY game_date",
            (start_date, end_date)
        ).fetchall()
        
        for game_row in games:
            game_id = game_row["id"]
            game_date = game_row["game_date"]
            team1_id = game_row["team1_id"]
            team2_id = game_row["team2_id"]
            
            # Process Team 1 players
            process_team_players(conn, game_id, team1_id, team2_id, game_date, team_id_to_name, proj_config, errors)
            # Process Team 2 players
            process_team_players(conn, game_id, team2_id, team1_id, game_date, team_id_to_name, proj_config, errors)

    mae_pts = sum(errors["pts"]) / len(errors["pts"]) if errors["pts"] else 0
    mae_reb = sum(errors["reb"]) / len(errors["reb"]) if errors["reb"] else 0
    mae_ast = sum(errors["ast"]) / len(errors["ast"]) if errors["ast"] else 0
    
    return ModelEvaluationResult(
        config_name="Custom",
        config=config_params,
        mae_pts=mae_pts,
        mae_reb=mae_reb,
        mae_ast=mae_ast,
        total_samples=len(errors["pts"])
    )

def process_team_players(conn, game_id, team_id, opp_id, game_date, team_map, config, errors):
    team_name = team_map.get(team_id)
    opp_name = team_map.get(opp_id)
    if not team_name or not opp_name:
        return

    # Opponent Abbrev
    opp_abbrev = abbrev_from_team_name(opp_name)
    
    # Get players stats
    players = conn.execute(
        "SELECT player_id, pts, reb, ast FROM boxscore_player WHERE game_id = ? AND team_id = ? AND minutes > 0",
        (game_id, team_id)
    ).fetchall()
    
    for p_row in players:
        p_id = p_row["player_id"]
        a_pts = p_row["pts"]
        a_reb = p_row["reb"]
        a_ast = p_row["ast"]
        
        proj = project_player_stats(
            conn, 
            p_id, 
            config=config, 
            opponent_abbrev=opp_abbrev,
            before_date=game_date 
        )
        
        if proj:
            errors["pts"].append(abs(proj.proj_pts - (a_pts or 0)))
            errors["reb"].append(abs(proj.proj_reb - (a_reb or 0)))
            errors["ast"].append(abs(proj.proj_ast - (a_ast or 0)))

def run_optimization_grid(start_date: str, end_date: str) -> List[ModelEvaluationResult]:
    # Define grid
    l5_weights = [0.2, 0.35, 0.5, 0.7]
    l20_weights = [0.2, 0.4, 0.6]
    season_weights = [0.1, 0.25, 0.4]
    
    results = []
    
    # Simple grid search 4x3x3 = 36 combinations
    # To save time in preview, we can reduce this or run in parallel
    
    for l5 in l5_weights:
        for l20 in l20_weights:
            for s in season_weights:
                # Basic check to skip nonsensical weights where season dominates too much or nothing sums up well
                # But our logic handles normalizing.
                
                cfg = {
                    "weight_l5": l5,
                    "weight_l20": l20,
                    "weight_season": s,
                    "recency_weight": 0.1
                }
                
                res = evaluate_model_config(cfg, start_date, end_date)
                res.config_name = f"L5:{l5}/L20:{l20}/S:{s}"
                results.append(res)
                
    return sorted(results, key=lambda x: x.total_mae)

"""Player archetype classification system.

Based on modern NBA roles beyond traditional positions:
- Offensive: Ball Handler, Shot Creator, Hub Big, Stretch Big, etc.
- Defensive: POA Defender, Wing Stopper, Roamer, Anchor Big, etc.
"""
from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from typing import Optional


# ============================================================================
# Archetype Definitions
# ============================================================================

OFFENSIVE_ARCHETYPES = {
    # Primary Ball Handlers
    "Heliocentric Creator": "Elite ball-dominant playmaker (USG% >32%, AST% >35%)",
    "PnR Maestro": "Guard who generates offense through pick-and-roll",
    "Scoring Guard": "Guard who prioritizes scoring over passing",
    "Speed Initiator": "Uses elite speed to initiate offense",
    
    # Wings
    "Isolation Scorer": "Creates own shot in isolation situations",
    "Shot Creator": "Self-generates offense from midrange/perimeter",
    "Movement Shooter": "Generates gravity by moving off screens",
    "Slasher": "Primarily attacks the rim and cuts",
    "3-and-D Wing": "Spots up for 3s and plays elite defense",
    "Point Forward": "Wing who initiates offense like a point guard",
    
    # Bigs
    "Hub Big": "Offensive fulcrum facilitating from high post",
    "Rim Runner": "Finisher relying on lobs and dunker spot",
    "Stretch Big": "Center/PF whose value is floor spacing",
    "Post Scorer": "Dominates in post-up situations",
    
    # Role Players
    "Connector": "Quick decisions, keeps ball moving, attacks closeouts",
    "Spot Up Shooter": "Stands in corners waiting for kick-outs",
}

DEFENSIVE_ARCHETYPES = {
    "POA Defender": "Point of Attack - guards opposing primary ball handler",
    "Wing Stopper": "Assigned to opponent's best scoring wing",
    "Chaser": "Trails shooters around screens",
    "Anchor Big": "Primary rim protector, plays drop coverage",
    "Switch Big": "Mobile big capable of switching onto guards",
    "Roamer": "Weak-side help defender, free safety role",
    "Low Activity": "Hidden defensively to conserve energy for offense",
    "Chased Target": "Opposing teams actively target this player",
}


@dataclass
class PlayerArchetype:
    """A player's archetype classification."""
    player_name: str
    team: str
    salary: Optional[int]
    salary_rank: Optional[int]
    
    primary_offensive: str
    secondary_offensive: Optional[str]
    defensive_role: str
    
    tier: int  # 1-6, 1 being superstars
    notes: Optional[str] = None


# ============================================================================
# Known Player Archetypes (from the archetype report)
# ============================================================================

# This is derived from the comprehensive archetype report
# Format: player_name -> (primary_off, secondary_off, defensive, tier, notes)
KNOWN_ARCHETYPES: dict[str, tuple[str, str | None, str, int, str | None]] = {
    # =========================================================================
    # Tier 1: MVP Candidates / Heliocentric Stars
    # =========================================================================
    "Luka Doncic": ("Heliocentric Creator", "Post Scorer", "Low Activity", 1, "38.3% USG, 41.4% AST"),
    "Shai Gilgeous-Alexander": ("Scoring Guard", "Slasher", "POA Defender", 1, "League leader in PPG, elite two-way"),
    "Trae Young": ("PnR Maestro", "Shot Creator", "Chased Target", 1, "2nd all-time AST%, 11.6 APG"),
    "Tyrese Haliburton": ("PnR Maestro", "Connector", "Chaser", 1, "4.73 AST/TO elite, transition hub"),
    "Jalen Brunson": ("Scoring Guard", "Connector", "Chased Target", 1, "31.6% USG, old-school craftiness"),
    "Cade Cunningham": ("PnR Maestro", "Shot Creator", "Wing Stopper", 1, "30.9% USG, 42.4% AST, big guard"),
    "Ja Morant": ("Slasher", "Connector", "Roamer", 1, "16.6 PPG in paint (historic for guard)"),
    "De'Aaron Fox": ("Speed Initiator", "Scoring Guard", "POA Defender", 1, "Clutch Player of the Year"),
    "LaMelo Ball": ("PnR Maestro", "Connector", "Chaser", 1, "6'7\" transition hub, flashy passing"),
    "Donovan Mitchell": ("Scoring Guard", "Isolation Scorer", "POA Defender", 1, "32.6% USG, explosive scorer"),
    "Stephen Curry": ("Movement Shooter", "Scoring Guard", "Chaser", 1, "Greatest shooter ever, off-ball master"),
    
    # =========================================================================
    # Tier 2: Two-Way Stars
    # =========================================================================
    "Jayson Tatum": ("Isolation Scorer", "Point Forward", "Wing Stopper", 2, "Prototype two-way wing"),
    "Anthony Edwards": ("Slasher", "Isolation Scorer", "POA Defender", 2, "Rising MVP, takes POA assignments"),
    "Jaylen Brown": ("Slasher", "Isolation Scorer", "Wing Stopper", 2, "Downhill attacking freight train"),
    "Devin Booker": ("Shot Creator", "PnR Maestro", "Chaser", 2, "Pure shot creator, evolved playmaker"),
    "Jimmy Butler": ("Slasher", "Point Forward", "Wing Stopper", 2, "Elite foul drawer, playoff performer"),
    "Kevin Durant": ("Isolation Scorer", "Spot Up Shooter", "Roamer", 2, "7-foot offensive unicorn"),
    "Kawhi Leonard": ("Isolation Scorer", "Post Scorer", "Wing Stopper", 2, "2x DPOY, elite when healthy"),
    "Paul George": ("Shot Creator", "Spot Up Shooter", "Wing Stopper", 2, "Two-way wing, relieves star pressure"),
    "Scottie Barnes": ("Point Forward", "Connector", "Roamer", 2, "23.5% AST, switchable 1-5"),
    "Paolo Banchero": ("Point Forward", "Isolation Scorer", "Switch Big", 2, "6'10\" point forward, mismatch creator"),
    "Jalen Williams": ("Slasher", "Connector", "Wing Stopper", 2, "Ideal complementary star, guards 1-4"),
    "Franz Wagner": ("Slasher", "Connector", "Wing Stopper", 2, "Elite euro-step, secondary handler"),
    "Brandon Ingram": ("Isolation Scorer", "Shot Creator", "Chaser", 2, "KD-lite build, midrange master"),
    "DeMar DeRozan": ("Isolation Scorer", "Connector", "Low Activity", 2, "Midrange specialist, underrated passer"),
    "LeBron James": ("Point Forward", "Post Scorer", "Roamer", 2, "Year 23, prototype point forward"),
    "Zion Williamson": ("Slasher", "Point Forward", "Roamer", 2, "Supersized slasher, Point Zion"),
    "James Harden": ("Scoring Guard", "Connector", "Low Activity", 2, "Elite court vision, floor general"),
    "Pascal Siakam": ("Point Forward", "Post Scorer", "Wing Stopper", 2, "Swiss-army knife, Spicy P"),
    "Lauri Markkanen": ("Stretch Big", "Slasher", "Chaser", 2, "7'0\" stretch four, MIP winner"),
    
    # =========================================================================
    # Tier 3: Elite Bigs
    # =========================================================================
    "Nikola Jokic": ("Hub Big", "Post Scorer", "Anchor Big", 3, "50.9% AST - best passing big ever"),
    "Victor Wembanyama": ("Stretch Big", "Rim Runner", "Anchor Big", 3, "7'4\" unicorn, DPOY level"),
    "Joel Embiid": ("Post Scorer", "Isolation Scorer", "Anchor Big", 3, "Former MVP, dominant post game"),
    "Anthony Davis": ("Rim Runner", "Post Scorer", "Anchor Big", 3, "Jack-of-all-trades, switchable"),
    "Giannis Antetokounmpo": ("Slasher", "Point Forward", "Roamer", 3, "Elite two-way, free safety"),
    "Bam Adebayo": ("Hub Big", "Connector", "Switch Big", 3, "Guards 1-5, switch everything"),
    "Domantas Sabonis": ("Hub Big", "Post Scorer", "Anchor Big", 3, "League rebounding leader, 7 APG"),
    "Chet Holmgren": ("Stretch Big", "Rim Runner", "Roamer", 3, "Elite 3PT + rim protection"),
    "Karl-Anthony Towns": ("Stretch Big", "Post Scorer", "Anchor Big", 3, "Best shooting 7-footer ever"),
    "Rudy Gobert": ("Rim Runner", "Connector", "Anchor Big", 3, "3x DPOY, elite drop coverage"),
    "Alperen Sengun": ("Hub Big", "Post Scorer", "Anchor Big", 3, "Mini-Jokic, 5-6 APG"),
    "Evan Mobley": ("Connector", "Rim Runner", "Roamer", 3, "DPOY candidate, switchable 1-5"),
    "Jarrett Allen": ("Rim Runner", "Connector", "Anchor Big", 3, "68.9% TS, elite efficiency"),
    "Myles Turner": ("Stretch Big", "Rim Runner", "Anchor Big", 3, "Rare spacing + shot blocking"),
    "Kristaps Porzingis": ("Stretch Big", "Rim Runner", "Anchor Big", 3, "7'3\" unicorn, deep range"),
    "Naz Reid": ("Stretch Big", "Slasher", "Switch Big", 3, "Big Jelly, can put ball on floor"),
    "Nic Claxton": ("Rim Runner", "Connector", "Switch Big", 3, "Elite switching, vertical spacer"),
    "Isaiah Hartenstein": ("Hub Big", "Rim Runner", "Anchor Big", 3, "High IQ connector big"),
    "Jalen Duren": ("Rim Runner", "Connector", "Anchor Big", 3, "67% TS, physical presence"),
    "Walker Kessler": ("Rim Runner", "Connector", "Anchor Big", 3, "Elite block rate"),
    "Ivica Zubac": ("Rim Runner", "Post Scorer", "Anchor Big", 3, "Good touch around rim"),
    "Deandre Ayton": ("Post Scorer", "Rim Runner", "Anchor Big", 3, "Midrange shooting big"),
    "Clint Capela": ("Rim Runner", "Connector", "Anchor Big", 3, "Lob threat, rebounder"),
    "Jonas Valanciunas": ("Post Scorer", "Connector", "Anchor Big", 3, "Bruising center"),
    "Nikola Vucevic": ("Hub Big", "Post Scorer", "Anchor Big", 3, "Offensive center, good passer"),
    "Brook Lopez": ("Stretch Big", "Rim Runner", "Anchor Big", 3, "Splash Mountain, elite drop"),
    "Daniel Gafford": ("Rim Runner", "Connector", "Anchor Big", 3, "Lob threat, rim protector"),
    
    # =========================================================================
    # Tier 4: Elite Role Players
    # =========================================================================
    "OG Anunoby": ("3-and-D Wing", "Slasher", "Wing Stopper", 4, "94th percentile DPM, elite corner 3s"),
    "Mikal Bridges": ("3-and-D Wing", "Connector", "Wing Stopper", 4, "Ironman durability, attacks closeouts"),
    "Derrick White": ("Connector", "3-and-D Wing", "POA Defender", 4, "Ultimate glue guy, blocks shots"),
    "Jrue Holiday": ("Connector", "3-and-D Wing", "POA Defender", 4, "POA defense standard, veteran IQ"),
    "Herbert Jones": ("Slasher", "3-and-D Wing", "Wing Stopper", 4, "Not on Herb, 80% defensive value"),
    "Alex Caruso": ("Connector", "3-and-D Wing", "POA Defender", 4, "Havoc defender, elite steals"),
    "Jalen Suggs": ("Spot Up Shooter", "Connector", "POA Defender", 4, "Full-court pressure, improved shooting"),
    "Luguentz Dort": ("Spot Up Shooter", "3-and-D Wing", "POA Defender", 4, "Dorture Chamber, physical POA"),
    "Kentavious Caldwell-Pope": ("Movement Shooter", "3-and-D Wing", "Chaser", 4, "Elite trail shooter"),
    "Donte DiVincenzo": ("Movement Shooter", "Connector", "Chaser", 4, "High energy spacer"),
    "Josh Hart": ("Connector", "Slasher", "Wing Stopper", 4, "10 RPG as guard, energy connector"),
    "Desmond Bane": ("Movement Shooter", "Connector", "Chaser", 4, "Elite catch-and-shoot, tank built"),
    "Trey Murphy III": ("Spot Up Shooter", "Slasher", "Wing Stopper", 4, "Deep spacing, athletic"),
    "Keegan Murray": ("Spot Up Shooter", "3-and-D Wing", "Wing Stopper", 4, "High-volume spot-up"),
    "Jaden McDaniels": ("3-and-D Wing", "Connector", "Wing Stopper", 4, "Length, designated wing stopper"),
    "Dillon Brooks": ("3-and-D Wing", "Isolation Scorer", "Wing Stopper", 4, "Physical stopper, villain role"),
    "Jerami Grant": ("Isolation Scorer", "Spot Up Shooter", "Wing Stopper", 4, "High-usage role player"),
    "Cameron Johnson": ("Movement Shooter", "Spot Up Shooter", "Chaser", 4, "Elite movement shooter"),
    "Norman Powell": ("Movement Shooter", "Slasher", "Chaser", 4, "Microwave scorer, instant offense"),
    "Tyler Herro": ("Shot Creator", "PnR Maestro", "Chased Target", 4, "Scoring punch, hidden on D"),
    "Marcus Smart": ("Connector", "3-and-D Wing", "POA Defender", 4, "Heart and soul, vocal leader"),
    "Christian Braun": ("Connector", "Slasher", "POA Defender", 4, "Energy wing, championship DNA"),
    "Peyton Watson": ("Slasher", "Connector", "Roamer", 4, "Elite block rate for wing"),
    
    # =========================================================================
    # Tier 5: Scoring Guards & Specialists
    # =========================================================================
    "Jamal Murray": ("PnR Maestro", "Shot Creator", "Chaser", 5, "Clutch, elite with Jokic"),
    "Kyrie Irving": ("Isolation Scorer", "Shot Creator", "Chaser", 5, "Elite handle, 90.2% FT"),
    "CJ McCollum": ("Shot Creator", "Spot Up Shooter", "Chased Target", 5, "Veteran pull-up scorer"),
    "Anfernee Simons": ("Movement Shooter", "PnR Maestro", "Chased Target", 5, "High-volume 3PT, elite range"),
    "Jordan Poole": ("Scoring Guard", "PnR Maestro", "Chased Target", 5, "High usage, high variance"),
    "Jalen Green": ("Slasher", "Shot Creator", "Chaser", 5, "Athletic scorer, improving"),
    "Bradley Beal": ("Shot Creator", "Spot Up Shooter", "Chaser", 5, "Former 30 PPG scorer"),
    "Khris Middleton": ("Shot Creator", "Spot Up Shooter", "Wing Stopper", 5, "Veteran stabilizer, midrange"),
    "Fred VanVleet": ("PnR Maestro", "Spot Up Shooter", "POA Defender", 5, "Stabilizing floor general"),
    "Austin Reaves": ("Connector", "PnR Maestro", "Chaser", 5, "Versatile, fits with stars"),
    "Malik Monk": ("Scoring Guard", "PnR Maestro", "Chaser", 5, "Elite 6th man scorer"),
    "Terry Rozier": ("Scoring Guard", "PnR Maestro", "POA Defender", 5, "Scary Terry, streaky"),
    "Coby White": ("Scoring Guard", "PnR Maestro", "Chaser", 5, "Breakout scorer, fast-paced"),
    "Josh Giddey": ("Connector", "Point Forward", "Chaser", 5, "Elite passer, SLOB wizard"),
    "RJ Barrett": ("Slasher", "Spot Up Shooter", "Wing Stopper", 5, "Physical driver"),
    "Immanuel Quickley": ("Scoring Guard", "PnR Maestro", "POA Defender", 5, "Microwave scorer, deep range"),
    "Dejounte Murray": ("PnR Maestro", "Connector", "POA Defender", 5, "Two-way guard, long arms"),
    "Bogdan Bogdanovic": ("Movement Shooter", "Connector", "Chaser", 5, "FIBA-style scorer"),
    "D'Angelo Russell": ("PnR Maestro", "Spot Up Shooter", "Chased Target", 5, "Streaky shooter/passer"),
    "Collin Sexton": ("Slasher", "Scoring Guard", "Chaser", 5, "High energy rim attacker"),
    "Darius Garland": ("PnR Maestro", "Shot Creator", "Chaser", 5, "~8 APG, 40% 3PT"),
    "Tyrese Maxey": ("Scoring Guard", "Slasher", "Chaser", 5, "Probably fastest in NBA"),
    "Zach LaVine": ("Shot Creator", "Slasher", "Chaser", 5, "2x dunk champ, athletic"),
    "Klay Thompson": ("Spot Up Shooter", "Movement Shooter", "Wing Stopper", 5, "Spacer for stars"),
    "Kyle Kuzma": ("Shot Creator", "Point Forward", "Roamer", 5, "High usage forward"),
    "Miles Bridges": ("Slasher", "Shot Creator", "Wing Stopper", 5, "Athletic scorer, powerful"),
    "Tobias Harris": ("Spot Up Shooter", "Post Scorer", "Wing Stopper", 5, "Veteran stabilizer"),
    "Caris LeVert": ("Connector", "Slasher", "Chaser", 5, "Bench creator, good passer"),
    "Grayson Allen": ("Spot Up Shooter", "Connector", "Chaser", 5, "Elite 3PT, tough"),
    "Max Strus": ("Movement Shooter", "Connector", "Chaser", 5, "High energy spacer"),
    "Gary Trent Jr.": ("Spot Up Shooter", "Movement Shooter", "Chaser", 5, "Floor spacer"),
    "Bobby Portis": ("Stretch Big", "Post Scorer", "Roamer", 5, "High energy bench big"),
    
    # =========================================================================
    # Tier 6: Rotation Pieces & Specialists
    # =========================================================================
    "Aaron Gordon": ("Slasher", "Connector", "Wing Stopper", 6, "Dunker spot, vital defense"),
    "Jonathan Kuminga": ("Slasher", "Isolation Scorer", "Wing Stopper", 6, "Athletic, developing ISO"),
    "Jabari Smith Jr.": ("Stretch Big", "3-and-D Wing", "Switch Big", 6, "3-and-D big, switchable"),
    "Amen Thompson": ("Slasher", "Connector", "POA Defender", 6, "Elite athlete/defender"),
    "Ausar Thompson": ("Slasher", "Connector", "Wing Stopper", 6, "Elite athlete, rebounder"),
    "Tari Eason": ("3-and-D Wing", "Slasher", "Wing Stopper", 6, "High motor, steal/block machine"),
    "Reed Sheppard": ("Movement Shooter", "Connector", "Chaser", 6, "Rookie sharpshooter, high IQ"),
    "Deni Avdija": ("Point Forward", "Slasher", "Wing Stopper", 6, "Versatile playmaker"),
    "Jeremy Sochan": ("Connector", "Slasher", "Wing Stopper", 6, "Rodman role, defensive specialist"),
    "Rui Hachimura": ("Spot Up Shooter", "Post Scorer", "Wing Stopper", 6, "Fits next to stars"),
    "Michael Porter Jr.": ("Spot Up Shooter", "Movement Shooter", "Roamer", 6, "Elite catch-and-shoot"),
    "De'Andre Hunter": ("3-and-D Wing", "Spot Up Shooter", "Wing Stopper", 6, "Solid two-way wing"),
    "Saddiq Bey": ("Spot Up Shooter", "Slasher", "Wing Stopper", 6, "Volume 3PT shooter"),
    "Obi Toppin": ("Rim Runner", "Spot Up Shooter", "Roamer", 6, "Transition dunker"),
    "Isaiah Stewart": ("Rim Runner", "Stretch Big", "Switch Big", 6, "Physical defender, added 3PT"),
    "Zach Collins": ("Stretch Big", "Post Scorer", "Anchor Big", 6, "Spacer for Wemby"),
    "Kelly Olynyk": ("Stretch Big", "Connector", "Anchor Big", 6, "Playmaking big"),
    "Al Horford": ("Stretch Big", "Connector", "Switch Big", 6, "Veteran leader, elite IQ"),
}


def get_player_archetype(player_name: str) -> Optional[PlayerArchetype]:
    """
    Get the archetype classification for a player.
    
    Args:
        player_name: Player's name
    
    Returns:
        PlayerArchetype or None if not classified
    """
    # Normalize name for lookup
    name_key = _normalize_name(player_name)
    
    for known_name, data in KNOWN_ARCHETYPES.items():
        if _normalize_name(known_name) == name_key:
            primary, secondary, defensive, tier, notes = data
            return PlayerArchetype(
                player_name=known_name,
                team="",  # Would need DB lookup
                salary=None,
                salary_rank=None,
                primary_offensive=primary,
                secondary_offensive=secondary,
                defensive_role=defensive,
                tier=tier,
                notes=notes,
            )
    
    return None


def _normalize_name(name: str) -> str:
    """Normalize player name for matching."""
    # Remove accents, lowercase, strip
    return re.sub(r"[^a-z\s]", "", name.lower().strip())


def classify_player_by_stats(
    conn: sqlite3.Connection,
    player_id: int,
) -> Optional[PlayerArchetype]:
    """
    Attempt to classify a player by their stats if not in known database.
    
    This is a heuristic approach based on:
    - Minutes (starters vs bench)
    - Points per game (scorers vs role players)
    - Assists per game (facilitators)
    - Position played
    - Rebounds (bigs)
    """
    # Get player stats
    row = conn.execute(
        """
        SELECT 
            p.name,
            AVG(b.minutes) as avg_min,
            AVG(b.pts) as avg_pts,
            AVG(b.ast) as avg_ast,
            AVG(b.reb) as avg_reb,
            AVG(b.tpm) as avg_3pm,
            MAX(b.pos) as pos,
            COUNT(*) as games
        FROM boxscore_player b
        JOIN players p ON p.id = b.player_id
        WHERE b.player_id = ?
          AND b.minutes > 5
        GROUP BY p.name
        """,
        (player_id,),
    ).fetchone()
    
    if not row or row["games"] < 3:
        return None
    
    # Check known archetypes first
    known = get_player_archetype(row["name"])
    if known:
        return known
    
    # Heuristic classification
    avg_min = row["avg_min"] or 0
    avg_pts = row["avg_pts"] or 0
    avg_ast = row["avg_ast"] or 0
    avg_reb = row["avg_reb"] or 0
    avg_3pm = row["avg_3pm"] or 0
    pos = (row["pos"] or "").upper()
    
    # Determine tier by minutes
    if avg_min >= 30:
        tier = 3 if avg_pts >= 20 else 4
    elif avg_min >= 20:
        tier = 5
    else:
        tier = 6
    
    # Determine offensive archetype
    if pos in ("C",) or avg_reb >= 8:
        # Big man
        if avg_3pm >= 1.5:
            primary = "Stretch Big"
        elif avg_ast >= 3:
            primary = "Hub Big"
        else:
            primary = "Rim Runner"
    elif avg_ast >= 6:
        # Facilitator
        if avg_pts >= 20:
            primary = "PnR Maestro"
        else:
            primary = "Connector"
    elif avg_pts >= 18:
        # Scorer
        if avg_3pm >= 2:
            primary = "Shot Creator"
        else:
            primary = "Slasher"
    else:
        # Role player
        if avg_3pm >= 1.5:
            primary = "3-and-D Wing"
        else:
            primary = "Spot Up Shooter"
    
    # Simplified defensive assignment
    if pos in ("C",) or avg_reb >= 8:
        defensive = "Anchor Big"
    elif avg_min >= 25:
        defensive = "Wing Stopper"
    else:
        defensive = "Chaser"
    
    return PlayerArchetype(
        player_name=row["name"],
        team="",
        salary=None,
        salary_rank=None,
        primary_offensive=primary,
        secondary_offensive=None,
        defensive_role=defensive,
        tier=tier,
        notes="Auto-classified by stats",
    )


def get_archetype_matchup_factor(
    offensive_archetype: str,
    defensive_archetype: str,
) -> float:
    """
    Get a matchup adjustment factor based on archetypes.
    
    Returns a multiplier (1.0 = neutral, >1.0 = favorable, <1.0 = unfavorable)
    """
    # Favorable matchups (offense has advantage)
    favorable = {
        ("Isolation Scorer", "Chaser"): 1.10,
        ("Slasher", "Anchor Big"): 0.95,  # Rim protection hurts slashers
        ("Hub Big", "Switch Big"): 1.08,
        ("Stretch Big", "Anchor Big"): 1.12,  # Stretch beats drop coverage
        ("Movement Shooter", "Low Activity"): 1.10,
        ("PnR Maestro", "Anchor Big"): 1.05,
        ("Post Scorer", "Chaser"): 1.15,
    }
    
    # Unfavorable matchups
    unfavorable = {
        ("Slasher", "Wing Stopper"): 0.92,
        ("Isolation Scorer", "Wing Stopper"): 0.93,
        ("Shot Creator", "POA Defender"): 0.94,
        ("PnR Maestro", "POA Defender"): 0.95,
        ("Movement Shooter", "Chaser"): 0.95,
        ("Rim Runner", "Anchor Big"): 0.90,
    }
    
    key = (offensive_archetype, defensive_archetype)
    
    if key in favorable:
        return favorable[key]
    if key in unfavorable:
        return unfavorable[key]
    
    return 1.0  # Neutral


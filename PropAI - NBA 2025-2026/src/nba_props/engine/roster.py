"""
Comprehensive NBA Player Roster System

This module provides:
1. Detailed player archetypes (offensive, defensive roles)
2. Player similarity groupings
3. Elite defender tracking for matchup analysis
4. Integration with projection adjustments

Based on modern NBA role classification moving beyond traditional positions.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


# ============================================================================
# Archetype Enums
# ============================================================================

class OffensiveRole(Enum):
    """Primary offensive archetypes."""
    # Ball Handlers
    HELIOCENTRIC_CREATOR = "Heliocentric Creator"  # USG% >32%, AST% >35%
    PNR_MAESTRO = "PnR Maestro"  # Pick-and-roll specialist
    PRIMARY_INITIATOR = "Primary Initiator"  # Team's offensive engine
    FLOOR_GENERAL = "Floor General"  # Traditional point guard
    SCORING_GUARD = "Scoring Guard"  # Score-first guard
    COMBO_GUARD = "Combo Guard"  # Can play both guard spots
    SPEED_INITIATOR = "Speed Initiator"  # Uses speed to create
    TRANSITION_HUB = "Transition Hub"  # Pushes pace, fast break specialist
    
    # Wings
    ISOLATION_SCORER = "Isolation Scorer"  # Creates own shot in ISO
    SHOT_CREATOR = "Shot Creator"  # Self-generates from midrange/perimeter
    SLASHER = "Slasher"  # Attacks rim, cuts
    SCORING_WING = "Scoring Wing"  # Primary wing scorer
    POINT_FORWARD = "Point Forward"  # Forward who initiates offense
    THREE_AND_D = "3-and-D Wing"  # Shoots 3s, plays defense
    MOVEMENT_SHOOTER = "Movement Shooter"  # Runs off screens (Curry, Bane)
    SPOT_UP_SHOOTER = "Spot Up Shooter"  # Catch and shoot specialist
    CONNECTOR = "Connector"  # Quick decisions, keeps ball moving
    
    # Bigs
    HUB_BIG = "Hub Big"  # Facilitates from high post (Jokic, Sabonis)
    RIM_RUNNER = "Rim Runner"  # Lobs, dunker spot
    STRETCH_BIG = "Stretch Big"  # Floor spacing center/PF
    POST_SCORER = "Post Scorer"  # Back-to-basket scorer
    ANCHOR_BIG = "Anchor Big"  # Rim protector, drop coverage
    VERSATILE_BIG = "Versatile Big"  # Can do multiple things
    INTERIOR_PLAYMAKER = "Interior Playmaker"  # Passes from paint
    
    # Role Players
    MICROWAVE = "Microwave"  # Instant offense off bench
    CUTTER = "Cutter"  # Off-ball movement, backdoor cuts


class DefensiveRole(Enum):
    """Defensive archetypes."""
    POA_DEFENDER = "POA Defender"  # Point of attack, guards ball handlers
    WING_STOPPER = "Wing Stopper"  # Guards best opposing wing
    CHASER = "Chaser"  # Trails shooters around screens
    ANCHOR_BIG = "Anchor Big"  # Rim protector, drop coverage
    SWITCH_BIG = "Switch Big"  # Can switch onto guards
    ROAMER = "Roamer"  # Help defender, free safety
    MOBILE_BIG = "Mobile Big"  # Can move feet on perimeter
    CHASED_TARGET = "Chased Target"  # Gets hunted defensively
    LOW_ACTIVITY = "Low Activity"  # Hidden on defense
    WING_DEFENDER = "Wing Defender"  # Solid but not elite wing D


class PlayerTier(Enum):
    """Player tier for prop betting focus."""
    MVP_CANDIDATE = 1  # Heliocentric stars
    TWO_WAY_STAR = 2  # Elite two-way players
    ELITE_BIG = 3  # Top tier bigs
    ELITE_ROLE = 4  # Championship-level role players
    SPECIALIST = 5  # Scoring specialists
    ROTATION = 6  # Rotation pieces


# ============================================================================
# Player Profile Data Structure
# ============================================================================

@dataclass
class PlayerProfile:
    """Complete player profile with archetype information."""
    name: str
    team: str
    
    # Archetypes
    primary_offensive: OffensiveRole
    secondary_offensive: Optional[OffensiveRole]
    defensive_role: DefensiveRole
    tier: PlayerTier
    
    # Additional info
    height: Optional[str] = None  # e.g., "6'6\""
    position: Optional[str] = None  # Traditional position (PG, SG, SF, PF, C)
    salary: Optional[int] = None
    
    # Play style notes
    strengths: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)
    notes: Optional[str] = None
    
    # Defensive matchup info
    guards_positions: list[str] = field(default_factory=list)  # What positions they guard
    is_elite_defender: bool = False
    avoid_betting_against: list[str] = field(default_factory=list)  # Names of defenders to avoid


# ============================================================================
# Complete Player Database
# ============================================================================

PLAYER_DATABASE: dict[str, PlayerProfile] = {
    # =========================================================================
    # TIER 1: MVP CANDIDATES / HELIOCENTRIC STARS
    # =========================================================================
    
    "Luka Doncic": PlayerProfile(
        name="Luka Doncic",
        team="Los Angeles Lakers",
        primary_offensive=OffensiveRole.HELIOCENTRIC_CREATOR,
        secondary_offensive=OffensiveRole.POST_SCORER,
        defensive_role=DefensiveRole.LOW_ACTIVITY,
        tier=PlayerTier.MVP_CANDIDATE,
        height="6'7\"",
        position="PG",
        strengths=["Elite playmaking", "Step-back 3", "Post-up smaller guards", "Triple-double machine"],
        weaknesses=["Defensive effort", "Turnovers when tired"],
        notes="38.3% USG, 41.4% AST. Ball-dominant, slows pace to manipulate mismatches.",
        guards_positions=["SG"],  # Hidden on weak offensive player
    ),
    
    "Shai Gilgeous-Alexander": PlayerProfile(
        name="Shai Gilgeous-Alexander",
        team="Oklahoma City Thunder",
        primary_offensive=OffensiveRole.PRIMARY_INITIATOR,
        secondary_offensive=OffensiveRole.SLASHER,
        defensive_role=DefensiveRole.POA_DEFENDER,
        tier=PlayerTier.MVP_CANDIDATE,
        height="6'6\"",
        position="PG",
        strengths=["Elite rim finishing", "Drawing fouls", "Midrange", "Length on defense"],
        weaknesses=["3-point volume"],
        notes="League leader in PPG. Elite two-way player, leads league in drives.",
        guards_positions=["PG", "SG"],
        is_elite_defender=True,
    ),
    
    "Trae Young": PlayerProfile(
        name="Trae Young",
        team="Atlanta Hawks",
        primary_offensive=OffensiveRole.PNR_MAESTRO,
        secondary_offensive=OffensiveRole.SHOT_CREATOR,
        defensive_role=DefensiveRole.CHASED_TARGET,
        tier=PlayerTier.MVP_CANDIDATE,
        height="6'1\"",
        position="PG",
        strengths=["Elite playmaking", "Deep 3-point range", "Floater game", "FT drawing"],
        weaknesses=["Defense", "Size", "Hunted in playoffs"],
        notes="2nd all-time in career AST%. 11.6 APG. Teams actively hunt him on switches.",
        guards_positions=["Weakest offensive player"],
    ),
    
    "Stephen Curry": PlayerProfile(
        name="Stephen Curry",
        team="Golden State Warriors",
        primary_offensive=OffensiveRole.PRIMARY_INITIATOR,
        secondary_offensive=OffensiveRole.MOVEMENT_SHOOTER,
        defensive_role=DefensiveRole.CHASER,
        tier=PlayerTier.MVP_CANDIDATE,
        height="6'2\"",
        position="PG",
        strengths=["Greatest shooter ever", "Off-ball movement", "Gravity", "Handles"],
        weaknesses=["Size on defense", "Age"],
        notes="Warps defenses with constant cuts and off-ball movement. League leader in off-ball sprint distance.",
        guards_positions=["PG", "SG"],
    ),
    
    "Nikola Jokic": PlayerProfile(
        name="Nikola Jokic",
        team="Denver Nuggets",
        primary_offensive=OffensiveRole.HUB_BIG,
        secondary_offensive=OffensiveRole.POST_SCORER,
        defensive_role=DefensiveRole.ANCHOR_BIG,
        tier=PlayerTier.MVP_CANDIDATE,
        height="6'11\"",
        position="C",
        strengths=["Best passing big ever", "Basketball IQ", "Post scoring", "Rebounding"],
        weaknesses=["Foot speed on perimeter switches"],
        notes="50.9% AST rate. Entire offense flows through high-post touches. Positional defender.",
        guards_positions=["C", "PF"],
    ),
    
    "Giannis Antetokounmpo": PlayerProfile(
        name="Giannis Antetokounmpo",
        team="Milwaukee Bucks",
        primary_offensive=OffensiveRole.SLASHER,
        secondary_offensive=OffensiveRole.POINT_FORWARD,
        defensive_role=DefensiveRole.ROAMER,
        tier=PlayerTier.MVP_CANDIDATE,
        height="6'11\"",
        position="PF",
        strengths=["Unstoppable drives", "Transition", "Help defense", "Rebounding"],
        weaknesses=["Jump shot", "FT shooting"],
        notes="League's best roamer/help defender. Paired with Lopez so he can play free safety.",
        guards_positions=["PF", "SF", "C"],
        is_elite_defender=True,
    ),
    
    "Joel Embiid": PlayerProfile(
        name="Joel Embiid",
        team="Philadelphia 76ers",
        primary_offensive=OffensiveRole.POST_SCORER,
        secondary_offensive=OffensiveRole.ISOLATION_SCORER,
        defensive_role=DefensiveRole.ANCHOR_BIG,
        tier=PlayerTier.MVP_CANDIDATE,
        height="7'0\"",
        position="C",
        strengths=["Dominant post game", "Midrange", "FT drawing", "Rim protection"],
        weaknesses=["Durability", "Conditioning late in games"],
        notes="Former MVP. Anchors defense while scoring 33+ PPG. Does things no other big can do.",
        guards_positions=["C"],
        is_elite_defender=True,
    ),
    
    "Tyrese Haliburton": PlayerProfile(
        name="Tyrese Haliburton",
        team="Indiana Pacers",
        primary_offensive=OffensiveRole.PNR_MAESTRO,
        secondary_offensive=OffensiveRole.TRANSITION_HUB,
        defensive_role=DefensiveRole.CHASER,
        tier=PlayerTier.MVP_CANDIDATE,
        height="6'5\"",
        position="PG",
        strengths=["Elite AST/TO ratio", "Transition offense", "3-point shooting", "Length"],
        weaknesses=["Creating own shot in halfcourt"],
        notes="4.73 AST/TO ratio (elite). League's premier transition hub. 10.4 APG.",
        guards_positions=["PG", "SG"],
    ),
    
    "Jalen Brunson": PlayerProfile(
        name="Jalen Brunson",
        team="New York Knicks",
        primary_offensive=OffensiveRole.SCORING_GUARD,
        secondary_offensive=OffensiveRole.PRIMARY_INITIATOR,
        defensive_role=DefensiveRole.CHASED_TARGET,
        tier=PlayerTier.MVP_CANDIDATE,
        height="6'1\"",
        position="PG",
        strengths=["Footwork", "Midrange", "Poise", "Post-up smaller guards"],
        weaknesses=["Size", "Targeted defensively"],
        notes="31.6% USG. Old-school PG who can give you 30 on a given night. Elite craftiness.",
        guards_positions=["Weakest offensive player"],
    ),
    
    "Cade Cunningham": PlayerProfile(
        name="Cade Cunningham",
        team="Detroit Pistons",
        primary_offensive=OffensiveRole.PNR_MAESTRO,
        secondary_offensive=OffensiveRole.SHOT_CREATOR,
        defensive_role=DefensiveRole.WING_STOPPER,
        tier=PlayerTier.MVP_CANDIDATE,
        height="6'6\"",
        position="PG",
        strengths=["Size for position", "Playmaking", "Can see over traps", "Improved defense"],
        weaknesses=["Efficiency historically"],
        notes="30.9% USG, 42.4% AST. Big guard who can contest larger wings defensively.",
        guards_positions=["PG", "SG", "SF"],
        is_elite_defender=True,
    ),
    
    "Ja Morant": PlayerProfile(
        name="Ja Morant",
        team="Memphis Grizzlies",
        primary_offensive=OffensiveRole.SLASHER,
        secondary_offensive=OffensiveRole.PRIMARY_INITIATOR,
        defensive_role=DefensiveRole.ROAMER,
        tier=PlayerTier.MVP_CANDIDATE,
        height="6'3\"",
        position="PG",
        strengths=["Elite athleticism", "Finishing at rim", "Transition", "Passing"],
        weaknesses=["3-point shooting", "Size on defense"],
        notes="Led NBA in points in paint for a guard (16.6 PPG). Relentless rim attacker.",
        guards_positions=["PG"],
    ),
    
    "De'Aaron Fox": PlayerProfile(
        name="De'Aaron Fox",
        team="San Antonio Spurs",
        primary_offensive=OffensiveRole.SPEED_INITIATOR,
        secondary_offensive=OffensiveRole.SCORING_GUARD,
        defensive_role=DefensiveRole.POA_DEFENDER,
        tier=PlayerTier.MVP_CANDIDATE,
        height="6'3\"",
        position="PG",
        strengths=["Elite speed", "Clutch scoring", "Improved pullup game"],
        weaknesses=["3-point volume"],
        notes="Clutch Player of the Year. Uses blinding speed to attack. Improved defensive engagement.",
        guards_positions=["PG", "SG"],
        is_elite_defender=True,
    ),
    
    "LaMelo Ball": PlayerProfile(
        name="LaMelo Ball",
        team="Charlotte Hornets",
        primary_offensive=OffensiveRole.TRANSITION_HUB,
        secondary_offensive=OffensiveRole.PNR_MAESTRO,
        defensive_role=DefensiveRole.CHASER,
        tier=PlayerTier.MVP_CANDIDATE,
        height="6'7\"",
        position="PG",
        strengths=["Flashy passing", "Court vision", "Rebounding for guard", "Deep range"],
        weaknesses=["Decision making", "Consistency", "Screen navigation"],
        notes="Pushes pace in transition. Size helps with rebounding and seeing over defense.",
        guards_positions=["PG", "SG"],
    ),
    
    "Donovan Mitchell": PlayerProfile(
        name="Donovan Mitchell",
        team="Cleveland Cavaliers",
        primary_offensive=OffensiveRole.SCORING_GUARD,
        secondary_offensive=OffensiveRole.PRIMARY_INITIATOR,
        defensive_role=DefensiveRole.POA_DEFENDER,
        tier=PlayerTier.MVP_CANDIDATE,
        height="6'1\"",
        position="SG",
        strengths=["Explosive scorer", "3-point shooting", "Clutch gene"],
        weaknesses=["Shot selection at times"],
        notes="32.6% USG. Scorer first, facilitator second. Improved defensive metrics.",
        guards_positions=["PG", "SG"],
    ),
    
    # =========================================================================
    # TIER 2: TWO-WAY STARS
    # =========================================================================
    
    "Jayson Tatum": PlayerProfile(
        name="Jayson Tatum",
        team="Boston Celtics",
        primary_offensive=OffensiveRole.ISOLATION_SCORER,
        secondary_offensive=OffensiveRole.POINT_FORWARD,
        defensive_role=DefensiveRole.WING_STOPPER,
        tier=PlayerTier.TWO_WAY_STAR,
        height="6'8\"",
        position="SF",
        strengths=["3-level scorer", "Playmaking growth", "Length", "Big moments"],
        weaknesses=["Can be passive at times"],
        notes="Prototype two-way wing. Designated wing stopper who also runs offense.",
        guards_positions=["SF", "PF", "SG"],
        is_elite_defender=True,
        avoid_betting_against=["Jayson Tatum"],
    ),
    
    "Anthony Edwards": PlayerProfile(
        name="Anthony Edwards",
        team="Minnesota Timberwolves",
        primary_offensive=OffensiveRole.SCORING_WING,
        secondary_offensive=OffensiveRole.SLASHER,
        defensive_role=DefensiveRole.POA_DEFENDER,
        tier=PlayerTier.TWO_WAY_STAR,
        height="6'4\"",
        position="SG",
        strengths=["Athletic finishing", "Pull-up 3s", "Strength", "Defensive growth"],
        weaknesses=["Shot selection"],
        notes="Rising MVP candidate. Now takes POA assignments against elite guards.",
        guards_positions=["PG", "SG", "SF"],
        is_elite_defender=True,
        avoid_betting_against=["Anthony Edwards"],
    ),
    
    "Jaylen Brown": PlayerProfile(
        name="Jaylen Brown",
        team="Boston Celtics",
        primary_offensive=OffensiveRole.SLASHER,
        secondary_offensive=OffensiveRole.ISOLATION_SCORER,
        defensive_role=DefensiveRole.WING_STOPPER,
        tier=PlayerTier.TWO_WAY_STAR,
        height="6'6\"",
        position="SG",
        strengths=["Downhill attacking", "Athleticism", "Improved midrange", "Defense"],
        weaknesses=["Ball handling under pressure", "Turnovers"],
        notes="Downhill attacking freight train. Takes more physical matchups than Tatum.",
        guards_positions=["SG", "SF"],
        is_elite_defender=True,
    ),
    
    "Kevin Durant": PlayerProfile(
        name="Kevin Durant",
        team="Houston Rockets",
        primary_offensive=OffensiveRole.ISOLATION_SCORER,
        secondary_offensive=OffensiveRole.SPOT_UP_SHOOTER,
        defensive_role=DefensiveRole.ROAMER,
        tier=PlayerTier.TWO_WAY_STAR,
        height="6'10\"",
        position="SF",
        strengths=["Unstoppable scorer", "7-foot wingspan", "Shooting touch", "Versatility"],
        weaknesses=["Age", "Durability"],
        notes="Offensive unicorn - unguardable due to size/skill combo. Used as weak-side helper.",
        guards_positions=["SF", "PF"],
    ),
    
    "Jimmy Butler": PlayerProfile(
        name="Jimmy Butler",
        team="Golden State Warriors",
        primary_offensive=OffensiveRole.SLASHER,
        secondary_offensive=OffensiveRole.POINT_FORWARD,
        defensive_role=DefensiveRole.WING_STOPPER,
        tier=PlayerTier.TWO_WAY_STAR,
        height="6'7\"",
        position="SF",
        strengths=["Drawing fouls", "Playoff performer", "Leadership", "Defense"],
        weaknesses=["3-point shooting", "Age"],
        notes="Two-way slashing playmaker. Career-high assists as de facto point guard.",
        guards_positions=["SF", "SG", "PF"],
        is_elite_defender=True,
        avoid_betting_against=["Jimmy Butler"],
    ),
    
    "Kawhi Leonard": PlayerProfile(
        name="Kawhi Leonard",
        team="LA Clippers",
        primary_offensive=OffensiveRole.ISOLATION_SCORER,
        secondary_offensive=OffensiveRole.POST_SCORER,
        defensive_role=DefensiveRole.WING_STOPPER,
        tier=PlayerTier.TWO_WAY_STAR,
        height="6'7\"",
        position="SF",
        strengths=["2-way elite", "Playoff performer", "Massive hands", "Midpost"],
        weaknesses=["Durability", "Load management"],
        notes="2x DPOY. When healthy, premier lockdown wing who also scores at will.",
        guards_positions=["SF", "SG", "PF"],
        is_elite_defender=True,
        avoid_betting_against=["Kawhi Leonard"],
    ),
    
    "Paul George": PlayerProfile(
        name="Paul George",
        team="Philadelphia 76ers",
        primary_offensive=OffensiveRole.SHOT_CREATOR,
        secondary_offensive=OffensiveRole.SPOT_UP_SHOOTER,
        defensive_role=DefensiveRole.WING_STOPPER,
        tier=PlayerTier.TWO_WAY_STAR,
        height="6'8\"",
        position="SF",
        strengths=["3-level scoring", "Length", "Two-way ability"],
        weaknesses=["Injuries", "Inconsistency in playoffs"],
        notes="Relieves pressure from Embiid. Guards premier wings so Maxey can hide.",
        guards_positions=["SF", "SG"],
        is_elite_defender=True,
    ),
    
    "Devin Booker": PlayerProfile(
        name="Devin Booker",
        team="Phoenix Suns",
        primary_offensive=OffensiveRole.SHOT_CREATOR,
        secondary_offensive=OffensiveRole.PNR_MAESTRO,
        defensive_role=DefensiveRole.WING_DEFENDER,
        tier=PlayerTier.TWO_WAY_STAR,
        height="6'5\"",
        position="SG",
        strengths=["Midrange", "3-point shooting", "Improved playmaking", "Clutch"],
        weaknesses=["Defense historically"],
        notes="Pure shot creator. Has evolved into capable combo guard with playmaking growth.",
        guards_positions=["SG", "SF"],
    ),
    
    "Anthony Davis": PlayerProfile(
        name="Anthony Davis",
        team="Dallas Mavericks",
        primary_offensive=OffensiveRole.VERSATILE_BIG,
        secondary_offensive=OffensiveRole.POST_SCORER,
        defensive_role=DefensiveRole.ANCHOR_BIG,
        tier=PlayerTier.TWO_WAY_STAR,
        height="6'10\"",
        position="PF",
        strengths=["Elite rim protection", "Versatile scoring", "Lob threat", "Switchability"],
        weaknesses=["Durability", "Perimeter shooting consistency"],
        notes="Jack-of-all-trades. Can hurt you in variety of ways. Elite rim protector who can switch.",
        guards_positions=["C", "PF", "SF"],
        is_elite_defender=True,
        avoid_betting_against=["Anthony Davis"],
    ),
    
    "LeBron James": PlayerProfile(
        name="LeBron James",
        team="Los Angeles Lakers",
        primary_offensive=OffensiveRole.POINT_FORWARD,
        secondary_offensive=OffensiveRole.POST_SCORER,
        defensive_role=DefensiveRole.ROAMER,
        tier=PlayerTier.TWO_WAY_STAR,
        height="6'9\"",
        position="SF",
        strengths=["Basketball IQ", "Playmaking", "Still athletic", "Leadership"],
        weaknesses=["Age", "Defensive effort varies"],
        notes="Year 23. Prototype point forward. Now exclusively a roamer on defense.",
        guards_positions=["SF", "PF"],
    ),
    
    "Scottie Barnes": PlayerProfile(
        name="Scottie Barnes",
        team="Toronto Raptors",
        primary_offensive=OffensiveRole.POINT_FORWARD,
        secondary_offensive=OffensiveRole.CONNECTOR,
        defensive_role=DefensiveRole.ROAMER,
        tier=PlayerTier.TWO_WAY_STAR,
        height="6'9\"",
        position="SF",
        strengths=["Versatility", "Passing", "Defense 1-5", "Motor"],
        weaknesses=["Jump shot consistency"],
        notes="23.5% AST rate. Switchable 1-5 defender. Swiss-army knife.",
        guards_positions=["PG", "SG", "SF", "PF", "C"],
        is_elite_defender=True,
    ),
    
    "Paolo Banchero": PlayerProfile(
        name="Paolo Banchero",
        team="Orlando Magic",
        primary_offensive=OffensiveRole.POINT_FORWARD,
        secondary_offensive=OffensiveRole.ISOLATION_SCORER,
        defensive_role=DefensiveRole.MOBILE_BIG,
        tier=PlayerTier.TWO_WAY_STAR,
        height="6'10\"",
        position="PF",
        strengths=["Ball handling for size", "Scoring versatility", "Playmaking"],
        weaknesses=["3-point consistency"],
        notes="Creates mismatches as point forward in 6'10\" frame. Key to Orlando's identity.",
        guards_positions=["PF", "SF", "C"],
    ),
    
    "Jalen Williams": PlayerProfile(
        name="Jalen Williams",
        team="Oklahoma City Thunder",
        primary_offensive=OffensiveRole.CONNECTOR,
        secondary_offensive=OffensiveRole.SLASHER,
        defensive_role=DefensiveRole.WING_STOPPER,
        tier=PlayerTier.TWO_WAY_STAR,
        height="6'6\"",
        position="SF",
        strengths=["Versatility", "Basketball IQ", "Defense 1-4", "Efficient scorer"],
        weaknesses=["Creation as primary"],
        notes="Ideal modern complementary star. Guards positions 1-4 in switch-heavy scheme.",
        guards_positions=["PG", "SG", "SF", "PF"],
        is_elite_defender=True,
    ),
    
    "Franz Wagner": PlayerProfile(
        name="Franz Wagner",
        team="Orlando Magic",
        primary_offensive=OffensiveRole.SLASHER,
        secondary_offensive=OffensiveRole.CONNECTOR,
        defensive_role=DefensiveRole.WING_DEFENDER,
        tier=PlayerTier.TWO_WAY_STAR,
        height="6'10\"",
        position="SF",
        strengths=["Euro-step", "Length", "Basketball IQ", "Defense"],
        weaknesses=["Shot creation consistency"],
        notes="Elite at attacking basket with euro-steps. Secondary handler alongside Banchero.",
        guards_positions=["SF", "PF"],
    ),
    
    "Brandon Ingram": PlayerProfile(
        name="Brandon Ingram",
        team="Toronto Raptors",
        primary_offensive=OffensiveRole.ISOLATION_SCORER,
        secondary_offensive=OffensiveRole.SHOT_CREATOR,
        defensive_role=DefensiveRole.WING_DEFENDER,
        tier=PlayerTier.TWO_WAY_STAR,
        height="6'8\"",
        position="SF",
        strengths=["Midrange mastery", "Length", "Shot creation"],
        weaknesses=["3-point consistency", "Defense effort"],
        notes="KD-lite in build and style. Operates primarily in isolation and midrange.",
        guards_positions=["SF"],
    ),
    
    # =========================================================================
    # TIER 3: ELITE BIGS
    # =========================================================================
    
    "Victor Wembanyama": PlayerProfile(
        name="Victor Wembanyama",
        team="San Antonio Spurs",
        primary_offensive=OffensiveRole.STRETCH_BIG,
        secondary_offensive=OffensiveRole.RIM_RUNNER,
        defensive_role=DefensiveRole.ANCHOR_BIG,
        tier=PlayerTier.ELITE_BIG,
        height="7'4\"",
        position="C",
        strengths=["Rim protection", "Perimeter shooting", "Shot blocking", "Length"],
        weaknesses=["Strength", "Consistency"],
        notes="Defensive category unto himself. Both Anchor and Roamer. Infinite range.",
        guards_positions=["C", "PF"],
        is_elite_defender=True,
        avoid_betting_against=["Victor Wembanyama"],
    ),
    
    "Bam Adebayo": PlayerProfile(
        name="Bam Adebayo",
        team="Miami Heat",
        primary_offensive=OffensiveRole.HUB_BIG,
        secondary_offensive=OffensiveRole.CONNECTOR,
        defensive_role=DefensiveRole.SWITCH_BIG,
        tier=PlayerTier.ELITE_BIG,
        height="6'9\"",
        position="C",
        strengths=["Switching 1-5", "Playmaking", "DHOs", "Motor"],
        weaknesses=["3-point shooting", "Perimeter creation"],
        notes="Quintessential switch big. Guards 1-5 which allows Miami to switch everything.",
        guards_positions=["PG", "SG", "SF", "PF", "C"],
        is_elite_defender=True,
        avoid_betting_against=["Bam Adebayo"],
    ),
    
    "Domantas Sabonis": PlayerProfile(
        name="Domantas Sabonis",
        team="Sacramento Kings",
        primary_offensive=OffensiveRole.HUB_BIG,
        secondary_offensive=OffensiveRole.POST_SCORER,
        defensive_role=DefensiveRole.ANCHOR_BIG,
        tier=PlayerTier.ELITE_BIG,
        height="6'11\"",
        position="C",
        strengths=["Passing", "Rebounding (led league)", "DHOs", "Touch"],
        weaknesses=["Rim protection", "Foot speed"],
        notes="Hub of Kings offense. 7+ APG shows elite passing. Drop coverage defender.",
        guards_positions=["C", "PF"],
    ),
    
    "Karl-Anthony Towns": PlayerProfile(
        name="Karl-Anthony Towns",
        team="New York Knicks",
        primary_offensive=OffensiveRole.STRETCH_BIG,
        secondary_offensive=OffensiveRole.POST_SCORER,
        defensive_role=DefensiveRole.ANCHOR_BIG,
        tier=PlayerTier.ELITE_BIG,
        height="7'0\"",
        position="C",
        strengths=["3-point shooting (best 7-footer ever)", "Versatile scoring", "Rebounding"],
        weaknesses=["Defense in space", "Consistency"],
        notes="Most accurate high-volume 3-point shooting 7-footer in history. Creates lanes for Brunson.",
        guards_positions=["C"],
    ),
    
    "Evan Mobley": PlayerProfile(
        name="Evan Mobley",
        team="Cleveland Cavaliers",
        primary_offensive=OffensiveRole.CONNECTOR,
        secondary_offensive=OffensiveRole.RIM_RUNNER,
        defensive_role=DefensiveRole.ROAMER,
        tier=PlayerTier.ELITE_BIG,
        height="7'0\"",
        position="PF",
        strengths=["Versatile defense", "Passing", "Rim protection", "Mobility"],
        weaknesses=["Offensive creation", "3-point shot"],
        notes="DPOY candidate. Ultimate help defender - switches onto guards, recovers to block shots.",
        guards_positions=["PG", "SG", "SF", "PF", "C"],
        is_elite_defender=True,
        avoid_betting_against=["Evan Mobley"],
    ),
    
    "Rudy Gobert": PlayerProfile(
        name="Rudy Gobert",
        team="Minnesota Timberwolves",
        primary_offensive=OffensiveRole.RIM_RUNNER,
        secondary_offensive=OffensiveRole.CONNECTOR,
        defensive_role=DefensiveRole.ANCHOR_BIG,
        tier=PlayerTier.ELITE_BIG,
        height="7'1\"",
        position="C",
        strengths=["Elite rim protection (3x DPOY)", "Rebounding", "Lobs", "Screens"],
        weaknesses=["Perimeter defense", "Offensive creation"],
        notes="Textbook anchor big. Patrols paint, plays drop coverage. Elite screen-setter.",
        guards_positions=["C"],
        is_elite_defender=True,
        avoid_betting_against=["Rudy Gobert"],
    ),
    
    "Chet Holmgren": PlayerProfile(
        name="Chet Holmgren",
        team="Oklahoma City Thunder",
        primary_offensive=OffensiveRole.STRETCH_BIG,
        secondary_offensive=OffensiveRole.RIM_RUNNER,
        defensive_role=DefensiveRole.ROAMER,
        tier=PlayerTier.ELITE_BIG,
        height="7'1\"",
        position="C",
        strengths=["Elite 3-point shooting", "Rim protection", "Length", "IQ"],
        weaknesses=["Strength", "Durability"],
        notes="Stretch big who also provides rim protection. Roams alongside Hartenstein.",
        guards_positions=["C", "PF"],
        is_elite_defender=True,
    ),
    
    "Alperen Sengun": PlayerProfile(
        name="Alperen Sengun",
        team="Houston Rockets",
        primary_offensive=OffensiveRole.HUB_BIG,
        secondary_offensive=OffensiveRole.POST_SCORER,
        defensive_role=DefensiveRole.ANCHOR_BIG,
        tier=PlayerTier.ELITE_BIG,
        height="6'10\"",
        position="C",
        strengths=["Elite passing for big", "Post footwork", "Touch", "IQ"],
        weaknesses=["Lateral mobility", "Rim protection"],
        notes="Mini-Jokic. Runs offense through elbow with 5-6 APG. Drop coverage on D.",
        guards_positions=["C"],
    ),
    
    "Jarrett Allen": PlayerProfile(
        name="Jarrett Allen",
        team="Cleveland Cavaliers",
        primary_offensive=OffensiveRole.RIM_RUNNER,
        secondary_offensive=OffensiveRole.CONNECTOR,
        defensive_role=DefensiveRole.ANCHOR_BIG,
        tier=PlayerTier.ELITE_BIG,
        height="6'11\"",
        position="C",
        strengths=["Elite efficiency (68.9% TS)", "Rim protection", "Lobs"],
        weaknesses=["Offensive creation", "Perimeter defense"],
        notes="Leads league in Stable True Shooting by strictly adhering to rim runner role.",
        guards_positions=["C"],
        is_elite_defender=True,
    ),
    
    # =========================================================================
    # TIER 4: ELITE ROLE PLAYERS
    # =========================================================================
    
    "OG Anunoby": PlayerProfile(
        name="OG Anunoby",
        team="New York Knicks",
        primary_offensive=OffensiveRole.THREE_AND_D,
        secondary_offensive=OffensiveRole.CUTTER,
        defensive_role=DefensiveRole.WING_STOPPER,
        tier=PlayerTier.ELITE_ROLE,
        height="6'7\"",
        position="SF",
        strengths=["Elite defense (94th percentile DPM)", "Corner 3s", "Cutting"],
        weaknesses=["Shot creation", "Playmaking"],
        notes="Prototypical 3-and-D. Nothing flashy but extremely valuable. Premier wing stopper.",
        guards_positions=["SF", "SG", "PF"],
        is_elite_defender=True,
        avoid_betting_against=["OG Anunoby"],
    ),
    
    "Mikal Bridges": PlayerProfile(
        name="Mikal Bridges",
        team="New York Knicks",
        primary_offensive=OffensiveRole.THREE_AND_D,
        secondary_offensive=OffensiveRole.CONNECTOR,
        defensive_role=DefensiveRole.WING_STOPPER,
        tier=PlayerTier.ELITE_ROLE,
        height="6'6\"",
        position="SF",
        strengths=["Ironman durability", "3-and-D", "Secondary handling", "IQ"],
        weaknesses=["Not a primary creator"],
        notes="Pairs with Anunoby for lockdown wing duo. Can attack closeouts and run PnR.",
        guards_positions=["SG", "SF", "PF"],
        is_elite_defender=True,
    ),
    
    "Derrick White": PlayerProfile(
        name="Derrick White",
        team="Boston Celtics",
        primary_offensive=OffensiveRole.CONNECTOR,
        secondary_offensive=OffensiveRole.SPOT_UP_SHOOTER,
        defensive_role=DefensiveRole.POA_DEFENDER,
        tier=PlayerTier.ELITE_ROLE,
        height="6'4\"",
        position="SG",
        strengths=["IQ", "Shot blocking (rare for guard)", "3-point shooting", "POA defense"],
        weaknesses=["Creation as primary"],
        notes="Ultimate connector. Blocks shots at rim, hits 3s, moves ball instantly.",
        guards_positions=["PG", "SG"],
        is_elite_defender=True,
        avoid_betting_against=["Derrick White"],
    ),
    
    "Jrue Holiday": PlayerProfile(
        name="Jrue Holiday",
        team="Portland Trail Blazers",
        primary_offensive=OffensiveRole.CONNECTOR,
        secondary_offensive=OffensiveRole.SPOT_UP_SHOOTER,
        defensive_role=DefensiveRole.POA_DEFENDER,
        tier=PlayerTier.ELITE_ROLE,
        height="6'4\"",
        position="PG",
        strengths=["Elite POA defense", "IQ", "Experience", "Clutch"],
        weaknesses=["Age", "Scoring consistency"],
        notes="Standard for POA defense. Takes toughest guard matchup nightly.",
        guards_positions=["PG", "SG"],
        is_elite_defender=True,
        avoid_betting_against=["Jrue Holiday"],
    ),
    
    "Herbert Jones": PlayerProfile(
        name="Herbert Jones",
        team="New Orleans Pelicans",
        primary_offensive=OffensiveRole.SLASHER,
        secondary_offensive=OffensiveRole.SPOT_UP_SHOOTER,
        defensive_role=DefensiveRole.WING_STOPPER,
        tier=PlayerTier.ELITE_ROLE,
        height="6'7\"",
        position="SF",
        strengths=["Elite wing defense", "Length", "Motor"],
        weaknesses=["Shooting", "Offensive creation"],
        notes="Not on Herb. Pure wing stopper. Value is 80% defensive.",
        guards_positions=["SF", "SG", "PF"],
        is_elite_defender=True,
        avoid_betting_against=["Herbert Jones"],
    ),
    
    "Alex Caruso": PlayerProfile(
        name="Alex Caruso",
        team="Oklahoma City Thunder",
        primary_offensive=OffensiveRole.CONNECTOR,
        secondary_offensive=OffensiveRole.CUTTER,
        defensive_role=DefensiveRole.POA_DEFENDER,
        tier=PlayerTier.ELITE_ROLE,
        height="6'5\"",
        position="SG",
        strengths=["Steals/deflections", "IQ", "Cutting", "Screen navigation"],
        weaknesses=["Shot creation", "Scoring volume"],
        notes="POA defender who generates havoc. Fits perfectly in OKC's motion offense.",
        guards_positions=["PG", "SG"],
        is_elite_defender=True,
        avoid_betting_against=["Alex Caruso"],
    ),
    
    "Jalen Suggs": PlayerProfile(
        name="Jalen Suggs",
        team="Orlando Magic",
        primary_offensive=OffensiveRole.SPOT_UP_SHOOTER,
        secondary_offensive=OffensiveRole.COMBO_GUARD,
        defensive_role=DefensiveRole.POA_DEFENDER,
        tier=PlayerTier.ELITE_ROLE,
        height="6'4\"",
        position="PG",
        strengths=["Full-court pressure", "Motor", "Improved shooting"],
        weaknesses=["Shooting consistency historically"],
        notes="Defensive bulldog. Picks up ball handlers full-court. Shooting has improved.",
        guards_positions=["PG", "SG"],
        is_elite_defender=True,
        avoid_betting_against=["Jalen Suggs"],
    ),
    
    "Luguentz Dort": PlayerProfile(
        name="Luguentz Dort",
        team="Oklahoma City Thunder",
        primary_offensive=OffensiveRole.SPOT_UP_SHOOTER,
        secondary_offensive=OffensiveRole.THREE_AND_D,
        defensive_role=DefensiveRole.POA_DEFENDER,
        tier=PlayerTier.ELITE_ROLE,
        height="6'4\"",
        position="SG",
        strengths=["Physical POA defense", "Strength", "Screen navigation"],
        weaknesses=["Offensive creation", "Efficiency"],
        notes="The Dorture Chamber. Navigates screens with brute strength.",
        guards_positions=["PG", "SG"],
        is_elite_defender=True,
        avoid_betting_against=["Luguentz Dort"],
    ),
    
    "Jaden McDaniels": PlayerProfile(
        name="Jaden McDaniels",
        team="Minnesota Timberwolves",
        primary_offensive=OffensiveRole.SPOT_UP_SHOOTER,
        secondary_offensive=OffensiveRole.CUTTER,
        defensive_role=DefensiveRole.WING_STOPPER,
        tier=PlayerTier.ELITE_ROLE,
        height="6'9\"",
        position="SF",
        strengths=["Length", "Wing defense", "Cutting"],
        weaknesses=["Shot creation", "Consistency"],
        notes="Minnesota's designated wing stopper. Length bothers elite scorers.",
        guards_positions=["SF", "SG", "PF"],
        is_elite_defender=True,
        avoid_betting_against=["Jaden McDaniels"],
    ),
    
    "Dillon Brooks": PlayerProfile(
        name="Dillon Brooks",
        team="Phoenix Suns",
        primary_offensive=OffensiveRole.SPOT_UP_SHOOTER,
        secondary_offensive=OffensiveRole.ISOLATION_SCORER,
        defensive_role=DefensiveRole.WING_STOPPER,
        tier=PlayerTier.ELITE_ROLE,
        height="6'7\"",
        position="SF",
        strengths=["Physical defense", "Motor", "Toughness"],
        weaknesses=["Shot selection", "Efficiency"],
        notes="Embraces villain role. Physical wing stopper.",
        guards_positions=["SF", "SG"],
        is_elite_defender=True,
    ),
    
    # =========================================================================
    # TIER 5: SPECIALISTS
    # =========================================================================
    
    "Jamal Murray": PlayerProfile(
        name="Jamal Murray",
        team="Denver Nuggets",
        primary_offensive=OffensiveRole.PNR_MAESTRO,
        secondary_offensive=OffensiveRole.SHOT_CREATOR,
        defensive_role=DefensiveRole.CHASER,
        tier=PlayerTier.SPECIALIST,
        height="6'4\"",
        position="PG",
        strengths=["Two-man game with Jokic", "Clutch scoring", "Pull-up shooting"],
        weaknesses=["Defense", "Consistency post-injury"],
        notes="Elite two-man game partner with Jokic. Multiple 40+ and 50-point playoff games.",
        guards_positions=["PG", "SG"],
    ),
    
    "Kyrie Irving": PlayerProfile(
        name="Kyrie Irving",
        team="Dallas Mavericks",
        primary_offensive=OffensiveRole.ISOLATION_SCORER,
        secondary_offensive=OffensiveRole.SPOT_UP_SHOOTER,
        defensive_role=DefensiveRole.CHASER,
        tier=PlayerTier.SPECIALIST,
        height="6'2\"",
        position="PG",
        strengths=["Elite handle", "Finishing", "Shot-making", "FT% (90.2%)"],
        weaknesses=["Size on defense", "Availability historically"],
        notes="Functions as secondary scorer to Luka. One of best finishers ever.",
        guards_positions=["PG", "SG"],
    ),
    
    "Tyrese Maxey": PlayerProfile(
        name="Tyrese Maxey",
        team="Philadelphia 76ers",
        primary_offensive=OffensiveRole.COMBO_GUARD,
        secondary_offensive=OffensiveRole.SLASHER,
        defensive_role=DefensiveRole.CHASER,
        tier=PlayerTier.SPECIALIST,
        height="6'2\"",
        position="PG",
        strengths=["Elite speed (probably fastest in NBA)", "Shooting", "Floater"],
        weaknesses=["Size", "Playmaking development"],
        notes="Lightning-quick guard. Blows by defenders, provides speed and scoring punch.",
        guards_positions=["PG", "SG"],
    ),
    
    "Zach LaVine": PlayerProfile(
        name="Zach LaVine",
        team="Sacramento Kings",
        primary_offensive=OffensiveRole.SHOT_CREATOR,
        secondary_offensive=OffensiveRole.SLASHER,
        defensive_role=DefensiveRole.CHASER,
        tier=PlayerTier.SPECIALIST,
        height="6'5\"",
        position="SG",
        strengths=["Athleticism", "Scoring burst", "Dunking", "Pull-up shooting"],
        weaknesses=["Defense", "Efficiency varies"],
        notes="Two-time Slam Dunk Contest champion. Classic slasher with improved shooting.",
        guards_positions=["SG"],
    ),
    
    "Bradley Beal": PlayerProfile(
        name="Bradley Beal",
        team="LA Clippers",
        primary_offensive=OffensiveRole.SHOT_CREATOR,
        secondary_offensive=OffensiveRole.SPOT_UP_SHOOTER,
        defensive_role=DefensiveRole.CHASER,
        tier=PlayerTier.SPECIALIST,
        height="6'4\"",
        position="SG",
        strengths=["Midrange", "3-point shooting", "Slashing"],
        weaknesses=["Injuries", "Defense"],
        notes="Back-to-back 30+ PPG seasons in Washington. Tertiary scorer now.",
        guards_positions=["SG"],
    ),
    
    "Tyler Herro": PlayerProfile(
        name="Tyler Herro",
        team="Miami Heat",
        primary_offensive=OffensiveRole.SHOT_CREATOR,
        secondary_offensive=OffensiveRole.PNR_MAESTRO,
        defensive_role=DefensiveRole.CHASED_TARGET,
        tier=PlayerTier.SPECIALIST,
        height="6'5\"",
        position="SG",
        strengths=["Shooting", "Shot creation", "Scoring punch"],
        weaknesses=["Defense (hunted)", "Size"],
        notes="Shot creator who runs PnR. Gets hidden in zone due to defensive limitations.",
        guards_positions=["Weakest offensive player"],
    ),
    
    "Desmond Bane": PlayerProfile(
        name="Desmond Bane",
        team="Orlando Magic",
        primary_offensive=OffensiveRole.MOVEMENT_SHOOTER,
        secondary_offensive=OffensiveRole.CONNECTOR,
        defensive_role=DefensiveRole.CHASER,
        tier=PlayerTier.SPECIALIST,
        height="6'5\"",
        position="SG",
        strengths=["Elite catch-and-shoot", "Strength", "Secondary ball handling"],
        weaknesses=["Primary creation"],
        notes="~20 PPG, 5 RPG, 5 APG on excellent splits. Tank-built guard.",
        guards_positions=["SG", "SF"],
    ),
    
    "Norman Powell": PlayerProfile(
        name="Norman Powell",
        team="Miami Heat",
        primary_offensive=OffensiveRole.MOVEMENT_SHOOTER,
        secondary_offensive=OffensiveRole.SLASHER,
        defensive_role=DefensiveRole.CHASER,
        tier=PlayerTier.SPECIALIST,
        height="6'4\"",
        position="SG",
        strengths=["Instant offense", "Shooting", "Slashing"],
        weaknesses=["Playmaking", "Consistency"],
        notes="Microwave scorer. Provides instant offense off bench.",
        guards_positions=["SG"],
    ),
    
    "Immanuel Quickley": PlayerProfile(
        name="Immanuel Quickley",
        team="Toronto Raptors",
        primary_offensive=OffensiveRole.SCORING_GUARD,
        secondary_offensive=OffensiveRole.PNR_MAESTRO,
        defensive_role=DefensiveRole.POA_DEFENDER,
        tier=PlayerTier.SPECIALIST,
        height="6'3\"",
        position="PG",
        strengths=["Microwave scoring", "Deep range", "Floater", "POA defense"],
        weaknesses=["Size", "Consistency"],
        notes="Dynamic guard with deep range. Good POA defender with quick feet.",
        guards_positions=["PG", "SG"],
        is_elite_defender=True,
    ),
    
    "Darius Garland": PlayerProfile(
        name="Darius Garland",
        team="Cleveland Cavaliers",
        primary_offensive=OffensiveRole.FLOOR_GENERAL,
        secondary_offensive=OffensiveRole.SHOT_CREATOR,
        defensive_role=DefensiveRole.CHASER,
        tier=PlayerTier.SPECIALIST,
        height="6'1\"",
        position="PG",
        strengths=["Court vision", "3-point shooting (40%)", "Floaters"],
        weaknesses=["Size", "Defense"],
        notes="~8 APG. Calmer orchestrator compared to Mitchell's score-first style.",
        guards_positions=["PG"],
    ),
    
    # =========================================================================
    # TIER 6: ROTATION PIECES
    # =========================================================================
    
    "Amen Thompson": PlayerProfile(
        name="Amen Thompson",
        team="Houston Rockets",
        primary_offensive=OffensiveRole.SLASHER,
        secondary_offensive=OffensiveRole.CONNECTOR,
        defensive_role=DefensiveRole.POA_DEFENDER,
        tier=PlayerTier.ROTATION,
        height="6'7\"",
        position="SG",
        strengths=["Elite athleticism", "Defense", "Transition", "Playmaking"],
        weaknesses=["Jump shot"],
        notes="Non-shooter but elite playmaker/finisher. Elite athlete/defender.",
        guards_positions=["PG", "SG", "SF"],
        is_elite_defender=True,
    ),
    
    "Ausar Thompson": PlayerProfile(
        name="Ausar Thompson",
        team="Detroit Pistons",
        primary_offensive=OffensiveRole.CUTTER,
        secondary_offensive=OffensiveRole.SLASHER,
        defensive_role=DefensiveRole.WING_STOPPER,
        tier=PlayerTier.ROTATION,
        height="6'7\"",
        position="SF",
        strengths=["Athleticism", "Defense", "Rebounding for size"],
        weaknesses=["Jump shot", "Offensive creation"],
        notes="Elite athlete/defender. Great rebounder for wing size.",
        guards_positions=["SF", "SG"],
        is_elite_defender=True,
    ),
    
    "Tari Eason": PlayerProfile(
        name="Tari Eason",
        team="Houston Rockets",
        primary_offensive=OffensiveRole.THREE_AND_D,
        secondary_offensive=OffensiveRole.SLASHER,
        defensive_role=DefensiveRole.WING_STOPPER,
        tier=PlayerTier.ROTATION,
        height="6'8\"",
        position="SF",
        strengths=["Motor", "Steals/blocks", "Rebounding"],
        weaknesses=["Fouling", "Offensive consistency"],
        notes="High motor defender. Steal/block machine.",
        guards_positions=["SF", "PF"],
        is_elite_defender=True,
    ),
    
    "Jabari Smith Jr.": PlayerProfile(
        name="Jabari Smith Jr.",
        team="Houston Rockets",
        primary_offensive=OffensiveRole.STRETCH_BIG,
        secondary_offensive=OffensiveRole.THREE_AND_D,
        defensive_role=DefensiveRole.SWITCH_BIG,
        tier=PlayerTier.ROTATION,
        height="6'10\"",
        position="PF",
        strengths=["3-point shooting", "Length", "Switchability"],
        weaknesses=["Creation", "Consistency"],
        notes="3-and-D big. Can switch onto guards.",
        guards_positions=["PF", "SF", "C"],
    ),
    
    "Reed Sheppard": PlayerProfile(
        name="Reed Sheppard",
        team="Houston Rockets",
        primary_offensive=OffensiveRole.MOVEMENT_SHOOTER,
        secondary_offensive=OffensiveRole.CONNECTOR,
        defensive_role=DefensiveRole.CHASER,
        tier=PlayerTier.ROTATION,
        height="6'3\"",
        position="SG",
        strengths=["Shooting", "IQ", "Passing"],
        weaknesses=["Athleticism", "Size"],
        notes="Rookie sharpshooter. Elite off-ball movement and basketball IQ.",
        guards_positions=["SG"],
    ),
    
    "Aaron Gordon": PlayerProfile(
        name="Aaron Gordon",
        team="Denver Nuggets",
        primary_offensive=OffensiveRole.CUTTER,
        secondary_offensive=OffensiveRole.CONNECTOR,
        defensive_role=DefensiveRole.WING_STOPPER,
        tier=PlayerTier.ROTATION,
        height="6'8\"",
        position="PF",
        strengths=["Athleticism", "Defense", "Dunker spot", "Cutting"],
        weaknesses=["Shooting consistency", "Shot creation"],
        notes="Dunker spot specialist. Vital defensive versatility for Denver.",
        guards_positions=["SF", "PF"],
        is_elite_defender=True,
    ),
    
    # =========================================================================
    # ADDITIONAL TIER 2: TWO-WAY STARS
    # =========================================================================
    
    "Zion Williamson": PlayerProfile(
        name="Zion Williamson",
        team="New Orleans Pelicans",
        primary_offensive=OffensiveRole.SLASHER,
        secondary_offensive=OffensiveRole.POINT_FORWARD,
        defensive_role=DefensiveRole.ROAMER,
        tier=PlayerTier.TWO_WAY_STAR,
        height="6'6\"",
        position="PF",
        strengths=["Elite paint scoring", "Strength", "Transition", "Playmaking growth"],
        weaknesses=["Durability", "Jump shot", "Defense positioning"],
        notes="Point Zion - supersized slasher. 20+ PPG in paint. Bulldozes to rim.",
        guards_positions=["PF"],
    ),
    
    "James Harden": PlayerProfile(
        name="James Harden",
        team="LA Clippers",
        primary_offensive=OffensiveRole.PRIMARY_INITIATOR,
        secondary_offensive=OffensiveRole.FLOOR_GENERAL,
        defensive_role=DefensiveRole.LOW_ACTIVITY,
        tier=PlayerTier.TWO_WAY_STAR,
        height="6'5\"",
        position="PG",
        strengths=["Elite playmaking", "Step-back 3", "Drawing fouls", "Court vision"],
        weaknesses=["Defense", "Athletic decline"],
        notes="Led NBA in assists. Orchestrates offense, toggles between scoring and facilitating.",
        guards_positions=["SG"],
    ),
    
    "Pascal Siakam": PlayerProfile(
        name="Pascal Siakam",
        team="Indiana Pacers",
        primary_offensive=OffensiveRole.POINT_FORWARD,
        secondary_offensive=OffensiveRole.POST_SCORER,
        defensive_role=DefensiveRole.WING_STOPPER,
        tier=PlayerTier.TWO_WAY_STAR,
        height="6'9\"",
        position="PF",
        strengths=["Spin moves", "Transition", "Versatility", "Playmaking"],
        weaknesses=["3-point consistency", "Half-court creation"],
        notes="Spicy P. Do-it-all forward, can guard multiple positions.",
        guards_positions=["SF", "PF"],
    ),
    
    "Lauri Markkanen": PlayerProfile(
        name="Lauri Markkanen",
        team="Utah Jazz",
        primary_offensive=OffensiveRole.STRETCH_BIG,
        secondary_offensive=OffensiveRole.SLASHER,
        defensive_role=DefensiveRole.CHASER,
        tier=PlayerTier.TWO_WAY_STAR,
        height="7'0\"",
        position="PF",
        strengths=["3-point shooting (~40%)", "Quick release", "Driving ability"],
        weaknesses=["Defense", "Rim protection"],
        notes="MIP winner. 7-foot stretch four who can also attack the basket.",
        guards_positions=["PF"],
    ),
    
    # =========================================================================
    # ADDITIONAL TIER 3: ELITE BIGS
    # =========================================================================
    
    "Myles Turner": PlayerProfile(
        name="Myles Turner",
        team="Indiana Pacers",
        primary_offensive=OffensiveRole.STRETCH_BIG,
        secondary_offensive=OffensiveRole.RIM_RUNNER,
        defensive_role=DefensiveRole.ANCHOR_BIG,
        tier=PlayerTier.ELITE_BIG,
        height="6'11\"",
        position="C",
        strengths=["3-point shooting", "Rim protection", "Shot blocking"],
        weaknesses=["Post defense strength", "Rebounding"],
        notes="Rare stretch big + shot blocker combo. Essential for Indiana's spacing.",
        guards_positions=["C"],
        is_elite_defender=True,
    ),
    
    "Kristaps Porzingis": PlayerProfile(
        name="Kristaps Porzingis",
        team="Boston Celtics",
        primary_offensive=OffensiveRole.STRETCH_BIG,
        secondary_offensive=OffensiveRole.RIM_RUNNER,
        defensive_role=DefensiveRole.ANCHOR_BIG,
        tier=PlayerTier.ELITE_BIG,
        height="7'3\"",
        position="C",
        strengths=["Deep range", "Rim protection", "Pick-and-pop", "Length"],
        weaknesses=["Durability", "Lateral movement"],
        notes="7'3\" unicorn. Unlocks Boston's offense with floor spacing.",
        guards_positions=["C", "PF"],
        is_elite_defender=True,
    ),
    
    "Naz Reid": PlayerProfile(
        name="Naz Reid",
        team="Minnesota Timberwolves",
        primary_offensive=OffensiveRole.STRETCH_BIG,
        secondary_offensive=OffensiveRole.SLASHER,
        defensive_role=DefensiveRole.MOBILE_BIG,
        tier=PlayerTier.ELITE_BIG,
        height="6'9\"",
        position="C",
        strengths=["3-point shooting", "Ball handling for big", "Perimeter movement"],
        weaknesses=["Rim protection"],
        notes="Big Jelly. Luxury stretch big who can put ball on floor.",
        guards_positions=["C", "PF"],
    ),
    
    "Nic Claxton": PlayerProfile(
        name="Nic Claxton",
        team="Brooklyn Nets",
        primary_offensive=OffensiveRole.RIM_RUNNER,
        secondary_offensive=OffensiveRole.CONNECTOR,
        defensive_role=DefensiveRole.SWITCH_BIG,
        tier=PlayerTier.ELITE_BIG,
        height="6'11\"",
        position="C",
        strengths=["Switching onto guards", "Lob threat", "Athleticism"],
        weaknesses=["Offensive creation", "Free throw shooting"],
        notes="Elite switch big. Can guard guards in isolation.",
        guards_positions=["C", "PF", "SF"],
        is_elite_defender=True,
    ),
    
    "Isaiah Hartenstein": PlayerProfile(
        name="Isaiah Hartenstein",
        team="Oklahoma City Thunder",
        primary_offensive=OffensiveRole.HUB_BIG,
        secondary_offensive=OffensiveRole.RIM_RUNNER,
        defensive_role=DefensiveRole.ANCHOR_BIG,
        tier=PlayerTier.ELITE_BIG,
        height="7'0\"",
        position="C",
        strengths=["High IQ passing", "Floater", "Rebounding", "Screen setting"],
        weaknesses=["Athleticism"],
        notes="Connector big. Provides physical presence Holmgren lacks.",
        guards_positions=["C"],
    ),
    
    "Walker Kessler": PlayerProfile(
        name="Walker Kessler",
        team="Utah Jazz",
        primary_offensive=OffensiveRole.RIM_RUNNER,
        secondary_offensive=OffensiveRole.CONNECTOR,
        defensive_role=DefensiveRole.ANCHOR_BIG,
        tier=PlayerTier.ELITE_BIG,
        height="7'1\"",
        position="C",
        strengths=["Elite block rate", "Rim protection", "Rebounding"],
        weaknesses=["Perimeter defense", "Offensive versatility"],
        notes="Throwback anchor big. Leads in block rate.",
        guards_positions=["C"],
        is_elite_defender=True,
    ),
    
    "Jalen Duren": PlayerProfile(
        name="Jalen Duren",
        team="Detroit Pistons",
        primary_offensive=OffensiveRole.RIM_RUNNER,
        secondary_offensive=OffensiveRole.POST_SCORER,
        defensive_role=DefensiveRole.ANCHOR_BIG,
        tier=PlayerTier.ELITE_BIG,
        height="6'10\"",
        position="C",
        strengths=["Rebounding", "Athleticism", "Efficiency (67% TS)"],
        weaknesses=["Perimeter defense", "Free throws"],
        notes="Physical force. Anchors Detroit's interior.",
        guards_positions=["C"],
    ),
    
    "Ivica Zubac": PlayerProfile(
        name="Ivica Zubac",
        team="LA Clippers",
        primary_offensive=OffensiveRole.RIM_RUNNER,
        secondary_offensive=OffensiveRole.POST_SCORER,
        defensive_role=DefensiveRole.ANCHOR_BIG,
        tier=PlayerTier.ELITE_BIG,
        height="7'0\"",
        position="C",
        strengths=["Good touch", "Rebounding", "Screens"],
        weaknesses=["Perimeter defense", "Mobility"],
        notes="Traditional big. Good around the rim.",
        guards_positions=["C"],
    ),
    
    "Deandre Ayton": PlayerProfile(
        name="Deandre Ayton",
        team="Portland Trail Blazers",
        primary_offensive=OffensiveRole.POST_SCORER,
        secondary_offensive=OffensiveRole.RIM_RUNNER,
        defensive_role=DefensiveRole.ANCHOR_BIG,
        tier=PlayerTier.ELITE_BIG,
        height="6'11\"",
        position="C",
        strengths=["Midrange shooting", "Rebounding", "Touch"],
        weaknesses=["Motor", "Defensive intensity"],
        notes="Skilled big. Can shoot midrange.",
        guards_positions=["C"],
    ),
    
    "Clint Capela": PlayerProfile(
        name="Clint Capela",
        team="Atlanta Hawks",
        primary_offensive=OffensiveRole.RIM_RUNNER,
        secondary_offensive=OffensiveRole.CONNECTOR,
        defensive_role=DefensiveRole.ANCHOR_BIG,
        tier=PlayerTier.ELITE_BIG,
        height="6'10\"",
        position="C",
        strengths=["Lob threat", "Rebounding", "PnR finishing"],
        weaknesses=["Aging", "Free throws"],
        notes="Elite lob catcher. Perfect PnR partner for Trae.",
        guards_positions=["C"],
    ),
    
    "Jonas Valanciunas": PlayerProfile(
        name="Jonas Valanciunas",
        team="Washington Wizards",
        primary_offensive=OffensiveRole.POST_SCORER,
        secondary_offensive=OffensiveRole.STRETCH_BIG,
        defensive_role=DefensiveRole.ANCHOR_BIG,
        tier=PlayerTier.ELITE_BIG,
        height="6'11\"",
        position="C",
        strengths=["Post moves", "Rebounding", "3-point shooting"],
        weaknesses=["Foot speed", "Perimeter defense"],
        notes="Bruising center. Elite screener.",
        guards_positions=["C"],
    ),
    
    "Nikola Vucevic": PlayerProfile(
        name="Nikola Vucevic",
        team="Chicago Bulls",
        primary_offensive=OffensiveRole.HUB_BIG,
        secondary_offensive=OffensiveRole.STRETCH_BIG,
        defensive_role=DefensiveRole.ANCHOR_BIG,
        tier=PlayerTier.ELITE_BIG,
        height="6'10\"",
        position="C",
        strengths=["Passing", "3-point shooting", "Post game"],
        weaknesses=["Rim protection", "Athleticism"],
        notes="Offensive center. Good passer and shooter.",
        guards_positions=["C"],
    ),
    
    "Brook Lopez": PlayerProfile(
        name="Brook Lopez",
        team="Milwaukee Bucks",
        primary_offensive=OffensiveRole.STRETCH_BIG,
        secondary_offensive=OffensiveRole.RIM_RUNNER,
        defensive_role=DefensiveRole.ANCHOR_BIG,
        tier=PlayerTier.ELITE_BIG,
        height="7'0\"",
        position="C",
        strengths=["3-point shooting", "Rim protection", "Drop coverage"],
        weaknesses=["Mobility", "Perimeter switches"],
        notes="Splash Mountain. Elite drop defender + spacer.",
        guards_positions=["C"],
        is_elite_defender=True,
    ),
    
    "Daniel Gafford": PlayerProfile(
        name="Daniel Gafford",
        team="Dallas Mavericks",
        primary_offensive=OffensiveRole.RIM_RUNNER,
        secondary_offensive=OffensiveRole.CONNECTOR,
        defensive_role=DefensiveRole.ANCHOR_BIG,
        tier=PlayerTier.ELITE_BIG,
        height="6'10\"",
        position="C",
        strengths=["Lob threat", "Rim protection", "Athleticism"],
        weaknesses=["Offensive versatility"],
        notes="Elite efficiency. Lob catcher with Luka.",
        guards_positions=["C"],
        is_elite_defender=True,
    ),
    
    # =========================================================================
    # ADDITIONAL TIER 4: ELITE ROLE PLAYERS
    # =========================================================================
    
    "Kentavious Caldwell-Pope": PlayerProfile(
        name="Kentavious Caldwell-Pope",
        team="Orlando Magic",
        primary_offensive=OffensiveRole.MOVEMENT_SHOOTER,
        secondary_offensive=OffensiveRole.THREE_AND_D,
        defensive_role=DefensiveRole.CHASER,
        tier=PlayerTier.ELITE_ROLE,
        height="6'5\"",
        position="SG",
        strengths=["3-point shooting", "Trail shooting", "Defense"],
        weaknesses=["Creation", "Playmaking"],
        notes="Championship DNA. Elite at chasing shooters around screens.",
        guards_positions=["SG", "SF"],
    ),
    
    "Donte DiVincenzo": PlayerProfile(
        name="Donte DiVincenzo",
        team="Minnesota Timberwolves",
        primary_offensive=OffensiveRole.MOVEMENT_SHOOTER,
        secondary_offensive=OffensiveRole.CONNECTOR,
        defensive_role=DefensiveRole.CHASER,
        tier=PlayerTier.ELITE_ROLE,
        height="6'4\"",
        position="SG",
        strengths=["3-point shooting", "Energy", "Cutting"],
        weaknesses=["Size", "Primary creation"],
        notes="High energy spacer. Excellent catch-and-shoot.",
        guards_positions=["SG", "PG"],
    ),
    
    "Josh Hart": PlayerProfile(
        name="Josh Hart",
        team="New York Knicks",
        primary_offensive=OffensiveRole.CONNECTOR,
        secondary_offensive=OffensiveRole.SLASHER,
        defensive_role=DefensiveRole.WING_DEFENDER,
        tier=PlayerTier.ELITE_ROLE,
        height="6'4\"",
        position="SG",
        strengths=["Rebounding (~10 RPG)", "Energy", "Transition", "IQ"],
        weaknesses=["3-point shooting", "Half-court offense"],
        notes="Unique connector/rebounder. Guard who averages nearly 10 RPG.",
        guards_positions=["SG", "SF"],
    ),
    
    "Trey Murphy III": PlayerProfile(
        name="Trey Murphy III",
        team="New Orleans Pelicans",
        primary_offensive=OffensiveRole.SPOT_UP_SHOOTER,
        secondary_offensive=OffensiveRole.SLASHER,
        defensive_role=DefensiveRole.WING_DEFENDER,
        tier=PlayerTier.ELITE_ROLE,
        height="6'9\"",
        position="SF",
        strengths=["Deep 3-point shooting", "Length", "Athleticism"],
        weaknesses=["Ball handling", "Creation"],
        notes="Deep spacing and vertical athleticism. Breakout player.",
        guards_positions=["SF"],
    ),
    
    "Keegan Murray": PlayerProfile(
        name="Keegan Murray",
        team="Sacramento Kings",
        primary_offensive=OffensiveRole.SPOT_UP_SHOOTER,
        secondary_offensive=OffensiveRole.CUTTER,
        defensive_role=DefensiveRole.WING_DEFENDER,
        tier=PlayerTier.ELITE_ROLE,
        height="6'8\"",
        position="SF",
        strengths=["3-point shooting", "Cutting", "Defensive improvement"],
        weaknesses=["Primary creation", "Ball handling"],
        notes="High-volume spot-up shooter. Cuts well off Sabonis.",
        guards_positions=["SF", "PF"],
    ),
    
    "Cameron Johnson": PlayerProfile(
        name="Cameron Johnson",
        team="Denver Nuggets",
        primary_offensive=OffensiveRole.MOVEMENT_SHOOTER,
        secondary_offensive=OffensiveRole.SPOT_UP_SHOOTER,
        defensive_role=DefensiveRole.CHASER,
        tier=PlayerTier.ELITE_ROLE,
        height="6'8\"",
        position="SF",
        strengths=["Elite shooting", "Length", "Off-ball movement"],
        weaknesses=["Creation", "Defense in ISO"],
        notes="Elite movement shooter. Spaces floor for Jokic.",
        guards_positions=["SF"],
    ),
    
    "Marcus Smart": PlayerProfile(
        name="Marcus Smart",
        team="Memphis Grizzlies",
        primary_offensive=OffensiveRole.CONNECTOR,
        secondary_offensive=OffensiveRole.THREE_AND_D,
        defensive_role=DefensiveRole.POA_DEFENDER,
        tier=PlayerTier.ELITE_ROLE,
        height="6'3\"",
        position="PG",
        strengths=["Defense", "Leadership", "Toughness", "Playmaking"],
        weaknesses=["Shooting efficiency", "Shot selection"],
        notes="Heart and soul defender. Vocal leader. DPOY winner.",
        guards_positions=["PG", "SG"],
        is_elite_defender=True,
        avoid_betting_against=["Marcus Smart"],
    ),
    
    "Christian Braun": PlayerProfile(
        name="Christian Braun",
        team="Denver Nuggets",
        primary_offensive=OffensiveRole.CUTTER,
        secondary_offensive=OffensiveRole.CONNECTOR,
        defensive_role=DefensiveRole.POA_DEFENDER,
        tier=PlayerTier.ELITE_ROLE,
        height="6'6\"",
        position="SG",
        strengths=["Energy", "Defense", "Cutting", "Championship DNA"],
        weaknesses=["Shooting consistency", "Creation"],
        notes="Replaced KCP in Denver lineup. High motor two-way player.",
        guards_positions=["SG", "SF"],
        is_elite_defender=True,
    ),
    
    "Peyton Watson": PlayerProfile(
        name="Peyton Watson",
        team="Denver Nuggets",
        primary_offensive=OffensiveRole.SLASHER,
        secondary_offensive=OffensiveRole.CUTTER,
        defensive_role=DefensiveRole.ROAMER,
        tier=PlayerTier.ELITE_ROLE,
        height="6'8\"",
        position="SF",
        strengths=["Shot blocking", "Athleticism", "Length"],
        weaknesses=["Shooting", "Offensive consistency"],
        notes="Defensive specialist. Elite block rate for a wing.",
        guards_positions=["SF", "PF"],
        is_elite_defender=True,
    ),
    
    "Jerami Grant": PlayerProfile(
        name="Jerami Grant",
        team="Portland Trail Blazers",
        primary_offensive=OffensiveRole.ISOLATION_SCORER,
        secondary_offensive=OffensiveRole.SPOT_UP_SHOOTER,
        defensive_role=DefensiveRole.WING_DEFENDER,
        tier=PlayerTier.ELITE_ROLE,
        height="6'8\"",
        position="SF",
        strengths=["ISO scoring", "Length", "Athleticism"],
        weaknesses=["Efficiency", "Playmaking"],
        notes="High-usage role player. Can spot up and create.",
        guards_positions=["SF", "PF"],
    ),
    
    # =========================================================================
    # ADDITIONAL TIER 5: SPECIALISTS
    # =========================================================================
    
    "CJ McCollum": PlayerProfile(
        name="CJ McCollum",
        team="New Orleans Pelicans",
        primary_offensive=OffensiveRole.SHOT_CREATOR,
        secondary_offensive=OffensiveRole.SPOT_UP_SHOOTER,
        defensive_role=DefensiveRole.CHASED_TARGET,
        tier=PlayerTier.SPECIALIST,
        height="6'3\"",
        position="SG",
        strengths=["Pull-up shooting", "Midrange", "Shot creation"],
        weaknesses=["Defense", "Size"],
        notes="Veteran scorer. Relies on pull-up shooting.",
        guards_positions=["SG"],
    ),
    
    "Anfernee Simons": PlayerProfile(
        name="Anfernee Simons",
        team="Portland Trail Blazers",
        primary_offensive=OffensiveRole.MOVEMENT_SHOOTER,
        secondary_offensive=OffensiveRole.PNR_MAESTRO,
        defensive_role=DefensiveRole.CHASED_TARGET,
        tier=PlayerTier.SPECIALIST,
        height="6'3\"",
        position="SG",
        strengths=["Deep 3-point range", "Shot creation", "Scoring burst"],
        weaknesses=["Defense", "Playmaking"],
        notes="High-volume 3-point shooter with elite range.",
        guards_positions=["SG"],
    ),
    
    "Jordan Poole": PlayerProfile(
        name="Jordan Poole",
        team="Washington Wizards",
        primary_offensive=OffensiveRole.SCORING_GUARD,
        secondary_offensive=OffensiveRole.PNR_MAESTRO,
        defensive_role=DefensiveRole.CHASED_TARGET,
        tier=PlayerTier.SPECIALIST,
        height="6'4\"",
        position="SG",
        strengths=["Scoring burst", "3-point shooting", "Ball handling"],
        weaknesses=["Defense", "Consistency", "Decision making"],
        notes="High usage, high variance scorer. Primary engine for rebuilding team.",
        guards_positions=["SG"],
    ),
    
    "Fred VanVleet": PlayerProfile(
        name="Fred VanVleet",
        team="Houston Rockets",
        primary_offensive=OffensiveRole.PNR_MAESTRO,
        secondary_offensive=OffensiveRole.SPOT_UP_SHOOTER,
        defensive_role=DefensiveRole.POA_DEFENDER,
        tier=PlayerTier.SPECIALIST,
        height="6'1\"",
        position="PG",
        strengths=["Leadership", "3-point shooting", "Defense for size"],
        weaknesses=["Size", "Finishing at rim"],
        notes="Stabilizing floor general. High IQ defender despite size.",
        guards_positions=["PG"],
        is_elite_defender=True,
    ),
    
    "Austin Reaves": PlayerProfile(
        name="Austin Reaves",
        team="Los Angeles Lakers",
        primary_offensive=OffensiveRole.CONNECTOR,
        secondary_offensive=OffensiveRole.PNR_MAESTRO,
        defensive_role=DefensiveRole.CHASER,
        tier=PlayerTier.SPECIALIST,
        height="6'5\"",
        position="SG",
        strengths=["IQ", "Playmaking", "Drawing fouls", "Clutch"],
        weaknesses=["Athleticism", "Speed"],
        notes="Versatile guard. Fits well next to stars.",
        guards_positions=["SG"],
    ),
    
    "Malik Monk": PlayerProfile(
        name="Malik Monk",
        team="Sacramento Kings",
        primary_offensive=OffensiveRole.SCORING_GUARD,
        secondary_offensive=OffensiveRole.PNR_MAESTRO,
        defensive_role=DefensiveRole.CHASER,
        tier=PlayerTier.SPECIALIST,
        height="6'3\"",
        position="SG",
        strengths=["Instant offense", "3-point shooting", "Scoring burst"],
        weaknesses=["Defense", "Consistency"],
        notes="Elite 6th man scorer. Provides instant offense and playmaking.",
        guards_positions=["SG"],
    ),
    
    "Bogdan Bogdanovic": PlayerProfile(
        name="Bogdan Bogdanovic",
        team="Atlanta Hawks",
        primary_offensive=OffensiveRole.MOVEMENT_SHOOTER,
        secondary_offensive=OffensiveRole.CONNECTOR,
        defensive_role=DefensiveRole.CHASER,
        tier=PlayerTier.SPECIALIST,
        height="6'6\"",
        position="SG",
        strengths=["FIBA-style scoring", "Off screens", "Playmaking"],
        weaknesses=["Defense", "Athleticism"],
        notes="FIBA-style scorer. Excellent coming off screens.",
        guards_positions=["SG"],
    ),
    
    "Terry Rozier": PlayerProfile(
        name="Terry Rozier",
        team="Miami Heat",
        primary_offensive=OffensiveRole.SCORING_GUARD,
        secondary_offensive=OffensiveRole.PNR_MAESTRO,
        defensive_role=DefensiveRole.POA_DEFENDER,
        tier=PlayerTier.SPECIALIST,
        height="6'1\"",
        position="PG",
        strengths=["Scoring burst", "Pull-up shooting", "Clutch"],
        weaknesses=["Consistency", "Size"],
        notes="Scary Terry. Can heat up quickly.",
        guards_positions=["PG", "SG"],
    ),
    
    "D'Angelo Russell": PlayerProfile(
        name="D'Angelo Russell",
        team="Los Angeles Lakers",
        primary_offensive=OffensiveRole.PNR_MAESTRO,
        secondary_offensive=OffensiveRole.SPOT_UP_SHOOTER,
        defensive_role=DefensiveRole.CHASED_TARGET,
        tier=PlayerTier.SPECIALIST,
        height="6'4\"",
        position="PG",
        strengths=["Shooting", "Playmaking", "Ice in veins"],
        weaknesses=["Defense", "Inconsistency"],
        notes="Streaky shooter/passer. Creative playmaker.",
        guards_positions=["PG"],
    ),
    
    "Coby White": PlayerProfile(
        name="Coby White",
        team="Chicago Bulls",
        primary_offensive=OffensiveRole.SCORING_GUARD,
        secondary_offensive=OffensiveRole.PNR_MAESTRO,
        defensive_role=DefensiveRole.CHASER,
        tier=PlayerTier.SPECIALIST,
        height="6'5\"",
        position="PG",
        strengths=["Scoring burst", "3-point shooting", "Transition"],
        weaknesses=["Defense", "Decision making"],
        notes="Breakout scorer. Fast-paced transition threat.",
        guards_positions=["PG", "SG"],
    ),
    
    "Josh Giddey": PlayerProfile(
        name="Josh Giddey",
        team="Chicago Bulls",
        primary_offensive=OffensiveRole.CONNECTOR,
        secondary_offensive=OffensiveRole.POINT_FORWARD,
        defensive_role=DefensiveRole.CHASER,
        tier=PlayerTier.SPECIALIST,
        height="6'8\"",
        position="PG",
        strengths=["Elite passing", "Rebounding", "Court vision"],
        weaknesses=["Shooting", "Defense"],
        notes="SLOB wizard. Elite passer, struggles with shooting.",
        guards_positions=["PG", "SG"],
    ),
    
    "RJ Barrett": PlayerProfile(
        name="RJ Barrett",
        team="Toronto Raptors",
        primary_offensive=OffensiveRole.SLASHER,
        secondary_offensive=OffensiveRole.SPOT_UP_SHOOTER,
        defensive_role=DefensiveRole.WING_DEFENDER,
        tier=PlayerTier.SPECIALIST,
        height="6'6\"",
        position="SG",
        strengths=["Physical driving", "Improved 3PT", "Defense"],
        weaknesses=["Efficiency", "Creation in half-court"],
        notes="Physical driver. Thrives getting downhill.",
        guards_positions=["SG", "SF"],
    ),
    
    "Dejounte Murray": PlayerProfile(
        name="Dejounte Murray",
        team="New Orleans Pelicans",
        primary_offensive=OffensiveRole.PNR_MAESTRO,
        secondary_offensive=OffensiveRole.CONNECTOR,
        defensive_role=DefensiveRole.POA_DEFENDER,
        tier=PlayerTier.SPECIALIST,
        height="6'4\"",
        position="PG",
        strengths=["Defense", "Rebounding for guard", "Playmaking"],
        weaknesses=["3-point shooting", "Efficiency"],
        notes="Two-way guard. Long arms allow for deflection-heavy defense.",
        guards_positions=["PG", "SG"],
        is_elite_defender=True,
    ),
    
    "Collin Sexton": PlayerProfile(
        name="Collin Sexton",
        team="Utah Jazz",
        primary_offensive=OffensiveRole.SLASHER,
        secondary_offensive=OffensiveRole.SCORING_GUARD,
        defensive_role=DefensiveRole.CHASER,
        tier=PlayerTier.SPECIALIST,
        height="6'1\"",
        position="PG",
        strengths=["Rim attacking", "Energy", "Scoring burst"],
        weaknesses=["Playmaking", "Defense"],
        notes="High energy scorer. Relentless rim attacker.",
        guards_positions=["PG"],
    ),
    
    "Klay Thompson": PlayerProfile(
        name="Klay Thompson",
        team="Dallas Mavericks",
        primary_offensive=OffensiveRole.SPOT_UP_SHOOTER,
        secondary_offensive=OffensiveRole.MOVEMENT_SHOOTER,
        defensive_role=DefensiveRole.WING_DEFENDER,
        tier=PlayerTier.SPECIALIST,
        height="6'6\"",
        position="SG",
        strengths=["3-point shooting", "Off-ball movement", "IQ"],
        weaknesses=["Lost lateral quickness", "Creation"],
        notes="Spacer for Luka/Kyrie. Still smart defender.",
        guards_positions=["SG"],
    ),
    
    "Kyle Kuzma": PlayerProfile(
        name="Kyle Kuzma",
        team="Washington Wizards",
        primary_offensive=OffensiveRole.SHOT_CREATOR,
        secondary_offensive=OffensiveRole.POINT_FORWARD,
        defensive_role=DefensiveRole.ROAMER,
        tier=PlayerTier.SPECIALIST,
        height="6'10\"",
        position="PF",
        strengths=["Scoring versatility", "Rebounding", "Creation"],
        weaknesses=["Defense", "Efficiency"],
        notes="High usage forward. Can create own shot.",
        guards_positions=["PF", "SF"],
    ),
    
    "Miles Bridges": PlayerProfile(
        name="Miles Bridges",
        team="Charlotte Hornets",
        primary_offensive=OffensiveRole.SLASHER,
        secondary_offensive=OffensiveRole.SHOT_CREATOR,
        defensive_role=DefensiveRole.WING_DEFENDER,
        tier=PlayerTier.SPECIALIST,
        height="6'6\"",
        position="SF",
        strengths=["Athleticism", "Finishing", "Scoring burst"],
        weaknesses=["Decision making", "Consistency"],
        notes="Athletic scorer. Powerful finisher at the rim.",
        guards_positions=["SF"],
    ),
    
    "Tobias Harris": PlayerProfile(
        name="Tobias Harris",
        team="Detroit Pistons",
        primary_offensive=OffensiveRole.SPOT_UP_SHOOTER,
        secondary_offensive=OffensiveRole.POST_SCORER,
        defensive_role=DefensiveRole.WING_DEFENDER,
        tier=PlayerTier.SPECIALIST,
        height="6'8\"",
        position="PF",
        strengths=["Veteran experience", "Midrange", "3-point shooting"],
        weaknesses=["Primary creation", "Athleticism"],
        notes="Veteran scorer. Stabilizing presence for young team.",
        guards_positions=["SF", "PF"],
    ),
    
    "Caris LeVert": PlayerProfile(
        name="Caris LeVert",
        team="Cleveland Cavaliers",
        primary_offensive=OffensiveRole.CONNECTOR,
        secondary_offensive=OffensiveRole.SLASHER,
        defensive_role=DefensiveRole.CHASER,
        tier=PlayerTier.SPECIALIST,
        height="6'6\"",
        position="SG",
        strengths=["Playmaking", "Scoring off bench", "Ball handling"],
        weaknesses=["Efficiency", "Defense"],
        notes="Bench creator. Good passer.",
        guards_positions=["SG", "SF"],
    ),
    
    "Grayson Allen": PlayerProfile(
        name="Grayson Allen",
        team="Phoenix Suns",
        primary_offensive=OffensiveRole.SPOT_UP_SHOOTER,
        secondary_offensive=OffensiveRole.CONNECTOR,
        defensive_role=DefensiveRole.CHASER,
        tier=PlayerTier.SPECIALIST,
        height="6'4\"",
        position="SG",
        strengths=["3-point shooting", "Toughness", "IQ"],
        weaknesses=["Creation", "Athleticism"],
        notes="Elite 3-point shooter. Tough competitor.",
        guards_positions=["SG"],
    ),
    
    "Max Strus": PlayerProfile(
        name="Max Strus",
        team="Cleveland Cavaliers",
        primary_offensive=OffensiveRole.MOVEMENT_SHOOTER,
        secondary_offensive=OffensiveRole.CONNECTOR,
        defensive_role=DefensiveRole.CHASER,
        tier=PlayerTier.SPECIALIST,
        height="6'5\"",
        position="SG",
        strengths=["3-point shooting", "Energy", "Movement"],
        weaknesses=["Creation", "Defense"],
        notes="High energy spacer. Excellent catch-and-shoot.",
        guards_positions=["SG"],
    ),
    
    "Gary Trent Jr.": PlayerProfile(
        name="Gary Trent Jr.",
        team="Milwaukee Bucks",
        primary_offensive=OffensiveRole.SPOT_UP_SHOOTER,
        secondary_offensive=OffensiveRole.MOVEMENT_SHOOTER,
        defensive_role=DefensiveRole.CHASER,
        tier=PlayerTier.SPECIALIST,
        height="6'5\"",
        position="SG",
        strengths=["3-point shooting", "Steals", "Movement"],
        weaknesses=["Playmaking", "Defense consistency"],
        notes="Floor spacer for Giannis. Volume shooter.",
        guards_positions=["SG"],
    ),
    
    "Bobby Portis": PlayerProfile(
        name="Bobby Portis",
        team="Milwaukee Bucks",
        primary_offensive=OffensiveRole.STRETCH_BIG,
        secondary_offensive=OffensiveRole.POST_SCORER,
        defensive_role=DefensiveRole.ROAMER,
        tier=PlayerTier.SPECIALIST,
        height="6'10\"",
        position="PF",
        strengths=["Energy", "Rebounding", "3-point shooting"],
        weaknesses=["Defense", "Rim protection"],
        notes="High energy bench big. Fan favorite.",
        guards_positions=["PF"],
    ),
    
    # =========================================================================
    # ADDITIONAL TIER 6: ROTATION PIECES
    # =========================================================================
    
    "Jonathan Kuminga": PlayerProfile(
        name="Jonathan Kuminga",
        team="Golden State Warriors",
        primary_offensive=OffensiveRole.SLASHER,
        secondary_offensive=OffensiveRole.ISOLATION_SCORER,
        defensive_role=DefensiveRole.WING_DEFENDER,
        tier=PlayerTier.ROTATION,
        height="6'8\"",
        position="SF",
        strengths=["Athleticism", "Finishing", "Developing ISO game"],
        weaknesses=["3-point shooting", "Decision making"],
        notes="Athletic wing. Developing isolation game.",
        guards_positions=["SF", "PF"],
    ),
    
    "Deni Avdija": PlayerProfile(
        name="Deni Avdija",
        team="Portland Trail Blazers",
        primary_offensive=OffensiveRole.POINT_FORWARD,
        secondary_offensive=OffensiveRole.SLASHER,
        defensive_role=DefensiveRole.WING_DEFENDER,
        tier=PlayerTier.ROTATION,
        height="6'9\"",
        position="SF",
        strengths=["Playmaking", "Length", "Versatility"],
        weaknesses=["Shooting consistency", "Strength"],
        notes="Versatile playmaker. Good size for position.",
        guards_positions=["SF"],
    ),
    
    "Jeremy Sochan": PlayerProfile(
        name="Jeremy Sochan",
        team="San Antonio Spurs",
        primary_offensive=OffensiveRole.CONNECTOR,
        secondary_offensive=OffensiveRole.SLASHER,
        defensive_role=DefensiveRole.WING_STOPPER,
        tier=PlayerTier.ROTATION,
        height="6'9\"",
        position="PF",
        strengths=["Defense", "Versatility", "Motor"],
        weaknesses=["Shooting", "Offensive creation"],
        notes="Rodman role. Defensive specialist, limited shooter.",
        guards_positions=["SF", "PF"],
        is_elite_defender=True,
    ),
    
    "Rui Hachimura": PlayerProfile(
        name="Rui Hachimura",
        team="Los Angeles Lakers",
        primary_offensive=OffensiveRole.SPOT_UP_SHOOTER,
        secondary_offensive=OffensiveRole.POST_SCORER,
        defensive_role=DefensiveRole.WING_DEFENDER,
        tier=PlayerTier.ROTATION,
        height="6'8\"",
        position="PF",
        strengths=["Midrange", "Post scoring", "Improving 3PT"],
        weaknesses=["Playmaking", "Lateral quickness"],
        notes="Fits well next to LeBron/AD. Midrange/post scorer.",
        guards_positions=["SF", "PF"],
    ),
    
    "Michael Porter Jr.": PlayerProfile(
        name="Michael Porter Jr.",
        team="Denver Nuggets",
        primary_offensive=OffensiveRole.SPOT_UP_SHOOTER,
        secondary_offensive=OffensiveRole.MOVEMENT_SHOOTER,
        defensive_role=DefensiveRole.ROAMER,
        tier=PlayerTier.ROTATION,
        height="6'10\"",
        position="SF",
        strengths=["Elite 3-point shooting", "Length", "Rebounding"],
        weaknesses=["Ball handling", "Defense"],
        notes="6'10\" shooter. Catch-and-shoot specialist next to Jokic.",
        guards_positions=["SF"],
    ),
    
    "De'Andre Hunter": PlayerProfile(
        name="De'Andre Hunter",
        team="Cleveland Cavaliers",
        primary_offensive=OffensiveRole.THREE_AND_D,
        secondary_offensive=OffensiveRole.SPOT_UP_SHOOTER,
        defensive_role=DefensiveRole.WING_DEFENDER,
        tier=PlayerTier.ROTATION,
        height="6'8\"",
        position="SF",
        strengths=["3-and-D", "Length", "Improving shot"],
        weaknesses=["Creation", "Durability"],
        notes="Solid two-way wing. Good size for position.",
        guards_positions=["SF"],
    ),
    
    "Saddiq Bey": PlayerProfile(
        name="Saddiq Bey",
        team="Washington Wizards",
        primary_offensive=OffensiveRole.SPOT_UP_SHOOTER,
        secondary_offensive=OffensiveRole.SLASHER,
        defensive_role=DefensiveRole.WING_DEFENDER,
        tier=PlayerTier.ROTATION,
        height="6'7\"",
        position="SF",
        strengths=["3-point volume", "Rebounding", "Versatility"],
        weaknesses=["Efficiency", "Defense consistency"],
        notes="Volume 3-point shooter. Can play multiple positions.",
        guards_positions=["SF"],
    ),
    
    "Obi Toppin": PlayerProfile(
        name="Obi Toppin",
        team="Indiana Pacers",
        primary_offensive=OffensiveRole.RIM_RUNNER,
        secondary_offensive=OffensiveRole.SPOT_UP_SHOOTER,
        defensive_role=DefensiveRole.ROAMER,
        tier=PlayerTier.ROTATION,
        height="6'9\"",
        position="PF",
        strengths=["Transition dunking", "Energy", "3-point improvement"],
        weaknesses=["Defense", "Post defense"],
        notes="Transition dunker. High energy off bench.",
        guards_positions=["PF"],
    ),
    
    "Isaiah Stewart": PlayerProfile(
        name="Isaiah Stewart",
        team="Detroit Pistons",
        primary_offensive=OffensiveRole.RIM_RUNNER,
        secondary_offensive=OffensiveRole.STRETCH_BIG,
        defensive_role=DefensiveRole.SWITCH_BIG,
        tier=PlayerTier.ROTATION,
        height="6'9\"",
        position="C",
        strengths=["Physical defense", "Added 3-point shot", "Motor"],
        weaknesses=["Rim protection", "Size"],
        notes="Physical defender. Has added 3-point shot.",
        guards_positions=["C", "PF"],
    ),
    
    "Zach Collins": PlayerProfile(
        name="Zach Collins",
        team="San Antonio Spurs",
        primary_offensive=OffensiveRole.STRETCH_BIG,
        secondary_offensive=OffensiveRole.POST_SCORER,
        defensive_role=DefensiveRole.ANCHOR_BIG,
        tier=PlayerTier.ROTATION,
        height="6'11\"",
        position="C",
        strengths=["3-point shooting", "Post moves", "IQ"],
        weaknesses=["Durability", "Athleticism"],
        notes="Spacer for Wemby. Veteran IQ.",
        guards_positions=["C"],
    ),
    
    "Kelly Olynyk": PlayerProfile(
        name="Kelly Olynyk",
        team="Toronto Raptors",
        primary_offensive=OffensiveRole.STRETCH_BIG,
        secondary_offensive=OffensiveRole.CONNECTOR,
        defensive_role=DefensiveRole.ANCHOR_BIG,
        tier=PlayerTier.ROTATION,
        height="6'11\"",
        position="C",
        strengths=["Playmaking", "3-point shooting", "IQ"],
        weaknesses=["Rim protection", "Athleticism"],
        notes="Playmaking big. High IQ connector.",
        guards_positions=["C"],
    ),
    
    "Al Horford": PlayerProfile(
        name="Al Horford",
        team="Boston Celtics",
        primary_offensive=OffensiveRole.STRETCH_BIG,
        secondary_offensive=OffensiveRole.CONNECTOR,
        defensive_role=DefensiveRole.SWITCH_BIG,
        tier=PlayerTier.ROTATION,
        height="6'9\"",
        position="C",
        strengths=["Elite IQ", "Switching", "Veteran leadership"],
        weaknesses=["Age", "Athleticism decline"],
        notes="Veteran leader. Elite defensive IQ, can switch.",
        guards_positions=["C", "PF"],
    ),
}


# ============================================================================
# Player Groupings (Similar Players)
# ============================================================================

PLAYER_SIMILARITY_GROUPS: dict[str, list[str]] = {
    # Heliocentric ball-dominant guards - high USG%, team revolves around them
    "Heliocentric Guards": [
        "Luka Doncic", "Trae Young", "Ja Morant", "LaMelo Ball",
        "James Harden", "Shai Gilgeous-Alexander",
    ],
    
    # PnR Maestros - elite pick-and-roll operators
    "Pick-and-Roll Maestros": [
        "Trae Young", "Tyrese Haliburton", "Cade Cunningham", "Jamal Murray",
        "Stephen Curry", "Darius Garland", "Fred VanVleet", "Dejounte Murray",
        "D'Angelo Russell", "Anfernee Simons",
    ],
    
    # Speed Slashers - use speed to attack the rim
    "Speed Slashers": [
        "Ja Morant", "De'Aaron Fox", "Tyrese Maxey", "Anthony Edwards",
        "Shai Gilgeous-Alexander", "Jalen Green", "Collin Sexton",
    ],
    
    # Hub Bigs (Passing Centers) - facilitate from the high post
    "Hub Bigs": [
        "Nikola Jokic", "Domantas Sabonis", "Alperen Sengun", "Bam Adebayo",
        "Isaiah Hartenstein", "Nikola Vucevic",
    ],
    
    # Stretch Bigs - floor-spacing centers
    "Stretch Bigs": [
        "Karl-Anthony Towns", "Victor Wembanyama", "Chet Holmgren",
        "Kristaps Porzingis", "Myles Turner", "Brook Lopez", "Naz Reid",
        "Lauri Markkanen",
    ],
    
    # Elite Two-Way Wings - star wings who excel on both ends
    "Elite Two-Way Wings": [
        "Jayson Tatum", "Kawhi Leonard", "Jimmy Butler", "Paul George",
        "Anthony Edwards", "Jaylen Brown", "Jalen Williams", "Franz Wagner",
    ],
    
    # Point Forwards - forwards who initiate offense like guards
    "Point Forwards": [
        "LeBron James", "Scottie Barnes", "Paolo Banchero", "Giannis Antetokounmpo",
        "Zion Williamson", "Pascal Siakam", "Josh Giddey", "Deni Avdija",
    ],
    
    # 3-and-D Specialists - elite corner shooters and wing defenders
    "3-and-D Specialists": [
        "OG Anunoby", "Mikal Bridges", "Jaden McDaniels", "Herbert Jones",
        "Dillon Brooks", "Kentavious Caldwell-Pope", "Trey Murphy III",
        "Keegan Murray", "De'Andre Hunter",
    ],
    
    # Elite POA Defenders - best point-of-attack defenders
    "Elite POA Defenders": [
        "Jrue Holiday", "Derrick White", "Alex Caruso", "Luguentz Dort",
        "Jalen Suggs", "Marcus Smart", "Fred VanVleet", "Dejounte Murray",
        "Christian Braun", "Amen Thompson",
    ],
    
    # Switchable Bigs - can defend guards on the perimeter
    "Switchable Bigs": [
        "Bam Adebayo", "Evan Mobley", "Scottie Barnes", "Nic Claxton",
        "Al Horford", "Naz Reid", "Jabari Smith Jr.",
    ],
    
    # Movement Shooters - run off screens, elite catch-and-shoot
    "Movement Shooters": [
        "Stephen Curry", "Klay Thompson", "Desmond Bane", "Norman Powell",
        "Donte DiVincenzo", "Cameron Johnson", "Anfernee Simons", 
        "Bogdan Bogdanovic", "Max Strus",
    ],
    
    # Microwave Scorers - instant offense off the bench
    "Bench Microwave Scorers": [
        "Tyler Herro", "Norman Powell", "Malik Monk", "Immanuel Quickley",
        "Jordan Poole", "Coby White", "Terry Rozier",
    ],
    
    # Anchor Bigs - elite rim protectors / drop coverage specialists
    "Rim Protection Anchors": [
        "Rudy Gobert", "Victor Wembanyama", "Walker Kessler", "Brook Lopez",
        "Jarrett Allen", "Myles Turner", "Daniel Gafford", "Chet Holmgren",
    ],
    
    # Isolation Scorers - elite at creating own shot in ISO
    "Isolation Scorers": [
        "Kevin Durant", "Kawhi Leonard", "Jayson Tatum", "Brandon Ingram",
        "DeMar DeRozan", "Kyrie Irving", "Zach LaVine", "Jerami Grant",
    ],
    
    # Midrange Specialists - efficient midrange scorers
    "Midrange Specialists": [
        "Kevin Durant", "DeMar DeRozan", "Kawhi Leonard", "Khris Middleton",
        "CJ McCollum", "Brandon Ingram", "Devin Booker",
    ],
    
    # Connectors - high IQ glue guys who keep offense flowing
    "High IQ Connectors": [
        "Derrick White", "Jrue Holiday", "Alex Caruso", "Josh Hart",
        "Austin Reaves", "Josh Giddey", "Scottie Barnes", "Caris LeVert",
    ],
    
    # Athletic Slashers - explosive rim attackers
    "Athletic Slashers": [
        "Giannis Antetokounmpo", "Anthony Edwards", "Zion Williamson",
        "Ja Morant", "Jonathan Kuminga", "Miles Bridges", "Amen Thompson",
        "Ausar Thompson",
    ],
    
    # Traditional Rim Runners - lob threats, dunker spot specialists
    "Rim Runners": [
        "Clint Capela", "Daniel Gafford", "Jarrett Allen", "Jalen Duren",
        "Obi Toppin", "Nic Claxton", "Ivica Zubac", "Deandre Ayton",
    ],
}


# ============================================================================
# Elite Defender Tracking
# ============================================================================

# Players to avoid betting OVER on when facing these defenders
# Comprehensive list based on defensive archetype research
ELITE_DEFENDERS_BY_POSITION: dict[str, list[str]] = {
    "PG": [
        # POA Defenders - navigate screens, stay attached to ball handlers
        "Jrue Holiday", "Derrick White", "Alex Caruso", "Luguentz Dort",
        "Jalen Suggs", "Marcus Smart", "De'Aaron Fox", "Fred VanVleet",
        "Dejounte Murray", "Christian Braun", "Amen Thompson", "Immanuel Quickley",
    ],
    "SG": [
        # Wing stoppers and POA who guard shooting guards
        "Anthony Edwards", "Jaylen Brown", "OG Anunoby", "Mikal Bridges",
        "Derrick White", "Luguentz Dort", "Jalen Suggs", "Alex Caruso",
        "Desmond Bane", "Josh Hart",
    ],
    "SF": [
        # Wing stoppers - assigned to best scoring wings
        "OG Anunoby", "Kawhi Leonard", "Jimmy Butler", "Jayson Tatum",
        "Herbert Jones", "Jaden McDaniels", "Dillon Brooks", "Mikal Bridges",
        "Aaron Gordon", "Jalen Williams", "Franz Wagner", "Scottie Barnes",
        "Ausar Thompson", "Tari Eason", "Jeremy Sochan", "Peyton Watson",
    ],
    "PF": [
        # Versatile defenders who guard power forwards / roamers
        "Giannis Antetokounmpo", "Anthony Davis", "Evan Mobley", "Aaron Gordon",
        "Scottie Barnes", "Pascal Siakam", "Cade Cunningham", "Paolo Banchero",
        "Jabari Smith Jr.",
    ],
    "C": [
        # Anchor bigs / rim protectors - deter shots at the rim
        "Rudy Gobert", "Victor Wembanyama", "Anthony Davis", "Bam Adebayo",
        "Evan Mobley", "Jarrett Allen", "Chet Holmgren", "Walker Kessler",
        "Brook Lopez", "Myles Turner", "Daniel Gafford", "Nic Claxton",
        "Joel Embiid",
    ],
}


# ============================================================================
# Helper Functions
# ============================================================================

def get_player_profile(name: str) -> Optional[PlayerProfile]:
    """Get a player's full profile."""
    return PLAYER_DATABASE.get(name)


def get_similar_players(name: str) -> list[str]:
    """Get players similar to the given player."""
    similar = []
    for group_name, players in PLAYER_SIMILARITY_GROUPS.items():
        if name in players:
            similar.extend([p for p in players if p != name])
    return list(set(similar))


def get_elite_defenders_for_position(position: str) -> list[str]:
    """Get elite defenders who guard a specific position."""
    return ELITE_DEFENDERS_BY_POSITION.get(position.upper(), [])


def should_avoid_betting_over(
    player_name: str,
    opponent_roster: list[str],
) -> tuple[bool, list[str]]:
    """
    Check if we should avoid betting OVER on a player based on opponent's defenders.
    
    Returns:
        (should_avoid, list of elite defenders on opponent)
    """
    profile = get_player_profile(player_name)
    if not profile:
        return False, []
    
    # Get positions player might be guarded at
    positions = [profile.position] if profile.position else []
    
    # Find elite defenders on opponent
    defenders_to_worry = []
    for pos in positions:
        elite = get_elite_defenders_for_position(pos)
        for defender in elite:
            if defender in opponent_roster:
                defenders_to_worry.append(defender)
    
    # Check if any specific players to avoid
    for defender in profile.avoid_betting_against:
        if defender in opponent_roster:
            defenders_to_worry.append(defender)
    
    return len(defenders_to_worry) > 0, list(set(defenders_to_worry))


def get_archetype_matchup_adjustment(
    player_profile: PlayerProfile,
    defender_profile: Optional[PlayerProfile],
) -> float:
    """
    Calculate projection adjustment based on archetype matchup.
    
    Returns multiplier (1.0 = no adjustment, <1.0 = expect lower, >1.0 = expect higher)
    """
    if not defender_profile:
        return 1.0
    
    adjustment = 1.0
    
    # Check if facing elite defender
    if defender_profile.is_elite_defender:
        adjustment *= 0.92  # 8% reduction against elite defenders
    
    # Specific matchup adjustments
    off_role = player_profile.primary_offensive
    def_role = defender_profile.defensive_role
    
    # Slashers vs Anchor Bigs
    if off_role == OffensiveRole.SLASHER and def_role == DefensiveRole.ANCHOR_BIG:
        adjustment *= 0.90  # Rim protection hurts slashers
    
    # Stretch Bigs vs traditional drop coverage
    if off_role == OffensiveRole.STRETCH_BIG and def_role == DefensiveRole.ANCHOR_BIG:
        adjustment *= 1.10  # Stretch beats drop coverage
    
    # Hub Bigs vs Switch Bigs
    if off_role == OffensiveRole.HUB_BIG and def_role == DefensiveRole.SWITCH_BIG:
        adjustment *= 1.05  # Can still exploit post-ups
    
    # POA vs Chased Target
    if def_role == DefensiveRole.POA_DEFENDER:
        if player_profile.defensive_role == DefensiveRole.CHASED_TARGET:
            # Player is used to being hidden, now facing POA
            adjustment *= 0.95
    
    # Movement Shooters vs Chasers
    if off_role == OffensiveRole.MOVEMENT_SHOOTER and def_role == DefensiveRole.CHASER:
        adjustment *= 0.95  # Chasers specifically trained for this
    
    # Wing Stoppers vs Scoring Wings
    if def_role == DefensiveRole.WING_STOPPER:
        if off_role in [OffensiveRole.ISOLATION_SCORER, OffensiveRole.SHOT_CREATOR, OffensiveRole.SCORING_WING]:
            adjustment *= 0.92  # Wing stoppers limit scoring wings
    
    return adjustment


def get_roster_for_team(team: str) -> list[PlayerProfile]:
    """Get all players in database for a team."""
    return [p for p in PLAYER_DATABASE.values() if p.team == team]


def get_all_elite_defenders() -> list[str]:
    """Get list of all elite defenders."""
    return [name for name, profile in PLAYER_DATABASE.items() if profile.is_elite_defender]


def get_players_by_tier(tier: PlayerTier) -> list[str]:
    """Get all players of a specific tier."""
    return [name for name, profile in PLAYER_DATABASE.items() if profile.tier == tier]


#!/usr/bin/env python3
"""
Compute a single player card for bridge game assignments.

This module provides functions to compute a player card for a single player
given the game assignments data.
"""

import random
from typing import Dict, List, Optional


def compute_player_card(
    player_num: int,
    player_games: Dict[int, List[Dict]],
    sitting_out: Dict[int, List[int]]
) -> Dict:
    """
    Compute a player card for a single player.
    
    Args:
        player_num: The player number (1-indexed)
        player_games: Dictionary mapping player numbers to their game assignments
        sitting_out: Dictionary mapping player numbers to games they're sitting out
    
    Returns:
        Dictionary with player's game assignments in card format
    """
    games = player_games.get(player_num, [])
    sitting = sitting_out.get(player_num, [])
    
    card = {
        'player': player_num,
        'games': [],
        'sitting_out': sitting
    }
    
    for game_info in sorted(games, key=lambda x: x['game']):
        # Use the stored partner if available, otherwise pick from teammates
        partner = game_info.get('partner')
        if partner is None:
            teammates = game_info.get('teammates', [])
            partner = random.choice(teammates) if teammates else None
        
        card['games'].append({
            'game': game_info['game'],
            'table': game_info['table'],
            'partner': partner
        })
    
    return card


def format_player_card_markdown(card: Dict) -> str:
    """
    Format a player card as markdown (matching playerCard.md format).
    
    Args:
        card: Player card dictionary from compute_player_card()
    
    Returns:
        Markdown formatted string
    """
    lines = []
    lines.append(f"# Player {card['player']}")
    lines.append("# Table 1")
    lines.append("")
    lines.append("|Game|Table|Partner|")
    lines.append("|--|--|--|")
    
    for game in card['games']:
        lines.append(f"|{game['game']}|{game['table']}|{game['partner']}|")
    
    if card['sitting_out']:
        sitting_str = ', '.join(map(str, sorted(card['sitting_out'])))
        lines.append("")
        lines.append(f"*Sitting out: Game {sitting_str}*")
    
    return '\n'.join(lines)


def format_player_card_table(card: Dict) -> str:
    """
    Format a player card as a text table (for console output).
    
    Args:
        card: Player card dictionary from compute_player_card()
    
    Returns:
        Text formatted string
    """
    lines = []
    lines.append(f"Player #{card['player']}")
    lines.append(f"{'Game':<6} {'Table':<6} {'Partner':<8}")
    lines.append(f"{'-'*20}")
    
    for game in card['games']:
        lines.append(f"{game['game']:<6} {game['table']:<6} {game['partner']:<8}")
    
    if card['sitting_out']:
        sitting_str = ', '.join(map(str, sorted(card['sitting_out'])))
        lines.append(f"\nSitting out: Game {sitting_str}")
    
    return '\n'.join(lines)


if __name__ == "__main__":
    # Test example
    example_games = {
        1: [
            {'game': 1, 'table': 1, 'teammates': [2, 3, 4]},
            {'game': 2, 'table': 3, 'teammates': [5, 6, 7]},
            {'game': 3, 'table': 5, 'teammates': [25, 26, 27]}
        ]
    }
    example_sitting = {}
    
    card = compute_player_card(1, example_games, example_sitting)
    print("Markdown format:")
    print(format_player_card_markdown(card))
    print("\n" + "="*40 + "\n")
    print("Table format:")
    print(format_player_card_table(card))
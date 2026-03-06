#!/usr/bin/env python3
"""
Generate player cards for bridge game assignments.

Configuration:
- Specify number of tables (always 4 players per table)
- Specify number of games/rounds
- All players play every game
- Random assignment with varied pairings
"""

import random
from collections import defaultdict
from typing import Dict, List
import csv
from datetime import datetime

from compute_player_card import compute_player_card, format_player_card_markdown, format_player_card_table


class PlayerCardGenerator:
    def __init__(self, tables: int = 5, games: int = 3, player_names: List[str] = None):
        self.tables = tables
        self.games = games
        self.players_per_table = 4
        
        if player_names:
            self.player_names = player_names
            self.num_players = len(player_names)
            # Create mapping from 1-indexed to names
            self.players = list(range(1, self.num_players + 1))
            self.name_map = {i: name for i, name in enumerate(player_names, 1)}
        else:
            # Default: numbered players
            self.num_players = tables * self.players_per_table
            self.players = list(range(1, self.num_players + 1))
            self.player_names = [str(p) for p in self.players]
            self.name_map = {p: str(p) for p in self.players}
        
        self.player_games = defaultdict(list)
    
    def generate_cards(self) -> Dict:
        """Generate player assignments with randomized pairs per game."""
        for game_num in range(1, self.games + 1):
            # Shuffle players for this game
            shuffled = self.players.copy()
            random.shuffle(shuffled)
            
            # Create pairs from shuffled list: (0,1), (2,3), (4,5), etc.
            pairs = []
            for i in range(0, len(shuffled), 2):
                if i + 1 < len(shuffled):
                    pairs.append((shuffled[i], shuffled[i + 1]))
            
            # Assign pairs to tables (2 pairs per table for 4-player tables)
            for table_num in range(1, self.tables + 1):
                pair_idx = (table_num - 1) * 2
                if pair_idx + 1 < len(pairs):
                    pair1 = pairs[pair_idx]      # First pair at this table
                    pair2 = pairs[pair_idx + 1]  # Second pair at this table
                    
                    # All 4 players at this table
                    table_players = [pair1[0], pair1[1], pair2[0], pair2[1]]
                    
                    # Record for first pair - they are partners
                    for p1, p2 in [pair1, pair2]:
                        # Each player's partner is their pair mate
                        # Their teammates are everyone else at the table
                        teammates = [p for p in table_players if p != p1]
                        self.player_games[p1].append({
                            'game': game_num,
                            'table': table_num,
                            'teammates': teammates,
                            'partner': p2
                        })
                        
                        # And reciprocally for p2
                        teammates = [p for p in table_players if p != p2]
                        self.player_games[p2].append({
                            'game': game_num,
                            'table': table_num,
                            'teammates': teammates,
                            'partner': p1
                        })
        
        return self.player_games
    
    def display_cards(self):
        """Display all player cards to console using compute_player_card."""
        sitting_out = {}  # No one sits out anymore
        for player_num in self.players:
            card = compute_player_card(player_num, self.player_games, sitting_out)
            player_name = self.name_map.get(player_num, f"Player #{player_num}")
            print(f"\n{'='*40}")
            print(f"Card for: {player_name}")
            print(format_player_card_table(card))
    
    def export_csv(self, filename: str = "player_cards.csv"):
        """Export player cards to CSV format."""
        with open(filename, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Player', 'Game', 'Table', 'Teammates'])
            
            for player_num in self.players:
                games = self.player_games.get(player_num, [])
                player_name = self.name_map.get(player_num, str(player_num))
                if games:
                    for game_info in sorted(games, key=lambda x: x['game']):
                        # Convert teammate numbers to names
                        teammate_names = [self.name_map.get(t, str(t)) for t in game_info['teammates']]
                        teammates_str = ', '.join(sorted(teammate_names))
                        writer.writerow([
                            player_name,
                            game_info['game'],
                            game_info['table'],
                            teammates_str
                        ])
                else:
                    writer.writerow([player_name, 'N/A', 'N/A', 'Not assigned'])
        
        print(f"\n✓ Exported to {filename}")
    
    def export_html(self, filename: str = "player_cards.html", cards_per_page: int = 4):
        """Export player cards to HTML format - compact matrix for 8.5x11 printing."""
        # Calculate grid dimensions
        cols = 2 if cards_per_page >= 4 else 1
        rows = (cards_per_page + cols - 1) // cols
        
        html_content = []
        html_content.append("<!DOCTYPE html>")
        html_content.append("<html>")
        html_content.append("<head>")
        html_content.append("<meta charset='UTF-8'>")
        html_content.append("<title>Bridge Player Cards</title>")
        html_content.append("<style>")
        html_content.append(f"""
@page {{
    size: 8.5in 11in;
    margin: 0.5in;
}}
* {{
    box-sizing: border-box;
}}
body {{
    font-family: Arial, sans-serif;
    margin: 0;
    padding: 0;
    background-color: white;
}}
.page {{
    width: 7.5in;  /* 8.5 - 0.5 - 0.5 */
    height: 10in;  /* 11 - 0.5 - 0.5 */
    padding: 0;
    page-break-after: always;
    page-break-inside: avoid;
    display: grid;
    grid-template-columns: repeat({cols}, 1fr);
    grid-template-rows: repeat({rows}, 1fr);
    gap: 0.15in;
}}
.page:last-child {{
    page-break-after: auto;
}}
.card {{
    border: 2px solid #333;
    padding: 0.15in;
    display: flex;
    flex-direction: column;
    overflow: hidden;
    font-size: 10pt;
}}
.card-header {{
    font-size: 14pt;
    font-weight: bold;
    text-align: center;
    margin-bottom: 0.1in;
    border-bottom: 1px solid #333;
    padding-bottom: 0.05in;
}}
.card-subheader {{
    font-size: 11pt;
    font-weight: bold;
    text-align: center;
    margin-bottom: 0.08in;
}}
.card-table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 9pt;
    flex-grow: 1;
}}
.card-table th,
.card-table td {{
    border: 1px solid #666;
    padding: 0.04in 0.06in;
    text-align: center;
}}
.card-table th {{
    background-color: #e0e0e0;
    font-weight: bold;
}}
.card-table tr:nth-child(even) {{
    background-color: #f5f5f5;
}}
.sitting-out {{
    color: #c00;
    font-style: italic;
    font-size: 8pt;
    text-align: center;
    margin-top: 0.05in;
}}
        """)
        html_content.append("</style>")
        html_content.append("</head>")
        html_content.append("<body>")
        
        # Sort players by game 1 table, then by player number
        def sort_key(player_num):
            games = self.player_games.get(player_num, [])
            game1_table = 999
            for game_info in games:
                if game_info['game'] == 1:
                    game1_table = game_info['table']
                    break
            return (game1_table, player_num)
        
        sorted_players = sorted(self.players, key=sort_key)
        
        # Group players into pages
        players_per_page = cards_per_page
        num_pages = (self.num_players + players_per_page - 1) // players_per_page
        
        for page in range(num_pages):
            html_content.append("<div class='page'>")
            start_idx = page * players_per_page
            end_idx = min(start_idx + players_per_page, self.num_players)
            
            page_players = sorted_players[start_idx:end_idx]
            for player_num in page_players:
                games = self.player_games.get(player_num, [])
                
                # Format player name - always show "Player #N" for numbered players
                is_numbered = self.name_map.get(player_num) == str(player_num)
                if is_numbered:
                    player_display = f"Player #{player_num}"
                else:
                    player_display = self.name_map.get(player_num, f"Player #{player_num}")
                
                # Find game 1 table for the subheader
                game1_table = 1
                for game_info in games:
                    if game_info['game'] == 1:
                        game1_table = game_info['table']
                        break
                
                html_content.append("<div class='card'>")
                html_content.append(f"<div class='card-header'>{player_display}</div>")
                html_content.append(f"<div class='card-subheader'>Table {game1_table}</div>")
                
                sitting_out = {}  # No one sits out
                card = compute_player_card(player_num, self.player_games, sitting_out)
                
                if card['games']:
                    html_content.append("<table class='card-table'>")
                    html_content.append("<tr><th>Game</th><th>Table</th><th>Partner</th></tr>")
                    for game in card['games']:
                        partner_num = game['partner']
                        # Format partner name - show "Player #N" for numbered players
                        is_partner_numbered = self.name_map.get(partner_num) == str(partner_num)
                        if is_partner_numbered:
                            partner_display = f"Player #{partner_num}"
                        else:
                            partner_display = self.name_map.get(partner_num, f"Player #{partner_num}") if partner_num else 'N/A'
                        html_content.append(f"<tr><td>{game['game']}</td><td>{game['table']}</td><td>{partner_display}</td></tr>")
                    html_content.append("</table>")
                
                html_content.append("</div>")
            
            # Fill empty slots with blank cards
            for _ in range(players_per_page - (end_idx - start_idx)):
                html_content.append("<div class='card' style='border:none;'></div>")
            
            html_content.append("</div>")
        
        html_content.append("</body>")
        html_content.append("</html>")
        
        with open(filename, 'w') as f:
            f.write('\n'.join(html_content))
        
        print(f"✓ Exported to {filename}")
    
    def display_summary(self):
        """Display a summary of the assignments."""
        print(f"\n{'='*65}")
        print("ASSIGNMENT SUMMARY")
        print(f"{'='*65}")
        print(f"Total Players: {self.num_players} ({self.tables} tables × {self.players_per_table} players)")
        print(f"Number of Games: {self.games}")
        print(f"Tables per Game: {self.tables}")
        print(f"Players per Table: {self.players_per_table}")
        
        print(f"\nGames Assigned per Player:")
        games_distribution = defaultdict(int)
        for player_num in self.players:
            games_count = len(self.player_games.get(player_num, []))
            games_distribution[games_count] += 1
        
        for games_count in sorted(games_distribution.keys()):
            count = games_distribution[games_count]
            print(f"  {games_count} game(s): {count} player(s)")


def main():
    """Main execution."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Generate player cards for bridge game assignments.",
        epilog="Example: python generate_player_cards.py --tables 5 --games 3 --seed 42"
    )
    
    parser.add_argument(
        "-t", "--tables",
        type=int,
        default=5,
        help="Number of tables (default: 5)"
    )
    parser.add_argument(
        "-g", "--games",
        type=int,
        default=3,
        help="Number of games/rounds (default: 3)"
    )
    parser.add_argument(
        "-p", "--players",
        type=str,
        default=None,
        help="Comma-separated list of player names (e.g., 'Alice,Bob,Charlie'). If not provided, uses numbered players."
    )
    parser.add_argument(
        "--players-file",
        type=str,
        default=None,
        help="File containing player names, one per line"
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Random seed for reproducible results (optional)"
    )
    parser.add_argument(
        "--output-csv",
        type=str,
        default="player_cards.csv",
        help="CSV output filename (default: player_cards.csv)"
    )
    parser.add_argument(
        "--output-html",
        type=str,
        default="player_cards.html",
        help="HTML output filename (default: player_cards.html)"
    )
    parser.add_argument(
        "--no-console",
        action="store_true",
        help="Skip console output (only export files)"
    )
    parser.add_argument(
        "--cards-per-page",
        type=int,
        default=4,
        choices=[1, 2, 4, 6, 9],
        help="Number of player cards per printed page (default: 4)"
    )
    
    args = parser.parse_args()
    
    # Load player names if provided
    player_names = None
    if args.players:
        player_names = [p.strip() for p in args.players.split(',')]
    elif args.players_file:
        with open(args.players_file, 'r') as f:
            player_names = [line.strip() for line in f if line.strip()]
    
    # Set seed for reproducibility if provided
    if args.seed is not None:
        random.seed(args.seed)
        print(f"Using random seed: {args.seed}")
    
    # Create generator and generate cards
    generator = PlayerCardGenerator(
        tables=args.tables,
        games=args.games,
        player_names=player_names
    )
    generator.generate_cards()
    
    # Display to console (unless disabled)
    if not args.no_console:
        generator.display_cards()
        generator.display_summary()
    
    # Export to files
    generator.export_csv(args.output_csv)
    generator.export_html(args.output_html, cards_per_page=args.cards_per_page)
    
    print("\n✓ Player card generation complete!")


if __name__ == "__main__":
    main()

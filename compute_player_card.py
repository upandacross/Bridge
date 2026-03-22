#!/usr/bin/env python3
"""
Compute a single player card for bridge game assignments.

This module provides functions to compute a player card for a single player
given the game assignments data.
"""

import random
import re
from typing import Dict, List, Optional, Any


def parse_html_template(template_path: str) -> str:
    """
    Parse an HTML template file and return its content.
    
    Args:
        template_path: Path to the HTML template file
        
    Returns:
        Content of the HTML template as a string
    """
    with open(template_path, 'r', encoding='utf-8') as f:
        return f.read()


def extract_table_structure(html_content: str) -> tuple:
    """
    Extract the table structure from the HTML template.
    
    Args:
        html_content: HTML content as string
        
    Returns:
        Tuple of (table_start, table_end, header_rows, data_row_pattern, total_row, name_row)
    """
    # Find the main table
    table_match = re.search(r'<table[^>]*>(.*?)</table>', html_content, re.DOTALL)
    if not table_match:
        return (None, None, [], None, None, None)
    
    table_content = table_match.group(1)
    
    # Extract table start and end
    table_start = html_content[:table_match.start()]
    table_end = html_content[table_match.end():]
    
    return (table_start, table_end, [], None, None, None)


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
    Format a player card as markdown with card-style styling.
    
    Args:
        card: Player card dictionary from compute_player_card()
    
    Returns:
        Markdown formatted string with card styling
    """
    lines = []
    lines.append("# Player Card")
    lines.append("")
    
    # Table number and Player info header
    lines.append("| | |")
    lines.append("|---|---|")
    lines.append(f"| **Player:** | #${card['player']} |")
    lines.append("")
    
    # Header row
    lines.append("|Round|Table|Partner|Scores|")
    lines.append("|--|--|--|--|")
    
    for i, game in enumerate(card['games'], 1):
        partner_str = str(game['partner']) if game['partner'] else ""
        lines.append(f"|{game['game']}|{game['table']}|{partner_str}| |")
    
    # Total row
    lines.append("|Total:| | | |")
    
    if card['sitting_out']:
        sitting_str = ', '.join(map(str, sorted(card['sitting_out'])))
        lines.append("")
        lines.append(f"*Sitting out: Game {sitting_str}*")
    
    return '\n'.join(lines)


def format_player_card_table(card: Dict) -> str:
    """
    Format a player card as an HTML table with borders (similar to Card.html pattern).
    
    Args:
        card: Player card dictionary from compute_player_card()
    
    Returns:
        HTML formatted string with border styling
    """
    lines = []
    lines.append('<table cellspacing="0" border="1">')
    lines.append('  <colgroup width="60"></colgroup>')
    lines.append('  <colgroup width="60"></colgroup>')
    lines.append('  <colgroup width="70"></colgroup>')
    lines.append('  <colgroup width="180"></colgroup>')
    
    # Header row - Player info section
    player_num = card['player']
    lines.append('  <tr>')
    lines.append('    <td style="border-top: 1px solid #000000; border-bottom: 1px solid #000000; border-left: 1px solid #000000; border-right: 1px solid #000000" colspan="2" height="27" align="right" valign="middle"><b>Player:</b></td>')
    lines.append(f'    <td style="border-top: 1px solid #000000; border-bottom: 1px solid #000000; border-left: 1px solid #000000; border-right: 1px solid #000000" align="center" valign="middle"><b>#{player_num}</b></td>')
    lines.append(f'    <td style="border-top: 1px solid #000000; border-bottom: 1px solid #000000; border-left: 1px solid #000000; border-right: 1px solid #000000" rowspan="2" align="center" valign="top"><b>Name</b></td>')
    lines.append('  </tr>')
    
    # Second header row - Game number placeholder
    lines.append('  <tr>')
    lines.append('    <td style="border-top: 1px solid #000000; border-bottom: 1px solid #000000; border-left: 1px solid #000000; border-right: 1px solid #000000" colspan="2" height="27" align="right" valign="middle"><b>Game:</b></td>')
    lines.append('    <td style="border-top: 1px solid #000000; border-bottom: 1px solid #000000; border-left: 1px solid #000000; border-right: 1px solid #000000" align="center" valign="middle"><b></b></td>')
    lines.append('  </tr>')
    
    # Data header row
    lines.append('  <tr>')
    lines.append('    <td style="border-top: 1px solid #000000; border-bottom: 1px solid #000000; border-left: 1px solid #000000; border-right: 1px solid #000000" height="27" align="center" valign="middle">Round</td>')
    lines.append('    <td style="border-top: 1px solid #000000; border-bottom: 1px solid #000000; border-left: 1px solid #000000; border-right: 1px solid #000000" align="center" valign="middle">Table</td>')
    lines.append('    <td style="border-top: 1px solid #000000; border-bottom: 1px solid #000000; border-left: 1px solid #000000; border-right: 1px solid #000000" align="center" valign="middle">Partner</td>')
    lines.append('    <td style="border-top: 1px solid #000000; border-bottom: 1px solid #000000; border-left: 1px solid #000000; border-right: 1px solid #000000" align="center" valign="middle"><b>Scores</b></td>')
    lines.append('  </tr>')
    
    # Data rows for each game
    for game in card['games']:
        partner_str = str(game['partner']) if game['partner'] else ""
        lines.append('  <tr>')
        lines.append(f'    <td style="border-top: 1px solid #000000; border-bottom: 1px solid #000000; border-left: 1px solid #000000; border-right: 1px solid #000000" height="27" align="center" valign="middle"><b>{game["game"]}</b></td>')
        lines.append(f'    <td style="border-top: 1px solid #000000; border-bottom: 1px solid #000000; border-left: 1px solid #000000; border-right: 1px solid #000000" align="center" valign="middle"><b>{game["table"]}</b></td>')
        lines.append(f'    <td style="border-top: 1px solid #000000; border-bottom: 1px solid #000000; border-left: 1px solid #000000; border-right: 1px solid #000000" align="center" valign="middle"><b>{partner_str}</b></td>')
        lines.append('    <td style="border-top: 1px solid #000000; border-bottom: 1px solid #000000; border-left: 1px solid #000000; border-right: 1px solid #000000" align="left" valign="middle"><b></b></td>')
        lines.append('  </tr>')
    
    # Total row
    lines.append('  <tr>')
    lines.append('    <td style="border-top: 1px solid #000000; border-bottom: 1px solid #000000; border-left: 1px solid #000000; border-right: 1px solid #000000" colspan="3" height="27" align="right" valign="middle"><b>Total:</b></td>')
    lines.append('    <td style="border-top: 1px solid #000000; border-bottom: 1px solid #000000; border-left: 1px solid #000000; border-right: 1px solid #000000" align="left" valign="middle"><b></b></td>')
    lines.append('  </tr>')
    
    lines.append('</table>')
    
    return '\n'.join(lines)


def format_player_card_from_template(card: Dict, template_path: str = "PlayerCardTemplate.html", player_name: str = "", num_players: int = None) -> str:
    """
    Format a player card using the PlayerCardTemplate.html as a base.
    
    This function parses the HTML template and replaces placeholder cells
    with the actual player data.
    
    Args:
        card: Player card dictionary from compute_player_card()
        template_path: Path to the HTML template file
        player_name: Optional name to display in the player card
        num_players: Total number of players in the game (for sequential N field)
        
    Returns:
        HTML formatted string with the player's data filled into the template
    """
    template_content = parse_html_template(template_path)
    
    # Find and parse the table
    table_match = re.search(r'<table[^>]*>(.*?)</table>', template_content, re.DOTALL)
    if not table_match:
        # If no table found, return the template with name inserted
        if player_name:
            return template_content.replace('<p>Player</p>', f'<p>Player: {player_name}</p>')
        return template_content
    
    table_start = table_match.start()
    table_end = table_match.end()
    
    # Extract rows from the table
    table_content = table_match.group(1)
    
    # Find all row patterns with their positions
    tr_pattern = r'(<tr[^>]*>)(.*?)(</tr>)'
    all_rows = re.findall(tr_pattern, table_content, re.DOTALL)
    
    # Player number for the 'N' field (which displays the actual player number)
    player_num = card.get('player', 0)
    
    # Get header rows from template (keep first 2 rows: Player header and Round/Table/Partner header)
    # Row 1: Header with "Player" and "N" - replace "N" with player number
    # Row 2: Header with "Round", "Table", "Partner", "Score"
    
    # Build the first header row with actual player number in the N field
    # Need to replace the "N" placeholder in the template's first row
    # The template's first row has <p>N</p> that we need to replace with the player number
    
    # Get the first row from template (Player header with N placeholder)
    if len(all_rows) >= 1:
        # Replace the <p>N</p> in the first row with the actual player number
        first_row_original = all_rows[0][0] + all_rows[0][1] + all_rows[0][2]
        # Replace <p>N</p> with the player number
        header_row1 = first_row_original.replace('<p>N</p>', f'<p>{player_num}</p>')
    else:
        header_row1 = build_header_row(player_num)
    
    # Get the second row from template (Round/Table/Partner header)
    if len(all_rows) >= 2:
        second_row_original = all_rows[1][0] + all_rows[1][1] + all_rows[1][2]
    else:
        second_row_original = ''
    
    # Build the data rows with actual game information
    data_rows_html = []
    for i, game in enumerate(card['games']):
        game_num = game['game']
        table_num = game['table']
        partner = game['partner'] if game['partner'] else ''
        
        data_row = build_data_row(i + 1, game_num, table_num, partner, player_num)
        data_rows_html.append(data_row)
    
    # Get the Total row from template (it's after the empty data rows in the template)
    # The template has 8 empty rows followed by a Total row
    total_row_original = None
    if len(all_rows) >= 11:
        # The Total row should be around index 10 (0-indexed, after 8 empty rows)
        # Row 0: Player header, Row 1: Round/Table/Partner header, Rows 2-9: empty, Row 10: Total
        total_row_original = all_rows[10][0] + all_rows[10][1] + all_rows[10][2]
    
    # Get the Name row from template
    name_row_original = None
    if len(all_rows) >= 12:
        name_row_original = all_rows[11][0] + all_rows[11][1] + all_rows[11][2]
    
    # Get empty data rows from template (rows 3-10 in original template)
    # These are the blank rows that we need to keep for structure
    empty_rows_html = []
    for i in range(2, min(10, len(all_rows))):
        # Check if this row has the correct class
        row_content = all_rows[i][0] + all_rows[i][1] + all_rows[i][2]
        if 'class="row-ro1"' in row_content:
            empty_rows_html.append(row_content)
        elif i < 10:  # If we don't have enough, add blank rows
            empty_rows_html.append('<tr class="row-ro1"><td style="text-align:left;width:0.889in; " class="cell-ce2"> </td><td style="text-align:left;width:0.889in; " class="cell-ce2"> </td><td style="text-align:left;width:0.889in; " class="cell-ce2"> </td><td style="text-align:left;width:0.25in; " class="cell-ce8"> </td><td style="text-align:left;width:0.25in; " class="cell-ce8"> </td><td style="text-align:left;width:0.25in; " class="cell-ce8"> </td><td style="text-align:left;width:0.25in; " class="cell-ce8"> </td><td style="text-align:left;width:0.25in; " class="cell-ce8"> </td><td style="text-align:left;width:0.25in; " class="cell-ce2"> </td><td style="text-align:left;width:0.889in; " class="cell-ce3"> </td></tr>')
    
    # Combine everything - keep template structure but replace header row 1
    new_table_content = header_row1 + '\n' + second_row_original + '\n'
    
    # Add game data rows
    for data_row in data_rows_html:
        new_table_content += data_row + '\n'
    
    # Add remaining empty rows (to fill the 8 data slots in the template)
    for empty_row in empty_rows_html[len(data_rows_html):]:
        new_table_content += empty_row + '\n'
    
    # Add only Name row (Total row is already in template after empty rows)
    if name_row_original:
        # Replace the "Name:" with "Name: X" where X is the player name or number
        if player_name:
            name_row = name_row_original.replace('<p>Name:</p>', f'<p>Name: {player_name}</p>')
        else:
            name_row = name_row_original.replace('<p>Name:</p>', f'<p>Name: {player_num}</p>')
    else:
        name_row = build_name_row(player_name)
    
    new_table_content += name_row + '\n'
    
    # Extract the original table opening tag
    original_table_start = template_content[table_start:table_match.end()]
    opening_end = original_table_start.find('>') + 1
    table_opening = original_table_start[:opening_end]
    
    # Replace the table with the new content
    new_table_html = f"{table_opening}{new_table_content}</table>"
    
    return template_content[:table_start] + new_table_html + template_content[table_end:]


def build_data_row(index: int, game_num: int, table_num: int, partner: str, player_num: int = None) -> str:
    """
    Build a data row for a game in the player card.
    
    Args:
        index: Row index
        game_num: Game number
        table_num: Table number
        partner: Partner number/name
        player_num: Player number for the 'N' field
        
    Returns:
        HTML string for the data row
    """
    # Based on the template structure, we need to match the cell classes
    # The template has 10 columns:
    # col1 (0.889in): blank
    # col2 (0.889in): blank  
    # col3 (0.889in): Round/Table/Partner data
    # col4-col8 (0.25in each): 5 score boxes per round
    # col9 (0.25in): blank
    # col10 (0.889in): blank
    #
    # Row structure from template:
    # Row 1: [ce1] [ce4] [ce4]Player [ce4]N [ce4] [ce4] [ce4] [ce9] [ce3]
    # Row 2: [ce2]Round [ce2]Table [ce2]Partner [ce1] [ce4] [ce7]Score [ce4] [ce4] [ce9] [ce3]
    # Data rows: [ce2] [ce2] [ce2] [ce2] [ce2] [ce8]Score [ce2] [ce2] [ce2] [ce3]
    partner_str = str(partner) if partner else ""
    player_str = str(player_num) if player_num is not None else ""
    
    # Data rows: Round, Table, Partner, and 5 score cells (0.25in each) with borders
    # cell-ce2 has all borders (border-bottom, border-left, border-right, border-top)
    # cell-ce8 is for the Score column header with borders and center alignment
    return f'''<tr class="row-ro1">
<td style="text-align:left;width:0.889in; " class="cell-ce2">
<p>{game_num}</p>
</td>
<td style="text-align:left;width:0.889in; " class="cell-ce2">
<p>{table_num}</p>
</td>
<td style="text-align:left;width:0.889in; " class="cell-ce2">
<p>{partner_str}</p>
</td>
<td style="text-align:left;width:0.25in; " class="cell-ce8"> </td>
<td style="text-align:left;width:0.25in; " class="cell-ce8"> </td>
<td style="text-align:left;width:0.25in; " class="cell-ce8"> </td>
<td style="text-align:left;width:0.25in; " class="cell-ce8"> </td>
<td style="text-align:left;width:0.25in; " class="cell-ce8"> </td>
<td style="text-align:left;width:0.25in; " class="cell-ce2"> </td>
<td style="text-align:left;width:0.889in; " class="cell-ce3"> </td>
</tr>'''


def build_header_row(player_num: int) -> str:
    """
    Build the header row (first row) that contains the Player and N (player number) fields.
    
    Args:
        player_num: Player number for the 'N' field
        
    Returns:
        HTML string for the header row
    """
    player_str = str(player_num) if player_num is not None else ""
    
    return f'''<tr class="row-ro1">
<td style="text-align:left;width:0.889in; " class="cell-ce1"> </td>
<td style="text-align:left;width:0.889in; " class="cell-ce4"> </td>
<td style="text-align:left;width:0.889in; " class="cell-ce4">
<p>Player</p>
</td>
<td style="text-align:left;width:0.25in; " class="cell-ce4">
<p>{player_str}</p>
</td>
<td style="text-align:left;width:0.25in; " class="cell-ce4"> </td>
<td style="text-align:left;width:0.25in; " class="cell-ce4"> </td>
<td style="text-align:left;width:0.25in; " class="cell-ce4"> </td>
<td style="text-align:left;width:0.25in; " class="cell-ce4"> </td>
<td style="text-align:left;width:0.25in; " class="cell-ce9"> </td>
<td style="text-align:left;width:0.889in; " class="cell-ce3"> </td>
</tr>'''


def build_total_row(num_games: int) -> str:
    """
    Build the Total row for the player card.
    
    Args:
        num_games: Number of games played
        
    Returns:
        HTML string for the Total row
    """
    return f'''<tr class="row-ro1">
<td style="text-align:left;width:0.889in; " class="cell-ce1"> </td>
<td style="text-align:left;width:0.889in; " class="cell-ce4"> </td>
<td style="text-align:left;width:0.889in; " class="cell-ce5">
<p>Total:</p>
</td>
<td style="text-align:left;width:0.25in; " class="cell-ce2"> </td>
<td style="text-align:left;width:0.25in; " class="cell-ce2"> </td>
<td style="text-align:left;width:0.25in; " class="cell-ce2"> </td>
<td style="text-align:left;width:0.25in; " class="cell-ce2"> </td>
<td style="text-align:left;width:0.25in; " class="cell-ce2"> </td>
<td style="text-align:left;width:0.25in; " class="cell-ce2"> </td>
<td style="text-align:left;width:0.889in; " class="cell-ce3"> </td>
</tr>'''


def build_name_row(player_name: str) -> str:
    """
    Build the Name row for the player card.
    
    Args:
        player_name: Player's name to display
        
    Returns:
        HTML string for the Name row
    """
    name_display = player_name if player_name else ""
    return f'''<tr class="row-ro2">
<td style="text-align:left;width:0.889in; " class="cell-ce1"> </td>
<td style="text-align:left;width:0.889in; " class="cell-ce4"> </td>
<td style="text-align:left;width:0.889in; " class="cell-ce6">
<p>Name: {name_display}</p>
</td>
<td style="text-align:left;width:0.25in; " class="cell-ce1"> </td>
<td style="text-align:left;width:0.25in; " class="cell-ce4"> </td>
<td style="text-align:left;width:0.25in; " class="cell-ce4"> </td>
<td style="text-align:left;width:0.25in; " class="cell-ce4"> </td>
<td style="text-align:left;width:0.25in; " class="cell-ce4"> </td>
<td style="text-align:left;width:0.25in; " class="cell-ce9"> </td>
<td style="text-align:left;width:0.889in; " class="cell-ce3"> </td>
</tr>'''


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
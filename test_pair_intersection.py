#!/usr/bin/env python3
"""
Test script to verify pair intersection checking functionality.
"""

import sys
import os

# Add the current directory to Python path so we can import generate_player_cards
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from generate_player_cards import PlayerCardGenerator

def test_pair_intersection():
    """Test that pairs from previous games are not repeated in subsequent games."""
    
    print("Testing pair intersection checking...")
    
    # Create a generator with 2 tables and 3 games
    generator = PlayerCardGenerator(tables=2, games=3, player_names=['Alice', 'Bob', 'Charlie', 'David', 'Eve', 'Frank', 'Grace', 'Henry'])
    
    # Generate cards
    result = generator.generate_cards()
    
    print("Generated cards successfully!")
    
    # Check that no pairs from game 1 appear in game 2
    game1_pairs = set()
    game2_pairs = set()
    
    # Extract pairs from game 1
    for player_num, games in result.items():
        for game_info in games:
            if game_info['game'] == 1:
                partner = game_info['partner']
                pair = tuple(sorted((player_num, partner)))
                game1_pairs.add(pair)
    
    # Extract pairs from game 2  
    for player_num, games in result.items():
        for game_info in games:
            if game_info['game'] == 2:
                partner = game_info['partner']
                pair = tuple(sorted((player_num, partner)))
                game2_pairs.add(pair)
    
    print(f"Game 1 pairs: {sorted(game1_pairs)}")
    print(f"Game 2 pairs: {sorted(game2_pairs)}")
    
    # Check for intersection
    intersection = game1_pairs.intersection(game2_pairs)
    if intersection:
        print(f"ERROR: Found intersection between games 1 and 2:")
        print(f"  Intersection pairs: {sorted(intersection)}")
        return False
    else:
        print("SUCCESS: No intersection found between games 1 and 2")
    
    # Check that no pairs from game 1 appear in game 3
    game3_pairs = set()
    
    # Extract pairs from game 3  
    for player_num, games in result.items():
        for game_info in games:
            if game_info['game'] == 3:
                partner = game_info['partner']
                pair = tuple(sorted((player_num, partner)))
                game3_pairs.add(pair)
    
    print(f"Game 3 pairs: {sorted(game3_pairs)}")
    
    # Check for intersection with game 1
    intersection_1_3 = game1_pairs.intersection(game3_pairs)
    if intersection_1_3:
        print(f"ERROR: Found intersection between games 1 and 3:")
        print(f"  Intersection pairs: {sorted(intersection_1_3)}")
        return False
    else:
        print("SUCCESS: No intersection found between games 1 and 3")
    
    # Check for intersection with game 2  
    intersection_2_3 = game2_pairs.intersection(game3_pairs)
    if intersection_2_3:
        print(f"ERROR: Found intersection between games 2 and 3:")
        print(f"  Intersection pairs: {sorted(intersection_2_3)}")
        return False
    else:
        print("SUCCESS: No intersection found between games 2 and 3")
    
    print("\nAll tests passed! No pair intersections found.")
    return True

if __name__ == "__main__":
    success = test_pair_intersection()
    sys.exit(0 if success else 1)
#!/usr/bin/env python3
"""
Script de test pour le système d'apprentissage de l'IA d'échecs.
Ce script fait jouer plusieurs parties automatiques pour tester l'apprentissage.
"""

from chess import Board, WHITE, BLACK
from ia_tree import TreeIA
import time

def test_learning_system():
    """Test le système d'apprentissage avec plusieurs parties."""
    print("=== Test du système d'apprentissage ===")
    
    # Créer deux IAs avec apprentissage activé
    ia_white = TreeIA(depth=3, enable_learning=True)
    ia_black = TreeIA(depth=3, enable_learning=True)
    
    games_to_play = 50
    print(f"Lancement de {games_to_play} parties automatiques...")
    
    for game_num in range(games_to_play):
        print(f"\n--- Partie {game_num + 1} ---")
        board = Board()
        move_count = 0
        max_moves = 200  # Limite pour éviter les boucles infinies
        
        while not board.is_game_over() and move_count < max_moves:
            move_count += 1
            
            try:
                if board.turn == WHITE:
                    # Tour des blancs
                    move_str = ia_white.coup(board)
                    board.push_san(move_str)
                else:
                    # Tour des noirs
                    move_str = ia_black.coup(board)
                    board.push_san(move_str)
                    
            except Exception as e:
                print(f"Erreur lors du coup: {e}")
                break
        
        # Résultat de la partie
        result = board.result()
        print(f"Résultat: {result} ({move_count} coups)")
        
        # Notifier les IAs de la fin de partie
        ia_white.end_game(result, board)
        ia_black.end_game(result, board)
        
        # Afficher les statistiques d'apprentissage
        stats_white = ia_white.get_learning_stats()
        stats_black = ia_black.get_learning_stats()
        
        if stats_white:
            print(f"IA Blanche - Parties: {stats_white['games_played']}, "
                  f"Positions apprises: {stats_white['positions_learned']}, "
                  f"Taux exploration: {stats_white['exploration_rate']:.3f}")
        
        if stats_black:
            print(f"IA Noire - Parties: {stats_black['games_played']}, "
                  f"Positions apprises: {stats_black['positions_learned']}, "
                  f"Taux exploration: {stats_black['exploration_rate']:.3f}")
    
    print("\n=== Test terminé ===")
    print("Les données d'apprentissage ont été sauvegardées dans 'ia_learning_data.json'")
    print("L'IA est maintenant plus expérimentée et utilisera ses connaissances lors des prochaines parties.")

if __name__ == "__main__":
    test_learning_system()

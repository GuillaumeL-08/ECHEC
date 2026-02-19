#!/usr/bin/env python3
"""
test_simple_ia.py - Test de l'IA simplifiée

Ce script teste les fonctionnalités de base de SimpleIA :
- Évaluation de positions
- Choix de coups
- Apprentissage par renforcement
"""

import chess
from simple_ia import SimpleIA


def test_evaluation():
    """Test de l'évaluation de positions."""
    print("=== Test Évaluation ===")
    
    ia = SimpleIA()
    board = chess.Board()
    
    # Position initiale
    score_initial = ia.evaluate_position(board)
    print(f"Score position initiale: {score_initial}")
    
    # Après 1.e4
    board.push_san("e4")
    score_e4 = ia.evaluate_position(board)
    print(f"Score après 1.e4: {score_e4}")
    
    # Après 1...e5
    board.push_san("e5")
    score_e5 = ia.evaluate_position(board)
    print(f"Score après 1...e5: {score_e5}")
    
    print()


def test_move_selection():
    """Test de la sélection de coups."""
    print("=== Test Sélection de Coups ===")
    
    ia = SimpleIA(epsilon=0.0)  # Pas d'exploration pour le test
    board = chess.Board()
    
    print("Coups possibles depuis la position initiale:")
    for move in board.legal_moves:
        print(f"  {board.san(move)}")
    
    # Choisir un coup
    best_move = ia.choose_move(board)
    print(f"Meilleur coup choisi: {board.san(best_move)}")
    print()


def test_learning():
    """Test de l'apprentissage."""
    print("=== Test Apprentissage ===")
    
    ia = SimpleIA(epsilon=0.5)  # Exploration élevée
    board = chess.Board()
    
    # Simuler une partie courte
    ia.start_new_game()
    
    moves = ["e4", "e5", "Nf3", "Nc6", "Bb5", "a6", "Ba4", "Nf6", "O-O", "Be7"]
    
    for i, san in enumerate(moves):
        if board.is_game_over():
            break
        move = board.push_san(san)
        print(f"Coup {i+1}: {san}")
    
    # Terminer la partie (nulle pour le test)
    ia.end_game("1/2-1/2", board)
    
    stats = ia.get_stats()
    print(f"Stats après la partie: {stats}")
    print()


def test_multiple_games():
    """Test sur plusieurs parties."""
    print("=== Test Parties Multiples ===")
    
    ia = SimpleIA(epsilon=0.3)
    
    for game_num in range(3):
        print(f"Partie {game_num + 1}:")
        ia.start_new_game()
        board = chess.Board()
        
        # Jouer quelques coups aléatoires
        for _ in range(10):
            if board.is_game_over():
                break
            move = ia.choose_move(board)
            if move:
                board.push(move)
        
        # Résultat aléatoire pour le test
        results = ["1-0", "0-1", "1/2-1/2"]
        result = results[game_num % 3]
        ia.end_game(result, board)
        
        stats = ia.get_stats()
        print(f"  Résultat: {result}, Total parties: {stats['games_played']}")
    
    stats_final = ia.get_stats()
    print(f"Stats finales: {stats_final}")
    print()


def main():
    """Fonction principale de test."""
    print("Test de SimpleIA - IA d'échecs simplifiée")
    print("=" * 50)
    
    test_evaluation()
    test_move_selection()
    test_learning()
    test_multiple_games()
    
    print("Tests terminés avec succès!")


if __name__ == "__main__":
    main()

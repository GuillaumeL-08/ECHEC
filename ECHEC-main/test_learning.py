#!/usr/bin/env python3
"""
test_learning.py — Script d'entraînement optimisé pour 10h.
Lance des parties IA vs IA en boucle avec stats de progression.
"""

from chess import Board, WHITE, BLACK
from ia_tree import TreeIA
import time
import signal
import sys

# Durée d'entraînement cible (secondes). Mettre 36000 pour 10h.
TRAINING_DURATION = 36000
# Profondeur de recherche pendant l'entraînement (3 = bon compromis vitesse/qualité)
TRAIN_DEPTH = 3
# Limite de temps par coup pendant l'entraînement (secondes)
TIME_PER_MOVE = 1.0
# Nombre max de coups par partie (évite les boucles infinies)
MAX_MOVES = 150

ia_white = None
ia_black = None

def signal_handler(sig, frame):
    """Sauvegarde propre en cas d'interruption Ctrl+C."""
    print("\n\n=== Interruption détectée — sauvegarde en cours... ===")
    if ia_white and ia_white.learning_manager:
        ia_white.learning_manager.force_save()
    if ia_black and ia_black.learning_manager:
        ia_black.learning_manager.force_save()
    print("Sauvegarde terminée.")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)


def print_stats(ia_w, ia_b, game_num, elapsed, total_duration):
    stats_w = ia_w.get_learning_stats()
    stats_b = ia_b.get_learning_stats()
    pct = elapsed / total_duration * 100
    remaining = total_duration - elapsed
    h, m = divmod(int(remaining), 3600)
    m, s = divmod(m, 60)

    print(f"\n{'='*60}")
    print(f"  Partie {game_num:4d} | {pct:.1f}% | Temps restant: {h:02d}h{m:02d}m{s:02d}s")
    print(f"  Blancs — W:{stats_w['wins']:4d} D:{stats_w['draws']:4d} L:{stats_w['losses']:4d} "
          f"| Positions: {stats_w['positions_learned']:6d} | ε={stats_w['exploration_rate']:.3f}")
    print(f"  Noirs  — W:{stats_b['wins']:4d} D:{stats_b['draws']:4d} L:{stats_b['losses']:4d} "
          f"| Positions: {stats_b['positions_learned']:6d} | ε={stats_b['exploration_rate']:.3f}")
    print(f"{'='*60}")


def train():
    global ia_white, ia_black

    print("=== Démarrage de l'entraînement ===")
    print(f"Durée prévue : {TRAINING_DURATION // 3600}h, profondeur={TRAIN_DEPTH}, "
          f"temps/coup={TIME_PER_MOVE}s\n")

    # Deux IAs avec des fichiers de données séparés
    ia_white = TreeIA(depth=TRAIN_DEPTH, enable_learning=True, time_limit=TIME_PER_MOVE)
    ia_black = TreeIA(depth=TRAIN_DEPTH, enable_learning=True, time_limit=TIME_PER_MOVE)

    # Utiliser des fichiers de données différents pour chaque couleur
    if ia_white.learning_manager:
        ia_white.learning_manager.data_file = "ia_white_data.json.gz"
        ia_white.learning_manager._load()
    if ia_black.learning_manager:
        ia_black.learning_manager.data_file = "ia_black_data.json.gz"
        ia_black.learning_manager._load()

    start_time = time.time()
    game_num = 0

    while True:
        elapsed = time.time() - start_time
        if elapsed >= TRAINING_DURATION:
            break

        game_num += 1
        board = Board()
        move_count = 0

        while not board.is_game_over() and move_count < MAX_MOVES:
            move_count += 1
            try:
                if board.turn == WHITE:
                    move_san = ia_white.coup(board)
                else:
                    move_san = ia_black.coup(board)
                board.push_san(move_san)
            except Exception as e:
                print(f"[Erreur coup partie {game_num}]: {e}")
                break

        result = board.result()

        ia_white.end_game(result, board)
        ia_black.end_game(result, board)

        # Afficher les stats toutes les 10 parties
        if game_num % 10 == 0:
            print_stats(ia_white, ia_black, game_num, elapsed, TRAINING_DURATION)

    # Sauvegarde finale
    print(f"\n=== Entraînement terminé ({game_num} parties) ===")
    if ia_white.learning_manager:
        ia_white.learning_manager.force_save()
    if ia_black.learning_manager:
        ia_black.learning_manager.force_save()
    print("Données sauvegardées.")

if __name__ == "__main__":
    train()
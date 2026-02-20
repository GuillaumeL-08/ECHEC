from chess import Board, WHITE, BLACK
from ia_tree import TreeIA
import time
import signal
import sys

TRAINING_DURATION = 36000 
TRAIN_DEPTH = 4
TIME_PER_MOVE = 1.0
MAX_MOVES = 200

ia_white = None
ia_black = None

def signal_handler(sig, frame):
    """Gère l'interruption du programme pour sauvegarder les données d'apprentissage avant de quitter."""
    print("\n\n=== Interruption détectée — sauvegarde en cours... ===")
    if ia_white and ia_white.learning_manager:
        ia_white.learning_manager.force_save()
    if ia_black and ia_black.learning_manager:
        ia_black.learning_manager.force_save()
    print("Sauvegarde terminée.")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)


def print_stats(ia_w, ia_b, game_num, elapsed, total_duration, results_log):
    """Affiche les statistiques d'entraînement après un certain nombre de parties, y compris les résultats réels et les performances des IA."""
    stats_w = ia_w.get_learning_stats()
    stats_b = ia_b.get_learning_stats()
    pct = elapsed / total_duration * 100
    remaining = total_duration - elapsed
    h, m = divmod(int(remaining), 3600)
    m, s = divmod(m, 60)

    white_wins  = results_log.count("1-0")
    black_wins  = results_log.count("0-1")
    draws       = results_log.count("1/2-1/2")
    interrupted = results_log.count("*")
    total       = len(results_log)

    print(f"\n{'='*65}")
    print(f"  Partie {game_num:4d} | {pct:.1f}% | Temps restant: {h:02d}h{m:02d}m{s:02d}s")
    print(f"  Résultats réels  — Blanc: {white_wins:4d}  Noir: {black_wins:4d}  "
          f"Nulles: {draws:4d}  Interrompues: {interrupted:3d} / {total}")
    print(f"  Blancs (IA) — W:{stats_w['wins']:4d} D:{stats_w['draws']:4d} L:{stats_w['losses']:4d} "
          f"| Positions: {stats_w['positions_learned']:6d} | ε={stats_w['exploration_rate']:.3f}")
    print(f"  Noirs  (IA) — W:{stats_b['wins']:4d} D:{stats_b['draws']:4d} L:{stats_b['losses']:4d} "
          f"| Positions: {stats_b['positions_learned']:6d} | ε={stats_b['exploration_rate']:.3f}")
    print(f"{'='*65}")


def train():
    """Entraîne deux IA l'une contre l'autre pendant une durée définie, en jouant des parties complètes et en sauvegardant les données d'apprentissage à la fin ou en cas d'interruption."""
    global ia_white, ia_black

    print("=== Démarrage de l'entraînement ===")
    print(f"Durée prévue : {TRAINING_DURATION // 3600}h, profondeur={TRAIN_DEPTH}, "
          f"temps/coup={TIME_PER_MOVE}s, max_coups/partie={MAX_MOVES}\n")

    ia_white = TreeIA(depth=TRAIN_DEPTH, enable_learning=True, time_limit=TIME_PER_MOVE)
    ia_black = TreeIA(depth=TRAIN_DEPTH, enable_learning=True, time_limit=TIME_PER_MOVE)

    if ia_white.learning_manager:
        ia_white.learning_manager.data_file = "ia_white_data.json.gz"
        ia_white.learning_manager._load()
    if ia_black.learning_manager:
        ia_black.learning_manager.data_file = "ia_black_data.json.gz"
        ia_black.learning_manager._load()

    start_time = time.time()
    game_num = 0
    results_log = []

    while True:
        elapsed = time.time() - start_time
        if elapsed >= TRAINING_DURATION:
            break

        game_num += 1
        board = Board()
        move_count = 0

        shallow_game = (game_num % 5 == 0)
        if shallow_game:
            ia_white.depth = 1
            ia_black.depth = 1
        else:
            ia_white.depth = TRAIN_DEPTH
            ia_black.depth = TRAIN_DEPTH

        while not board.is_game_over() and move_count < MAX_MOVES:
            move_count += 1
            try:
                if board.turn == WHITE:
                    move_san = ia_white.coup(board)
                else:
                    move_san = ia_black.coup(board)
                board.push_san(move_san)
            except Exception as e:
                print(f"[Erreur coup partie {game_num}, coup {move_count}]: {e}")
                break

        result = board.result()
        results_log.append(result)

        ia_white.end_game(result, board, color=WHITE)
        ia_black.end_game(result, board, color=BLACK)

        if game_num % 10 == 0:
            print_stats(ia_white, ia_black, game_num, elapsed, TRAINING_DURATION, results_log)

    print(f"\n=== Entraînement terminé ({game_num} parties) ===")
    if ia_white.learning_manager:
        ia_white.learning_manager.force_save()
    if ia_black.learning_manager:
        ia_black.learning_manager.force_save()
    print("Données sauvegardées.")

if __name__ == "__main__":
    train()

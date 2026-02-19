"""
simple_ia.py — IA d'échecs simplifiée utilisant Q-learning.

Architecture minimaliste :
- Évaluation de position basique (matériel + position)
- Q-learning avec table de valeurs
- Sépsilon-greedy pour exploration/exploitation
- Apprentissage par renforcement simple
"""

import random
import json
import os
import chess
from chess import PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING, WHITE, BLACK


class SimpleIA:
    """IA d'échecs simple avec Q-learning."""
    
    # Valeurs des pièces
    PIECE_VALUES = {
        PAWN: 100, KNIGHT: 300, BISHOP: 320, 
        ROOK: 500, QUEEN: 900, KING: 20000
    }
    
    # Bonus positionnels simples (centrage, avancement)
    POSITION_BONUS = {
        PAWN: [0, 0, 0, 0, 10, 20, 30, 40],  # avancement
        KNIGHT: [-20, -10, 0, 10, 10, 0, -10, -20],  # centre
        BISHOP: [-10, -5, 0, 5, 5, 0, -5, -10],  # centre
        ROOK: [0, 0, 0, 5, 5, 0, 0, 0],  # colonnes centrales
        QUEEN: [-10, -5, 0, 0, 0, 0, -5, -10],  # arrière au début
        KING: [-30, -20, -10, 0, 0, -10, -20, -30]  # sécurité
    }
    
    def __init__(self, epsilon=0.3, learning_rate=0.1, gamma=0.9):
        self.epsilon = epsilon  # taux d'exploration
        self.learning_rate = learning_rate
        self.gamma = gamma
        self.q_table = {}  # position_hash -> valeur
        self.game_history = []  # historique de la partie en cours
        self.data_file = "simple_ia_learning.json"
        
        # Statistiques
        self.games_played = 0
        self.wins = 0
        self.draws = 0
        self.losses = 0
        
        self._load_learning_data()
    
    def _get_position_hash(self, board):
        """Hash simple pour identifier une position."""
        return board.fen()
    
    def _evaluate_material(self, board):
        """Évaluation matérielle simple."""
        score = 0
        for piece_type, value in self.PIECE_VALUES.items():
            white_pieces = len(board.pieces(piece_type, WHITE))
            black_pieces = len(board.pieces(piece_type, BLACK))
            score += value * (white_pieces - black_pieces)
        return score
    
    def _evaluate_position_bonus(self, board):
        """Bonus positionnels simples."""
        score = 0
        
        # Bonus pour chaque pièce selon sa position
        for piece_type in [PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING]:
            # Pièces blanches
            for square in board.pieces(piece_type, WHITE):
                rank = square // 8  # 0-7 (bas vers haut)
                file = square % 8   # 0-7 (gauche vers droite)
                
                # Bonus de rangée
                if piece_type in self.POSITION_BONUS:
                    score += self.POSITION_BONUS[piece_type][rank]
                
                # Bonus de centralité (colonnes d et e)
                if file in [3, 4] and piece_type in [KNIGHT, BISHOP, QUEEN]:
                    score += 10
            
            # Pièces noires (inversé)
            for square in board.pieces(piece_type, BLACK):
                rank = 7 - (square // 8)  # inversé pour les noirs
                file = square % 8
                
                if piece_type in self.POSITION_BONUS:
                    score -= self.POSITION_BONUS[piece_type][rank]
                
                if file in [3, 4] and piece_type in [KNIGHT, BISHOP, QUEEN]:
                    score -= 10
        
        # Bonus pour le roque
        if board.has_castling_rights(WHITE):
            score += 20
        if board.has_castling_rights(BLACK):
            score -= 20
            
        # Pénalité pour les pièces clouées ou attaquées
        for square in board.pieces(KING, WHITE):
            if board.is_attacked_by(BLACK, square):
                score -= 50
        for square in board.pieces(KING, BLACK):
            if board.is_attacked_by(WHITE, square):
                score += 50
        
        return score
    
    def evaluate_position(self, board):
        """Évaluation complète d'une position."""
        if board.is_checkmate():
            return -100000 if board.turn == WHITE else 100000
        if board.is_stalemate() or board.is_insufficient_material():
            return 0
        
        material_score = self._evaluate_material(board)
        position_score = self._evaluate_position_bonus(board)
        
        total_score = material_score + position_score
        
        # Ajouter la valeur apprise si disponible
        pos_hash = self._get_position_hash(board)
        if pos_hash in self.q_table:
            learned_value = self.q_table[pos_hash]
            # Pondérer la valeur apprise (plus de poids avec l'expérience)
            weight = min(0.3, self.games_played * 0.01)
            total_score = total_score * (1 - weight) + learned_value * weight
        
        return total_score
    
    def _get_move_scores(self, board):
        """Calcule les scores pour tous les coups légaux."""
        move_scores = []
        
        for move in board.legal_moves:
            # Simuler le coup
            board.push(move)
            score = self.evaluate_position(board)
            board.pop()
            
            # Négamax : inverser le score si c'est au tour des noirs
            if board.turn == BLACK:
                score = -score
                
            move_scores.append((move, score))
        
        return move_scores
    
    def choose_move(self, board):
        """Choisit un coup avec epsilon-greedy."""
        legal_moves = list(board.legal_moves)
        if not legal_moves:
            return None
        
        # Exploration : coup aléatoire
        if random.random() < self.epsilon:
            move = random.choice(legal_moves)
            # Enregistrer pour l'apprentissage
            pos_hash = self._get_position_hash(board)
            self.game_history.append((pos_hash, move, None))  # score sera mis à jour plus tard
            return move
        
        # Exploitation : meilleur coup selon l'évaluation
        move_scores = self._get_move_scores(board)
        move_scores.sort(key=lambda x: x[1], reverse=True)
        
        best_move = move_scores[0][0]
        best_score = move_scores[0][1]
        
        # Enregistrer pour l'apprentissage
        pos_hash = self._get_position_hash(board)
        self.game_history.append((pos_hash, best_move, best_score))
        
        return best_move
    
    def start_new_game(self):
        """Commence une nouvelle partie."""
        self.game_history = []
    
    def end_game(self, result, final_board=None):
        """Termine une partie et met à jour l'apprentissage."""
        self.games_played += 1
        
        # Déterminer la récompense
        if result == "1-0":  # Blancs gagnent
            reward = 1000
            self.wins += 1
        elif result == "0-1":  # Noirs gagnent
            reward = -1000
            self.losses += 1
        elif result == "1/2-1/2":  # Nulle
            reward = 0
            self.draws += 1
        else:  # Résultat inconnu, évaluer le matériel
            if final_board:
                reward = self._evaluate_material(final_board) // 10
            else:
                reward = 0
            self.draws += 1
        
        # Backpropagation : mettre à jour la Q-table
        self._backpropagate(reward)
        
        # Décroître l'exploration
        self.epsilon = max(0.05, self.epsilon * 0.995)
        
        # Sauvegarder
        self._save_learning_data()
    
    def _backpropagate(self, final_reward):
        """Met à jour la Q-table avec backpropagation."""
        # Parcourir l'historique en ordre inverse
        for i in range(len(self.game_history) - 1, -1, -1):
            pos_hash, move, score = self.game_history[i]
            
            # Calculer la récompense actualisée
            if i == len(self.game_history) - 1:
                # Dernier coup : récompense finale
                discounted_reward = final_reward
            else:
                # Coups précédents : utiliser la valeur du prochain état
                next_pos_hash = self.game_history[i + 1][0]
                next_value = self.q_table.get(next_pos_hash, 0)
                discounted_reward = final_reward * (self.gamma ** (len(self.game_history) - 1 - i))
            
            # Mettre à jour la Q-table
            old_value = self.q_table.get(pos_hash, score if score else 0)
            new_value = old_value + self.learning_rate * (discounted_reward - old_value)
            self.q_table[pos_hash] = new_value
    
    def _load_learning_data(self):
        """Charge les données d'apprentissage."""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.q_table = {k: v for k, v in data.get('q_table', {}).items()}
                    self.games_played = data.get('games_played', 0)
                    self.wins = data.get('wins', 0)
                    self.draws = data.get('draws', 0)
                    self.losses = data.get('losses', 0)
                    self.epsilon = max(0.05, data.get('epsilon', 0.3))
                    
                print(f"[SimpleIA] Chargé: {len(self.q_table)} positions, {self.games_played} parties")
                print(f"[SimpleIA] Stats: W:{self.wins} D:{self.draws} L:{self.losses} (eps={self.epsilon:.3f})")
            except Exception as e:
                print(f"[SimpleIA] Erreur chargement: {e}")
    
    def _save_learning_data(self):
        """Sauvegarde les données d'apprentissage."""
        try:
            data = {
                'q_table': self.q_table,
                'games_played': self.games_played,
                'wins': self.wins,
                'draws': self.draws,
                'losses': self.losses,
                'epsilon': self.epsilon
            }
            
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
                
            print(f"[SimpleIA] Sauvegardé: {len(self.q_table)} positions, {self.games_played} parties")
        except Exception as e:
            print(f"[SimpleIA] Erreur sauvegarde: {e}")
    
    def get_stats(self):
        """Retourne les statistiques de l'IA."""
        total = max(1, self.games_played)
        return {
            'games_played': self.games_played,
            'positions_learned': len(self.q_table),
            'wins': self.wins,
            'draws': self.draws,
            'losses': self.losses,
            'win_rate': round(self.wins / total, 3),
            'epsilon': round(self.epsilon, 3)
        }
    
    def coup(self, board):
        """Interface compatible avec le code existant."""
        move = self.choose_move(board)
        if move:
            return board.san(move)
        return None

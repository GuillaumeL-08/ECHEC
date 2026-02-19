# SimpleIA - IA d'Échecs Simplifiée

## Présentation

`SimpleIA` est une intelligence artificielle pour jouer aux échecs, conçue pour être la plus simple possible tout en utilisant le reinforcement learning. Elle remplace l'IA complexe `TreeIA` (1000+ lignes) par une solution minimaliste et compréhensible.

## Caractéristiques

### 🎯 Simplicité
- **~200 lignes de code** (vs 1000+ pour TreeIA)
- Architecture claire et modulaire
- Facile à comprendre et modifier

### 🧠 Apprentissage par Renforcement
- **Q-learning** : Table de valeurs pour chaque position
- **Epsilon-greedy** : Balance exploration/exploitation
- **Backpropagation** : Apprentissage après chaque partie

### ⚡ Performance
- Évaluation rapide des positions
- Apprentissage visible partie après partie
- Sauvegarde automatique des connaissances

## Architecture

### 1. Évaluation de Position
```python
def evaluate_position(self, board):
    # Score matériel (pion=100, dame=900, etc.)
    # Bonus positionnels (centrage, avancement)
    # Valeurs apprises (Q-table)
```

### 2. Sélection des Coups
```python
def choose_move(self, board):
    if random.random() < self.epsilon:
        return random.choice(legal_moves)  # Exploration
    else:
        return best_move_by_evaluation()    # Exploitation
```

### 3. Apprentissage
```python
def end_game(self, result, final_board):
    reward = get_reward(result)  # +1000 victoire, -1000 défaite
    backpropagate(reward)        # Mettre à jour Q-table
    self.epsilon *= 0.995        # Réduire exploration
```

## Paramètres

| Paramètre | Valeur par défaut | Description |
|-----------|-------------------|-------------|
| `epsilon` | 0.3 | Taux d'exploration (0 = exploitation pure) |
| `learning_rate` | 0.1 | Vitesse d'apprentissage |
| `gamma` | 0.9 | Facteur d'actualisation (importance du futur) |

## Utilisation

### Lancer l'interface graphique
```bash
python main.py
```

### Tester l'IA
```bash
python test_simple_ia.py
```

### Utiliser dans votre code
```python
from simple_ia import SimpleIA
import chess

ia = SimpleIA()
board = chess.Board()

# Choisir un coup
move = ia.choose_move(board)
board.push(move)

# Terminer une partie (pour l'apprentissage)
ia.end_game("1-0", board)  # Victoire des blancs
```

## Fichiers

- **`simple_ia.py`** : L'IA principale
- **`simple_ia_learning.json`** : Données d'apprentissage sauvegardées
- **`main.py`** : Interface graphique modifiée pour utiliser SimpleIA
- **`test_simple_ia.py`** : Tests de fonctionnement

## Apprentissage

### Récompenses
- **Victoire** : +1000
- **Défaite** : -1000
- **Nulle** : 0

### Sauvegarde
Les données sont automatiquement sauvegardées après chaque partie dans `simple_ia_learning.json` :
- Positions apprises
- Statistiques (victoires/défaites)
- Taux d'exploration actuel

### Évolution
L'IA s'améliore progressivement :
1. **Début** : Explore beaucoup (epsilon = 0.3)
2. **Milieu** : Équilibre exploration/exploitation
3. **Fin** : Exploite les connaissances (epsilon → 0.05)

## Comparaison avec TreeIA

| Caractéristique | SimpleIA | TreeIA |
|-----------------|----------|--------|
| **Lignes de code** | ~200 | 1000+ |
| **Complexité** | Simple | Très complexe |
| **Temps de calcul** | Rapide | Lent |
| **Apprentissage** | Q-learning | Table de transposition |
| **Compréhension** | Facile | Difficile |
| **Maintenance** | Simple | Complexe |

## Avantages

✅ **Simplicité** : Code facile à lire et modifier  
✅ **Pédagogique** : Idéal pour apprendre le reinforcement learning  
✅ **Léger** : Fonctionne sur des machines modestes  
✅ **Extensible** : Facile à améliorer avec de nouvelles fonctionnalités  
✅ **Fiable** : Moins de bugs grâce à la simplicité  

## Limitations

⚠️ **Force modérée** : Pas aussi forte que des moteurs complexes  
⚠️ **Pas de book d'ouvertures** : Apprend tout depuis zéro  
⚠️ **Q-table croissance** : Peut devenir grande avec beaucoup de parties  

## Améliorations Possibles

1. **Book d'ouvertures** : Ajouter des coups d'ouverture standards
2. **Réseau neuronal** : Remplacer la Q-table par un petit réseau
3. **Évaluation avancée** : Ajouter plus de heuristiques positionnelles
4. **Multi-threading** : Paralléliser la recherche de coups
5. **Interface web** : Créer une interface de jeu en ligne

## Conclusion

`SimpleIA` démontre qu'une IA d'échecs fonctionnelle peut être implémentée simplement avec le reinforcement learning. C'est un excellent point de départ pour comprendre les principes de base avant de passer à des implémentations plus complexes.

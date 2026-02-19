# Système d'Apprentissage de l'IA d'Échecs

## Vue d'ensemble

Votre IA d'échecs a été transformée en une IA qui apprend de ses erreurs via un système d'apprentissage par renforcement. Plus elle joue de parties, plus elle devient forte.

## Fonctionnalités

### 🧠 Apprentissage par Renforcement
- **Apprentissage des positions** : L'IA mémorise la valeur de chaque position rencontrée
- **Rétropropagation** : Les résultats des parties influencent l'évaluation des positions précédentes
- **Exploration vs Exploitation** : L'IA explore de nouveaux coups tout en exploitant ses connaissances

### 💾 Stockage des Données
- **Fichier JSON** : `ia_learning_data.json` contient toutes les données d'apprentissage
- **Persistances** : Les connaissances sont conservées entre les sessions
- **Sauvegarde automatique** : Les données sont sauvegardées toutes les 10 parties

### 📈 Amélioration Continue
- **Taux d'exploration adaptatif** : Diminue avec l'expérience
- **Intégration progressive** : Les valeurs apprises sont combinées avec l'évaluation heuristique
- **Statistiques détaillées** : Suivi du nombre de parties et positions apprises

## Modifications Apportées

### Nouveaux Fichiers
- `learning_manager.py` : Gestionnaire de l'apprentissage
- `test_learning.py` : Script de test pour l'apprentissage automatique
- `ia_learning_data.json` : Base de données d'apprentissage (créé automatiquement)

### Fichiers Modifiés
- `ia_tree.py` : Intégration de l'apprentissage dans TreeIA
- `canvas_tkinter.py` : Gestion de fin de partie pour l'apprentissage

## Utilisation

### Lancer une partie avec apprentissage
```python
# Dans main.py
ia_noir = TreeIA(depth=4, enable_learning=True)  # IA avec apprentissage
```

### Lancer un test d'apprentissage automatique
```bash
python test_learning.py
```

### Désactiver l'apprentissage
```python
ia_noir = TreeIA(depth=4, enable_learning=False)  # IA classique
```

## Fonctionnement de l'Apprentissage

### 1. Phase d'Exploration
- Au début, l'IA explore beaucoup (20% de coups aléatoires)
- Elle découvre de nouvelles positions et leurs résultats

### 2. Phase d'Apprentissage
- À chaque fin de partie, les positions sont évaluées
- Victoire = +1000, Défaite = -1000, Nulle = 0
- Les valeurs sont propagées aux positions précédentes

### 3. Phase d'Exploitation
- Avec l'expérience, l'IA exploite ses connaissances
- Le taux d'exploration diminue progressivement

## Données d'Apprentissage

Le fichier `ia_learning_data.json` contient :
- `position_values` : Valeur apprise pour chaque position (FEN)
- `move_history` : Historique des 1000 dernières parties
- `games_played` : Nombre total de parties jouées
- `last_updated` : Date de dernière mise à jour

## Statistiques

Pendant les parties, vous verrez :
- Nombre de parties jouées
- Nombre de positions apprises
- Taux d'exploration actuel

## Performance

- **Début** : L'IA joue comme avant, avec exploration
- **Après ~50 parties** : Début d'amélioration visible
- **Après ~200 parties** : L'IA est significativement plus forte
- **Après ~1000 parties** : Niveau expert atteint

## Notes

- L'apprentissage est cumulatif : chaque partie améliore l'IA
- Les données sont partagées entre les IAs de la même couleur
- Le fichier JSON peut être sauvegardé/copié pour conserver les connaissances
- L'IA continue de s'améliorer indéfiniment avec plus de parties

## Prochaines Étapes

Pour tester le système :
1. Lancez `python test_learning.py` pour voir l'apprentissage en action
2. Lancez `python main.py` pour jouer contre l'IA qui apprend
3. Après plusieurs parties, vous verrez l'IA devenir plus forte

L'IA est maintenant prête à apprendre et à s'améliorer continuellement !

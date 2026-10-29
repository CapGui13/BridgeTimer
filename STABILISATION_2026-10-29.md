# Bridge Timer 1.7.8 — stabilisation du 29 octobre 2026

## Références de restauration

- **Programme validé visuellement sur Windows 10 :** commit `895347f33fcce10c9fc03871c310d77f9103172d`, branche `sauvegarde-bridge-timer-valide-20261029`.
- **Version principale précédente :** commit `a76fe0dbf5e4304bce04d3c77aa49c7371416429`, branche `archive-main-avant-stabilisation-20261029`.
- **Dernier audit automatisé du programme validé :** commit `07ccadfbcc425c1abd29dbf949f630f808530bea`, branche `audit-horloge-et-sons-20261029`.
- **Dernière compilation d'audit réussie :** https://github.com/CapGui13/BridgeTimer/actions/runs/40885940671

## Fonctionnalités conservées

1. Fenêtre Paramètres au démarrage : 812 × 680, bandeaux natifs (titre 34 px, en-tête 55 px, pied 59 px).
2. Fenêtre Timer plus basse ; largeur choisie par l'utilisateur préservée, hauteur recalculée.
3. Retour aux Paramètres en conservant la largeur et la hauteur enregistrée.
4. Positionnement de la fenêtre à l'intérieur de la zone utilisable du moniteur.
5. Mini-timer en bas à gauche, panneau Reprise compact, raccourcis et confirmation de fermeture.
6. Plein écran natif et mode projeté.
7. Décompte fondé sur le temps monotone, rattrapage après retard de rafraîchissement et pause.
8. Formats Paires et Match par 4, sauts, pauses inter-tours, annonces et messages.

## Contrôles GitHub Actions requis

- `checks/test_synced_ui.js` — invariants de production.
- `checks/test_visual_transitions.py` — mises en page et changements d'écran.
- `checks/test_windowed_settings_bands.py` — tailles visuelles des boutons et bandeaux aux largeurs 684, 812, 960.
- `checks/test_functional_end_to_end.py` — **15 scénarios** en navigateur Microsoft Edge.
- `checks/test_long_clock_sound.py` — **10 scénarios** d'horloge simulée, sons et anti-veille.
- `go test ./...` — géométrie native, vraie fenêtre Win32 et requête anti-veille.
- `go vet ./...` et compilation Windows `go build`.
- `checks/check_exe_embed.py` — conformité du HTML embarqué dans l'EXE.

**Limite des tests :** les tests automatisés n'équivalent pas à une séance réelle
de plusieurs heures ni à une vérification acoustique sur les haut-parleurs.
Ils ne garantissent pas non plus l'absence de régression graphique sur toutes
les configurations DPI/Windows. Conserver un EXE déjà éprouvé pour l'arbitrage.

## Procédure de mise en production

1. Préserver les deux branches de restauration ci-dessus.
2. Vérifier la PR, contrôler que les tests GitHub Actions sont tous verts, puis fusionner sur `main`.
3. Attendre la compilation `main` et vérifier le SHA de la source du binaire.
4. Extraire l'EXE officiel de l'artifact `BridgeTimer-Windows-unsigned`.
5. Tester sur Windows 10 les entrées/sorties de plein écran, le démarrage, les transitions, le bouton Test son et l'anti-veille.
6. Ne pas supprimer les branches d'essai tant que la version n'a pas été utilisée sur une séance réelle.

## Retour arrière

La branche `sauvegarde-bridge-timer-valide-20261029` conserve **le code de l'EXE
validé par l'utilisateur**. La branche `archive-main-avant-stabilisation-20261029`
conserve l'état de `main` avant consolidation. Ne pas déplacer ces références.

Pour récupérer un EXE de la version précédente, utiliser les artifacts de
https://github.com/CapGui13/BridgeTimer/actions/runs/40878830646 .

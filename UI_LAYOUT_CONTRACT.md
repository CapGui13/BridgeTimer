# Bridge Timer — contrat d'affichage à préserver

> **RÈGLES IMPÉRATIVES DONNÉES PAR L'UTILISATEUR — 25 octobre 2026.**
> À lire **avant toute modification** du rendu, du CSS, du calcul des polices,
> de `fc()`, `captureFullscreenStage()`, `scaleFullscreenStage()`,
> `q25()`, `fs()` ou des tests d'affichage.
> Ces contraintes ne sont **pas** de simples préférences ; elles priment sur
> les ajustements visuels opportunistes. Ne pas les supprimer pour résoudre un
> autre problème.

## 1. Plein écran strictement homothétique

**« Plein écran homothétique : l'ensemble de l'interface est agrandi avec un
facteur unique. Les chiffres, textes, boutons, espacements et barres conservent
leurs proportions. »**

Pour un **même état** du timer (même temps restant, même message, mêmes boutons),
le plein écran est la même maquette agrandie, et non une autre mise en page :
- un seul facteur d'échelle uniforme pour tous les composants ;
- mêmes positions *relatives*, rapports de taille, alignements et espacements ;
- aucun changement arbitraire de taille de police, de marges, de positions ou
  de proportion entre fenêtré et plein écran ;
- aucun étirement différent sur X et Y ;
- mêmes règles pour les modes MP4 / Paires et les écrans spéciaux
  (Pause, pré-saut, saut, fin de tour, fin de séance, annonces de donnes).

Un seul ajustement du chrono ne doit **jamais** casser le haut, le bas, les
messages ou les écrans spéciaux.

## 2. Le chrono HH:MM:SS doit remplir la largeur utile

**Autre exigence impérative, explicitement réaffirmée le 25 octobre 2026 :**
lorsqu'il reste **plus d'une heure** (p. ex. `01:03:30`), les grands chiffres
doivent occuper **presque toute la largeur utile du plein écran**, comme dans
les versions précédentes de Bridge Timer.

**BUG CONSTATÉ / NON CORRIGÉ :** la version du 25/10/2026 utilise
`Math.min(innerWidth/stage.width, innerHeight/stage.height)` pour préserver
l'homothétie, mais cela rétrécit la maquette et laisse de **grandes bandes
latérales** lorsque les proportions de la fenêtre et du moniteur diffèrent.
L'utilisateur a expressément rejeté ce rendu.

**Ne pas déclarer le bug résolu** au seul motif que la transformation est
homothétique. Le comportement final devra respecter à la fois (1) et (2).
Lorsque les rapports d'aspect diffèrent, un simple zoom uniforme de l'intégralité
d'une maquette de dimensions figées ne peut pas remplir simultanément la
largeur et la hauteur sans marges ou découpe. Résoudre ce conflit avec une
maquette de référence / une stratégie de composition validée, **sans revenir**
à des mises à l'échelle indépendantes par élément.

## 3. Chiffres MM:SS : grands mais sans chevauchement

Au passage sous l'heure (`59:59`, `57:20`) :
- l'affichage à cinq caractères peut être agrandi par rapport à `HH:MM:SS` ;
- le haut des chiffres garde une **marge visuelle nette** sous le nom
  d'évènement (p. ex. « Compet ») ;
- le bas des chiffres ne chevauche jamais la barre de progression ;
- à temps affiché **identique**, fenêtré et plein écran gardent la même
  homothétie pour tous les éléments, y compris ces chiffres agrandis.

Ne pas corriger une proximité excessive avec le titre en réduisant toute
l'interface, en rétrécissant le chrono long ou en détruisant l'homothétie.

## 4. Vérifications obligatoires avant de proposer un nouvel EXE

1. Fenêtré puis plein écran au **même instant** à `01:03:30` :
   comparer titre, chrono, barre, commandes, heure, numéro de tour et toutes
   leurs positions et proportions ; le chrono long conserve une grande largeur.
2. Refaire la même comparaison à `59:59` et `57:20` : agrandissement correct,
   marge nette sous le titre, aucune collision avec la barre.
3. Aller et revenir du plein écran plusieurs fois ; vérifier aussi un
   redimensionnement de fenêtre et plusieurs rapports d'aspect.
4. Tester les messages temporaires, annonces de donnes, Pause, saut,
   fin de tour MP4 et fin de séance Paires.
5. Lancer la suite de tests et une compilation Windows ; **ne pas prétendre
   avoir vérifié le rendu Windows natif** sans un test visuel réel.

## 5. Procédure de modification

- Lire les commentaires de protection placés dans `timer.html`.
- Modifier le minimum nécessaire ; préserver les fonctions métier et leurs
  raccourcis.
- Mettre à jour les tests pour **maintenir** le contrat de comportement ;
  ne jamais assouplir ou supprimer une assertion parce qu'elle gêne une
  correction sans expliquer pourquoi le contrat est toujours respecté.
- Conserver explicitement ce document lors des refontes du moteur d'affichage.
- **État au 25/10/2026 :** homothétie structurelle introduite, mais largeur
  du chrono long en plein écran **non conforme** à l'attente ; la correction
  reste à faire, distinctement des présentes annotations.

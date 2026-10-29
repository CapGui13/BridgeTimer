# Bridge Timer — contrat d'affichage à préserver

> **RÈGLES IMPÉRATIVES DONNÉES PAR L'UTILISATEUR — 25 octobre 2026.**
> À lire **avant toute modification** du rendu, du CSS, du calcul des polices,
> de `fc()`, `captureFullscreenStage()`, `scaleFullscreenStage()`,
> `q25()`, `fs()` ou des tests d'affichage.
> Ces contraintes ne sont **pas** de simples préférences ; elles priment sur
> les ajustements visuels opportunistes. Ne pas les supprimer pour résoudre un
> autre problème.

## RÈGLES FONDAMENTALES — NE JAMAIS FAIRE RÉGRESSER (26/10/2026)

**RÈGLE A — Homothétie totale entre fenêtre et plein écran.**
Une seule maquette de référence de **1600 × 900 (16:9)**, avec **un seul
coefficient d’agrandissement uniforme** pour chaque affichage. Fenêtré et plein
écran doivent montrer **exactement la même composition** pour un état identique :
positions relatives, tailles relatives, chiffres, titre, nom du club, boutons,
messages, espaces, bandeau et écrans spéciaux. **Aucun élément ne doit avoir son
propre facteur d’échelle**, ni sa position recalculée différemment selon le mode.
L'espace libre hors maquette n'autorise ni déformation ni déplacement interne.

**RÈGLE B — Parité visuelle des formats court et long.**
Le format est sélectionné **une fois à partir de la durée initiale du tour**
(voir §7), pas d'après le temps restant. **Les grands chiffres** du format long
(`H:MM`) doivent avoir **exactement la même taille de police, la même hauteur
visuelle et le même placement vertical** que ceux du format court (`MM:SS`),
avec la **même distance visible entre le bas du nom de l’évènement et le haut
des chiffres**. Le titre, le nom du club, les contrôles et tous les éléments
communs conservent les mêmes positions et proportions. Seules exceptions
explicitement voulues : le **contenu et la composition du temps** (`MM:SS`
contre `H:MM  SS`), et les secondes du format long affichées à **56 %**
de la taille des chiffres principaux. Ces secondes réduites ne doivent PAS
entraîner une réduction des grands chiffres ou un déplacement du groupe.

**RÈGLE C — Réglage partagé, source unique de vérité.**
Tout paramètre visuel commun (position et taille de l'évènement, taille et
ligne de base des grands chiffres, écart titre/chrono, boutons, alignements,
espaces et composition générale) doit avoir **une seule valeur de référence**
dans la maquette et **une seule règle de calcul**. Quand l'utilisateur affine
un de ces paramètres, **le changement s'applique automatiquement** :
- au format court et au format long, sans retouche indépendante ;
- au mode fenêtré et au plein écran, par la seule homothétie uniforme ;
- aux vues spéciales qui partagent réellement cet élément, sauf exception
  explicitement demandée.

**Interdit :** recopier un décalage ou une taille en dur dans chaque branche,
ou corriger successivement les variantes « à l’œil ». Si un réglage commun
est encore calculé séparément dans le code actuel, le centraliser avant de le
modifier, puis prouver par les tests que les deux variantes utilisent la même
référence. Les différences intentionnelles du format long (composition et
secondes à 56 %) restent des exceptions explicites, jamais des réglages
concurrents pour les grands chiffres.

**État technique :** certaines formules du moteur `fc()` sont aujourd'hui
encore distinctes pour les deux formats. Cette règle est donc **une obligation
d'architecture pour les prochaines modifications**, pas une affirmation que
tous les paramètres sont déjà centralisés. Ne pas annoncer une synchronisation
automatique avant de l'avoir démontrée.

**RÈGLE D — Deux familles d'annonces, chacune à réglage unique (27/10/2026).**

1. **Pendant le tour :** message temporaire, numéro de donne (« attaquer » /
   « jouer ») et pré-alerte de saut partagent **la même boîte `#msg`**,
   les mêmes positions, dimensions, police, couleur, relief et adaptation
   automatique à la longueur du texte (`q38()`).
2. **Transitions :** les bandeaux permanents haut (club, boutons) et bas (heure, tour, contrôles) restent visibles pendant les transitions. Le panneau commun `#jumpSplash` ne recouvre que `.main`. Le **temps entre deux tours** doit désormais avoir
   **EXACTEMENT le même design que le saut effectif de table**, réutilisant
   **le même écran `#jumpSplash`**, le même titre en haut, le message central,
   le décompte et sa barre, ainsi que le même ajustement `q40()`.
   Aucune règle CSS ou coordonnée parallèle ne doit être créée.
   Seuls le texte, le titre et la durée changent : entre-tours =
   « CHANGEMENT DE TOUR » / « Changez de table » (ou message temporaire actif),
   avec les secondes restantes et « secondes pour le changement ».
   Le saut conserve ses textes configurables.

**RÈGLE E — Bouton CHGT (27/10/2026).**
Dans les paramètres de Paires, le bouton **CHGT** est à droite du champ
« Temps entre tours ». **En fonctionnement normal**, il apparaît
si la durée de l'entre-tours atteint **1 seconde** (à `00`, bouton masqué).
**Exception explicite Debug :** en mode **Paires**, activer Debug rend
CHGT visible et utilisable même avec `00` seconde pour permettre les réglages
et essais. Le passage Debug activé/désactivé rafraîchit le bouton immédiatement.
**Lorsqu'on bascule Match par 4 ↔ Paires sous Debug, CHGT doit également
changer de visibilité pendant le même événement, avant le prochain rendu,
sans attendre l'enregistrement automatique ni un délai de 450 ms.**
En Match par 4, CHGT reste masqué, y compris lorsque Debug est activé.
Le bouton ouvre un dialogue du **même modèle graphique que MSG pour le saut**
(titre, texte central, puis **deux colonnes sur la même ligne : durée en secondes
à gauche, texte du décompte à droite**, et Annuler / Valider).
Les valeurs sont **indépendantes** de celles du saut. La durée peut être
modifiée soit dans « Temps entre tours », soit dans la fenêtre CHGT :
**c'est une seule donnée `between`**, synchronisée de manière
bidirectionnelle lors de l'ouverture et de la validation de CHGT.
L'édition dans CHGT est transactionnelle : **Annuler ne modifie pas
les paramètres**, Valider met immédiatement à jour la case de temps dans
les paramètres et enregistre la valeur. La phrase « Durée : réglée par… »
n'apparaît plus. Le bouton conserve la règle de visibilité précédente,
notamment son affichage à `00` seconde en mode Paires + Debug.
Ces réglages sont enregistrés avec les paramètres et utilisés par
`transitionSplashModel`. Le design de l'écran final demeure partagé
entre saut et entre-tours ; aucune variante graphique de CHGT n'est permise.

**RÈGLE F — Couleur indépendante des messages de transition (27/10/2026).**
Dans « Personnalisation des couleurs », proposer une ligne distincte
**« Messages de changement et saut »**, avec un sélecteur de couleur
**rouge `#ef4444` par défaut** (le même rouge que l'alerte).
Ce réglage unique `transitionMessageColor` s'applique **aux titres et
aux messages centraux du même écran `#jumpSplash`** dans les deux cas :
« Saut de table » et « Temps entre tours / Changement de tour ».
Il est indépendant de `accent` (la barre de décompte reste bleue si la
couleur principale est bleue) et de `messageColor` (les messages verts
ordinaires restent inchangés). Les textes du décompte restent en
`--text`, sans changement de couleur ni de dimension.
La couleur doit être persistée, restaurée avec Annuler, intégrée aux
thèmes personnalisés et remise au rouge lors d'OG Colors. Les anciens
paramètres sans ce champ migrent sans perte et obtiennent le rouge par
défaut. **Aucune duplication entre les écrans** : une seule variable CSS
`--transition-message-color` pilote les deux.

Toutes ces annonces suivent la même homothétie fenêtré/plein écran.
**Changement de tour :** la ligne « Prochain tour : X » est définitivement
supprimée. PAUSE et fin de séance restent distincts et inchangés.

**Important :** « même hauteur » signifie **mêmes mesures typographiques et
même bande visuelle à glyphes comparables**, et non pas artificiellement la
même boîte englobante pour des chiffres de formes différentes. Vérifier les
rendus à caractères comparables et dans plusieurs tailles de fenêtre.

**AUCUN AUTRE CHANGEMENT GRAPHIQUE** lors de la mise en place de ces règles.
Il est interdit de corriger un défaut local en modifiant indépendamment le
format court, le format long, le mode fenêtré ou le plein écran.
Si une exception devient nécessaire, demander une validation explicite avant
de modifier les protections.

### Validation anti-régression obligatoire

1. Pour un même temps et un même état, mesurer les rapports de dimensions
   **fenêtré → plein écran** du titre, des grands chiffres, des petites
   secondes, des boutons, des espaces et du bas d’écran : **le rapport doit
   être identique partout**, égal au coefficient d’échelle commun.
2. Comparer à résolution égale un tour de départ court et un tour de départ
   long, en utilisant des **glyphes identiques ou comparables** pour les grands
   chiffres : taille de police, haut/bas visibles, marge sous l’évènement.
3. Contrôler les deux passages de mode, la période sous 1h d'un tour ayant
   démarré à 1h ou plus, et les autres écrans et messages.
4. Garder des tests permanents dans `checks/test_synced_ui.js`, ainsi que les
   commentaires de protection près de `updateStage()` et de `fc()`.
   **Les tests de présence de code ne remplacent pas une vérification visuelle
   sur Windows natif.** Ne jamais revendiquer celle-ci sans l'avoir effectuée.

---

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
pour un tour démarré à une heure ou davantage, les grands chiffres `H:MM`
restent **très grands**, comme ceux du format court. Les secondes `SS` sont
plus petites (56 %). Ne jamais réduire les grands chiffres à cause de ces
secondes, ni les étirer indépendamment pour remplir artificiellement l'écran.

**RÉGRESSION HISTORIQUE (25/10/2026) :** le passage en plein écran
de l'ancienne maquette au rapport de la fenêtre étroite provoquait de grandes
bandes latérales, réduisant le chrono long au lieu de lui laisser presque toute
la largeur. Ce rendu a été rejeté par l'utilisateur.

**RETOUR AU RENDU ANTÉRIEUR :** la tentative de correction utilisant
`syncWindowedStage()` a elle aussi provoqué une régression visible :
une barre bleue trop large, un chrono HH:MM:SS plus petit, des contrôles
non affichés sur la première capture et une composition bouleversée.
**L'utilisateur a rejeté cette version le 25 octobre 2026.**

Le code d'affichage a donc été **restauré depuis le commit
`0e5b340`** (dernier rendu antérieur à ces régressions), avec uniquement
des annotations et des tests de protection ajoutés. Cette restauration
ne résout PAS encore parfaitement l'homothétie : cette exigence reste
ouverte. Toute future tentative devra d'abord prouver visuellement
qu'elle conserve la grande taille du chrono long et l'apparence globale,
en fenêtre ET en plein écran.

**Validation encore nécessaire :** vérifier cet affichage dans l'application
Windows native sur les écrans de l'utilisateur. Ne jamais réintroduire
l'agrandissement d'une fenêtre au rapport d'aspect différent : cela rétablirait
les marges latérales excessives.

## 3. Chiffres MM:SS : grands mais sans chevauchement

Au passage sous l'heure (`59:59`, `57:20`) :
- l'affichage à cinq caractères peut être agrandi par rapport à `HH:MM:SS` ;
- le haut des chiffres garde une **marge visuelle nette** sous le nom
  d'évènement (p. ex. « Compet ») ;
- le bas des chiffres conserve une marge suffisante avec le bandeau inférieur (la barre bleue de progression a été supprimée) ;
- à temps affiché **identique**, fenêtré et plein écran gardent la même
  homothétie pour tous les éléments, y compris ces chiffres agrandis.

Ne pas corriger une proximité excessive avec le titre en réduisant toute
l'interface, en rétrécissant le chrono long ou en détruisant l'homothétie.

## 4. Vérifications obligatoires avant de proposer un nouvel EXE

1. Fenêtré puis plein écran pour **le même état d'un tour démarré à plus
   d'une heure** (p. ex. `1:03 30`) : comparer titre, grands chiffres,
   petites secondes, commandes, heure et numéro de tour, ainsi que toutes
   leurs positions et proportions ; un seul coefficient pour l'ensemble.
2. Refaire la même comparaison pour un **tour démarré à moins d'une heure**
   (`59:59`, `57:20`) ; comparer aussi l'alignement des grands chiffres
   entre formats court et long à une même résolution.
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
- **État au 25/10/2026 :** régression graphique annulée en restaurant
  l'affichage du commit `0e5b340`. Grande largeur du chrono HH:MM:SS et
  largeur normale de la barre conservées. **Homothétie stricte toujours
  à améliorer**, après validation avec captures comparatives sur Windows.

## 6. Essai isolé du 25/10/2026 — maquette 16:9

- **Branche de test seulement :** `experiment/bridge-timer-16x9-20261025`.
- **Retour arrière immédiat :** branche stable `main`, commit de départ
  `a76fe0dbf5e4304bce04d3c77aa49c7371416429`, non modifié par l'essai.
- La scène du timer se calcule toujours sur **1600 × 900** unités (16:9).
  Mode fenêtré et plein écran appliquent exactement **un seul coefficient** à
  tout le timer, sans recalcul des éléments lors du changement de mode.
- Taille d'ouverture/minimum actuelle de la fenêtre Windows : **960 × 720** (dimensions nécessaires aux paramètres ; ne pas les réduire pour la maquette du timer)
  unités logiques ; la maquette interne 16:9 est ajustée uniformément à cette
  fenêtre.
- Les boutons d'en-tête ont une largeur suffisante pour « Paramètres » et
  « Quitter plein écran », et la miniature copie le rendu au format 16:9.
- **Contrôle manuel obligatoire sur Windows :** lisibilité des boutons, ratio
  correct, absence de chevauchement sous le titre, grande largeur du chrono
  à une heure et affichage MM:SS. Vérifier les deux passages de mode.
- Si le résultat ne convient pas, **ne pas fusionner cette branche**. Continuer
  à utiliser `main` et l'EXE précédemment validé.

## 7. Contrat du chrono selon la DURÉE INITIALE du tour (26/10/2026)

**Règle impérative : la durée du tour au DÉMARRAGE fixe le rendu pour tout le tour.**
Ne JAMAIS basculer le style lorsque le compte à rebours passe sous une heure.

- **Tour initial inférieur à 3600 secondes :** conserver EXACTEMENT le chrono
  approuvé `MM:SS` en cinq grands caractères, sans modifier l'alignement,
  les polices, les titres, les boutons, le fond ni les autres zones.
- **Tour initial supérieur ou égal à 3600 secondes :** afficher
  `H:MM  SS` en deux blocs. `H:MM` a **exactement la même taille et la même
  position verticale que les grands chiffres du format court** ; seuls les
  deux chiffres des secondes sont à **56 %** de cette taille,
  sur la même ligne et alignés visuellement en bas.
- Exemple : au début d'un tour de 1 h 54 min 58 s → `1:54  58` ;
  lorsqu'il reste 59 min 59 s → `0:59  59`, sans changement de style.
- Au commencement de chaque nouveau tour, la sélection peut être recalculée
  sur sa nouvelle durée initiale. Les réglages de temps pendant un tour ne
  doivent pas modifier rétrospectivement son style.
- Conserver le retour en arrière/annulation d'une position avec sa sélection.
- **Ne pas réintroduire** la barre de progression bleue précédemment supprimée.
- Les éléments restent identiquement proportionnés entre la fenêtre et le
  plein écran au moyen de la maquette commune 16:9.

En cas d'incompatibilité avec un futur correctif : préserver le format court
déjà approuvé, préserver la durée initiale comme unique discriminant, et
mettre à jour le test `checks/test_synced_ui.js` uniquement si le contrat est
toujours pleinement respecté.


## Stabilité des bandeaux entre tous les écrans (27/10/2026)

- Pendant une transition, l'écran commun ne couvre que `.main`, jamais l'en-tête ni le pied de page.
- L'état `breakState` ne doit pas modifier la couleur de fond de `#timer` : l'éventuelle teinte spéciale est limitée à `.main`.
- Le groupe des commandes du bas conserve sa **géométrie strictement identique** quand les boutons changent de libellé entre « − 1 min / + 1 min » et « − 15 s / + 15 s ».
- Les chemins `round → break → round`, `round → jump → round`, `round → roundEnd → round`, `round → ended → round`, `fenêtré → plein écran → fenêtré`, `timer → paramètres → timer` et `Écrans tests → paramètres` sont des scénarios de non-régression.
- Conserver l'ouverture Windows à **960 × 720** pour les paramètres. Ne pas toucher aux dimensions natives de la fenêtre pour corriger la maquette 16:9.
- Tests source/CI et matrice visuelle Chromium sont complémentaires. Aucun test ne remplace la confirmation finale sur Windows.


## Fenêtre native distincte des paramètres et du timer — 27/10/2026

Le 1600 × 900 strict 16:9 ne peut pas remplir un client Windows d'aspect 4:3 sans
bandes vides. Le **correctif natif**, pas une modification CSS, préserve :

- paramètres : fenêtre initiale et minimale **960 × 720** (hauteur nécessaire
  à l'interface avec défilement et barre d'actions) ;
- timer : **même largeur**, mais hauteur extérieure ajustée via Win32 selon
  `H_client = round(W_client × 9/16)`, plus les bordures et la barre de titre
  réellement mesurées avec `GetWindowRect` et `GetClientRect` ;
- retour aux paramètres : restauration des dimensions antérieures de fenêtre ;
- plein écran : aucune modification de la logique et de la projection 16:9
  native existante, nouveau contrôle de mode seulement au retour.

Ne jamais corriger le letterboxing en réduisant le format de **toute**
l'application ou en déformant la maquette. Ne jamais modifier la géométrie
native en fonction du changement de tour, du saut, du chrono ou d'un thème.


## Touche M et champ du message temporaire (27/10/2026)

- Lorsqu'un message temporaire est effectivement **visible** pendant un tour ou
  un changement de tour, un premier appui bref sur **M** le masque immédiatement.
  Le message enregistré n'est ni supprimé ni modifié, et aucun formulaire ne
  doit apparaître à cet appui.
- Seul un **deuxième appui distinct** sur M ouvre le formulaire de message, déjà
  prérempli avec le texte enregistré. L'auto-répétition de touche n'ouvre pas
  de formulaire accidentellement. Le bouton « Message » adopte le même geste.
- Si aucun message temporaire n'est affiché, M ouvre directement le formulaire
  (comportement antérieur). Si le formulaire est ouvert, le bouton Message le
  referme comme auparavant.
- Dans les paramètres, le clic ou l'entrée dans le champ « Message temporaire »
  sélectionne immédiatement l'intégralité du texte existant pour remplacement.
- Toute cette logique est indépendante des modes d'écran et de la géométrie
  des bandeaux. Préserver les contrôles visuels précédents.


## Harmonisation de l'en-tête en plein écran et miniature (27/10/2026)

**Périmètre strict :** l'en-tête des paramètres en plein écran et la
miniature en cours. Ne jamais modifier l'en-tête existant du timer, son chrono,
ses commandes, ses transitions, la taille native des paramètres ou la grille
des paramètres en mode fenêtré.

- Sur paramètres **en plein écran**, en-tête largeur **1600** et hauteur
  **82 unités virtuelles**, positionné via **les mêmes** origine et coefficient
  homothétique calculés par `updateStage()` pour le timer. La taille de police
  du titre « Bridge Timer » égale celle du nom du club (40 px virtuels,
  ligne 55 px). La couleur d'accent du titre est conservée.
- Bouton « Timer » à l'emplacement exact du bouton « Paramètres » du timer,
  largeur **168 unités virtuelles**. Bouton « Quitter plein écran » de
  **246 unités virtuelles**, superposé à l'équivalent du timer. Tous deux
  sont dans la même barre d'en-tête ; sortir du plein écran restaure la
  présentation initiale des paramètres.
- Le bouton « Quitter plein écran » dans les paramètres est relié à la
  commande native/HTML plein écran existante, pas à une nouvelle logique.
- La miniature du timer actif est **déplacée en dehors du DOM de la barre
  d'actions**, directement sous `body`, avec `position:fixed;left:0;bottom:0` :
  **coïncidence exacte des angles inférieurs gauches**, affichage au-dessus
  de la barre, sans modifier le placement de ses boutons ni la forme du timer.
- Test graphique Windows obligatoire : mêmes x/y/largeur/hauteur pour
  les en-têtes et les deux boutons en plein écran, miniature à (0, bas),
  et retour au timer et au mode fenêtré sans dérive.


## Paramètres en tournoi démarré et pied de page plein écran (27/10/2026)

- Mode Match par 4 : les champs **Temps par match** (H, M, S)
  et **Temps par donne** (M, S) sont désactivés/grisés une fois le
  tournoi lancé ; le bouton « Affichage n° donne en cours » reste
  utilisable indépendamment de la cohérence des durées. Les minutes
  supplémentaires se donnent depuis le timer.
- Mode Paires : mêmes deux groupes de durée grisés (le premier est
  « Temps par tour »), mais **Temps entre tours** reste modifiable
  lorsque la séance est démarrée. L'affichage du numéro de donne reste
  activable.
- **Debug** réactive tous ces réglages immédiatement.
- Les changements d'une durée de tour/match ou de donne effectués sous Debug
  et enregistrés **ne doivent jamais réinitialiser** le tour en cours, le
  décompte restant, l'horloge de fin native, la phase courante ni un changement
  de tour en cours. Les nouveaux paramètres entrent en vigueur au départ du
  **prochain tour**. Le temps entre tours s'applique aux prochaines pauses.
- Le pied de page **Paramètres en plein écran** reprend les dimensions exactes
  du pied de page 1600×900 du Timer, le même facteur de zoom, la taille
  typographique de ses boutons et leur hauteur. La miniature reste
  indépendante et au-dessus. Les paramètres en mode fenêtré et le timer
  restent inchangés.


## Actualisation 27/10 : même format 16:9 natif en mode fenêtré

* Cette décision **remplace** toutes les consignes anciennes de restauration d'une
  fenêtre de paramètres à **960×720** : ouverture initiale **960×570** extérieur
  (cible : zone utile réelle en 16:9 après prise en compte des bordures Windows).
  La fenêtre des paramètres garde donc les **mêmes dimensions** au lancement,
  pendant les changements de tour et au retour du timer ; aucune restauration
  de hauteur ne doit plus avoir lieu entre les deux vues.
* Calibration de la zone cliente Win32 **une seule fois à l'initialisation**,
  puis aucune modification native de la taille lors des transitions
  Paramètres ⇄ Timer. Le contenu des paramètres défile normalement.
* Le fond de la barre inférieure des paramètres reste **totalement opaque**
  en mode fenêtré comme en plein écran : aucun réglage défilant visible
  à travers, aucun effet de verre. La miniature demeure posée au-dessus.
* Dans la barre d'actions de paramètres, le bouton **Timer/Lancer précède
  Arrêter** ; toutes les fonctions associées aux identifiants restent les mêmes.
* Vérifier les modes Match et Paires, Debug, la non-réinitialisation du
  décompte et les transitions en plein écran avec les contrôles préexistants.


## Ajustement isolé de la barre du haut Paramètres en mode fenêtré (27/10/2026)

Après le passage aux fenêtres natives communes 16:9, l'en-tête des paramètres
restait trop haut : marge supérieure de `.wrap` + titre 34px + séparation.
La page **fenêtrée seulement** reprend désormais la hauteur du haut du Timer
mesurée au moment du passage de vue. Le titre « Bridge Timer » et son bouton
« Retour au timer » sont réduits proportionnellement ; la barre n'ajoute
aucune marge verticale. Le mode plein écran conserve son en-tête synchronisé,
la barre opaque du bas et sa miniature restent inchangées. Un test Chromium
compare désormais les hauteurs des deux en-têtes en mode fenêtré, ainsi que
la géométrie du timer avant/après le retour.


## Complément 27/10 : boutons Paramètres superposés aux boutons Timer en fenêtre

L'en-tête des Paramètres fenêtrés reprend exactement la projection
1600 × 900 du Timer : même origine, même facteur homothétique, même marge
de droite et même hauteur. Les deux boutons de Paramètres occupent les
**deux dernières positions** du Timer : « Retour au timer » (largeur 168)
superposé à « Paramètres », « Plein écran » (largeur 246) superposé au bouton
homonyme du Timer. En plein écran, le texte de sortie existant reste
« Quitter plein écran ». La zone de réglages défile sous l'en-tête fixe,
et l'espace réservé n'a pas été ajouté deux fois. Tests de coordonnées
pour sept tailles de fenêtre et les deux modes de tournoi. Aucun autre
panneau ne doit être retouché.


## Retour initial et barre inférieure fenêtrée (27/10/2026)

- Au démarrage de l'application, **aucune séance n'a commencé** :
  masquer (visibilité et interaction) le bouton « Retour au timer »
  de la page Paramètres, tout en **réservant son emplacement** afin de
  ne pas déplacer le bouton « Plein écran » à droite.
- Dès qu'un timer a commencé, « Retour au timer » devient visible
  dans les paramètres. Si la séance est arrêtée, il disparaît.
- Le pied de page Paramètres en mode fenêtré reprend la hauteur physique
  exacte des **88 unités virtuelles** du pied de page Timer, multipliées
  par le même coefficient 16:9. Cela s'applique à l'ouverture,
  pendant un tournoi, Match ou Paires, et après des transitions.
- La miniature en cours reste un objet indépendant, superposé depuis
  l'angle inférieur gauche. **Aucune min-height historique** ne peut
  augmenter la hauteur de la barre pour loger cette miniature.
- Boutons de pied de page : même hauteur virtuelle et même taille de
  police que ceux du timer. Barre opaque ; pas de modification de la
  présentation plein écran ni des commandes du chronomètre.


## 27/10 — Centrage des commandes du timer entre l'heure et le tour

Pour MP4 et Tournoi par paires, l'espace effectivement libre sur la barre
inférieure se situe entre **le bord droit de l'heure** et **le bord gauche
du libellé de tour**. Le groupe de boutons doit occuper le centre exact de
cet espace : distance heure→premier bouton égale à distance dernier bouton→tour.
L'ancien centrage à 50 % de la largeur totale des 1600 pixels était faux quand
les étiquettes gauche et droite ont des largeurs différentes.

Le point médian est mesuré en coordonnées visibles, converti ensuite dans
les pixels virtuels (facteur homothétique unique). Il s'actualise après
l'affichage du tour, lors du changement de phase, et lors d'un redimensionnement
de fenêtre. Ni la position de l'heure ou du tour, ni leur taille, ni les dimensions
de la barre ne changent. Le contrôle dans Edge doit vérifier l'écart entre
les deux espaces (≤1.1 pixel projeté) dans les 2 formats, y compris les numéros
de tour à un et deux chiffres, le mode plein écran et les transitions.


## 27 octobre 2026 — stabilité de tous les boutons + proportions identiques

Un bouton invisible ne doit **jamais retirer sa place du groupe** : réserver
cinq positions fixes en fin de paramètres (Lancer/Timer 104, Arrêter 136,
Reset param. 154, Debug 106, Écrans tests 162), avec les mêmes intervalles
dans les deux états. Arrêter reste invisible et non cliquable au lancement,
mais son emplacement de 136 unités est toujours réservé ; l'espace avant
Reset param. reste 13 unités supplémentaires. Le groupe entier reste centré,
ainsi aucun bouton ne se déplace quand Lancer devient Timer ou quand Arrêter
apparaît. Le pied de page, la miniature et Quitter ne changent pas.

Le Timer est un seul stage 1600 × 900 redimensionné par homothétie. Les
anciennes règles CSS adaptatives pour des fenêtres larges de moins de
850 pixels ne doivent plus diminuer les polices ou espacements du TIMER.
La barre haute utilise 18px virtuels pour ses boutons, la barre basse 21px
virtuels, quels que soient la résolution et le mode plein écran. La taille
apparente change **uniquement** par le coefficient de projection 16:9.

Le test sous Edge compare les coordonnées **normalisées** du même timer
fenêtré, en plein écran et de retour en fenêtre, et vérifie les cinq
emplacements des paramètres avant/après démarrage, dans les deux formats.


## 27/10 — Cause racine des différences visibles fenêtré/plein écran

Les anciennes CSS `@media(max-width:980px)` et
`@media(max-width:760px)` forçaient l'heure du pied de page à
20/18 unités de police et le « TOUR x sur y » à 20/18 unités, avec
marges de 14 au lieu de 22. Comme le stage Timer entier est déjà
réduit homothétiquement de 1600×900 vers 812×456, ces règles réduisaient
une **seconde fois** les deux libellés en mode fenêtré : ils devenaient
minuscules par rapport aux boutons et au plein écran. L'override ciblé
`#timer #localTime` et `#timer #round` rétablit les tailles virtuelles
uniques et les positions gauche/droite à 22 unités.

Les tests précédents `q25(true)` dans la même fenêtre ne pouvaient pas
repérer l'erreur car ils ne changeaient pas la *largeur réelle* du viewport.
Désormais, un rendu fenêtré 812×456 et les autres tailles sont comparés
au **rendu séparé** de référence 1600×900, en normalisant leurs coordonnées
par le facteur de scale. Cela protège les dimensions de tous les éléments
et les polices du Timer, notamment l'heure et le numéro de tour.


## 27/10/2026 — Audit corrections 1 et 2 (point 3 laissé inchangé)

1. **Quitter / croix Windows / Alt+F4 / Échap en dehors du plein écran :**
   ouvrir le dialogue existant `exitConfirmOverlay`, sans fermer ni modifier
   le timer avant une confirmation explicite. **Non** ou **Échap** ferme le
   dialogue uniquement, en conservant la séance et le temps restant.
   La demande Win32 passe par `nativeConsumeCloseRequest` et la même
   fonction `q34()`. `q46()` refuse toute fermeture si le dialogue n'est
   pas ouvert. Le mécanisme de secours Win32 après 12 secondes, qui exige
   lui aussi une réponse explicite de l'utilisateur, n'est pas modifié.
2. **Temps entre tours en Paires :** synchroniser `s.between` et
   `st.roundBetween` lors de *tout* retour depuis les paramètres vers
   le timer actif (bouton Retour, bouton Timer du bas, touche F9,
   Échap, miniature). Enregistrer les réglages avant le retour.
   Ne jamais modifier `st.remaining`, `st.endAt`, `st.roundDuration`,
   `st.breakDuration`, `st.phase` ou `st.running` : la valeur mise à
   jour est utilisée pour les **prochains** changements de tour.
3. **Comportement des durées au redémarrage :** inchangé à la demande
   expresse de l'utilisateur. Le calcul standard `8 × temps par donne`
   reste la source des durées du nouveau tournoi.

Tests navigateur dédiés : annulation/confirmation fermeture, demande
Win32 simulée, cinq chemins de retour, conservation exacte des champs
chronométriques, et règle standard des huit donnes au lancement.


## 27 octobre — régression corrigée : fermeture par X et dimensions natives

La dimension d'ouverture ET minimum historique demandée est **812 × 640**.
La configuration native de WebView2 utilise cette paire en démarrage et en
`HintMin`; aucune recalibration du rectangle de fenêtre à un ratio 16:9
ne doit réduire sa hauteur au chargement ni aux changements de vue. Le
chronomètre reste une maquette 16:9 **intérieure** qui s'adapte à la fenêtre.
La fenêtre peut être agrandie librement horizontalement et verticalement,
mais ne peut devenir plus petite que son format d'ouverture.

Une demande WM_CLOSE déclenchée par la croix ou Alt+F4 ouvre directement
une boîte Windows Oui/Non. Non ne ferme rien; Oui ferme explicitement.
Cela remplace l'ancien accusé de réception JS asynchrone pouvant avaler
le clic sans rien afficher. Le bouton Quitter de l'interface reste branché
sur son dialogue HTML et `nativeExit` contourne le second dialogue natif
après confirmation. Le moteur de tournoi, les règles de sauvegarde, les
couleurs et la logique de minuterie ne sont pas modifiés.


## 28 octobre — ajustement de la hauteur native à la capture de référence

L'utilisatrice a fourni deux captures sur le même écran, mêmes positions
horizontales et même bord supérieur. La première (format demandé) a une hauteur
visible de 633 px sur le PNG, la seconde (ancienne ouverture) 605 px :
**écart exact +28 px**. On augmente uniquement `defaultWindowHeight` de
612 à **640** en conservant la largeur **812**. Le même couple est passé
à `WindowOptions` au lancement et à `SetSize(..., webview.HintMin)`
pour empêcher toute réduction au-dessous du format voulu.
Le rendu du timer, les bandes, la confirmation de sortie, le plein écran
et la mise à l'échelle restent inchangés dans cette correction.

## Miniature en plein écran — bordure des paramètres (29/10/2026)

**Essai isolé** sur `essai-mini-bas-gauche-bordure-menus-20261029`, après le rejet visuel de
`essai-mini-jusqua-colonne-raccourcis-20261029`. Conserver `main` comme
référence stable.

- Quand la séance est lancée et que les paramètres sont en plein écran,
  `#miniTimer` reste **à gauche = 0 et en bas = 0** du viewport.
- Sa bordure droite coïncide **exactement** avec la bordure gauche du bloc
  `#settings .tournamentCard` (« Tournoi »), commune aux cartes du formulaire.
  La largeur est calculée avec `getBoundingClientRect().left`, pas depuis
  les boutons du pied de page ni depuis les raccourcis clavier.
- `aspect-ratio:16/9` détermine la hauteur ; aucune limite de hauteur liée
  à la barre inférieure, ni remontée artificielle au-dessus de cette barre.
- La barre d'actions, le timer principal, les transitions, la fenêtre de
  paramètres fenêtrée et sa miniature existante restent inchangés.
- Vérifier la géométrie en Paires et MP4, en 960×600, 1280×720, 1650×928
  et 1920×1080, la réversibilité fenêtré ↔ plein écran, et une capture Edge
  à 1650×928. Le test navigateur ne remplace pas la validation de l'EXE Windows.

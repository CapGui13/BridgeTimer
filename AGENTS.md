# Instructions impératives pour toute intervention — BridgeTimer

Ce fichier est destiné aux assistants et développeurs qui interviennent sur ce dépôt.
**Le lire AVANT tout changement du timer, à chaque intervention, même minime.**
Lire ensuite **UI_LAYOUT_CONTRACT.md**, puis les tests **checks/test_synced_ui.js**.
Ne pas considérer les instructions de chats précédents comme suffisantes.

## Contrat non négociable

1. **Homothétie fenêtré ↔ plein écran.** Une seule scène de référence de
   1600 × 900, un seul coefficient uniforme pour tous les éléments (titre,
   club, chrono, boutons, espacement, messages, pied de page, écrans spéciaux).
   Pas de variation arbitraire entre les deux modes.
2. **Parité court ↔ long.** Les grands chiffres MM:SS et H:MM doivent conserver
   la même taille de police, la même bande verticale et le même écart visuel
   sous le nom de l'évènement ; les éléments communs ne bougent pas quand
   on change de format. Les seules différences prévues sont la composition
   du temps et les secondes du format long à **56 %** de la taille principale.
   Le choix du format repose sur la durée **initiale** du tour.
3. **Source de vérité commune.** Une modification de taille, position ou
   espacement communs doit se propager à la fois en court et en long, en
   fenêtre et en plein écran. Ne pas faire quatre retouches distinctes.
   Certaines formules actuelles de `fc()` sont encore séparées : les
   centraliser lorsqu'on touche à un paramètre partagé, sans modifier
   les caractéristiques déjà validées.

## Procédure obligatoire — chaque modification

- **Avant :** lire `UI_LAYOUT_CONTRACT.md`, inspecter `updateStage()`,
  `fc()` et les tests concernés ; établir ce qui doit changer et les parties
  qui doivent rester *strictement identiques*.
- **Pendant :** modifier le minimum, préférer une valeur ou fonction commune,
  maintenir les exceptions explicitement demandées, ne jamais détourner un
  ajustement d'un format pour réparer l'autre.
- **Après :** lancer les tests du dépôt, vérifier visuellement si le rendu a
  changé en court et long ainsi qu'en fenêtre et plein écran, aux résolutions
  appropriées. Une compilation Windows réussie ne prouve pas le rendu natif.
- **Livraison :** indiquer exactement les modifications, celles qui ont été
  protégées, les tests réellement effectués et ce qui demeure non vérifié.
  Garder un retour arrière identifié.

**Stopper la livraison si l'une de ces règles n'est pas satisfaite.**
Ne modifier les règles qu'à la demande explicite de l'utilisateur. Aucun
commentaire ou test ne garantit à lui seul l'apparence Windows : demander
une vérification sur l'EXE réel lorsque nécessaire.

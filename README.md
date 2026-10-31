# BridgeTimer — chronomètre de tournoi de bridge

**Deux éditions Windows et une version web, avec un seul moteur de chronométrage.**

## ▶ Utiliser BridgeTimer directement dans le navigateur

### [Ouvrir BridgeTimer Light en ligne](https://capgui13.github.io/BridgeTimer/)

La version web démarre **sans installation** dans une fenêtre du navigateur. Elle fonctionne avec Chrome, Edge, Firefox ou Safari récents, sous réserve des fonctionnalités prises en charge. Pour une projection de tournoi, le bouton **Plein écran** est disponible.

> Le lien `github.com/CapGui13/BridgeTimer` reste obligatoirement l'interface du dépôt GitHub : GitHub ne permet pas de la remplacer par une application. L'application web est publiée sur **GitHub Pages**, à l'adresse ci-dessus.

## Télécharger pour Windows

| Édition | Télécharger | Contenu |
| --- | --- | --- |
| **BridgeTimer Complet** | [BridgeTimer.exe — version complète](https://github.com/CapGui13/BridgeTimer/releases/download/bridge-timer-preview-20261031-fin-tour-chrono-identique/BridgeTimer.exe) | Tous les réglages, couleurs et écrans tests |
| **BridgeTimer Light** | [BridgeTimer.exe — version épurée](https://github.com/CapGui13/BridgeTimer/releases/download/bridge-timer-edition-epuree-20261031/BridgeTimer.exe) | Interface simplifiée, sans accès aux couleurs ni aux écrans tests |

Les deux fichiers sont des **EXE portables** sous Windows, sans installateur. Ils ont été compilés et vérifiés sous Windows Edge / WebView2 ; ils restent disponibles séparément. Les exécutables sont actuellement non signés (Windows SmartScreen peut demander une confirmation).

La version **Complète** n'a pas été remplacée par la version Light : elle reste la référence pour les réglages avancés.

## Différence entre Complète et Light

Les deux éditions conservent les mêmes fonctions de tournoi : Paires et Match par 4, choix du temps, position de départ, changements de tour, messages temporaires, avertissements, pause/reprise, plein écran et mini-timer. Le chrono conserve ses deux formats, l'agrandissement visuel ×1,15 au repos, la réduction maximale de 10 % lorsqu'une annonce apparaît, et l'animation de 420 ms.

La version **Light** supprime **de l'interface utilisateur** le bouton de personnalisation des couleurs ainsi que l'accès aux écrans tests, y compris en mode Debug. Les composants internes de compatibilité restent présents, afin de ne pas modifier le moteur ni les mécanismes de sauvegarde. Le bloc des paramètres est nommé « Informations affichées » et conserve le club et l'événement. Les couleurs enregistrées antérieurement restent appliquées sur l'édition Windows Light, mais ne peuvent plus être modifiées depuis cette interface.

## Version web : précautions utiles

- Les paramètres et les éventuelles sauvegardes de séance sont conservés localement **dans le navigateur de l'appareil** (stockage local), indépendamment des données de l'EXE Windows. Ne pas utiliser la navigation privée pour conserver les réglages.
- Les API natives Windows de WebView2 ne sont pas disponibles sur le web. L'anti-veille repose, si elle est autorisée, sur la fonctionnalité du navigateur (Screen Wake Lock) et non sur l'anti-veille Windows de l'EXE.
- L'option « Quitter » de la version web revient au dépôt GitHub ; l'application Windows continue de fermer sa propre fenêtre.
- Le son, le plein écran et la veille peuvent être soumis aux permissions et aux politiques du navigateur. Pour arbitrer une épreuve longue, tester sur le PC et l'écran de projection prévus.

## Organisation du dépôt

| Fichier ou branche | Rôle |
| --- | --- |
| [`timer.html`](timer.html) sur `main` | **Source de l'édition Windows Complète** |
| [`index.html`](index.html) sur `main` | **BridgeTimer Light pour GitHub Pages** — page d'entrée web |
| [`edition-complete-20261031`](https://github.com/CapGui13/BridgeTimer/tree/edition-complete-20261031) | Point de sauvegarde de la Complète avant publication web |
| [`edition-epuree-sans-couleurs-sans-tests-20261031`](https://github.com/CapGui13/BridgeTimer/tree/edition-epuree-sans-couleurs-sans-tests-20261031) | Source Windows de l'édition Light |
| [`.github/workflows/pages-light.yml`](.github/workflows/pages-light.yml) | Tests navigateur et publication automatique du site |
| [`UI_LAYOUT_CONTRACT.md`](UI_LAYOUT_CONTRACT.md) | Règles de rendu à préserver : homothétie 1600 × 900, parité court/long |

La publication web est distincte de la compilation Windows. Une mise à jour de `index.html` sur `main` déclenche la vérification en navigateur puis le déploiement GitHub Pages. Un changement du chrono complet suit les vérifications et le circuit de compilation Windows.

## Construire l'application Windows

Les sources Go/WebView2 et le moteur HTML sont inclus. La compilation officielle utilise GitHub Actions sur Windows avec Go 1.24, les tests de géométrie et de rendu Microsoft Edge, les tests Go, et une vérification du HTML embarqué dans l'EXE.

La référence visuelle est une scène **1600 × 900** homothétique en mode fenêtré et plein écran. Les grands chiffres des formats court et long partagent leur taille et leur position. Lire impérativement [AGENTS.md](AGENTS.md) et [UI_LAYOUT_CONTRACT.md](UI_LAYOUT_CONTRACT.md) avant toute modification du rendu.

## Licence, confidentialité et distribution

- [Licence MIT](LICENSE)
- [Mentions des dépendances](THIRD_PARTY_NOTICES.md)
- [Confidentialité](PRIVACY.md)
- [Signature du logiciel Windows](CODE_SIGNING_POLICY.md)

Pour supprimer l'application Windows, effacer le fichier `BridgeTimer.exe`. Pour retirer également les préférences locales de WebView2, supprimer `%LOCALAPPDATA%\BridgeTimerWebView2`.

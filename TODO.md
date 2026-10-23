# Maelstrom — Feuille de route

Idees d'evolution, dictees puis mises en forme ici. Document en francais (le
code et les identifiants restent en anglais). Une entree livree est retiree
(l'historique git la garde).

Convention : `- [ ] (priorite) titre — courte note`, priorite `P1` (bientot) /
`P2` / `P3` (un jour). On regroupera par rubrique quand la liste grossira.

## A faire

- [ ] (P2) **Succes / achievements par secteur** — des defis debloquables,
  plusieurs par secteur. Exemples de criteres : liberer sans mourir, sans etre
  touche (no-hit), sous un temps donne, tuer l'Intercepteur sans qu'il se
  referme, ramasser N conteneurs, finir avec une arme precise.
  - *A definir* : stockage dans la meta (`meta.json`, donc web via localStorage)
    avec montee de `META_VERSION` ; detection au bon moment
    (`game.py` / `combat.py`, a la cle d'un secteur) ; affichage (pastilles sur
    les cartes de secteur, bilan a la victoire, ou un ecran dedie) ; noms et
    descriptions dans les locales ; eventuelle petite recompense en meta-alliage.

- [ ] (P2) **Mode de difficulte** — quatre crans, nommes comme une echelle de
  menace thargoide : **Scout** (le plus facile) -> **Interceptor** -> **Hunter**
  -> **Titan** (le plus dur). Chaque cran ajuste des multiplicateurs : PV et
  degats ennemis, cadence de tir, generosite des butins, peut-etre survie du
  joueur et nombre de coeurs des boss.
  - *A definir* : table des multiplicateurs dans `settings/balance.py`, appliquee
    la ou servent `LEVEL_HP_SCALE` / `LEVEL_DAMAGE_SCALE` (`enemies.py`,
    `enemy_fire`) et le tirage des conteneurs ; choix du cran (accueil ou
    Options, ou nouvel ecran), memorise dans les prefs ; noms et descriptions
    dans les locales (comme `difficulty_name` de purr-tage) ; interaction avec
    les records et les succes par secteur (record par difficulte ?).

- [ ] (P1) **Boss final Titan** (apres le secteur 4) — le vrai climax de la
  campagne : aujourd'hui la victoire tombe quand l'Hydre meurt, le Titan devient
  l'affrontement ultime qui suit. Reference : `docs/img_src/TITAN.jpg`.
  - *Direction visuelle* (d'apres l'image) : un enorme coeur spherique herisse
    d'epines (une rosace demesuree), des **vents orange** qui pulsent, plusieurs
    **pods rouges lumineux** servant de points faibles, et de longues
    **tentacules articulees** qui s'etirent et balaient. Il ecrase les
    Intercepteurs par la taille (remplit une large part de l'ecran).
  - *Gameplay* : multi-phases (detruire les pods rouges un par un), rayon bien
    plus grand, nouveaux motifs d'attaque (balayage de tentacules, crachat de
    caustique, lachers d'essaims).
  - *A definir* : entree `titan` dans `BOSSES` (`balance.py`) + `BOSS_LOOKS`
    (`ui.py`) ; sans doute une **nouvelle classe** (ou extension d'`Interceptor`)
    pour les tentacules articulees ; 5e rencontre et flux de campagne
    (`main.py` / `loop.py`, la victoire passe apres le Titan) ; nom et texte de
    victoire dans les locales (mettre a jour `victory.sub`) ; lien avec le cran
    de difficulte « Titan ».

- [ ] (P1) **Boss : nouveaux motifs et petales a cibler** (retour de jeu,
  rapports `20261021-163941` « changer le paterne des boss » et
  `20261021-164230` « utiliser le paterne des thargo d'elite avec les petals a
  cibler ») — aujourd'hui les quatre Intercepteurs se jouent pareil : une
  alternance minutee blinde / expose (`BOSS_ARMORED_TIME`,
  `BOSS_EXPOSED_TIME`) et une rotation de tirs (`aimed`, `radial`, `swarm`).
  - *Petales a cibler* (comme les Thargoides d'elite d'Elite Dangerous) : les
    petales deviennent des cibles a detruire pour ouvrir le coeur, au lieu d'un
    minuteur ; un coeur detruit referme la rosace avec de nouveaux petales.
  - *Motifs* : un jeu de motifs propre a chaque Intercepteur (Cyclops, Basilisk,
    Medusa, Hydra), qui change d'un coeur a l'autre.
  - *A definir* : petales avec leurs PV dans `Interceptor` (`enemies.py`) et
    collisions par petale dans `combat.py` ; nombre de petales et PV dans
    `BOSSES` (`balance.py`) ; lecture claire a l'ecran (petale touche, petale
    detruit) ; lien avec le **Titan** et ses pods rouges, qui suivent la meme
    logique de points faibles.

- [ ] (P2) **Campagne etendue sur une carte de la Voie lactee** (retour de jeu,
  rapport `20261021-164337`) — « plus de niveaux : utiliser la carte de la voie
  lactee decoupee par secteur x N niveaux pour repousser l'invasion des xeno ».
  Aujourd'hui, 4 secteurs en ligne (`LEVELS`).
  - *A definir* : ecran de carte galactique a la place de la liste des secteurs
    (`menu.sectors()`) ; regions (Pleiades, Merope, Oracle...) contenant chacune
    N niveaux et un boss ; progression de l'invasion sur la carte (zones
    reprises / perdues) ; stockage dans la meta (`unlocked`, `best`, `deaths`
    passent par region, montee de `META_VERSION`) ; generation des vagues pour
    beaucoup plus de niveaux sans tout ecrire a la main.

- [ ] (P2) **Loots et ameliorations** (retour de jeu, rapport `20261021-164639`) —
  « avoir des loots et des ameliorations ». Constat dans `saves/meta.json` : en
  une session, le hangar est presque au maximum (coque, cadence, degats,
  bouclier a 5), il reste 896 de meta-alliage sans rien a acheter, et une seule
  mort sur la campagne. La progression s'epuise trop vite.
  - *A definir* : butins varies laches par les ennemis et les boss (pieces,
    modules) en plus du meta-alliage ; nouvelles ameliorations au hangar, ou des
    paliers au-dela des `max` actuels de `HANGAR` ; courbe de couts
    (`HANGAR_GROWTH`) ; lien avec le **Mode de difficulte**, qui donnerait une
    raison de rejouer avec un hangar plein.

- [ ] (P3) **Sites Guardians : technologies et evolution du vaisseau** (retour de
  jeu, rapport `20261021-164701`) — « ajouter des donjons guardians pour recup
  des techno et faire evoluer le ship dans le hangar ». Des niveaux a part,
  dans les ruines Guardians, ou l'on recupere des technologies.
  - *A definir* : forme du niveau (exploration plutot que defilement, gardiens
    sentinelles) ; technologies obtenues (nouvelles armes, modules) qui font
    evoluer le vaisseau au hangar au-dela des ameliorations chiffrees ; place sur
    la **carte de la Voie lactee** ; suite naturelle de **Loots et
    ameliorations**.

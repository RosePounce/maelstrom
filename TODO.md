# Maelstrom — Feuille de route

Idees d'evolution, dictees puis mises en forme ici. Document en francais (le
code et les identifiants restent en anglais). Coche `[x]` une entree livree.

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
  l'affrontement ultime qui suit. Reference : `docs/TITAN.jpg`.
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

## Fait

- [x] (P3) **Multijoueur a 2 en LAN** — branche `feature/coop-lan`, **teste et
  valide sur deux machines**. **Cooperatif**, desktop seulement (carte
  « Coop LAN » de l'accueil, absente sous pygbag).
  - **Hote autoritaire** plutot que lockstep : l'hote simule comme en solo avec
    un 2e vaisseau pilote par le reseau, et envoie un instantane JSON par image
    (`session/coop.py`) ; le client envoie ses entrees, dessine et rejoue les
    effets (`Combat.emit`). Aucune purge du RNG necessaire. Transport repris de
    purr-tage (`maelstrom/net.py` : TCP 50517 + annonce UDP 50518).
  - **Salon** `menu.lobby()` : heberger, liste des parties annoncees, saisie
    d'IP ; poignee de main `hello` / `welcome` avec numero de protocole.
  - **Regles** : vaisseau abattu de retour apres `COOP_RESPAWN` s, essai perdu
    quand les deux sont abattus, Thargoides visant le plus proche, pause qui ne
    fige rien, seul l'hote decide apres une mort ou une victoire.
  - **Meta** : chacun son vaisseau, son hangar, ses equipements ; meta-alliage
    de l'equipe verse aux deux ; records et deblocages solo intouches ; l'hote
    choisit parmi ses secteurs liberes.

- [x] (P2) **Musique synthwave** — leve le « pas de son ». `maelstrom/audio.py`
  streame une piste a la fois (`pygame.mixer.music`), table `MUSIC` et assets
  `.ogg` par secteur / boss / jingle, volume dans Options, mise en pause sur
  perte de focus. Un changement de piste n'est plus une coupure seche mais un
  pont fondu (`MUSIC_CROSSFADE` : fondu de sortie puis d'entree, un seul flux) :
  plus d'a-coup a l'arrivee de l'Intercepteur (retour de jeu `20261021-124702`).
  *Effets sonores ecartes* : un essai de SFX proceduraux noyait la musique
  (retour `20261022-202900`) ; le jeu reste a la musique seule.

- [x] (P1) **F8 partout** — le formulaire de rapport s'ouvre a F8 sur chaque
  ecran hors secteur (accueil, vaisseau, secteurs, hangar, options, salon),
  plus seulement en partie. Le formulaire est sorti dans `maelstrom/bugform.py`
  (classe `BugForm`, utilisable sans instance `Game`) ; `session/bug_form.py`
  n'en est plus que l'adaptateur du jeu (qui repasse par la pause a la
  fermeture). Chaque boucle de `menu.py` appelle `_bug_intercept` / `_bug_overlay` ;
  le rapport note l'ecran d'ou il part (`screen: <nom>`). Bureau seulement.

- [x] (P1) **Remontee des bugs vers un relais Cloudflare** — sur le modele de
  purr-tage : `maelstrom/bugsend.py` (envoi HTTPS en tache de fond, boite
  `saves/bugs/outbox/` rejouee au lancement, `send.log`, `certifi`), une case
  « Envoyer le rapport » dans le formulaire (consentement memorise dans
  `prefs.json`), `BUG_REPORT_URL` dans `settings/` (depassable par
  `MAELSTROM_REPORT_URL`, actif seulement une fois empaquete). Le relais est un
  Cloudflare Worker dans `relay/` (Discord), a deployer sur le compte
  RosePounce. Bureau seulement.

- [x] **Ecran du choix du vaisseau : mise en page** (retour de jeu, rapport
  `20261021-163755`) — le libelle « Lancer la campagne (Entree) » debordait de son
  bouton (298 px pour 220) ; le sous-titre passait sous les cartes ; la silhouette
  du Type-10 sortait de sa carte et du nom ; « Mamba » etait ecrit plus gros que
  les autres noms ; les boutons recouvraient la ligne de version. Cartes
  descendues sous le sous-titre, silhouettes mises a l'echelle de leur cadre
  (`_draw_ship_shape`), une seule taille de nom, boutons elargis et remontes.

- [x] (P1) **Choix du vaisseau de depart** — ecran avant la campagne (`menu.ships()`),
  4 chasseurs aux profils distincts : **Krait Mk II** (polyvalent), **Alliance
  Chieftain** (agile, coque solide), **Type-10 Defender** (tank lent, hitbox
  elargie), **Mamba** (glass cannon rapide). Profils dans `SHIPS`
  (`balance.py`), silhouettes dans `SHIP_SHAPES` (`player.py`), stats / hitbox /
  vitesse / arme de depart appliquees par `Ship`, choix memorise dans la meta
  (`meta["ship"]`), noms et descriptions dans les locales (`ships.*`).

- [x] **Suivi souris : decalage sur les gestes rapides** (retour de jeu) — le
  drag que le plafond ne consommait pas etait jete a chaque frame ; il est
  desormais conserve (`Ship.update`) et rattrape sur les frames suivantes, et
  `DRAG_SPEED_CAP` passe de 1.8 a 3.5. Plus de decrochage permanent du pointeur.

- [x] **Plus d'info sur les bonus / malus** (retour de jeu) — **legende dans la
  pause** (deux colonnes BONUS / MALUS avec une description par conteneur) et
  **effet chiffre dans le HUD** (« SURCHARGE x1,7 », « CAUSTIQUE -coque »).
  Descriptions `info` et token `tag` dans les locales (`pickups.*`), aides
  `i18n.pickup_info` / `pickup_tag`, legende dans `Hud._draw_legend`.

- [x] **Glitch du boss a l'arrivee** (retour de jeu) — l'Intercepteur sautait
  vers le bas juste avant le combat : en quittant l'etat `enter`, son `y` passait
  d'un coup a `0.47H + sin(self.t*0.55)*0.26H`, or `self.t` avait defile pendant
  toute l'entree (phase du sinus arbitraire). Corrige par une horloge de
  mouvement `move_t` demarrant a 0 a l'arrivee, avec la position d'entree alignee
  sur le centre du balancement : transition sans saut (0 px).

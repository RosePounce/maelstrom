# Maelstrom — Feuille de route

Idees d'evolution, dictees puis mises en forme ici. Document en francais (le
code et les identifiants restent en anglais). Coche `[x]` une entree livree.

Convention : `- [ ] (priorite) titre — courte note`, priorite `P1` (bientot) /
`P2` / `P3` (un jour). On regroupera par rubrique quand la liste grossira.

## A faire

- [ ] (P2) **Son et musique synthwave** — leve le « pas de son » actuel. Deux
  volets :
  - **Effets** : tir, impacts, explosions, ramassage bonus / malus, alerte
    Intercepteur, coeur detruit, clics d'interface.
  - **Musique** : nappes synthwave en fond, variant par secteur et montant d'un
    cran au boss.
  - *A definir* : assets audio embarques **ou** synthese procedurale (rester
    coherent avec le « zero asset, tout dessine » du projet) ; contraintes
    pygbag (audio navigateur, prechargement, mixer en async, deblocage au
    premier clic) ; reglage volume / coupure dans les Options (memorise comme la
    langue) ; mise en sourdine quand l'onglet ou la fenetre perd le focus.

- [ ] (P2) **Succes / achievements par secteur** — des defis debloquables,
  plusieurs par secteur. Exemples de criteres : liberer sans mourir, sans etre
  touche (no-hit), sous un temps donne, tuer l'Intercepteur sans qu'il se
  referme, ramasser N conteneurs, finir avec une arme precise.
  - *A definir* : stockage dans la meta (`meta.json`, donc web via localStorage)
    avec montee de `META_VERSION` ; detection au bon moment
    (`game.py` / `combat.py`, a la cle d'un secteur) ; affichage (pastilles sur
    les cartes de secteur, bilan a la victoire, ou un ecran dedie) ; noms et
    descriptions dans les locales ; eventuelle petite recompense en meta-alliage.

- [ ] (P3) **Multijoueur a 2 en LAN** (le plus gros chantier) — sur le modele de
  purr-tage. A priori **cooperatif** : deux chasseurs contre les Thargoides
  (versus a decider). Reutiliser le transport de purr-tage (`net.py` : TCP +
  annonce LAN en UDP) et son `lockstep.py`.
  - *Gros point dur* : purr-tage est **deterministe** (lockstep, aucun etat ne
    traverse le reseau, pas de RNG global, pas de `hypot`/trigo, entites
    renumerotees). Maelstrom ne l'est **pas** aujourd'hui : les vagues sont deja
    semees par secteur (bon depart), mais les butins, les particules et la gigue
    des ennemis passent par le `random` global. Un vrai lockstep demande de
    purger ce RNG (RNG seme partage), de fixer le pas de simulation et de
    bannir le non-deterministe. Alternative plus simple mais qui s'ecarte de
    purr-tage : un hote autoritaire qui diffuse l'etat.
  - *A definir* : co-op vs versus ; ecran de lobby / decouverte LAN dans
    `menu.py` ; entrees serialisees en ordres ; **desktop seulement** (le
    reseau LAN n'existe pas dans le navigateur pygbag) ; comment la meta, le
    hangar et le choix du vaisseau se partagent a deux.

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

- [ ] (P1) **F8 partout** — pouvoir signaler un bug (F8) a n'importe quelle etape,
  y compris dans les menus (accueil, choix du vaisseau, secteurs, hangar, options),
  pas seulement en partie. Aujourd'hui F8 n'ouvre le formulaire que dans un secteur
  (`loop.play`) ; le filet anti-plantage couvre deja les menus, mais pas le
  signalement manuel.
  - *A definir* : sortir le formulaire de `session/bug_form.py` pour qu'un ecran
    de menu (sans instance `Game`) puisse l'ouvrir ; variante de
    `bugreport.write_report` sans partie (ecran + description + quel ecran + meta,
    comme le fait deja `report_crash` avec « game: none (menus) ») ; chaque boucle
    d'ecran de `menu.py` gere F8 et fige l'ecran pendant la saisie ; **bureau
    seulement** (comme l'existant).

- [ ] (P1) **Remontee des bugs vers un relais Cloudflare** — sur le modele de
  purr-tage (`relay/` et `purrtage/bugsend.py`), pour les versions installees
  (AppImage, installeur Windows) produites par `.github/workflows/packages.yml` :
  aujourd'hui un rapport F8 ou un plantage reste dans le dossier du joueur
  (`saves/bugs/`, ou `~/.local/share/maelstrom/bugs/` / `%APPDATA%\Maelstrom\bugs\`
  une fois installe) et ne nous parvient jamais.
  - *Principe* : le jeu ne connait qu'une adresse, celle d'un Cloudflare Worker
    (offre gratuite, stockage Workers KV) qui verifie le rapport, en garde une
    copie et le transmet aux services branches (GitHub Issues, Discord,
    e-mail) ; aucune cle de service dans le jeu, dont le code est public.
  - *Cote jeu* : envoi HTTPS en tache de fond apres l'ecriture sur disque
    (`bugreport`), boite d'envoi `outbox/` rejouee au lancement suivant (rien
    perdu hors connexion), journal `send.log` ; certificats `certifi` a
    embarquer dans `packaging/maelstrom.spec` ; notification du resultat dans le
    formulaire ; consentement du joueur avant envoi ; **bureau seulement**.
  - *A definir* : reprendre le Worker de purr-tage tel quel ou un deploiement
    dedie ; URL du relais dans `settings/` ; commit de la version installee
    (`bugreport.git_commit` renvoie « unknown » hors depot : l'injecter au
    build) ; lien avec **F8 partout** ci-dessus.

## En cours

## Fait

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

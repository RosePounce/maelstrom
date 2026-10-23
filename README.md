# Maelstrom

Un shoot'em up synthwave où vous repoussez une invasion extraterrestre, seul ou à deux.

Aux commandes de votre chasseur, foncez à travers quatre secteurs de l'espace — une ceinture d'astéroïdes baignée de néons, les ruines d'une station, une nébuleuse glacée, puis le cœur du Maelstrom.
Chaque secteur se termine par un affrontement contre un boss colossal en forme de fleur mécanique, qu'il faut apprendre à percer.

C'est un jeu « on meurt, on comprend, on recommence » : chaque run est une partie de bras de fer avec des vagues d'ennemis, des tirs à esquiver et des pièges à éviter. Ramassez des bonus (boucliers,
missiles à tête chercheuse, surcharge d'armes…), méfiez-vous des pièges qui rongent votre coque ou brouillent votre vaisseau, et améliorez peu à peu votre hangar entre deux tentatives.

Ce qui vous attend :
🎮 4 secteurs aux ambiances uniques
🛸 4 vaisseaux aux styles bien différents : polyvalent, agile, tank, ou rapide mais fragile
🔫 3 familles d'armes qui montent en puissance (laser rapide, canon à fragmentation, rail perforant)
🤝 Coop à deux en réseau local — affrontez l'invasion côte à côte
🎵 Une bande-son synthwave
🌌 Direction artistique néon rétro-futuriste
💻 Jouable sur ordinateur

Prenez les commandes. Les Pléiades comptent sur vous.

## Lancer le jeu

```bash
pip install -r requirements.txt      # pygame (Python < 3.14) ou pygame-ce (3.14+)
python main.py
```

Dans le navigateur, via **pygbag** (depuis CE dossier, qui porte `pygbag.ini`) :

```bash
cd maelstrom
pygbag --build --app_name maelstrom --title "Maelstrom" --icon assets/favicon.png .
pygbag .                  # idem, mais sert sur http://localhost:8000
```

`F11` bascule fenetre <-> plein ecran partout. `Echap` ou `P` en partie ouvre la
pause ; `Echap` a l'accueil demande confirmation avant de fermer (bureau).
**`F8`** ouvre le formulaire de rapport de bug sur tous les ecrans, en partie
comme dans les menus (bureau seulement, voir « Rapports de bug (F8) »).

## Le jeu

**Controles.** Deplacement aux fleches, `ZQSD` ou `WASD` (lus en continu, donc
azerty et qwerty sans reglage), ou en **glissant** a la souris / au doigt : le
vaisseau suit le **mouvement** du pointeur (relatif, le doigt ne cache jamais le
vaisseau), plafonne a `DRAG_SPEED_CAP` fois sa vitesse. **Tir automatique.**
`Espace` / `X` ou le bouton rond `AX` : une paire de **missiles AX** a tete
chercheuse (une unite de stock). `Entree` / `R` sur l'ecran de mort ou de
victoire : la premiere action.

**Vaisseau** (`maelstrom/player.py`). Coque et bouclier ; le bouclier encaisse
d'abord et se recharge apres `SHIELD_DELAY` sans coup. Hitbox volontairement
petite (`SHIP_HITBOX`, le point blanc au centre), grace de `HIT_INVULN` apres un
coup. Il ne depasse pas `PLAY_RIGHT` (72 % de la largeur) : il garde de la vue
devant lui.

**Armes principales** (`WEAPONS`, 5 niveaux) : laser a impulsion (rapide,
canons en eventail), canon a fragmentation (gerbe courte portee), canon a rails
(lent, traverse tout). Un **module d'arme** ramasse **defile** entre les trois
(`CAPSULE_CYCLE`) : ce qu'il montre a l'instant ou on le prend est ce qu'on
obtient. Meme arme : +1 niveau ; autre arme : on change en **gardant** le
niveau ; deja au maximum : du meta-alliage.

**Conteneurs** (`maelstrom/pickups.py`). Un ennemi detruit lache un conteneur
avec la chance `drop` de son type (x `Recuperation`). Categorie selon
`DROP_SPLIT` :
- **bonus** (hexagone cyan, attire par l'aimant) : module d'arme, banque de
  cellules (bouclier plein), limpet de reparation (+coque, **nettoie la
  caustique**), missiles AX, surcharge (cadence x1,7), meta-alliage ;
- **malus** (eclat vert thargoide, **jamais attire**) : caustique (la coque
  fond, bouclier ou pas), onde d'arret (ni tir, ni recharge, vaisseau lent),
  surchauffe (cadence /2), brouillage (vaisseau lent, image dechiree) ;
- **conteneur inconnu** (`?` violet) : bonus a `MYSTERY_BONUS`, sinon malus ;
  son meta-alliage vaut triple.
Les effets en cours s'affichent en haut a gauche, avec leur duree.

**Thargoides** (`maelstrom/enemies.py`, `ENEMIES`). Chaque type est une methode
`_<type>` : essaim (Thargons en ligne, en vague ou en V, certains **s'inflechissent**
vers le joueur, cle `home`), scout (sinusoide, tir vise), maraudeur (s'aligne,
**trait rouge** d'avertissement, puis charge), berserker (stationne et tire en
eventail), mine caustique (laisse un **nuage** qui tache la coque), asteroide
(obstacle destructible). Les PV et degats montent par secteur
(`LEVEL_HP_SCALE`, `LEVEL_DAMAGE_SCALE`).

**Intercepteurs** (`Interceptor`, `BOSSES`) : quatre petales autour d'un coeur.
Il alterne **blinde** (petales fermes, ne prend que `BOSS_ARMOR` des degats) et
**expose** (coeur ouvert, degats pleins, il tire moins vite : c'est le tour du
joueur). Chaque coeur detruit : **onde d'arret** sur le vaisseau (reduite par
les amortisseurs), etourdissement sans degats, deux bonus. Ses attaques
tournent dans `patterns` : `aimed`, `radial`, `spiral`, `swarm`, `mines`.
Cyclope 2 coeurs, Basilic 3, Meduse 4, Hydre 5.

## Die and retry

**Un secteur se joue toujours pareil.** `maelstrom/levels.py` ecrit ses vagues
avec un generateur **seme** (`seed` du secteur) a partir des poids `patterns` :
memes ennemis, memes moments, a chaque essai. Les **butins**, eux, restent
aleatoires. Ajouter un motif de vague : une fonction `(t, rng) -> [Spawn]` dans
`levels.py` et sa cle dans la table `patterns` d'un secteur.

**Phases d'un essai** (`Game.phase`, voir `maelstrom/session/game.py`) : `play`
(les vagues jusqu'a `duration`), `warning` (« Intercepteur en approche »),
`boss`, `boss_dying` (le vaisseau ne peut plus etre touche), `dead`, `cleared`.

**Mourir ne quitte pas la boucle.** `Reessayer` relance un essai dans le meme
`Game` (`start()`), sans chargement. Le **point de reprise** est pris a l'entree
en `warning` : l'equipement du vaisseau a cet instant (`checkpoint`). Mort apres
lui, l'ecran propose « Reprendre a l'Intercepteur » (Entree) ou « Depuis le debut
du secteur ».

**Ce qui se garde.** L'equipement (arme, niveau, missiles) passe d'un secteur
au suivant quand on le libere, et il est **memorise a l'entree** de chaque
secteur (`loadouts` de la meta) : rejouer un secteur repart avec ce qu'on avait
en y entrant, pas avec ce qu'on a perdu en mourant. Les missiles ne descendent
jamais sous `MISSILE_START` + la soute du hangar. Coque et bouclier repartent
pleins a chaque essai.

**Meta-alliage et hangar.** Chaque ennemi donne du meta-alliage (`alloy`), les
Intercepteurs aussi. Il est **verse a la meta** a la mort, a la victoire et a
toute sortie (`Game.bank()`) : rien de ce qui a ete ramasse n'est perdu. Le
**hangar** (`menu.hangar()`, table `HANGAR`, prix `hangar_cost`) l'echange
contre des ameliorations permanentes : coque, bouclier, recharge, degats,
cadence, soute AX, aimant, amortisseurs de malus, recuperation (chance de
butin). On y va depuis l'accueil, ou depuis l'ecran de mort ou de victoire :
apres le hangar, la partie reprend sur le secteur suivant (victoire) ou le meme
(mort).

## Coop LAN (2 joueurs)

**Bureau seulement** (une page pygbag n'a pas de sockets) : la carte « Coop LAN » de l'accueil
n'apparait pas dans le navigateur. Deux chasseurs cooperent contre les Thargoides.

**Deroulement.** Chacun choisit son vaisseau, puis le salon : l'un **heberge** (il annonce sa partie
en UDP sur le reseau local et affiche son adresse), l'autre la voit dans la liste ou tape l'adresse
IP de l'hote. Une fois relies, l'hote choisit le secteur parmi ceux qu'**il** a liberes. Ports :
TCP 50517 et UDP 50518 (`maelstrom/net.py`), a ouvrir dans le pare-feu si besoin.

**Hote autoritaire, pas de lockstep.** Le jeu n'est pas deterministe (le `random` global pilote
butins, etincelles et gigue des ennemis) : au lieu du lockstep de purr-tage, l'hote simule le secteur
exactement comme en solo, avec un second vaisseau pilote par le reseau, et envoie a chaque image un
**instantane** de tout le secteur (`session/coop.py`, quelques Ko en JSON). Le client ne simule rien :
il envoie ses entrees (direction, glisser, missiles), dessine le dernier instantane et **rejoue les
effets** que l'hote a enregistres (`Combat.emit`). Bandeaux et textes flottants voyagent comme
*donnees* (`i18n.text`) : chaque machine les affiche dans sa langue.

**Regles a deux.** Un vaisseau abattu revient apres `COOP_RESPAWN` secondes avec
`COOP_REVIVE_HULL` de sa coque, si son partenaire tient bon ; l'essai est perdu quand les deux sont
abattus. Les Thargoides visent le vaisseau le plus proche (`game.target`). La pause ne fige rien.
Seul l'hote repond aux ecrans de mort et de victoire (reessayer, secteur suivant) ; le client attend
ou quitte. Partir (ou perdre la liaison) arrete la partie des deux cotes.

**Meta.** Chacun vole avec son vaisseau, son hangar et son equipement d'entree de secteur. Le
meta-alliage ramasse par l'equipe est verse aux **deux** metas. Les records solo (morts, temps,
deblocages, equipements memorises) ne bougent pas ; l'equipement passe d'un secteur coop au suivant.

## Organisation du code

```
maelstrom/                 (dossier du projet)
  main.py, menu.py
  settings/            ce qui se REGLE, sans code de jeu
    __init__.py        GAME_NAME et VERSION : des noms propres, pas du texte traduit
    balance.py         vaisseau, armes, missiles, conteneurs, hangar,
                       ennemis, Intercepteurs, secteurs
    ui.py              canevas, couleurs, palettes des secteurs, HUD, musique
  maelstrom/           le paquet du jeu (importe comme `maelstrom`)
    i18n.py            traduction : t(cle, **champs) ; une langue = un fichier
    locales/           fr.json (reference), en.json : tout ce que le joueur lit
    storage.py         meta et prefs (fichier ou localStorage), journal
    audio.py           musique : une piste a la fois, volume
    neon.py            glow, blit_glow, neon_polygon, draw_bar, draw_sun
    screen.py          fenetre, polices, icone, scanlines, init()
    widgets.py         Button, wrap, stack_buttons
    effects.py         Particle, FloatText, Ring
    backdrop.py        decor defilant d'un secteur
    projectiles.py     Shot, Missile, CausticCloud
    player.py          Ship
    enemies.py         Enemy, Interceptor
    pickups.py         Pickup, tirage des conteneurs
    levels.py          vagues semees d'un secteur
    bugreport.py       rapports de bug ecrits dans saves/bugs/ (bureau)
    bugform.py         formulaire de rapport (F8), partage par le jeu et les menus
    bugsend.py         envoi des rapports au relais, boite d'envoi (bureau)
    net.py             transport LAN : TCP + annonce UDP (bureau, repris de purr-tage)
    session/           la classe Game, un fichier par responsabilite
      game.py          etat, essais, phases, update, draw
      combat.py        touches, destructions, butin, conteneurs, Intercepteur
      controls.py      clavier, souris, doigt, pause, actions des ecrans
      hud.py           HUD, bandeaux, ecrans pause / mort / victoire
      bug_form.py      adaptateur du formulaire de rapport pour le jeu (retour a la pause)
      coop.py          coop LAN : session, instantane de l'hote, miroir du client
    loop.py            play() : la boucle d'un secteur ; play_coop() : une partie a deux
```

Les memes trois regles qu'Orbital Defense :

1. **`settings/` ne contient que des valeurs**, et **tout texte affiche va dans
   `maelstrom/locales/*.json`**, lu par `maelstrom.i18n` (`i18n.t("cle")`,
   gabarits `.format()` a trous nommes : le format comme `{time:.0f}` fait
   partie du gabarit, il pilote l'alignement a l'ecran). Les tables de noms
   (ennemis, armes, secteurs, ameliorations...) sont indexees par les cles de
   `balance.py` via des aides (`i18n.level_name`, `i18n.boss_name`,
   `i18n.weapon_name`, `i18n.hangar_name`...). Le **nom propre** du jeu
   (`GAME_NAME`) et sa `VERSION` sont des constantes de `settings` : un nom
   propre ne se traduit pas.
2. **Les valeurs creees a l'execution se lisent par le module** :
   `screen.SCREEN`, `screen.FONT_SMALL`, jamais `from maelstrom.screen import
   SCREEN`.
3. **Les imports vont dans un seul sens**, dans l'ordre de la liste ci-dessus.
   Une entite recoit `game` en argument (`game.enemy_fire`, `game.spawn_enemy`).

**`Game` est une composition** (`class Game(Combat, Controls, Hud, BugForm, Coop)`) : les
classes de base n'ont ni etat ni `__init__`. L'etat est cree dans `game.py` :
l'interface par `__init__`, un essai par `start()`.

**Flux des ecrans** (`main.py`) : accueil -> secteurs -> `campaign(level)`, qui
enchaine `loop.play()`. `play()` rend `(issue, secteur)` : `"next"` enchaine le
secteur suivant, `"hangar"` ouvre le hangar puis rejoue le secteur indique,
`"menu"` revient a l'accueil, `"quit"` ferme. En coop : accueil -> vaisseau -> salon (`menu.lobby()`)
-> secteurs (hote) -> `loop.play_coop()`, qui enchaine les secteurs sur la meme liaison.

**Ou ajouter quoi.**

| Je veux... | Fichier |
|---|---|
| changer des degats, une cadence, des PV, un cout, la duree d'un secteur | `settings/balance.py` |
| changer une couleur, la palette d'un secteur, une taille du HUD | `settings/ui.py` |
| changer un libelle, un nom, une description | `maelstrom/locales/fr.json` (+ `en.json`) |
| ajouter une langue | deposer `maelstrom/locales/<iso>.json` (copier `fr.json`) : apparait tout seul dans Options |
| ajouter un type d'ennemi | `ENEMIES` + methode `_<type>` et forme dans `maelstrom/enemies.py` |
| ajouter un motif de vague | `maelstrom/levels.py` + table `patterns` du secteur |
| ajouter une attaque d'Intercepteur | methode `_<motif>` d'`Interceptor` + `patterns` du boss |
| ajouter un bonus ou un malus | `BONUSES` / `MALUSES`, puis `take_pickup` (`combat.py`) et, pour un effet dans la duree, `Ship` ; son nom dans les cles `pickups.<cle>` des locales |
| ajouter un secteur | `LEVELS` + `LEVEL_LOOKS` + les cles `levels.<cle>` des locales (et un boss) |

## Langues (i18n)

Calque sur purr-tage. **Une langue = un fichier** `maelstrom/locales/<code>.json`
(ISO-639-1 : `fr.json`, `en.json`...). Le code ne tient aucune liste : deposer
un fichier suffit, il apparait dans le bouton **Langue** des Options. Les cles
sont hierarchiques, ecrites avec des points (`dead.progress`, `banner.sector`).

- **`fr.json` est la reference** (francais sans accents, convention du depot) et
  le **repli** : une cle absente de la langue courante est prise la, une cle
  absente partout est rendue telle quelle (visible a l'ecran plutot que vide).
- **`en.json`** suit la terminologie **Elite Dangerous** : Thargoids,
  Interceptor, Cyclops / Basilisk / Medusa / Hydra, Meta-Alloy, Shield Cell
  Bank, AX / Anti-Xeno, limpets, Pleiades...
- La langue se **detecte** au lancement (`i18n.detect()`, appele par
  `menu.init()`) : choix memorise (`prefs.json`), sinon langue du systeme, sinon
  francais. Le bouton Langue des Options la change a chaud et la **memorise**.
- Les deux langues livrees sont trouvees meme si `os.listdir` n'enumere pas le
  dossier embarque sous pygbag (elles sont **sondees par nom**, `_BUILTIN`).

## Ecran et navigateur

**Canevas fixe 960 x 540**, paysage (`WIDTH`, `HEIGHT` dans `settings/ui.py`).
Sur le bureau, `make_screen()` ouvre la fenetre en `SCALED | RESIZABLE` et ne la
recree pas si elle a deja la bonne taille. Dans le navigateur, pas de
`SCALED` (pas de renderer SDL) ; la page est reajustee apres la creation du
canvas (`_refit_page`), sinon le jeu serait ecrase dans un carre.

Les contraintes pygbag sont celles d'Orbital Defense : **toutes les boucles sont
`async`** et font `await asyncio.sleep(0)` apres `flip()` ; **rien ne se cree au
chargement d'un module** (`screen.init()`, appele par `menu.init()`) ; **aucune
police systeme** (`assets/DejaVuSansMono.ttf` embarquee) ; la meta et les prefs
passent par le **localStorage** (`store_read` / `store_write`, prefixe
`maelstrom.`) ; `Echap` n'atteint pas le jeu, d'ou le bouton `Pause` du HUD ;
pas de `Quitter` dans le navigateur. Le jeu se **met en pause** quand la fenetre
ou l'onglet perd le focus (`WINDOWFOCUSLOST`).

## Sauvegarde

Pas de sauvegarde de partie : un secteur est court. Un document pour la
progression, `saves/meta.json` (`META_VERSION`) : meta-alliage, niveaux du
hangar, secteurs ouverts, morts et meilleur temps par secteur, equipement a
l'entree de chaque secteur, campagne gagnee. `read_meta()` **reconstruit**
chaque champ : un fichier abime donne une meta par defaut, jamais une exception.
Un second document, `saves/prefs.json`, retient la **langue** choisie et le
**volume** de la musique.

## Rapports de bug (F8)

Meme systeme que les autres jeux du depot (copie voulue, pas de code partage),
**sur le bureau seulement** (`bugreport.ENABLED = not WEB` : dans le navigateur,
pas de fichiers durables, et le bouton de la pause n'existe pas). Un rapport =
**un dossier** `saves/bugs/<AAAAMMJJ-HHMMSS>/` (suffixe `-2`, `-3` si
l'horodatage est pris), hors de git comme tout `saves/` :

| Fichier | Contenu |
|---|---|
| `report.md` | description, date, commit git (`+dirty` si le dossier du projet est modifie), et le contexte de l'essai : secteur, phase (et ecran ouvert), ecran d'ou part le rapport (`screen`), horloge du secteur et rang dans le script des vagues, duree de l'essai, coque, bouclier, arme / niveau / missiles, effets en cours, ennemis et tirs ennemis, conteneurs, point de reprise, destructions, meta-alliage de l'essai, Intercepteur (etat, coeur, PV), puis la **meta** relue dans `meta.json` (meta-alliage, hangar, secteurs ouverts, morts) ; la trace pour un plantage ; une rubrique « Missing » si une piece manque |
| `screen.png` | l'ecran au moment du bug |
| `state.json` | un **instantane** de l'essai (`Game.state_data()`) : vaisseau, ennemis, conteneurs, Intercepteur |
| `log.txt` | les 200 dernieres lignes de `saves/maelstrom.log` |

**`state.json` ne se recharge pas** : il n'y a pas de sauvegarde de partie. Pour
**rejouer un bug**, on relance le secteur : ses vagues sont semees, donc
l'horloge `t` du rapport dit ou l'on en etait, et l'equipement (`ship`,
`checkpoint`) dit avec quoi.

**Deux entrees, un seul ecrivain** (`bugreport.write_report`) :

- **Signalement manuel** : **`F8`** sur tous les ecrans. En partie (y compris
  sur l'ecran de mort ou de victoire), ou par le bouton `Signaler un bug` du
  menu de pause ; hors secteur, sur l'accueil, le choix du vaisseau, les
  secteurs, le hangar, les Options et le salon coop. Le formulaire
  (`maelstrom/bugform.py`, classe `BugForm`, utilisable sans `Game`) est une
  ligne de texte (200 caracteres au plus) et une case « Envoyer le rapport » ;
  `Entree` enregistre, `Echap` annule, et il prend tout le clavier et les clics
  tant qu'il est ouvert. En partie, `session/bug_form.py` n'en est que
  l'adaptateur (drapeau `showing_bug_form`) ; dans les menus, chaque boucle de
  `menu.py` appelle `_bug_intercept` et `_bug_overlay`. Le rapport note l'ecran
  d'ou il part (`screen: <nom>`, `sector` en partie). **Tout est capture a
  l'ouverture** : l'ecran, l'instantane et le contexte. Depuis la pause,
  l'ecran joint est celui **d'avant** la pause (`open_pause` en garde une copie,
  `pause_shot`, avant de dessiner son voile).
- **Filet anti-plantage** : `main.py` entoure `asyncio.run(main())` d'un `try` ;
  une exception non rattrapee, en secteur **ou dans les menus**, ecrit un
  rapport (`report_crash`, avec la trace) puis se propage comme avant. L'etat
  vient de `loop.current_game`, pose par `play()` et remis a `None` par
  `campaign()` au retour (un plantage dans les menus dit « game: none (menus) »).

**Le secteur est vraiment fige** pendant le formulaire : `play()` n'appelle plus
`game.update()`, et la secousse est remise a zero a l'ouverture. **A la
fermeture, on tombe sur le menu de pause** si le vaisseau volait (F8 en vol, ou
le bouton de la pause) : dans un shoot'em up, rendre la main d'un coup jetterait
le joueur sous le feu. Ouvert sur l'ecran de mort ou de victoire, il y revient ;
ouvert depuis un menu, on reste sur ce menu.
Apres l'enregistrement, une ligne « Rapport enregistre : saves/bugs/<dossier> »
(ou « non enregistre », ou l'etat de l'envoi) s'affiche en bas de l'ecran
pendant `BUG_NOTICE_TIME` secondes ; son minuteur (`tick_notice`) tourne dans
`play()`, pour descendre aussi sous la pause, et dans `_bug_overlay` pour les
menus.

**Envoi au relais** (`maelstrom/bugsend.py`). Le rapport est toujours ecrit sur
le disque d'abord. Si la case « Envoyer le rapport » est cochee (choix memorise
dans `prefs.json`, `send_reports`), il est confie a la **boite d'envoi**
`saves/bugs/outbox/` (un ticket `.json`) puis envoye en HTTPS sur un fil de
fond (`certifi` pour les certificats), sans jamais bloquer le jeu. Trois
issues : **envoye** (le ticket disparait), **refuse** par le relais (erreur
4xx hors 408 / 429 : le ticket disparait, le rapport reste sur le disque),
**pas de reponse** (le ticket reste et `main.py` le renvoie au lancement
suivant, `flush_async`). Chaque tentative est notee dans `saves/bugs/send.log`.
L'adresse est `BUG_REPORT_URL` (`settings/__init__.py`), utilisee **seulement
par le jeu empaquete** ; depuis les sources rien ne part, sauf si
**`MAELSTROM_REPORT_URL`** pointe vers un relais d'essai. Sans relais, la case
est remplacee par « Enregistre sur le disque (aucun relais configure) ». Le
relais lui-meme (Cloudflare Worker vers Discord, copie dans Workers KV) est
decrit dans `relay/README.md`.

**Tout y est defensif** : une capture impossible, un etat qui ne se serialise
pas ou un disque en lecture seule sont notes dans `report.md` (ou journalises)
au lieu de lever.

**Journal** : `setup_logging()` (dans `storage.py`, appele en tete de
`screen.init()`), niveau par **`MAELSTROM_LOG`** (`WARNING` par defaut),
fichier `saves/maelstrom.log` hors navigateur, que **`MAELSTROM_LOG_FILE`**
remplace : les tests sans fenetre la posent, pour que leurs lignes n'aillent ni
dans le journal du joueur ni dans le `log.txt` d'un rapport.

## Musique

Bande-son de **Ookamy** ([suno.com/@ookamy](https://suno.com/@ookamy)), generee avec Suno a partir des prompts de
`docs/musique.md` (ambiance, tempo, durees ideales, phase de chaque piste).
Fichiers `.ogg` dans `assets/music/` ; la table `MUSIC` de `settings/ui.py`
relie chaque piste a son fichier, et `maelstrom/audio.py` la joue selon
l'ecran ou la phase de jeu. Une piste absente donne du silence. Le volume se
regle dans Options (retenu dans `prefs.json`).

| Piste            | Fichier                     | Quand                                         |
|------------------|-----------------------------|-----------------------------------------------|
| Titre            | `title.ogg`                 | accueil, choix du vaisseau, secteurs, options |
| Hangar           | `hangar.ogg`                | hangar                                        |
| Pause            | `pause.ogg`                 | menu pause ; le secteur reprend ensuite       |
| Secteur 1        | `sector_1.ogg`              | Ceinture de Merope                            |
| Secteur 2        | `sector_2.ogg`              | Ruines de l'Oracle                            |
| Secteur 3        | `sector_3.ogg`              | Nebuleuse des Pleiades                        |
| Secteur 4        | `sector_4.ogg`              | Coeur du Maelstrom                            |
| Alerte           | `warning.ogg`               | « Intercepteur en approche »                  |
| Cyclope, Basilic | `boss_cyclops_basilisk.ogg` | combat des secteurs 1 et 2                    |
| Meduse           | `boss_medusa.ogg`           | combat du secteur 3                           |
| Hydre            | `boss_hydra.ogg`            | combat du secteur 4                           |
| Titan            | `boss_titans.ogg`           | secteur du Titan (approche + combat)          |
| Mort             | `dead.ogg`                  | ecran de mort                                 |
| Secteur libere   | `cleared.ogg`               | victoire sur un Intercepteur                  |
| Generique        | `credits.ogg`               | fin de campagne (secteur 4 libere)            |

En reserve, non branchees : `boss_titans.ogg` et les secondes versions
(`sector_1_alt` a `sector_4_alt`, `warning_alt`, `dead_alt`).

## Conventions

- **Code en anglais** (identifiants, commentaires, docstrings, cles). **Le texte
  affiche vit dans les locales** : `fr.json` est la reference (francais sans
  accents), `en.json` sa traduction (terminologie Elite Dangerous). La langue se
  choisit dans Options et se detecte au lancement. Documentation en francais.
- **Aucune ressource externe** hors la police et la musique : tout est dessine.
- **Couleurs** : constantes `C_...` de `settings/ui.py`. Vert thargoide pour
  l'ennemi et les malus, cyan pour le joueur et les bonus, orange-rouge pour
  les coeurs.
- **`dt`** plafonne a 0,05 s ; toute logique de temps passe par `dt`.
- **Classe `Button`** : `draw(surf, mouse_pos)` / `click(pos)`.

## Mesure et equilibrage

Il n'y a pas de script de mesure versionne. Les reglages actuels ont ete poses
le 20 octobre 2026 avec des bots sans fenetre (`SDL_VIDEODRIVER=dummy`,
`storage.SAVE_DIR` detourne) : un vaisseau **immobile** meurt dans l'Intercepteur
du secteur 1 et vers 30 %, 35 %, 12 % des secteurs 2 a 4 ; un vaisseau qui
**ondule** sans viser atteint l'Intercepteur des secteurs 1 et 2 (et souvent du
3) et meurt entre 34 et 56 % du secteur 4. Ces bots ne ramassent rien
volontairement et n'achetent rien au hangar. Aucun joueur reel n'a encore joue : les chiffres sont a
reprendre a la main.

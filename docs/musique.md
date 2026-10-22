# Musique - prompts Suno

Bande-son de *Maelstrom* a generer avec Suno. La direction reprend celle du
jeu : synthwave neon, shoot'em up die and retry, quatre secteurs aux palettes
distinctes, quatre Intercepteurs. Le lecteur (`maelstrom/audio.py`) cherche
chaque piste dans `assets/music/` sous le nom du tableau ci-dessous, en `.ogg`
puis en `.mp3` ; la table est `MUSIC` dans `settings/ui.py`. Une piste absente
donne du silence, pas une erreur. Le volume se regle dans Options.

## Regles de generation

- Mode **Custom**, case **Instrumental** cochee.
- Prompts en anglais (mieux compris par Suno). Pas de nom d'artiste ni de
  marque (Elite Dangerous, Thargoid) : Suno les refuse ou les ignore.
- **Exclude styles**, a mettre partout :
  `vocals, choir lyrics, acoustic guitar, orchestral strings, lo-fi, jazz`
- **Tempo croissant par secteur** (110, 118, 126, 136 BPM) pour suivre le
  defilement (`scroll` de 140 a 200 dans `settings/balance.py`).
- **Bouclage** : on meurt et on recommence souvent, chaque piste doit boucler
  sans a-coup. Demander une fin abrupte (`hard stop`), puis couper la boucle
  sur une mesure entiere (Audacity).
- Duree : voir « Durees ideales » plus bas.
- **Coherence** : generer d'abord le theme titre, puis partir de lui avec
  **Extend** ou **Cover** pour les secteurs, afin de garder le meme timbre de
  lead. Toutes les tonalites sont mineures sauf la victoire.

## Pistes et phases du jeu

Phases de `Game.phase` (`maelstrom/session/game.py`) : `play`, `warning`,
`boss`, `boss_dying`, `dead`, `cleared`.

Les fichiers sont dans `assets/music/`, nommes sans extension dans la table
`MUSIC` de `settings/ui.py`. Statut : `Fait` si le fichier existe, `A faire`
sinon (la phase reste alors silencieuse).

| Cle         | Fichier                 | Ecran / phase                        | Type   | Statut  |
|-------------|-------------------------|--------------------------------------|--------|---------|
| `title`     | `title`                 | accueil, vaisseau, secteurs, options | boucle | Fait    |
| `credits`   | `credits`               | `cleared` du dernier secteur         | piste  | Fait    |
| `pause`     | `pause`                 | menu pause (solo)                    | boucle | Fait    |
| `hangar`    | `hangar`                | hangar                               | boucle | Fait    |
| `merope`    | `sector_1`              | `play`, secteur 1                    | boucle | Fait    |
| `oracle`    | `sector_2`              | `play`, secteur 2                    | boucle | Fait    |
| `pleiades`  | `sector_3`              | `play`, secteur 3                    | boucle | Fait    |
| `maelstrom` | `sector_4`              | `play`, secteur 4                    | boucle | Fait    |
| `warning`   | `warning`               | `warning` (Intercepteur en approche) | jingle | Fait    |
| `cyclops`   | `boss_cyclops_basilisk` | `boss`, Cyclope                      | boucle | Fait    |
| `basilisk`  | `boss_cyclops_basilisk` | `boss`, Basilic                      | boucle | Fait    |
| `medusa`    | `boss_medusa`           | `boss`, Meduse                       | boucle | Fait    |
| `hydra`     | `boss_hydra`            | `boss`, Hydre                        | boucle | Fait    |
| `dead`      | `dead`                  | `dead`                               | jingle | Fait    |
| `cleared`   | `cleared`               | `cleared` (secteur libere)           | jingle | A faire |

En reserve, non branches : `boss_titans`, et la seconde version Suno de
plusieurs pistes (`sector_1_alt`, `sector_2_alt`, `sector_3_alt`,
`sector_4_alt`, `warning_alt`, `dead_alt`). Pour en changer, echanger les
noms de fichiers ou pointer la cle de `MUSIC` vers le `_alt`.

Les sources sont dans `docs/music/` (export Suno en `.mp3`, numerote dans
l'ordre de generation) ; chaque `.ogg` en est la conversion integrale
(Vorbis, 48 kHz, 192 kb/s) :

```bash
ffmpeg -i docs/music/Maelstrom_07_Merope_01.mp3 -map 0:a -c:a libvorbis \
       -b:a 192k -ar 48000 assets/music/sector_1.ogg
```

Pendant `boss_dying`, la musique de boss s'eteint en fondu sous les
explosions (`MUSIC_FADE_OUT`). En pause, la piste `pause` remplace celle du
secteur, qui reprend ensuite la ou elle s'etait arretee (de meme pour l'accueil
apres le hangar). Un nouvel essai repart du debut de la piste.

Format : `.ogg` pour le navigateur (pygbag ne lit pas le `.mp3` partout) ; le
`.mp3` suffit sur le bureau.

## Durees ideales

On genere plus long que necessaire (Suno ajoute intro et fin), puis on extrait
du milieu une boucle d'un nombre entier de mesures (multiple de 8). Pour un
secteur, la boucle depasse `duration` + `BOSS_CLEAR_WAIT` (5 s) : un essai
complet n'entend jamais la couture, et chaque nouvel essai repart du debut.

| Fichier         | A generer   | Boucle a extraire       | Repere dans le jeu                      |
|-----------------|-------------|-------------------------|-----------------------------------------|
| `title.ogg`     | 2:30        | 48 mesures, 1:55        | menus, temps libre                      |
| `hangar.ogg`    | 2:00        | 32 mesures, 1:25        | temps libre                             |
| `merope.ogg`    | 2:00        | 40 mesures, 1:27        | secteur de 75 s                         |
| `oracle.ogg`    | 2:15        | 48 mesures, 1:38        | secteur de 85 s                         |
| `pleiades.ogg`  | 2:30        | 56 mesures, 1:47        | secteur de 95 s                         |
| `maelstrom.ogg` | 2:30        | 64 mesures, 1:53        | secteur de 105 s                        |
| `warning.ogg`   | 0:15        | pas de boucle, 3 s      | `BOSS_WARNING` = 3,2 s (1,4 s en reprise) |
| `boss.ogg`      | 2:30        | 64 mesures, 1:50        | combat de duree variable                |
| `hydra.ogg`     | 2:30        | 64 mesures, 1:44        | combat le plus long                     |
| `dead.ogg`      | 0:15        | pas de boucle, 3 a 4 s  | avant l'ecran de mort                   |
| `cleared.ogg`   | 0:15        | pas de boucle, 5 a 6 s  | apres `BOSS_DEATH_TIME` (2,4 s)         |
| `credits.ogg`   | 2:30 a 3:00 | pas de boucle           | ecoute en entier                         |

Les jingles ressortent rarement assez courts de Suno : generer une piste breve
et garder le debut, avec un fondu de 0,2 s a la coupe.

## 1. Ecran titre / menu des secteurs

**Style :**
```
dark synthwave, retrowave, 100 BPM, A minor, slow analog pad swells, deep pulsing sawtooth bass arpeggio, gated reverb snare, distant cosmic drones, nostalgic and ominous, neon space horizon, 80s sci-fi film score, cinematic, instrumental, seamless loop
```
**Structure (champ paroles) :**
```
[Intro: lone synth pad, distant radio static]
[Verse: arpeggiated bass enters, soft drums]
[Chorus: wide lead synth melody, heroic but melancholic]
[Bridge: drums drop out, alien whispering texture]
[Chorus]
[End: hard stop, no fade]
```

## 2. Hangar

**Style :**
```
chill synthwave, 90 BPM, D minor, warm Rhodes-like synth chords, soft sidechained pads, mechanical ambience, servo clicks, calm workshop vibe between battles, retro-futuristic, relaxed but focused, instrumental, loopable
```
**Structure :**
```
[Intro: hangar ambience, metallic echoes]
[Verse: mellow chords, light hi-hats]
[Chorus: gentle lead synth hook]
[Verse]
[End: hard stop]
```

## 3. Secteur 1 - Ceinture de Merope

Soleil rose et or, champ d'asteroides, premiers essaims.

**Style :**
```
outrun synthwave, 110 BPM, E minor, driving sawtooth bassline, punchy 80s drum machine, bright pink neon lead synth, sunset over an asteroid belt, adventurous and hopeful with underlying tension, arcade shoot em up, instrumental, seamless loop
```
**Structure :**
```
[Intro: rising synth sweep, engine hum]
[Verse: driving bass and drums]
[Chorus: soaring lead melody, heroic]
[Verse: added arpeggio layer]
[Chorus]
[Break: short filter sweep]
[End: hard stop, no fade]
```

## 4. Secteur 2 - Ruines de l'Oracle

Ciel rouge, debris de la station, maraudeurs et mines.

**Style :**
```
darksynth, 118 BPM, C minor, aggressive distorted bass, industrial percussion, metallic clangs, red warning alarm synth, ruined space station, eerie detuned pads, tense and dangerous, cyberpunk action, instrumental, seamless loop
```
**Structure :**
```
[Intro: distress beacon pulse, creaking metal]
[Verse: heavy bass groove, industrial drums]
[Chorus: menacing lead synth, alarm stabs]
[Breakdown: sparse, ghostly pads, debris noises]
[Chorus]
[End: hard stop]
```

## 5. Secteur 3 - Nebuleuse des Pleiades

Bleu glace, nebuleuse, les Berserkers.

**Style :**
```
cosmic synthwave, spacesynth, 126 BPM, F# minor, shimmering icy arpeggios, crystalline bell synths, deep sub bass, fast driving drums, vast blue nebula, awe and dread, ethereal yet relentless, epic space battle, instrumental, seamless loop
```
**Structure :**
```
[Intro: crystalline shimmer, slow swell]
[Verse: rapid arpeggios, pounding kick]
[Chorus: epic wide lead, choir-like synth pad]
[Bridge: weightless ambient section, alien resonance]
[Chorus: full intensity]
[End: hard stop]
```

## 6. Secteur 4 - Coeur du Maelstrom

Vert toxique, le nid, l'assaut final.

**Style :**
```
dark cyberpunk darksynth, 136 BPM, B minor, organic alien textures, pulsing bio-mechanical bass, distorted heavy synths, relentless drums, toxic green vortex, hive heartbeat, oppressive and overwhelming, final assault, cinematic horror sci-fi, instrumental, seamless loop
```
**Structure :**
```
[Intro: alien heartbeat, swirling vortex drone]
[Verse: crushing bass, fast drums]
[Chorus: dissonant screaming lead synth]
[Breakdown: heartbeat alone, eerie alien calls]
[Chorus: maximum intensity]
[End: hard stop]
```

## 7. Intercepteur (Cyclope, Basilic, Meduse)

Le combat alterne **blinde** (petales fermes) et **expose** (coeur ouvert,
c'est au joueur de frapper) : la musique alterne pression et percee heroique.

**Style :**
```
boss battle darksynth, 140 BPM, D minor, massive distorted bass, aggressive drums, alien dissonant stabs, heroic counter-melody, alternating oppressive and triumphant sections, giant flower-shaped alien warship, intense arcade boss fight, instrumental, seamless loop
```
**Structure :**
```
[Intro: alarm, low alien roar]
[Verse: oppressive heavy groove]
[Chorus: heroic lead melody breaks through]
[Verse: heavier, dissonant]
[Chorus]
[End: hard stop]
```

## 8. Boss final - Hydre

**Style :**
```
epic final boss darksynth, 148 BPM, C# minor, colossal distorted synths, double-time drums, alien choir pads, chaotic arpeggios, desperate heroic lead, apocalyptic space battle at the heart of the vortex, maximum intensity, instrumental, seamless loop
```
**Structure :**
```
[Intro: alarm, low alien roar]
[Verse: oppressive heavy groove]
[Chorus: heroic lead melody breaks through]
[Verse: heavier, dissonant]
[Bridge: alien choir, heartbeat]
[Chorus]
[End: hard stop]
```

## 9. Jingles et generique

Demander une piste courte et couper l'excedent.

| Fichier       | Style |
|---------------|-------|
| `warning.ogg` | `alarm stinger, synthwave, rising tension riser, low alien roar, warning siren synth, 3 seconds, instrumental` |
| `dead.ogg`    | `game over stinger, darksynth, descending detuned synth, fading engine, short and melancholic, 4 seconds, instrumental` |
| `cleared.ogg` | `victory fanfare, synthwave, triumphant major chord lead, bright arpeggio, gated snare, 6 seconds, instrumental` |
| `credits.ogg` | `triumphant emotional synthwave, 100 BPM, A major, soaring lead, warm pads, hopeful sunrise after the war, cinematic outro, instrumental` |

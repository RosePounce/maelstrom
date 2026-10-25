# Kit presse

Images de la page itch.io et du README, toutes dessinées par le jeu lui-même :
aucune n'a été retouchée, et aucune n'est un agrandissement d'une autre.

## Captures (960 × 540)

| Fichier | Ce qu'on y voit |
| --- | --- |
| `01-accueil.png` | L'écran d'accueil et ses trois cartes |
| `02-vaisseaux.png` | Le choix du chasseur, stats comparées |
| `03-secteurs.png` | Les quatre secteurs, records et morts |
| `04-hangar.png` | Les améliorations permanentes |
| `05-secteur-1-merope.png` | Ceinture de Mérope, laser à impulsion Nv 3 |
| `06-secteur-2-oracle.png` | Ruines de l'Oracle, canon à fragmentation Nv 4 |
| `07-secteur-3-pleiades.png` | Nébuleuse des Pléiades, canon à rails Nv 4 |
| `08-intercepteur-en-approche.png` | La bannière d'alerte avant le boss |
| `09-boss-cyclops.png` | Le Cyclope, cœur exposé |
| `10-boss-hydra.png` | L'Hydre et son mur de projectiles |
| `11-titan.png` | Taranis, le Titan, rayon en action |

## Art de page

| Fichier | Taille | Usage |
| --- | --- | --- |
| `banniere-1920x480.png` | 1920 × 480 | Bandeau en haut de la page itch.io, en-tête de dépôt |
| `couverture-630x500.png` | 630 × 500 | Image de couverture itch.io (la vignette des listes) |
| `fond-1920x1080.png` | 1920 × 1080 | Fond de page, volontairement sombre : le texte passe par-dessus |

## Regénérer

```bash
python tools/capture.py      # les captures
python tools/press_art.py    # bannière, couverture, fond
```

Les deux scripts tournent sans fenêtre ni son (pilotes SDL `dummy`), en quelques
secondes, et ne touchent jamais à `saves/` : la sauvegarde servie aux captures
est une fausse, assez avancée pour que la liste des secteurs et le hangar valent
le coup d'œil. `--lang en` produit la série en anglais.

# Le relais des rapports de bogue

**Français** · [English](README.en.md)

> **Dossier réservé** — ce relais est celui du jeu : il tourne sur le compte
> Cloudflare de RosePounce et reçoit les rapports des joueurs. Lancé depuis les
> sources, le jeu n'envoie aucun rapport ; cette page sert à qui tient le
> relais du jeu, ou à qui héberge le sien sur son propre fork et son compte.

Le jeu ne connaît qu'une seule adresse : celle de ce relais. Quand un joueur
envoie un rapport (**F8**), le relais le vérifie, en garde une copie et le
transmet à Discord :

```
Jeu (F8)  ──HTTPS──>  Relais /report  ──>  Discord (webhook)
                          └─ copie dans Workers KV (rapport, capture)
```

Brancher ou débrancher un service se fait sur le relais, sans nouvelle version
du jeu. Aucune clé ne se trouve dans le jeu, dont le code est public.

C'est un [Cloudflare Worker](https://developers.cloudflare.com/workers/), écrit
en JavaScript sans aucune dépendance. Le Worker comme son stockage, Workers KV,
restent dans l'offre gratuite de Cloudflare pour un jeu de cette taille.

## Mettre le relais en ligne

Il faut un compte Cloudflare, sur l'offre gratuite. Deux façons de faire.

### Depuis le tableau de bord, sans rien installer

1. **Storage & Databases** > **Workers KV** > **Create** : nommer l'espace
   `maelstrom-reports`, puis copier son **ID**.
2. Coller cet ID dans `wrangler.toml`, à la place de
   `REPLACE_WITH_THE_NAMESPACE_ID`, puis commiter et pousser. L'ID n'a rien de
   secret.
3. **Workers & Pages** > **Create** > **Import a repository** : choisir le
   dépôt, la branche qui contient `relay/`, et indiquer `relay` comme **Root
   directory**. La commande par défaut, `npx wrangler deploy`, convient.

Le secret Discord s'ajoute ensuite dans la page du Worker : **Settings** >
**Variables and Secrets** > **Add**, type **Secret**, nom `DISCORD_WEBHOOK_URL`.
Il est conservé d'un déploiement à l'autre.

### En ligne de commande

Il faut Node.js 18 ou plus récent, avec npm.

```bash
cd relay
npm install                                      # installe wrangler
npx wrangler login                               # ouvre le navigateur
npx wrangler kv namespace create maelstrom-reports   # affiche l'ID à coller dans wrangler.toml
npx wrangler deploy
npx wrangler secret put DISCORD_WEBHOOK_URL      # l'URL du webhook du salon
```

### Essayer

Le tableau de bord comme `deploy` donnent l'adresse du relais, de la forme
`https://maelstrom.<votre-compte>.workers.dev`. Avant de toucher au jeu, on
l'essaie avec la version de développement :

```bash
MAELSTROM_REPORT_URL=https://maelstrom.<votre-compte>.workers.dev/report python main.py
```

**F8**, un mot, coche **Envoyer le rapport**, **Entrée** : la fenêtre doit
afficher « Rapport envoye. Merci ! ». Une fois l'essai concluant, l'adresse va
dans `BUG_REPORT_URL`, dans `settings/__init__.py`, et les paquets construits
ensuite enverront leurs rapports.

Sans aucun service branché, le relais garde quand même chaque rapport dans KV :
on peut le déployer d'abord et brancher Discord ensuite.

## Discord

Un message dans un salon, avec le rapport et la capture en pièces jointes.

1. Paramètres du salon > **Intégrations** > **Webhooks** > **Nouveau webhook** >
   **Copier l'URL du webhook**.
2. ```bash
   npx wrangler secret put DISCORD_WEBHOOK_URL
   ```

Les mentions sont désactivées : un joueur qui écrit `@everyone` ne réveille
personne. Pour débrancher : `npx wrangler secret delete DISCORD_WEBHOOK_URL`.

Ajouter un autre service (GitHub, e-mail...) : un fichier dans
`src/connectors/`, sur le modèle de `discord.js` (`name`, `enabled(env)`,
`send(report, env)`), ajouté à la liste de `src/connectors/index.js`.

## Ce que le relais accepte

| | |
|---|---|
| Adresse | `POST /report`, en `multipart/form-data` |
| `meta` | JSON : `version`, `language`, `system`, `install`, `description` |
| `report` | le fichier `report.md`, 64 Kio au plus |
| `screenshot` | facultatif, un PNG de 6 Mio au plus |
| En-tête | un `User-Agent` qui commence par `Maelstrom/` |

| Réponse | Sens | Le jeu |
|---|---|---|
| 202 | rapport conservé, ou transmis à au moins un service | l'oublie |
| 400, 413 | refusé : mal formé, trop gros | l'abandonne |
| 429 | plus de 5 rapports en une minute depuis la même adresse | le renvoie plus tard |
| 503 | ni stockage, ni service joignable | le renvoie plus tard |

`GET /shot/<id>.png` sert une capture conservée.

## Confidentialité

* Un rapport ne contient rien de personnel : la description du joueur, l'état
  de la partie, les versions du jeu et du système.
* L'adresse IP sert uniquement à limiter le nombre d'envois ; elle n'est ni
  enregistrée, ni transmise.
* KV efface chaque rapport et sa capture au bout de 180 jours
  (`REPORT_TTL_DAYS` dans `wrangler.toml`).

## Diagnostiquer

1. **Côté jeu** : `send.log`, dans `saves/bugs/`. Une ligne par tentative :
   `no relay address`, `unreachable`, `refused` ou `sent`, avec la réponse.
2. **L'état du relais** : `https://maelstrom.<votre-compte>.workers.dev/health`
   indique si KV est branché et quels services ont trouvé leurs secrets.
   ```json
   {"storage":true,"limiter":true,"connectors":["discord"]}
   ```
3. **Les journaux du relais** : page du Worker > **Logs**. Une ligne JSON par
   rapport, sans l'adresse IP ni les mots du joueur.

## Développer

```bash
npm test               # les tests, avec Node 22 seul : aucune dépendance
npx wrangler dev       # le relais sur http://localhost:8787
npx wrangler tail      # les journaux du relais en ligne, en direct
```

Avec `wrangler dev`, le secret va dans un fichier `.dev.vars`, que Git ignore :

```
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
```

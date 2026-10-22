# The bug report relay

[Français](README.md) · **English**

> **Reserved folder** — this relay is the game's own: it runs on RosePounce's
> Cloudflare account and receives the players' reports. Run from the sources,
> the game sends no report; this page is for whoever keeps the game's relay, or
> hosts their own on their own fork and account.

The game knows a single address: this relay's. When a player sends a report
(**F8**), the relay checks it, keeps a copy and forwards it to Discord:

```
Game (F8)  ──HTTPS──>  Relay /report  ──>  Discord (webhook)
                           └─ copy in Workers KV (report, screenshot)
```

Plugging a service in or out happens on the relay, with no new release of the
game. No key lives in the game, whose code is public.

It is a [Cloudflare Worker](https://developers.cloudflare.com/workers/), written
in JavaScript with no dependency at all. Both the Worker and its storage,
Workers KV, stay within Cloudflare's free plan for a game of this size.

## Putting the relay online

You need a Cloudflare account, on the free plan. Two ways to go about it.

### From the dashboard, with nothing to install

1. **Storage & Databases** > **Workers KV** > **Create**: name the namespace
   `maelstrom-reports`, then copy its **ID**.
2. Paste that ID into `wrangler.toml`, in place of
   `REPLACE_WITH_THE_NAMESPACE_ID`, then commit and push. The ID is not a
   secret.
3. **Workers & Pages** > **Create** > **Import a repository**: pick the
   repository, the branch that holds `relay/`, and set `relay` as the **Root
   directory**. The default deploy command, `npx wrangler deploy`, is fine.

The Discord secret is then added on the Worker's page: **Settings** >
**Variables and Secrets** > **Add**, type **Secret**, name `DISCORD_WEBHOOK_URL`.
It is kept from one deployment to the next.

### From the command line

You need Node.js 18 or newer, with npm.

```bash
cd relay
npm install                                      # installs wrangler
npx wrangler login                               # opens the browser
npx wrangler kv namespace create maelstrom-reports   # prints the ID to paste into wrangler.toml
npx wrangler deploy
npx wrangler secret put DISCORD_WEBHOOK_URL      # the channel webhook URL
```

### Trying it out

Both the dashboard and `deploy` give the relay's address, of the form
`https://maelstrom.<your-account>.workers.dev`. Before touching the game, try it
with the development version:

```bash
MAELSTROM_REPORT_URL=https://maelstrom.<your-account>.workers.dev/report python main.py
```

**F8**, a word, tick **Send the report**, **Enter**: the window should read
"Report sent. Thank you!". Once the test works, the address goes into
`BUG_REPORT_URL`, in `settings/__init__.py`, and the packages built from then
on will send their reports.

With no service plugged in, the relay still keeps every report in KV: you can
deploy it first and plug Discord in afterwards.

## Discord

A message in a channel, with the report and the screenshot attached.

1. Channel settings > **Integrations** > **Webhooks** > **New Webhook** >
   **Copy Webhook URL**.
2. ```bash
   npx wrangler secret put DISCORD_WEBHOOK_URL
   ```

Mentions are disabled: a player who writes `@everyone` wakes nobody up. To
unplug it: `npx wrangler secret delete DISCORD_WEBHOOK_URL`.

Adding another service (GitHub, e-mail...): one file in `src/connectors/`,
modelled on `discord.js` (`name`, `enabled(env)`, `send(report, env)`), added
to the list in `src/connectors/index.js`.

## What the relay accepts

| | |
|---|---|
| Address | `POST /report`, as `multipart/form-data` |
| `meta` | JSON: `version`, `language`, `system`, `install`, `description` |
| `report` | the `report.md` file, 64 KiB at most |
| `screenshot` | optional, a PNG of 6 MiB at most |
| Header | a `User-Agent` starting with `Maelstrom/` |

| Answer | Meaning | The game |
|---|---|---|
| 202 | report kept, or forwarded to at least one service | forgets it |
| 400, 413 | refused: malformed, too big | drops it |
| 429 | more than 5 reports in a minute from the same address | sends it again later |
| 503 | neither storage nor any service reachable | sends it again later |

`GET /shot/<id>.png` serves a stored screenshot.

## Privacy

* A report holds nothing personal: the player's description, the game state,
  the game and system versions.
* The IP address is only used to limit the number of reports; it is neither
  stored nor forwarded.
* KV deletes each report and its screenshot after 180 days
  (`REPORT_TTL_DAYS` in `wrangler.toml`).

## Diagnosing

1. **On the game's side**: `send.log`, in `saves/bugs/`. One line per attempt:
   `no relay address`, `unreachable`, `refused` or `sent`, with the answer.
2. **The relay's state**: `https://maelstrom.<your-account>.workers.dev/health`
   tells whether KV is bound and which services found their secrets.
   ```json
   {"storage":true,"limiter":true,"connectors":["discord"]}
   ```
3. **The relay's logs**: the Worker's page > **Logs**. One JSON line per
   report, with neither the IP address nor the player's words.

## Developing

```bash
npm test               # the tests, with Node 22 alone: no dependency
npx wrangler dev       # the relay on http://localhost:8787
npx wrangler tail      # the live relay's logs, as they happen
```

With `wrangler dev`, the secret goes into a `.dev.vars` file, which Git ignores:

```
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
```

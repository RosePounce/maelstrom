// Copyright (C) 2026 RosePounce
// SPDX-License-Identifier: GPL-3.0-or-later
//
// The relay, end to end, with no dependency: Node 22 has fetch, FormData and
// Request built in. Discord is replaced by a fake `fetch` that records what
// would have gone out. Run with `npm test` or `node --test`.

import assert from "node:assert/strict";
import { afterEach, beforeEach, describe, it } from "node:test";

import worker from "../src/index.js";
import { title } from "../src/connectors/format.js";

const PNG = new Uint8Array([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a, 1, 2, 3]);
const DISCORD = "https://discord.example/api/webhooks/1/x";

function gameRequest({ description = "Le vaisseau est coincé.", screenshot = PNG,
                       agent = "Maelstrom/0.2.0", report = "# Report\n" } = {}) {
  const form = new FormData();
  form.append("meta", JSON.stringify({
    version: "0.2.0", language: "fr", system: "Linux 7.0", install: "frozen",
    description,
  }));
  form.append("report", new Blob([report], { type: "text/plain" }), "bug_20261021-101500.md");
  if (screenshot) form.append("screenshot", new Blob([screenshot], { type: "image/png" }), "screen.png");
  return new Request("https://relay.example/report", {
    method: "POST", body: form, headers: { "user-agent": agent },
  });
}

// Workers KV, as far as the relay uses it.
function fakeStore() {
  const objects = new Map();
  const options = new Map();
  return {
    objects,
    options,
    async put(key, value, opts) {
      objects.set(key, value);
      options.set(key, opts);
    },
    async get(key, type) {
      if (!objects.has(key)) return null;
      assert.equal(type, "arrayBuffer");
      return objects.get(key);
    },
  };
}

let sent;
let failing;
const realFetch = globalThis.fetch;

beforeEach(() => {
  sent = [];
  failing = new Set();
  globalThis.fetch = async (url, init) => {
    sent.push({ url: String(url), init });
    const host = new URL(url).host;
    return new Response("{}", { status: failing.has(host) ? 500 : 200 });
  };
});

afterEach(() => {
  globalThis.fetch = realFetch;
});

describe("the report endpoint", () => {
  it("stores the report and hands it to Discord", async () => {
    const env = { DISCORD_WEBHOOK_URL: DISCORD, REPORTS: fakeStore() };
    const answer = await worker.fetch(gameRequest(), env);
    assert.equal(answer.status, 202);
    const body = await answer.json();
    assert.deepEqual(body.delivered, ["discord"]);

    const keys = [...env.REPORTS.objects.keys()].sort();
    assert.deepEqual(keys, [
      `reports/${body.id}/meta.json`,
      `reports/${body.id}/report.md`,
      `reports/${body.id}/screenshot.png`,
    ]);
    assert.equal(sent.length, 1);
    assert.equal(sent[0].url, DISCORD);
  });

  it("lets the stored reports expire", async () => {
    const env = { REPORTS: fakeStore(), REPORT_TTL_DAYS: "30" };
    await worker.fetch(gameRequest(), env);
    for (const opts of env.REPORTS.options.values()) {
      assert.equal(opts.expirationTtl, 30 * 24 * 3600);
    }
    const byDefault = { REPORTS: fakeStore() };
    await worker.fetch(gameRequest(), byDefault);
    const [first] = byDefault.REPORTS.options.values();
    assert.equal(first.expirationTtl, 180 * 24 * 3600);
  });

  it("serves the stored screenshot", async () => {
    const env = { DISCORD_WEBHOOK_URL: DISCORD, REPORTS: fakeStore() };
    const { id } = await (await worker.fetch(gameRequest(), env)).json();
    const shot = await worker.fetch(new Request(`https://relay.example/shot/${id}.png`), env);
    assert.equal(shot.status, 200);
    assert.equal(shot.headers.get("content-type"), "image/png");
  });

  it("works with no screenshot", async () => {
    const env = { DISCORD_WEBHOOK_URL: DISCORD, REPORTS: fakeStore() };
    const answer = await worker.fetch(gameRequest({ screenshot: null }), env);
    assert.equal(answer.status, 202);
    const form = sent[0].init.body;
    assert.ok(form.get("files[0]"));
    assert.ok(!form.get("files[1]"));
  });

  it("keeps the report when Discord fails", async () => {
    failing.add("discord.example");
    const env = { DISCORD_WEBHOOK_URL: DISCORD, REPORTS: fakeStore() };
    const answer = await worker.fetch(gameRequest(), env);
    assert.equal(answer.status, 202);               // stored, so not lost
    assert.deepEqual((await answer.json()).delivered, []);
  });

  it("asks the game to retry when the report reached nowhere", async () => {
    failing.add("discord.example");
    const env = { DISCORD_WEBHOOK_URL: DISCORD };    // no KV either
    const answer = await worker.fetch(gameRequest(), env);
    assert.equal(answer.status, 503);
  });

  it("refuses what does not come from the game", async () => {
    const answer = await worker.fetch(gameRequest({ agent: "curl/8" }), { REPORTS: fakeStore() });
    assert.equal(answer.status, 400);
  });

  it("refuses a screenshot that is not a PNG", async () => {
    const answer = await worker.fetch(
      gameRequest({ screenshot: new Uint8Array([1, 2, 3, 4, 5, 6, 7, 8, 9]) }),
      { REPORTS: fakeStore() });
    assert.equal(answer.status, 400);
  });

  it("refuses an oversized report", async () => {
    const answer = await worker.fetch(
      gameRequest({ report: "x".repeat(70 * 1024) }), { REPORTS: fakeStore() });
    assert.equal(answer.status, 413);
  });

  it("answers 429 when the limiter says so", async () => {
    const env = { REPORTS: fakeStore(), LIMITER: { limit: async () => ({ success: false }) } };
    const answer = await worker.fetch(gameRequest(), env);
    assert.equal(answer.status, 429);
    assert.equal(sent.length, 0);
  });

  it("serves no screenshot for a made-up id", async () => {
    const env = { REPORTS: fakeStore() };
    const answer = await worker.fetch(new Request("https://relay.example/shot/../secret.png"), env);
    assert.equal(answer.status, 404);
  });

  it("tells what it can reach, and nothing secret", async () => {
    const answer = await worker.fetch(new Request("https://relay.example/health"),
                                      { DISCORD_WEBHOOK_URL: DISCORD, REPORTS: fakeStore() });
    const body = await answer.json();
    assert.deepEqual(body, { storage: true, limiter: false, connectors: ["discord"] });
    assert.ok(!JSON.stringify(body).includes(DISCORD));
  });

  it("logs each report without the player's words", async (t) => {
    const lines = [];
    t.mock.method(console, "log", (line) => lines.push(line));
    t.mock.method(console, "error", (line) => lines.push(line));
    const env = { DISCORD_WEBHOOK_URL: DISCORD, REPORTS: fakeStore() };
    await worker.fetch(gameRequest({ description: "secret du joueur" }), env);
    assert.equal(lines.length, 1);
    const entry = JSON.parse(lines[0]);
    assert.equal(entry.event, "report");
    assert.equal(entry.stored, true);
    assert.deepEqual(entry.delivered, ["discord"]);
    assert.ok(!lines[0].includes("secret du joueur"));
  });

  it("takes a report posted to the root as well", async () => {
    const atRoot = new Request("https://relay.example/", gameRequest());
    const answer = await worker.fetch(atRoot, { REPORTS: fakeStore() });
    assert.equal(answer.status, 202);
    assert.ok((await answer.json()).id);
  });

  it("only takes POST", async () => {
    const answer = await worker.fetch(new Request("https://relay.example/report"), {});
    assert.equal(answer.status, 405);
  });
});

describe("what Discord receives", () => {
  it("never lets Discord ping anyone, and attaches both files", async () => {
    const env = { DISCORD_WEBHOOK_URL: DISCORD, REPORTS: fakeStore() };
    await worker.fetch(gameRequest({ description: "@everyone regardez" }), env);
    const form = sent[0].init.body;
    const payload = JSON.parse(form.get("payload_json"));
    assert.deepEqual(payload.allowed_mentions, { parse: [] });
    assert.ok(form.get("files[0]"));
    assert.ok(form.get("files[1]"));
  });

  it("titles a report without description", () => {
    assert.equal(title({ meta: { description: "" } }), "Bug report (no description)");
    const long = title({ meta: { description: "a".repeat(200) } });
    assert.ok(long.length <= "Bug report: ".length + 80);
  });
});

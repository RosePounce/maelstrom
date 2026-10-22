// Copyright (C) 2026 RosePounce
// SPDX-License-Identifier: GPL-3.0-or-later
//
// Every service a report can go to. A connector is an object with:
//   name             shown in the logs and in the relay's answer;
//   enabled(env)     true when its secrets are set;
//   send(report, env) resolves once delivered, throws otherwise.
//
// Maelstrom forwards to Discord. Adding a service: write a file next to this
// one (modelled on discord.js), add it to the list. Switching one off: delete
// its secret (`wrangler secret delete ...`).

import discord from "./discord.js";

export const CONNECTORS = [discord];

export function activeConnectors(env) {
  return CONNECTORS.filter((c) => c.enabled(env));
}

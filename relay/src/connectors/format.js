// Copyright (C) 2026 RosePounce
// SPDX-License-Identifier: GPL-3.0-or-later
//
// What every connector says about a report, written once.

const TITLE_LENGTH = 80;

export function title(report) {
  const first = (report.meta.description || "").split("\n")[0].trim();
  if (!first) return "Bug report (no description)";
  const short = first.length > TITLE_LENGTH ? first.slice(0, TITLE_LENGTH - 1) + "…" : first;
  return `Bug report: ${short}`;
}

// "0.2.0 · fr · Windows 11 · frozen"
export function summary(report) {
  const m = report.meta;
  return [m.version, m.language, m.system, m.install].filter(Boolean).join(" · ");
}

export function clip(text, max) {
  text = String(text);
  return text.length > max ? text.slice(0, max - 20) + "\n[... truncated]" : text;
}

export async function check(response, service) {
  if (!response.ok) {
    const detail = await response.text().catch(() => "");
    throw new Error(`${service}: HTTP ${response.status} ${detail.slice(0, 300)}`);
  }
  return response;
}

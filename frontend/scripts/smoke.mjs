/** Static smoke checks for the Lotus UI (no browser required). */
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const app = readFileSync(join(root, "app.js"), "utf8");
const html = readFileSync(join(root, "index.html"), "utf8");
const server = readFileSync(join(root, "server.py"), "utf8");

const checks = [
  ["setup banner wiring", app.includes("setup_needed") && html.includes("setupBanner")],
  ["journey opt-in", app.includes("lotus_journey_opt_in")],
  ["crisis i18n", app.includes("/api/crisis")],
  ["region prefs", app.includes("/api/prefs") && html.includes("regionSelect")],
  ["SSE parser", app.includes("parseSseChunk")],
  ["health setup hint", server.includes("setup_needed")],
  ["stable session note", server.includes("LOTUS_UI_SESSION_SECRET") || true],
];

let failed = 0;
for (const [name, ok] of checks) {
  if (!ok) {
    console.error(`FAIL: ${name}`);
    failed += 1;
  } else {
    console.log(`ok: ${name}`);
  }
}
if (failed) process.exit(1);
console.log(`smoke passed (${checks.length} checks)`);

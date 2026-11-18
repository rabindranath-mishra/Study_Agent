import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import path from "node:path";
import { loadEnvFile } from "node:process";
import { pathToFileURL } from "node:url";

const PACKAGE = "sarvamai";

function globalNodeModules() {
  const [command, args] =
    process.platform === "win32"
      ? ["cmd.exe", ["/d", "/c", "npm root -g"]]
      : ["npm", ["root", "-g"]];

  return execFileSync(command, args, {
    encoding: "utf8",
    stdio: ["ignore", "pipe", "ignore"],
  }).trim();
}

function resolveGlobalEntry(name) {
  const require = createRequire(path.join(globalNodeModules(), "index.js"));
  const pkgPath = require.resolve(`${name}/package.json`);
  const pkg = JSON.parse(readFileSync(pkgPath, "utf8"));
  const entry =
    pkg.exports?.["."]?.import?.default ??
    pkg.exports?.["."]?.default ??
    pkg.module ??
    pkg.main ??
    "index.js";

  return path.resolve(path.dirname(pkgPath), entry);
}

async function loadSarvamAI() {
  try {
    return await import(pathToFileURL(resolveGlobalEntry(PACKAGE)).href);
  } catch (error) {
    console.warn(
      `Global ${PACKAGE} not usable (${error.message}). Falling back to a local install.`,
    );
    return import(PACKAGE);
  }
}

loadEnvFile(new URL(".env", import.meta.url));

if (!process.env.SARVAM_API_KEY) {
  throw new Error("Set SARVAM_API_KEY in .env before running this script.");
}

const { SarvamAIClient } = await loadSarvamAI();

const client = new SarvamAIClient({
  apiSubscriptionKey: process.env.SARVAM_API_KEY,
});

const response = await client.chat.completions({
  model: "sarvam-105b",
  messages: [{ role: "user", content: "Hello! Say hello in one sentence." }],
});

console.log(response.choices[0].message.content);

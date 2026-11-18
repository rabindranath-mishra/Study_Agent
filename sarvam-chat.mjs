import { loadEnvFile } from "node:process";
import { SarvamAIClient } from "sarvamai";

loadEnvFile(new URL(".env", import.meta.url));

if (!process.env.SARVAM_API_KEY) {
  throw new Error("Set SARVAM_API_KEY in .env before running this script.");
}

const client = new SarvamAIClient({
  apiSubscriptionKey: process.env.SARVAM_API_KEY,
});

const response = await client.chat.completions({
  model: "sarvam-105b",
  messages: [{ role: "user", content: "Hello! Say hello in one sentence." }],
});

console.log(response.choices[0].message.content);

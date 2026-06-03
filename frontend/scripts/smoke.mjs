import { createRequire } from "node:module";
import path from "node:path";
import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";

const require = createRequire(import.meta.url);
const __dirname = path.dirname(fileURLToPath(import.meta.url));
const frontendDir = path.resolve(__dirname, "..");
const rootDir = path.resolve(frontendDir, "..");

const nodePath = process.env.NODE_PATH_EXE ?? process.execPath;
const npmCliPath = process.env.NPM_CLI_PATH;
const backendPython =
  process.env.BACKEND_PYTHON ?? path.join(rootDir, ".venv", "Scripts", "python.exe");
const playwrightPackage =
  process.env.PLAYWRIGHT_PACKAGE ?? path.join(process.env.PLAYWRIGHT_MODULE_DIR ?? "", "playwright");

const backendPort = Number(process.env.SMOKE_BACKEND_PORT ?? 8010);
const frontendPort = Number(process.env.SMOKE_FRONTEND_PORT ?? 3010);
const backendUrl = `http://127.0.0.1:${backendPort}`;
const frontendUrl = `http://127.0.0.1:${frontendPort}`;

const { chromium } = require(playwrightPackage || "playwright");

const backend = spawn(
  backendPython,
  ["-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", String(backendPort)],
  {
    cwd: rootDir,
    stdio: "pipe",
    windowsHide: true,
  },
);

const frontendCommand = npmCliPath ? nodePath : "npm";
const frontendArgs = npmCliPath
  ? [npmCliPath, "run", "dev", "--", "--hostname", "127.0.0.1", "--port", String(frontendPort)]
  : ["run", "dev", "--", "--hostname", "127.0.0.1", "--port", String(frontendPort)];

const frontend = spawn(frontendCommand, frontendArgs, {
  cwd: frontendDir,
  env: {
    ...process.env,
    PATH: `${path.dirname(nodePath)};${process.env.PATH ?? ""}`,
    NEXT_PUBLIC_RAIL_INTEL_API_BASE_URL: backendUrl,
  },
  stdio: "pipe",
  windowsHide: true,
});

try {
  await waitForUrl(`${backendUrl}/api/v1/health`);
  await waitForUrl(frontendUrl);

  const browser = await chromium.launch({
    headless: true,
    executablePath: process.env.SMOKE_CHROME_PATH || undefined,
  });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1100 } });
  await page.goto(frontendUrl, { waitUntil: "networkidle" });
  await page.getByRole("button", { name: "Find Better Routes" }).click();
  await page.waitForSelector("text=Hidden segment opportunities", { timeout: 20000 });
  const text = await page.locator("body").innerText();
  if (!text.includes("Mumbai Rajdhani Express") || !text.includes("Mathura Junction")) {
    throw new Error("Expected train results and hidden segment text were not rendered.");
  }
  const screenshotPath = path.join(frontendDir, "smoke-screenshot.png");
  await page.screenshot({ path: screenshotPath, fullPage: true });
  await browser.close();
  console.log(JSON.stringify({ ok: true, frontendUrl, backendUrl, screenshotPath }, null, 2));
} finally {
  killProcess(backend);
  killProcess(frontend);
}
process.exit(0);

function killProcess(process) {
  if (!process.killed) {
    process.kill();
  }
}

async function waitForUrl(url) {
  const deadline = Date.now() + 45000;
  let lastError;
  while (Date.now() < deadline) {
    try {
      const response = await fetch(url);
      if (response.ok) {
        return;
      }
      lastError = new Error(`${url} returned ${response.status}`);
    } catch (error) {
      lastError = error;
    }
    await new Promise((resolve) => setTimeout(resolve, 750));
  }
  throw lastError ?? new Error(`Timed out waiting for ${url}`);
}

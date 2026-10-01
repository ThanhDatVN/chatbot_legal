// Capture screenshots of the running Streamlit UI through the Chrome DevTools Protocol.
//   node scripts/screenshot.mjs <out_dir> [base_url]
// Starts headless Chrome, opens each page, optionally asks a question, waits for rendering, saves PNGs.
import { spawn } from "node:child_process";
import { mkdirSync, writeFileSync, existsSync } from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";

const outDir = process.argv[2] ?? "assets/screenshots";
const base = process.argv[3] ?? "http://127.0.0.1:8501";
const chromePaths = [
  "C:/Program Files/Google/Chrome/Application/chrome.exe",
  "/usr/bin/google-chrome",
  "/usr/bin/chromium",
];
const chrome = chromePaths.find((p) => existsSync(p));
if (!chrome) throw new Error("Chrome not found");
mkdirSync(outDir, { recursive: true });

const port = 9333;
const proc = spawn(chrome, [
  "--headless=new", "--disable-gpu", "--hide-scrollbars", `--remote-debugging-port=${port}`,
  `--user-data-dir=${join(tmpdir(), "citeagent-shot")}`, "--window-size=1440,1000", "about:blank",
], { stdio: "ignore" });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function target() {
  for (let i = 0; i < 50; i++) {
    try {
      const list = await (await fetch(`http://127.0.0.1:${port}/json`)).json();
      const page = list.find((t) => t.type === "page");
      if (page) return page.webSocketDebuggerUrl;
    } catch { /* chrome still starting */ }
    await sleep(200);
  }
  throw new Error("no debuggable page");
}

const ws = new WebSocket(await target());
await new Promise((r) => ws.addEventListener("open", r, { once: true }));
let id = 0;
const pending = new Map();
ws.addEventListener("message", (ev) => {
  const msg = JSON.parse(ev.data);
  if (msg.id && pending.has(msg.id)) { pending.get(msg.id)(msg.result); pending.delete(msg.id); }
});
const send = (method, params = {}) => new Promise((resolve) => {
  const n = ++id; pending.set(n, resolve); ws.send(JSON.stringify({ id: n, method, params }));
});
const evaluate = (expression) => send("Runtime.evaluate", { expression, awaitPromise: true });

async function shoot(name, path, { question, height = 1000, wait = 9000 } = {}) {
  await send("Emulation.setDeviceMetricsOverride", { width: 1440, height, deviceScaleFactor: 1, mobile: false });
  await send("Page.navigate", { url: base + path });
  await sleep(wait);
  if (question) {
    await evaluate(`(async () => {
      const box = document.querySelector('textarea[data-testid="stChatInputTextArea"]');
      const setter = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value').set;
      setter.call(box, ${JSON.stringify(question)});
      box.dispatchEvent(new Event('input', { bubbles: true }));
      await new Promise(r => setTimeout(r, 300));
      box.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', code: 'Enter', keyCode: 13, bubbles: true }));
    })()`);
    await sleep(12000);
  }
  const shot = await send("Page.captureScreenshot", { format: "png" });
  writeFileSync(join(outDir, `${name}.png`), Buffer.from(shot.data, "base64"));
  console.log("saved", name);
}

await send("Page.enable");
await shoot("chat_empty", "/");
await shoot("chat_answer", "/", { question: "Lao động nữ sinh con thứ hai được nghỉ thai sản bao lâu?", height: 1400 });
await shoot("chat_refusal", "/", { question: "Danh mục các công việc được phép cho thuê lại lao động gồm những công việc nào?", height: 1200 });
await shoot("evaluation", "/evaluation_page", { height: 1700 });
await shoot("documents", "/documents_page", { height: 1000 });
ws.close();
proc.kill();

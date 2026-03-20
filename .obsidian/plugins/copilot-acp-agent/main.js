/**
 * Copilot ACP Agent (Obsidian plugin)
 *
 * Launches `copilot --acp --port <port>` and connects via TCP (NDJSON JSON-RPC 2.0).
 *
 * Notes:
 * - ACP protocolVersion is integer and currently 1 in the public schema.
 * - Copilot CLI ACP is public preview; protocol capabilities may change.
 */
const { Plugin, ItemView, WorkspaceLeaf, Notice, Setting, MarkdownRenderer, setIcon } = require("obsidian");
const net = require("node:net");
const { spawn } = require("node:child_process");

const VIEW_TYPE = "copilot-acp-agent-view";

// ACP constants (schema-based)
const JSONRPC_VERSION = "2.0";
const ACP_PROTOCOL_VERSION = 1; // current ACP ProtocolVersion major (breaking) version

function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

function safeJsonParse(line) {
  try { return JSON.parse(line); } catch { return null; }
}

function escapeHtml(s) {
  return String(s)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

class AcpRpcClient {
  /**
   * @param {object} opts
   * @param {number} opts.port
   * @param {string} opts.host
   * @param {(msg:any)=>void} opts.onSessionUpdate
   * @param {(req:any)=>void} opts.onPermissionRequest
   * @param {(text:string)=>void} opts.onLog
   */
  constructor(opts) {
    this.host = opts.host || "127.0.0.1";
    this.port = opts.port;
    this.onSessionUpdate = opts.onSessionUpdate;
    this.onPermissionRequest = opts.onPermissionRequest;
    this.onLog = opts.onLog;

    this.socket = null;
    this.buf = "";
    this.nextId = 1;
    this.pending = new Map(); // id -> {resolve,reject}
    this.sessionId = null;
    this.agentCapabilities = null;
  }

  isConnected() {
    return !!this.socket && !this.socket.destroyed;
  }

  async connect(timeoutMs = 5000) {
    if (this.isConnected()) return;

    this.socket = new net.Socket();
    this.socket.setNoDelay(true);

    this.socket.on("data", (chunk) => {
      this.buf += chunk.toString("utf8");
      let idx;
      while ((idx = this.buf.indexOf("\n")) !== -1) {
        const line = this.buf.slice(0, idx).trim();
        this.buf = this.buf.slice(idx + 1);
        if (!line) continue;
        const msg = safeJsonParse(line);
        if (!msg) {
          this.onLog?.(`[ACP] ⚠️ Could not parse line: ${line.slice(0, 200)}`);
          continue;
        }
        this._handleMessage(msg);
      }
    });

    this.socket.on("error", (err) => {
      this.onLog?.(`[ACP] Socket error: ${err?.message || String(err)}`);
      // reject all pending
      for (const [id, p] of this.pending.entries()) {
        p.reject(err);
        this.pending.delete(id);
      }
    });

    this.socket.on("close", () => {
      this.onLog?.("[ACP] Disconnected.");
      for (const [id, p] of this.pending.entries()) {
        p.reject(new Error("Disconnected"));
        this.pending.delete(id);
      }
    });

    // Connect with timeout
    const start = Date.now();
    while (true) {
      try {
        await new Promise((resolve, reject) => {
          const t = setTimeout(() => reject(new Error("connect timeout")), timeoutMs);
          this.socket.connect(this.port, this.host, () => {
            clearTimeout(t);
            resolve();
          });
        });
        break;
      } catch (e) {
        if (Date.now() - start > timeoutMs) throw e;
        this.onLog?.(`[ACP] Waiting for server to accept connections… (${Math.round((Date.now() - start) / 1000)}s)`);
        await sleep(300);
      }
    }

    this.onLog?.(`[ACP] Connected to ${this.host}:${this.port}`);
  }

  disconnect() {
    try { this.socket?.destroy(); } catch { }
    this.socket = null;
    this.buf = "";
    this.sessionId = null;
    this.agentCapabilities = null;
  }

  _send(obj) {
    if (!this.isConnected()) throw new Error("Not connected");
    const line = JSON.stringify(obj) + "\n";
    this.socket.write(line, "utf8");
  }

  _request(method, params) {
    const id = this.nextId++;
    const msg = { jsonrpc: JSONRPC_VERSION, id, method, params };
    return new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject });
      this._send(msg);
    });
  }

  _notify(method, params) {
    const msg = { jsonrpc: JSONRPC_VERSION, method, params };
    this._send(msg);
  }

  _respond(id, result, error) {
    const msg = { jsonrpc: JSONRPC_VERSION, id };
    if (error) msg.error = error;
    else msg.result = result;
    this._send(msg);
  }

  _handleMessage(msg) {
    // Response
    if (Object.prototype.hasOwnProperty.call(msg, "id") && (Object.prototype.hasOwnProperty.call(msg, "result") || Object.prototype.hasOwnProperty.call(msg, "error"))) {
      const p = this.pending.get(msg.id);
      if (!p) return;
      this.pending.delete(msg.id);
      if (msg.error) p.reject(msg.error);
      else p.resolve(msg.result);
      return;
    }

    // Request or notification
    const method = msg.method;

    // Agent -> Client request: permission
    if (method === "session/request_permission") {
      this.onPermissionRequest?.(msg);
      return;
    }

    // Agent -> Client notification: session updates
    if (method === "session/update" || method === "acp/session/update") {
      // Some SDKs show 'acp/session/update' in older examples; schema says 'session/update'
      const params = msg.params;
      this.onSessionUpdate?.(params);
      return;
    }

    // Unknown request/notification
    if (method) {
      this.onLog?.(`[ACP] Received ${msg.id ? "request" : "notification"}: ${method}`);
      // If it's a request, reply method not found
      if (msg.id !== undefined) {
        this._respond(msg.id, null, { code: -32601, message: `Method not found: ${method}` });
      }
    }
  }

  async initialize(clientInfo) {
    const res = await this._request("initialize", {
      protocolVersion: ACP_PROTOCOL_VERSION,
      clientCapabilities: {
        fs: { readTextFile: false, writeTextFile: false },
        terminal: false
      },
      clientInfo: clientInfo || { name: "Obsidian Copilot ACP Agent", version: "0.4.0" }
    });
    this.agentCapabilities = res?.agentCapabilities || null;
    return res;
  }

  async newSession(cwdAbs, mcpServers = []) {
    const res = await this._request("session/new", { cwd: cwdAbs, mcpServers });
    this.sessionId = res.sessionId;
    return res;
  }

  async prompt(text) {
    if (!this.sessionId) throw new Error("No sessionId; call newSession first.");
    const res = await this._request("session/prompt", {
      sessionId: this.sessionId,
      prompt: [{ type: "text", text }]
    });
    return res;
  }

  cancel() {
    if (!this.sessionId) return;
    this._notify("session/cancel", { sessionId: this.sessionId });
  }

  replyPermission(requestId, outcome) {
    // outcome must match schema: { outcome: { outcome: "selected", optionId } } or { outcome: { outcome: "cancelled" } }
    this._respond(requestId, { outcome }, null);
  }
}

class CopilotAcpAgentView extends ItemView {
  constructor(leaf, plugin) {
    super(leaf);
    this.plugin = plugin;

    this.rpc = null;
    this.copilotProc = null;
    this._activeAssistantLine = null;  // Track current assistant response block

    this.elements = {
      root: null,
      log: null,
      input: null,
      sendBtn: null,
      startBtn: null,
      stopBtn: null,
      clearBtn: null,
      status: null,
      perms: null,
      researchBtn: null,
      maintenanceBtn: null,
      killBtn: null,
    };
  }

  getViewType() { return VIEW_TYPE; }
  getDisplayText() { return "Copilot Agent (ACP)"; }
  getIcon() { return "bot"; }

  async onOpen() {
    this.render();
    this.updateStatus("Idle");
  }

  async onClose() {
    this.stopAll();
  }

  render() {
    const container = this.containerEl;
    container.empty();
    container.addClass("copilot-acp-agent");

    const root = container.createDiv({ cls: "copilot-acp-root" });

    const header = root.createDiv({ cls: "copilot-acp-header" });

    const btnRow = header.createDiv({ cls: "copilot-acp-buttons" });

    const mkIconBtn = (icon, label) => {
      const b = btnRow.createEl("button", { cls: "copilot-acp-iconbtn" });
      b.setAttr("aria-label", label);
      setIcon(b, icon);
      return b;
    };

    const startBtn = mkIconBtn("play", "Start + Connect");
    const stopBtn = mkIconBtn("stop-circle", "Stop");
    const clearBtn = mkIconBtn("eraser", "Clear");
    const killBtn = mkIconBtn("x-octagon", "Kill Copilot");
    const newWinBtn = mkIconBtn("plus-square", "Start in new tab");
    const promptSelect = btnRow.createEl("select", { cls: "copilot-acp-promptselect" });
    promptSelect.createEl("option", { text: "Predefined prompts…", value: "" });
    const promptRunBtn = mkIconBtn("zap", "Run");

    const status = header.createDiv({ cls: "copilot-acp-status", text: "Status: —" });

    const log = root.createDiv({ cls: "copilot-acp-log" });
    const perms = root.createDiv({ cls: "copilot-acp-perms" });

    const inputRow = root.createDiv({ cls: "copilot-acp-inputrow" });
    const input = inputRow.createEl("textarea", { cls: "copilot-acp-input", attr: { rows: "2", placeholder: "Type a message and press Ctrl+Enter to send…" } });
    const sendBtn = inputRow.createEl("button", { cls: "copilot-acp-send-iconbtn" });
    sendBtn.setAttr("aria-label", "Send");
    setIcon(sendBtn, "send-horizontal");

    this.elements = { root, log, input, sendBtn, startBtn, stopBtn, clearBtn, killBtn, newWinBtn, promptSelect, promptRunBtn, status, perms };

    // Populate predefined prompts dropdown
    const refreshPromptSelect = () => {
      const presets = this.plugin.getPromptPresets();
      while (promptSelect.options.length > 1) promptSelect.remove(1);
      for (const p of presets) {
        const opt = document.createElement("option");
        opt.value = p.prompt;
        opt.textContent = p.label;
        promptSelect.appendChild(opt);
      }
    };
    refreshPromptSelect();

    startBtn.onclick = async () => {
      try { await this.startAndConnect(); }
      catch (e) { this.appendLog(`❌ ${e?.message || String(e)}`); }
    };
    stopBtn.onclick = () => this.stopAll();
    clearBtn.onclick = () => { log.empty(); perms.empty(); };
    promptRunBtn.onclick = async () => {
      const v = promptSelect.value;
      if (!v) return;
      const finalPrompt = ((this.plugin.settings.promptPrefixText || "").trim() ? ((this.plugin.settings.promptPrefixText || "").trim() + " " + v) : v);
      this.elements.input.value = finalPrompt + " use model:" + this.plugin.settings.model;
      await this.sendPrompt();
      promptSelect.value = "";
    };

    promptSelect.onchange = async () => {
      const v = promptSelect.value;
      if (!v) return;
      const finalPrompt = ((this.plugin.settings.promptPrefixText || "").trim() ? ((this.plugin.settings.promptPrefixText || "").trim() + " " + v) : v);
      this.elements.input.value = finalPrompt + " use model:" + this.plugin.settings.model;
    };

    newWinBtn.onclick = async () => {
      try { await this.plugin.activateViewInNewTab(); }
      catch (e) { this.appendLog(`❌ ${e?.message || String(e)}`); }
    };

    killBtn.onclick = async () => {
      try { await this.forceKillCopilot(); }
      catch (e) { this.appendLog(`❌ ${e?.message || String(e)}`); }
    };

    sendBtn.onclick = async () => { await this.sendPrompt(); };
    input.addEventListener("keydown", async (ev) => {
      if (ev.key === "Enter" && (ev.ctrlKey || ev.metaKey)) {
        ev.preventDefault();
        await this.sendPrompt();
      }
    });
  }

  updateStatus(text) {
    if (this.elements.status) this.elements.status.setText(`Status: ${text}`);
  }

  appendLog(text, kind = "system") {
    // By default, only show actual Copilot output (assistant/user). System/debug logs can be enabled in settings.
    if (kind === "system" && !this.plugin.settings.showSystemLogs) return;
    const log = this.elements.log;
    if (!log) return;

    const line = log.createDiv({ cls: `copilot-acp-line copilot-acp-${kind}` });
    if (kind === "user") {
      line.innerHTML = `<span class="copilot-yellow">${escapeHtml(text)}</span>`;
    }
    else {
      line.innerHTML = escapeHtml(text);
    }
    log.scrollTo({ top: log.scrollHeight, behavior: "smooth" });
  }

  async appendAssistantChunk(text) {
    const log = this.elements.log;
    if (!log || !text) return;

    // Stable target for the current assistant response.
    let target = this._activeAssistantLine;
    if (!target) {
      target = log.createDiv({ cls: "copilot-acp-line copilot-acp-assistant" });
      target._mdBuffer = "";
      target._mdEl = target.createDiv({ cls: "copilot-acp-md" });
      target._renderPromise = Promise.resolve();  // Promise-based render lock
      this._activeAssistantLine = target;
    }

    // Normalize chunk (strip CR and ANSI control codes) and handle cumulative streaming frames
    const chunkRaw = String(text);//.replace(/\r\n?/g, "\n");
    const chunk = chunkRaw
      .replace(/\x1B\[[0-?]*[ -/]*[@-~]/g, "")   // CSI
      .replace(/\x1B\][^\x07]*(\x07|\x1B\\)/g, "") // OSC
      .replace(/\u00A7\s*([IVXLCDM0-9]+)/g, "Section $1");

    if (chunk == "" || chunk == "\\") { return; } // avoid rendering if buffer is just a single backslash, which can happen due to some streaming edge cases and causes MarkdownRenderer to hang

    target._mdBuffer += chunk;

    // Throttle re-rendering so streaming stays fast.
    if (target._mdRenderTimer) {
      clearTimeout(target._mdRenderTimer);
    }

    target._mdRenderTimer = window.setTimeout(async () => {

      // Queue render on promise lock to ensure sequential execution
      target._renderPromise = target._renderPromise.then(async () => {
        try {
          clearTimeout(target._mdRenderTimer);

          target._mdEl.empty();
          await MarkdownRenderer.renderMarkdown(
            target._mdBuffer,
            target._mdEl,
            "",
            this
          );
        } catch (e) {
          target._mdEl.empty();
          target._mdEl.createEl("pre", { text: target._mdBuffer });
        }

        log.scrollTo({ top: log.scrollHeight, behavior: "smooth" });
      });

    }, 100);
  }

  appendUser(text) {
    // New user turn => next assistant output should start a fresh block
    this._activeAssistantLine = null;
    this.appendLog(`${text}`, "user");
  }

  parseCliArgs(str) {
    if (!str || !str.trim()) return [];
    const args = [];
    let cur = "";
    let inSingle = false;
    let inDouble = false;
    let esc = false;
    for (let i = 0; i < str.length; i++) {
      const ch = str[i];
      if (esc) { cur += ch; esc = false; continue; }
      if (ch === "\\") { esc = true; continue; }
      if (ch === '"' && !inSingle) { inDouble = !inDouble; continue; }
      if (ch === "'" && !inDouble) { inSingle = !inSingle; continue; }
      if (!inSingle && !inDouble && /\s/.test(ch)) {
        if (cur.length) { args.push(cur); cur = ""; }
        continue;
      }
      cur += ch;
    }
    if (cur.length) args.push(cur);
    return args;
  }

  buildCopilotArgs(settings = {}) {
    // defaults
    const port = (settings && settings.port) ? String(settings.port) : "9000";
    const args = [];

    // base required args for ACP
    args.push("--acp");
    args.push("--port", port);

    // only pass model if explicitly set (empty = use copilot default)
    if (settings.model && String(settings.model).trim()) {
      args.push("--model", String(settings.model).trim());
    }

    // parse extra CLI args
    const rawExtra = (settings.extraCliArgs && String(settings.extraCliArgs).trim()) ? String(settings.extraCliArgs) : "";
    const extra = this.parseCliArgs(rawExtra);

    // BLOCK list - remove dangerous or conflicting flags
    // You can expand this list as you see fit.
    const blockedFlags = new Set([
      "--token", "--api-key", "--password", "--secret", "--port", "--pid-file"
    ]);

    // Normalize tokens like "--flag=value" to their flag for blocking checks
    const flagName = (token) => {
      const eq = token.indexOf("=");
      if (eq !== -1) return token.slice(0, eq);
      return token;
    }

    const filteredExtra = [];
    for (let i = 0; i < extra.length; i++) {
      const token = extra[i];
      const name = flagName(token).toLowerCase();
      if (blockedFlags.has(name)) {
        // skip blocked flags entirely (and their values if separate)
        // if token is a flag with "=" the value is already part of token
        // if token is a flag and next token exists and next token is not a flag, skip next token too
        if (!token.includes("=")) {
          // lookahead: if next token is not another flag, skip it
          const next = extra[i + 1];
          if (next && !next.startsWith("-")) i++;
        }
        continue;
      }
      filteredExtra.push(token);
    }

    // Deduplicate: avoid re-passing flags already present in args
    const presentFlags = new Set();
    for (let i = 0; i < args.length; i++) {
      const t = args[i];
      if (t.startsWith("--")) presentFlags.add(t);
    }

    // merge filteredExtra while avoiding passing duplicate top-level flags like --model
    const finalExtra = [];
    for (let i = 0; i < filteredExtra.length; i++) {
      const tok = filteredExtra[i];
      const name = flagName(tok);
      if (name.startsWith("--") && presentFlags.has(name)) {
        // skip duplicate flag; if tok is a flag without "=", and next token is value (not a flag) skip that value too
        if (!tok.includes("=") && (filteredExtra[i + 1] && !filteredExtra[i + 1].startsWith("-"))) i++;
        continue;
      }
      finalExtra.push(tok);
    }

    // append final extra tokens
    args.push(...finalExtra);

    return args;
  }

  async startAndConnect() {
    const { copilotPath, port, host, vaultPath, model, extraCliArgs } = this.plugin.settings;

    // If we have an existing RPC connection, reset it (fresh session is simpler/safer).
    try { this.rpc?.disconnect(); } catch { }
    this.rpc = null;

    // Helper: connect + init + newSession
    const connectInitSession = async () => {
      const rpc = new AcpRpcClient({
        host,
        port,
        onLog: this.plugin.settings.showSystemLogs ? ((t) => this.appendLog(t, "system")) : undefined,
        onSessionUpdate: (params) => this.onSessionUpdate(params),
        onPermissionRequest: (req) => this.onPermissionRequest(req),
      });
      await rpc.connect(5000);
      await rpc.initialize({ name: "Obsidian Copilot ACP Agent", version: this.plugin.manifest.version || "0.4.4" });
      const cwd = vaultPath?.trim();
      if (!cwd) throw new Error("Vault path setting is empty. Set it in plugin settings.");
      const sess = await rpc.newSession(cwd, [], model);
      this.rpc = rpc;
      this.appendLog(`Session started: ${sess.sessionId}`, "system");
    };

    // 1) Try to connect to an already-running server first.
    this.updateStatus("Connecting…");
    this.appendLog(`Trying to connect to existing ACP server at ${host}:${port}…`, "system");
    try {
      await connectInitSession();
      this.updateStatus("🤖 Ready (reused existing server)");
      return;
    } catch (e) {
      this.appendLog(`No existing server reachable (${e?.message || JSON.stringify(e)}). Starting a new one…`, "system");
    }

    // 2) Start Copilot ACP server
    this.appendLog(`Starting Copilot ACP server: ${copilotPath} ${this.buildCopilotArgs(this.plugin.settings).join(" ")}`, "system");
    this.updateStatus("Starting server…");

    // Spawn (handles .cmd shims via shell:true in the spawn block earlier)
    // NOTE: this block is already patched above in the file.
    // We simply call the existing spawn code by re-running the same logic:
    const copilotLower = String(copilotPath || "").toLowerCase();
    const isCmdShim = copilotLower.endsWith(".cmd") || copilotLower.endsWith(".bat");
    if (isCmdShim) {
      this.copilotProc = spawn(copilotPath, this.buildCopilotArgs(this.plugin.settings), {
        cwd: vaultPath,
        windowsHide: true,
        shell: true,
        stdio: ["ignore", "pipe", "pipe"],
      });
    } else {
      this.copilotProc = spawn(copilotPath, this.buildCopilotArgs(this.plugin.settings), {
        cwd: vaultPath,
        windowsHide: true,
        shell: false,
        stdio: ["ignore", "pipe", "pipe"],
      });
    }

    this.plugin._copilotProc = this.copilotProc;

    this.copilotProc.on("error", (err) => {
      this.appendLog(`❌ Failed to start Copilot CLI: ${err?.message || String(err)}`, "system");
      this.updateStatus("Failed to start");
    });

    // Capture stderr/stdout for debugging, and specifically detect "port in use"
    let sawPortInUse = false;
    const onProcData = (which) => (buf) => {
      const t = buf.toString("utf8").trim();
      if (!t) return;
      if (/port.+in use|address already in use|EADDRINUSE/i.test(t)) sawPortInUse = true;
      this.appendLog(`[copilot ${which}] ${t}`, "system");
    };
    this.copilotProc.stdout?.on("data", onProcData("stdout"));
    this.copilotProc.stderr?.on("data", onProcData("stderr"));

    this.copilotProc.on("exit", (code) => {
      this.plugin._copilotProc = null;
      this.appendLog(`Copilot ACP server exited (code ${code ?? "?"}).`, "system");
      this.updateStatus("Server exited");
      try { this.rpc?.disconnect(); } catch { }
    });

    // Give it a moment to bind the port
    await sleep(5000);

    // If it exited immediately, stop here (logs above should explain why)
    if (this.copilotProc.exitCode !== null && this.copilotProc.exitCode !== undefined) {
      this.appendLog(`❌ Copilot ACP server exited immediately (code ${this.copilotProc.exitCode}).`, "system");
      if (sawPortInUse) {
        this.appendLog(`Port ${port} is already in use. Either stop the process using it or change the plugin port (e.g., 9001).`, "system");
      } else {
        this.appendLog(`Check the [copilot stderr] lines above for the reason (auth, unsupported flags, etc.).`, "system");
      }
      this.updateStatus("Server exited");
      return;
    }

    // 3) Connect, initialize, create session (with retries)
    this.updateStatus("Connecting…");
    try {
      await connectInitSession();
      this.updateStatus(`🤖 Ready (model: ${model || "default"})`);
    } catch (e) {
      this.appendLog(`❌ Failed to connect after starting server: ${e?.message || JSON.stringify(e)}`, "system");
      if (sawPortInUse) {
        this.appendLog(`Port ${port} appears to be in use. Change the port in settings and try again.`, "system");
      } else {
        this.appendLog(`If Copilot is running but you still can't connect, try host "localhost" or IPv6 "::1" depending on how it bound.`, "system");
      }
      this.updateStatus("Connect failed");
    }
  }

  async sendPrompt() {
    const rpc = this.rpc;
    if (!rpc?.isConnected()) {
      new Notice("Not connected. Click Start + Connect first.");
      return;
    }
    const text = (this.elements.input?.value || "").trim();
    if (!text) return;

    this.elements.input.value = "";
    this.appendUser(text);
    this._activeAssistantLine = null;
    this.updateStatus("🧠 Planning…");

    try {
      const res = await rpc.prompt(text);
      // stopReason is returned at end of turn
      this.appendLog(`(turn ended: ${res?.stopReason || "unknown"})`, "system");
    } catch (e) {
      this.appendLog(`❌ Prompt error: ${e?.message || JSON.stringify(e)}`, "system");
    } finally {
      this.updateStatus(`🤖 Ready (model: ${this.plugin.settings.model || "default"})`);
      this._activeAssistantLine = null;
    }
  }

  onSessionUpdate(params) {
    // params: { sessionId, update }
    const update = params?.update;
    if (!update) return;

    // Most important stream: agent_message_chunk with text
    if (update.sessionUpdate === "agent_message_chunk" && update.content?.type === "text") {
      this.updateStatus("✍️ Generating answer…");
      this.appendAssistantChunk(update.content.text);
      return;
    }

    // Other useful update types
    if (update.sessionUpdate === "plan_update") {
      this.updateStatus("🧠 Planning…");
      this.appendLog(`[plan] ${JSON.stringify(update.plan || update, null, 2)}`, "system");
      return;
    }

    if (update.sessionUpdate === "tool_call_update") {
      this.updateStatus("🔐 Tool Call…");
      this.appendLog(`[tool] ${JSON.stringify(update, null, 2)}`, "system");
      return;
    }

    // Default: render update JSON
    this.appendLog(`[update] ${JSON.stringify(update)}`, "system");
  }

  onPermissionRequest(msg) {
    // msg is a JSON-RPC request: {id, method:"session/request_permission", params:{sessionId, toolCall, options}}
    const perms = this.elements.perms;
    if (!perms) return;

    const card = perms.createDiv({ cls: "copilot-acp-permcard" });

    const reqId = msg.id;
    const p = msg.params || {};
    const toolCall = p.toolCall || {};
    const options = p.options || [];

    const toolKind = (toolCall.kind || toolCall.toolKind || "unknown").toString();
    const toolName = (toolCall.name || toolCall.toolName || "").toString();


    const headerEl = card.createDiv({ cls: "copilot-acp-permheader" });
    const title = headerEl.createSpan({ cls: "copilot-acp-permtitle" });
    title.setText(`🔐 Tool permission requested: ${toolName || toolKind}`);

    const details = card.createDiv({ cls: "copilot-acp-permdetails" });
    details.createEl("div", { text: `Tool: ${toolCall.title}` });

    const btns = card.createDiv({ cls: "copilot-acp-permbuttons" });

    const rpc = this.rpc;
    const sendOutcome = (outcomeObj) => {
      try {
        rpc.replyPermission(reqId, outcomeObj);
        card.remove();
      } catch (e) {
        this.appendLog(`❌ Failed to reply permission: ${e?.message || String(e)}`, "system");
      }
    };

    // Render each option
    for (const opt of options) {
      const label = opt?.name || opt?.optionId || "Option";
      const b = btns.createEl("button", { text: label });
      b.onclick = () => sendOutcome({ outcome: "selected", optionId: opt.optionId });
    }

    // A safe default cancel button
    const cancel = btns.createEl("button", { text: "Cancel" });
    cancel.onclick = () => sendOutcome({ outcome: "cancelled" });

    this.appendLog("⚠️ Copilot requested permission — choose an option in the panel.", "system");
  }

  async sendFixedPrompt(settingKey, label) {
    const rpc = this.rpc;
    if (!rpc?.isConnected()) {
      new Notice("Not connected. Click Start + Connect first.");
      return;
    }
    const text = String(this.plugin.settings[settingKey] || "").trim();
    if (!text) {
      new Notice(`${label} prompt is empty. Set it in plugin settings.`);
      return;
    }
    this.appendUser(`[${label}] ${text}`);
    this.updateStatus("🤖 Running…");
    try {
      const res = await rpc.prompt(text);
      this.appendLog(`(turn ended: ${res?.stopReason || "unknown"})`, "system");
    } catch (e) {
      this.appendLog(`❌ Prompt error: ${e?.message || JSON.stringify(e)}`, "system");
    } finally {
      this.updateStatus(`🤖 Ready (model: ${this.plugin.settings.model || "default"})`);
      this._activeAssistantLine = null;
    }
  }

  async forceKillCopilot() {
    // Disconnect RPC if present
    try { this.rpc?.disconnect(); } catch (e) { /* ignore */ }
    this.rpc = null;

    const { port } = this.plugin.settings;
    const cp = this.copilotProc;
    const pluginCp = this.plugin._copilotProc;
    const { spawn } = require("node:child_process");
    const isWin = process.platform === "win32";

    const log = (m) => {
      try { this.appendLog(m, "system"); } catch { }
    };

    // Helper: taskkill-based kill for Windows (kills PID + child tree)
    const taskkillPid = (pid) => new Promise((resolve) => {
      if (!pid) return resolve(false);
      if (!isWin) return resolve(false);
      log(`Running taskkill on PID ${pid} ...`);
      const tk = spawn("taskkill", ["/PID", String(pid), "/F", "/T"]);
      let out = "", err = "";
      tk.stdout?.on("data", (b) => out += b.toString());
      tk.stderr?.on("data", (b) => err += b.toString());
      tk.on("close", (code) => {
        log(`[taskkill] code=${code} stdout=${out.trim()} stderr=${err.trim()}`);
        resolve(code === 0);
      });
      tk.on("error", (e) => {
        log(`[taskkill] failed: ${e?.message || e}`);
        resolve(false);
      });
    });

    // Helper: kill pid (cross-platform best-effort)
    const killPid = async (pid) => {
      if (!pid) return false;
      try {
        // first try Node API (SIGTERM)
        try {
          process.kill(pid, "SIGTERM");
          log(`Sent SIGTERM to PID ${pid}`);
        } catch (e) {
          log(`process.kill failed for PID ${pid}: ${e?.message || e}`);
        }

        // short wait
        await new Promise(r => setTimeout(r, 400));

        // check if still alive
        try {
          // still alive
          if (isWin) {
            // Force via taskkill /T
            const ok = await taskkillPid(pid);
            return ok;
          } else {
            // Force via kill -9
            const k = spawn("kill", ["-9", String(pid)]);
            await new Promise((res) => k.on("close", res));
            log(`Sent kill -9 to PID ${pid}`);
            return true;
          }
        } catch (e) {
          // throws if process not present -> success
          log(`PID ${pid} is no longer running.`);
          return true;
        }
      } catch (e) {
        log(`Failed to kill PID ${pid}: ${e?.message || e}`);
        return false;
      }
    };

    // 1) Try to kill the process objects we control first
    let anyKilled = false;

    if (pluginCp && pluginCp.pid && (!cp || pluginCp.pid !== cp.pid)) {
      log(`Attempting to kill plugin-tracked Copilot (pid=${pluginCp.pid})...`);
      const ok = await killPid(pluginCp.pid);
      anyKilled = anyKilled || ok;
    }
    if (cp && cp.pid) {
      log(`Attempting to kill spawned Copilot (pid=${cp.pid})...`);
      const ok = await killPid(cp.pid);
      anyKilled = anyKilled || ok;
    }

    // 2) If nothing killed and port is still bound, find the pid listening on the port and kill it
    if (!anyKilled && port) {
      try {
        log(`Checking for process listening on port ${port}...`);
        if (isWin) {
          // netstat -ano | findstr :<port>
          const net = spawn("cmd.exe", ["/d", "/s", "/c", `netstat -ano | findstr :${port}`], { shell: false });
          let out = "";
          net.stdout?.on("data", (b) => out += b.toString());
          await new Promise((res) => net.on("close", res));
          if (out && out.trim()) {
            const lines = out.trim().split(/\r?\n/).map(s => s.trim()).filter(Boolean);
            for (const l of lines) {
              const parts = l.split(/\s+/);
              const pid = parts[parts.length - 1];
              if (pid && /^\d+$/.test(pid)) {
                log(`Found listener PID ${pid} for port ${port}; attempting taskkill...`);
                const ok = await taskkillPid(Number(pid));
                anyKilled = anyKilled || ok;
              }
            }
          } else {
            log(`No listening process found on port ${port}.`);
          }
        } else {
          // Unix: lsof -i :port -t
          const lsof = spawn("sh", ["-c", `lsof -i :${port} -t || true`]);
          let out = "";
          lsof.stdout?.on("data", (b) => out += b.toString());
          await new Promise((res) => lsof.on("close", res));
          out = out.trim();
          if (out) {
            const pids = out.split(/\r?\n/).map(s => s.trim()).filter(Boolean);
            for (const pid of pids) {
              log(`Found listener PID ${pid} for port ${port}; sending kill -9...`);
              const k = spawn("kill", ["-9", pid]);
              await new Promise((res) => k.on("close", res));
              anyKilled = true;
            }
          } else {
            log(`No listening process found on port ${port}.`);
          }
        }
      } catch (e) {
        log(`Port-check/kill failed: ${e?.message || e}`);
      }
    }

    // 3) Fallback: kill by image name (Windows)
    if (!anyKilled && isWin) {
      log("Attempting fallback: taskkill /IM copilot.exe /F");
      const tk2 = spawn("taskkill", ["/IM", "copilot.exe", "/F"]);
      let out = "", err = "";
      tk2.stdout?.on("data", (b) => out += b.toString());
      tk2.stderr?.on("data", (b) => err += b.toString());
      await new Promise((res) => tk2.on("close", res));
      log(`[taskkill fallback] stdout=${out.trim()} stderr=${err.trim()}`);
      anyKilled = err.trim() === "";
    }

    // 4) Final cleanup
    this.copilotProc = null;
    this.plugin._copilotProc = null;

    if (anyKilled) {
      this.appendLog("✅ Copilot process killed (or port freed).", "system");
      this.updateStatus("Force stopped");
    } else {
      this.appendLog("⚠️ Unable to definitively kill Copilot. Check Task Manager or run `taskkill /F /PID <pid> /T` manually.", "system");
      this.updateStatus("Stop attempted");
    }
  }

  stopAll() {
    try { this.rpc?.cancel(); } catch { }
    try { this.rpc?.disconnect(); } catch { }
    this.rpc = null;

    if (this.copilotProc && !this.copilotProc.killed) {
      this.plugin._copilotProc = null;
      try { this.copilotProc.kill("SIGTERM"); } catch { }
    }
    this.copilotProc = null;
    this.updateStatus("Stopped");
  }
}

class CopilotAcpAgentPlugin extends Plugin {
  async onload() {
    this._copilotProc = null;
    await this.loadSettings();

    // Ensure Copilot ACP process is terminated when Obsidian window closes.
    this.registerDomEvent(window, "beforeunload", () => {
      this.killCopilotProc();
    });

    this.registerView(VIEW_TYPE, (leaf) => new CopilotAcpAgentView(leaf, this));

    // Ribbon icon
    this.addRibbonIcon("bot", "Copilot Agent (ACP)", async () => {
      await this.activateViewInNewTab();
    });

    // Command palette entry
    this.addCommand({
      id: "open-copilot-acp-agent",
      name: "Open Copilot Agent (ACP panel)",
      callback: async () => await this.activateView()
    });

    // Settings tab
    this.addSettingTab(new CopilotAcpSettingsTab(this.app, this));

    // Auto open panel on load (optional)
    if (this.settings.openOnStartup) {
      this.app.workspace.onLayoutReady(() => this.activateView());
    }
  }


  killCopilotProc() {
    const p = this._copilotProc;
    if (p && !p.killed) {
      try { p.kill("SIGTERM"); } catch { }
    }
    this._copilotProc = null;
  }

  onunload() {
    this.killCopilotProc();
    this.app.workspace.detachLeavesOfType(VIEW_TYPE);
  }

  async activateView() {
    let leaf = this.app.workspace.getLeavesOfType(VIEW_TYPE)?.[0];
    if (!leaf) {
      leaf = this.app.workspace.getRightLeaf(false);
      await leaf.setViewState({ type: VIEW_TYPE, active: true });
    }
    this.app.workspace.revealLeaf(leaf);
  }

  getPromptPresets() {
    const raw = (this.settings.promptPresetsText || "").trim();
    if (!raw) return [];
    const lines = raw.split(/\\n|\r?\n/).map(l => l.trim()).filter(Boolean);
    const out = [];
    for (const line of lines) {
      const parts = line.split("::");
      if (parts.length >= 2) {
        const label = parts[0].trim();
        const prompt = parts.slice(1).join("::").trim();
        if (label && prompt) out.push({ label, prompt });
      } else {
        // If no label provided, use first 32 chars as label
        const prompt = line;
        out.push({ label: prompt.slice(0, 32) + (prompt.length > 32 ? "…" : ""), prompt });
      }
    }
    return out;
  }

  async activateViewInNewTab() {
    const leaf = this.app.workspace.getLeaf("tab");
    await leaf.setViewState({ type: VIEW_TYPE, active: true });
    this.app.workspace.revealLeaf(leaf);
  }

  async loadSettings() {
    this.settings = Object.assign({}, CopilotAcpAgentPlugin.DEFAULT_SETTINGS, await this.loadData());
  }

  async saveSettings() {
    await this.saveData(this.settings);
  }
}

CopilotAcpAgentPlugin.DEFAULT_SETTINGS = {
  copilotPath: "copilot",
  host: "127.0.0.1",
  port: 9000,
  // Use the user's vault path you provided earlier:
  vaultPath: "C:\\GitViews\\ai_notes",
  openOnStartup: false,
  model: "claude-sonnet-4.6",
  showSystemLogs: false,
  extraCliArgs: "",
  promptPrefixText: "",
  promptPresetsText: "Summarize my last note :: Summarize the currently open note and propose 5 follow-ups.\nDraft note :: Draft a new Obsidian note with sources and frontmatter.\nRefactor outline :: Turn the above into a structured outline with headings."
};

class CopilotAcpSettingsTab extends require("obsidian").PluginSettingTab {
  constructor(app, plugin) {
    super(app, plugin);
    this.plugin = plugin;
  }


  display() {
    const { containerEl } = this;
    containerEl.empty();

    containerEl.createEl("h2", { text: "Copilot ACP Agent" });

    new Setting(containerEl)
      .setName("Copilot CLI path")
      .setDesc("Optional. If empty, the plugin will try to use `copilot` from PATH.")
      .addText((t) =>
        t.setPlaceholder("copilot")
          .setValue(this.plugin.settings.copilotPath || "")
          .onChange(async (v) => {
            this.plugin.settings.copilotPath = v.trim();
            await this.plugin.saveSettings();
          })
      );

    new Setting(containerEl)
      .setName("ACP port")
      .setDesc("TCP port used by copilot --acp --port. If the port is in use, change it.")
      .addText((t) =>
        t.setPlaceholder("9000")
          .setValue(String(this.plugin.settings.port ?? 9000))
          .onChange(async (v) => {
            const n = Number(v);
            if (!Number.isFinite(n)) return;
            this.plugin.settings.port = n;
            await this.plugin.saveSettings();
          })
      );

    new Setting(containerEl)
      .setName("Model")
      .setDesc("Passed to copilot as --model <value>. Leave blank to use Copilot default.")
      .addText((t) =>
        t.setPlaceholder("gpt-4o")
          .setValue(this.plugin.settings.model || "")
          .onChange(async (v) => {
            this.plugin.settings.model = v.trim();
            await this.plugin.saveSettings();
          })
      );

    new Setting(containerEl)
      .setName("Additional CLI arguments")
      .setDesc("Optional. Extra arguments appended to the Copilot CLI spawn command (e.g. --log-level debug). Quoted strings are supported.")
      .addText((t) =>
        t.setPlaceholder("--foo bar --baz \"quoted value\"")
          .setValue(this.plugin.settings.extraCliArgs || "")
          .onChange(async (v) => {
            this.plugin.settings.extraCliArgs = v;
            await this.plugin.saveSettings();
          })
      );

    new Setting(containerEl)
      .setName("Vault location (cwd)")
      .setDesc("Copilot process will start with this folder as working directory. Leave empty to use the current vault root.")
      .addText((t) =>
        t.setPlaceholder("C:\\GitViews\\ai_notes")
          .setValue(this.plugin.settings.vaultPath || "")
          .onChange(async (v) => {
            this.plugin.settings.vaultPath = v.trim();
            await this.plugin.saveSettings();
          })
      );

    new Setting(containerEl)
      .setName("Open on startup")
      .setDesc("Automatically open the ACP panel when Obsidian starts.")
      .addToggle((tg) =>
        tg.setValue(!!this.plugin.settings.openOnStartup)
          .onChange(async (v) => {
            this.plugin.settings.openOnStartup = v;
            await this.plugin.saveSettings();
          })
      );

    new Setting(containerEl)
      .setName("Prompt prefix (prepended)")
      .setDesc("This text will be prepended before the selected predefined prompt to form the final prompt sent to Copilot.")
      .addTextArea((t) =>
        t.setPlaceholder("e.g., Follow the Vault Constitution. Output in Markdown with citations.\n---")
          .setValue(this.plugin.settings.promptPrefixText || "")
          .onChange(async (v) => {
            this.plugin.settings.promptPrefixText = v;
            await this.plugin.saveSettings();
          })
      );

    new Setting(containerEl)
      .setName("Predefined prompts (dropdown)")
      .setDesc("One per line. Format: Label :: prompt. Example: Daily research :: Research topic X and draft a note.")
      .addTextArea((t) =>
        t.setValue(this.plugin.settings.promptPresetsText || "")
          .onChange(async (v) => {
            this.plugin.settings.promptPresetsText = v;
            await this.plugin.saveSettings();
          })
      );

    new Setting(containerEl)
      .setName("Show system/debug logs")
      .setDesc("If enabled, shows ACP connection logs and Copilot server stderr/stdout. Keep off to show only Copilot chat output.")
      .addToggle((tg) =>
        tg.setValue(!!this.plugin.settings.showSystemLogs)
          .onChange(async (v) => {
            this.plugin.settings.showSystemLogs = v;
            await this.plugin.saveSettings();
          })
      );
  }
}

module.exports = CopilotAcpAgentPlugin;

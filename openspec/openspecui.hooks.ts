// @reqstool-openspec-hooks: 0.1.1
import { spawn, ChildProcess } from "child_process";
import type { OnReadDocumentHookV1 } from "openspecui/hooks";

// Minimal MCP client over stdio (JSON-RPC 2.0, newline-delimited).
// Uses only Node.js built-ins — no npm packages required.
class McpStdioClient {
  private proc: ChildProcess;
  private buf = "";
  private pending = new Map<
    number,
    { resolve: (v: unknown) => void; reject: (e: Error) => void }
  >();
  private id = 1;
  readonly ready: Promise<void>;

  constructor(cwd: string) {
    this.proc = spawn("reqstool", ["mcp"], {
      cwd,
      stdio: ["pipe", "pipe", "pipe"],
    });
    this.proc.stdout!.on("data", (chunk: Buffer) => {
      this.buf += chunk.toString();
      let nl: number;
      while ((nl = this.buf.indexOf("\n")) !== -1) {
        const line = this.buf.slice(0, nl).trim();
        this.buf = this.buf.slice(nl + 1);
        if (line) this.handle(line);
      }
    });
    this.ready = this.init();
  }

  private handle(line: string) {
    try {
      const msg = JSON.parse(line) as { id?: number; result?: unknown; error?: { message: string } };
      if (msg.id !== undefined) {
        const p = this.pending.get(msg.id);
        if (p) {
          this.pending.delete(msg.id);
          msg.error ? p.reject(new Error(msg.error.message)) : p.resolve(msg.result);
        }
      }
    } catch (e) {
      console.warn("[reqstool-openspec] Skipping non-JSON line from reqstool mcp:", e instanceof Error ? e.message : e);
    }
  }

  private send(method: string, params: unknown, expectReply = true): Promise<unknown> {
    if (!expectReply) {
      this.proc.stdin!.write(JSON.stringify({ jsonrpc: "2.0", method, params }) + "\n");
      return Promise.resolve();
    }
    const id = this.id++;
    return new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject });
      this.proc.stdin!.write(JSON.stringify({ jsonrpc: "2.0", id, method, params }) + "\n");
    });
  }

  private async init(): Promise<void> {
    await this.send("initialize", {
      protocolVersion: "2024-11-05",
      capabilities: { tools: {} },
      clientInfo: { name: "openspecui", version: "1.0" },
    });
    this.send("notifications/initialized", {}, false);
  }

  async enrich(content: string, preset: string): Promise<string> {
    await this.ready;
    const result = (await this.send("tools/call", {
      name: "enrich_document",
      arguments: { content, preset },
    })) as { content: { text: string }[] };
    return result.content[0].text;
  }

  close() {
    this.proc.stdin?.end();
    this.proc.kill();
  }
}

let client: McpStdioClient | null = null;

export const onReadDocument: OnReadDocumentHookV1 = async (ctx, read) => {
  if (!client) {
    client = new McpStdioClient(ctx.projectDir);
    ctx.lifecycle.onDispose(() => {
      client?.close();
      client = null;
    });
  }

  const result = await read();
  const preset = `openspec:${ctx.document.kind}`;

  try {
    const enriched = await client.enrich(result.markdown, preset);
    return { ...result, markdown: enriched, sourceLabel: `reqstool ${preset}` };
  } catch (e) {
    return {
      ...result,
      diagnostics: [{ level: "warning", message: `reqstool enrich failed: ${e}` }],
    };
  }
};

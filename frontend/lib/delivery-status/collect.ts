import { execFile } from "node:child_process";
import { existsSync } from "node:fs";
import { promises as fs } from "node:fs";
import net from "node:net";
import path from "node:path";
import { promisify } from "node:util";
import {
  isLocalDeliveryStatusEnabled,
  DELIVERY_STATUS_UNAVAILABLE_REASON,
} from "./guard";
import { serializeDeliveryStatus, unavailableStatus } from "./serialize";
import type { DeliveryCommit, DeliveryRecentFile, DeliveryStatus } from "./types";

const execFileAsync = promisify(execFile);

const RECENT_SCAN_ROOTS = ["frontend", "backend", "docs", "scripts"] as const;

/** Documented local Next.js preview for this workspace. */
export const DEFAULT_DELIVERY_PREVIEW_URL = "http://127.0.0.1:3001/";

/**
 * Narrow override for the local preview health probe.
 * Example: DELIVERY_STATUS_PREVIEW_URL=http://127.0.0.1:3000/
 */
export const DELIVERY_STATUS_PREVIEW_URL_ENV = "DELIVERY_STATUS_PREVIEW_URL";

export function resolveDeliveryPreviewUrl(
  env: NodeJS.ProcessEnv = process.env,
): string {
  const override = env[DELIVERY_STATUS_PREVIEW_URL_ENV]?.trim();
  if (override) {
    return override.endsWith("/") ? override : `${override}/`;
  }
  return DEFAULT_DELIVERY_PREVIEW_URL;
}

/**
 * True only for Cursor Agent Node CLI / worker processes.
 * PowerShell/cmd launcher wrappers that merely mention cursor-agent are excluded.
 */
export function isCursorAgentNodeProcess(
  processName: string | null | undefined,
  commandLine: string | null | undefined,
): boolean {
  if (!commandLine || !/cursor-agent/i.test(commandLine)) return false;
  if (/grep\b/i.test(commandLine)) return false;

  const name = (processName || "").toLowerCase();
  if (name === "node.exe" || name === "node") return true;
  if (name && name !== "node.exe" && name !== "node") return false;

  // Unix `ps` often has no separate Name column — require a node binary in args.
  return /(?:^|[\s"/\\])node(?:\.exe)?(?:\s|"|$)/i.test(commandLine);
}

export function countCursorAgentNodeProcesses(
  processes: Array<{ name?: string | null; commandLine?: string | null }>,
): number {
  return processes.filter((proc) =>
    isCursorAgentNodeProcess(proc.name, proc.commandLine),
  ).length;
}

function toRepoRelative(repoRoot: string, absolutePath: string): string {
  return path.relative(repoRoot, absolutePath).split(path.sep).join("/");
}

async function findRepoRoot(startDir: string = process.cwd()): Promise<string> {
  let dir = path.resolve(startDir);
  for (;;) {
    if (existsSync(path.join(dir, ".git"))) return dir;
    const parent = path.dirname(dir);
    if (parent === dir) return path.resolve(startDir);
    dir = parent;
  }
}

async function runGit(repoRoot: string, args: string[]): Promise<string> {
  const { stdout } = await execFileAsync("git", args, {
    cwd: repoRoot,
    windowsHide: true,
    maxBuffer: 1024 * 1024,
  });
  // Preserve leading spaces in porcelain status (XY codes); only strip trailing newlines.
  return stdout.toString().replace(/[\r\n]+$/, "");
}

async function collectBranch(repoRoot: string): Promise<string> {
  try {
    return (await runGit(repoRoot, ["branch", "--show-current"])).trim();
  } catch {
    return "(unknown)";
  }
}

async function collectCommits(repoRoot: string, limit = 5): Promise<DeliveryCommit[]> {
  try {
    const raw = await runGit(repoRoot, [
      "log",
      `-${limit}`,
      "--pretty=format:%h%x09%s%x09%cr",
    ]);
    if (!raw) return [];
    return raw.split("\n").flatMap((line) => {
      const [hash, subject, when] = line.split("\t");
      if (!hash || !subject) return [];
      return [{ hash, subject, when: when || "" }];
    });
  } catch {
    return [];
  }
}

async function collectDirtyFiles(repoRoot: string): Promise<string[]> {
  try {
    const raw = await runGit(repoRoot, ["status", "--porcelain", "-u"]);
    if (!raw) return [];
    return raw
      .split(/\r?\n/)
      .map((line) => {
        if (line.length < 4) return "";
        // porcelain: two status chars, a space, then path (or "old -> new")
        const entry = line.slice(3).trim().replace(/^"|"$/g, "");
        const arrow = " -> ";
        if (entry.includes(arrow)) {
          return entry.slice(entry.lastIndexOf(arrow) + arrow.length).trim();
        }
        return entry;
      })
      .filter(Boolean)
      .map((entry) => entry.split(path.sep).join("/"));
  } catch {
    return [];
  }
}

async function walkRecentFiles(
  repoRoot: string,
  relativeRoot: string,
  acc: { absolute: string; mtimeMs: number }[],
): Promise<void> {
  const absoluteRoot = path.join(repoRoot, relativeRoot);
  let entries;
  try {
    entries = await fs.readdir(absoluteRoot, { withFileTypes: true });
  } catch {
    return;
  }

  for (const entry of entries) {
    if (entry.name === "node_modules" || entry.name === ".next" || entry.name === ".git") {
      continue;
    }
    if (entry.name === ".venv" || entry.name === "dist" || entry.name === "coverage") {
      continue;
    }
    const absolute = path.join(absoluteRoot, entry.name);
    if (entry.isDirectory()) {
      await walkRecentFiles(repoRoot, path.join(relativeRoot, entry.name), acc);
      continue;
    }
    if (!entry.isFile()) continue;
    try {
      const stat = await fs.stat(absolute);
      acc.push({ absolute, mtimeMs: stat.mtimeMs });
    } catch {
      // skip unreadable files
    }
  }
}

async function collectRecentFiles(
  repoRoot: string,
  limit = 8,
): Promise<DeliveryRecentFile[]> {
  const acc: { absolute: string; mtimeMs: number }[] = [];
  for (const root of RECENT_SCAN_ROOTS) {
    await walkRecentFiles(repoRoot, root, acc);
  }
  return acc
    .sort((a, b) => b.mtimeMs - a.mtimeMs)
    .slice(0, limit)
    .map((item) => ({
      path: toRepoRelative(repoRoot, item.absolute),
      modifiedAt: new Date(item.mtimeMs).toISOString(),
    }));
}

async function countCursorCliProcesses(): Promise<number> {
  if (process.platform === "win32") {
    try {
      // Emit Name<TAB>CommandLine so wrappers can be filtered in JS.
      const script =
        "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'cursor-agent' } | ForEach-Object { $_.Name + [char]9 + $_.CommandLine }";
      const { stdout } = await execFileAsync(
        "powershell",
        ["-NoProfile", "-NonInteractive", "-Command", script],
        { windowsHide: true, maxBuffer: 1024 * 1024 },
      );
      const processes = stdout
        .toString()
        .split(/\r?\n/)
        .map((line) => line.trim())
        .filter(Boolean)
        .map((line) => {
          const sep = line.indexOf("\t");
          if (sep <= 0) return { name: null, commandLine: line };
          return {
            name: line.slice(0, sep),
            commandLine: line.slice(sep + 1),
          };
        });
      return countCursorAgentNodeProcesses(processes);
    } catch {
      return 0;
    }
  }

  try {
    const { stdout } = await execFileAsync("ps", ["-A", "-o", "comm=,args="], {
      maxBuffer: 2 * 1024 * 1024,
    });
    const processes = stdout
      .toString()
      .split("\n")
      .map((line) => line.trim())
      .filter(Boolean)
      .map((line) => {
        const parts = line.split(/\s+/);
        const name = parts[0] || null;
        const commandLine = parts.slice(1).join(" ") || line;
        return { name, commandLine };
      });
    return countCursorAgentNodeProcesses(processes);
  } catch {
    return 0;
  }
}

function previewPort(url: string): { host: string; port: number } {
  try {
    const parsed = new URL(url);
    return {
      host: parsed.hostname || "127.0.0.1",
      port: Number(parsed.port || (parsed.protocol === "https:" ? 443 : 80)),
    };
  } catch {
    return { host: "127.0.0.1", port: 3001 };
  }
}

function canTcpConnect(host: string, port: number, timeoutMs = 1000): Promise<boolean> {
  return new Promise((resolve) => {
    const socket = net.connect({ host, port }, () => {
      socket.end();
      resolve(true);
    });
    socket.on("error", () => resolve(false));
    socket.setTimeout(timeoutMs, () => {
      socket.destroy();
      resolve(false);
    });
  });
}

async function probePreview(url: string = resolveDeliveryPreviewUrl()): Promise<{
  url: string;
  healthy: boolean;
  statusCode: number | null;
}> {
  // Avoid HTTP self-fetch deadlocks against the same Next.js process; TCP proves listen health.
  const { host, port } = previewPort(url);
  const listening = await canTcpConnect(host, port);
  return {
    url,
    healthy: listening,
    statusCode: listening ? 200 : null,
  };
}

/** Collect local workspace delivery telemetry. Safe no-op outside development. */
export async function collectDeliveryStatus(
  options: { nodeEnv?: string } = {},
): Promise<DeliveryStatus> {
  const checkedAt = new Date().toISOString();
  if (!isLocalDeliveryStatusEnabled(options.nodeEnv)) {
    return unavailableStatus(checkedAt, DELIVERY_STATUS_UNAVAILABLE_REASON);
  }

  const repoRoot = await findRepoRoot();
  const [branch, commits, dirtyFiles, recentFiles, cursorProcessCount, preview] =
    await Promise.all([
      collectBranch(repoRoot),
      collectCommits(repoRoot),
      collectDirtyFiles(repoRoot),
      collectRecentFiles(repoRoot),
      countCursorCliProcesses(),
      probePreview(),
    ]);

  return serializeDeliveryStatus({
    checkedAt,
    branch,
    commits,
    dirtyFiles,
    recentFiles,
    cursorProcessCount,
    preview,
  });
}

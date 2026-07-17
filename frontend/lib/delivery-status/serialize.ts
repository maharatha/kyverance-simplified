import type {
  DeliveryCommit,
  DeliveryPreviewProbe,
  DeliveryRecentFile,
  DeliveryStatus,
  DeliveryStatusAvailable,
  DeliveryStatusUnavailable,
} from "./types";
import { DELIVERY_STATUS_UNAVAILABLE_REASON } from "./guard";

export function unavailableStatus(
  checkedAt: string = new Date().toISOString(),
  reason: string = DELIVERY_STATUS_UNAVAILABLE_REASON,
): DeliveryStatusUnavailable {
  return {
    available: false,
    checkedAt,
    reason,
  };
}

export function serializeDeliveryStatus(input: {
  checkedAt: string;
  branch: string;
  commits: DeliveryCommit[];
  dirtyFiles: string[];
  recentFiles: DeliveryRecentFile[];
  cursorProcessCount: number;
  preview: DeliveryPreviewProbe;
}): DeliveryStatusAvailable {
  return {
    available: true,
    checkedAt: input.checkedAt,
    branch: input.branch || "(unknown)",
    commits: input.commits.map((commit) => ({
      hash: commit.hash,
      subject: commit.subject,
      when: commit.when,
    })),
    dirtyFiles: [...input.dirtyFiles],
    recentFiles: input.recentFiles.map((file) => ({
      path: file.path,
      modifiedAt: file.modifiedAt,
    })),
    cursorCli: {
      active: input.cursorProcessCount > 0,
      processCount: Math.max(0, input.cursorProcessCount),
    },
    preview: {
      url: input.preview.url,
      healthy: input.preview.healthy,
      statusCode: input.preview.statusCode,
    },
  };
}

export function formatDirtySummary(dirtyFiles: string[]): string {
  if (dirtyFiles.length === 0) return "Working tree clean";
  if (dirtyFiles.length === 1) return "1 dirty file";
  return `${dirtyFiles.length} dirty files`;
}

export function formatCursorSummary(status: DeliveryStatus): string {
  if (!status.available) return "Unavailable";
  if (!status.cursorCli.active) return "No active Cursor CLI process";
  const count = status.cursorCli.processCount;
  return count === 1
    ? "1 active Cursor CLI process"
    : `${count} active Cursor CLI processes`;
}

export function formatPreviewSummary(status: DeliveryStatus): string {
  if (!status.available) return "Unavailable";
  if (status.preview.healthy) {
    return `Healthy (HTTP ${status.preview.statusCode ?? "ok"})`;
  }
  return "Unavailable";
}

export function assertNoAbsolutePaths(status: DeliveryStatus): string[] {
  if (!status.available) return [];
  const offenders: string[] = [];
  const check = (value: string, label: string) => {
    if (/^[A-Za-z]:[\\/]/.test(value) || value.startsWith("/") || value.includes("\\")) {
      offenders.push(label);
    }
  };
  for (const file of status.dirtyFiles) check(file, `dirty:${file}`);
  for (const file of status.recentFiles) check(file.path, `recent:${file.path}`);
  return offenders;
}

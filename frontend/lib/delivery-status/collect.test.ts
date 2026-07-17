import { afterEach, describe, expect, it } from "vitest";
import {
  collectDeliveryStatus,
  countCursorAgentNodeProcesses,
  DEFAULT_DELIVERY_PREVIEW_URL,
  DELIVERY_STATUS_PREVIEW_URL_ENV,
  isCursorAgentNodeProcess,
  resolveDeliveryPreviewUrl,
} from "./collect";

describe("collectDeliveryStatus", () => {
  it("does not collect workspace telemetry outside development", async () => {
    const status = await collectDeliveryStatus({ nodeEnv: "production" });
    expect(status.available).toBe(false);
    if (!status.available) {
      expect(status.reason).toMatch(/local Next\.js development/i);
    }
  });
});

describe("resolveDeliveryPreviewUrl", () => {
  const previous = process.env[DELIVERY_STATUS_PREVIEW_URL_ENV];

  afterEach(() => {
    if (previous === undefined) {
      delete process.env[DELIVERY_STATUS_PREVIEW_URL_ENV];
    } else {
      process.env[DELIVERY_STATUS_PREVIEW_URL_ENV] = previous;
    }
  });

  it("defaults to the documented local preview on port 3001", () => {
    delete process.env[DELIVERY_STATUS_PREVIEW_URL_ENV];
    expect(resolveDeliveryPreviewUrl({})).toBe(DEFAULT_DELIVERY_PREVIEW_URL);
    expect(DEFAULT_DELIVERY_PREVIEW_URL).toBe("http://127.0.0.1:3001/");
  });

  it("honors a narrowly scoped environment override", () => {
    expect(
      resolveDeliveryPreviewUrl({
        [DELIVERY_STATUS_PREVIEW_URL_ENV]: "http://127.0.0.1:3000",
      }),
    ).toBe("http://127.0.0.1:3000/");
  });
});

describe("Cursor Agent Node process counting", () => {
  it("counts Node CLI and worker processes, not PowerShell/cmd wrappers", () => {
    const processes = [
      {
        name: "powershell.exe",
        commandLine:
          "powershell.exe -NoProfile -Command & 'C:\\Users\\me\\AppData\\Local\\cursor-agent\\cursor-agent.cmd' -p",
      },
      {
        name: "cmd.exe",
        commandLine:
          'cmd.exe /c ""C:\\Users\\me\\AppData\\Local\\cursor-agent\\cursor-agent.cmd" -p --trust"',
      },
      {
        name: "node.exe",
        commandLine:
          '"C:\\Users\\me\\AppData\\Local\\cursor-agent\\versions\\2026.07.16\\node.exe" C:\\Users\\me\\AppData\\Local\\cursor-agent\\versions\\2026.07.16\\index.js -p --trust',
      },
      {
        name: "node.exe",
        commandLine:
          "C:\\Users\\me\\AppData\\Local\\cursor-agent\\versions\\2026.07.16\\node.exe C:\\Users\\me\\AppData\\Local\\cursor-agent\\versions\\2026.07.16\\index.js worker-server",
      },
    ];

    expect(countCursorAgentNodeProcesses(processes)).toBe(2);
    expect(isCursorAgentNodeProcess(processes[0].name, processes[0].commandLine)).toBe(
      false,
    );
    expect(isCursorAgentNodeProcess(processes[2].name, processes[2].commandLine)).toBe(
      true,
    );
  });

  it("recognizes unix node args that include cursor-agent", () => {
    expect(
      isCursorAgentNodeProcess(
        "node",
        "/home/me/.local/cursor-agent/versions/x/node /home/me/.local/cursor-agent/versions/x/index.js -p",
      ),
    ).toBe(true);
    expect(
      isCursorAgentNodeProcess(
        "bash",
        "bash /home/me/.local/bin/cursor-agent -p",
      ),
    ).toBe(false);
  });
});

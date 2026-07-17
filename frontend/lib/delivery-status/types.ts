/** Local delivery board payload — only populated in development. */

export type DeliveryCommit = {
  hash: string;
  subject: string;
  when: string;
};

export type DeliveryRecentFile = {
  /** Repo-relative path using forward slashes. */
  path: string;
  modifiedAt: string;
};

export type DeliveryPreviewProbe = {
  url: string;
  healthy: boolean;
  statusCode: number | null;
};

export type DeliveryStatusAvailable = {
  available: true;
  checkedAt: string;
  branch: string;
  commits: DeliveryCommit[];
  dirtyFiles: string[];
  recentFiles: DeliveryRecentFile[];
  cursorCli: {
    active: boolean;
    processCount: number;
  };
  preview: DeliveryPreviewProbe;
};

export type DeliveryStatusUnavailable = {
  available: false;
  checkedAt: string;
  reason: string;
};

export type DeliveryStatus = DeliveryStatusAvailable | DeliveryStatusUnavailable;

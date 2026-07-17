"use client";

import { FormEvent, useState } from "react";
import { formatMoney, formatTimestamp } from "@/lib/home/format";
import {
  confirmOrder,
  previewOrder,
  type ActivityItem,
  type OrderPreview,
  type OrderReceipt,
  type Position,
} from "@/lib/orders-api";

type OrderLoopPanelProps = {
  portfolioId: string;
  currencyCode: string;
  accessToken: string | null;
  positions: Position[];
  activity: ActivityItem[];
  onMutated: () => Promise<void>;
};

function newIdempotencyKey(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return `confirm-${crypto.randomUUID()}`;
  }
  return `confirm-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export function OrderLoopPanel({
  portfolioId,
  currencyCode,
  accessToken,
  positions,
  activity,
  onMutated,
}: OrderLoopPanelProps) {
  const [symbol, setSymbol] = useState("AAPL");
  const [side, setSide] = useState<"buy" | "sell">("buy");
  const [sizeMode, setSizeMode] = useState<"quantity" | "notional">("quantity");
  const [sizeValue, setSizeValue] = useState("1");
  const [preview, setPreview] = useState<OrderPreview | null>(null);
  const [receipt, setReceipt] = useState<OrderReceipt | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onPreview(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setReceipt(null);
    try {
      const next = await previewOrder(
        portfolioId,
        {
          symbol,
          side,
          quantity: sizeMode === "quantity" ? sizeValue : null,
          notional: sizeMode === "notional" ? sizeValue : null,
        },
        { accessToken },
      );
      setPreview(next);
    } catch (err) {
      setPreview(null);
      setError(err instanceof Error ? err.message : "Preview failed");
    } finally {
      setBusy(false);
    }
  }

  async function onConfirm() {
    if (!preview) return;
    setBusy(true);
    setError(null);
    try {
      const next = await confirmOrder(portfolioId, preview.preview_id, {
        accessToken,
        idempotencyKey: newIdempotencyKey(),
      });
      setReceipt(next);
      setPreview(null);
      await onMutated();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Confirmation failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <section className="portfolio-panel" aria-label="Simulated order">
        <h2 className="portfolio-title" style={{ fontSize: "1.25rem" }}>
          Simulated market order
        </h2>
        <p className="portfolio-meta">
          Preview is server-calculated. Confirmation is a separate explicit step. No broker
          routing.
        </p>
        <form className="order-form" onSubmit={onPreview}>
          <label className="order-field">
            Symbol
            <input
              value={symbol}
              onChange={(e) => setSymbol(e.target.value.toUpperCase())}
              required
              maxLength={32}
              aria-label="Symbol"
            />
          </label>
          <label className="order-field">
            Side
            <select
              value={side}
              onChange={(e) => setSide(e.target.value as "buy" | "sell")}
              aria-label="Side"
            >
              <option value="buy">Buy</option>
              <option value="sell">Sell</option>
            </select>
          </label>
          <label className="order-field">
            Size mode
            <select
              value={sizeMode}
              onChange={(e) => setSizeMode(e.target.value as "quantity" | "notional")}
              aria-label="Size mode"
            >
              <option value="quantity">Quantity</option>
              <option value="notional">Notional</option>
            </select>
          </label>
          <label className="order-field">
            {sizeMode === "quantity" ? "Quantity" : "Notional"}
            <input
              value={sizeValue}
              onChange={(e) => setSizeValue(e.target.value)}
              required
              inputMode="decimal"
              aria-label={sizeMode === "quantity" ? "Quantity" : "Notional"}
            />
          </label>
          <button className="order-preview-btn" type="submit" disabled={busy}>
            Preview order
          </button>
        </form>

        {error ? (
          <p className="portfolio-error" role="alert">
            {error}
          </p>
        ) : null}

        {preview ? (
          <div className="order-preview" role="region" aria-label="Order preview">
            <p className="portfolio-balance">
              {preview.side.toUpperCase()} {preview.quantity} {preview.symbol} @{" "}
              {formatMoney(preview.execution_price, currencyCode)}
            </p>
            <p className="portfolio-meta">
              Notional {formatMoney(preview.notional, currencyCode)} · cash after{" "}
              {formatMoney(preview.cash_after, currencyCode)}
            </p>
            <p className="portfolio-meta">
              Data mode: {preview.quote.data_mode} · freshness: {preview.quote.freshness_label} ·
              policy: {preview.quote.execution_policy}
            </p>
            <p className="portfolio-notice">{preview.disclosure}</p>
            <button
              className="order-confirm-btn"
              type="button"
              onClick={() => void onConfirm()}
              disabled={busy}
            >
              Confirm simulated order
            </button>
          </div>
        ) : null}

        {receipt ? (
          <div className="order-receipt" role="status">
            <p className="portfolio-balance">
              Receipt {receipt.status}: {receipt.side.toUpperCase()} {receipt.quantity}{" "}
              {receipt.symbol}
            </p>
            <p className="portfolio-meta">
              Fill {formatMoney(receipt.execution_price, currencyCode)} · cash{" "}
              {formatMoney(receipt.cash_balance, currencyCode)}
            </p>
            <p className="portfolio-meta">{receipt.disclosure}</p>
          </div>
        ) : null}
      </section>

      <section className="portfolio-panel" aria-label="Positions">
        <h2 className="portfolio-title" style={{ fontSize: "1.25rem" }}>
          Positions
        </h2>
        {positions.length === 0 ? (
          <p className="portfolio-meta">No simulated holdings yet.</p>
        ) : (
          <ul className="portfolio-ledger">
            {positions.map((pos) => (
              <li key={pos.symbol} className="portfolio-ledger-row">
                <strong className="portfolio-balance">
                  {pos.symbol} · {pos.quantity}
                </strong>
                <span className="portfolio-meta">
                  Avg cost {formatMoney(pos.avg_cost, currencyCode)}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="portfolio-panel" aria-label="Activity">
        <h2 className="portfolio-title" style={{ fontSize: "1.25rem" }}>
          Activity
        </h2>
        {activity.length === 0 ? (
          <p className="portfolio-meta">No confirmed simulated orders yet.</p>
        ) : (
          <ul className="portfolio-ledger">
            {activity.map((item) => (
              <li key={item.receipt_id} className="portfolio-ledger-row">
                <strong className="portfolio-balance">
                  {item.status} {item.side.toUpperCase()} {item.quantity} {item.symbol}
                </strong>
                <span className="portfolio-meta">
                  {formatMoney(item.notional, currencyCode)} · {formatTimestamp(item.created_at)}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </>
  );
}

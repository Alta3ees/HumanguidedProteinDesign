import { useEffect } from "react";
import "./confirm-dialog.css";

export default function ConfirmDialog({
  open,
  title,
  message,
  detail,
  confirmLabel = "Delete",
  busy = false,
  error = null,
  onCancel,
  onConfirm,
}: {
  open: boolean;
  title: string;
  message: string;
  detail?: string | null;
  confirmLabel?: string;
  busy?: boolean;
  error?: string | null;
  onCancel: () => void;
  onConfirm: () => void;
}) {
  useEffect(() => {
    if (!open) return;
    const handleKey = (event: KeyboardEvent) => {
      if (event.key === "Escape" && !busy) onCancel();
    };
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [open, busy, onCancel]);

  if (!open) return null;

  return (
    <div className="modal-backdrop hgd-confirm-backdrop" role="presentation" onMouseDown={(event) => {
      if (event.target === event.currentTarget && !busy) onCancel();
    }}>
      <section className="modal-dialog hgd-confirm-dialog" role="alertdialog" aria-modal="true" aria-labelledby="hgd-confirm-title" aria-describedby="hgd-confirm-message">
        <div className="hgd-confirm-icon" aria-hidden="true">!</div>
        <div className="hgd-confirm-copy">
          <p className="eyebrow">Confirm destructive action</p>
          <h2 id="hgd-confirm-title">{title}</h2>
          <p id="hgd-confirm-message">{message}</p>
          {detail && <p className="hgd-confirm-detail">{detail}</p>}
          {error && <p className="form-error hgd-confirm-error">{error}</p>}
        </div>
        <div className="modal-actions hgd-confirm-actions">
          <button type="button" className="secondary-button" onClick={onCancel} disabled={busy}>Cancel</button>
          <button type="button" className="danger-button" onClick={onConfirm} disabled={busy}>{busy ? "Deleting…" : confirmLabel}</button>
        </div>
      </section>
    </div>
  );
}

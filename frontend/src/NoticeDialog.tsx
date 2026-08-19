import { useEffect } from "react";
import "./notice-dialog.css";

export type NoticeContent = {
  title: string;
  message: string;
  detail?: string | null;
};

export default function NoticeDialog({
  notice,
  onClose,
}: {
  notice: NoticeContent | null;
  onClose: () => void;
}) {
  useEffect(() => {
    if (!notice) return;
    const handleKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [notice, onClose]);

  if (!notice) return null;

  return (
    <div
      className="modal-backdrop hgd-notice-backdrop"
      role="presentation"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <section
        className="modal-dialog hgd-notice-dialog"
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="hgd-notice-title"
        aria-describedby="hgd-notice-message"
      >
        <div className="hgd-notice-icon" aria-hidden="true">i</div>
        <div className="hgd-notice-copy">
          <p className="eyebrow">Action needs attention</p>
          <h2 id="hgd-notice-title">{notice.title}</h2>
          <p id="hgd-notice-message">{notice.message}</p>
          {notice.detail && <p className="hgd-notice-detail">{notice.detail}</p>}
        </div>
        <div className="modal-actions hgd-notice-actions">
          <button type="button" className="primary-button" onClick={onClose}>Got it</button>
        </div>
      </section>
    </div>
  );
}

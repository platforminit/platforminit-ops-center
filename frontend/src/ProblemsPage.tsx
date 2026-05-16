import { useCallback, useEffect, useState } from "react";
import type { ProblemEntry } from "./api";
import { fetchProblems } from "./api";
import "./ProblemsPage.css";

type LoadState =
  | { kind: "loading" }
  | { kind: "error"; message: string }
  | { kind: "loaded"; problems: ProblemEntry[] };

function statusClass(status: string): string {
  switch (status) {
    case "CRITICAL":
      return "status-critical";
    case "WARNING":
      return "status-warning";
    case "UNKNOWN":
      return "status-unknown";
    default:
      return "status-ok";
  }
}

function formatTimestamp(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleString();
}

function ProblemsTable({ problems }: { problems: ProblemEntry[] }) {
  if (problems.length === 0) {
    return <p className="empty-state">No current problems.</p>;
  }

  return (
    <table className="problems-table">
      <thead>
        <tr>
          <th>Status</th>
          <th>Check</th>
          <th>Output</th>
          <th>Since</th>
          <th>Ack</th>
          <th>Downtime</th>
        </tr>
      </thead>
      <tbody>
        {problems.map((p) => (
          <tr key={`${p.check_id}-${p.created_at}`}>
            <td>
              <span className={`status-badge ${statusClass(p.status)}`}>
                {p.status}
              </span>
            </td>
            <td className="cell-check-id">{p.check_id}</td>
            <td className="cell-output">{p.output}</td>
            <td className="cell-time">{formatTimestamp(p.created_at)}</td>
            <td>
              {p.acknowledged ? (
                <span className="ack-badge ack-yes" title={p.acknowledged_reason ?? ""}>
                  Yes
                </span>
              ) : (
                <span className="ack-badge ack-no">No</span>
              )}
            </td>
            <td>
              {p.in_downtime ? (
                <span className="downtime-badge downtime-yes">Yes</span>
              ) : (
                <span className="downtime-badge downtime-no">No</span>
              )}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export default function ProblemsPage() {
  const [state, setState] = useState<LoadState>({ kind: "loading" });

  const loadProblems = useCallback(async () => {
    try {
      const data = await fetchProblems();
      setState({ kind: "loaded", problems: data.problems });
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "An unexpected error occurred";
      setState({ kind: "error", message });
    }
  }, []);

  useEffect(() => {
    let cancelled = false;

    fetchProblems()
      .then((data) => {
        if (!cancelled) {
          setState({ kind: "loaded", problems: data.problems });
        }
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          const message = err instanceof Error ? err.message : "An unexpected error occurred";
          setState({ kind: "error", message });
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const retry = () => {
    setState({ kind: "loading" });
    loadProblems();
  };

  return (
    <div className="problems-page">
      <h1>Problems</h1>

      {state.kind === "loading" && <p className="loading-state">Loading problems…</p>}
      {state.kind === "error" && (
        <div className="error-state">
          <p>Failed to load problems.</p>
          <p className="error-detail">{state.message}</p>
          <button type="button" onClick={retry}>
            Retry
          </button>
        </div>
      )}
      {state.kind === "loaded" && <ProblemsTable problems={state.problems} />}
    </div>
  );
}

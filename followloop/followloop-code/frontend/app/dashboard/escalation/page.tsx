"use client";

import { useEffect, useState } from "react";
import Nav from "@/components/Nav";

function getCookie(name: string): string | undefined {
  if (typeof document === "undefined") return undefined;
  return document.cookie
    .split("; ")
    .find((row) => row.startsWith(`${name}=`))
    ?.split("=")[1];
}

interface EscalationRow {
  id: string;
  client_name: string;
  client_company?: string;
  meeting_type: string;
  meeting_date: string;
  escalation_risk: "high" | "medium" | "low" | "healthy" | "unknown";
  risk_signals?: string[];
  sentiment_summary?: string;
}

const RISK_CONFIG = {
  high:    { dot: "🔴", label: "High",    bg: "bg-red-50",    border: "border-red-200",    text: "text-red-800"    },
  medium:  { dot: "🟡", label: "Medium",  bg: "bg-amber-50",  border: "border-amber-200",  text: "text-amber-800"  },
  low:     { dot: "🟡", label: "Low",     bg: "bg-amber-50",  border: "border-amber-200",  text: "text-amber-800"  },
  healthy: { dot: "🟢", label: "Healthy", bg: "bg-green-50",  border: "border-green-200",  text: "text-green-800"  },
  unknown: { dot: "⚪", label: "Unknown", bg: "bg-gray-50",   border: "border-gray-200",   text: "text-gray-600"   },
};

export default function EscalationPage() {
  const [rows, setRows] = useState<EscalationRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});

  useEffect(() => {
    const id = getCookie("pm_id") || "";
    if (!id) { setLoading(false); return; }
    fetch(`/api/escalation?pm_id=${id}`, { credentials: "include" })
      .then((r) => r.json())
      .then((data) => { setRows(data); setLoading(false); })
      .catch(() => setLoading(false));
  }, []);

  const high    = rows.filter((r) => r.escalation_risk === "high");
  const medium  = rows.filter((r) => r.escalation_risk === "medium");
  const low     = rows.filter((r) => r.escalation_risk === "low");
  const healthy = rows.filter((r) => r.escalation_risk === "healthy");

  function renderGroup(title: string, items: EscalationRow[]) {
    if (!items.length) return null;
    const cfg = RISK_CONFIG[items[0].escalation_risk] || RISK_CONFIG.unknown;
    return (
      <div className="mb-6">
        <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">{title}</p>
        <div className="space-y-2">
          {items.map((row) => {
            const clientKey = row.client_company || row.client_name;
            const isOpen = expanded[row.id];
            const date = new Date(row.meeting_date || "").toLocaleDateString("en-US", { month: "short", day: "numeric" });
            return (
              <div key={row.id} className={`border ${cfg.border} rounded-xl overflow-hidden`}>
                <button
                  onClick={() => setExpanded((prev) => ({ ...prev, [row.id]: !prev[row.id] }))}
                  className={`w-full flex items-center gap-3 px-4 py-3 ${cfg.bg} text-left`}
                >
                  <span className="text-base">{cfg.dot}</span>
                  <div className="flex-1 min-w-0">
                    <span className={`font-medium text-sm ${cfg.text}`}>{clientKey}</span>
                    <span className="text-xs text-gray-400 ml-2">{row.meeting_type?.replace(/_/g, " ")}</span>
                  </div>
                  <span className="text-xs text-gray-400 shrink-0">{date}</span>
                  <span className="text-xs text-gray-400">{isOpen ? "▲" : "▼"}</span>
                </button>
                {isOpen && (
                  <div className="px-4 py-3 bg-white border-t border-gray-100">
                    {row.sentiment_summary && (
                      <p className="text-sm text-gray-700 mb-3">{row.sentiment_summary}</p>
                    )}
                    {row.risk_signals && row.risk_signals.length > 0 && (
                      <div>
                        <p className="text-xs font-medium text-gray-500 mb-1">Signals detected:</p>
                        <ul className="space-y-1">
                          {row.risk_signals.map((signal, i) => (
                            <li key={i} className="text-xs text-gray-600 flex gap-2">
                              <span className="text-gray-400">•</span>
                              <span>{signal}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                    <a
                      href={`/dashboard/history`}
                      className="text-xs text-blue-600 hover:underline mt-3 block"
                    >
                      View full history →
                    </a>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    );
  }

  return (
    <>
      <Nav />
      <main className="min-h-screen bg-gray-50 px-4 pt-8 pb-16">
        <div className="max-w-2xl mx-auto">
          <div className="mb-6">
            <h1 className="text-2xl font-semibold text-gray-900">Escalation Radar</h1>
            <p className="text-gray-500 text-sm mt-1">Customer health across your accounts — updated after each meeting</p>
          </div>

          {loading && <p className="text-gray-400 text-sm text-center py-12">Loading…</p>}

          {!loading && rows.length === 0 && (
            <div className="bg-white border border-gray-200 rounded-xl p-8 text-center">
              <p className="text-gray-400 text-sm">No escalation data yet.</p>
              <p className="text-gray-300 text-xs mt-1">Scores appear automatically after meetings are processed.</p>
            </div>
          )}

          {!loading && rows.length > 0 && (
            <>
              {renderGroup("Needs immediate attention", high)}
              {renderGroup("Monitor closely", [...medium, ...low])}
              {renderGroup("Healthy", healthy)}
            </>
          )}
        </div>
      </main>
    </>
  );
}

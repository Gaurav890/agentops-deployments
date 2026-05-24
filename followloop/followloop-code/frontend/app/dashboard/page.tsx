"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Nav from "@/components/Nav";
import { getHistory, getEscalation, getTasks, DraftRecord, EscalationRow, Task } from "@/lib/api";

function getCookie(name: string): string | undefined {
  if (typeof document === "undefined") return undefined;
  return document.cookie
    .split("; ")
    .find((row) => row.startsWith(`${name}=`))
    ?.split("=")[1];
}

function greeting(): string {
  const h = new Date().getHours();
  if (h < 12) return "Good morning";
  if (h < 17) return "Good afternoon";
  return "Good evening";
}

export default function HomePage() {
  const router = useRouter();
  const [pmName, setPmName] = useState("");
  const [drafts, setDrafts] = useState<DraftRecord[]>([]);
  const [escalation, setEscalation] = useState<EscalationRow[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const pmId = getCookie("pm_id") || "";
    if (!pmId) {
      router.replace("/");
      return;
    }

    // Check onboarding + fetch PM name
    fetch(`/api/pm/${pmId}`, { credentials: "include" })
      .then((r) => r.json())
      .then((pm) => {
        if (!pm.onboarding_complete) {
          router.replace("/dashboard/onboarding");
          return;
        }
        setPmName(pm.name?.split(" ")[0] || "");
      })
      .catch(() => {});

    Promise.all([
      getHistory(pmId).catch(() => [] as DraftRecord[]),
      getEscalation(pmId).catch(() => [] as EscalationRow[]),
      getTasks(pmId).catch(() => [] as Task[]),
    ]).then(([h, e, t]) => {
      setDrafts(h);
      setEscalation(e);
      setTasks(t);
      setLoading(false);
    });
  }, []);

  const pendingDrafts = drafts.filter((d) => d.status === "pending");
  const highRisk = escalation.filter((e) => e.escalation_risk === "high");
  const mediumRisk = escalation.filter((e) => e.escalation_risk === "medium" || e.escalation_risk === "low");
  const pendingTasks = tasks.filter((t) => t.status === "pending");

  // Group pending tasks by client
  const tasksByClient = pendingTasks.reduce<Record<string, number>>((acc, t) => {
    acc[t.client_name] = (acc[t.client_name] || 0) + 1;
    return acc;
  }, {});

  return (
    <>
      <Nav />
      <main className="min-h-screen bg-gray-50 px-4 pt-8 pb-16">
        <div className="max-w-2xl mx-auto">
          {/* Header */}
          <div className="mb-8">
            <h1 className="text-2xl font-semibold text-gray-900">
              {greeting()}{pmName ? `, ${pmName}` : ""}
            </h1>
            <p className="text-gray-500 text-sm mt-1">
              {new Date().toLocaleDateString("en-US", { weekday: "long", month: "long", day: "numeric" })}
            </p>
          </div>

          {loading && <p className="text-gray-400 text-sm text-center py-12">Loading…</p>}

          {!loading && (
            <div className="space-y-4">
              {/* Pending Gmail drafts */}
              <section className="bg-white border border-gray-200 rounded-xl overflow-hidden">
                <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100">
                  <div className="flex items-center gap-2">
                    <span className="text-base">📬</span>
                    <span className="text-sm font-semibold text-gray-800">
                      Drafts waiting in Gmail
                    </span>
                    {pendingDrafts.length > 0 && (
                      <span className="text-xs bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded-full font-medium">
                        {pendingDrafts.length}
                      </span>
                    )}
                  </div>
                  <a href="/dashboard/history" className="text-xs text-blue-600 hover:underline">
                    View all →
                  </a>
                </div>

                {pendingDrafts.length === 0 ? (
                  <p className="text-sm text-gray-400 px-4 py-4">All caught up — no pending drafts.</p>
                ) : (
                  <div className="divide-y divide-gray-50">
                    {pendingDrafts.slice(0, 5).map((d) => (
                      <div key={d.id} className="flex items-center gap-3 px-4 py-3">
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium text-gray-800 truncate">
                            {d.client_company || d.client_name}
                          </p>
                          <p className="text-xs text-gray-400">
                            {d.meeting_type?.replace(/_/g, " ")} ·{" "}
                            {new Date(d.meeting_date || d.created_at).toLocaleDateString("en-US", {
                              month: "short",
                              day: "numeric",
                            })}
                          </p>
                        </div>
                        <a
                          href="/dashboard/history"
                          className="text-xs text-blue-600 hover:underline shrink-0"
                        >
                          Review →
                        </a>
                      </div>
                    ))}
                    {pendingDrafts.length > 5 && (
                      <p className="text-xs text-gray-400 px-4 py-2 text-center">
                        +{pendingDrafts.length - 5} more in{" "}
                        <a href="/dashboard/history" className="text-blue-500 hover:underline">History</a>
                      </p>
                    )}
                  </div>
                )}
              </section>

              {/* Escalation alerts */}
              {(highRisk.length > 0 || mediumRisk.length > 0) && (
                <section className="bg-white border border-gray-200 rounded-xl overflow-hidden">
                  <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100">
                    <div className="flex items-center gap-2">
                      <span className="text-base">⚠️</span>
                      <span className="text-sm font-semibold text-gray-800">Accounts needing attention</span>
                      <span className="text-xs bg-red-100 text-red-700 px-1.5 py-0.5 rounded-full font-medium">
                        {highRisk.length + mediumRisk.length}
                      </span>
                    </div>
                    <a href="/dashboard/escalation" className="text-xs text-blue-600 hover:underline">
                      Radar →
                    </a>
                  </div>
                  <div className="divide-y divide-gray-50">
                    {highRisk.map((r) => (
                      <div key={r.id} className="flex items-center gap-3 px-4 py-3">
                        <span className="text-base shrink-0">🔴</span>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium text-gray-800 truncate">
                            {r.client_company || r.client_name}
                          </p>
                          {r.sentiment_summary && (
                            <p className="text-xs text-gray-400 truncate">{r.sentiment_summary}</p>
                          )}
                        </div>
                        <span className="text-xs font-medium text-red-700 bg-red-50 px-2 py-0.5 rounded-full shrink-0">
                          High risk
                        </span>
                      </div>
                    ))}
                    {mediumRisk.map((r) => (
                      <div key={r.id} className="flex items-center gap-3 px-4 py-3">
                        <span className="text-base shrink-0">🟡</span>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium text-gray-800 truncate">
                            {r.client_company || r.client_name}
                          </p>
                          {r.sentiment_summary && (
                            <p className="text-xs text-gray-400 truncate">{r.sentiment_summary}</p>
                          )}
                        </div>
                        <span className="text-xs font-medium text-amber-700 bg-amber-50 px-2 py-0.5 rounded-full shrink-0">
                          Monitor
                        </span>
                      </div>
                    ))}
                  </div>
                </section>
              )}

              {/* Tasks summary */}
              <section className="bg-white border border-gray-200 rounded-xl overflow-hidden">
                <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100">
                  <div className="flex items-center gap-2">
                    <span className="text-base">✅</span>
                    <span className="text-sm font-semibold text-gray-800">Pending tasks</span>
                    {pendingTasks.length > 0 && (
                      <span className="text-xs bg-gray-100 text-gray-600 px-1.5 py-0.5 rounded-full font-medium">
                        {pendingTasks.length}
                      </span>
                    )}
                  </div>
                  <a href="/dashboard/tasks" className="text-xs text-blue-600 hover:underline">
                    View all →
                  </a>
                </div>

                {pendingTasks.length === 0 ? (
                  <p className="text-sm text-gray-400 px-4 py-4">No pending tasks.</p>
                ) : (
                  <div className="px-4 py-3">
                    <div className="flex flex-wrap gap-2">
                      {Object.entries(tasksByClient)
                        .sort((a, b) => b[1] - a[1])
                        .map(([client, count]) => (
                          <span
                            key={client}
                            className="text-xs bg-gray-100 text-gray-700 px-2 py-1 rounded-full"
                          >
                            {client} <span className="font-semibold">({count})</span>
                          </span>
                        ))}
                    </div>
                  </div>
                )}
              </section>

              {/* All clear */}
              {pendingDrafts.length === 0 && highRisk.length === 0 && mediumRisk.length === 0 && pendingTasks.length === 0 && (
                <div className="bg-green-50 border border-green-200 rounded-xl px-4 py-6 text-center">
                  <p className="text-green-700 font-medium text-sm">You're all caught up</p>
                  <p className="text-green-500 text-xs mt-1">No pending drafts, alerts, or tasks right now.</p>
                </div>
              )}
            </div>
          )}
        </div>
      </main>
    </>
  );
}

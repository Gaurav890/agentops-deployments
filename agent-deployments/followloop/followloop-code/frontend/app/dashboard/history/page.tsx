"use client";

import { useEffect, useState } from "react";
import Nav from "@/components/Nav";
import {
  getHistory,
  getTranscript,
  regenerateDraft,
  pushDraftToGmail,
  markDraftUsed,
  addTasks,
  generateWeeklyReport,
  DraftRecord,
} from "@/lib/api";

function getCookie(name: string): string | undefined {
  if (typeof document === "undefined") return undefined;
  return document.cookie
    .split("; ")
    .find((row) => row.startsWith(`${name}=`))
    ?.split("=")[1];
}

type FilterStatus = "all" | "pending" | "sent" | "discarded";
type ExpandedPanel = "transcript" | "draft" | "diff" | "regen" | "tasks" | null;

function statusBadge(draft: DraftRecord) {
  if (draft.status === "sent" && draft.was_edited === false)
    return <span className="text-xs font-medium bg-green-100 text-green-700 px-2 py-0.5 rounded-full">Sent as-is</span>;
  if (draft.status === "sent" && draft.was_edited === true)
    return <span className="text-xs font-medium bg-amber-100 text-amber-700 px-2 py-0.5 rounded-full">Sent with edits</span>;
  if (draft.status === "pending")
    return <span className="text-xs font-medium bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full">In Gmail</span>;
  return <span className="text-xs font-medium bg-red-100 text-red-600 px-2 py-0.5 rounded-full">Not sent</span>;
}

export default function HistoryPage() {
  const [pmId, setPmId] = useState("");
  const [drafts, setDrafts] = useState<DraftRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState<Record<string, ExpandedPanel>>({});
  const [transcripts, setTranscripts] = useState<Record<string, string>>({});
  const [filterStatus, setFilterStatus] = useState<FilterStatus>("all");
  const [searchClient, setSearchClient] = useState("");
  const [collapsedClients, setCollapsedClients] = useState<Record<string, boolean>>({});

  // Regenerate state
  const [regenFeedback, setRegenFeedback] = useState<Record<string, string>>({});
  const [regenDraft, setRegenDraft] = useState<Record<string, string>>({});
  const [regenLoading, setRegenLoading] = useState<Record<string, boolean>>({});
  const [pushLoading, setPushLoading] = useState<Record<string, boolean>>({});
  const [pushDone, setPushDone] = useState<Record<string, boolean>>({});

  // Tasks state per draft
  const [taskChecked, setTaskChecked] = useState<Record<string, Record<number, boolean>>>({});
  const [taskSaving, setTaskSaving] = useState<Record<string, boolean>>({});
  const [taskSaved, setTaskSaved] = useState<Record<string, boolean>>({});

  // Copy-to-use state per draft
  const [copyState, setCopyState] = useState<Record<string, "idle" | "copied" | "done">>({});

  // Report state per client
  const [reportLoading, setReportLoading] = useState<Record<string, boolean>>({});
  const [reportText, setReportText] = useState<Record<string, string>>({});
  const [reportCopied, setReportCopied] = useState<Record<string, boolean>>({});
  const [reportOpen, setReportOpen] = useState<Record<string, boolean>>({});
  const [reportEmailThread, setReportEmailThread] = useState<Record<string, string>>({});
  const [reportWeekEnding, setReportWeekEnding] = useState<Record<string, string>>({});

  useEffect(() => {
    const id = getCookie("pm_id") || "";
    setPmId(id);
    if (id) {
      getHistory(id).then((data) => {
        setDrafts(data);
        setLoading(false);
      });
    }
  }, []);

  // Initialise task checkboxes when tasks panel opens
  function initTaskChecked(draft: DraftRecord) {
    if (taskChecked[draft.id]) return;
    const items = draft.fleetpanda_action_items || [];
    const init: Record<number, boolean> = {};
    items.forEach((_, i) => { init[i] = true; });
    setTaskChecked((prev) => ({ ...prev, [draft.id]: init }));
  }

  function setPanel(draftId: string, panel: ExpandedPanel) {
    setExpanded((prev) => ({ ...prev, [draftId]: prev[draftId] === panel ? null : panel }));
  }

  async function toggleTranscript(draft: DraftRecord) {
    if (!transcripts[draft.id]) {
      const res = await getTranscript(draft.id);
      setTranscripts((prev) => ({ ...prev, [draft.id]: res.transcript }));
    }
    setPanel(draft.id, "transcript");
  }

  async function handleRegenerate(draft: DraftRecord) {
    const feedback = regenFeedback[draft.id] || "";
    setRegenLoading((prev) => ({ ...prev, [draft.id]: true }));
    setPushDone((prev) => ({ ...prev, [draft.id]: false }));
    try {
      const res = await regenerateDraft(draft.id, feedback);
      setRegenDraft((prev) => ({ ...prev, [draft.id]: res.new_draft }));
      setDrafts((prev) =>
        prev.map((d) => (d.id === draft.id ? { ...d, agent_draft: res.new_draft } : d))
      );
    } finally {
      setRegenLoading((prev) => ({ ...prev, [draft.id]: false }));
    }
  }

  async function handlePushToGmail(draft: DraftRecord) {
    const body = regenDraft[draft.id] || draft.agent_draft;
    setPushLoading((prev) => ({ ...prev, [draft.id]: true }));
    try {
      await pushDraftToGmail(draft.id, body);
      setPushDone((prev) => ({ ...prev, [draft.id]: true }));
    } finally {
      setPushLoading((prev) => ({ ...prev, [draft.id]: false }));
    }
  }

  async function handleAddTasks(draft: DraftRecord) {
    const items = draft.fleetpanda_action_items || [];
    const checked = taskChecked[draft.id] || {};
    const descriptions = items
      .filter((_, i) => checked[i] !== false)
      .map((item) => item.action);
    if (!descriptions.length) return;

    setTaskSaving((prev) => ({ ...prev, [draft.id]: true }));
    try {
      await addTasks(pmId, draft.id, draft.client_company || draft.client_name, descriptions);
      setTaskSaved((prev) => ({ ...prev, [draft.id]: true }));
    } finally {
      setTaskSaving((prev) => ({ ...prev, [draft.id]: false }));
    }
  }

  async function handleCopyDraft(draft: DraftRecord) {
    const text = draft.agent_draft || "";
    await navigator.clipboard.writeText(text);
    setCopyState((prev) => ({ ...prev, [draft.id]: "copied" }));
    // After 3 s ask if they edited it — two quick buttons appear
    setTimeout(() => setCopyState((prev) => ({ ...prev, [draft.id]: "done" })), 3000);
    // Fire-and-forget: mark used with was_edited=false (default).
    // If PM says they edited, we'll update again below.
    markDraftUsed(draft.id, false).catch(() => {});
    setDrafts((prev) =>
      prev.map((d) => d.id === draft.id ? { ...d, status: "sent", was_edited: false } : d)
    );
  }

  function handleMarkEdited(draft: DraftRecord) {
    markDraftUsed(draft.id, true).catch(() => {});
    setDrafts((prev) =>
      prev.map((d) => d.id === draft.id ? { ...d, status: "sent", was_edited: true } : d)
    );
    setCopyState((prev) => ({ ...prev, [draft.id]: "idle" }));
  }

  function getThisFriday(): string {
    const d = new Date();
    const daysToFriday = (5 - d.getDay() + 7) % 7;
    d.setDate(d.getDate() + daysToFriday);
    return d.toISOString().slice(0, 10);
  }

  function openReportPanel(clientKey: string) {
    setReportOpen((prev) => ({ ...prev, [clientKey]: true }));
    setReportText((prev) => ({ ...prev, [clientKey]: "" }));
    setReportWeekEnding((prev) => ({ ...prev, [clientKey]: prev[clientKey] || getThisFriday() }));
  }

  async function handleGenerateReport(clientKey: string) {
    const weekEnding = reportWeekEnding[clientKey] || getThisFriday();
    const emailThread = reportEmailThread[clientKey] || "";
    setReportLoading((prev) => ({ ...prev, [clientKey]: true }));
    try {
      const res = await generateWeeklyReport(pmId, clientKey, weekEnding, emailThread);
      setReportText((prev) => ({ ...prev, [clientKey]: res.report_text }));
    } finally {
      setReportLoading((prev) => ({ ...prev, [clientKey]: false }));
    }
  }

  async function handleCopyReport(clientKey: string) {
    await navigator.clipboard.writeText(reportText[clientKey] || "");
    setReportCopied((prev) => ({ ...prev, [clientKey]: true }));
    setTimeout(() => setReportCopied((prev) => ({ ...prev, [clientKey]: false })), 2000);
  }

  // Stats — only count drafts explicitly marked as used (via Copy button).
  // verbatim = 20 min saved, edited = 10 min saved. Never estimate for untracked drafts.
  const now = new Date();
  const weekAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
  const thisWeek = drafts.filter((d) => new Date(d.created_at) >= weekAgo).length;
  const usedDrafts = drafts.filter((d) => d.status === "sent");
  const usedAsIs = usedDrafts.filter((d) => d.was_edited === false).length;
  const usedEdited = usedDrafts.filter((d) => d.was_edited === true).length;
  const pctAsIs = usedDrafts.length ? Math.round((usedAsIs / usedDrafts.length) * 100) : 0;
  const timeSaved = usedAsIs * 20 + usedEdited * 10;

  // Filter
  const filtered = drafts.filter((d) => {
    if (filterStatus !== "all" && d.status !== filterStatus) return false;
    if (searchClient && !d.client_name?.toLowerCase().includes(searchClient.toLowerCase())) return false;
    return true;
  });

  // Group by client (company if available, else name)
  const grouped = filtered.reduce<Record<string, DraftRecord[]>>((acc, d) => {
    const key = d.client_company || d.client_name || "Unknown client";
    if (!acc[key]) acc[key] = [];
    acc[key].push(d);
    return acc;
  }, {});
  const sortedClients = Object.keys(grouped).sort((a, b) => {
    // Sort clients by most recent meeting first
    const latestA = new Date(grouped[a][0].meeting_date || grouped[a][0].created_at).getTime();
    const latestB = new Date(grouped[b][0].meeting_date || grouped[b][0].created_at).getTime();
    return latestB - latestA;
  });

  return (
    <>
    <Nav />
    <main className="min-h-screen bg-gray-50 px-4 pt-10 pb-16">
      <div className="max-w-4xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-semibold text-gray-900">Draft History</h1>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-8">
          {[
            { label: "This week", value: thisWeek },
            { label: "Used as-is", value: usedDrafts.length ? `${usedAsIs} (${pctAsIs}%)` : "—" },
            { label: "Time saved", value: usedDrafts.length ? `${timeSaved} min` : "—" },
            { label: "Total drafts", value: drafts.length },
          ].map((stat) => (
            <div key={stat.label} className="bg-white border border-gray-200 rounded-xl p-4 text-center">
              <p className="text-2xl font-bold text-gray-900">{stat.value}</p>
              <p className="text-xs text-gray-500 mt-1">{stat.label}</p>
            </div>
          ))}
        </div>

        {/* Filters */}
        <div className="flex gap-3 mb-6 flex-wrap">
          <input
            type="text"
            value={searchClient}
            onChange={(e) => setSearchClient(e.target.value)}
            placeholder="Search client…"
            className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value as FilterStatus)}
            className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="all">All statuses</option>
            <option value="pending">In Gmail</option>
            <option value="sent">Sent</option>
            <option value="discarded">Not sent</option>
          </select>
        </div>

        {loading && <p className="text-gray-400 text-sm text-center py-12">Loading…</p>}
        {!loading && filtered.length === 0 && (
          <p className="text-gray-400 text-sm text-center py-12">No drafts found.</p>
        )}

        {/* Grouped by client */}
        <div className="space-y-6">
          {sortedClients.map((clientKey) => {
            const clientDrafts = grouped[clientKey];
            const isCollapsed = collapsedClients[clientKey];
            const pendingCount = clientDrafts.filter((d) => d.status === "pending").length;

            return (
              <div key={clientKey}>
                {/* Client header */}
                <div className="flex items-center justify-between mb-2">
                  <button
                    onClick={() =>
                      setCollapsedClients((prev) => ({ ...prev, [clientKey]: !prev[clientKey] }))
                    }
                    className="flex items-center gap-2 group flex-1 min-w-0"
                  >
                    <span className="text-sm font-semibold text-gray-700">{clientKey}</span>
                    <span className="text-xs text-gray-400">
                      {clientDrafts.length} meeting{clientDrafts.length !== 1 ? "s" : ""}
                    </span>
                    {pendingCount > 0 && (
                      <span className="text-xs bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded-full font-medium">
                        {pendingCount} in Gmail
                      </span>
                    )}
                    <span className="text-xs text-gray-400 group-hover:text-gray-600">
                      {isCollapsed ? "▶" : "▼"}
                    </span>
                  </button>
                  <button
                    onClick={() => openReportPanel(clientKey)}
                    className="text-xs text-indigo-600 hover:text-indigo-800 border border-indigo-200 bg-indigo-50 hover:bg-indigo-100 px-2 py-1 rounded shrink-0 ml-2"
                  >
                    Report
                  </button>
                </div>

                {/* Weekly report panel */}
                {reportOpen[clientKey] && (
                  <div className="mb-3 border border-indigo-200 rounded-xl overflow-hidden bg-indigo-50">
                    <div className="flex items-center justify-between px-4 py-2 border-b border-indigo-100">
                      <p className="text-xs font-semibold text-indigo-700">Weekly Status Report — {clientKey}</p>
                      <div className="flex gap-2">
                        {reportText[clientKey] && (
                          <>
                            <button
                              onClick={() => openReportPanel(clientKey)}
                              className="text-xs text-indigo-600 hover:text-indigo-800 border border-indigo-200 bg-white px-2 py-0.5 rounded"
                            >
                              New
                            </button>
                            <button
                              onClick={() => handleCopyReport(clientKey)}
                              className="text-xs text-indigo-600 hover:text-indigo-800 border border-indigo-200 bg-white px-2 py-0.5 rounded"
                            >
                              {reportCopied[clientKey] ? "✓ Copied" : "Copy"}
                            </button>
                          </>
                        )}
                        <button
                          onClick={() => setReportOpen((prev) => ({ ...prev, [clientKey]: false }))}
                          className="text-xs text-gray-400 hover:text-gray-600"
                        >
                          ✕
                        </button>
                      </div>
                    </div>
                    <div className="px-4 py-3">
                      {reportLoading[clientKey] ? (
                        <p className="text-xs text-indigo-400 text-center py-4">Generating report…</p>
                      ) : reportText[clientKey] ? (
                        <pre className="whitespace-pre-wrap text-xs text-gray-700 font-mono max-h-96 overflow-y-auto">
                          {reportText[clientKey]}
                        </pre>
                      ) : (
                        <div className="space-y-3">
                          <div>
                            <label className="block text-xs font-medium text-indigo-700 mb-1">Week ending</label>
                            <input
                              type="date"
                              value={reportWeekEnding[clientKey] || getThisFriday()}
                              onChange={(e) =>
                                setReportWeekEnding((prev) => ({ ...prev, [clientKey]: e.target.value }))
                              }
                              className="text-sm border border-gray-300 rounded-lg px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-indigo-400 bg-white"
                            />
                          </div>
                          <div>
                            <label className="block text-xs font-medium text-indigo-700 mb-1">
                              Paste email threads{" "}
                              <span className="font-normal text-gray-400">(optional — auto-pulled from meetings too)</span>
                            </label>
                            <textarea
                              value={reportEmailThread[clientKey] || ""}
                              onChange={(e) =>
                                setReportEmailThread((prev) => ({ ...prev, [clientKey]: e.target.value }))
                              }
                              placeholder="e.g. paste forwarded email thread here"
                              rows={4}
                              className="w-full text-sm border border-gray-300 rounded-lg px-3 py-2 text-gray-900 focus:outline-none focus:ring-2 focus:ring-indigo-400 resize-none bg-white"
                            />
                          </div>
                          <button
                            onClick={() => handleGenerateReport(clientKey)}
                            className="text-sm bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-1.5 rounded-lg"
                          >
                            Generate Report
                          </button>
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {!isCollapsed && (
                  <div className="space-y-2 pl-0">
                    {clientDrafts.map((draft) => {
                      const items = draft.fleetpanda_action_items || [];
                      const checked = taskChecked[draft.id] || {};

                      return (
                        <div key={draft.id} className="bg-white border border-gray-200 rounded-xl overflow-hidden">
                          <div className="flex items-center gap-4 px-4 py-3">
                            <div className="flex-1 min-w-0">
                              <p className="font-medium text-gray-900 truncate text-sm">
                                {draft.meeting_title || draft.meeting_type?.replace(/_/g, " ")}
                              </p>
                              <p className="text-xs text-gray-400 mt-0.5">
                                {new Date(draft.meeting_date || draft.created_at).toLocaleDateString("en-US", {
                                  month: "short",
                                  day: "numeric",
                                  year: "numeric",
                                  hour: "2-digit",
                                  minute: "2-digit",
                                })}
                              </p>
                            </div>
                            <div className="flex items-center gap-2 shrink-0 flex-wrap justify-end">
                              {statusBadge(draft)}

                              {/* Copy draft + usage tracking */}
                              {draft.status === "pending" && copyState[draft.id] !== "done" && copyState[draft.id] !== "copied" && (
                                <button
                                  onClick={() => handleCopyDraft(draft)}
                                  className="text-xs text-gray-600 hover:text-gray-900 border border-gray-200 bg-white hover:bg-gray-50 px-2 py-1 rounded"
                                  title="Copy draft to clipboard and mark as used"
                                >
                                  Copy
                                </button>
                              )}
                              {copyState[draft.id] === "copied" && (
                                <span className="text-xs text-green-600 font-medium">✓ Copied!</span>
                              )}
                              {copyState[draft.id] === "done" && (
                                <div className="flex items-center gap-1">
                                  <span className="text-xs text-gray-400">Edited?</span>
                                  <button
                                    onClick={() => handleMarkEdited(draft)}
                                    className="text-xs text-amber-600 border border-amber-200 px-1.5 py-0.5 rounded hover:bg-amber-50"
                                  >
                                    Yes
                                  </button>
                                  <button
                                    onClick={() => setCopyState((prev) => ({ ...prev, [draft.id]: "idle" }))}
                                    className="text-xs text-gray-400 border border-gray-200 px-1.5 py-0.5 rounded hover:bg-gray-50"
                                  >
                                    No
                                  </button>
                                </div>
                              )}

                              {items.length > 0 && (
                                <button
                                  onClick={() => {
                                    initTaskChecked(draft);
                                    setPanel(draft.id, "tasks");
                                  }}
                                  title="Add my to-dos to task board"
                                  className="text-xs font-bold text-emerald-700 hover:text-emerald-900 border border-emerald-200 bg-emerald-50 hover:bg-emerald-100 w-6 h-6 flex items-center justify-center rounded"
                                >
                                  +
                                </button>
                              )}
                              <button
                                onClick={() => toggleTranscript(draft)}
                                className="text-xs text-gray-500 hover:text-blue-600 border border-gray-200 px-2 py-1 rounded"
                              >
                                Transcript
                              </button>
                              <button
                                onClick={() => setPanel(draft.id, "draft")}
                                className="text-xs text-gray-500 hover:text-blue-600 border border-gray-200 px-2 py-1 rounded"
                              >
                                Draft
                              </button>
                              {draft.was_edited && (
                                <button
                                  onClick={() => setPanel(draft.id, "diff")}
                                  className="text-xs text-amber-600 hover:text-amber-800 border border-amber-200 px-2 py-1 rounded"
                                >
                                  View diff
                                </button>
                              )}
                              {draft.status === "pending" && (
                                <button
                                  onClick={() => setPanel(draft.id, "regen")}
                                  className="text-xs text-purple-600 hover:text-purple-800 border border-purple-200 px-2 py-1 rounded"
                                >
                                  Regenerate
                                </button>
                              )}
                            </div>
                          </div>

                          {/* Tasks panel */}
                          {expanded[draft.id] === "tasks" && (
                            <div className="border-t border-gray-100 px-4 py-4 bg-emerald-50">
                              <p className="text-xs font-medium text-emerald-800 mb-3">
                                FleetPanda action items — select which to add to your tasks board:
                              </p>
                              {items.length === 0 ? (
                                <p className="text-xs text-gray-400">No action items extracted for this meeting.</p>
                              ) : (
                                <div className="space-y-2 mb-3">
                                  {items.map((item, i) => (
                                    <label key={i} className="flex items-start gap-2 cursor-pointer">
                                      <input
                                        type="checkbox"
                                        checked={checked[i] !== false}
                                        onChange={(e) =>
                                          setTaskChecked((prev) => ({
                                            ...prev,
                                            [draft.id]: { ...prev[draft.id], [i]: e.target.checked },
                                          }))
                                        }
                                        className="mt-0.5 accent-emerald-600"
                                      />
                                      <span className="text-xs text-gray-700">
                                        {item.action}
                                        {item.owner && (
                                          <span className="text-gray-400 ml-1">— {item.owner}</span>
                                        )}
                                      </span>
                                    </label>
                                  ))}
                                </div>
                              )}
                              {items.length > 0 && (
                                <button
                                  onClick={() => handleAddTasks(draft)}
                                  disabled={taskSaving[draft.id] || taskSaved[draft.id]}
                                  className="text-sm bg-emerald-600 hover:bg-emerald-700 text-white px-4 py-1.5 rounded-lg disabled:opacity-50"
                                >
                                  {taskSaved[draft.id]
                                    ? "✓ Added to tasks"
                                    : taskSaving[draft.id]
                                    ? "Saving…"
                                    : "Add to my tasks"}
                                </button>
                              )}
                            </div>
                          )}

                          {expanded[draft.id] === "transcript" && (
                            <div className="border-t border-gray-100 px-4 py-3 bg-gray-50">
                              <pre className="whitespace-pre-wrap text-xs text-gray-600 font-mono max-h-72 overflow-y-auto">
                                {transcripts[draft.id] || "Loading…"}
                              </pre>
                            </div>
                          )}

                          {expanded[draft.id] === "draft" && (
                            <div className="border-t border-gray-100 px-4 py-3 bg-gray-50">
                              <pre className="whitespace-pre-wrap text-sm text-gray-700 font-mono max-h-72 overflow-y-auto">
                                {draft.agent_draft}
                              </pre>
                            </div>
                          )}

                          {expanded[draft.id] === "diff" && draft.edit_diff && (
                            <div className="border-t border-gray-100 px-4 py-3 bg-gray-50">
                              <p className="text-xs font-medium text-gray-500 mb-2">Changes you made:</p>
                              <div className="space-y-1 text-xs font-mono max-h-72 overflow-y-auto">
                                {draft.edit_diff.removed.map((line, i) => (
                                  <div key={`r-${i}`} className="bg-red-50 text-red-700 px-2 py-0.5 rounded">
                                    − {line}
                                  </div>
                                ))}
                                {draft.edit_diff.added.map((line, i) => (
                                  <div key={`a-${i}`} className="bg-green-50 text-green-700 px-2 py-0.5 rounded">
                                    + {line}
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}

                          {expanded[draft.id] === "regen" && (
                            <div className="border-t border-gray-100 px-4 py-4 bg-purple-50 space-y-3">
                              <p className="text-xs font-medium text-purple-700">
                                Tell Claude what to fix, then push the updated draft back to Gmail.
                              </p>
                              <div className="text-xs text-gray-500 font-mono bg-white border border-gray-200 rounded p-3 max-h-48 overflow-y-auto whitespace-pre-wrap">
                                {regenDraft[draft.id] || draft.agent_draft}
                              </div>
                              <textarea
                                value={regenFeedback[draft.id] || ""}
                                onChange={(e) =>
                                  setRegenFeedback((prev) => ({ ...prev, [draft.id]: e.target.value }))
                                }
                                placeholder="e.g. You missed the loading numbers discussion. Also mention we're pushing live to next Friday."
                                rows={3}
                                className="w-full text-sm border border-gray-300 rounded-lg px-3 py-2 text-gray-900 focus:outline-none focus:ring-2 focus:ring-purple-400 resize-none"
                              />
                              <div className="flex gap-2">
                                <button
                                  onClick={() => handleRegenerate(draft)}
                                  disabled={regenLoading[draft.id]}
                                  className="text-sm bg-purple-600 hover:bg-purple-700 text-white px-4 py-1.5 rounded-lg disabled:opacity-50"
                                >
                                  {regenLoading[draft.id] ? "Regenerating…" : "Regenerate"}
                                </button>
                                {regenDraft[draft.id] && (
                                  <button
                                    onClick={() => handlePushToGmail(draft)}
                                    disabled={pushLoading[draft.id] || pushDone[draft.id]}
                                    className="text-sm bg-green-600 hover:bg-green-700 text-white px-4 py-1.5 rounded-lg disabled:opacity-50"
                                  >
                                    {pushDone[draft.id]
                                      ? "✓ Updated in Gmail"
                                      : pushLoading[draft.id]
                                      ? "Pushing…"
                                      : "Push to Gmail"}
                                  </button>
                                )}
                              </div>
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </main>
    </>
  );
}

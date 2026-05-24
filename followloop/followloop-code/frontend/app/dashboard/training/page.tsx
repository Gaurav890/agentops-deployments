"use client";

import { useEffect, useState } from "react";
import Nav from "@/components/Nav";
import {
  getSamples,
  addSample,
  deleteSample,
  getStylePreview,
  StyleSample,
} from "@/lib/api";

const MEETING_TYPES = [
  { value: "onboarding", label: "Onboarding" },
  { value: "weekly_sync", label: "Weekly Sync" },
  { value: "qbr", label: "QBR" },
  { value: "kickoff", label: "Kickoff" },
  { value: "escalation", label: "Escalation" },
  { value: "other", label: "Other" },
];

function getCookie(name: string): string | undefined {
  if (typeof document === "undefined") return undefined;
  return document.cookie
    .split("; ")
    .find((row) => row.startsWith(`${name}=`))
    ?.split("=")[1];
}

export default function TrainingPage() {
  const [pmId, setPmId] = useState("");
  const [samples, setSamples] = useState<StyleSample[]>([]);
  const [emailBody, setEmailBody] = useState("");
  const [meetingType, setMeetingType] = useState("weekly_sync");
  const [clientName, setClientName] = useState("");
  const [saving, setSaving] = useState(false);
  const [preview, setPreview] = useState<string | null>(null);
  const [previewing, setPreviewing] = useState(false);
  const [previewError, setPreviewError] = useState("");
  const [isLive, setIsLive] = useState(false);
  const [needsReauth, setNeedsReauth] = useState(false);

  useEffect(() => {
    const id = getCookie("pm_id") || "";
    setPmId(id);
    if (id) {
      loadSamples(id);
      fetch(`/api/pm/${id}/needs-reauth`, { credentials: "include" })
        .then((r) => r.json())
        .then((d) => setNeedsReauth(d.needs_reauth === true))
        .catch(() => {});
    }
  }, []);

  async function loadSamples(id: string) {
    const data = await getSamples(id);
    setSamples(data);
    setIsLive(data.length >= 3);
  }

  async function handleAdd() {
    if (!emailBody.trim()) return;
    setSaving(true);
    try {
      await addSample({ pm_id: pmId, meeting_type: meetingType, email_body: emailBody, client_name: clientName });
      setEmailBody("");
      setClientName("");
      await loadSamples(pmId);
      runPreview(pmId);
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(id: string) {
    await deleteSample(id);
    await loadSamples(pmId);
    runPreview(pmId);
  }

  async function runPreview(id?: string) {
    const targetId = id || pmId;
    if (!targetId) return;
    setPreviewing(true);
    setPreviewError("");
    try {
      const res = await getStylePreview(targetId);
      setPreview(res.draft);
    } catch (e: unknown) {
      setPreviewError(e instanceof Error ? e.message : "Preview failed");
    } finally {
      setPreviewing(false);
    }
  }

  const progress = Math.min((samples.length / 10) * 100, 100);

  return (
    <>
    <Nav />
    <main className="min-h-screen bg-gray-50 px-4 pt-10 pb-16">
      <div className="max-w-5xl mx-auto">
        {needsReauth && (
          <div className="mb-5 flex items-center justify-between gap-4 bg-amber-50 border border-amber-200 rounded-xl px-4 py-3">
            <p className="text-sm text-amber-800">
              <span className="font-semibold">Action needed:</span> Reconnect Google so the agent can read your email history with clients and write smarter follow-ups.
            </p>
            <a
              href="/api/auth/google"
              className="shrink-0 text-sm font-medium bg-amber-600 hover:bg-amber-700 text-white px-4 py-1.5 rounded-lg"
            >
              Reconnect Google →
            </a>
          </div>
        )}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-semibold text-gray-900">Style Training</h1>
            <p className="text-gray-500 text-sm mt-1">
              Paste past emails so Claude learns your writing style.
            </p>
          </div>
          <a href="/dashboard/history" className="text-sm text-blue-600 hover:underline">
            View history →
          </a>
        </div>

        {isLive && (
          <div className="bg-green-50 border border-green-200 rounded-xl px-4 py-3 mb-6 text-green-800 text-sm font-medium">
            ✓ Setup complete — you&apos;re live. The agent will draft emails after your next meeting.
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Left: sample list */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-gray-700">
                {samples.length} sample{samples.length !== 1 ? "s" : ""} added (target: 5–10)
              </span>
            </div>
            <div className="h-2 bg-gray-100 rounded-full mb-4">
              <div
                className="h-2 bg-blue-500 rounded-full transition-all"
                style={{ width: `${progress}%` }}
              />
            </div>

            {samples.length === 0 && (
              <p className="text-gray-400 text-sm text-center py-8">No samples yet — add your first one →</p>
            )}

            <div className="space-y-2">
              {samples.map((s) => (
                <div
                  key={s.id}
                  className="bg-white border border-gray-200 rounded-lg p-3 flex gap-3 items-start"
                >
                  <span className="text-xs font-medium bg-blue-50 text-blue-700 px-2 py-0.5 rounded whitespace-nowrap">
                    {MEETING_TYPES.find((t) => t.value === s.meeting_type)?.label ?? s.meeting_type}
                  </span>
                  <p className="text-xs text-gray-600 flex-1 line-clamp-2">
                    {s.email_body.slice(0, 80)}…
                  </p>
                  <button
                    onClick={() => handleDelete(s.id)}
                    className="text-gray-300 hover:text-red-400 text-xs shrink-0"
                  >
                    ✕
                  </button>
                </div>
              ))}
            </div>
          </div>

          {/* Right: add new sample */}
          <div className="bg-white border border-gray-200 rounded-xl p-5">
            <h2 className="font-medium text-gray-900 mb-3">Add a sample email</h2>

            <label className="block text-xs font-medium text-gray-600 mb-1">Meeting type</label>
            <select
              value={meetingType}
              onChange={(e) => setMeetingType(e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm mb-3 text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {MEETING_TYPES.map((t) => (
                <option key={t.value} value={t.value}>{t.label}</option>
              ))}
            </select>

            <label className="block text-xs font-medium text-gray-600 mb-1">Client name (optional)</label>
            <input
              type="text"
              value={clientName}
              onChange={(e) => setClientName(e.target.value)}
              placeholder="e.g. Raj at Acme"
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm mb-3 text-gray-900 placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />

            <label className="block text-xs font-medium text-gray-600 mb-1">Email body</label>
            <textarea
              value={emailBody}
              onChange={(e) => setEmailBody(e.target.value)}
              rows={8}
              placeholder={"Hi Raj,\n\nGreat meeting today..."}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm resize-none text-gray-900 placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 mb-3 font-mono"
            />

            <button
              onClick={handleAdd}
              disabled={saving || !emailBody.trim()}
              className="w-full bg-blue-600 text-white text-sm font-medium py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50 transition"
            >
              {saving ? "Saving…" : "Save sample"}
            </button>
          </div>
        </div>

        {/* Style preview */}
        <div className="mt-8 bg-white border border-gray-200 rounded-xl p-5">
          <div className="flex items-center justify-between mb-3">
            <div>
              <h2 className="font-medium text-gray-900">Style preview</h2>
              <p className="text-xs text-gray-400 mt-0.5">Based on your samples, drafts will look like this</p>
            </div>
            <button
              onClick={() => runPreview()}
              disabled={previewing || samples.length === 0}
              className="text-sm text-blue-600 hover:underline disabled:opacity-40"
            >
              {previewing ? "Generating…" : "Preview how my emails will look"}
            </button>
          </div>

          {previewError && (
            <p className="text-red-500 text-sm mb-3">{previewError}</p>
          )}
          {preview ? (
            <pre className="whitespace-pre-wrap text-sm text-gray-700 bg-gray-50 rounded-lg p-4 font-mono leading-relaxed">
              {preview}
            </pre>
          ) : (
            <p className="text-gray-400 text-sm text-center py-6">
              Add at least 1 sample and click &quot;Preview&quot; to see a draft example.
            </p>
          )}
        </div>
      </div>
    </main>
    </>
  );
}

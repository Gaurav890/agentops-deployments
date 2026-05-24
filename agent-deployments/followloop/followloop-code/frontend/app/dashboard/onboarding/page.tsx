"use client";

import { useEffect, useState } from "react";
import { saveSlackId } from "@/lib/api";

type Step = "signin" | "google" | "slack";

interface StepState {
  signin: boolean;
  google: boolean;
  slack: boolean;
}

function getCookie(name: string): string | undefined {
  return document.cookie
    .split("; ")
    .find((row) => row.startsWith(`${name}=`))
    ?.split("=")[1];
}

export default function OnboardingPage() {
  const [pmId, setPmId] = useState<string>("");
  const [pmEmail, setPmEmail] = useState<string>("");
  const [completed, setCompleted] = useState<StepState>({
    signin: false,
    google: false,
    slack: false,
  });
  const [slackInput, setSlackInput] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    const id = getCookie("pm_id") || "";
    setPmId(id);

    // Step 1: auto-complete (they signed in to reach this page)
    // Step 2: auto-complete — we request all Google scopes on first sign-in,
    //         so gmail.compose + calendar.readonly are already granted.
    //         Also marked done via ?google=done after the OAuth callback.
    const params = new URLSearchParams(window.location.search);
    const googleDone = params.get("google") === "done";
    setCompleted((prev) => ({ ...prev, signin: true, google: googleDone || !!id }));
  }, []);

  async function handleSaveSlack() {
    if (!slackInput.trim()) return;
    setSaving(true);
    setError("");
    try {
      await saveSlackId(pmId, slackInput.trim());
      setCompleted((prev) => ({ ...prev, slack: true }));
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to save Slack ID");
    } finally {
      setSaving(false);
    }
  }

  // Slack is optional — only steps 1 and 2 are required to proceed
  const allDone = completed.signin && completed.google;

  return (
    <main className="min-h-screen bg-gray-50 flex flex-col items-center pt-16 px-4">
      <div className="max-w-lg w-full">
        <h1 className="text-2xl font-semibold text-gray-900 mb-1">Set up your account</h1>
        <p className="text-gray-500 text-sm mb-8">Complete steps 1 and 2 to activate the agent. Slack is optional.</p>

        {/* Step 1 */}
        <StepCard
          number={1}
          title="Sign in with Google"
          done={completed.signin}
          active={true}
        >
          {completed.signin && pmEmail && (
            <p className="text-sm text-gray-600">Signed in as {pmEmail}</p>
          )}
          {completed.signin && !pmEmail && (
            <p className="text-sm text-green-600 font-medium">Signed in successfully</p>
          )}
        </StepCard>

        {/* Step 2 */}
        <StepCard
          number={2}
          title="Grant Gmail + Calendar access"
          done={completed.google}
          active={completed.signin}
        >
          {!completed.google ? (
            <div>
              <p className="text-sm text-gray-500 mb-3">
                We create email drafts in your Gmail. <span className="font-medium text-gray-700">Draft only — we cannot read your inbox.</span>
              </p>
              <a
                href="/api/auth/google"
                className="inline-block bg-blue-600 text-white text-sm font-medium px-4 py-2 rounded-lg hover:bg-blue-700 transition"
              >
                Connect Google account
              </a>
            </div>
          ) : (
            <p className="text-sm text-green-600 font-medium">Gmail + Calendar connected</p>
          )}
        </StepCard>

        {/* Step 3 */}
        <StepCard
          number={3}
          title="Add your Slack user ID"
          optional={true}
          done={completed.slack}
          active={completed.google}
        >
          {!completed.slack ? (
            <div>
              <p className="text-sm text-gray-500 mb-2">
                Optional — we&apos;ll DM you in Slack when your draft is ready.
                <br />
                <span className="text-xs text-gray-400">
                  Find your ID: Slack → click your name → Profile → More → Copy member ID (format: U0XXXXXXX)
                </span>
              </p>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={slackInput}
                  onChange={(e) => setSlackInput(e.target.value)}
                  placeholder="U0XXXXXXX"
                  className="border border-gray-300 rounded-lg px-3 py-2 text-sm flex-1 text-gray-900 placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  disabled={!completed.google}
                />
                <button
                  onClick={handleSaveSlack}
                  disabled={saving || !slackInput.trim()}
                  className="bg-blue-600 text-white text-sm font-medium px-4 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50 transition"
                >
                  {saving ? "Saving..." : "Save"}
                </button>
              </div>
              {error && <p className="text-red-500 text-xs mt-1">{error}</p>}
            </div>
          ) : (
            <p className="text-sm text-green-600 font-medium">Slack ID saved</p>
          )}
        </StepCard>

        {allDone && (
          <div className="mt-6 text-center">
            <a
              href="/dashboard/training"
              className="inline-block bg-green-600 text-white font-medium px-6 py-3 rounded-lg hover:bg-green-700 transition"
            >
              Go to style training →
            </a>
          </div>
        )}
      </div>
    </main>
  );
}

function StepCard({
  number,
  title,
  done,
  active,
  optional = false,
  children,
}: {
  number: number;
  title: string;
  done: boolean;
  active: boolean;
  optional?: boolean;
  children: React.ReactNode;
}) {
  return (
    <div
      className={`bg-white rounded-xl border p-5 mb-4 transition ${
        !active ? "opacity-50 pointer-events-none" : ""
      } ${done ? "border-green-200" : "border-gray-200"}`}
    >
      <div className="flex items-center gap-3 mb-3">
        <div
          className={`w-7 h-7 rounded-full flex items-center justify-center text-sm font-semibold ${
            done
              ? "bg-green-100 text-green-700"
              : active
              ? "bg-blue-100 text-blue-700"
              : "bg-gray-100 text-gray-400"
          }`}
        >
          {done ? "✓" : number}
        </div>
        <h2 className="font-medium text-gray-900">{title}</h2>
        {optional && (
          <span className="text-xs font-medium text-gray-400 bg-gray-100 px-2 py-0.5 rounded-full">Optional</span>
        )}
      </div>
      {children}
    </div>
  );
}

// Empty string = same origin. Next.js rewrites proxy /api/* → Flask.
const API_BASE = "";

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...options.headers },
    credentials: "include",
    ...options,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API ${path} failed ${res.status}: ${text}`);
  }
  return res.json();
}

// Style samples
export const getSamples = (pmId: string) =>
  request<StyleSample[]>(`/api/samples?pm_id=${pmId}`);

export const addSample = (data: {
  pm_id: string;
  meeting_type: string;
  email_body: string;
  client_name?: string;
}) => request<StyleSample>("/api/samples", { method: "POST", body: JSON.stringify(data) });

export const deleteSample = (id: string) =>
  request<{ ok: boolean }>(`/api/samples/${id}`, { method: "DELETE" });

export const getStylePreview = (pmId: string) =>
  request<{ draft: string }>("/api/style-preview", {
    method: "POST",
    body: JSON.stringify({ pm_id: pmId }),
  });

// Onboarding
export const saveSlackId = (pmId: string, slackUserId: string) =>
  request<{ ok: boolean }>("/api/onboarding/slack", {
    method: "POST",
    body: JSON.stringify({ pm_id: pmId, slack_user_id: slackUserId }),
  });

// History
export const getHistory = (pmId: string) =>
  request<DraftRecord[]>(`/api/history?pm_id=${pmId}`);

export const getTranscript = (draftId: string) =>
  request<{ transcript: string }>(`/api/history/${draftId}/transcript`);

// Enhancement 3: in-dashboard draft regeneration
export const regenerateDraft = (draftId: string, feedback: string) =>
  request<{ new_draft: string }>(`/api/drafts/${draftId}/regenerate`, {
    method: "POST",
    body: JSON.stringify({ feedback }),
  });

export const pushDraftToGmail = (draftId: string, body: string) =>
  request<{ ok: boolean }>(`/api/drafts/${draftId}/push-to-gmail`, {
    method: "POST",
    body: JSON.stringify({ body }),
  });

export const markDraftUsed = (draftId: string, wasEdited: boolean) =>
  request<{ ok: boolean }>(`/api/drafts/${draftId}/mark-used`, {
    method: "POST",
    body: JSON.stringify({ was_edited: wasEdited }),
  });

// Tasks
export const getTasks = (pmId: string) =>
  request<Task[]>(`/api/tasks?pm_id=${pmId}`);

export const addTasks = (
  pmId: string,
  draftId: string,
  clientName: string,
  descriptions: string[]
) =>
  request<Task[]>("/api/tasks", {
    method: "POST",
    body: JSON.stringify({ pm_id: pmId, draft_id: draftId, client_name: clientName, descriptions }),
  });

export const updateTaskStatus = (taskId: string, status: "pending" | "done") =>
  request<{ ok: boolean }>(`/api/tasks/${taskId}`, {
    method: "PATCH",
    body: JSON.stringify({ status }),
  });

// Escalation
export const getEscalation = (pmId: string) =>
  request<EscalationRow[]>(`/api/escalation?pm_id=${pmId}`);

// Weekly report
export const generateWeeklyReport = (pmId: string, clientName: string, weekEnding: string, emailThread?: string) =>
  request<{ report_text: string }>("/api/reports/weekly", {
    method: "POST",
    body: JSON.stringify({ pm_id: pmId, client_name: clientName, week_ending: weekEnding, email_thread: emailThread || "" }),
  });

// Auth
export const exchangeGoogleCode = (code: string) =>
  request<{ pm_id: string; session_token: string }>("/auth/google/exchange", {
    method: "POST",
    body: JSON.stringify({ code }),
  });

// Types
export interface StyleSample {
  id: string;
  pm_id: string;
  meeting_type: string;
  email_body: string;
  client_name?: string;
  created_at: string;
}

export interface DraftRecord {
  id: string;
  pm_id: string;
  client_name: string;
  client_company?: string;
  meeting_type: string;
  meeting_date: string;
  agent_draft: string;
  sent_draft?: string;
  status: "pending" | "sent" | "discarded";
  was_edited?: boolean;
  edit_diff?: { removed: string[]; added: string[] };
  gmail_draft_id?: string;
  slack_notified_at?: string;
  created_at: string;
  transcript?: string;
  fleetpanda_action_items?: Array<{ action: string; owner?: string; due_date?: string | null }>;
  meeting_title?: string;
}

export interface Task {
  id: string;
  pm_id: string;
  draft_id: string;
  client_name: string;
  description: string;
  status: "pending" | "done";
  created_at: string;
  completed_at?: string;
}

export interface EscalationRow {
  id: string;
  client_name: string;
  client_company?: string;
  meeting_type: string;
  meeting_date: string;
  escalation_risk: "high" | "medium" | "low" | "healthy" | "unknown";
  risk_signals?: string[];
  sentiment_summary?: string;
}

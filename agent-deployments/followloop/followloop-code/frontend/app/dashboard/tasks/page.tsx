"use client";

import { useEffect, useState } from "react";
import Nav from "@/components/Nav";
import { getTasks, updateTaskStatus, Task } from "@/lib/api";

function getCookie(name: string): string | undefined {
  if (typeof document === "undefined") return undefined;
  return document.cookie
    .split("; ")
    .find((row) => row.startsWith(`${name}=`))
    ?.split("=")[1];
}

export default function TasksPage() {
  const [pmId, setPmId] = useState("");
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [showDone, setShowDone] = useState(false);
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>({});

  useEffect(() => {
    const id = getCookie("pm_id") || "";
    setPmId(id);
    if (id) {
      getTasks(id).then((data) => {
        setTasks(data);
        setLoading(false);
      });
    }
  }, []);

  async function toggle(task: Task) {
    const newStatus = task.status === "done" ? "pending" : "done";
    await updateTaskStatus(task.id, newStatus);
    setTasks((prev) =>
      prev.map((t) => (t.id === task.id ? { ...t, status: newStatus } : t))
    );
  }

  const pending = tasks.filter((t) => t.status === "pending");
  const done = tasks.filter((t) => t.status === "done");

  // Group pending tasks by client
  const grouped = pending.reduce<Record<string, Task[]>>((acc, t) => {
    const key = t.client_name || "Other";
    if (!acc[key]) acc[key] = [];
    acc[key].push(t);
    return acc;
  }, {});
  const sortedClients = Object.keys(grouped).sort();

  return (
    <>
    <Nav />
    <main className="min-h-screen bg-gray-50 px-4 pt-10 pb-16">
      <div className="max-w-2xl mx-auto">
        <div className="mb-6">
          <h1 className="text-2xl font-semibold text-gray-900">My Tasks</h1>
          <p className="text-gray-500 text-sm mt-1">Action items from your meetings</p>
        </div>

        {loading && <p className="text-gray-400 text-sm text-center py-12">Loading…</p>}

        {!loading && pending.length === 0 && (
          <div className="bg-white border border-gray-200 rounded-xl p-8 text-center">
            <p className="text-gray-400 text-sm">No pending tasks.</p>
            <p className="text-gray-300 text-xs mt-1">
              Click the + button on a meeting in History to add action items here.
            </p>
          </div>
        )}

        {/* Pending tasks grouped by client */}
        {sortedClients.map((client) => {
          const isCollapsed = collapsed[client];
          const count = grouped[client].length;
          return (
            <div key={client} className="mb-4">
              <button
                onClick={() => setCollapsed((prev) => ({ ...prev, [client]: !prev[client] }))}
                className="w-full flex items-center justify-between py-1.5 group mb-2"
              >
                <div className="flex items-center gap-2">
                  <span className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
                    {client}
                  </span>
                  <span className="text-xs text-gray-400 bg-gray-100 px-1.5 py-0.5 rounded-full">
                    {count}
                  </span>
                </div>
                <span className="text-xs text-gray-400 group-hover:text-gray-600">
                  {isCollapsed ? "▶" : "▼"}
                </span>
              </button>

              {!isCollapsed && (
                <div className="space-y-2">
                  {grouped[client].map((task) => (
                    <div
                      key={task.id}
                      className="bg-white border border-gray-200 rounded-xl px-4 py-3 flex items-start gap-3"
                    >
                      <button
                        onClick={() => toggle(task)}
                        className="mt-0.5 w-5 h-5 rounded-full border-2 border-gray-300 hover:border-emerald-500 flex items-center justify-center shrink-0 transition-colors"
                      >
                        <span className="w-2.5 h-2.5 rounded-full bg-transparent" />
                      </button>
                      <p className="text-sm text-gray-800 flex-1">{task.description}</p>
                      <p className="text-xs text-gray-400 shrink-0">
                        {new Date(task.created_at).toLocaleDateString("en-US", {
                          month: "short",
                          day: "numeric",
                        })}
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          );
        })}

        {/* Completed tasks */}
        {done.length > 0 && (
          <div className="mt-6">
            <button
              onClick={() => setShowDone((v) => !v)}
              className="text-xs text-gray-400 hover:text-gray-600 mb-2"
            >
              {showDone ? "Hide" : "Show"} {done.length} completed task{done.length !== 1 ? "s" : ""}
            </button>
            {showDone && (
              <div className="space-y-2">
                {done.map((task) => (
                  <div
                    key={task.id}
                    className="bg-white border border-gray-100 rounded-xl px-4 py-3 flex items-start gap-3 opacity-50"
                  >
                    <button
                      onClick={() => toggle(task)}
                      className="mt-0.5 w-5 h-5 rounded-full border-2 border-emerald-400 bg-emerald-400 flex items-center justify-center shrink-0"
                    >
                      <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                      </svg>
                    </button>
                    <p className="text-sm text-gray-500 flex-1 line-through">{task.description}</p>
                    <p className="text-xs text-gray-300 shrink-0">
                      {task.client_name}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </main>
    </>
  );
}

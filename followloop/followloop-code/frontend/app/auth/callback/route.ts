import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:5000";

/**
 * GET /auth/callback?code=...
 * Exchanges the Google auth code for tokens via Flask backend,
 * sets an httpOnly session cookie, then redirects to onboarding.
 */
export async function GET(req: NextRequest) {
  const code = req.nextUrl.searchParams.get("code");

  if (!code) {
    return NextResponse.redirect(new URL("/?error=missing_code", req.url));
  }

  const res = await fetch(`${API_BASE}/auth/google/exchange`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ code }),
  });

  if (!res.ok) {
    console.error("Token exchange failed:", await res.text());
    return NextResponse.redirect(new URL("/?error=exchange_failed", req.url));
  }

  const { pm_id, session_token } = await res.json();

  const cookieStore = await cookies();
  cookieStore.set("session_token", session_token, {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    maxAge: 60 * 60 * 24 * 30, // 30 days
    path: "/",
  });

  cookieStore.set("pm_id", pm_id, {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    maxAge: 60 * 60 * 24 * 30,
    path: "/",
  });

  return NextResponse.redirect(new URL("/dashboard/onboarding", req.url));
}

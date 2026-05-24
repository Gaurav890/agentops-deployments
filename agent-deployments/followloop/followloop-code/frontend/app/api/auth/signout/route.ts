import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";

export async function GET(req: NextRequest) {
  const cookieStore = await cookies();
  cookieStore.delete("session_token");
  cookieStore.delete("pm_id");
  return NextResponse.redirect(new URL("/", req.url));
}

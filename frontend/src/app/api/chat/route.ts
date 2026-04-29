import { NextRequest, NextResponse } from "next/server";

const BACKEND = process.env.LANGGRAPH_API_BASE ?? "http://127.0.0.1:8000";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const res = await fetch(`${BACKEND}/webhook/test`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await res.json();
    return NextResponse.json(data, { status: res.ok ? 200 : res.status });
  } catch {
    return NextResponse.json(
      { error: "Backend indisponível. Certifique-se de que o NanoAssist está rodando em localhost:8000." },
      { status: 503 },
    );
  }
}

import { type NextRequest, NextResponse } from "next/server"

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000"

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { disease } = body

    if (!disease || typeof disease !== "string" || disease.trim().length === 0) {
      return NextResponse.json({ success: false, error: "Disease name is required" }, { status: 400 })
    }

    const response = await fetch(`${BACKEND_URL}/disease-info`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ disease_name: disease }),
    })

    if (!response.ok) {
      const errorData = await response.json()
      throw new Error(errorData.detail || "Backend request failed")
    }

    const result = await response.json()
    return NextResponse.json({ success: true, info: result })
  } catch (error: any) {
    console.error("Disease info error:", error)
    const message = error instanceof Error ? error.message : "Failed to fetch disease info"
    return NextResponse.json({ success: false, error: message }, { status: 500 })
  }
}
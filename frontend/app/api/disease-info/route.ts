import { type NextRequest, NextResponse } from "next/server"

const BACKEND_URL = (process.env.BACKEND_URL || "http://localhost:8000").replace(/\/$/, "")

export async function POST(request: NextRequest) {
  console.log("Disease info request received at frontend API")
  try {
    const body = await request.json()
    const { disease } = body

    if (!disease || typeof disease !== "string" || disease.trim().length === 0) {
      console.error("Invalid disease name provided")
      return NextResponse.json({ success: false, error: "Disease name is required" }, { status: 400 })
    }

    console.log(`Forwarding disease info request to backend: ${BACKEND_URL}/disease-info`)
    
    const response = await fetch(`${BACKEND_URL}/disease-info`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ disease_name: disease }),
    })

    if (!response.ok) {
      let errorMessage = "Backend request failed"
      try {
        const errorData = await response.json()
        errorMessage = errorData.detail || errorMessage
      } catch (e) {
        const text = await response.text()
        errorMessage = text || `Backend returned status ${response.status}`
      }
      console.error(`Backend error (${response.status}):`, errorMessage)
      throw new Error(errorMessage)
    }

    const result = await response.json()
    console.log("Backend disease info successful")
    return NextResponse.json({ success: true, info: result })
  } catch (error: any) {
    console.error("Disease info handler error:", error)
    const message = error instanceof Error ? error.message : "Failed to fetch disease info"
    return NextResponse.json({ success: false, error: message }, { status: 500 })
  }
}
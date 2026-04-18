import { type NextRequest, NextResponse } from "next/server"

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000"

export async function POST(request: NextRequest) {
  try {
    console.log("Calling backend URL:", `${BACKEND_URL}/analyze-blood`)
    const contentType = request.headers.get("content-type") || ""
    
    if (contentType.includes("multipart/form-data")) {
      const formData = await request.formData()
      const file = formData.get("file") as File | null
      
      if (!file) {
        return NextResponse.json({ success: false, error: "PDF file is required" }, { status: 400 })
      }

      // Create a new FormData to send to the backend
      const backendFormData = new FormData()
      backendFormData.append("file", file)

      const response = await fetch(`${BACKEND_URL}/analyze-blood`, {
        method: "POST",
        body: backendFormData,
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || "Backend request failed")
      }

      const result = await response.json()
      return NextResponse.json({ success: true, info: result })
    } else {
      return NextResponse.json({ success: false, error: "Multipart form-data is required" }, { status: 400 })
    }
  } catch (error: any) {
    console.error("Blood analysis error:", error)
    const message = error instanceof Error ? error.message : "Failed to analyze labs"
    return NextResponse.json({ success: false, error: message }, { status: 500 })
  }
}
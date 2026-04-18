import { type NextRequest, NextResponse } from "next/server"

const BACKEND_URL = (process.env.BACKEND_URL || "http://localhost:8000").replace(/\/$/, "")

export async function POST(request: NextRequest) {
  console.log("Blood analysis request received at frontend API")
  try {
    const contentType = request.headers.get("content-type") || ""
    
    if (contentType.includes("multipart/form-data")) {
      const formData = await request.formData()
      const file = formData.get("file") as File | null
      
      if (!file) {
        console.error("No file provided in request")
        return NextResponse.json({ success: false, error: "PDF file is required" }, { status: 400 })
      }

      console.log(`Forwarding blood report to backend: ${BACKEND_URL}/analyze-blood`)
      
      // Create a new FormData to send to the backend
      const backendFormData = new FormData()
      backendFormData.append("file", file)

      const response = await fetch(`${BACKEND_URL}/analyze-blood`, {
        method: "POST",
        body: backendFormData,
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
      console.log("Backend analysis successful")
      return NextResponse.json({ success: true, info: result })
    } else {
      console.error("Invalid content type:", contentType)
      return NextResponse.json({ success: false, error: "Multipart form-data is required" }, { status: 400 })
    }
  } catch (error: any) {
    console.error("Blood analysis handler error:", error)
    const message = error instanceof Error ? error.message : "Failed to analyze labs"
    return NextResponse.json({ success: false, error: message }, { status: 500 })
  }
}
import { type NextRequest, NextResponse } from "next/server"

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000"

export async function POST(request: NextRequest) {
  try {
    const contentType = request.headers.get("content-type") || ""
    
    if (contentType.includes("multipart/form-data")) {
      const formData = await request.formData()
      const file = formData.get("file") as File | null
      
      if (!file) {
        return NextResponse.json({ success: false, error: "File is required" }, { status: 400 })
      }

      // Create a new FormData to send to the backend
      const backendFormData = new FormData()
      backendFormData.append("file", file)

      const response = await fetch(`${BACKEND_URL}/analyze-xray`, {
        method: "POST",
        body: backendFormData,
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || "Backend request failed")
      }

      const result = await response.json()
      
      let diseaseInfo = null
      if (result && result.likely_conditions && result.likely_conditions.length > 0) {
        const primaryCondition = result.likely_conditions[0]
        try {
          const diseaseResponse = await fetch(`${BACKEND_URL}/disease-info`, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify({ disease_name: primaryCondition }),
          })
          if (diseaseResponse.ok) {
            diseaseInfo = await diseaseResponse.json()
          }
        } catch (e) {
          console.error("Error fetching disease info:", e)
        }
      }
      
      return NextResponse.json({ success: true, info: { ...result, disease_info: diseaseInfo } })
    } else {
      return NextResponse.json({ success: false, error: "Multipart form-data is required" }, { status: 400 })
    }
  } catch (error: any) {
    console.error("X-ray analysis error:", error)
    const message = error instanceof Error ? error.message : "Failed to analyze X-ray"
    return NextResponse.json({ success: false, error: message }, { status: 500 })
  }
}

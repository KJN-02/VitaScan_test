import { type NextRequest, NextResponse } from "next/server"

const BACKEND_URL = (process.env.BACKEND_URL || "http://localhost:8000").replace(/\/$/, "")

export async function POST(request: NextRequest) {
  console.log("X-ray analysis request received at frontend API")
  try {
    const contentType = request.headers.get("content-type") || ""
    
    if (contentType.includes("multipart/form-data")) {
      const formData = await request.formData()
      const file = formData.get("file") as File | null
      
      if (!file) {
        console.error("No file provided in request")
        return NextResponse.json({ success: false, error: "File is required" }, { status: 400 })
      }

      console.log(`Forwarding X-ray to backend: ${BACKEND_URL}/analyze-xray`)
      
      // Create a new FormData to send to the backend
      const backendFormData = new FormData()
      backendFormData.append("file", file)

      const response = await fetch(`${BACKEND_URL}/analyze-xray`, {
        method: "POST",
        body: backendFormData,
      })

      if (!response.ok) {
        let errorMessage = "Backend request failed"
        try {
          const errorData = await response.json()
          errorMessage = errorData.detail || errorMessage
        } catch (e) {
          // If response is not JSON
          const text = await response.text()
          errorMessage = text || `Backend returned status ${response.status}`
        }
        console.error(`Backend error (${response.status}):`, errorMessage)
        throw new Error(errorMessage)
      }

      const result = await response.json()
      console.log("Backend analysis successful")
      
      let diseaseInfo = null
      if (result && result.likely_conditions && result.likely_conditions.length > 0) {
        const primaryCondition = result.likely_conditions[0]
        console.log(`Fetching extra info for condition: ${primaryCondition}`)
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
            console.log("Disease info fetched successfully")
          }
        } catch (e) {
          console.error("Error fetching disease info:", e)
        }
      }
      
      return NextResponse.json({ success: true, info: { ...result, disease_info: diseaseInfo } })
    } else {
      console.error("Invalid content type:", contentType)
      return NextResponse.json({ success: false, error: "Multipart form-data is required" }, { status: 400 })
    }
  } catch (error: any) {
    console.error("X-ray analysis handler error:", error)
    const message = error instanceof Error ? error.message : "Failed to analyze X-ray"
    return NextResponse.json({ success: false, error: message }, { status: 500 })
  }
}

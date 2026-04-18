import { type NextRequest, NextResponse } from "next/server"

const BACKEND_URL = (process.env.BACKEND_URL || "http://localhost:8000").replace(/\/$/, "")

export async function POST(request: NextRequest) {
  console.log("Prediction request received at frontend API")
  try {
    const body = await request.json()
    const { symptoms } = body

    if (!symptoms || !Array.isArray(symptoms) || symptoms.length === 0) {
      console.error("Invalid symptoms provided")
      return NextResponse.json({ success: false, error: "Symptoms array is required" }, { status: 400 })
    }

    console.log(`Forwarding prediction to backend: ${BACKEND_URL}/predict`)
    
    const response = await fetch(`${BACKEND_URL}/predict`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ symptoms }),
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

    const prediction = await response.json()
    console.log("Backend prediction successful")
    return NextResponse.json(prediction)
  } catch (error) {
    console.error("Prediction handler error:", error)
    return NextResponse.json({ 
      success: false, 
      error: error instanceof Error ? error.message : "Failed to process prediction" 
    }, { status: 500 })
  }
}

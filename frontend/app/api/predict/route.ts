import { type NextRequest, NextResponse } from "next/server"

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000"

export async function POST(request: NextRequest) {
  try {
    console.log("Calling backend URL:", `${BACKEND_URL}/predict`)
    const body = await request.json()
    const { symptoms } = body

    if (!symptoms || !Array.isArray(symptoms) || symptoms.length === 0) {
      return NextResponse.json({ success: false, error: "Symptoms array is required" }, { status: 400 })
    }

    const response = await fetch(`${BACKEND_URL}/predict`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ symptoms }),
    })

    if (!response.ok) {
      const errorData = await response.json()
      throw new Error(errorData.detail || "Backend request failed")
    }

    const prediction = await response.json()
    return NextResponse.json(prediction)
  } catch (error) {
    console.error("Prediction error:", error)
    return NextResponse.json({ 
      success: false, 
      error: error instanceof Error ? error.message : "Failed to process prediction" 
    }, { status: 500 })
  }
}

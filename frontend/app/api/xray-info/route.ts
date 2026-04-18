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
      if (msg.includes("No module named") || msg.includes("ModuleNotFoundError")) {
        continue
      }
      if (msg.includes("NVIDIA_API_KEY")) {
        return { error: "NVIDIA_API_KEY not configured", raw_output: msg }
      }
      if (e?.code === "ENOENT") {
        continue
      }
    }
  }
  const finalMsg = String(lastError?.message || lastError)
  if (finalMsg.includes("No module named") || finalMsg.includes("ModuleNotFoundError")) {
    return { error: "Python package missing: install requests and pillow", raw_output: finalMsg }
  }
  return { error: typeof lastError?.message === "string" ? lastError.message : "Python failed to run" }
}

async function callXrayInfo(payload: any): Promise<any> {
  const scriptPath = path.join(process.cwd(), "scripts", "xray_info.py")
  const pythonPath = "C:/Users/kakad/OneDrive/Desktop/1/2/venv/Scripts/python.exe"
  const argsJson = JSON.stringify(payload)

  async function runOnce(exe: string, args: string[]): Promise<string> {
    return new Promise((resolve, reject) => {
      const proc = spawn(exe, args, { env: { ...process.env } })
      let out = ""
      let err = ""
      proc.stdout.on("data", (d) => (out += d.toString()))
      proc.stderr.on("data", (d) => (err += d.toString()))
      proc.on("close", (code) => {
        if (code !== 0) {
          reject(new Error(err || `Python exited with code ${code}`))
        } else {
          resolve(out)
        }
      })
      proc.on("error", (e: any) => reject(e))
    })
  }

  const candidates = [
    { exe: pythonPath, args: [scriptPath, argsJson] },
    { exe: "python", args: [scriptPath, argsJson] },
    { exe: "py", args: ["-3", scriptPath, argsJson] },
    { exe: "python3", args: [scriptPath, argsJson] },
  ]

  let lastError: any = null
  for (const c of candidates) {
    try {
      const out = await runOnce(c.exe, c.args)
      const trimmed = out.trim()
      
      // Find the first '{' and the last '}' to extract the JSON object
      const startIdx = trimmed.indexOf('{')
      const endIdx = trimmed.lastIndexOf('}')
      
      if (startIdx === -1 || endIdx === -1) {
        throw new Error("No JSON object found in Python output")
      }
      
      const jsonStr = trimmed.substring(startIdx, endIdx + 1)
      const parsed = JSON.parse(jsonStr)
      return parsed
    } catch (e: any) {
      lastError = e
      const msg = String(e?.message || e)
      
      // If it's a module error, this interpreter is invalid, try the next one
      if (msg.includes("No module named") || msg.includes("ModuleNotFoundError")) {
        continue
      }
      
      if (msg.includes("NVIDIA_API_KEY")) {
        return { error: "NVIDIA_API_KEY not configured", raw_output: msg }
      }
      if (e?.code === "ENOENT") {
        continue
      }
    }
  }
  
  const finalMsg = String(lastError?.message || lastError)
  if (finalMsg.includes("No module named") || finalMsg.includes("ModuleNotFoundError")) {
    return { error: "Python package missing: install tensorflow and pandas and numpy and pillow", raw_output: finalMsg }
  }
  
  return { error: typeof lastError?.message === "string" ? lastError.message : "Python failed to run" }
}
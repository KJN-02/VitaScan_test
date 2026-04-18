"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Loader2, Download } from "lucide-react"
import { generateBloodAnalysisPDF } from "@/lib/pdf-generator"
import { useAuth } from "@/hooks/use-auth"

export default function BloodAnalysis() {
  const [file, setFile] = useState<File | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [result, setResult] = useState<any>(null)
  const [error, setError] = useState("")
  const { addScan, user } = useAuth()

  const analyze = async () => {
    if (!file) return
    setIsLoading(true)
    setError("")
    setResult(null)
    try {
      const form = new FormData()
      form.append("file", file)
      const res = await fetch("/api/blood-info", { method: "POST", body: form })
      const data = await res.json()
      if (data.success) {
        const info = data.info || {}
        const mapped = {
          irregularities: Array.isArray(info.irregularities)
            ? info.irregularities
            : Array.isArray(info.notable_abnormalities)
            ? info.notable_abnormalities
            : [],
          possible_diseases: Array.isArray(info.possible_diseases)
            ? info.possible_diseases
            : Array.isArray(info.possible_causes)
            ? info.possible_causes
            : [],
          irregularity_info: typeof info.irregularity_info === "string" && info.irregularity_info
            ? info.irregularity_info
            : typeof info.summary === "string"
            ? info.summary
            : "",
          causes_or_risk_factors: Array.isArray(info.causes_or_risk_factors)
            ? info.causes_or_risk_factors
            : Array.isArray(info.common_causes_or_risk_factors)
            ? info.common_causes_or_risk_factors
            : Array.isArray(info.risk_factors)
            ? info.risk_factors
            : [],
          precautions_and_prevention: Array.isArray(info.precautions_and_prevention)
            ? info.precautions_and_prevention
            : Array.isArray(info.precautions)
            ? info.precautions
            : Array.isArray(info.prevention)
            ? info.prevention
            : [],
          when_to_see_a_doctor:
            typeof info.when_to_see_a_doctor === "string" && info.when_to_see_a_doctor
              ? info.when_to_see_a_doctor
              : typeof info.when_to_seek_medical_care === "string"
              ? info.when_to_seek_medical_care
              : "",
        }
        setResult(mapped)
        
        // Auto-save to history if logged in
        if (user) {
            try {
                // Use irregularities as symptoms summary
                const summary = mapped.irregularities.length > 0 
                    ? mapped.irregularities 
                    : ["Blood Analysis"]
                
                await addScan(summary, "blood", mapped)
                console.log("Analysis saved to history")
            } catch (err) {
                console.error("Failed to save to history", err)
            }
        }

      } else {
        setError(data.error || "Analysis failed")
      }
    } catch (e) {
      setError("Failed to analyze labs")
    } finally {
      setIsLoading(false)
    }
  }

  const handleDownloadPDF = () => {
    if (!result) return
    generateBloodAnalysisPDF(result)
  }

  return (
    <div className="container max-w-4xl py-8 md:py-12">
      <div className="space-y-4 mb-8">
        <h1 className="text-3xl font-bold tracking-tighter md:text-4xl text-center">AI Blood Analysis</h1>
        <p className="text-muted-foreground md:text-xl text-center">Upload lab  to get AI guidance.</p>
      </div>

      <div className="bg-black text-white p-8 rounded-lg">
        <div className="grid gap-4 mb-6">
          <input
            type="file"
            accept=".pdf"
            onChange={(e) => setFile(e.target.files?.[0] || null)}
            className="text-white"
          />
          <p className="text-xs text-gray-400">Upload Lab(pdf). The AI will extract key values and interpret them.</p>
        </div>

        <Button className="w-full mb-6 bg-primary hover:bg-primary/90" onClick={analyze} disabled={isLoading || !file}>
          {isLoading ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Analyzing...
            </>
          ) : (
            "Analyze Labs"
          )}
        </Button>

        <Card className="bg-transparent border-white">
          <CardContent className="p-6 min-h-[200px]">
            {isLoading ? (
              <div className="flex flex-col items-center gap-2">
                <Loader2 className="h-8 w-8 animate-spin text-white" />
                <p>Analyzing labs with AI...</p>
              </div>
            ) : result ? (
              <div className="space-y-4">
                <div className="flex justify-between items-center">
                  <h3 className="text-xl font-semibold text-white">AI Results</h3>
                  <Button variant="outline" size="sm" onClick={handleDownloadPDF} className="bg-transparent border-white text-white hover:bg-white hover:text-black">
                    <Download className="mr-2 h-4 w-4" />
                    Download PDF
                  </Button>
                </div>
                {result.irregularity_info && <p className="text-sm text-gray-200">{result.irregularity_info}</p>}
                {Array.isArray(result.irregularities) && result.irregularities.length > 0 && (
                  <div>
                    <p className="text-sm font-medium text-white">Irregularities</p>
                    <ul className="text-sm text-gray-300 list-disc ml-5">
                      {result.irregularities.map((s: string, i: number) => (
                        <li key={i}>{s}</li>
                      ))}
                    </ul>
                  </div>
                )}
                {Array.isArray(result.possible_diseases) && result.possible_diseases.length > 0 && (
                  <div>
                    <p className="text-sm font-medium text-white">Possible Diseases</p>
                    <ul className="text-sm text-gray-300 list-disc ml-5">
                      {result.possible_diseases.map((s: string, i: number) => (
                        <li key={i}>{s}</li>
                      ))}
                    </ul>
                  </div>
                )}
                {Array.isArray(result.causes_or_risk_factors) && result.causes_or_risk_factors.length > 0 && (
                  <div>
                    <p className="text-sm font-medium text-white">Causes / Risk Factors</p>
                    <ul className="text-sm text-gray-300 list-disc ml-5">
                      {result.causes_or_risk_factors.map((s: string, i: number) => (
                        <li key={i}>{s}</li>
                      ))}
                    </ul>
                  </div>
                )}
                {Array.isArray(result.precautions_and_prevention) && result.precautions_and_prevention.length > 0 && (
                  <div>
                    <p className="text-sm font-medium text-white">Precautions & Prevention</p>
                    <ul className="text-sm text-gray-300 list-disc ml-5">
                      {result.precautions_and_prevention.map((s: string, i: number) => (
                        <li key={i}>{s}</li>
                      ))}
                    </ul>
                  </div>
                )}
                {result.when_to_see_a_doctor && (
                  <div>
                    <p className="text-sm font-medium text-white">When to See a Doctor</p>
                    <p className="text-sm text-gray-300">{result.when_to_see_a_doctor}</p>
                  </div>
                )}
              </div>
            ) : error ? (
              <div className="text-center text-red-400">
                <p>Analysis Error: {error}</p>
              </div>
            ) : (
              <p className="text-gray-400 text-center">Upload labs and click "Analyze Labs"</p>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

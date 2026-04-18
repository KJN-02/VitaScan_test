"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Loader2, Download, AlertCircle, Info, Stethoscope, ShieldAlert } from "lucide-react"
import { useAuth } from "@/hooks/use-auth"
import { generateXRayPDF } from "@/lib/pdf-generator"
import { Badge } from "@/components/ui/badge"

export default function XrayAnalysis() {
  const [file, setFile] = useState<File | null>(null)
  const [studyType] = useState("X-ray")
  const [isLoading, setIsLoading] = useState(false)
  const [result, setResult] = useState<any>(null)
  const [error, setError] = useState("")
  const { user, addScan } = useAuth()

  const analyze = async () => {
    if (!file) return
    setIsLoading(true)
    setError("")
    setResult(null)
    try {
      const form = new FormData()
      form.append("file", file)
      form.append("study_type", studyType)
      const res = await fetch("/api/xray-info", { method: "POST", body: form })
      const data = await res.json()
      if (data.success) {
        setResult(data.info)
        
        // Save to history
        if (user) {
          try {
            await addScan([], "x-ray", data.info)
            console.log("X-ray analysis saved to history")
          } catch (err) {
            console.error("Failed to save to history", err)
          }
        }
      } else {
        setError(data.error || "Analysis failed")
      }
    } catch (e) {
      setError("Failed to analyze image")
    } finally {
      setIsLoading(false)
    }
  }

  const handleDownloadPDF = () => {
    if (result) {
      generateXRayPDF(result)
    }
  }

  return (
    <div className="container max-w-4xl py-8 md:py-12">
      <div className="space-y-4 mb-8">
        <h1 className="text-3xl font-bold tracking-tighter md:text-4xl text-center">AI X-ray Analysis</h1>
        <p className="text-muted-foreground md:text-xl text-center">Upload an X-ray and get AI findings.</p>
      </div>

      <div className="bg-black text-white p-8 rounded-lg">
        <div className="grid gap-4 mb-6">
          <input
            type="file"
            accept=".jpg,.jpeg,.png,.pdf"
            onChange={(e) => setFile(e.target.files?.[0] || null)}
            className="text-white"
          />
          <p className="text-xs text-gray-400">Upload a X-ray (jpg, jpeg, png or pdf). The AI will extract key values and interpret them.</p>
        </div>

        <Button className="w-full mb-6 bg-primary hover:bg-primary/90" onClick={analyze} disabled={isLoading || !file}>
          {isLoading ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Analyzing...
            </>
          ) : (
            "Analyze X-ray"
          )}
        </Button>

        <Card className="bg-transparent border-white">
          <CardContent className="p-6 min-h-[200px]">
            {isLoading ? (
              <div className="flex flex-col items-center gap-2">
                <Loader2 className="h-8 w-8 animate-spin text-white" />
                <p>Analyzing image with AI...</p>
              </div>
            ) : result ? (
              <div className="space-y-6">
                <div className="text-center">
                  <h3 className="text-xl font-semibold text-white mb-2">AI Results</h3>
                  <Button 
                    variant="outline" 
                    size="sm" 
                    onClick={handleDownloadPDF} 
                    className="mb-4 bg-transparent border-white text-white hover:bg-white hover:text-black"
                  >
                    <Download className="mr-2 h-4 w-4" />
                    Download PDF
                  </Button>
                  <div className="bg-primary/20 rounded-lg p-4 mb-4">
                    <p className="text-lg font-medium text-white">{result.study_type || studyType}</p>
                    {result.urgency && (
                      <Badge variant={result.urgency === "High" ? "destructive" : "secondary"} className="mt-2">
                        Urgency: {result.urgency}
                      </Badge>
                    )}
                  </div>
                </div>

                {result.top_finding && result.top_finding.details && (
                  <div className="space-y-4 bg-white/5 p-6 rounded-xl border border-white/10">
                    <div className="flex items-center gap-2 text-primary border-b border-white/10 pb-2 mb-4">
                      <AlertCircle className="h-5 w-5" />
                      <h4 className="text-lg font-bold uppercase tracking-wider">Top Finding: {result.top_finding.name}</h4>
                      <Badge variant="outline" className="ml-auto text-primary border-primary">
                        {result.top_finding.probability} Confidence
                      </Badge>
                    </div>
                    
                    <div className="space-y-4">
                      <div className="space-y-1">
                        <div className="flex items-center gap-2 text-sm font-semibold text-primary/80">
                          <Info className="h-4 w-4" />
                          <span>Description</span>
                        </div>
                        <p className="text-sm text-gray-200 leading-relaxed">
                          {result.top_finding.details.short_description}
                        </p>
                      </div>

                      <div className="grid md:grid-cols-2 gap-4">
                        <div className="space-y-2">
                          <div className="flex items-center gap-2 text-sm font-semibold text-primary/80">
                            <Stethoscope className="h-4 w-4" />
                            <span>Common Symptoms</span>
                          </div>
                          <ul className="text-xs text-gray-300 space-y-1 list-disc ml-4">
                            {result.top_finding.details.common_symptoms?.map((s: string, i: number) => (
                              <li key={i}>{s}</li>
                            ))}
                          </ul>
                        </div>
                        <div className="space-y-2">
                          <div className="flex items-center gap-2 text-sm font-semibold text-primary/80">
                            <ShieldAlert className="h-4 w-4" />
                            <span>Causes & Risks</span>
                          </div>
                          <ul className="text-xs text-gray-300 space-y-1 list-disc ml-4">
                            {result.top_finding.details.common_causes_or_risk_factors?.map((s: string, i: number) => (
                              <li key={i}>{s}</li>
                            ))}
                          </ul>
                        </div>
                      </div>

                      <div className="space-y-2 pt-2 border-t border-white/10">
                        <div className="flex items-center gap-2 text-sm font-semibold text-green-400">
                          <ShieldAlert className="h-4 w-4" />
                          <span>Precautions & Prevention</span>
                        </div>
                        <ul className="text-xs text-gray-300 grid grid-cols-1 md:grid-cols-2 gap-x-4 gap-y-1 list-disc ml-4">
                          {result.top_finding.details.precautions_and_prevention?.map((s: string, i: number) => (
                            <li key={i}>{s}</li>
                          ))}
                        </ul>
                      </div>

                      <div className="bg-blue-500/10 border border-blue-500/20 p-3 rounded-lg">
                        <div className="flex justify-between items-start mb-1">
                          <p className="text-xs font-bold text-blue-400 uppercase">When to see a doctor</p>
                          {result.top_finding.details.confidence && (
                            <Badge variant="outline" className="text-[10px] h-4 text-blue-300 border-blue-500/30 px-1">
                              AI Confidence: {result.top_finding.details.confidence}
                            </Badge>
                          )}
                        </div>
                        <p className="text-xs text-blue-100">{result.top_finding.details.when_to_see_a_doctor}</p>
                      </div>
                    </div>
                  </div>
                )}

                {result.disease_info && !result.disease_info.error && (
                  <div className="space-y-4 bg-white/5 p-6 rounded-xl border border-white/10">
                    <div className="flex items-center gap-2 text-primary border-b border-white/10 pb-2 mb-4">
                      <Info className="h-5 w-5" />
                      <h4 className="text-lg font-bold uppercase tracking-wider">Disease Information: {result.disease_info.disease}</h4>
                      {result.disease_info.confidence && (
                        <Badge variant="outline" className="ml-auto text-primary border-primary">
                          AI Confidence: {result.disease_info.confidence}
                        </Badge>
                      )}
                    </div>
                    
                    <div className="space-y-4">
                      <div className="space-y-1">
                        <div className="flex items-center gap-2 text-sm font-semibold text-primary/80">
                          <Info className="h-4 w-4" />
                          <span>Description</span>
                        </div>
                        <p className="text-sm text-gray-200 leading-relaxed">
                          {result.disease_info.short_description}
                        </p>
                      </div>

                      <div className="grid md:grid-cols-2 gap-4">
                        <div className="space-y-2">
                          <div className="flex items-center gap-2 text-sm font-semibold text-primary/80">
                            <Stethoscope className="h-4 w-4" />
                            <span>Common Symptoms</span>
                          </div>
                          <ul className="text-xs text-gray-300 space-y-1 list-disc ml-4">
                            {result.disease_info.common_symptoms?.map((s: string, i: number) => (
                              <li key={i}>{s}</li>
                            ))}
                          </ul>
                        </div>
                        <div className="space-y-2">
                          <div className="flex items-center gap-2 text-sm font-semibold text-primary/80">
                            <ShieldAlert className="h-4 w-4" />
                            <span>Causes & Risks</span>
                          </div>
                          <ul className="text-xs text-gray-300 space-y-1 list-disc ml-4">
                            {result.disease_info.common_causes_or_risk_factors?.map((s: string, i: number) => (
                              <li key={i}>{s}</li>
                            ))}
                          </ul>
                        </div>
                      </div>

                      <div className="space-y-2 pt-2 border-t border-white/10">
                        <div className="flex items-center gap-2 text-sm font-semibold text-green-400">
                          <ShieldAlert className="h-4 w-4" />
                          <span>Precautions & Prevention</span>
                        </div>
                        <ul className="text-xs text-gray-300 grid grid-cols-1 md:grid-cols-2 gap-x-4 gap-y-1 list-disc ml-4">
                          {result.disease_info.precautions_and_prevention?.map((s: string, i: number) => (
                            <li key={i}>{s}</li>
                          ))}
                        </ul>
                      </div>

                      <div className="bg-blue-500/10 border border-blue-500/20 p-3 rounded-lg">
                        <div className="flex justify-between items-start mb-1">
                          <p className="text-xs font-bold text-blue-400 uppercase">When to see a doctor</p>
                          {result.disease_info.confidence && (
                            <Badge variant="outline" className="text-[10px] h-4 text-blue-300 border-blue-500/30 px-1">
                              AI Confidence: {result.disease_info.confidence}
                            </Badge>
                          )}
                        </div>
                        <p className="text-xs text-blue-100">{result.disease_info.when_to_see_a_doctor}</p>
                      </div>
                    </div>
                  </div>
                )}

                {result.disease_info && result.disease_info.error && (
                  <div className="text-center text-red-400">
                    <p>Error fetching disease information: {result.disease_info.error}</p>
                  </div>
                )}

                <div className="grid md:grid-cols-2 gap-6">
                  {Array.isArray(result.other_possibilities) && result.other_possibilities.length > 0 && (
                    <div className="bg-white/5 p-4 rounded-lg">
                      <p className="text-sm font-medium text-white mb-2 border-b border-white/10 pb-1">Other Possibilities (&gt;20%)</p>
                      <ul className="text-sm text-gray-300 list-disc ml-5 space-y-1">
                        {result.other_possibilities.map((s: string, i: number) => (
                          <li key={i}>{s}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {Array.isArray(result.recommendations) && result.recommendations.length > 0 && (
                    <div className="bg-white/5 p-4 rounded-lg">
                      <p className="text-sm font-medium text-white mb-2 border-b border-white/10 pb-1">Recommendations</p>
                      <ul className="text-sm text-gray-300 list-disc ml-5 space-y-1">
                        {result.recommendations.map((s: string, i: number) => (
                          <li key={i}>{s}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>

                {result.summary && (
                  <div className="bg-muted/10 p-4 rounded-lg italic text-gray-400 text-xs text-center border border-white/5">
                    {result.summary}
                  </div>
                )}
              </div>
            ) : error ? (
              <div className="text-center text-red-400">
                <p>Analysis Error: {error}</p>
              </div>
            ) : (
              <p className="text-gray-400 text-center">Upload X-ray and click "Analyze X-ray"</p>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
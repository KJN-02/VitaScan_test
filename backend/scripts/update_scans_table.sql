-- Add new columns to scans table for supporting different analysis types and storing results
ALTER TABLE public.scans 
ADD COLUMN IF NOT EXISTS type TEXT DEFAULT 'symptom',
ADD COLUMN IF NOT EXISTS result JSONB DEFAULT '{}'::jsonb;

-- Comment on columns
COMMENT ON COLUMN public.scans.type IS 'Type of scan: symptom, blood, or xray';
COMMENT ON COLUMN public.scans.result IS 'Structured result of the analysis';

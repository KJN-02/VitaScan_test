import { createClient } from "@supabase/supabase-js"

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || ""
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || ""

// Only create the client if we have the credentials, otherwise return a proxy or handle it gracefully
// This prevents build errors on Vercel if environment variables are not provided at build time
export const supabase = (supabaseUrl && supabaseAnonKey) 
  ? createClient(supabaseUrl, supabaseAnonKey)
  : (null as any) // Fallback for build time

export type Database = {
  public: {
    Tables: {
      profiles: {
        Row: {
          id: string
          email: string | null
          name: string | null
          created_at: string
          updated_at: string
        }
        Insert: {
          id: string
          email?: string | null
          name?: string | null
          created_at?: string
          updated_at?: string
        }
        Update: {
          id?: string
          email?: string | null
          name?: string | null
          created_at?: string
          updated_at?: string
        }
      }
      scans: {
        Row: {
          id: string
          user_id: string | null
          symptoms: string[]
          date: string
          created_at: string
          type: string
          result: any
        }
        Insert: {
          id?: string
          user_id?: string | null
          symptoms?: string[]
          date: string
          created_at?: string
          type?: string
          result?: any
        }
        Update: {
          id?: string
          user_id?: string | null
          symptoms?: string[]
          date?: string
          created_at?: string
          type?: string
          result?: any
        }
      }
      shared_scans: {
        Row: {
          id: string
          scan_id: string | null
          user_name: string
          symptoms: string[]
          date: string
          created_at: string
          expires_at: string | null
        }
        Insert: {
          id: string
          scan_id?: string | null
          user_name: string
          symptoms: string[]
          date: string
          created_at?: string
          expires_at?: string | null
        }
        Update: {
          id?: string
          scan_id?: string | null
          user_name?: string
          symptoms?: string[]
          date?: string
          created_at?: string
          expires_at?: string | null
        }
      }
    }
  }
}

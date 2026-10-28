// Mirrors the Pydantic schemas in backend/app/schemas/analysis.py.
// If you change the backend schema, update these types too.

export type CEFRLevel = "A1" | "A2" | "B1" | "B2" | "C1" | "C2";

export interface GrammarPoint {
  phrase: string;
  concept: string;
  explanation: string;
  level: CEFRLevel;
}

export interface VocabularyItem {
  french: string;
  english: string;
  level: CEFRLevel;
}

export interface AnalysisResult {
  translation: string;
  grammar_points: GrammarPoint[];
  vocabulary: VocabularyItem[];
}

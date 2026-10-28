"use client";
// "use client" = this component runs in the browser, so it can use state and handle clicks.

import { useState, type FormEvent } from "react";

import { AnalysisResultView } from "@/components/AnalysisResultView";
import { analyzePassage, ApiError } from "@/lib/api";
import type { AnalysisResult } from "@/lib/types";

// Keep in sync with MAX_INPUT_CHARS in backend/app/schemas/analysis.py.
// The backend enforces the limit; this just gives faster feedback.
const MAX_CHARS = 2000;

export default function HomePage() {
  const [text, setText] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AnalysisResult | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); // stop the browser's default full-page form submission

    if (!text.trim()) {
      setError("Please enter an English passage.");
      return;
    }

    setIsLoading(true);
    setError(null);
    setResult(null);
    try {
      setResult(await analyzePassage(text));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong. Please try again.");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <main>
      <h1>ApprendreAI</h1>
      <p className="muted">Translate English into French and learn the grammar and vocabulary behind it.</p>

      <form onSubmit={handleSubmit}>
        <label htmlFor="passage">Enter an English passage</label>
        <textarea
          id="passage"
          rows={5}
          maxLength={MAX_CHARS}
          value={text}
          onChange={(event) => setText(event.target.value)}
          placeholder="I recently started learning French because I hope to visit France next summer."
          disabled={isLoading}
        />
        <div className="form-footer">
          <span className="muted">
            {text.length}/{MAX_CHARS}
          </span>
          <button type="submit" disabled={isLoading}>
            {isLoading ? "Analyzing…" : "Analyze"}
          </button>
        </div>
      </form>

      {isLoading && <p className="status">Analyzing your passage. This usually takes a few seconds…</p>}
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      {result && <AnalysisResultView result={result} />}
    </main>
  );
}

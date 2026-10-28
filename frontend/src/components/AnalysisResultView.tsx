import type { AnalysisResult } from "@/lib/types";

export function AnalysisResultView({ result }: { result: AnalysisResult }) {
  return (
    <div className="results">
      <section>
        <h2>French Translation</h2>
        <p className="translation" lang="fr">
          {result.translation}
        </p>
      </section>

      <section>
        <h2>Grammar</h2>
        {result.grammar_points.length === 0 ? (
          <p className="muted">No grammar points returned.</p>
        ) : (
          <ul className="cards">
            {result.grammar_points.map((point, index) => (
              <li key={index} className="card">
                <div className="card-header">
                  <span className="phrase" lang="fr">
                    {point.phrase}
                  </span>
                  <span className="level">{point.level}</span>
                </div>
                <p>
                  <strong>Concept:</strong> {point.concept}
                </p>
                <p>{point.explanation}</p>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section>
        <h2>Vocabulary</h2>
        {result.vocabulary.length === 0 ? (
          <p className="muted">No vocabulary returned.</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>French</th>
                <th>English</th>
                <th>Level</th>
              </tr>
            </thead>
            <tbody>
              {result.vocabulary.map((item, index) => (
                <tr key={index}>
                  <td lang="fr">{item.french}</td>
                  <td>{item.english}</td>
                  <td>
                    <span className="level">{item.level}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}

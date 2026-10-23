import React, { useState } from "react";
import { apiFetch } from "../api";

// Minimal Markdown support for LLM answers: **bold**, *italic*, "#" headings, "*" bullets, "---" dividers.
function renderInline(text) {
  return text.split(/(\*\*[^*]+\*\*)/g).map((part, i) =>
    part.startsWith("**") && part.endsWith("**")
      ? <strong key={i}>{part.slice(2, -2)}</strong>
      : part.replace(/\*([^*\s][^*]*)\*/g, "$1")
  );
}

function FormattedText({ text }) {
  return text.split("\n").map((line, i) => {
    if (/^\s*-{3,}\s*$/.test(line)) return <hr key={i} />;
    const heading = line.match(/^#{1,6}\s+(.*)/);
    const cleaned = heading ? `**${heading[1]}**` : line.replace(/^(\s*)\* /, "$1• ");
    return <React.Fragment key={i}>{renderInline(cleaned)}{"\n"}</React.Fragment>;
  });
}

const EXAMPLES = [
  "Which shipments are high risk right now and what should we do?",
  "What should we do about SHP2?",
  "Electronics got wet in the truck, what is the procedure?",
  "Who must be notified for a high risk shipment?",
];

function Assistant({ onAuthError }) {
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);

  const ask = async (text) => {
    const q = text.trim();
    if (!q || loading) return;
    setQuestion("");
    setMessages((m) => [...m, { role: "user", text: q }]);
    setLoading(true);
    try {
      const data = await apiFetch("/api/assistant", { method: "POST", body: { question: q } });
      setMessages((m) => [...m, { role: "assistant", text: data.answer, sources: data.sources, mode: data.mode }]);
    } catch (err) {
      if (err.status === 401) return onAuthError();
      setMessages((m) => [...m, { role: "assistant", text: err.message, error: true }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <h2>🤖 Ops Copilot</h2>
      <p className="muted">
        Answers questions using live shipment data and the company SOPs (retrieval-augmented generation).
      </p>

      {messages.length === 0 && (
        <div className="examples">
          {EXAMPLES.map((e) => (
            <button key={e} className="example" onClick={() => ask(e)}>{e}</button>
          ))}
        </div>
      )}

      <div className="chat">
        {messages.map((m, i) => (
          <div key={i} className={`message ${m.role} ${m.error ? "error" : ""}`}>
            <div className="message-text"><FormattedText text={m.text} /></div>
            {m.sources?.length > 0 && (
              <div className="sources">
                <b>Sources:</b>
                {m.sources.map((s) => (
                  <span key={s.file + s.title} className="source" title={`similarity ${s.score}`}>
                    {s.document} › {s.title}
                  </span>
                ))}
                {m.mode === "retrieval-only" && <small className="muted"> (LLM not configured: showing retrieved context)</small>}
              </div>
            )}
          </div>
        ))}
        {loading && <div className="message assistant muted">Thinking...</div>}
      </div>

      <form className="chat-input" onSubmit={(e) => { e.preventDefault(); ask(question); }}>
        <input placeholder="Ask about shipments or procedures..." value={question}
          onChange={(e) => setQuestion(e.target.value)} maxLength={500} />
        <button className="btn" type="submit" disabled={loading}>Ask</button>
      </form>
    </div>
  );
}

export default Assistant;

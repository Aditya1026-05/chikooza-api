import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import axios from "axios";
import { Button } from "reactstrap";
import { apiPath, getAuthConfig, handleUnauthorized } from "../../Constants";
import "./styles.css";

const getAiApiUrl = () => {
  const baseUrl = apiPath || "/";
  return `${baseUrl.replace(/\/?$/, "/")}ai/`;
};

const examples = [
  "What are my total sales?",
  "What is my profit or loss?",
  "How many birds are current?",
  "What is my average FCR?",
];

const initialMessages = [
  {
    id: "intro",
    sender: "bot",
    text: "Ask me about your own Chikooza farm data: sales, purchases, profit/loss, birds, mortality, feed, weight, or FCR. I only use the data linked to your logged-in account.",
  },
];

const FarmerAiChatbot = () => {
  const navigate = useNavigate();
  const [messages, setMessages] = useState(initialMessages);
  const [draft, setDraft] = useState("");
  const [isSending, setIsSending] = useState(false);
  const hasToken = localStorage.getItem("token") !== null;

  const askQuestion = async (question) => {
    const cleanQuestion = question.trim();
    if (!cleanQuestion || isSending) {
      return;
    }

    const userMessage = {
      id: `user-${Date.now()}`,
      sender: "user",
      text: cleanQuestion,
    };
    const loadingId = `loading-${Date.now()}`;

    setDraft("");
    setIsSending(true);
    setMessages((prev) => [
      ...prev,
      userMessage,
      { id: loadingId, sender: "bot", text: "Checking your farm data..." },
    ]);

    try {
      const response = await axios.post(
        getAiApiUrl(),
        { query: cleanQuestion },
        getAuthConfig()
      );
      const answer =
        response.data?.answer ||
        response.data?.message ||
        "I found the data, but the response did not include a readable answer.";
      const meta = response.data?.route ? `Route: ${response.data.route}` : "";

      setMessages((prev) =>
        prev.map((message) =>
          message.id === loadingId
            ? { ...message, text: answer, meta, status: "success" }
            : message
        )
      );
    } catch (err) {
      if (handleUnauthorized(err, navigate)) {
        return;
      }

      const apiError =
        err?.response?.data?.error ||
        err?.response?.data?.details ||
        "I could not answer that safely. Try asking about sales, purchases, profit, birds, mortality, feed, weight, or FCR.";

      setMessages((prev) =>
        prev.map((message) =>
          message.id === loadingId
            ? { ...message, text: apiError, status: "error" }
            : message
        )
      );
    } finally {
      setIsSending(false);
    }
  };

  const handleSubmit = (event) => {
    event.preventDefault();
    askQuestion(draft);
  };

  if (!hasToken) {
    return (
      <section className="farmer-ai-page">
        <div className="farmer-ai-empty">
          <span className="farmer-ai-kicker">Private farmer assistant</span>
          <h1>Login required</h1>
          <p>
            This assistant answers questions from your own farm data only. Login
            first so Chikooza can apply user-level data isolation.
          </p>
          <Link to="/login" className="farmer-ai-login-link">
            Go to farmer login
          </Link>
        </div>
      </section>
    );
  }

  return (
    <section className="farmer-ai-page">
      <div className="farmer-ai-shell">
        <aside className="farmer-ai-panel">
          <span className="farmer-ai-kicker">Authenticated AI</span>
          <h1>Ask questions about your farm data.</h1>
          <p>
            The private assistant calls the backend `/ai/` endpoint with your
            bearer token. The backend builds read-only SQL and validates it
            against your authenticated user before execution.
          </p>
          <div className="farmer-ai-guardrail">
            <strong>Data isolation</strong>
            <span>
              It should never answer from another farmer&apos;s records. If a
              question asks for another user, the backend blocks it.
            </span>
          </div>
        </aside>

        <div className="farmer-ai-chat">
          <div className="farmer-ai-chat-header">
            <div>
              <span>Chikooza Farmer AI</span>
              <strong>Private data assistant</strong>
            </div>
            <span className="farmer-ai-status">Tenant scoped</span>
          </div>

          <div className="farmer-ai-messages" aria-live="polite">
            {messages.map((message) => (
              <div
                key={message.id}
                className={`farmer-ai-message farmer-ai-message-${message.sender}`}
              >
                <p>{message.text}</p>
                {message.meta && <small>{message.meta}</small>}
              </div>
            ))}
          </div>

          <div className="farmer-ai-examples" aria-label="Example questions">
            {examples.map((example) => (
              <button
                key={example}
                type="button"
                onClick={() => askQuestion(example)}
                disabled={isSending}
              >
                {example}
              </button>
            ))}
          </div>

          <form className="farmer-ai-form" onSubmit={handleSubmit}>
            <label htmlFor="farmer-ai-question">Ask from your farm data</label>
            <div>
              <textarea
                id="farmer-ai-question"
                value={draft}
                onChange={(event) => setDraft(event.target.value)}
                placeholder="Example: What is my total feed consumed?"
                rows={2}
              />
              <Button type="submit" disabled={isSending || !draft.trim()}>
                {isSending ? "Asking..." : "Ask AI"}
              </Button>
            </div>
          </form>
        </div>
      </div>
    </section>
  );
};

export default FarmerAiChatbot;

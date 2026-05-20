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
  "Total sales",
  "Profit or loss",
  "Current birds",
  "Average FCR",
];

const initialMessages = [
  {
    id: "intro",
    sender: "bot",
    text: "Ask a question about your farm records.",
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

      setMessages((prev) =>
        prev.map((message) =>
          message.id === loadingId
            ? { ...message, text: answer, status: "success" }
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
        "I could not answer that. Try asking about sales, purchases, birds, mortality, feed, weight, or FCR.";

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
            Login first to ask questions about your farm records.
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
      <div className="farmer-ai-shell farmer-ai-shell-simple">
        {/* U: OLD: Farmer AI showed backend/SQL/token guardrail details to farmers.
            U: NEW: keep the UI farmer-facing and leave technical details in docs/code. */}
        <div className="farmer-ai-chat">
          <div className="farmer-ai-chat-header">
            <div>
              <span>Farmer AI</span>
              <strong>Ask about your farm records</strong>
            </div>
          </div>

          <div className="farmer-ai-messages" aria-live="polite">
            {messages.map((message) => (
              <div
                key={message.id}
                className={`farmer-ai-message farmer-ai-message-${message.sender}`}
              >
                <p>{message.text}</p>
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
            <label htmlFor="farmer-ai-question">Ask a question</label>
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

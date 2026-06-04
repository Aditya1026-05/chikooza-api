import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import axios from "axios";
import { Button } from "reactstrap";
import { apiPath, getAuthConfig, handleUnauthorized } from "../../Constants";
import "./styles.css";

const getAiApiUrl = () => {
  const baseUrl = apiPath || "/";
  return `${baseUrl.replace(/\/?$/, "/")}ai/`;
};

const initialMessages = [
  {
    id: "intro",
    sender: "bot",
    text: "Ask me about your farms, flocks, sales, purchases, daily data, mortality, feed, weight, FCR, or profit.",
  },
];

const quickPrompts = [
  "Show my farm summary",
  "Show all flocks",
  "Profit or loss",
  "Daily data for active flock",
];

const formatInlineText = (text) => {
  const separatorIndex = text.indexOf(":");
  if (separatorIndex > 0 && separatorIndex < 42) {
    return (
      <>
        <strong>{text.slice(0, separatorIndex + 1)}</strong>
        {text.slice(separatorIndex + 1)}
      </>
    );
  }

  return text;
};

const renderFormattedMessage = (text) => {
  const lines = String(text || "")
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);

  if (lines.length === 0) {
    return <p>No response available.</p>;
  }

  const blocks = [];
  let listItems = [];

  const flushList = () => {
    if (listItems.length === 0) {
      return;
    }

    blocks.push(
      <ul className="farmer-ai-response-list" key={`list-${blocks.length}`}>
        {listItems.map((item, index) => (
          <li key={`${item}-${index}`}>{formatInlineText(item)}</li>
        ))}
      </ul>
    );
    listItems = [];
  };

  lines.forEach((line) => {
    const bulletMatch = line.match(/^[-•]\s+(.*)$/);
    const numberedMatch = line.match(/^\d+\.\s+(.*)$/);

    if (bulletMatch || numberedMatch) {
      listItems.push((bulletMatch || numberedMatch)[1]);
      return;
    }

    flushList();

    if (/^[A-Za-z][A-Za-z\s/-]{2,45}:$/.test(line)) {
      blocks.push(
        <h3 className="farmer-ai-response-heading" key={`heading-${blocks.length}`}>
          {line.replace(/:$/, "")}
        </h3>
      );
      return;
    }

    blocks.push(
      <p key={`paragraph-${blocks.length}`}>{formatInlineText(line)}</p>
    );
  });

  flushList();

  return <>{blocks}</>;
};

const FarmerAiChatbot = () => {
  const navigate = useNavigate();
  const [messages, setMessages] = useState(initialMessages);
  const [draft, setDraft] = useState("");
  const [isSending, setIsSending] = useState(false);
  const messagesPanelRef = useRef(null);
  const hasToken = localStorage.getItem("token") !== null;

  useEffect(() => {
    const panel = messagesPanelRef.current;
    if (!panel) {
      return;
    }

    window.requestAnimationFrame(() => {
      panel.scrollTo({ top: panel.scrollHeight, behavior: "smooth" });
    });
  }, [messages]);

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
      { id: loadingId, sender: "bot", text: "Checking your farm data...", status: "loading" },
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
      const suggestion = err?.response?.data?.suggestion;

      setMessages((prev) =>
        prev.map((message) =>
          message.id === loadingId
            ? {
                ...message,
                text: suggestion ? `${apiError}\n\nTry this: ${suggestion}` : apiError,
                status: "error",
              }
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

  const handleComposerKeyDown = (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      askQuestion(draft);
    }
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
              <span>Private farm workspace</span>
              <strong>AI Assistant</strong>
              <p>Ask questions from your saved farm records.</p>
            </div>
          </div>

          <div className="farmer-ai-messages" aria-live="polite" ref={messagesPanelRef}>
            {messages.map((message) => (
              <div
                key={message.id}
                className={`farmer-ai-message-row farmer-ai-message-row-${message.sender}`}
              >
                <div className="farmer-ai-avatar" aria-hidden="true">
                  {message.sender === "user" ? "U" : "AI"}
                </div>
                <div
                  className={`farmer-ai-message farmer-ai-message-${message.sender} ${message.status ? `farmer-ai-message-${message.status}` : ""}`}
                >
                  {message.status === "loading" ? (
                    <div className="farmer-ai-typing">
                      <span />
                      <span />
                      <span />
                      <strong>{message.text}</strong>
                    </div>
                  ) : (
                    <div className="farmer-ai-response">
                      {message.sender === "bot" ? renderFormattedMessage(message.text) : <p>{message.text}</p>}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>

          <form className="farmer-ai-form" onSubmit={handleSubmit}>
            <div className="farmer-ai-suggestions" aria-label="Suggested questions">
              {quickPrompts.map((prompt) => (
                <button
                  key={prompt}
                  type="button"
                  onClick={() => askQuestion(prompt)}
                  disabled={isSending}
                >
                  {prompt}
                </button>
              ))}
            </div>
            <div className="farmer-ai-composer">
              <textarea
                id="farmer-ai-question"
                value={draft}
                onChange={(event) => setDraft(event.target.value)}
                onKeyDown={handleComposerKeyDown}
                placeholder="Ask about your farm records..."
                rows={2}
              />
              <Button type="submit" disabled={isSending || !draft.trim()}>
                {isSending ? "Thinking..." : "Send"}
              </Button>
            </div>
          </form>
        </div>
      </div>
    </section>
  );
};

export default FarmerAiChatbot;

import React, { useLayoutEffect, useRef, useState } from 'react';
import PropTypes from 'prop-types';
import { apiPath } from '../../Constants';
import ChikbotLogo from '../../assets/images/poultry/chikbot-logo.png';
import './styles.css';

const INITIAL_MESSAGE = {
  id: 'initial',
  role: 'bot',
  text: 'Hi, I am Chikbot. Ask me about Chikooza or poultry farming.',
  display: {
    kind: 'public_answer',
    summary: 'Hi, I am Chikbot. Ask me about Chikooza or poultry farming.',
    items: [],
    sources: []
  }
};

const getChatApiUrl = () => {
  const baseUrl = apiPath || '/';
  return `${baseUrl.replace(/\/?$/, '/')}chat/`;
};

const buildHistoryPayload = (messageList) => {
  const selected = [];
  const counts = { user: 0, bot: 0 };

  [...messageList].reverse().forEach((message) => {
    if (message.loading || message.id === 'initial' || !message.text) {
      return;
    }
    const role = message.role === 'user' ? 'user' : 'bot';
    if (counts[role] >= 3) {
      return;
    }
    counts[role] += 1;
    selected.push({
      role,
      content: String(message.text).slice(0, 500)
    });
  });

  return selected.reverse();
};

const normalizeAnswer = (message) => {
  const display = message.display || {};
  if (display.kind === 'public_answer') {
    const items = Array.isArray(display.items) ? display.items.filter(Boolean) : [];
    return {
      summary: display.summary || message.text,
      items,
      sources: Array.isArray(display.sources) ? display.sources : []
    };
  }

  const lines = String(message.text || '')
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean);
  const items = [];
  const summary = [];

  lines.forEach((line) => {
    const bullet = line.match(/^(?:[-*•]|\d+[.)])\s*(.+)$/);
    if (bullet) {
      items.push(bullet[1].trim());
    } else if (items.length) {
      items[items.length - 1] = `${items[items.length - 1]} ${line}`.trim();
    } else {
      summary.push(line);
    }
  });

  const summaryText = summary.join(' ') || message.text;
  return {
    summary: summaryText,
    items,
    sources: Array.isArray(message.sources) ? message.sources : []
  };
};

const PublicBotMessage = ({ message }) => {
  const { summary, items } = normalizeAnswer(message);
  const hasList = items.length > 0;

  return (
    <div className="chikbot-message chikbot-message-bot">
      <div className="chikbot-bubble chikbot-bubble-bot">
        {summary && !hasList && <p>{summary}</p>}
        {summary && hasList && (
          <p className="chikbot-answer-lead">{summary}</p>
        )}

        {hasList && (
          <ul className="chikbot-bullet-list">
            {items.map((item, index) => (
              <li key={`${item}-${index}`}>{item}</li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
};

const PublicUserMessage = ({ text }) => (
  <div className="chikbot-message chikbot-message-user">
    <div className="chikbot-bubble chikbot-bubble-user">{text}</div>
  </div>
);

/** Public chatbot that preserves the reader's position unless they are near the latest message. */
const ChikoozaChatbot = ({ defaultOpen = false, alwaysVisible = true }) => {
  const [showChatbot, setShowChatbot] = useState(defaultOpen);
  const [messages, setMessages] = useState([INITIAL_MESSAGE]);
  const [inputValue, setInputValue] = useState('');
  const [isSending, setIsSending] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const messageListRef = useRef(null);
  const shouldStickToBottomRef = useRef(true);

  useLayoutEffect(() => {
    if (!showChatbot || !shouldStickToBottomRef.current) {
      return;
    }
    const node = messageListRef.current;
    if (node) {
      node.scrollTop = node.scrollHeight;
    }
  }, [messages, showChatbot]);

  const toggleChatbot = () => {
    setShowChatbot(prev => !prev);
  };

  const updateScrollPreference = () => {
    const node = messageListRef.current;
    if (!node) {
      return;
    }
    const distanceFromBottom = node.scrollHeight - node.scrollTop - node.clientHeight;
    shouldStickToBottomRef.current = distanceFromBottom < 70;
  };

  const appendMessage = (message) => {
    setMessages(prev => [...prev, message]);
  };

  const sendMessage = async () => {
    const query = inputValue.trim();
    if (!query || isSending) {
      return;
    }
    const history = buildHistoryPayload(messages);

    shouldStickToBottomRef.current = true;
    setInputValue('');
    setIsSending(true);
    appendMessage({
      id: `user-${Date.now()}`,
      role: 'user',
      text: query
    });
    appendMessage({
      id: `loading-${Date.now()}`,
      role: 'bot',
      loading: true,
      text: 'Finding the right answer...'
    });

    try {
      const response = await fetch(getChatApiUrl(), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, mode: 'rag', history, session_id: sessionId })
      });
      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        throw new Error(
          response.status >= 500
            ? 'Chikbot is temporarily unavailable. Please try again in a moment.'
            : data.error || data.message || 'Chatbot request failed.'
        );
      }

      if (data.session_id) {
        setSessionId(data.session_id);
      }

      setMessages(prev => [
        ...prev.filter(message => !message.loading),
        {
          id: `bot-${Date.now()}`,
          role: 'bot',
          text: data.response || data.message || 'No response received.',
          display: data.display || {},
          sources: data.sources || []
        }
      ]);
    } catch (error) {
      setMessages(prev => [
        ...prev.filter(message => !message.loading),
        {
          id: `error-${Date.now()}`,
          role: 'bot',
          text: error.message || "Sorry, I couldn't get a response."
        }
      ]);
    } finally {
      setIsSending(false);
    }
  };

  const handleKeyDown = (event) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      sendMessage();
    }
  };

  return (
    <div className="chikooza-chatbot-container" hidden={!alwaysVisible && !showChatbot}>
      {showChatbot && (
        <section className="chikbot-panel" aria-label="Conversation with Chikbot">
          <header className="chikbot-panel-header">
            <div>
              <p>Conversation with</p>
              <h2>Chikbot</h2>
            </div>
            <button
              type="button"
              className="chikbot-panel-close"
              onClick={toggleChatbot}
              aria-label="Close Chikbot"
            >
              <span aria-hidden="true">×</span>
            </button>
          </header>

          <div
            className="chikbot-message-list"
            ref={messageListRef}
            onScroll={updateScrollPreference}
          >
            {messages.map((message) => (
              message.role === 'user'
                ? <PublicUserMessage key={message.id} text={message.text} />
                : <PublicBotMessage key={message.id} message={message} />
            ))}
          </div>

          <footer className="chikbot-composer">
            <textarea
              aria-label="Message Chikbot"
              value={inputValue}
              onChange={(event) => setInputValue(event.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Message..."
              rows={1}
            />
            <button
              type="button"
              onClick={sendMessage}
              disabled={isSending || !inputValue.trim()}
              aria-label="Send message"
            >
              <span aria-hidden="true">↗</span>
            </button>
          </footer>
        </section>
      )}

      {!showChatbot && (
        <button
          type="button"
          className="chatbot-toggle-button"
          onClick={toggleChatbot}
          aria-expanded={showChatbot}
          aria-label="Open chatbot"
        >
          <img src={ChikbotLogo} alt="" className="chatbot-launcher-logo" aria-hidden="true" />
        </button>
      )}
      {!showChatbot && (
        <div className="chatbot-label">
          <span>Chikbot</span>
        </div>
      )}
    </div>
  );
};

PublicBotMessage.propTypes = {
  message: PropTypes.shape({
    text: PropTypes.string,
    display: PropTypes.object,
    sources: PropTypes.array
  }).isRequired
};

PublicUserMessage.propTypes = {
  text: PropTypes.string.isRequired
};

ChikoozaChatbot.propTypes = {
  defaultOpen: PropTypes.bool,
  alwaysVisible: PropTypes.bool
};

export default ChikoozaChatbot;

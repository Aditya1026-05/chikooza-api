// MV-2025-07-05-<4>  STARTS
import { apiPath } from '../../Constants';

const LOADING_MESSAGE = 'Searching the Chikooza knowledge base...';

const getChatApiUrl = () => {
  const baseUrl = apiPath || '/';
  return `${baseUrl.replace(/\/?$/, '/')}chat/`;
};

class ActionProvider {
  constructor(createChatBotMessage, setStateFunc, createClientMessage, stateRef, createCustomMessage) {
    this.createChatBotMessage = createChatBotMessage;
    this.setState = setStateFunc;
    this.createCustomMessage = createCustomMessage;
  }

  handleUserMessage = async (message) => {
    if (!message?.trim()) {
      this.updateChatbotState(this.createChatBotMessage("Please type a question first."));
      return;
    }

    // U: NEW: public chat now uses RAG, so show retrieval-specific loading.
    const loadingMessage = this.createChatBotMessage(LOADING_MESSAGE);
    this.updateChatbotState(loadingMessage);

    try {
      // OLD: const res = await fetch('https://local.api.chuza.com:8001/chat/', {
      // U: NEW: build the URL from the configured API base URL and tolerate missing trailing slashes.
      const res = await fetch(getChatApiUrl(), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        // U: OLD: the public website widget called the legacy RAG assistant by default.
        // U: NEW: route homepage visitors to the public product assistant; authenticated
        // U: farmer-data chat stays separate behind /ai/.
        body: JSON.stringify({ query: message.trim(), mode: 'site' })
      });

      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        const safeError = res.status >= 500
          ? "Chikbot is temporarily unavailable. Please try again in a moment."
          : data.error || data.message || "Chatbot request failed.";
        throw new Error(safeError);
      }

      const answer = data.response || data.message || "No response received.";
      const payload = {
        answer,
        display: data.display || {},
        sources: data.sources || [],
        provider: data.provider,
        fallback: data.fallback
      };
      const botMessage = this.createCustomMessage
        ? this.createCustomMessage(answer, 'publicAnswer', { payload })
        : this.createChatBotMessage(answer);
      this.updateChatbotState(botMessage);
    } catch (error) {
      // U: OLD: every backend error displayed the same generic message.
      // U: NEW: show safe backend validation errors, while still hiding technical details.
      const errorMessage = this.createChatBotMessage(
        error.message || "Sorry, I couldn't get a response."
      );
      this.updateChatbotState(errorMessage);
    }
  };

  updateChatbotState = (message) => {
    this.setState(prev => ({
      ...prev,
      messages: [...prev.messages.filter(m => m.message !== LOADING_MESSAGE), message]
    }));
  };
}

export default ActionProvider;
// MV-2025-07-05-<4>  ENDS

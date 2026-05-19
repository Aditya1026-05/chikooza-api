// MV-2025-07-05-<4>  STARTS
import { apiPath } from '../../Constants';

const getChatApiUrl = () => {
  const baseUrl = apiPath || '/';
  return `${baseUrl.replace(/\/?$/, '/')}chat/`;
};

class ActionProvider {
  constructor(createChatBotMessage, setStateFunc) {
    this.createChatBotMessage = createChatBotMessage;
    this.setState = setStateFunc;
  }

  handleUserMessage = async (message) => {
    if (!message?.trim()) {
      this.updateChatbotState(this.createChatBotMessage("Please type a question first."));
      return;
    }

    const loadingMessage = this.createChatBotMessage("Thinking...");
    this.updateChatbotState(loadingMessage);

    try {
      // OLD: const res = await fetch('https://local.api.chuza.com:8001/chat/', {
      // U: NEW: build the URL from the configured API base URL and tolerate missing trailing slashes.
      const res = await fetch(getChatApiUrl(), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: message.trim() })
      });

      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(data.error || data.message || "Chatbot request failed.");
      }

      const botMessage = this.createChatBotMessage(data.response || data.message || "No response received.");
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
      messages: [...prev.messages.filter(m => m.message !== "Thinking..."), message]
    }));
  };
}

export default ActionProvider;
// MV-2025-07-05-<4>  ENDS

// MV-2025-07-05-<4>  STARTS
import { apiPath } from '../../Constants';

class ActionProvider {
  constructor(createChatBotMessage, setStateFunc) {
    this.createChatBotMessage = createChatBotMessage;
    this.setState = setStateFunc;
  }

  handleUserMessage = async (message) => {
    // Show loading message
    const loadingMessage = this.createChatBotMessage("Thinking...");
    this.updateChatbotState(loadingMessage);

    try {
      // Send to backend and get response
      // OLD: const res = await fetch('https://local.api.chuza.com:8001/chat/', {
      // NEW: Use the same environment-driven API base URL as the rest of the UI.
      const res = await fetch(`${apiPath}chat/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: message })
      });
      const data = await res.json();
      const botMessage = this.createChatBotMessage(data.response || data.message || "No response received");
      this.updateChatbotState(botMessage);

    } catch (error) {
      const errorMessage = this.createChatBotMessage("Sorry, I couldn't get a response");
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

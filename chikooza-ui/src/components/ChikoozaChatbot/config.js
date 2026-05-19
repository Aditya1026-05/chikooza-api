// MV-2025-07-05-<2>  STARTS
import { createChatBotMessage } from 'react-chatbot-kit';

const config = {
  // U: OLD: generic greeting did not explain what the public bot can do.
  // U: NEW: make the unauthenticated assistant purpose clear to visitors.
  initialMessages: [createChatBotMessage("Hi, I am ChikBOT. Ask me what Chikooza does, how it helps poultry farms, or how to get started.")],
  botName: "ChikBOT",
  customComponents: {},
  widgets: [],
};

export default config;
// MV-2025-07-05-<2>  ENDS

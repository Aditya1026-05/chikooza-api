// MV-2025-07-05-<2>  STARTS
import { createChatBotMessage } from 'react-chatbot-kit';

const config = {
  // U: OLD: generic greeting did not explain what the public bot can do.
  // U: NEW: make the unauthenticated RAG assistant purpose clear to visitors.
  initialMessages: [createChatBotMessage("Hi, I am Chikooza AI. Ask me about Chikooza, poultry farm setup, broiler management, feed, mortality, FCR, or how to get started.")],
  botName: "ChikBOT",
  customComponents: {},
  widgets: [],
};

export default config;
// MV-2025-07-05-<2>  ENDS

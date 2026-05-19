/*  MV-2025-07-05-<7>  STARTS */
import { lazy } from "react";

// U: OLD: this page reused the public website chatbot even for logged-in farmers.
// const ChikoozaChatbot = lazy(() => import("../../components/ChikoozaChatbot/ChikoozaChatbot"));
// U: NEW: logged-in `/chatbot` route now uses authenticated `/ai/` farmer-data chat.
const FarmerAiChatbot = lazy(() => import("../../components/FarmerAiChatbot/FarmerAiChatbot"));

const ChatbotPage = () => {
  return (
    <div className="chatbot-page-container">
      <FarmerAiChatbot />
    </div>
  );
};

export default ChatbotPage;
/*  MV-2025-07-05-<7>  ENDS */

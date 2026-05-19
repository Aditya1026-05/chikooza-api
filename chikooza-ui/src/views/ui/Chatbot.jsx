/*  MV-2025-07-05-<7>  STARTS */
import { lazy } from "react";
const ChikoozaChatbot = lazy(() => import("../../components/ChikoozaChatbot/ChikoozaChatbot"));

const ChatbotPage = () => {
  return (
    <div className="chatbot-page-container">
      <ChikoozaChatbot />
    </div>
  );
};

export default ChatbotPage;
/*  MV-2025-07-05-<7>  ENDS */
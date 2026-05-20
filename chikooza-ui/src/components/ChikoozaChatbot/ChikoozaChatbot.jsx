// MV-2025-07-05-<3>  STARTS
import React, { useState } from 'react';
import PropTypes from 'prop-types';
import Chatbot from 'react-chatbot-kit';
import ActionProvider from './ActionProvider';
import MessageParser from './MessageParser';
import config from './config';
import './styles.css'; // Import your chatbot styles

/**
 * ChikoozaChatbot Component
 * A customizable chatbot interface for the Chikooza application
 */
const ChikoozaChatbot = ({ defaultOpen = false, alwaysVisible = true }) => {
  const [showChatbot, setShowChatbot] = useState(defaultOpen);

  const toggleChatbot = () => {
    setShowChatbot(prev => !prev);
  };

  return (
    <div className="chikooza-chatbot-container" hidden={!alwaysVisible && !showChatbot}>
      {showChatbot && (
        <div className="chatbot-wrapper">
          <Chatbot
            config={config}
            messageParser={MessageParser}
            actionProvider={ActionProvider}
          />
        </div>
      )}

      <button
        type="button"
        className="chatbot-toggle-button"
        onClick={toggleChatbot}
        aria-expanded={showChatbot}
        aria-label={showChatbot ? 'Close chatbot' : 'Open chatbot'}
      >
        {showChatbot ? '×' : '💭'}
      </button>
      {!showChatbot && (
        <div className="chatbot-label">
          <span>Chat with</span>
          <span>AI</span>
        </div>
      )}
    </div>
  );
};

ChikoozaChatbot.propTypes = {
  defaultOpen: PropTypes.bool,
  alwaysVisible: PropTypes.bool
};

export default ChikoozaChatbot;
// MV-2025-07-05-<3>  ENDS

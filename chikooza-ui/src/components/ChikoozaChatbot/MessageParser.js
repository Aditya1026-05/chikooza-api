// MV-2025-07-05-<5>  STARTS
class MessageParser {
  constructor(actionProvider) {
    this.actionProvider = actionProvider;
  }

  parse(message) {
    console.log("Parser received:", message); // Add this line
    this.actionProvider.handleUserMessage(message);
  }
}

export default MessageParser;
// MV-2025-07-05-<5>  ENDS
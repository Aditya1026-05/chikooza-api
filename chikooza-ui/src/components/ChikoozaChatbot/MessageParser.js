// MV-2025-07-05-<5>  STARTS
class MessageParser {
  constructor(actionProvider) {
    this.actionProvider = actionProvider;
  }

  parse(message) {
    // U: NEW: keep public chat clean in production browser consoles.
    this.actionProvider.handleUserMessage(message);
  }
}

export default MessageParser;
// MV-2025-07-05-<5>  ENDS

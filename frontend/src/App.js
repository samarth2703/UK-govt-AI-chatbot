import { useState, useEffect, useRef } from "react";
import "@/App.css";
import axios from "axios";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Mic, Send, Trash2, Globe } from "lucide-react";
import { toast } from "sonner";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

function App() {
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState("");
  const [isRecording, setIsRecording] = useState(false);
  const [sessionId] = useState(() => `session-${Date.now()}`);
  const [language, setLanguage] = useState("english");
  const [isLoading, setIsLoading] = useState(false);
  const scrollRef = useRef(null);
  const recognitionRef = useRef(null);

  // Initialize speech recognition
  useEffect(() => {
    if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      recognitionRef.current = new SpeechRecognition();
      recognitionRef.current.continuous = false;
      recognitionRef.current.interimResults = false;
      recognitionRef.current.lang = language === "hindi" ? "hi-IN" : "en-US";

      recognitionRef.current.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        setInputMessage(transcript);
        setIsRecording(false);
      };

      recognitionRef.current.onerror = (event) => {
        console.error('Speech recognition error:', event.error);
        setIsRecording(false);
        toast.error("Voice input failed. Please try again.");
      };

      recognitionRef.current.onend = () => {
        setIsRecording(false);
      };
    }
  }, [language]);

  // Scroll to bottom when messages change
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  // Load chat history
  useEffect(() => {
    loadChatHistory();
  }, []);

  const loadChatHistory = async () => {
    try {
      const response = await axios.get(`${API}/chat/history/${sessionId}`);
      const history = response.data.map(msg => ([
        { type: 'user', text: msg.message },
        { type: 'bot', text: msg.response }
      ])).flat();
      setMessages(history);
    } catch (error) {
      console.error('Failed to load history:', error);
    }
  };

  const handleSendMessage = async () => {
    if (!inputMessage.trim() || isLoading) return;

    const userMessage = inputMessage.trim();
    setInputMessage("");
    setMessages(prev => [...prev, { type: 'user', text: userMessage }]);
    setIsLoading(true);

    try {
      const response = await axios.post(`${API}/chat`, {
        session_id: sessionId,
        message: userMessage,
        language: language
      });

      setMessages(prev => [
        ...prev,
        { type: 'bot', text: response.data.response }
      ]);
    } catch (error) {
      console.error('Chat error:', error);
      toast.error("Failed to get response. Please try again.");
      setMessages(prev => [
        ...prev,
        { type: 'bot', text: "Sorry, I encountered an error. Please try again." }
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleVoiceInput = () => {
    if (!recognitionRef.current) {
      toast.error("Voice input is not supported in your browser.");
      return;
    }

    if (isRecording) {
      recognitionRef.current.stop();
      setIsRecording(false);
    } else {
      setIsRecording(true);
      recognitionRef.current.start();
      toast.info("Listening...");
    }
  };

  const handleClearChat = async () => {
    try {
      await axios.delete(`${API}/chat/session/${sessionId}`);
      setMessages([]);
      toast.success("Chat cleared successfully");
    } catch (error) {
      console.error('Clear chat error:', error);
      toast.error("Failed to clear chat");
    }
  };

  const toggleLanguage = () => {
    const newLang = language === "english" ? "hindi" : "english";
    setLanguage(newLang);
    if (recognitionRef.current) {
      recognitionRef.current.lang = newLang === "hindi" ? "hi-IN" : "en-US";
    }
  };

  return (
    <div className="app-container">
      {/* Header */}
      <header className="header">
        <div className="header-content">
          <div className="logo-section">
            <div className="logo-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M12 2L2 7l10 5 10-5-10-5z"/>
                <path d="M2 17l10 5 10-5M2 12l10 5 10-5"/>
              </svg>
            </div>
            <div>
              <h1 className="header-title">Apni Sarkar Bot</h1>
              <p className="header-subtitle">Uttarakhand Government Services Assistant</p>
            </div>
          </div>
          <div className="header-actions">
            <Button
              variant="ghost"
              size="sm"
              onClick={toggleLanguage}
              className="language-btn"
              data-testid="language-toggle-btn"
            >
              <Globe className="icon" />
              {language === "hindi" ? "हिंदी" : "English"}
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={handleClearChat}
              className="clear-btn"
              data-testid="clear-chat-btn"
            >
              <Trash2 className="icon" />
            </Button>
          </div>
        </div>
      </header>

      {/* Chat Area */}
      <main className="chat-main">
        <div className="chat-container">
          <Card className="chat-card">
            <ScrollArea className="messages-area" ref={scrollRef}>
              {messages.length === 0 ? (
                <div className="welcome-screen" data-testid="welcome-screen">
                  <div className="welcome-icon">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M12 2L2 7l10 5 10-5-10-5z"/>
                      <path d="M2 17l10 5 10-5M2 12l10 5 10-5"/>
                    </svg>
                  </div>
                  <h2 className="welcome-title">Welcome to Apni Sarkar Bot</h2>
                  <p className="welcome-text">
                    Ask me anything about Uttarakhand Government Services
                  </p>
                  <div className="suggestions">
                    <button
                      className="suggestion-chip"
                      onClick={() => setInputMessage("Tell me about Char Dham Yatra registration")}
                      data-testid="suggestion-chip-1"
                    >
                      Char Dham Yatra Registration
                    </button>
                    <button
                      className="suggestion-chip"
                      onClick={() => setInputMessage("How to apply for birth certificate?")}
                      data-testid="suggestion-chip-2"
                    >
                      Birth Certificate
                    </button>
                    <button
                      className="suggestion-chip"
                      onClick={() => setInputMessage("What is Digital Signature Certificate?")}
                      data-testid="suggestion-chip-3"
                    >
                      Digital Signature
                    </button>
                  </div>
                </div>
              ) : (
                <div className="messages-list" data-testid="messages-list">
                  {messages.map((msg, index) => (
                    <div
                      key={index}
                      className={`message ${msg.type}`}
                      data-testid={`message-${msg.type}-${index}`}
                    >
                      <div className="message-avatar">
                        {msg.type === 'user' ? (
                          <div className="user-avatar">U</div>
                        ) : (
                          <div className="bot-avatar">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                              <path d="M12 2L2 7l10 5 10-5-10-5z"/>
                              <path d="M2 17l10 5 10-5"/>
                            </svg>
                          </div>
                        )}
                      </div>
                      <div className="message-content">
                        <div className="message-text">{msg.text}</div>
                      </div>
                    </div>
                  ))}
                  {isLoading && (
                    <div className="message bot" data-testid="loading-indicator">
                      <div className="message-avatar">
                        <div className="bot-avatar">
                          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <path d="M12 2L2 7l10 5 10-5-10-5z"/>
                            <path d="M2 17l10 5 10-5"/>
                          </svg>
                        </div>
                      </div>
                      <div className="message-content">
                        <div className="typing-indicator">
                          <span></span>
                          <span></span>
                          <span></span>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </ScrollArea>

            {/* Input Area */}
            <div className="input-area">
              <div className="input-container">
                <Input
                  value={inputMessage}
                  onChange={(e) => setInputMessage(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
                  placeholder={language === "hindi" ? "अपना सवाल यहाँ लिखें..." : "Type your question here..."}
                  className="message-input"
                  disabled={isLoading}
                  data-testid="message-input"
                />
                <Button
                  onClick={handleVoiceInput}
                  variant="ghost"
                  size="icon"
                  className={`voice-btn ${isRecording ? 'recording' : ''}`}
                  data-testid="voice-input-btn"
                >
                  <Mic className="icon" />
                </Button>
                <Button
                  onClick={handleSendMessage}
                  disabled={!inputMessage.trim() || isLoading}
                  className="send-btn"
                  data-testid="send-message-btn"
                >
                  <Send className="icon" />
                </Button>
              </div>
            </div>
          </Card>
        </div>
      </main>

      {/* Footer */}
      <footer className="footer">
        <p>Powered by AI | Uttarakhand Government Services</p>
      </footer>
    </div>
  );
}

export default App;
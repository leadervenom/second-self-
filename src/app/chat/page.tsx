"use client";

import { useEffect, useState } from "react";
import ChatView from "@/components/chat/ChatView";
import { postChat } from "@/lib/api";

type MessageRole = "twin" | "user";

interface ToolCall {
  name: string;
  args: string;
}

interface ChatMessage {
  id: string;
  role: MessageRole;
  content: string;
  timestamp: string;
  toolCall?: ToolCall;
}

function nowTime() {
  return new Date().toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function ChatPage() {
  const [userName, setUserName] = useState("Vajhra");
  const [sessionId] = useState("demo-local");
  const [isThinking, setIsThinking] = useState(false);

  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: crypto.randomUUID(),
      role: "twin",
      content:
        "I am running in Windows web mode. The macOS desktop shell is disabled, but the assistant interface is ready for testing.",
      timestamp: nowTime(),
    },
  ]);

  useEffect(() => {
    const storedName = localStorage.getItem("secondSelfName");
    if (storedName) setUserName(storedName);
  }, []);

  const handleSendMessage = async (message: string) => {
    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: message,
      timestamp: nowTime(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setIsThinking(true);

    try {
      const response = await postChat(message, sessionId);

      const twinMessage: ChatMessage = {
        id: crypto.randomUUID(),
        role: "twin",
        content: response.response || "Done.",
        timestamp: nowTime(),
      };

      setMessages((prev) => [...prev, twinMessage]);
    } catch (err) {
      console.error(err);

      const fallbackMessage: ChatMessage = {
        id: crypto.randomUUID(),
        role: "twin",
        content:
          "The chat backend is reachable from the UI, but the real AI brain is not connected yet. Next step is adding Claude, Gemini, or a local model.",
        timestamp: nowTime(),
        toolCall: {
          name: "demo_mode",
          args: "no API key connected",
        },
      };

      setMessages((prev) => [...prev, fallbackMessage]);
    } finally {
      setIsThinking(false);
    }
  };

  return (
    <ChatView
      userName={userName}
      messages={messages}
      isThinking={isThinking}
      onSendMessage={handleSendMessage}
    />
  );
}

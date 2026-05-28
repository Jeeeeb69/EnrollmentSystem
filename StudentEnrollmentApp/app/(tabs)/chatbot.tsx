import React, { useRef, useState } from "react";

import {
  ActivityIndicator,
  Alert,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";

import Ionicons from "@expo/vector-icons/Ionicons";

import { api, getChatbotWebSocketUrl } from "../../src/api/api";
import { tokenStorage } from "../../src/api/storage";
import {
  cleanText,
  getApiErrorMessage,
} from "../../src/utils/validation";

interface ChatMessage {
  id: number;
  role: "bot" | "user";
  text: string;
}

const starterPrompts = [
  "What subjects are available?",
  "Show my enrollment status",
  "Which sections have slots?",
  "How do I enroll?",
];

const requestChatbotReplyOverWebSocket = async (message: string) => {
  const token = await tokenStorage.getItem("accessToken");

  if (!token) {
    throw new Error("Missing access token.");
  }

  return new Promise<string>((resolve, reject) => {
    const socket = new WebSocket(getChatbotWebSocketUrl(token));
    let settled = false;

    const cleanup = () => {
      settled = true;
      clearTimeout(timeoutId);
      socket.close();
    };

    const timeoutId = setTimeout(() => {
      if (!settled) {
        cleanup();
        reject(new Error("Chatbot WebSocket timed out."));
      }
    }, 35000);

    socket.onopen = () => {
      socket.send(JSON.stringify({ message }));
    };

    socket.onmessage = (event) => {
      try {
        const payload = JSON.parse(String(event.data));

        if (payload.type === "reply") {
          cleanup();
          resolve(payload.reply || "I could not prepare a reply.");
        }

        if (payload.type === "error") {
          cleanup();
          reject(new Error(payload.error || "Chatbot WebSocket error."));
        }
      } catch {
        cleanup();
        reject(new Error("Invalid chatbot WebSocket response."));
      }
    };

    socket.onerror = () => {
      if (!settled) {
        cleanup();
        reject(new Error("Chatbot WebSocket unavailable."));
      }
    };

    socket.onclose = () => {
      if (!settled) {
        cleanup();
        reject(new Error("Chatbot WebSocket closed."));
      }
    };
  });
};

export default function Chatbot() {
  const scrollRef = useRef<ScrollView | null>(null);
  const [message, setMessage] = useState("");
  const [sending, setSending] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: Date.now(),
      role: "bot",
      text: "Hi. I am the Ollama Qwen enrollment assistant. Ask me about subjects, sections, profile, account, or enrollment questions.",
    },
  ]);

  const scrollToEnd = () => {
    requestAnimationFrame(() => {
      scrollRef.current?.scrollToEnd({ animated: true });
    });
  };

  const sendMessage = async (rawMessage = message) => {
    const cleanMessage = cleanText(rawMessage);

    if (!cleanMessage) {
      Alert.alert("Error", "Please type a message.");
      return;
    }

    if (cleanMessage.length > 500) {
      Alert.alert("Error", "Message must be 500 characters or fewer.");
      return;
    }

    const userMessage: ChatMessage = {
      id: Date.now(),
      role: "user",
      text: cleanMessage,
    };

    setMessages((current) => [...current, userMessage]);
    setMessage("");
    setSending(true);
    scrollToEnd();

    try {
      let reply = "";

      try {
        reply = await requestChatbotReplyOverWebSocket(cleanMessage);
      } catch {
        const response = await api.post("chatbot/", {
          message: cleanMessage,
        });
        reply = response.data.reply || "I could not prepare a reply.";
      }

      const botMessage: ChatMessage = {
        id: Date.now() + 1,
        role: "bot",
        text: reply,
      };

      setMessages((current) => [...current, botMessage]);
      scrollToEnd();
    } catch (error: any) {
      console.log("CHATBOT ERROR:", error?.response?.data || error);

      const botMessage: ChatMessage = {
        id: Date.now() + 1,
        role: "bot",
        text: getApiErrorMessage(
          error?.response?.data,
          "Chatbot is unavailable right now."
        ),
      };

      setMessages((current) => [...current, botMessage]);
      scrollToEnd();
    } finally {
      setSending(false);
    }
  };

  return (
    <KeyboardAvoidingView
      behavior={Platform.OS === "ios" ? "padding" : undefined}
      style={styles.page}
    >
      <View style={styles.header}>
        <View>
          <Text style={styles.title}>WebSocket Chat</Text>
          <Text style={styles.subtitle}>Live Ollama Qwen enrollment assistant</Text>
        </View>

        <View style={styles.headerIcon}>
          <Ionicons name="chatbubble-ellipses-outline" size={24} color="#1D4ED8" />
        </View>
      </View>

      <ScrollView
        ref={scrollRef}
        style={styles.messages}
        contentContainerStyle={styles.messagesContent}
        keyboardShouldPersistTaps="handled"
      >
        {messages.map((item) => (
          <View
            key={item.id}
            style={[
              styles.messageRow,
              item.role === "user" && styles.userMessageRow,
            ]}
          >
            <View
              style={[
                styles.bubble,
                item.role === "user" ? styles.userBubble : styles.botBubble,
              ]}
            >
              <Text
                style={[
                  styles.bubbleText,
                  item.role === "user" && styles.userBubbleText,
                ]}
              >
                {item.text}
              </Text>
            </View>
          </View>
        ))}

        {sending && (
          <View style={styles.messageRow}>
            <View style={[styles.bubble, styles.botBubble, styles.typingBubble]}>
              <ActivityIndicator color="#1D4ED8" />
              <Text style={styles.typingText}>Thinking...</Text>
            </View>
          </View>
        )}
      </ScrollView>

      <View style={styles.promptRow}>
        <ScrollView horizontal showsHorizontalScrollIndicator={false}>
          {starterPrompts.map((prompt) => (
            <TouchableOpacity
              key={prompt}
              style={styles.promptChip}
              onPress={() => sendMessage(prompt)}
              disabled={sending}
            >
              <Text style={styles.promptText}>{prompt}</Text>
            </TouchableOpacity>
          ))}
        </ScrollView>
      </View>

      <View style={styles.composer}>
        <TextInput
          style={styles.input}
          value={message}
          onChangeText={setMessage}
          placeholder="Ask about enrollment..."
          placeholderTextColor="#94A3B8"
          multiline
          maxLength={500}
        />

        <TouchableOpacity
          style={[styles.sendButton, sending && styles.sendButtonDisabled]}
          onPress={() => sendMessage()}
          disabled={sending}
        >
          <Ionicons name="send" size={18} color="#FFFFFF" />
        </TouchableOpacity>
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  page: {
    flex: 1,
    backgroundColor: "#F8FAFC",
  },

  header: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingHorizontal: 16,
    paddingTop: 18,
    paddingBottom: 14,
    backgroundColor: "#FFFFFF",
    borderBottomWidth: 1,
    borderBottomColor: "#E2E8F0",
  },

  title: {
    color: "#0F172A",
    fontSize: 24,
    fontWeight: "700",
  },

  subtitle: {
    color: "#64748B",
    fontSize: 13,
    marginTop: 2,
  },

  headerIcon: {
    width: 44,
    height: 44,
    borderRadius: 8,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "#DBEAFE",
  },

  messages: {
    flex: 1,
  },

  messagesContent: {
    padding: 16,
    paddingBottom: 10,
    width: "100%",
    maxWidth: 960,
    alignSelf: "center",
  },

  messageRow: {
    flexDirection: "row",
    marginBottom: 10,
  },

  userMessageRow: {
    justifyContent: "flex-end",
  },

  bubble: {
    maxWidth: "82%",
    borderRadius: 8,
    paddingHorizontal: 14,
    paddingVertical: 11,
  },

  botBubble: {
    backgroundColor: "#FFFFFF",
    borderWidth: 1,
    borderColor: "#E2E8F0",
  },

  userBubble: {
    backgroundColor: "#1D4ED8",
  },

  bubbleText: {
    color: "#0F172A",
    fontSize: 14,
    lineHeight: 20,
  },

  userBubbleText: {
    color: "#FFFFFF",
  },

  typingBubble: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
  },

  typingText: {
    color: "#64748B",
    fontSize: 13,
  },

  promptRow: {
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderTopWidth: 1,
    borderTopColor: "#E2E8F0",
    backgroundColor: "#FFFFFF",
  },

  promptChip: {
    backgroundColor: "#EFF6FF",
    borderWidth: 1,
    borderColor: "#BFDBFE",
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 8,
    marginRight: 8,
  },

  promptText: {
    color: "#1D4ED8",
    fontSize: 13,
    fontWeight: "700",
  },

  composer: {
    flexDirection: "row",
    alignItems: "flex-end",
    gap: 10,
    padding: 12,
    paddingBottom: Platform.OS === "ios" ? 22 : 12,
    backgroundColor: "#FFFFFF",
    borderTopWidth: 1,
    borderTopColor: "#E2E8F0",
  },

  input: {
    flex: 1,
    minHeight: 44,
    maxHeight: 110,
    borderWidth: 1,
    borderColor: "#CBD5E1",
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 10,
    color: "#0F172A",
    backgroundColor: "#FFFFFF",
    fontSize: 14,
  },

  sendButton: {
    width: 44,
    height: 44,
    borderRadius: 8,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "#1D4ED8",
  },

  sendButtonDisabled: {
    opacity: 0.65,
  },
});

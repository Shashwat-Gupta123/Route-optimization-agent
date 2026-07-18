/**
 * useChat — conversation state hook for Component 5.
 *
 * Generates a UUID once per app load (React state, NOT localStorage so
 * sessions don't persist across browser restarts). Manages the local
 * message list, sends to POST /api/chat, and loads history on first open.
 */
import { useState, useCallback, useRef } from "react";
import { postChat, getChatHistory } from "../api/endpoints";

function generateUUID() {
    return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
        const r = (Math.random() * 16) | 0;
        return (c === "x" ? r : (r & 0x3) | 0x8).toString(16);
    });
}

/**
 * @typedef {Object} ChatMessage
 * @property {string} id          - local unique id
 * @property {"user"|"assistant"} role
 * @property {string} content
 * @property {string[]} sources   - tool names (assistant only)
 * @property {string[]} followUps - suggested follow-up chips (assistant only)
 * @property {string} timestamp
 */

export default function useChat() {
    // UUID generated once per React tree mount — stays in state, not storage
    const [conversationId] = useState(() => generateUUID());
    const [messages, setMessages] = useState([]);
    const [thinking, setThinking] = useState(false);
    const [error, setError] = useState(null);
    const historyLoadedRef = useRef(false);

    /** Load conversation history from the backend on first panel open. */
    const loadHistory = useCallback(async () => {
        if (historyLoadedRef.current) return;
        historyLoadedRef.current = true;
        try {
            const data = await getChatHistory(conversationId);
            const turns = data.turns || [];
            if (turns.length === 0) return;
            const loaded = turns.map((t) => ({
                id: `hist-${t.turn_id}`,
                role: t.role,
                content: t.message,
                sources: t.sources_used || [],
                followUps: t.suggested_follow_ups || [],
                timestamp: t.timestamp,
            }));
            setMessages(loaded);
        } catch {
            // Silently ignore — history is nice-to-have, not critical
        }
    }, [conversationId]);

    /** Send a user message and append the assistant's reply. */
    const send = useCallback(
        async (text, pageContext = null) => {
            const trimmed = text.trim();
            if (!trimmed || thinking) return;

            const userMsg = {
                id: `u-${Date.now()}`,
                role: "user",
                content: trimmed,
                sources: [],
                followUps: [],
                timestamp: new Date().toISOString(),
            };
            setMessages((prev) => [...prev, userMsg]);
            setThinking(true);
            setError(null);

            try {
                const data = await postChat(trimmed, conversationId, pageContext);
                const assistantMsg = {
                    id: `a-${Date.now()}`,
                    role: "assistant",
                    content: data.reply || "",
                    sources: data.sources_used || [],
                    followUps: data.suggested_follow_ups || [],
                    timestamp: new Date().toISOString(),
                };
                setMessages((prev) => [...prev, assistantMsg]);
            } catch (err) {
                setError(err?.message || "Failed to get a response. Please try again.");
                // Add error as assistant message so the UI stays clean
                setMessages((prev) => [
                    ...prev,
                    {
                        id: `err-${Date.now()}`,
                        role: "assistant",
                        content:
                            "Sorry, I couldn't reach the assistant right now. Please try again.",
                        sources: [],
                        followUps: [],
                        timestamp: new Date().toISOString(),
                    },
                ]);
            } finally {
                setThinking(false);
            }
        },
        [conversationId, thinking]
    );

    return { conversationId, messages, thinking, error, send, loadHistory };
}

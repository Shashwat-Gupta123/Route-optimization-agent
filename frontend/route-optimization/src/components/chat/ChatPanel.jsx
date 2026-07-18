/**
 * ChatPanel — the expandable chat interface panel.
 *
 * Contains: message list, starter chips (when empty), text input + send,
 * and an animated "thinking" card while the agent is processing.
 */
import { useEffect, useRef, useState } from "react";
import ChatMessage from "./ChatMessage";

const THINKING_STEPS = [
    "Analyzing your query\u2026",
    "Fetching live data\u2026",
    "Running agent tools\u2026",
    "Preparing your answer\u2026",
];

/** Animated thinking card shown while the assistant is working */
function ThinkingCard() {
    const [stepIdx, setStepIdx] = useState(0);

    useEffect(() => {
        const id = setInterval(() => {
            setStepIdx((i) => (i + 1) % THINKING_STEPS.length);
        }, 1400);
        return () => clearInterval(id);
    }, []);

    return (
        <div className="chat-message chat-message--assistant chat-message--fade-in">
            <div className="chat-thinking-card">
                {/* Brain icon */}
                <div className="chat-thinking-icon">
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="currentColor">
                        <path d="M12 2a2 2 0 0 1 2 2c0 .74-.4 1.38-1 1.73V7h1a7 7 0 0 1 7 7h1a1 1 0 0 1 1 1v3a1 1 0 0 1-1 1h-1v1a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-1H2a1 1 0 0 1-1-1v-3a1 1 0 0 1 1-1h1a7 7 0 0 1 7-7h1V5.73c-.6-.35-1-.99-1-1.73a2 2 0 0 1 2-2zm-2 10a1.5 1.5 0 1 0 0 3 1.5 1.5 0 0 0 0-3zm4 0a1.5 1.5 0 1 0 0 3 1.5 1.5 0 0 0 0-3z"/>
                    </svg>
                </div>
                <div className="chat-thinking-body">
                    {/* Cycling status label */}
                    <div className="chat-thinking-status" key={stepIdx}>
                        {THINKING_STEPS[stepIdx]}
                    </div>
                    {/* Progress shimmer bar */}
                    <div className="chat-thinking-bar">
                        <div className="chat-thinking-bar-fill" />
                    </div>
                    {/* Dot bounce */}
                    <div className="chat-thinking-dots">
                        <span /><span /><span />
                    </div>
                </div>
            </div>
        </div>
    );
}

const STARTER_QUERIES = [
    "How many shipments are pending today?",
    "Which vehicles are available right now?",
    "What was our on-time % last week?",
    "Is any vehicle delayed right now?",
];

/**
 * @param {{ chatHook: ReturnType<import("../../hooks/useChat").default>, onClose: ()=>void, pageContext?: object }} props
 */
export default function ChatPanel({ chatHook, onClose, pageContext }) {
    const { messages, thinking, send, loadHistory } = chatHook;
    const [input, setInput] = useState("");
    const bottomRef = useRef(null);

    // Load history once when the panel first mounts
    useEffect(() => {
        loadHistory();
    }, [loadHistory]);

    // Auto-scroll to bottom on new messages
    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages, thinking]);

    const handleSend = () => {
        if (!input.trim() || thinking) return;
        send(input, pageContext);
        setInput("");
    };

    const handleKey = (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };

    const handleChip = (text) => {
        if (thinking) return;
        send(text, pageContext);
    };

    const isEmpty = messages.length === 0 && !thinking;

    return (
        <div className="chat-panel" role="dialog" aria-label="Chat assistant">
            {/* Header */}
            <div className="chat-panel-header">
                <div className="chat-panel-title">
                    <span className="chat-panel-icon">🤖</span>
                    <div>
                        <div className="chat-panel-name">Operations Assistant</div>
                        <div className="chat-panel-subtitle">Ask about shipments, fleet & routes</div>
                    </div>
                </div>
                <button
                    className="chat-close-btn"
                    onClick={onClose}
                    aria-label="Close chat"
                >
                    ✕
                </button>
            </div>

            {/* Message list */}
            <div className="chat-messages">
                {isEmpty && (
                    <div className="chat-empty">
                        <div className="chat-empty-title">How can I help you?</div>
                        <div className="chat-empty-sub">
                            I can answer questions grounded in real warehouse data.
                        </div>
                        <div className="chat-chips chat-starters">
                            {STARTER_QUERIES.map((q) => (
                                <button
                                    key={q}
                                    className="chat-chip"
                                    onClick={() => handleChip(q)}
                                >
                                    {q}
                                </button>
                            ))}
                        </div>
                    </div>
                )}

                {messages.map((msg, i) => (
                    <ChatMessage
                        key={msg.id}
                        message={msg}
                        onFollowUp={handleChip}
                        isLatest={i === messages.length - 1}
                    />
                ))}

                {thinking && <ThinkingCard />}


                <div ref={bottomRef} />
            </div>

            {/* Input row */}
            <div className="chat-input-row">
                <textarea
                    className="chat-input"
                    placeholder="Ask a question about today's operations…"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={handleKey}
                    rows={1}
                    disabled={thinking}
                />
                <button
                    className="chat-send-btn"
                    onClick={handleSend}
                    disabled={!input.trim() || thinking}
                    aria-label="Send"
                >
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                        <line x1="22" y1="2" x2="11" y2="13" />
                        <polygon points="22 2 15 22 11 13 2 9 22 2" />
                    </svg>
                </button>
            </div>
        </div>
    );
}

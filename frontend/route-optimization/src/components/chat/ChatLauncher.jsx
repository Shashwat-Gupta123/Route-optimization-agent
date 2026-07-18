/**
 * ChatLauncher — floating chat button + panel, mounted once in AppShell.
 *
 * Sits fixed at the bottom-right corner. Clicking the circular red button
 * slides up the ChatPanel without navigating away from the current page.
 */
import { useState } from "react";
import useChat from "../../hooks/useChat";
import ChatPanel from "./ChatPanel";

export default function ChatLauncher({ pageContext }) {
    const [open, setOpen] = useState(false);
    const chatHook = useChat();

    return (
        <>
            {/* Floating launcher button */}
            <button
                className="chat-launcher"
                onClick={() => setOpen((o) => !o)}
                aria-label={open ? "Close chat assistant" : "Open chat assistant"}
                title="Operations Chat Assistant"
            >
                {open ? (
                    /* X when open */
                    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
                        <line x1="18" y1="6" x2="6" y2="18" />
                        <line x1="6" y1="6" x2="18" y2="18" />
                    </svg>
                ) : (
                    /* Chat bubble icon when closed */
                    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
                    </svg>
                )}
            </button>

            {/* Slide-up panel */}
            <div className={`chat-panel-wrap ${open ? "chat-panel-wrap--open" : ""}`}>
                {open && (
                    <ChatPanel
                        chatHook={chatHook}
                        onClose={() => setOpen(false)}
                        pageContext={pageContext}
                    />
                )}
            </div>
        </>
    );
}

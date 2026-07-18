/**
 * ChatMessage — single message bubble with sources footnote and follow-up chips.
 *
 * User messages: right-aligned, primary-red pill.
 * Assistant messages: left-aligned white card with optional sources + follow-up chips.
 * Supports inline markdown: **bold**, - bullet lists, section headings.
 */

/** Render a single line with **bold** parsed into <strong> tags */
function RichLine({ text }) {
    const parts = text.split(/(\*\*[^*]+\*\*)/g);
    return (
        <>
            {parts.map((part, i) =>
                part.startsWith("**") && part.endsWith("**") ? (
                    <strong key={i}>{part.slice(2, -2)}</strong>
                ) : (
                    <span key={i}>{part}</span>
                )
            )}
        </>
    );
}

/** Parse content into structured blocks and render them */
function RichContent({ content }) {
    const lines = content.split("\n");
    const blocks = [];
    let currentList = null;

    const flushList = () => {
        if (currentList) {
            blocks.push({ type: "list", items: currentList });
            currentList = null;
        }
    };

    lines.forEach((raw, idx) => {
        const line = raw.trim();
        if (!line) {
            flushList();
            return;
        }
        // Bullet list line: starts with - or •
        if (/^[-•]\s+/.test(line)) {
            const text = line.replace(/^[-•]\s+/, "");
            if (!currentList) currentList = [];
            currentList.push(text);
            return;
        }
        flushList();
        // Looks like a section heading: ends with : and no other colon, or starts with **...**:
        const headingMatch = line.match(/^\*\*(.+?)\*\*\s*:?$/);
        if (headingMatch && line.length < 80) {
            blocks.push({ type: "heading", text: headingMatch[1] });
            return;
        }
        blocks.push({ type: "para", text: line });
    });
    flushList();

    return (
        <div className="chat-rich-content">
            {blocks.map((block, i) => {
                if (block.type === "heading") {
                    return (
                        <div key={i} className="chat-section-heading">
                            {block.text}
                        </div>
                    );
                }
                if (block.type === "list") {
                    return (
                        <ul key={i} className="chat-list">
                            {block.items.map((item, j) => (
                                <li key={j}><RichLine text={item} /></li>
                            ))}
                        </ul>
                    );
                }
                // para
                return (
                    <p key={i} className="chat-para">
                        <RichLine text={block.text} />
                    </p>
                );
            })}
        </div>
    );
}

/**
 * @param {{ message: import("../hooks/useChat").ChatMessage, onFollowUp: (text:string)=>void, isLatest: boolean }} props
 */
export default function ChatMessage({ message, onFollowUp, isLatest }) {
    const isUser = message.role === "user";

    // Map raw tool names to human-readable labels
    const sourceLabel = (name) => {
        const map = {
            query_shipments_tool: "shipment data",
            query_fleet_tool: "fleet data",
            query_route_plan_tool: "route plan",
            query_alerts_tool: "alerts",
            explain_plan_tool: "route plan analysis",
            compute_kpi_tool: "KPI data",
            get_weather_tool: "weather data",
        };
        return map[name] || name;
    };

    const sourcesText =
        !isUser && message.sources && message.sources.length > 0
            ? "Based on: " + [...new Set(message.sources.map(sourceLabel))].join(", ")
            : null;

    return (
        <div className={`chat-message ${isUser ? "chat-message--user" : "chat-message--assistant"} chat-message--fade-in`}>
            {/* AI avatar badge for assistant messages */}
            {!isUser && (
                <div className="chat-avatar">
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="currentColor">
                        <path d="M12 2a2 2 0 0 1 2 2c0 .74-.4 1.38-1 1.73V7h1a7 7 0 0 1 7 7h1a1 1 0 0 1 1 1v3a1 1 0 0 1-1 1h-1v1a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-1H2a1 1 0 0 1-1-1v-3a1 1 0 0 1 1-1h1a7 7 0 0 1 7-7h1V5.73c-.6-.35-1-.99-1-1.73a2 2 0 0 1 2-2zm-2 10a1.5 1.5 0 1 0 0 3 1.5 1.5 0 0 0 0-3zm4 0a1.5 1.5 0 1 0 0 3 1.5 1.5 0 0 0 0-3z"/>
                    </svg>
                </div>
            )}

            <div className="chat-bubble">
                {isUser ? (
                    // User messages: simple text
                    message.content.split("\n").map((line, i) =>
                        line.trim() ? <p key={i} className="chat-para">{line}</p> : null
                    )
                ) : (
                    // Assistant messages: rich markdown rendering
                    <RichContent content={message.content} />
                )}
            </div>

            {/* Sources footnote — subtle, muted */}
            {sourcesText && (
                <div className="chat-sources">
                    <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{marginRight:3, verticalAlign:'middle', flexShrink:0}}>
                        <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
                    </svg>
                    {sourcesText}
                </div>
            )}

            {/* Follow-up chips — only on the latest assistant message */}
            {!isUser && isLatest && message.followUps && message.followUps.length > 0 && (
                <div className="chat-chips">
                    {message.followUps.map((q, i) => (
                        <button
                            key={i}
                            className="chat-chip"
                            onClick={() => onFollowUp(q)}
                            title={q}
                        >
                            {q}
                        </button>
                    ))}
                </div>
            )}
        </div>
    );
}

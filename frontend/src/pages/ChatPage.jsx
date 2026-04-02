import { useState, useRef, useEffect } from 'react'
import { askQuestion } from '../api/index'

const SUGGESTED = [
  "How has Kansas City covered the spread the last 4 years?",
  "Which NFL teams have the best ATS record as road dogs?",
  "How has Alabama performed ATS since 2021?",
  "Which CFB teams have the best home favorite ATS record?",
  "What are the Chiefs' Over/Under trends?",
]

export default function ChatPage() {
  const [messages, setMessages] = useState([
    {
      role   : 'assistant',
      content: 'Welcome to Playbook Football AI. Ask me anything about NFL and CFB stats, ATS records, trends, and more.',
      sources: [],
    }
  ])
  const [input,   setInput]   = useState('')
  const [loading, setLoading] = useState(false)
  const bottomRef             = useRef(null)
  const inputRef              = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSend = async (question) => {
    const q = question || input.trim()
    if (!q || loading) return
    setInput('')
    setMessages((prev) => [...prev, { role: 'user', content: q }])
    setLoading(true)
    try {
      const res = await askQuestion(q)
      setMessages((prev) => [...prev, {
        role   : 'assistant',
        content: res.data.answer,
        sources: res.data.sources || [],
        cached : res.data.cached,
      }])
    } catch {
      setMessages((prev) => [...prev, {
        role   : 'assistant',
        content: 'Sorry, something went wrong. Please try again.',
        sources: [],
      }])
    } finally {
      setLoading(false)
      inputRef.current?.focus()
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="fade-in" style={{ maxWidth: '860px', margin: '0 auto' }}>
      {/* Header */}
      <div style={{ marginBottom: '20px' }}>
        <h1 style={{
          fontFamily   : 'Oswald, sans-serif',
          fontSize     : '1.8rem',
          fontWeight   : '700',
          letterSpacing: '0.05em',
          textTransform: 'uppercase',
          color        : 'var(--text-primary)',
        }}>
          AI <span style={{ color: 'var(--text-accent)' }}>CHAT</span>
        </h1>
        <p style={{
          fontFamily: 'Barlow Condensed, sans-serif',
          fontSize  : '0.9rem',
          color     : 'var(--text-muted)',
          marginTop : '4px',
        }}>
          Powered by GPT-4o-mini with vector search across all NFL & CFB stats
        </p>
      </div>

      {/* Suggested questions */}
      <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginBottom: '20px' }}>
        {SUGGESTED.map((q) => (
          <button
            key={q}
            onClick={() => handleSend(q)}
            disabled={loading}
            style={{
              background  : 'var(--bg-card)',
              border      : '1px solid var(--border)',
              borderRadius: '20px',
              color       : 'var(--text-secondary)',
              cursor      : loading ? 'not-allowed' : 'pointer',
              fontFamily  : 'Barlow Condensed, sans-serif',
              fontSize    : '0.8rem',
              padding     : '5px 12px',
              transition  : 'border-color 0.15s, color 0.15s',
              opacity     : loading ? 0.5 : 1,
            }}
            onMouseEnter={(e) => {
              if (!loading) {
                e.currentTarget.style.borderColor = 'var(--border-accent)'
                e.currentTarget.style.color = 'var(--text-accent)'
              }
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.borderColor = 'var(--border)'
              e.currentTarget.style.color = 'var(--text-secondary)'
            }}
          >
            {q}
          </button>
        ))}
      </div>

      {/* Messages */}
      <div className="card" style={{
        minHeight  : '400px',
        maxHeight  : '560px',
        overflowY  : 'auto',
        padding    : '0',
        display    : 'flex',
        flexDirection: 'column',
      }}>
        <div style={{ flex: 1, padding: '16px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {messages.map((msg, i) => (
            <MessageBubble key={i} msg={msg} />
          ))}

          {loading && (
            <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
              <div style={{
                width       : '28px',
                height      : '28px',
                background  : 'var(--border-accent)',
                borderRadius: '4px',
                display     : 'flex',
                alignItems  : 'center',
                justifyContent: 'center',
                fontSize    : '0.7rem',
                fontFamily  : 'Oswald, sans-serif',
                color       : '#0d0d0d',
                fontWeight  : '700',
                flexShrink  : 0,
              }}>
                AI
              </div>
              <div style={{
                background  : 'var(--bg-table-alt)',
                border      : '1px solid var(--border)',
                borderRadius: '8px',
                padding     : '10px 14px',
                display     : 'flex',
                gap         : '4px',
                alignItems  : 'center',
              }}>
                {[0, 1, 2].map((j) => (
                  <div key={j} className="animate-pulse" style={{
                    width       : '6px',
                    height      : '6px',
                    background  : 'var(--text-muted)',
                    borderRadius: '50%',
                    animationDelay: `${j * 0.2}s`,
                  }} />
                ))}
              </div>
            </div>
          )}

          <div ref={bottomRef} />
        </div>
      </div>

      {/* Input */}
      <div style={{
        display     : 'flex',
        gap         : '8px',
        marginTop   : '12px',
      }}>
        <textarea
          ref={inputRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask about ATS records, trends, strength of schedule..."
          rows={2}
          style={{
            flex        : 1,
            background  : 'var(--bg-card)',
            border      : '1px solid var(--border)',
            borderRadius: '6px',
            color       : 'var(--text-primary)',
            fontFamily  : 'Barlow, sans-serif',
            fontSize    : '0.9rem',
            padding     : '10px 14px',
            outline     : 'none',
            resize      : 'none',
            transition  : 'border-color 0.15s',
          }}
          onFocus={(e) => e.target.style.borderColor = 'var(--border-accent)'}
          onBlur={(e)  => e.target.style.borderColor = 'var(--border)'}
        />
        <button
          onClick={() => handleSend()}
          disabled={loading || !input.trim()}
          style={{
            background  : loading || !input.trim() ? 'var(--border)' : 'var(--border-accent)',
            border      : 'none',
            borderRadius: '6px',
            color       : loading || !input.trim() ? 'var(--text-muted)' : '#0d0d0d',
            cursor      : loading || !input.trim() ? 'not-allowed' : 'pointer',
            fontFamily  : 'Oswald, sans-serif',
            fontSize    : '0.9rem',
            fontWeight  : '600',
            letterSpacing: '0.06em',
            padding     : '0 20px',
            transition  : 'background 0.15s',
            whiteSpace  : 'nowrap',
          }}
        >
          SEND
        </button>
      </div>
      <p style={{
        fontFamily: 'Barlow Condensed, sans-serif',
        fontSize  : '0.75rem',
        color     : 'var(--text-muted)',
        marginTop : '6px',
      }}>
        Press Enter to send • Shift+Enter for new line
      </p>
    </div>
  )
}

function MessageBubble({ msg }) {
  const isUser = msg.role === 'user'
  return (
    <div style={{
      display      : 'flex',
      gap          : '8px',
      flexDirection: isUser ? 'row-reverse' : 'row',
      alignItems   : 'flex-start',
    }}>
      {/* Avatar */}
      <div style={{
        width       : '28px',
        height      : '28px',
        background  : isUser ? 'var(--border-accent)' : 'var(--border-accent)',
        borderRadius: '4px',
        display     : 'flex',
        alignItems  : 'center',
        justifyContent: 'center',
        fontSize    : '0.65rem',
        fontFamily  : 'Oswald, sans-serif',
        color       : '#0d0d0d',
        fontWeight  : '700',
        flexShrink  : 0,
      }}>
        {isUser ? 'YOU' : 'AI'}
      </div>

      <div style={{ maxWidth: '80%' }}>
        {/* Bubble */}
        <div style={{
          background  : isUser ? 'var(--border-accent)' : 'var(--bg-table-alt)',
          border      : '1px solid var(--border)',
          borderRadius: isUser ? '8px 2px 8px 8px' : '2px 8px 8px 8px',
          padding     : '10px 14px',
        }}>
          <div style={{
            fontFamily: 'Barlow, sans-serif',
            fontSize  : '0.88rem',
            color     : isUser ? '#0d0d0d' : 'var(--text-primary)',
            lineHeight: 1.6,
            whiteSpace: 'pre-wrap',
          }}>
            {msg.content.split(/(\*\*[^*]+\*\*)/).map((part, i) =>
              part.startsWith('**') && part.endsWith('**')
                ? <strong key={i} style={{ color: isUser ? '#0d0d0d' : 'var(--text-accent)', fontFamily: 'Barlow Condensed, sans-serif' }}>
                    {part.slice(2, -2)}
                  </strong>
                : part
            )}
          </div>
        </div>

        {/* Sources */}
        {msg.sources?.length > 0 && (
          <div style={{
            display   : 'flex',
            gap       : '4px',
            flexWrap  : 'wrap',
            marginTop : '6px',
          }}>
            <span style={{
              fontFamily: 'Barlow Condensed, sans-serif',
              fontSize  : '0.72rem',
              color     : 'var(--text-muted)',
            }}>
              Sources:
            </span>
            {msg.sources.map((s) => (
              <span key={s} style={{
                background  : 'var(--bg-card)',
                border      : '1px solid var(--border)',
                borderRadius: '3px',
                fontFamily  : 'Barlow Condensed, sans-serif',
                fontSize    : '0.72rem',
                color       : 'var(--text-secondary)',
                padding     : '1px 6px',
              }}>
                {s}
              </span>
            ))}
            {msg.cached && (
              <span style={{
                fontFamily: 'Barlow Condensed, sans-serif',
                fontSize  : '0.72rem',
                color     : 'var(--text-muted)',
                fontStyle : 'italic',
              }}>
                (cached)
              </span>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

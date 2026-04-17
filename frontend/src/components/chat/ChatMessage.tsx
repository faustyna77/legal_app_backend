import type { ChatTurn } from '../../types'

interface ChatMessageProps {
  turn: ChatTurn
}

export function ChatMessage({ turn }: ChatMessageProps) {
  return (
    <div className="chat-turn">
      <p className="q">P: {turn.question}</p>
      <p className="a">O: {turn.answer}</p>
      {turn.evidence_quotes.length > 0 && (
        <div className="evidence-list">
          {turn.evidence_quotes.map((quote, i) => (
            <p key={`${turn.id}-${i}`} className="quote">„{quote}"</p>
          ))}
        </div>
      )}
    </div>
  )
}

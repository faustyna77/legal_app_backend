interface AnswerBoxProps {
  answer: string
}

export function AnswerBox({ answer }: AnswerBoxProps) {
  return <div className="answer-box">{answer}</div>
}

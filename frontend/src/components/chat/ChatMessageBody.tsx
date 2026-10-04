import { Link } from 'react-router-dom'

import { type Inline, parseReply } from './chatText'

const LINK_CLASS =
  'font-semibold text-brand-700 underline decoration-brand-300 underline-offset-2 hover:text-brand-800'

function InlineParts({ parts }: { parts: Inline[] }) {
  return (
    <>
      {parts.map((part, index) => {
        if (part.kind === 'bold') {
          return (
            <strong key={index} className="font-bold">
              {part.text}
            </strong>
          )
        }
        if (part.kind === 'link') {
          return part.internal ? (
            <Link key={index} to={part.href} className={LINK_CLASS}>
              {part.text}
            </Link>
          ) : (
            <a key={index} href={part.href} target="_blank" rel="noopener noreferrer" className={LINK_CLASS}>
              {part.text}
            </a>
          )
        }
        return <span key={index}>{part.text}</span>
      })}
    </>
  )
}

/** Renders a bot reply. Text is always drawn as React text nodes, never as HTML. */
export default function ChatMessageBody({ text }: { text: string }) {
  const blocks = parseReply(text, window.location.origin)
  return (
    <div className="space-y-2 [overflow-wrap:anywhere]">
      {blocks.map((block, index) => {
        if (block.kind === 'ordered') {
          return (
            <ol key={index} className="list-decimal space-y-1 pl-5">
              {block.items.map((item, itemIndex) => (
                <li key={itemIndex}>
                  <InlineParts parts={item} />
                </li>
              ))}
            </ol>
          )
        }
        if (block.kind === 'bullets') {
          return (
            <ul key={index} className="list-disc space-y-1 pl-5">
              {block.items.map((item, itemIndex) => (
                <li key={itemIndex}>
                  <InlineParts parts={item} />
                </li>
              ))}
            </ul>
          )
        }
        return (
          <p key={index}>
            {block.lines.map((line, lineIndex) => (
              <span key={lineIndex}>
                {lineIndex > 0 && <br />}
                <InlineParts parts={line} />
              </span>
            ))}
          </p>
        )
      })}
    </div>
  )
}

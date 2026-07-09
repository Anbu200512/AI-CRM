import { Bot } from 'lucide-react'

export function TypingIndicator() {
  return (
    <div className="flex gap-2.5">
      <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-primary-400 to-primary-600 text-white flex items-center justify-center flex-shrink-0 shadow-sm">
        <Bot size={17} />
      </div>
      <div className="px-4 py-3 rounded-2xl rounded-bl-sm bg-gray-100 dark:bg-gray-800 flex items-center gap-1.5">
        <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-typing-dot" style={{ animationDelay: '0ms' }} />
        <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-typing-dot" style={{ animationDelay: '150ms' }} />
        <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-typing-dot" style={{ animationDelay: '300ms' }} />
      </div>
    </div>
  )
}

export function AssistantMessage({ content }) {
  const lines = content.split('\n')

  return (
    <div className="space-y-0.5 text-sm leading-relaxed">
      {lines.map((line, i) => {
        if (!line.trim()) return <div key={i} className="h-2" />

        if (/^[🎯📋✅🔍📅🔬💊📌💡🏥⚠️]/.test(line)) {
          return (
            <p key={i} className="font-semibold text-gray-900 dark:text-white pt-1">
              {line}
            </p>
          )
        }

        if (line.startsWith('✓') || line.startsWith('✔')) {
          return (
            <div key={i} className="flex items-start gap-2">
              <span className="text-emerald-500 font-bold mt-0.5 flex-shrink-0">✓</span>
              <span className="text-gray-800 dark:text-gray-200">{line.slice(1).trim()}</span>
            </div>
          )
        }

        if (line.startsWith('•') || line.startsWith('-')) {
          return (
            <div key={i} className="flex items-start gap-2 pl-1">
              <span className="text-primary-500 mt-1.5 flex-shrink-0 text-xs">●</span>
              <span className="text-gray-700 dark:text-gray-300">{line.replace(/^[•\-]\s*/, '')}</span>
            </div>
          )
        }

        if (/^\d+\./.test(line)) {
          const match = line.match(/^(\d+)\.\s*(.*)$/)
          if (match) {
            return (
              <div key={i} className="flex items-start gap-2.5">
                <span className="w-5 h-5 rounded-full bg-primary-100 dark:bg-primary-900/30 text-primary-600 dark:text-primary-300 text-xs font-semibold flex items-center justify-center flex-shrink-0 mt-0.5">
                  {match[1]}
                </span>
                <span className="text-gray-800 dark:text-gray-200 text-sm">{match[2]}</span>
              </div>
            )
          }
        }

        if (line.startsWith('   ') || line.startsWith('\t')) {
          return (
            <p key={i} className="pl-7 text-xs text-gray-500 dark:text-gray-400">
              {line.trim()}
            </p>
          )
        }

        return <p key={i} className="text-gray-800 dark:text-gray-200">{line}</p>
      })}
    </div>
  )
}

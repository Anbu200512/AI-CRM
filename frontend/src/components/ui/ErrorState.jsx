import { AlertTriangle, RefreshCw } from 'lucide-react'

export default function ErrorState({ message = 'Something went wrong', onRetry }) {
  return (
    <div className="flex flex-col items-center justify-center py-12 text-center">
      <div className="p-4 rounded-2xl bg-red-50 dark:bg-red-900/30 mb-4">
        <AlertTriangle size={40} className="text-red-500" />
      </div>
      <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-1">Error</h3>
      <p className="text-sm text-gray-500 dark:text-gray-400 max-w-xs mb-4">{message}</p>
      {onRetry && (
        <button onClick={onRetry} className="btn-secondary flex items-center gap-2">
          <RefreshCw size={16} /> Try Again
        </button>
      )}
    </div>
  )
}

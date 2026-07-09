import { ClipboardList } from 'lucide-react'

export default function EmptyState({ title = 'No data found', description = 'There are no records to display.', action }) {
  return (
    <div className="flex flex-col items-center justify-center py-12 text-center">
      <div className="p-4 rounded-2xl bg-gray-100 dark:bg-gray-800 mb-4">
        <ClipboardList size={40} className="text-gray-400" />
      </div>
      <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-1">{title}</h3>
      <p className="text-sm text-gray-500 dark:text-gray-400 max-w-xs">{description}</p>
      {action && <div className="mt-4">{action}</div>}
    </div>
  )
}

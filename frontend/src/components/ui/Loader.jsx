export default function Loader({ fullPage = false }) {
  const content = (
    <div className="flex items-center justify-center gap-2 text-primary-600">
      <svg className="animate-spin h-6 w-6" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
      </svg>
      <span className="text-sm font-medium">Loading...</span>
    </div>
  )

  if (fullPage) return <div className="min-h-screen flex items-center justify-center">{content}</div>
  return <div className="py-12">{content}</div>
}

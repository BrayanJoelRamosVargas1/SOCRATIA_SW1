import * as React from "react"
export function Badge({ className, variant, ...props }: React.HTMLAttributes<HTMLSpanElement> & { variant?: string }) {
  return <span className={`px-2 py-1 text-xs rounded-full bg-gray-100 ${className || ''}`} {...props} />
}

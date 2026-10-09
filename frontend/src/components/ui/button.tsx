import * as React from "react"
export function Button({ ...props }: React.ButtonHTMLAttributes<HTMLButtonElement> & { asChild?: boolean, variant?: string, size?: string }) {
  return <button {...props} className={`px-4 py-2 bg-blue-500 text-white rounded ${props.className || ''}`} />
}

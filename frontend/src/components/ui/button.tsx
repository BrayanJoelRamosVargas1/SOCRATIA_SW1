import * as React from "react";
type ButtonProps = React.ButtonHTMLAttributes<HTMLButtonElement> & { asChild?: boolean; variant?: string; size?: string };
export function Button({className = "", asChild, variant = "default", size, children, ...props}: ButtonProps) {
  const style = `ui-button ui-button-${variant} ${size ? `ui-button-${size}` : ""} ${className}`;
  if (asChild && React.isValidElement<{className?:string}>(children)) return React.cloneElement(children,{...props,className:`${style} ${children.props.className ?? ""}`});
  return <button type="button" {...props} className={style}>{children}</button>;
}

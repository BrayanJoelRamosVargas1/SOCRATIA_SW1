import * as React from "react";
export function Badge({className = "",variant = "default",...props}: React.HTMLAttributes<HTMLSpanElement> & {variant?:string}) {return <span className={`ui-badge ui-badge-${variant} ${className}`} {...props}/>;}

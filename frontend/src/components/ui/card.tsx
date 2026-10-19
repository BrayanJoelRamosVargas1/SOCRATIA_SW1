import * as React from "react";
export function Card({className = "",...props}: React.HTMLAttributes<HTMLDivElement>) {return <div className={`ui-card ${className}`} {...props}/>;}
export function CardHeader({className = "",...props}: React.HTMLAttributes<HTMLDivElement>) {return <div className={`ui-card-header ${className}`} {...props}/>;}
export function CardTitle({className = "",...props}: React.HTMLAttributes<HTMLHeadingElement>) {return <h3 className={`ui-card-title ${className}`} {...props}/>;}
export function CardDescription({className = "",...props}: React.HTMLAttributes<HTMLParagraphElement>) {return <p className={`ui-card-description ${className}`} {...props}/>;}
export function CardContent({className = "",...props}: React.HTMLAttributes<HTMLDivElement>) {return <div className={`ui-card-content ${className}`} {...props}/>;}

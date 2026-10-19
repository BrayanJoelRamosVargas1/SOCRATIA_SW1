export function LoadingSkeleton({label,rows=3}:{label:string;rows?:number}) {
  return <section className="loading-skeleton" role="status" aria-label={label} aria-busy="true">
    <div className="skeleton-bar skeleton-heading" aria-hidden="true"/>
    <p>{label}</p>
    {Array.from({length:rows},(_,index)=><div key={index} className="skeleton-card" aria-hidden="true">
      <div className="skeleton-bar" style={{width:`${70-index*8}%`}}/>
      <div className="skeleton-bar skeleton-secondary"/>
    </div>)}
  </section>;
}

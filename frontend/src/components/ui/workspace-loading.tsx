import { AppSidebar } from "@/components/layout/app-sidebar";
import { LoadingSkeleton } from "./loading-skeleton";

export function WorkspaceLoading({active,label}:{active:"documents"|"simulations"|"history"|"dashboard";label:string}) {
  return <main className="dashboard-layout"><AppSidebar active={active}/><section className="dashboard-content"><LoadingSkeleton label={label}/></section></main>;
}

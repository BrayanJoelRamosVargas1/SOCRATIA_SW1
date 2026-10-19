import { apiRequest } from "@/lib/api";
export type PreparationTask={id:string;document_id:string;kind:"process"|"questions"|"presentation";status:"QUEUED"|"RUNNING"|"SUCCEEDED"|"FAILED"|"INTERRUPTED";error_code:string|null;elapsed_ms:number|null;duration_minutes:number};
export const taskIsActive=(task:PreparationTask)=>["QUEUED","RUNNING"].includes(task.status);
export const listPreparationTasks=(id:string)=>apiRequest<PreparationTask[]>(`/documents/${id}/tasks`);
export function submitPreparationTask(id:string,kind:PreparationTask["kind"],durationMinutes=15,regenerate=false){
 return apiRequest<PreparationTask>(`/documents/${id}/tasks`,{method:"POST",body:JSON.stringify({kind,request_key:crypto.randomUUID(),duration_minutes:durationMinutes,regenerate})});
}

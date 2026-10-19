import { apiRequest } from "./api";

export function warmNavigation(href:string) {
  const connection=(navigator as Navigator & {connection?:{saveData?:boolean;effectiveType?:string}}).connection;
  if(connection?.saveData || ["slow-2g","2g"].includes(connection?.effectiveType??""))return;
  const path:Record<string,string>={"/documents":"/documents","/simulations":"/simulations","/profile":"/profile","/subscription":"/subscription"};
  // Intent-driven reads only. Never generate questions, acquire devices or download models.
  void apiRequest("/profile").catch(()=>undefined);
  if(path[href] && path[href]!=="/profile")void apiRequest(path[href]).catch(()=>undefined);
}

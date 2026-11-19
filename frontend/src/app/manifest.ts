import type { MetadataRoute } from "next";
export default function manifest(): MetadataRoute.Manifest {
  return {name:"Socratia · Prepara tu defensa",short_name:"Socratia",lang:"es",
    start_url:"/documents",scope:"/",display:"standalone",background_color:"#f4f7f6",theme_color:"#167768",
    icons:[{src:"/icon-192.png",sizes:"192x192",type:"image/png"},{src:"/icon-512.png",sizes:"512x512",type:"image/png"}]};
}

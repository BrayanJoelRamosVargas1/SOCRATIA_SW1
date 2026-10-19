import type {Landmark} from "./practice-signals";

export type CameraQuality = {
  lighting: "unknown" | "dim" | "bright" | "backlit" | "usable";
  brightness: number | null;
  faceBrightness: number | null;
  faces: number | null;
  freshness: "waiting" | "live" | "stale";
};
export const EMPTY_QUALITY: CameraQuality = {lighting:"unknown",brightness:null,faceBrightness:null,faces:null,freshness:"waiting"};

// Exposure is measured from luminance, independently of skin color or clothing.
// A small canvas stays in the browser; no image is retained or uploaded here.
export function measureExposure(pixels: Uint8ClampedArray, width: number, height: number, face: Landmark[] = []): Pick<CameraQuality,"lighting"|"brightness"|"faceBrightness"> {
  if (width < 1 || height < 1 || pixels.length !== width*height*4) return {lighting:"unknown",brightness:null,faceBrightness:null};
  let sum=0,clipped=0,faceSum=0,facePixels=0;
  const outline=[face[10],face[152],face[234],face[454]];
  const valid=outline.every(p=>p && Number.isFinite(p.x) && Number.isFinite(p.y));
  const minX=valid ? Math.min(...outline.map(p=>p.x))*width : 0;
  const maxX=valid ? Math.max(...outline.map(p=>p.x))*width : 0;
  const minY=valid ? Math.min(...outline.map(p=>p.y))*height : 0;
  const maxY=valid ? Math.max(...outline.map(p=>p.y))*height : 0;
  for(let y=0;y<height;y++)for(let x=0;x<width;x++){
    const i=(y*width+x)*4;
    const value=.2126*pixels[i]+.7152*pixels[i+1]+.0722*pixels[i+2];
    sum+=value;if(value>245)clipped++;
    if(valid && x>=minX && x<=maxX && y>=minY && y<=maxY){faceSum+=value;facePixels++;}
  }
  const brightness=sum/(width*height), faceBrightness=facePixels>4 ? faceSum/facePixels : null;
  const lighting=faceBrightness!==null && faceBrightness<75 && brightness-faceBrightness>45 ? "backlit" : (faceBrightness??brightness)<40 ? "dim" : (faceBrightness??brightness)>225 && clipped/(width*height)>.4 ? "bright" : "usable";
  return {lighting,brightness:Math.round(brightness),faceBrightness:faceBrightness===null ? null : Math.round(faceBrightness)};
}

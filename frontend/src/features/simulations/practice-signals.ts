export type Landmark = { x: number; y: number; visibility?: number; presence?: number };
export type VisualSignals = { present: boolean; reliable: boolean; shoulderTilt: number | null; centered: boolean | null; framing: "near" | "far" | "ready" | "unknown"; handsVisible: number | null; handsNearFace?: number | null };
export const EMPTY_SIGNALS: VisualSignals = { present: false, reliable: false, shoulderTilt: null, centered: null, framing: "unknown", handsVisible: null, handsNearFace: null };
function visible(point: Landmark | undefined): point is Landmark {
  return !!point && Number.isFinite(point.x) && Number.isFinite(point.y) && point.x >= 0 && point.x <= 1 && point.y >= 0 && point.y <= 1 && (point.visibility ?? 0) >= .65 && (point.presence ?? 1) >= .65;
}
export function measurePose(points: Landmark[], aspectRatio = 4 / 3): VisualSignals {
  const nose = points[0], left = points[11], right = points[12];
  // An isolated landmark can be a tracking artifact; require two body anchors.
  const present = [nose,left,right].filter(visible).length>=2;
  if (!visible(left) || !visible(right) || !visible(nose)) return {...EMPTY_SIGNALS, present};
  const span = Math.abs(left.x - right.x);
  if (span < .06) return {...EMPTY_SIGNALS, present};
  const shoulderTilt = Math.atan2(Math.abs(left.y - right.y), span * (Number.isFinite(aspectRatio) && aspectRatio > 0 ? aspectRatio : 4 / 3)) * 180 / Math.PI;
  const center = (left.x + right.x) / 2;
  return { present: true, reliable: true, shoulderTilt: Math.round(shoulderTilt * 10) / 10, centered: Math.abs(center - .5) < .18, framing: span > .68 ? "near" : span < .20 ? "far" : "ready", handsVisible: Number(visible(points[15])) + Number(visible(points[16])), handsNearFace: [points[15],points[16]].filter(point => visible(point) && Math.hypot((point.x-nose.x)*aspectRatio,point.y-nose.y)<span*aspectRatio*.35).length };
}
export function analyzeTranscript(text: string) {
  const words = text.toLocaleLowerCase("es").match(/[\p{L}]+/gu) ?? [];
  const fillers: string[] = [];
  const pattern = /(?:^|[^\p{L}])(eh+|em+|mmm+|o sea|digamos)(?=$|[^\p{L}])/giu;
  for (const match of text.matchAll(pattern)) fillers.push(match[1].toLocaleLowerCase("es"));
  const repetitions = words.slice(1).filter((word, index) => word === words[index]);
  return { wordCount: words.length, fillers, repetitions };
}

export type GazeReference = { horizontal: number; vertical: number; yaw: number; pitch: number };
export type FaceSignals = {
  detected: boolean; eyes: "open" | "closed" | "unknown";
  direction: "camera" | "away" | "unknown"; headTilt: number | null;
  gaze: GazeReference | null; calibrated: boolean; framing?: "near" | "far" | "cropped" | "ready" | "unknown";
  reason: "no_face" | "eyes_closed" | "no_iris" | "head_turned" | "eyes_away" | "centered" | "borderline";
};
export const EMPTY_FACE: FaceSignals = {detected:false, eyes:"unknown", direction:"unknown", headTilt:null, gaze:null, calibrated:false, framing:"unknown", reason:"no_face"};
export function measureFace(points: Landmark[], blends: {categoryName:string; score:number}[] = [], aspectRatio = 4/3, reference: GazeReference | null = null): FaceSignals {
  const valid = (p: Landmark | undefined): p is Landmark => !!p && Number.isFinite(p.x) && Number.isFinite(p.y) && p.x >= 0 && p.x <= 1 && p.y >= 0 && p.y <= 1;
  const left=points[33], right=points[263], nose=points[1];
  if (!valid(left) || !valid(right) || !valid(nose)) return {...EMPTY_FACE};
  const span=Math.abs(right.x-left.x);
  if (span < .035) return {...EMPTY_FACE};
  const scores = new Map(blends.map(item => [item.categoryName,item.score]));
  const blinkLeft=scores.get("eyeBlinkLeft"), blinkRight=scores.get("eyeBlinkRight");
  const eyes=blinkLeft === undefined || blinkRight === undefined ? "unknown" : blinkLeft > .55 && blinkRight > .55 ? "closed" : "open";
  const ratio=Number.isFinite(aspectRatio) && aspectRatio > 0 ? aspectRatio : 4/3;
  const ex=(right.x-left.x)*ratio,ey=right.y-left.y;
  const eyeLength2=ex*ex+ey*ey;
  const nx=(nose.x-(left.x+right.x)/2)*ratio,ny=nose.y-(left.y+right.y)/2;
  const yaw=(nx*ex+ny*ey)/eyeLength2;
  const mouth=points[17];
  const mouthY=valid(mouth) ? ((mouth.x-(left.x+right.x)/2)*ratio*(-ey)+(mouth.y-(left.y+right.y)/2)*ex) : 0;
  const pitch=mouthY>.001 ? (nx*(-ey)+ny*ex)/mouthY : .5;
  const forehead=points[10],chin=points[152],edgeLeft=points[234],edgeRight=points[454];
  const outline=[forehead,chin,edgeLeft,edgeRight];
  const framing: NonNullable<FaceSignals["framing"]> = !outline.every(valid) ? "unknown" : outline.some(point => point.x<.025 || point.x>.975 || point.y<.025 || point.y>.975) ? "cropped" : span>.32 ? "near" : span<.09 ? "far" : "ready";
  const base: FaceSignals = {detected:true, framing, eyes, direction:"unknown", headTilt:Math.round(Math.atan2(Math.abs(left.y-right.y),span*ratio)*180/Math.PI),gaze:null, calibrated:!!reference,reason:eyes === "closed" ? "eyes_closed" : "no_iris"};
  // Head orientation and iris position are separate: looking sideways with a
  // still head must not pass as camera contact. Missing iris data never passes.
  if (Math.abs(yaw-(reference?.yaw ?? 0))>.16 || Math.abs(pitch-(reference?.pitch ?? .55))>(reference ? .14 : .25)) return {...base,direction:eyes === "closed" ? "unknown" : "away",reason:"head_turned"};
  function irisPosition(a: number,b: number,center:number,top:number,bottom:number) {
    const start=points[a], end=points[b], iris=points[center], upper=points[top],lower=points[bottom];
    if (![start,end,iris,upper,lower].every(valid)) return null;
    const dx=(end.x-start.x)*ratio, dy=end.y-start.y;
    const length2=dx*dx+dy*dy;
    if (length2<.000025) return null;
    const horizontal=((iris.x-start.x)*ratio*dx+(iris.y-start.y)*dy)/length2;
    const vertical=((iris.x-(upper.x+lower.x)/2)*ratio*(-dy)+(iris.y-(upper.y+lower.y)/2)*dx)/length2;
    if (horizontal < -.1 || horizontal > 1.1 || Math.abs(vertical)>.5) return null;
    return {horizontal,vertical};
  }
  const a=irisPosition(33,133,468,159,145), b=irisPosition(362,263,473,386,374);
  if (!a || !b || eyes !== "open") return base;
  const gaze={horizontal:(a.horizontal+b.horizontal)/2,vertical:(a.vertical+b.vertical)/2,yaw,pitch};
  const dx=Math.abs(gaze.horizontal-(reference?.horizontal ?? .5)), dy=Math.abs(gaze.vertical-(reference?.vertical ?? 0));
  const lookScore=Math.max(...["eyeLookDownLeft","eyeLookDownRight","eyeLookUpLeft","eyeLookUpRight","eyeLookOutLeft","eyeLookOutRight"].map(key => scores.get(key) ?? 0));
  const away=dx>(reference ? .055 : .065) || dy>(reference ? .022 : .025) || lookScore>.4;
  const centered=dx<(reference ? .035 : .045) && dy<(reference ? .015 : .018) && lookScore<.3;
  return {...base,gaze,direction:away ? "away" : centered ? "camera" : "unknown",reason:away ? "eyes_away" : centered ? "centered" : "borderline"};
}
export function measureTorso(points: Landmark[], aspectRatio=4/3): number | null {
  if (![points[11],points[12],points[23],points[24]].every(visible)) return null;
  const shoulders={x:(points[11].x+points[12].x)/2,y:(points[11].y+points[12].y)/2};
  const hips={x:(points[23].x+points[24].x)/2,y:(points[23].y+points[24].y)/2};
  if (hips.y-shoulders.y < .08) return null;
  const ratio=Number.isFinite(aspectRatio) && aspectRatio>0 ? aspectRatio : 4/3;
  return Math.round(Math.atan2(Math.abs(shoulders.x-hips.x)*ratio,hips.y-shoulders.y)*180/Math.PI);
}

export function presenceFromSignals(pose: VisualSignals, face: FaceSignals): "present" | "absent" {
  return pose.present || face.detected ? "present" : "absent";
}

export function torsoFitsFrame(points: Landmark[], aspectRatio=4/3): boolean {
  const left=points[11],right=points[12];
  if(!visible(left)||!visible(right))return false;
  const span=Math.abs(left.x-right.x);
  // A face/neck crop is insufficient evidence of clothing. Require room
  // below the shoulders proportional to their pixel width, not a skin color.
  return span>=.12 && Math.max(left.y,right.y)+span*aspectRatio*.4<=.97;
}

// Sound activity only: this does not transcribe or decide whether an answer is correct.
export class TurnEndDetector {
  private previous:number;
  private started:number;
  private activityMs=0;
  private lastSound:number;
  constructor(now:number){this.previous=now;this.started=now;this.lastSound=now;}
  get hasSpeech(){return this.activityMs>=600;}
  pause(now:number){this.started+=Math.max(0,now-this.previous);this.previous=now;this.lastSound=now;}
  update(rms:number,now:number):"listening"|"submit"|"empty" {
    const dt=Math.max(0,Math.min(250,now-this.previous));this.previous=now;
    if(Number.isFinite(rms) && rms>.025){this.activityMs+=dt;this.lastSound=now;}
    if(this.activityMs>=600 && now-this.lastSound>=4000)return "submit";
    if(now-this.started>=20000 && this.activityMs<600)return "empty";
    return "listening";
  }
}

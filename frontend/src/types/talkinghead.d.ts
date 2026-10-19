declare module "@/vendor/talkinghead.mjs" {
  export class TalkingHead {
    constructor(node: HTMLElement, options: Record<string, unknown>);
    isSpeaking: boolean;
    audioCtx: AudioContext;
    mtAvatar: Record<string, { newvalue: number; needsUpdate: boolean }>;
    showAvatar(options: Record<string, unknown>, onprogress?: (event: ProgressEvent) => void): Promise<void>;
    start(): void;
    stop(): void;
    dispose(): void;
    lookAtCamera(duration: number): void;
    makeEyeContact(duration: number): void;
    speakWithHands(delay: number, probability: number): void;
  }
}

/* global Vision */
// CPU inference lives off the UI thread. Frames stay on this device.
let pose, face, busy = false;
self.onmessage = async ({data}) => {
  if (data.type === 'init') {
    try {
      importScripts('vision_bundle.js');
      const files = await Vision.FilesetResolver.forVisionTasks(new URL('wasm', self.location.href).href);
      const errors = {};
      try {
        pose = await Vision.PoseLandmarker.createFromOptions(files, {
          baseOptions:{modelAssetPath:new URL('models/pose.task', self.location.href).href},
          runningMode:'VIDEO',numPoses:1,minPoseDetectionConfidence:.5,minTrackingConfidence:.5,
        });
      } catch { errors.pose = true; }
      try {
        face = await Vision.FaceLandmarker.createFromOptions(files, {
          baseOptions:{modelAssetPath:new URL('models/face.task', self.location.href).href},
          runningMode:'VIDEO',numFaces:2,outputFaceBlendshapes:true,minFaceDetectionConfidence:.5,minTrackingConfidence:.5,
        });
      } catch { errors.face = true; }
      if (!pose && !face) throw Error('detectors-unavailable');
      self.postMessage({type:'ready',pose:Boolean(pose),face:Boolean(face),errors});
    } catch { self.postMessage({type:'error',reason:'detectors-unavailable'}); }
    return;
  }
  if (data.type !== 'frame') return;
  const bitmap = data.bitmap;
  if (busy) { bitmap.close(); self.postMessage({type:'frame-error',id:data.id}); return; }
  busy = true;
  try {
    const started = performance.now();
    let poseResult = null, faceResult = null;
    try { if (pose) poseResult = pose.detectForVideo(bitmap, data.timestamp); } catch { /* reported through null result */ }
    try { if (face) faceResult = face.detectForVideo(bitmap, data.timestamp); } catch { /* reported through null result */ }
    self.postMessage({type:'result',id:data.id,pose:poseResult,face:faceResult,elapsed:performance.now()-started});
  } catch { self.postMessage({type:'frame-error',id:data.id}); }
  finally { bitmap.close(); busy = false; }
};

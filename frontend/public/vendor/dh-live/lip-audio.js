// Decode at the engine rate without opening a speaker or microphone device.
window.socratiaLipAudio = async (input) => {
  const rate = 16000;
  const decoder = new OfflineAudioContext(1, 1, rate);
  const buffer = await decoder.decodeAudioData(input.slice(0));
  const wav = new ArrayBuffer(44 + buffer.length * 2);
  const view = new DataView(wav);
  const label = (at, value) => [...value].forEach((c, i) => view.setUint8(at + i, c.charCodeAt(0)));
  label(0,'RIFF'); view.setUint32(4,wav.byteLength-8,true); label(8,'WAVE'); label(12,'fmt ');
  view.setUint32(16,16,true); view.setUint16(20,1,true); view.setUint16(22,1,true);
  view.setUint32(24,rate,true); view.setUint32(28,rate*2,true);
  view.setUint16(32,2,true); view.setUint16(34,16,true);
  label(36,'data'); view.setUint32(40,buffer.length*2,true);
  const channels = Array.from({length:buffer.numberOfChannels},(_,i)=>buffer.getChannelData(i));
  for (let i=0; i<buffer.length; i++) {
    const sample = channels.reduce((sum,channel)=>sum+channel[i],0)/channels.length;
    view.setInt16(44+i*2,Math.max(-1,Math.min(1,sample))*32767,true);
  }
  return wav;
};

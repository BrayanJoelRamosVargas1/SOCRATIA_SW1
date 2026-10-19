import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
const input = new ArrayBuffer(80);
const context = vm.createContext({window:{},ArrayBuffer,DataView,
  OfflineAudioContext:class {
    constructor(_channels,_length,rate){assert.equal(rate,16000);}
    async decodeAudioData(bytes){
      assert.notEqual(bytes,input,'decoding must not detach the playback data');
      return {length:4,numberOfChannels:2,getChannelData:i=>i ? [1,0,-1,.5] : [1,1,-1,-.5]};
    }
  },
});
vm.runInContext(readFileSync(new URL('../public/vendor/dh-live/lip-audio.js',import.meta.url),'utf8'),context);
const output = await context.window.socratiaLipAudio(input);
const view = new DataView(output);
assert.equal(output.byteLength,52);
assert.equal(view.getUint16(22,true),1);
assert.equal(view.getUint32(24,true),16000);
assert.equal(view.getUint32(28,true),32000);
assert.equal(view.getUint32(40,true),8);
assert.deepEqual([0,1,2,3].map(i=>view.getInt16(44+i*2,true)),[32767,16383,-32767,0]);
console.log('PASS: engine-rate decoding, mono PCM16 WAV and preserved playback input.');

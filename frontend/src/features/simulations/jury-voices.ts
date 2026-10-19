// Prefer three distinct Spanish identities when the browser provides them.
export function juryVoice(voices: SpeechSynthesisVoice[], index: number) {
  const spanish=voices.filter(voice=>voice.lang.toLowerCase().startsWith("es"));
  const unique=spanish.filter((voice,at)=>spanish.findIndex(other=>(other.voiceURI||other.name)===(voice.voiceURI||voice.name))===at);
  const female=/helena|laura|elvira|dalia|sabina|paulina|monica|mónica|dora/i;
  const male=/pablo|alvaro|álvaro|jorge|diego|raul|raúl|andres|andrés|antonio|carlos|juan|alex/i;
  const alex=unique.find(voice=>male.test(voice.name))??unique.find(voice=>!female.test(voice.name))??unique[0];
  const elena=unique.find(voice=>voice!==alex && female.test(voice.name))??unique.find(voice=>voice!==alex)??alex;
  const daniel=unique.find(voice=>voice!==alex && voice!==elena && male.test(voice.name))??unique.find(voice=>voice!==alex && voice!==elena)??alex;
  const slot=((index%3)+3)%3;
  const profile=[{voice:alex,rate:.93,pitch:.88},{voice:elena,rate:1,pitch:1.12},{voice:daniel,rate:.98,pitch:.72}][slot];
  return {...profile,distinctVoice:unique.length>=3};
}

// Names differ between OS/browser voice catalogs. Prefer a known Spanish voice
// matching the demo person; never fall back to an English voice for Spanish text.
export function juryVoice(voices: SpeechSynthesisVoice[], index: number) {
  const spanish = voices.filter(voice => voice.lang.toLowerCase().startsWith("es"));
  const female = /helena|laura|elvira|dalia|sabina|paulina|monica|mónica/i;
  const male = /pablo|alvaro|álvaro|jorge|diego|raul|raúl|andres|andrés|antonio|carlos|juan/i;
  const normalized = ((index % 3) + 3) % 3;
  const voice = spanish.find(item => (normalized === 1 ? female : male).test(item.name)) ?? spanish[0];
  return {voice, rate: normalized === 0 ? .92 : normalized === 1 ? .98 : 1.02, pitch: normalized === 0 ? .94 : normalized === 1 ? 1 : 1.04};
}

export const toggleTTS = (index, activeTTS, setActiveTTS) => {
  // If speech synthesis is not available, return
  if (!window.speechSynthesis) return;
  
  // If this is the currently active TTS segment
  if (activeTTS === index) {
    // Stop the speech
    window.speechSynthesis.cancel();
    setActiveTTS(null);
    return;
  }
  
  // If another TTS is active, stop it
  if (activeTTS !== null) {
    window.speechSynthesis.cancel();
  }
  
  // Just set the active TTS index - the component will handle the speech
  setActiveTTS(index);
};

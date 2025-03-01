import React, { useState, useEffect, useRef } from 'react';

const HighlightedText = ({ text, activeTTS, isPlaying }) => {
  const [currentWordIndex, setCurrentWordIndex] = useState(-1);
  const words = text.split(/\s+/);
  const utteranceRef = useRef(null);
  
  useEffect(() => {
    if (!isPlaying) {
      setCurrentWordIndex(-1);
      return;
    }
    
    // Initialize speech synthesis with word boundary detection
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 0.9; // Match your existing rate
    
    // Track word boundaries
    utterance.onboundary = (event) => {
      if (event.name === 'word') {
        // Calculate which word we're on
        const upToIndex = text.substring(0, event.charIndex).split(/\s+/).length - 1;
        setCurrentWordIndex(upToIndex);
      }
    };
    
    utterance.onend = () => {
      setCurrentWordIndex(-1);
    };
    
    // Store reference and start speaking
    utteranceRef.current = utterance;
    window.speechSynthesis.speak(utterance);
    
    return () => {
      window.speechSynthesis.cancel();
    };
  }, [isPlaying, text]);
  
  return (
    <p>
      {words.map((word, index) => (
        <React.Fragment key={index}>
          <span 
            className={currentWordIndex === index ? "highlighted-word" : ""}
          >
            {word}
          </span>
          {index < words.length - 1 ? ' ' : ''}
        </React.Fragment>
      ))}
    </p>
  );
};

export default HighlightedText;

import React, { useState, useEffect, useRef } from 'react';

// Helper function to split text into sentences with more natural breaks
function splitIntoSentencesImproved(text) {
  if (!text) return [];
  
  // Split text into sentences based on punctuation
  const results = [];
  // Match sentence ending punctuation followed by space or end of text
  const regex = /[^.!?]+[.!?]+[\s$]?/g;
  let match;
  
  while ((match = regex.exec(text)) !== null) {
    // Get the matched sentence
    let sentence = match[0].trim();
    if (sentence) {
      results.push(sentence);
    }
  }
  
  // Handle any remaining text that wasn't matched
  const matchedText = results.join(' ');
  if (matchedText.length < text.length) {
    const remaining = text.substring(matchedText.length).trim();
    if (remaining) {
      results.push(remaining);
    }
  }
  
  // If no sentences were found, return the entire text as one sentence
  if (results.length === 0 && text.trim()) {
    results.push(text.trim());
  }
  
  return results;
}

// Calculate estimated sentence durations based on content
function calculateSentenceDurations(sentences, totalDuration) {
  if (!sentences.length) return [];
  if (!totalDuration) return sentences.map(() => 2000); // Default 2 seconds per sentence
  
  // Calculate character count and distribution
  const totalChars = sentences.reduce((sum, sentence) => sum + sentence.length, 0);
  const minDuration = 1000; // Minimum 1 second per sentence
  
  return sentences.map(sentence => {
    // Calculate proportional duration based on sentence length
    const proportion = sentence.length / totalChars;
    const duration = Math.max(minDuration, proportion * totalDuration * 1000);
    return duration;
  });
}

const HighlightedText = ({ text, activeTTS, isPlaying, isAITTS, audioRef }) => {
  const [currentHighlight, setCurrentHighlight] = useState(-1);
  const utteranceRef = useRef(null);
  const sentencesRef = useRef([]);
  const sentenceDurationsRef = useRef([]);
  const intervalRef = useRef(null);
  const lastProgressRef = useRef(0);
  const lastUpdateTimeRef = useRef(0);
  
  // Split text by sentences for AI TTS or words for browser TTS
  const segments = isAITTS 
    ? splitIntoSentencesImproved(text) // Use improved function
    : text.split(/\s+/); // Split by words for web TTS
  
  // Cache the segments
  useEffect(() => {
    sentencesRef.current = isAITTS ? segments : segments;
  }, [segments, isAITTS]);
  
  useEffect(() => {
    // Reset highlight when stopped
    if (!isPlaying) {
      setCurrentHighlight(-1);
      
      // Clear any active intervals
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
      
      // Reset references
      lastProgressRef.current = 0;
      lastUpdateTimeRef.current = 0;
      
      return;
    }
    
    // Handle AI TTS highlighting
    if (isAITTS) {
      console.log("Using AI TTS mode for highlighting");
      
      // Set initial highlight to first sentence
      setCurrentHighlight(0);
      
      // Clear previous interval if any
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
      
      // If audio element is provided, use it for timing
      if (audioRef && audioRef.current) {
        console.log("Using audio element for highlighting timing");
        
        // Get the total number of sentences
        const sentenceCount = sentencesRef.current.length;
        
        // Initialize last update time
        lastUpdateTimeRef.current = Date.now();
        
        // Reset progress tracking
        lastProgressRef.current = 0;
        
        // Calculate timing once audio has loaded
        const handleLoadedMetadata = () => {
          if (!audioRef.current) return;
          
          const audioDuration = audioRef.current.duration;
          console.log("Audio duration:", audioDuration);
          
          if (audioDuration && !isNaN(audioDuration) && audioDuration > 0) {
            const durations = calculateSentenceDurations(sentencesRef.current, audioDuration);
            sentenceDurationsRef.current = durations;
            console.log("Calculated sentence durations:", durations);
          }
        };
        
        // Add event listener for metadata loaded
        audioRef.current.addEventListener('loadedmetadata', handleLoadedMetadata);
        
        // Pre-calculate durations if metadata already loaded
        if (audioRef.current.duration && !isNaN(audioRef.current.duration)) {
          handleLoadedMetadata();
        }
        
        // Handle time updates from audio element with hysteresis to prevent too frequent updates
        const handleTimeUpdate = () => {
          if (!audioRef.current) return;
          
          // Get current position and total duration
          const position = audioRef.current.currentTime;
          const duration = audioRef.current.duration;
          
          // Skip if not enough time has passed (30ms minimum between updates)
          const now = Date.now();
          if (now - lastUpdateTimeRef.current < 30) return;
          lastUpdateTimeRef.current = now;
          
          // Skip if progress hasn't changed significantly (0.5% minimum)
          const progress = duration ? position / duration : 0;
          if (Math.abs(progress - lastProgressRef.current) < 0.005) return;
          lastProgressRef.current = progress;
          
          // Calculate which sentence we should be on
          if (duration && duration > 0 && sentenceCount > 0) {
            // Option 1: Simply proportional distribution
            const estimatedPosition = Math.min(
              Math.floor(progress * sentenceCount),
              sentenceCount - 1
            );
            
            // Option 2: Use pre-calculated sentence durations if available
            let advancedPosition = 0;
            if (sentenceDurationsRef.current.length === sentenceCount) {
              let accumulatedTime = 0;
              for (let i = 0; i < sentenceCount; i++) {
                accumulatedTime += sentenceDurationsRef.current[i] / 1000; // Convert ms to s
                if (position <= accumulatedTime) {
                  advancedPosition = i;
                  break;
                }
              }
              // If we've passed all sentences, use the last one
              if (position > accumulatedTime) {
                advancedPosition = sentenceCount - 1;
              }
            }
            
            // Use the advanced position if available, otherwise fall back to proportional
            const finalPosition = sentenceDurationsRef.current.length === sentenceCount ?
              advancedPosition : estimatedPosition;
            
            if (finalPosition !== currentHighlight) {
              console.log(`Highlighting sentence ${finalPosition} at position ${position}s/${duration}s (${(progress*100).toFixed(1)}%)`);
              setCurrentHighlight(finalPosition >= 0 ? finalPosition : 0);
            }
          }
        };
        
        // Add event listener for time updates
        audioRef.current.addEventListener('timeupdate', handleTimeUpdate);
        
        // Also handle audio ending
        const handleEnded = () => {
          setCurrentHighlight(-1);
        };
        
        audioRef.current.addEventListener('ended', handleEnded);
        
        // Clean up when unmounted
        return () => {
          if (audioRef.current) {
            audioRef.current.removeEventListener('timeupdate', handleTimeUpdate);
            audioRef.current.removeEventListener('ended', handleEnded);
            audioRef.current.removeEventListener('loadedmetadata', handleLoadedMetadata);
          }
          if (intervalRef.current) {
            clearInterval(intervalRef.current);
          }
        };
      } else {
        // Fallback to a timer based approach if no audio element
        console.log("Using timer-based highlighting");
        
        let currentIndex = 0;
        const sentenceCount = sentencesRef.current.length;
        
        // Algorithm to estimate reading time: ~275ms per word + 500ms per sentence
        const estimateDuration = (sentence) => {
          const words = sentence.split(/\s+/).length;
          return Math.max(1000, (words * 275) + 500);
        };
        
        // Create an array of timings for each sentence
        const sentenceDurations = sentencesRef.current.map(estimateDuration);
        console.log("Estimated sentence durations:", sentenceDurations);
        
        // Update current sentence using the calculated durations
        const updateHighlight = () => {
          if (currentIndex >= sentenceCount) {
            clearTimeout(intervalRef.current);
            setCurrentHighlight(-1);
            return;
          }
          
          setCurrentHighlight(currentIndex);
          
          // Schedule the next update based on sentence duration
          const duration = sentenceDurations[currentIndex];
          intervalRef.current = setTimeout(() => {
            currentIndex++;
            updateHighlight();
          }, duration);
        };
        
        // Start the first sentence highlight
        updateHighlight();
        
        // Cleanup function
        return () => {
          if (intervalRef.current) {
            clearTimeout(intervalRef.current);
          }
        };
      }
    } else {
      // Handle browser TTS - fix highlighting issues
      console.log("Using browser TTS for highlighting");
      
      // Cancel any existing speech synthesis first
      window.speechSynthesis.cancel();
      
      // Create a new utterance for word boundary detection
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.rate = 0.9;
      
      // Set up boundary detection for word highlighting
      utterance.onboundary = (event) => {
        if (event.name === 'word') {
          // Count words up to this position to determine which to highlight
          const textUpToIndex = text.substring(0, event.charIndex);
          const upToIndex = textUpToIndex.split(/\s+/).length - 1;
          console.log(`Word boundary at char ${event.charIndex}, word index: ${upToIndex}`);
          setCurrentHighlight(upToIndex >= 0 ? upToIndex : 0);
        }
      };
      
      // Reset highlight when done speaking
      utterance.onend = () => {
        console.log("Web speech synthesis ended");
        setCurrentHighlight(-1);
      };
      
      utterance.onerror = (e) => {
        console.error("Speech synthesis error:", e);
        setCurrentHighlight(-1);
      };
      
      // Store reference to the utterance object
      utteranceRef.current = utterance;
      
      // Start speaking using the utterance with our attached event handlers
      try {
        window.speechSynthesis.speak(utteranceRef.current);
      } catch (e) {
        console.error("Failed to start speech synthesis:", e);
      }
      
      // Clean up on unmount or when isPlaying changes
      return () => {
        if (window.speechSynthesis) {
          window.speechSynthesis.cancel();
        }
      };
    }
  }, [isPlaying, isAITTS, text, audioRef]);
  
  return (
    <p>
      {segments.map((segment, index) => (
        <React.Fragment key={index}>
          <span 
            className={currentHighlight === index ? "highlighted-word" : ""}
          >
            {segment}
          </span>
          {index < segments.length - 1 ? ' ' : ''}
        </React.Fragment>
      ))}
    </p>
  );
};

export default HighlightedText;

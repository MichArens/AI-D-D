
/**
 * Utility functions for managing chapter content and navigation
 */

/**
 * Creates a deep copy of an object with new timestamps to force React rerenders
 * @param {Object} obj - Object to clone
 * @returns {Object} Deep cloned object
 */
export const deepCloneWithNewRefs = (obj) => {
  if (obj === null || typeof obj !== 'object') return obj;
  
  // First create a complete deep clone
  const clone = JSON.parse(JSON.stringify(obj));
  
  // Then add unique timestamps to force React to treat this as completely new
  const addTimestamps = (object) => {
    if (object === null || typeof object !== 'object') return;
    
    // Add timestamp to this object
    object._timestamp = Date.now() + Math.random();
    
    // Process all properties
    Object.keys(object).forEach(key => {
      if (object[key] && typeof object[key] === 'object') {
        addTimestamps(object[key]);
      }
    });
  };
  
  addTimestamps(clone);
  return clone;
};

/**
 * Takes a chapter and prepares its content for viewing
 * @param {Object} chapter - Chapter to prepare
 * @param {Array} allSegments - All story segments
 * @returns {Array} Prepared story segments for viewing
 */
export const prepareChapterContent = (chapter, allSegments) => {
  if (!chapter || !allSegments) return [];
  
  // If it's not the current chapter, simply create a summary view
  if (chapter.summary) {
    return [{
      text: chapter.summary,
      image: chapter.image,
      chapterId: chapter.id,
      isChapterSummary: true,
      _timestamp: Date.now() + Math.random()
    }];
  }
  
  // For current chapter, carefully collect all related segments
  const chapterSegments = (chapter.segments || [])
    .filter(idx => idx >= 0 && idx < allSegments.length)
    .map(idx => {
      const segment = allSegments[idx];
      // Create brand new copy with unique timestamp
      const segmentCopy = deepCloneWithNewRefs(segment);
      // Ensure it's associated with this chapter
      segmentCopy.chapterId = chapter.id;
      return segmentCopy;
    });
  
  return chapterSegments;
};

/**
 * Stores a new segment in the appropriate chapter
 * @param {Array} chapters - All chapters
 * @param {Object} segment - New segment to store
 * @param {Number} chapterIndex - Current chapter index
 * @returns {Object} Updated chapter information
 */
export const addSegmentToChapter = (chapters, segment, chapterIndex) => {
  if (!chapters || chapterIndex < 0 || chapterIndex >= chapters.length) {
    return { chapters, allSegments: [] };
  }
  
  // Create fresh copies of everything
  const updatedChapters = deepCloneWithNewRefs(chapters);
  const currentChapter = updatedChapters[chapterIndex];
  
  // Create allSegments array if not present
  const allSegments = [];
  
  // Collect all existing segments first
  updatedChapters.forEach(chapter => {
    (chapter.segments || []).forEach(segIdx => {
      if (chapter.storedSegments && chapter.storedSegments[segIdx]) {
        allSegments.push(deepCloneWithNewRefs(chapter.storedSegments[segIdx]));
      }
    });
  });
  
  // Add the new segment
  const newSegIndex = allSegments.length;
  allSegments.push(deepCloneWithNewRefs(segment));
  
  // Initialize storedSegments if not present
  if (!currentChapter.storedSegments) {
    currentChapter.storedSegments = {};
  }
  
  // Store segment directly in the chapter
  currentChapter.storedSegments[newSegIndex] = deepCloneWithNewRefs(segment);
  
  // Add the index to the chapter's segments array
  if (!currentChapter.segments) {
    currentChapter.segments = [];
  }
  currentChapter.segments.push(newSegIndex);
  
  return {
    chapters: updatedChapters,
    allSegments
  };
};

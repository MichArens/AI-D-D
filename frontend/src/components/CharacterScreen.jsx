import React, { useEffect } from 'react';

const CharacterScreen = ({ gameState, setGameState, characterOptions, handleCharacterChange, handleStartGame, loading, error, areCharactersComplete, setScreen }) => {
  // Function to get a random item from an array
  const getRandomItem = (array) => {
    if (!array || array.length === 0) return "";
    return array[Math.floor(Math.random() * array.length)];
  };

  // Function to generate random name (simple placeholder)
  const generateRandomName = () => {
    const prefixes = ["Ar", "Bel", "Cal", "Dor", "El", "Fae", "Gor", "Hel", "Ir", "Jor", "Kal", "Lum", "Mor", "Nar", "Oth", "Par"];
    const suffixes = ["ian", "ius", "or", "en", "on", "eth", "wyn", "iel", "and", "ara", "ella", "ira", "one", "ade", "ina", "isa"];
    return getRandomItem(prefixes) + getRandomItem(suffixes);
  };

  // Auto-assign random attributes when character options become available
  useEffect(() => {
    if (characterOptions?.races?.length && characterOptions?.classes?.length) {
      // Only proceed if we have options available
      const updatedCharacters = gameState.characters.map(character => {
        // Only assign random values for empty fields
        const updatedCharacter = { ...character };
        
        if (!updatedCharacter.race) {
          updatedCharacter.race = getRandomItem(characterOptions.races);
        }
        
        if (!updatedCharacter.characterClass) {
          updatedCharacter.characterClass = getRandomItem(characterOptions.classes);
        }
        
        if (!updatedCharacter.gender) {
          updatedCharacter.gender = getRandomItem(["Male", "Female"]);
        }
        
        if (!updatedCharacter.name || updatedCharacter.name.trim() === '') {
          updatedCharacter.name = generateRandomName();
        }
        
        return updatedCharacter;
      });
      
      // Update the game state with our randomly generated characters
      setGameState(prevState => ({
        ...prevState,
        characters: updatedCharacters
      }));
    }
  }, [characterOptions, gameState.characters.length]); // Re-run when options change or player count changes

  return (
    <div className="character-screen">
      <h1>Character Creation</h1>
      
      <div className="character-form">
        {gameState.characters.map((character, index) => (
          <div key={index} className="character-card">
            <h3>Player {index + 1}</h3>
            
            <div className="form-group">
              <label>Character Name:</label>
              <input 
                type="text" 
                value={character.name || ''}
                onChange={(e) => handleCharacterChange(index, 'name', e.target.value)}
                placeholder="Enter name"
              />
            </div>
            
            <div className="form-group">
              <label>Race:</label>
              <select 
                value={character.race || ''}
                onChange={(e) => handleCharacterChange(index, 'race', e.target.value)}
              >
                <option value="">Select Race</option>
                {characterOptions?.races?.map(race => (
                  <option key={race} value={race}>{race}</option>
                ))}
              </select>
            </div>
            
            <div className="form-group">
              <label>Class:</label>
              <select 
                value={character.characterClass || ''}
                onChange={(e) => handleCharacterChange(index, 'characterClass', e.target.value)}
              >
                <option value="">Select Class</option>
                {characterOptions?.classes?.map(cls => (
                  <option key={cls} value={cls}>{cls}</option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label>Gender:</label>
              <select
                value={character.gender || ''}
                onChange={(e) => handleCharacterChange(index, 'gender', e.target.value)}
              >
                <option value="">Select Gender</option>
                <option value="Male">Male</option>
                <option value="Female">Female</option>
              </select>
            </div>
          </div>
        ))}
      </div>
      
      <div className="actions">
        <button 
          className="secondary-button" 
          onClick={() => setScreen('setup')}
          disabled={loading}
        >
          Back
        </button>
        <button 
          className="main-button" 
          onClick={handleStartGame}
          disabled={loading || !areCharactersComplete()}
        >
          {loading ? 'Creating Adventure...' : 'Start Adventure!'}
        </button>
      </div>
      
      {error && <div className="error-message">{error}</div>}
      {!areCharactersComplete() && (
        <div className="info-message">All characters must have a name, race, and class.</div>
      )}
    </div>
  );
};

export default CharacterScreen;

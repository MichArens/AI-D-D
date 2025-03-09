import React, { use, useEffect, useState } from 'react';
import { GameScreens } from '../types/game-screens';
import { api } from '../utils/api-service';
import { IGameState, IPlayerCharacter } from '../types/game-types';

interface CharacterScreenProps {
  gameState: IGameState;
  setGameState: React.Dispatch<React.SetStateAction<IGameState>>;
  setScreen: React.Dispatch<React.SetStateAction<GameScreens>>;
}

const CharacterScreen: React.FC<CharacterScreenProps> = ({
  gameState,
  setGameState,
  setScreen,
}) => {
    const [error, setError] = useState<string | null>(null);
    const [loading, setLoading] = useState<boolean>(false);
    const [characterOptions, setCharacterOptions] = useState<{races: string[], classes: string[]} | null>(null);

    useEffect(() => {
        const prepareCharacterOptions = async () => {
            setLoading(true);
            setError(null);
            console.log("Starting setup and fetching character options...");
            
            try {
                let options;
                try {
                options = await api.getCharacterOptions();
                console.log("Received character options:", options);
                } catch (optionsError) {
                console.error("Error fetching character options:", optionsError);
                options = {
                    races: ["Human", "Elf", "Dwarf", "Orc", "Halfling"],
                    classes: ["Warrior", "Mage", "Rogue", "Cleric", "Bard"]
                };
                setError('Using default character options due to API error.');
                }
                
                setCharacterOptions(options);
                
                // Initialize character slots based on player count
                const initialCharacters: IPlayerCharacter[] = Array(gameState.settings?.playerCount || 2).fill(null).map((_, idx) => ({
                name: '',
                race: undefined,
                characterClass: undefined,
                gender: undefined,
                playerIndex: idx,
                icon: undefined
                }));
                
                setGameState(prev => ({
                ...prev,
                characters: initialCharacters
                }));
            } catch (err: any) {
                console.error('Failed to initialize character creation:', err);
                setError(`Failed to initialize character creation: ${err.message || 'Unknown error'}`);
            } finally {
                setLoading(false);
            }
        };

        prepareCharacterOptions();
    }, []);

    const getRandomItem = (array: any[]) => {
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
    }, [characterOptions, gameState.characters.length]);

    const areCharactersComplete = () => {
        return gameState.characters.every(char => 
          char.name && char.race && char.characterClass && char.gender
        );
    };

    const handleCharacterChange = (index: number, field: string, value: any) => {
        setGameState(prev => {
          const newCharacters = [...prev.characters];
          newCharacters[index] = { ...newCharacters[index], [field]: value };
          return { ...prev, characters: newCharacters };
        });
    };

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
              onClick={undefined}
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
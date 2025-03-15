import React, { useState, useRef, useEffect } from 'react';
import { GameScreens } from '../types/game-screens';
import { api } from '../utils/api-service';
import { IGameState } from '../types/game-types';

interface JoinGameScreenProps {
  setScreen: React.Dispatch<React.SetStateAction<GameScreens>>;
}

const JoinGameScreen: React.FC<JoinGameScreenProps> = ({
  setScreen,
}) => {
  // State for the 4 digits
  const [digits, setDigits] = useState(['', '', '', '']);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  
  // Refs for the input fields
  const inputRefs = [
    useRef<HTMLInputElement>(null),
    useRef<HTMLInputElement>(null),
    useRef<HTMLInputElement>(null),
    useRef<HTMLInputElement>(null),
  ];

  // Focus the first input when the component loads
  useEffect(() => {
    inputRefs[0].current?.focus();
  }, []);

  // Handle digit input
  const handleDigitChange = (index: number, value: string) => {
    if (value.length > 1) {
      value = value.slice(0, 1);
    }
    
    if (!/^[0-9]$/.test(value) && value !== '') {
      return;
    }
    
    const newDigits = [...digits];
    newDigits[index] = value;
    setDigits(newDigits);
    
    // Auto-focus to next input if this one is filled
    if (value !== '' && index < 3) {
      inputRefs[index + 1]?.current?.focus();
    }
  };

  // Handle backspace to go back to previous input
  const handleKeyDown = (index: number, e: React.KeyboardEvent) => {
    if (e.key === 'Backspace' && digits[index] === '' && index > 0) {
      inputRefs[index - 1]?.current?.focus();
    }
  };

  const handleJoinGame = async () => {
    const code = digits.join('');
    if (code.length !== 4) {
      setError('Please enter all 4 digits of the session code');
      return;
    }
    
    setLoading(true);
    setError(null);
    
    try {
      // Note: This is just UI for now, actual API integration would go here
      console.log('Joining session with code:', code);
      
      // For demonstration purposes only
      setTimeout(() => {
        setScreen('game');
      }, 1500);
    } catch (err: any) {
      setError(err.message || 'Failed to join game session');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="join-game-screen">
      <h1>Join Existing Game</h1>
      
      <div className="join-form">
        <h2>Enter 4-Digit Session Code</h2>
        
        <div className="code-input-container">
          {[0, 1, 2, 3].map(index => (
            <input
              key={index}
              ref={inputRefs[index]}
              type="text"
              maxLength={1}
              value={digits[index]}
              onChange={(e) => handleDigitChange(index, e.target.value)}
              onKeyDown={(e) => handleKeyDown(index, e)}
              className="code-input"
              disabled={loading}
            />
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
            onClick={handleJoinGame}
            disabled={loading || digits.some(d => d === '')}
          >
            {loading ? 'Joining...' : 'Join Session'}
          </button>
        </div>
      </div>
      
      {error && <div className="error-message">{error}</div>}
    </div>
  );
};

export default JoinGameScreen;

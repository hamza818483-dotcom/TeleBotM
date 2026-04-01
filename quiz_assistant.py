import os
import google.generativeai as genai
from dotenv import load_dotenv
import re
import time
from .gemini_service import key_manager

load_dotenv()

class QuizAssistant:
    """Service to predict answers and solve equations for quiz questions"""
    
    def __init__(self):
        """Initialize the quiz assistant with multi-key Gemini API support"""
        # Use the global key manager for multi-key support
        self.key_manager = key_manager
        print("QuizAssistant initialized with multi-key support")
    
    def predict_answer(self, question, options, max_retries: int = 3):
        """
        Predict the most likely correct answer for a given question using multi-key support
        
        Args:
            question (str): The question text
            options (list): List of possible answer options
            max_retries (int): Maximum number of retry attempts with different keys
            
        Returns:
            int: The index of the most likely correct answer (0-3)
            float: Confidence score (0-1)
        """
        # Create a structured prompt for the model
        prompt = self._create_prompt(question, options)
        
        for attempt in range(max_retries):
            try:
                # Use random key for load balancing on first attempt, then rotate on failures
                use_random = (attempt == 0)
                api_key = self.key_manager.get_random_healthy_key() if use_random else self.key_manager.get_current_key()
                
                if not api_key:
                    print("No healthy API keys available for prediction")
                    return None, 0.0
                
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel('gemini-2.5-flash')
                
                start_time = time.time()
                print(f"Starting answer prediction (attempt {attempt + 1}/{max_retries}) at {start_time}")
                
                # Get prediction from Gemini
                response = model.generate_content(prompt)
                
                end_time = time.time()
                print(f"Received prediction in {end_time - start_time:.2f} seconds")
                
                answer_index, confidence = self._parse_response(response.text)
                
                # Record successful API call
                self.key_manager.record_success(api_key)
                
                # Return the index and confidence
                return answer_index, confidence
                
            except Exception as e:
                error_msg = str(e)
                print(f"Error predicting answer (attempt {attempt + 1}): {error_msg}")
                self.key_manager.record_failure(api_key, error_msg)
                
                # Rotate to next key if this isn't the last attempt
                if attempt < max_retries - 1:
                    self.key_manager.rotate_key(f"Prediction error: {error_msg[:50]}...")
                    continue
                else:
                    return None, 0.0
        
        return None, 0.0
    
    def solve_equation(self, question, max_retries: int = 3):
        """
        Solve physics, chemistry, or math questions with related equations and concise solutions using multi-key support
        
        Args:
            question (str): The question text
            max_retries (int): Maximum number of retry attempts with different keys
            
        Returns:
            str: Concise solution with relevant equations
        """
        # Create a prompt for solving the equation
        prompt = (
            f"You are an expert physics, chemistry, and mathematics solver. "
            f"Solve this problem in an ultra-concise manner:\n\n"
            f"{question}\n\n"
            f"Follow these strict guidelines:\n"
            f"1. First identify and list ONLY the most essential equation(s) needed (max 1-2 lines)\n"
            f"2. Solve step-by-step using absolute minimum number of lines (3-4 steps max)\n" 
            f"3. Use proper mathematical notation and variables\n"
            f"4. Focus on calculations only, NO explanations or theory\n"
            f"5. Include ONLY the final answer with proper units in one line\n"
            f"6. Total response must not exceed 10 lines\n\n"
            f"Format must be exactly like this:\n"
            f"Equation(s): [Just write the equation(s), no explanation]\n"
            f"Solution:\n"
            f"1. [First calculation step]\n"
            f"2. [Second calculation step]\n"
            f"Answer: [Final result with units]"
        )
        
        for attempt in range(max_retries):
            try:
                # Use random key for load balancing on first attempt, then rotate on failures
                use_random = (attempt == 0)
                api_key = self.key_manager.get_random_healthy_key() if use_random else self.key_manager.get_current_key()
                
                if not api_key:
                    print("No healthy API keys available for equation solving")
                    return "Unable to solve the equation."
                
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel('gemini-2.5-flash')
                
                start_time = time.time()
                print(f"Starting equation solving (attempt {attempt + 1}/{max_retries}) at {start_time}")
                
                # Get solution from Gemini
                response = model.generate_content(prompt)
                solution = response.text.strip()
                
                end_time = time.time()
                print(f"Received solution in {end_time - start_time:.2f} seconds")
                
                # Record successful API call
                self.key_manager.record_success(api_key)
                
                return solution
                
            except Exception as e:
                error_msg = str(e)
                print(f"Error solving equation (attempt {attempt + 1}): {error_msg}")
                self.key_manager.record_failure(api_key, error_msg)
                
                # Rotate to next key if this isn't the last attempt
                if attempt < max_retries - 1:
                    self.key_manager.rotate_key(f"Equation solving error: {error_msg[:50]}...")
                    continue
                else:
                    return "Unable to solve the equation."
        
        return "Unable to solve the equation."
    
    def _create_prompt(self, question, options):
        """Create a structured prompt for the model"""
        option_text = "\n".join([f"{chr(65+i)}. {opt}" for i, opt in enumerate(options)])
        
        prompt = f"""You are an expert at answering multiple-choice questions. 
        
For the following question, determine which answer option is most likely correct.
Analyze each option carefully and provide your answer in the following format:
1. The letter of your answer (A, B, C, or D)
2. Your confidence level as a percentage between 0-100%
3. A brief explanation of your reasoning

Question: {question}

Options:
{option_text}

Your answer:"""
        
        return prompt
    
    def _parse_response(self, response_text):
        """
        Parse the model response to extract the predicted answer index and confidence
        
        Returns:
            int: The index of the predicted answer (0-3)
            float: Confidence score (0-1)
        """
        # Default values
        answer_index = None
        confidence = 0.0
        
        try:
            # Clean up response text
            response_text = response_text.strip()
            
            # Look for a letter A, B, C, or D in the response
            for char in response_text:
                if char in "ABCDabcd":
                    # Convert letter to index (A=0, B=1, C=2, D=3)
                    answer_index = ord(char.upper()) - ord('A')
                    break
            
            # Look for percentage confidence in the text
            confidence_patterns = [
                r'(\d{1,3})%',  # Match "75%"
                r'(\d{1,3})\s*percent',  # Match "75 percent"
                r'confidence\D*(\d{1,3})',  # Match "confidence: 75"
                r'confidence level\D*(\d{1,3})'  # Match "confidence level: 75"
            ]
            
            for pattern in confidence_patterns:
                matches = re.search(pattern, response_text)
                if matches:
                    confidence_value = int(matches.group(1))
                    # Ensure confidence is between 0-100
                    confidence_value = max(0, min(100, confidence_value))
                    confidence = confidence_value / 100.0
                    break
            
            # If no confidence was found but we have an answer, set a default
            if confidence == 0.0 and answer_index is not None:
                confidence = 0.5  # Default 50% confidence
                
            return answer_index, confidence
            
        except Exception as e:
            print(f"Error parsing response: {str(e)}")
            return None, 0.0 
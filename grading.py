from google import genai
from google.api_core import exceptions as google_exceptions
import logging

# Configure logging
logging.basicConfig(filename='grading.log', level=logging.INFO)

# Initialize the client
client = genai.Client(api_key="YOUR_API_KEY")  # Replace with your actual API key

def grade_submission(student_answer, reference_answer):
    """
    Grade student submission against reference answer using Gemini AI
    Returns: (score, feedback, improvement_suggestions)
    """
    if not student_answer or not reference_answer:
        return 0, "Missing content", "Please provide complete answers"
    
    try:
        # Construct the grading prompt
        prompt = f"""
        ACT AS AN EXPERIENCED TEACHER. GRADE THIS STUDENT SUBMISSION AGAINST THE REFERENCE ANSWER.
        
        GUIDELINES:
        1. Score (0-100) based on accuracy and completeness
        2. Provide specific feedback
        3. Suggest concrete improvements
        
        REFERENCE ANSWER: {reference_answer}
        STUDENT ANSWER: {student_answer}
        
        RESPONSE FORMAT (EXACTLY THIS FORMAT):
        SCORE: [number between 0-100]
        FEEDBACK: [detailed feedback]
        IMPROVEMENT: [specific suggestions]
        """
        
        # Generate the response
        response = client.models.generate_content(
            model="gemini-1.5-flash",  # Using the latest flash model
            contents=prompt
        )
        
        # Debug logging
        logging.info(f"Grading response: {response.text}")
        
        if not response.text:
            raise ValueError("Empty response from AI model")
        
        # Parse the response
        score = 50  # Default score if parsing fails
        feedback = "No feedback generated"
        improvement = "No suggestions provided"
        
        # Parse each line of the response
        for line in response.text.split('\n'):
            if line.startswith("SCORE:"):
                try:
                    score = float(line.replace("SCORE:", "").strip())
                    score = max(0, min(100, score))  # Ensure score is between 0-100
                except ValueError:
                    pass
            elif line.startswith("FEEDBACK:"):
                feedback = line.replace("FEEDBACK:", "").strip()
            elif line.startswith("IMPROVEMENT:"):
                improvement = line.replace("IMPROVEMENT:", "").strip()
        
        return score, feedback, improvement
        
    except google_exceptions.GoogleAPIError as e:
        logging.error(f"API Error: {str(e)}")
        return 50, "Grading service unavailable", "Please try again later"
    except ValueError as e:
        logging.error(f"Value Error: {str(e)}")
        return 50, "Grading error", "Could not parse the grading results"
    except Exception as e:
        logging.error(f"Unexpected error: {str(e)}")
        return 50, "Grading failed", "Technical error occurred"

def simple_fallback_grade(student_answer, reference_answer):
    """Fallback grading when AI grading fails"""
    common_words = len(set(student_answer.lower().split()) & 
                      set(reference_answer.lower().split()))
    total_words = len(reference_answer.split())
    score = min(100, (common_words / total_words) * 100) if total_words > 0 else 0
    return score, "Basic evaluation", "Compare your answer with the reference material"

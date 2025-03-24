import os
import google.generativeai as genai
from flask import current_app

# Initialize the Generative AI client
genai.configure(api_key=os.getenv('GENAI_API_KEY'))

def grade_submission(student_answer, reference_answer):
    try:
        # Initialize the model
        model = genai.GenerativeModel('gemini-pro')
        
        prompt = f"""
        Grade this student submission against the reference answer.
        Provide:
        1. A score (0-100)
        2. Detailed feedback
        3. Areas for improvement
        
        REFERENCE ANSWER: {reference_answer}
        STUDENT ANSWER: {student_answer}
        
        Format your response as:
        SCORE: [score]
        FEEDBACK: [feedback]
        IMPROVEMENT: [suggestions]
        """
        
        response = model.generate_content(prompt)
        
        # Parse the response
        result = {
            "score": 50,  # Default score if parsing fails
            "feedback": "No feedback generated",
            "improvement": "No suggestions provided"
        }
        
        for line in response.text.split('\n'):
            if line.startswith("SCORE:"):
                try:
                    result["score"] = float(line.replace("SCORE:", "").strip())
                except ValueError:
                    pass
            elif line.startswith("FEEDBACK:"):
                result["feedback"] = line.replace("FEEDBACK:", "").strip()
            elif line.startswith("IMPROVEMENT:"):
                result["improvement"] = line.replace("IMPROVEMENT:", "").strip()
        
        return result["score"], result["feedback"], result["improvement"]
        
    except Exception as e:
        print(f"Grading error: {str(e)}")
        return 50, "Grading service unavailable", "Please try again later"

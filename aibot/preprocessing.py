#MV-2025-07-10-<6>  STARTS
from better_profanity import profanity

class QueryPreprocessor:
    def __init__(self):
        profanity.load_censor_words()
        
    def preprocess(self, query_text):
        """Clean and validate the input query"""
        # Remove leading/trailing whitespace
        cleaned = query_text.strip()
        
        # Check for offensive language
        if profanity.contains_profanity(cleaned):
            raise ValueError("Query contains inappropriate language")
            
        return cleaned
#MV-2025-07-10-<6>  ENDS

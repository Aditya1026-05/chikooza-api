from better_profanity import profanity


class QueryPreprocessor:
    def __init__(self):
        profanity.load_censor_words()

    def preprocess(self, query_text):
        """Clean and validate the input query."""
        cleaned = query_text.strip()

        if profanity.contains_profanity(cleaned):
            raise ValueError("Query contains inappropriate language")

        return cleaned

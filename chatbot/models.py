from django.db import models
from django.db.models import Q

# Create your models here.

class ChatbotQA(models.Model):
    """Store the chatbot's question and answer pairs"""
    question = models.CharField(max_length=255, unique=True, help_text="Question Keywords(English)")
    answer = models.TextField(help_text="Answer(English)")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.question
    
    @classmethod
    def find_best_match(cls, query):
        """
        Find the best matching question and answer pair for the user's query
        Use a more advanced matching logic to avoid false matches
        """
        from chatbot.views import clean_text
        
        cleaned_query = clean_text(query)
        query_words = cleaned_query.split()
        
        # First try exact matching
        exact_matches = cls.objects.filter(question__iexact=query)
        if exact_matches.exists():
            return exact_matches.first()
        
        # If there is no exact match, try matching all query words
        best_match = None
        best_score = 0
        
        for qa in cls.objects.all():
            cleaned_question = clean_text(qa.question)
            question_words = set(cleaned_question.split())
            
            # Calculate keyword matching score - higher weight for exact matches
            word_matches = sum(1 for word in query_words if word in question_words)
            exact_phrase_bonus = 3 if cleaned_query in cleaned_question else 0
            
            # Avoid false triggers for certain keywords
            if 'data' in query_words and 'analyze' in query_words and 'analyze' not in question_words:
                continue
                
            score = (word_matches / len(query_words) if query_words else 0) + exact_phrase_bonus
            
            if score > best_score:
                best_match = qa
                best_score = score
        
        # Only return results when the score exceeds the threshold
        if best_score > 0.6:  # Increase threshold to reduce false matches
            return best_match
            
        return None

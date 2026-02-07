"""
User domain model.

This module defines the User domain model for the application.
The User model represents a user with their preferences and can store
clothing recommendations and comfort scores.

Note: This is a domain model separate from the database model (app.database.models.User).
This model is used for business logic, while the database model is for persistence.
"""
class User:
    """
    User domain model.
    
    Represents a user in the application domain with their preferences.
    Used for business logic and can store temporary data like clothing
    recommendations and comfort scores.
    
    Attributes:
        name: User's name
        comfort_temperature: User's preferred comfort temperature in Fahrenheit
        clothing: Dictionary to store clothing recommendations (optional)
        score: Comfort score calculated for the user (optional)
    """
    def __init__(self, name, comfort_temperature):
        """
        Create a User object.
        
        Args:
            name: User's name (string)
            comfort_temperature: Preferred comfort temperature in Fahrenheit (float)
        """
        self.name = name
        self.comfort_temperature = comfort_temperature
        self.clothing = {}  # Store clothing recommendations if needed
        self.score = 0  # Store comfort score if calculated

    def __str__(self):
        """
        Human-friendly string representation.
        
        Returns:
            str: Formatted string with user name, comfort temperature, and clothing
        """
        return (f"User: {self.name}, Comfort Temperature: {self.comfort_temperature}, Clothing: {self.clothing}")

    # ---- Accessors (defensive: use .get with defaults) -----------------------
    def get_comfort_temperature(self):
        """
        Get user's comfort temperature preference.
        
        Returns:
            float: Comfort temperature in Fahrenheit
        """
        return self.comfort_temperature

    def get_clothing(self):
        """
        Get user's clothing recommendations.
        
        Returns:
            dict: Dictionary of clothing recommendations
        """
        return self.clothing

    # ---- Scoring --------------------------------------------------------------
    def get_score(self):
        """
        Get user's comfort score.
        
        Returns:
            float: Comfort score (0 if not set)
        """
        return self.score

    def set_score(self, score):
        """
        Set user's comfort score.
        
        Args:
            score: Comfort score value (float)
        """
        self.score = score


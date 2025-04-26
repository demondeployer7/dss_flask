from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from sqlalchemy import event
from sqlalchemy.orm import validates

db = SQLAlchemy()

def init_db(app):
    """Initialize the database with proper error handling"""
    try:
        with app.app_context():
            db.create_all()
            print("Database tables created successfully")
    except Exception as e:
        print(f"Error creating database tables: {str(e)}")
        raise

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    group_id = db.Column(db.String(50), db.ForeignKey('groups.group_id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    preferences = db.relationship('UserPreference', backref='user', uselist=False)
    reviews = db.relationship('UserReview', backref='user', uselist=False)
    group = db.relationship('Group', backref='members')

    @validates('user_id', 'password')
    def validate_string_fields(self, key, value):
        if not value or not value.strip():
            raise ValueError(f"{key} cannot be empty")
        return value.strip()

class UserPreference(db.Model):
    __tablename__ = 'user_preferences'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    group_id = db.Column(db.String(50), db.ForeignKey('groups.group_id'), nullable=False)
    
    # Preference fields
    preferred_cuisine = db.Column(db.String(200))
    usual_eating_time = db.Column(db.String(100))
    preferred_place = db.Column(db.String(100))
    main_course = db.Column(db.String(100))
    extra_treat = db.Column(db.String(100))
    drink_choice = db.Column(db.String(100))
    comfort_sip = db.Column(db.String(100))
    dietary_preference = db.Column(db.String(100))
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    group = db.relationship('Group', backref='preferences')

    @validates('dietary_preference')
    def validate_dietary_preference(self, key, value):
        valid_preferences = ['Vegetarian', 'Non-Vegetarian', 'Vegan', 'No Preference']
        if value and value not in valid_preferences:
            raise ValueError(f"Invalid dietary preference. Must be one of: {', '.join(valid_preferences)}")
        return value

class Group(db.Model):
    __tablename__ = 'groups'
    
    group_id = db.Column(db.String(50), primary_key=True)
    group_size = db.Column(db.Integer, nullable=False)
    is_completed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Add constraint for supported group sizes
    __table_args__ = (
        db.CheckConstraint('group_size IN (5, 8)', name='check_group_size'),
    )

    def check_completion(self):
        """Check if all group members have submitted their reviews"""
        if self.is_completed:
            return True
            
        total_members = len(self.members)
        total_reviews = len(self.reviews)
        
        if total_members == self.group_size and total_reviews == self.group_size:
            self.is_completed = True
            return True
            
        return False

class UserReview(db.Model):
    __tablename__ = 'user_reviews'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    group_id = db.Column(db.String(50), db.ForeignKey('groups.group_id'), nullable=False)
    
    # Track if recommendations were shown to user
    recommendations_shown = db.Column(db.Boolean, default=False)
    
    # Review/Questionnaire fields
    matched_interests = db.Column(db.Integer)
    discovered_new_items = db.Column(db.Integer)
    diverse_recommendations = db.Column(db.Integer)
    easy_to_find = db.Column(db.Integer)
    ideal_item_found = db.Column(db.Integer)
    overall_satisfaction = db.Column(db.Integer)
    confidence_in_decision = db.Column(db.Integer)
    would_buy_recommendations = db.Column(db.Integer)
    good_group_suggestions = db.Column(db.Integer)
    convinced_of_items = db.Column(db.Integer)
    confident_will_like = db.Column(db.Integer)
    trust_in_recommender = db.Column(db.Integer)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    group = db.relationship('Group', backref='reviews')

    @validates('matched_interests', 'discovered_new_items', 'diverse_recommendations',
              'easy_to_find', 'ideal_item_found', 'overall_satisfaction',
              'confidence_in_decision', 'would_buy_recommendations',
              'good_group_suggestions', 'convinced_of_items', 'confident_will_like',
              'trust_in_recommender')
    def validate_rating_fields(self, key, value):
        if value is not None and (value < 1 or value > 5):
            raise ValueError(f"{key} must be between 1 and 5")
        return value

# Event listener to check group completion after review submission
@event.listens_for(UserReview, 'after_insert')
def check_group_completion(mapper, connection, target):
    group = Group.query.get(target.group_id)
    if group:
        group.check_completion()
        db.session.commit() 
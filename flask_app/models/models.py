from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    group_id = db.Column(db.String(50), nullable=False)
    
    responses = db.relationship('UserResponse', backref='user', lazy=True)
    reviews = db.relationship('UserReview', backref='user', lazy=True)

class UserResponse(db.Model):
    __tablename__ = 'user_responses'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(50), db.ForeignKey('users.user_id'), nullable=False)
    group_id = db.Column(db.String(50), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    preferred_cuisine = db.Column(db.String(500))
    usual_eating_time = db.Column(db.String(100))
    preferred_place = db.Column(db.String(100))
    main_course = db.Column(db.String(500))
    extra_treat = db.Column(db.String(500))
    drink_choice = db.Column(db.String(500))
    comfort_sip = db.Column(db.String(500))
    dietary_preference = db.Column(db.String(100))

class UserReview(db.Model):
    __tablename__ = 'user_reviews'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(50), db.ForeignKey('users.user_id'), nullable=False)
    group_id = db.Column(db.String(50), nullable=False)
    # Removed top_3_recommendations as it's no longer needed
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
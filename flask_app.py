from flask import Flask, request, jsonify, session
from flask_session import Session
from models import db, User, UserPreference, GroupRating, UserReview, Group
from config import Config
import json
import os
from datetime import datetime
from functools import wraps
import math
import ast

app = Flask(__name__)
app.config.from_object(Config)
Session(app)
db.init_app(app)

# Load JSON data at startup
def load_json_data():
    # Load dominant categories (same for all group sizes)
    with open('Dominant_Categories.json', 'r') as f:
        app.dominant_categories = json.load(f)
        app.dominant_categories = [ele.capitalize() for ele in app.dominant_categories]
    
    # Load group vectors and recommendations for different group sizes
    app.group_vectors = {
        5: None,
        8: None
    }
    app.recommendations = {
        5: None,
        8: None
    }
    
    # Load data for group size 5
    with open('group_vectors_size_5.json', 'r') as f:
        app.group_vectors[5] = json.load(f)
    
    with open('proper_dominant_categories_list_reco_grop_size_5_reco_5.json', 'r') as f:
        app.recommendations[5] = json.load(f)
    
    # Load data for group size 8
    with open('group_vectors_size_8.json', 'r') as f:
        app.group_vectors[8] = json.load(f)
    
    with open('proper_dominant_categories_list_reco_grop_size_8_reco_5.json', 'r') as f:
        app.recommendations[8] = json.load(f)

# Vector similarity functions
def list_to_frequency_vector(category_list, vector_size=122):
    category_to_index = {cat: idx for idx, cat in enumerate(app.dominant_categories)}
    freq_vector = [0] * vector_size
    for ele in category_list:
        ele = ele.capitalize()
        if ele in category_to_index:
            idx = category_to_index[ele]
            freq_vector[idx] += 1
    return freq_vector

def cosine_similarity(vec1, vec2):
    dot = sum(a * b for a, b in zip(vec1, vec2)) 
    norm1 = math.sqrt(sum(a * a for a in vec1))
    norm2 = math.sqrt(sum(b * b for b in vec2))
    if norm1 == 0 or norm2 == 0:
        return 0
    return dot / (norm1 * norm2)

def find_most_similar_group(input_vector, group_size):
    max_sim = -1
    best_match = None
    group_vectors = app.group_vectors[group_size]
    
    for idx, group_vec in group_vectors.items():
        sim = cosine_similarity(input_vector, group_vec)
        if sim > max_sim:
            max_sim = sim
            best_match = idx
    return best_match, max_sim

def get_group_preferences(group_id):
    preferences = UserPreference.query.filter_by(group_id=group_id).all()
    
    # Process preferences to exclude "None of the below" and special values
    processed_preferences = []
    for pref in preferences:
        user_preferences = []
        for key in ['preferred_cuisine', 'usual_eating_time', 'preferred_place', 
                   'main_course', 'extra_treat', 'drink_choice', 'comfort_sip']:
            try:
                value = getattr(pref, key)
                if value:
                    if key == 'dietary_preference':
                        if value not in ["Non-Vegetarian", "No Preference"]:
                            user_preferences.append(value)
                    else:
                        try:
                            values = ast.literal_eval(value) if value.startswith("[") else [value]
                            filtered_values = [v for v in values if v != "None of the below"]
                            user_preferences.extend(filtered_values)
                        except:
                            if value != "None of the below":
                                user_preferences.append(value)
            except:
                continue
        processed_preferences.extend(user_preferences)
    
    return processed_preferences

def get_recommendations(group_preferences, group_size):
    if not group_preferences:
        return {}
        
    # Create frequency vector from all preferences
    vec = list_to_frequency_vector(group_preferences)
    
    # Find most similar group and get recommendations
    best_group, _ = find_most_similar_group(vec, group_size)
    recommendations = app.recommendations[group_size][best_group]
    
    if not recommendations:
        return {}
        
    return recommendations

# Error handling
class APIError(Exception):
    def __init__(self, message, status_code=400):
        self.message = message
        self.status_code = status_code

@app.errorhandler(APIError)
def handle_api_error(error):
    response = jsonify({'error': error.message})
    response.status_code = error.status_code
    return response

# Authentication decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            raise APIError('Authentication required', 401)
        return f(*args, **kwargs)
    return decorated_function

# User routes
@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    if not data or 'user_id' not in data or 'password' not in data or 'group_id' not in data:
        raise APIError('Missing required fields', 400)
    
    # Check if group exists and get its size
    group = Group.query.filter_by(group_id=data['group_id']).first()
    if not group:
        raise APIError('Group not found', 404)
    
    # Check if group is full
    current_members = User.query.filter_by(group_id=data['group_id']).count()
    if current_members >= group.group_size:
        raise APIError('Group is full', 400)
    
    if User.query.filter_by(user_id=data['user_id']).first():
        raise APIError('User already exists', 409)
    
    user = User(
        user_id=data['user_id'],
        password=data['password'],
        group_id=data['group_id']
    )
    
    db.session.add(user)
    db.session.commit()
    
    return jsonify({
        'message': 'User registered successfully',
        'group_size': group.group_size,
        'current_members': current_members + 1
    }), 201

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data or 'user_id' not in data or 'password' not in data:
        raise APIError('Missing credentials', 400)
    
    user = User.query.filter_by(user_id=data['user_id'], password=data['password']).first()
    if not user:
        raise APIError('Invalid credentials', 401)
    
    session['user_id'] = user.id
    return jsonify({'message': 'Login successful'})

@app.route('/api/logout', methods=['POST'])
@login_required
def logout():
    session.pop('user_id', None)
    return jsonify({'message': 'Logged out successfully'})

# Group routes
@app.route('/api/groups', methods=['POST'])
@login_required
def create_group():
    data = request.get_json()
    if not data or 'group_size' not in data:
        raise APIError('Missing group size', 400)
    
    group_size = data['group_size']
    if group_size not in [5, 8]:
        raise APIError('Unsupported group size. Only groups of size 5 or 8 are supported.', 400)
    
    group = Group(
        group_id=f"group_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
        group_size=group_size
    )
    
    db.session.add(group)
    db.session.commit()
    
    return jsonify({
        'group_id': group.group_id,
        'group_size': group.group_size,
        'message': f'Group created successfully with size {group_size}'
    }), 201

# User preferences routes
@app.route('/api/preferences', methods=['POST'])
@login_required
def save_preferences():
    data = request.get_json()
    if not data:
        raise APIError('No data provided', 400)
    
    user = User.query.get(session['user_id'])
    if not user:
        raise APIError('User not found', 404)
    
    preference = UserPreference(
        user_id=user.id,
        group_id=user.group_id,
        preferred_cuisine=data.get('preferred_cuisine'),
        usual_eating_time=data.get('usual_eating_time'),
        preferred_place=data.get('preferred_place'),
        main_course=data.get('main_course'),
        extra_treat=data.get('extra_treat'),
        drink_choice=data.get('drink_choice'),
        comfort_sip=data.get('comfort_sip'),
        dietary_preference=data.get('dietary_preference')
    )
    
    db.session.add(preference)
    db.session.commit()
    
    return jsonify({'message': 'Preferences saved successfully'}), 201

# Get recommendations
@app.route('/api/recommendations', methods=['GET'])
@login_required
def get_recommendations_endpoint():
    user = User.query.get(session['user_id'])
    if not user:
        raise APIError('User not found', 404)
    
    # Check if all group members have submitted preferences
    group_preferences = UserPreference.query.filter_by(group_id=user.group_id).all()
    group = Group.query.filter_by(group_id=user.group_id).first()
    
    if not group:
        raise APIError('Group not found', 404)
    
    if len(group_preferences) < group.group_size:
        return jsonify({
            'message': f'Waiting for {group.group_size - len(group_preferences)} more members to submit preferences',
            'status': 'incomplete'
        })
    
    # Get processed preferences for recommendations
    processed_preferences = get_group_preferences(user.group_id)
    recommendations = get_recommendations(processed_preferences, group.group_size)
    
    if not recommendations:
        raise APIError('No recommendations found', 404)
    
    # Mark that recommendations were shown to user
    review = UserReview.query.filter_by(user_id=user.id, group_id=user.group_id).first()
    if not review:
        review = UserReview(user_id=user.id, group_id=user.group_id)
        db.session.add(review)
    
    review.recommendations_shown = True
    db.session.commit()
    
    return jsonify({
        'recommendations': recommendations,
        'status': 'complete',
        'group_size': group.group_size
    })

# Reviews routes
@app.route('/api/reviews', methods=['POST'])
@login_required
def save_review():
    data = request.get_json()
    if not data:
        raise APIError('No data provided', 400)
    
    user = User.query.get(session['user_id'])
    if not user:
        raise APIError('User not found', 404)
    
    # Check if recommendations were shown to user
    review = UserReview.query.filter_by(user_id=user.id, group_id=user.group_id).first()
    if not review or not review.recommendations_shown:
        raise APIError('Recommendations must be shown before submitting review', 400)
    
    # Update review with questionnaire responses
    review.matched_interests = data.get('matched_interests')
    review.discovered_new_items = data.get('discovered_new_items')
    review.diverse_recommendations = data.get('diverse_recommendations')
    review.easy_to_find = data.get('easy_to_find')
    review.ideal_item_found = data.get('ideal_item_found')
    review.overall_satisfaction = data.get('overall_satisfaction')
    review.confidence_in_decision = data.get('confidence_in_decision')
    review.would_buy_recommendations = data.get('would_buy_recommendations')
    review.good_group_suggestions = data.get('good_group_suggestions')
    review.convinced_of_items = data.get('convinced_of_items')
    review.confident_will_like = data.get('confident_will_like')
    review.trust_in_recommender = data.get('trust_in_recommender')
    
    db.session.commit()
    
    return jsonify({'message': 'Review saved successfully'}), 201

# Add a new endpoint to get group status
@app.route('/api/groups/<group_id>/status', methods=['GET'])
@login_required
def get_group_status(group_id):
    group = Group.query.filter_by(group_id=group_id).first()
    if not group:
        raise APIError('Group not found', 404)
    
    current_members = User.query.filter_by(group_id=group_id).count()
    preferences_submitted = UserPreference.query.filter_by(group_id=group_id).count()
    
    return jsonify({
        'group_id': group.group_id,
        'group_size': group.group_size,
        'current_members': current_members,
        'preferences_submitted': preferences_submitted,
        'is_full': current_members >= group.group_size,
        'all_preferences_submitted': preferences_submitted >= group.group_size
    })

if __name__ == '__main__':
    with app.app_context():
        from models import init_db
        init_db(app)
        load_json_data()
    app.run(debug=True) 
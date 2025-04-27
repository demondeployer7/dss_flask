from flask import Flask, request, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from flask_session import Session
from models.models import db, User, UserResponse, UserReview
import json
import math
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Configure Flask app
app.config['SQLALCHEMY_DATABASE_URI'] = f"postgresql://postgres:mysecretpassword@localhost:5434/postgres?sslmode=disable"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key')
app.config['SESSION_TYPE'] = 'filesystem'

# Initialize extensions
Session(app)
db.init_app(app)

# Load JSON data
with open('Dominant_Categories.json', 'r') as f:
    Dominant_Categories = json.load(f)

# Load group vectors for both group sizes
group_vectors = {}
group_vectors_5 = {}
group_vectors_8 = {}

with open('group_vectors_size_5.json', 'r') as f:
    group_vectors_5 = json.load(f)

with open('group_vectors_size_8.json', 'r') as f:
    group_vectors_8 = json.load(f)

# Load recommendation data for both group sizes
dominant_categories_list_reco_5 = {}
dominant_categories_list_reco_8 = {}

with open('proper_dominant_categories_list_reco_grop_size_5_reco_5.json', 'r') as f:
    dominant_categories_list_reco_5 = json.load(f)

with open('proper_dominant_categories_list_reco_grop_size_8_reco_5.json', 'r') as f:
    dominant_categories_list_reco_8 = json.load(f)

def list_to_frequency_vector(category_list, vector_size=122):
    category_to_index = {cat: idx for idx, cat in enumerate(Dominant_Categories)}
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

def find_most_similar_group(input_vector):
    max_sim = -1
    best_match = None
    for idx, group_vec in group_vectors.items():
        sim = cosine_similarity(input_vector, group_vec)
        if sim > max_sim:
            max_sim = sim
            best_match = idx
    return best_match, max_sim

def get_group_preferences(group_id):
    group_responses = UserResponse.query.filter_by(group_id=group_id).all()
    processed_preferences = []
    
    for response in group_responses:
        user_preferences = []
        preference_fields = [
            'preferred_cuisine', 'preferred_place',
            'main_course', 'extra_treat', 'drink_choice', 'comfort_sip'
        ]
        
        for field in preference_fields:
            value = getattr(response, field)
            try:
                values = json.loads(value) if value.startswith("[") else [value]
                filtered_values = [v for v in values if v != "None of the below"]
                user_preferences.extend(filtered_values)
            except:
                if value != "None of the below":
                    user_preferences.append(value)
                    
        if response.dietary_preference not in ["Non-Vegetarian", "No Preference"]:
            user_preferences.append(response.dietary_preference)
        if response.usual_eating_time not in ["Lunch"]:
            user_preferences.append(response.usual_eating_time)
            
        processed_preferences.extend(user_preferences)
    
    return processed_preferences

def get_recommendations(group_preferences):
    if not group_preferences:
        return {"error": "No group preferences found."}
    
    # Get current group size from session
    group_size = session.get('group_size', 0)
    
    # Select appropriate vectors and recommendations based on group size
    if group_size == 5:
        current_vectors = group_vectors_5
        current_reco = dominant_categories_list_reco_5
    elif group_size == 8:
        current_vectors = group_vectors_8
        current_reco = dominant_categories_list_reco_8
    else:
        return {"error": f"Unsupported group size: {group_size}"}
        
    vec = list_to_frequency_vector(group_preferences)
    best_group, _ = find_most_similar_group(vec, current_vectors)
    recommendations = current_reco[best_group]
    
    if not recommendations:
        return {"error": "No recommendations found for the group."}
        
    return recommendations

def find_most_similar_group(input_vector, current_vectors):
    max_sim = -1
    best_match = None
    for idx, group_vec in current_vectors.items():
        sim = cosine_similarity(input_vector, group_vec)
        if sim > max_sim:
            max_sim = sim
            best_match = idx
    return best_match, max_sim

# Routes
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    user_id = data.get('user_id')
    password = data.get('password')
    
    if not user_id or not password:
        return jsonify({"error": "Please provide both user ID and password"}), 400
    
    user = User.query.filter_by(user_id=user_id, password=password).first()
    if user:
        # Get group size by counting users in the same group
        group_size = User.query.filter_by(group_id=user.group_id).count()
        
        session['logged_in'] = True
        session['user_id'] = user_id
        session['group_id'] = user.group_id
        session['group_size'] = group_size
        session['last_activity'] = datetime.utcnow()
        return jsonify({
            "message": "Login successful",
            "user_id": user_id,
            "group_id": user.group_id,
            "group_size": group_size
        })
    return jsonify({"error": "Invalid credentials"}), 401

@app.route('/submit_preferences', methods=['POST'])
def submit_preferences():
    if not session.get('logged_in'):
        return jsonify({"error": "Please login first"}), 401
    
    data = request.get_json()
    required_fields = [
        'preferred_cuisine', 'usual_eating_time', 'preferred_place',
        'main_course', 'extra_treat', 'drink_choice', 'comfort_sip',
        'dietary_preference'
    ]
    
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"Missing field: {field}"}), 400
    
    try:
        response = UserResponse(
            user_id=session['user_id'],
            group_id=session['group_id'],
            **data
        )
        db.session.add(response)
        db.session.commit()
        return jsonify({"message": "Preferences saved successfully"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/get_recommendations', methods=['GET'])
def recommendations():
    if not session.get('logged_in'):
        return jsonify({"error": "Please login first"}), 401
    
    group_preferences = get_group_preferences(session['group_id'])
    recommendations = get_recommendations(group_preferences)
    
    return jsonify(recommendations)

@app.route('/submit_review', methods=['POST'])
def submit_review():
    if not session.get('logged_in'):
        return jsonify({"error": "Please login first"}), 401
    
    data = request.get_json()
    required_fields = [
        'top_3_recommendations', 'matched_interests', 'discovered_new_items',
        'diverse_recommendations', 'easy_to_find', 'ideal_item_found',
        'overall_satisfaction', 'confidence_in_decision', 'would_buy_recommendations',
        'good_group_suggestions', 'convinced_of_items', 'confident_will_like',
        'trust_in_recommender'
    ]
    
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"Missing field: {field}"}), 400
    
    try:
        review = UserReview(
            user_id=session['user_id'],
            group_id=session['group_id'],
            **data
        )
        db.session.add(review)
        db.session.commit()
        return jsonify({"message": "Review saved successfully"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({"message": "Logged out successfully"})

@app.route('/get_group_size', methods=['GET'])
def get_group_size():
    if not session.get('logged_in'):
        return jsonify({"error": "Please login first"}), 401
    
    group_id = session.get('group_id')
    group_size = User.query.filter_by(group_id=group_id).count()
    
    return jsonify({
        "group_id": group_id,
        "group_size": group_size
    })

# Create database tables
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True, port=5000)

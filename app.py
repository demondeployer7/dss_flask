import streamlit as st
import pandas as pd
import pickle
import math
from datetime import datetime
import ast
import os
import base64
import requests
import io

# GitHub API Constants
REPO_OWNER = "demondeployer7"  # Replace with your GitHub username
REPO_NAME = "dss8"  # Replace with your repository name
GITHUB_TOKEN = st.secrets["github_token"]  # Make sure to add this in Streamlit secrets

# File paths in GitHub repo
USERS_CSV_PATH = "users.csv"
RESPONSES_CSV_PATH = "user_responses.csv"
RATINGS_CSV_PATH = "recommendation_ratings.csv"
REVIEWS_CSV_PATH = "user_reviews.csv"

def get_file_from_github(file_path):
    """Fetch a file from GitHub repository."""
    api_url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{file_path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    response = requests.get(api_url, headers=headers)

    if response.status_code == 200:
        content = response.json()
        decoded = base64.b64decode(content["content"]).decode("utf-8")
        sha = content["sha"]
        return decoded, sha
    elif response.status_code == 404:
        # File doesn't exist yet, return empty content and None sha
        return "", None
    else:
        st.error(f"❌ Failed to fetch {file_path} from GitHub (Status Code: {response.status_code})")
        try:
            error_message = response.json().get("message", "No message in response")
            st.text(f"GitHub Error: {error_message}")
        except Exception as e:
            st.text(f"Could not parse GitHub response. Raw response:\n{response.text}")
        return None, None

def update_file_on_github(file_path, content, sha):
    """Update a file on GitHub repository."""
    api_url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{file_path}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }
    encoded_content = base64.b64encode(content.encode("utf-8")).decode("utf-8")
    message = f"Update {file_path} via Streamlit app"
    data = {
        "message": message,
        "content": encoded_content,
        "sha": sha
    }
    response = requests.put(api_url, headers=headers, json=data)
    return response.status_code == 200

# Set page config
st.set_page_config(
    page_title="KCGRS Group Eatery Recommender",
    page_icon="🍽️",
    layout="wide"
)

# Custom CSS
st.markdown("""
    <style>
    .main {
        background-color: #000000;
    }
    .stButton>button {
        background-color: #4CAF50;
        color: white;
        border-radius: 5px;
        padding: 10px 20px;
        font-weight: bold;
    }
    .stButton>button:hover {
        background-color: #45a049;
    }
    .stTextInput>div>div>input {
        border-radius: 5px;
    }
    .stSelectbox>div>div>select {
        border-radius: 5px;
    }
    .stSlider>div>div>div>div {
        background-color: #4CAF50;
    }
    .css-1d391kg {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .stMarkdown h1 {
        color: #4d6b80;
        text-align: center;
        margin-bottom: 30px;
    }
    .stMarkdown h2 {
        color: #ffffff;
        border-bottom: 2px solid #4CAF50;
        padding-bottom: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

def load_users():
    """Load users from GitHub repository."""
    content, _ = get_file_from_github(USERS_CSV_PATH)
    if content is None:
        return pd.DataFrame(columns=['user_id', 'password', 'group_id'])
    try:
        return pd.read_csv(io.StringIO(content))
    except pd.errors.EmptyDataError:
        return pd.DataFrame(columns=['user_id', 'password', 'group_id'])

def load_responses():
    """Load user responses from GitHub repository."""
    content, _ = get_file_from_github(RESPONSES_CSV_PATH)
    if content is None:
        return pd.DataFrame(columns=[
            'user_id', 'group_id', 'timestamp',
            'preferred_cuisine', 'usual_eating_time', 'preferred_place',
            'main_course', 'extra_treat', 'drink_choice',
            'comfort_sip', 'dietary_preference'
        ])
    try:
        return pd.read_csv(io.StringIO(content))
    except pd.errors.EmptyDataError:
        return pd.DataFrame(columns=[
            'user_id', 'group_id', 'timestamp',
            'preferred_cuisine', 'usual_eating_time', 'preferred_place',
            'main_course', 'extra_treat', 'drink_choice',
            'comfort_sip', 'dietary_preference'
        ])

def save_response(user_id, group_id, responses_dict):
    """Save user response to GitHub repository."""
    responses = load_responses()
    new_response = pd.DataFrame({
        'user_id': [user_id],
        'group_id': [group_id],
        'timestamp': [datetime.now().strftime('%Y-%m-%d %H:%M:%S')],
        'preferred_cuisine': [responses_dict['preferred_cuisine']],
        'usual_eating_time': [responses_dict['usual_eating_time']],
        'preferred_place': [responses_dict['preferred_place']],
        'main_course': [responses_dict['main_course']],
        'extra_treat': [responses_dict['extra_treat']],
        'drink_choice': [responses_dict['drink_choice']],
        'comfort_sip': [responses_dict['comfort_sip']],
        'dietary_preference': [responses_dict['dietary_preference']]
    })
    responses = pd.concat([responses, new_response], ignore_index=True)
    csv_str = responses.to_csv(index=False)
    
    # Get current file content and SHA
    _, sha = get_file_from_github(RESPONSES_CSV_PATH)
    if update_file_on_github(RESPONSES_CSV_PATH, csv_str, sha):
        return True
    else:
        st.error("Failed to save response to GitHub")
        return False

def load_ratings():
    """Load recommendation ratings from GitHub repository."""
    content, _ = get_file_from_github(RATINGS_CSV_PATH)
    if content is None:
        return pd.DataFrame(columns=['user_id', 'group_id', 'recommendation', 'rating'])
    try:
        return pd.read_csv(io.StringIO(content))
    except pd.errors.EmptyDataError:
        return pd.DataFrame(columns=['user_id', 'group_id', 'recommendation', 'rating'])

def save_rating(user_id, group_id, recommendation, rating):
    """Save rating to GitHub repository."""
    ratings = load_ratings()
    
    # Check for duplicate ratings
    existing_rating = ratings[
        (ratings['user_id'] == user_id) & 
        (ratings['group_id'] == group_id) & 
        (ratings['recommendation'] == recommendation)
    ]
    
    if not existing_rating.empty:
        st.warning("You have already rated this recommendation.")
        return False
    
    new_rating = pd.DataFrame({
        'user_id': [user_id],
        'group_id': [group_id],
        'recommendation': [recommendation],
        'rating': [rating]
    })
    ratings = pd.concat([ratings, new_rating], ignore_index=True)
    csv_str = ratings.to_csv(index=False)
    
    # Get current file content and SHA
    _, sha = get_file_from_github(RATINGS_CSV_PATH)
    if update_file_on_github(RATINGS_CSV_PATH, csv_str, sha):
        return True
    else:
        st.error("Failed to save rating to GitHub")
        return False

def load_user_reviews():
    """Load user reviews from GitHub repository."""
    content, _ = get_file_from_github(REVIEWS_CSV_PATH)
    if content is None:
        return pd.DataFrame(columns=[
            'user_id', 'group_id', 'top_3_recommendations',
            'matched_interests', 'discovered_new_items', 'diverse_recommendations',
            'easy_to_find', 'ideal_item_found', 'overall_satisfaction',
            'confidence_in_decision', 'would_buy_recommendations',
            'good_group_suggestions', 'convinced_of_items', 'confident_will_like',
            'trust_in_recommender'
        ])
    try:
        return pd.read_csv(io.StringIO(content))
    except pd.errors.EmptyDataError:
        return pd.DataFrame(columns=[
            'user_id', 'group_id', 'top_3_recommendations',
            'matched_interests', 'discovered_new_items', 'diverse_recommendations',
            'easy_to_find', 'ideal_item_found', 'overall_satisfaction',
            'confidence_in_decision', 'would_buy_recommendations',
            'good_group_suggestions', 'convinced_of_items', 'confident_will_like',
            'trust_in_recommender'
        ])

def save_user_review(user_id, group_id, top_3_recommendations, survey_responses):
    """Save user review to GitHub repository."""
    reviews = load_user_reviews()
    new_review = pd.DataFrame({
        'user_id': [user_id],
        'group_id': [group_id],
        'top_3_recommendations': [str(top_3_recommendations)],
        'matched_interests': [survey_responses['matched_interests']],
        'discovered_new_items': [survey_responses['discovered_new_items']],
        'diverse_recommendations': [survey_responses['diverse_recommendations']],
        'easy_to_find': [survey_responses['easy_to_find']],
        'ideal_item_found': [survey_responses['ideal_item_found']],
        'overall_satisfaction': [survey_responses['overall_satisfaction']],
        'confidence_in_decision': [survey_responses['confidence_in_decision']],
        'would_buy_recommendations': [survey_responses['would_buy_recommendations']],
        'good_group_suggestions': [survey_responses['good_group_suggestions']],
        'convinced_of_items': [survey_responses['convinced_of_items']],
        'confident_will_like': [survey_responses['confident_will_like']],
        'trust_in_recommender': [survey_responses['trust_in_recommender']]
    })
    reviews = pd.concat([reviews, new_review], ignore_index=True)
    csv_str = reviews.to_csv(index=False)
    
    # Get current file content and SHA
    _, sha = get_file_from_github(REVIEWS_CSV_PATH)
    if update_file_on_github(REVIEWS_CSV_PATH, csv_str, sha):
        return True
    else:
        st.error("Failed to save review to GitHub")
        return False

# Error handling for missing data files
required_files = [
    "Dominant_Categories.pkl",
    "group_vectors_size_8.pkl",
    "cleaned_dominant_categories_list_reco_grop_size_8_reco_15.pkl",
    "users.csv"
]

missing_files = [f for f in required_files if not os.path.exists(f)]
if missing_files:
    st.error(f"Missing required files: {', '.join(missing_files)}")
    st.stop()

# Load necessary data with error handling
try:
    with open("Dominant_Categories.pkl", "rb") as f:
        Dominant_Categories = pickle.load(f)
        Dominant_Categories = [ele.capitalize() for ele in Dominant_Categories]

    with open("group_vectors_size_8.pkl", "rb") as f:
        group_vectors = pickle.load(f)

    with open("cleaned_dominant_categories_list_reco_grop_size_8_reco_15.pkl", "rb") as f:
        dominant_categories_list_reco = pickle.load(f)
        
    with open("tucson_name_dict.pkl", "rb") as f:
        business_names = pickle.load(f)
except Exception as e:
    st.error(f"Error loading data files: {str(e)}")
    st.stop()

# Initialize session state
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user_id' not in st.session_state:
    st.session_state.user_id = None
if 'group_id' not in st.session_state:
    st.session_state.group_id = None

# Load/save user and response data
def check_user_submission(user_id):
    responses = load_responses()
    return responses[responses['user_id'] == user_id].shape[0] > 0

def validate_preferences(preferences):
    required_fields = [
        'preferred_cuisine',
        'usual_eating_time',
        'preferred_place',
        'main_course',
        'extra_treat',
        'drink_choice',
        'comfort_sip',
        'dietary_preference'
    ]
    
    for field in required_fields:
        if not preferences.get(field):
            st.error(f"Please provide {field.replace('_', ' ')}")
            return False
    return True

def validate_survey_responses(responses):
    required_fields = [
        'matched_interests',
        'discovered_new_items',
        'diverse_recommendations',
        'easy_to_find',
        'ideal_item_found',
        'overall_satisfaction',
        'confidence_in_decision',
        'would_buy_recommendations',
        'good_group_suggestions',
        'convinced_of_items',
        'confident_will_like',
        'trust_in_recommender'
    ]
    
    for field in required_fields:
        if field not in responses or not isinstance(responses[field], int) or not (1 <= responses[field] <= 5):
            st.error(f"Please provide a valid rating (1-5) for {field.replace('_', ' ')}")
            return False
    return True

# Vector similarity functions
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
    responses = load_responses()
    group_responses = responses[responses['group_id'] == group_id]
    
    # Process preferences to exclude "None of the below" and special values
    processed_preferences = []
    for _, row in group_responses.iterrows():
        user_preferences = []
        for key in ['preferred_cuisine', 'usual_eating_time', 'preferred_place', 
                   'main_course', 'extra_treat', 'drink_choice', 'comfort_sip']:
            try:
                values = ast.literal_eval(row[key]) if row[key].startswith("[") else [row[key]]
                # Filter out "None of the below" and special values
                if key == 'dietary_preference':
                    if row[key] not in ["Non-Vegetarian", "No Preference"]:
                        user_preferences.append(row[key])
                else:
                    filtered_values = [v for v in values if v != "None of the below"]
                    user_preferences.extend(filtered_values)
            except:
                if row[key] != "None of the below":
                    user_preferences.append(row[key])
        processed_preferences.extend(user_preferences)
    
    return processed_preferences

def get_recommendations(group_preferences):
    if not group_preferences:  # Check if list is empty
        st.error("No group preferences found.")
        return {}
        
    # Create frequency vector from all preferences
    vec = list_to_frequency_vector(group_preferences)
    
    # Find most similar group and get recommendations
    best_group, _ = find_most_similar_group(vec)
    recommendations = dominant_categories_list_reco[best_group]
    
    if not recommendations:
        st.error("No recommendations found for the group.")
        return {}
        
    return recommendations

def initialize_user_reviews_csv():
    try:
        # Try to read the file to check if it exists
        pd.read_csv('user_reviews.csv')
    except FileNotFoundError:
        # Create the file with proper structure if it doesn't exist
        df = pd.DataFrame(columns=[
            'user_id', 'group_id', 'top_3_recommendations',
            'matched_interests', 'discovered_new_items', 'diverse_recommendations',
            'easy_to_find', 'ideal_item_found', 'overall_satisfaction',
            'confidence_in_decision', 'would_buy_recommendations',
            'good_group_suggestions', 'convinced_of_items', 'confident_will_like',
            'trust_in_recommender'
        ])
        df.to_csv('user_reviews.csv', index=False)

# Initialize the CSV file at the start of the app
initialize_user_reviews_csv()

# Main Streamlit App
st.markdown("<h1 style='text-align: center; color: #2c3e50;'>🍽️ KCGRS Group Eatery Recommender</h1>", unsafe_allow_html=True)

# Session timeout handling
if 'last_activity' not in st.session_state:
    st.session_state.last_activity = datetime.now()
else:
    time_diff = (datetime.now() - st.session_state.last_activity).total_seconds()
    if time_diff > 3600:  # 1 hour timeout
        st.session_state.logged_in = False
        st.session_state.user_id = None
        st.session_state.group_id = None
        st.session_state.last_activity = datetime.now()
        st.error("Session expired. Please login again.")
    else:
        st.session_state.last_activity = datetime.now()

# Login
if not st.session_state.logged_in:
    st.markdown("<h2 style='color: #34495e;'>🔐 Login</h2>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        user_id = st.text_input('User ID', key='login_user_id')
    with col2:
        password = st.text_input('Password', type='password', key='login_password')
    
    if st.button('Login', key='login_button'):
        if not user_id or not password:
            st.error("Please enter both User ID and Password")
        else:
            users_df = load_users()
            user = users_df[(users_df['user_id'] == user_id) & (users_df['password'] == password)]
            if not user.empty:
                st.session_state.logged_in = True
                st.session_state.user_id = user_id
                st.session_state.group_id = user.iloc[0]['group_id']
                st.session_state.last_activity = datetime.now()
                st.success('Login successful!')
                st.rerun()
            else:
                st.error('Invalid credentials')

# Logged-in view
else:
    st.markdown(f"""
        <p style='font-size: 20px; font-weight: bold; color: #ffffff;'>Welcome, {st.session_state.user_id}!</p>
        <p style='font-size: 18px; font-weight: bold; color: #ffffff;'>Group: {st.session_state.group_id}</p>
    """, unsafe_allow_html=True)


    # Add a logout button in the sidebar
    with st.sidebar:
        if st.button('Logout'):
            st.session_state.logged_in = False
            st.session_state.user_id = None
            st.session_state.group_id = None
            st.session_state.last_activity = datetime.now()
            st.rerun()

    # Check if user has already submitted preferences
    user_submitted = check_user_submission(st.session_state.user_id)

    if not user_submitted:
        st.markdown("<h2 style='color: #34495e;'>📝 Dining Preferences Questionnaire</h2>", unsafe_allow_html=True)
        
        with st.container():
           st.markdown("""
                <div style='background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);'>
                    <p style='color: #000000; font-size: 24px; font-weight: bold;'>Please fill in your dining preferences to help us recommend the best options for your group.</p>
                </div>
            """, unsafe_allow_html=True)


        response_data = {
            'preferred_cuisine': (
                st.markdown("""
    <span style='font-size: 18px; font-weight: bold; color: #ffffff;'>Which type of cuisine do you usually prefer when eating out?</span><br>
    <span style='color: #ffffff;'>Please select the one that best matches your taste.</span>
""", unsafe_allow_html=True),
                st.multiselect("", ["None of the below", "Mexican", "African", "Latin", "Italian", "Soul", "Tex", "Mex", "Japanese", "Thai", "Asian", 
                "Chinese", "Southern", "Cajun", "Creole", "Pakistani", "Indian", "Korean", "Vietnamese", 
                "Greek", "Mediterranean", "Hawaiian", "Caribbean", "Cantonese", "Szechuan", "Eastern", 
                "Middle", "American"], placeholder="Choose options")
            ),

            'usual_eating_time': (
st.markdown("""
    <span style='font-size: 18px; font-weight: bold; color: #ffffff;'>When do you typically enjoy eating outside?</span><br>
    <span style='color: #ffffff;'>Select the option that best describes your usual eating time.</span>
""", unsafe_allow_html=True),
                st.selectbox("", ["Breakfast", "Brunch", "Nightlife"], placeholder="Choose an option")
            ),

            'preferred_place': (
st.markdown("""
    <span style='font-size: 18px; font-weight: bold; color: #ffffff;'>What type of place do you usually prefer when eating out?</span><br>
    <span style='color: #ffffff;'>Choose the option that best matches your go-to spot.</span>
""", unsafe_allow_html=True),

                st.multiselect("", ["Restaurants", "Bars", "Cafes", "Diners", "Pubs", "Lounges", "Buffets", 
                "Street Food Stalls"], placeholder="Choose options")
            ),

            'main_course': (
                st.markdown("""
    <span style='font-size: 18px; font-weight: bold; color: #ffffff;'>Which of the following food combinations do you most often go for when eating out?</span><br>
    <span style='color: #ffffff;'>Pick the pair that best matches your usual main course preference.</span>
""", unsafe_allow_html=True),

                st.multiselect("", ["None of the below", "Burgers and Pizza", "Pizza and Wings", "Noodles and Ramen", "Sushi and Ramen",
                "Soup and Sandwiches", "Chicken and Salad", "Tacos and Chips", "Fish and Chips",
                "Cheesesteaks and Chips", "Poke and Salad", "Soup and Noodles"], placeholder="Choose options")
            ),

            'extra_treat': (
                st.markdown("""
    <span style='font-size: 18px; font-weight: bold; color: #ffffff;'>What's your go-to extra treat when eating out?</span><br>
    <span style='color: #ffffff;'>Whether it's a refreshing smoothie or a sweet dessert, pick the combo you just can't skip!</span>
""", unsafe_allow_html=True),
                st.multiselect("", ["None of the below", "Bagels and Juice", "Smoothies and Bagels", "Yogurt and Smoothies", "Desserts"], placeholder="Choose options")
            ),

            'drink_choice': (
               st.markdown("""
    <span style='font-size: 18px; font-weight: bold; color: #ffffff;'>What's your usual drink of choice when dining out?</span><br>
    <span style='color: #ffffff;'>Pick the one that best matches your vibe—whether you're keeping it chill or toasting the night!</span>
""", unsafe_allow_html=True),
                st.multiselect("", ["None of the below", "Cocktail", "Beer", "Juice", "Wine"], placeholder="Choose options")
            ),

            'comfort_sip': (
st.markdown("""
    <span style='font-size: 18px; font-weight: bold; color: #ffffff;'>When it's time for a quick break, what's your sip of comfort?</span><br>
    <span style='color: #ffffff;'>Are you team coffee or team tea?</span>
""", unsafe_allow_html=True),

                    st.multiselect("", ["None of the below", "Coffee", "Tea"], placeholder="Choose options")
            ),

            'dietary_preference': (
            st.markdown("""
    <span style='font-size: 18px; font-weight: bold; color: #ffffff;'>What's your dietary preference when eating out?</span><br>
    <span style='color: #ffffff;'>Do you go for vegan, vegetarian, non-vegetarian or no preference?</span>
""", unsafe_allow_html=True) ,
                st.selectbox("", ["Vegan", "Vegetarian", "Non-Vegetarian", "No Preference"], placeholder="Choose an option")
            )
        }

        # Process the response data to get only the input values
        processed_response_data = {}
        for key, (_, value) in response_data.items():
            processed_response_data[key] = value

        if st.button("Submit Preferences", key="submit_preferences"):
            if validate_preferences(processed_response_data):
                # Check if all required fields have at least one selection
                required_fields = ['preferred_cuisine', 'usual_eating_time', 'preferred_place', 
                                 'main_course', 'extra_treat', 'drink_choice', 'comfort_sip']
                
                if all(processed_response_data.get(field) for field in required_fields):
                    for key in processed_response_data:
                        if isinstance(processed_response_data[key], list):
                            processed_response_data[key] = str(processed_response_data[key])
                    if save_response(st.session_state.user_id, st.session_state.group_id, processed_response_data):
                        st.markdown('<div style="background-color: #d4edda; color: #155724; padding: 15px; border-radius: 5px;">Preferences submitted successfully!</div>', unsafe_allow_html=True)
                        st.rerun()
                else:
                    st.markdown('<div style="background-color: #f8d7da; color: #721c24; padding: 15px; border-radius: 5px;">Please make a selection for each field.</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div style="background-color: #f8d7da; color: #721c24; padding: 15px; border-radius: 5px;">Please fill in all required fields.</div>', unsafe_allow_html=True)

    # Group status and recommendations
    responses = load_responses()
    group_responses = responses[responses['group_id'] == st.session_state.group_id]
    total_submissions = group_responses.shape[0]
    
    st.markdown(f"""
        <div style='background-color: #d1ecf1; color: #0c5460; padding: 15px; border-radius: 5px;'>
            Group submission status: {total_submissions}/8 members have submitted
        </div>
    """, unsafe_allow_html=True)

    # Add refresh button for group status
    if st.button("🔄 Check Group Submission Status", key="refresh_group_status"):
        st.rerun()

    if total_submissions == 8:
        st.markdown("<h2 style='color: #34495e;'>🍽️ Group Recommendations</h2>", unsafe_allow_html=True)
        
        # Get processed preferences for recommendations
        group_preferences = get_group_preferences(st.session_state.group_id)
        if not group_preferences:  # Check if list is empty
            st.error("No valid preferences found in group data.")
            st.stop()
            
        recommendations = get_recommendations(group_preferences)
        
        # Check if user has already rated
        ratings = load_ratings()
        user_ratings = ratings[ratings['user_id'] == st.session_state.user_id]
        user_rated = not user_ratings.empty
        
        if not user_rated:
            # Show recommendations first
            st.markdown("<h3 style='color: #2c3e50;'>Recommended Items</h3>", unsafe_allow_html=True)
            
            # Add refresh button for recommendations
            if st.button("🔄 Refresh Recommendations", key="refresh_recommendations"):
                st.rerun()
            
            for category, score in recommendations.items():
                # Get the business name from the dictionary
                business_name = business_names.get(category, category)  # Fallback to ID if name not found
                # Format the score display
                score_display = f"{score:.2f}" if isinstance(score, (int, float)) else str(score)
                st.markdown(f"""
                    <div style='background-color: #f8f9fa; padding: 15px; border-radius: 8px; margin: 10px 0; 
                    border: 1px solid #e9ecef; box-shadow: 0 2px 4px rgba(0,0,0,0.1);'>
                        <div style='font-weight: bold; color: #2c3e50;'>{business_name}</div>
                        <div style='color: #6c757d; margin-top: 5px;'>Score: {score_display}</div>
                    </div>
                """, unsafe_allow_html=True)
            
            st.markdown("<h3 style='color: #2c3e50;'>Please rate each recommendation (1-5)</h3>", unsafe_allow_html=True)
            st.markdown('<div style="color: #ffffff; margin-bottom: 20px;">1 = Not interested, 5 = Very interested</div>', unsafe_allow_html=True)
            
            # Add refresh button for ratings
            if st.button("🔄 Refresh Ratings", key="refresh_ratings"):
                st.rerun()
            
            # Collect all ratings first
            ratings = {}
            for category, score in recommendations.items():
                business_name = business_names.get(category, category)  # Fallback to ID if name not found
                st.markdown(f"<h3 style='color: #ffffff;font-weight: bold;'>Rate {business_name}</h3>", unsafe_allow_html=True)

                ratings[category] = st.slider(f"from 1 to 5", 1, 5, 3, key=f"{category}_slider")
                
            # Submit all ratings at once
            if st.button("Submit All Ratings", key="submit_ratings"):
                all_rated = True
                for category, rating in ratings.items():
                    if not save_rating(st.session_state.user_id, st.session_state.group_id, category, rating):
                        all_rated = False
                        break
                
                if all_rated:
                    st.markdown('<div style="background-color: #d4edda; color: #155724; padding: 15px; border-radius: 5px;">All ratings submitted successfully!</div>', unsafe_allow_html=True)
                    
                    # Check if all group members have rated
                    group_ratings = load_ratings()
                    unique_users_rated = group_ratings['user_id'].nunique()
                    
                    # Add refresh button for rating status
                    if st.button("🔄 Check Group Rating Status", key="refresh_rating_status"):
                        st.rerun()
                    
                    if unique_users_rated == 8:
                        st.markdown('<div style="background-color: #d1ecf1; color: #0c5460; padding: 15px; border-radius: 5px;">All group members have rated! Click the button below to proceed to the survey.</div>', unsafe_allow_html=True)
                        if st.button("🔄 Proceed to Survey", key="proceed_to_survey"):
                            st.rerun()
                    else:
                        st.markdown(f"""
                            <div style='background-color: #d1ecf1; color: #0c5460; padding: 15px; border-radius: 5px;'>
                                Waiting for other group members to rate ({unique_users_rated}/8 have rated)
                            </div>
                        """, unsafe_allow_html=True)
                        if st.button("🔄 Check Group Progress", key="check_progress"):
                            st.rerun()
                else:
                    st.markdown('<div style="background-color: #f8d7da; color: #721c24; padding: 15px; border-radius: 5px;">Please rate all recommendations before submitting.</div>', unsafe_allow_html=True)
        else:
            # Check if all group members have rated
            group_ratings = load_ratings()
            unique_users_rated = group_ratings['user_id'].nunique()
            
            # Add refresh button for rating status
            if st.button("🔄 Check Group Rating Status", key="refresh_rating_status"):
                st.rerun()
            
            if unique_users_rated == 8:
                # Show top 5 recommendations
                st.markdown("<h2 style='color: #34495e;'>🏆 Top 5 Recommendations Based on Group Ratings</h2>", unsafe_allow_html=True)
                
                # Add refresh button for top recommendations
                if st.button("🔄 Refresh Top Recommendations", key="refresh_top_recommendations"):
                    st.rerun()
                
                top_recommendations = load_ratings().groupby('recommendation')['rating'].mean().sort_values(ascending=False).head(5)
                
                if not top_recommendations.empty:
                    # Display top 5 recommendations with visual indicators
                    st.markdown("<h3 style='color: #2c3e50;'>Your Group's Top Choices</h3>", unsafe_allow_html=True)
                    
                    # Get the best matching group for the current group's preferences
                    group_preferences = get_group_preferences(st.session_state.group_id)
                    if not group_preferences:  # Check if list is empty
                        st.error("No group preferences found.")
                        st.stop()
                    
                    vec = list_to_frequency_vector(group_preferences)
                    best_group, _ = find_most_similar_group(vec)
                    
                    # Consistent color scheme for all recommendations
                    bg_color = "#f8f9fa"
                    text_color = "#2c3e50"
                    
                    for idx, (recommendation, rating) in enumerate(top_recommendations.items(), 1):
                        medal = "🥇" if idx == 1 else "🥈" if idx == 2 else "🥉" if idx == 3 else "🏅" if idx == 4 else "🎖️"
                        
                        # Get business name from the dictionary
                        business_name = business_names.get(recommendation, recommendation)  # Fallback to ID if name not found
                        
                        # Get categories for this recommendation
                        categories = dominant_categories_list_reco[best_group][recommendation]
                        
                        st.markdown(f"""
                            <div style='background-color: {bg_color}; padding: 20px; border-radius: 10px; margin: 15px 0; 
                            border: 2px solid #e9ecef; box-shadow: 0 4px 6px rgba(0,0,0,0.1);'>
                                <div style='font-size: 1.2em; font-weight: bold; color: {text_color};'>{medal} {idx}. {business_name}</div>
                                <div style='color: {text_color}; margin-top: 10px; font-size: 1.1em;'>Average Rating: {rating:.2f}</div>
                                <div style='color: {text_color}; margin-top: 5px; font-size: 1em;'>Categories: {', '.join(categories)}</div>
                            </div>
                        """, unsafe_allow_html=True)
                    
                    # Check if user has already submitted the survey
                    reviews = load_user_reviews()
                    user_reviewed = not reviews[reviews['user_id'] == st.session_state.user_id].empty
                    
                    if not user_reviewed:
                        st.markdown("<h2 style='color: #34495e;'>📝 Feedback Survey</h2>", unsafe_allow_html=True)
                        st.markdown('<div style="color: #666; margin-bottom: 20px;">Please rate your experience with the recommendations (1 = Strongly Disagree, 5 = Strongly Agree)</div>', unsafe_allow_html=True)
                        
                        survey_responses = {
                            'matched_interests': st.slider(
                                "The items recommended to group matched my interests",
                                1, 5, 3,
                                help="How well did the recommendations match your personal preferences?"
                            ),
                            'discovered_new_items': st.slider(
                                "The recommender system helped me discover new items",
                                1, 5, 3,
                                help="Did you find any new or interesting options?"
                            ),
                            'diverse_recommendations': st.slider(
                                "The items recommended to group are diverse",
                                1, 5, 3,
                                help="Were the recommendations varied enough?"
                            ),
                            'easy_to_find': st.slider(
                                "I easily found the recommended items",
                                1, 5, 3,
                                help="How easy was it to understand the recommendations?"
                            ),
                            'ideal_item_found': st.slider(
                                "The recommender helped me find the ideal item while hanging out in a group",
                                1, 5, 3,
                                help="Did you find something you would really like to try?"
                            ),
                            'overall_satisfaction': st.slider(
                                "Overall, I am satisfied with the recommender",
                                1, 5, 3,
                                help="How satisfied are you with the recommendation process?"
                            ), 
                            'confidence_in_decision': st.slider(
                                "The recommender made me more confident about my selection/decision when dining out in a group",
                                1, 5, 3,
                                help="Did the recommendations help you feel more confident about group dining choices?"
                            ),
                            'would_buy_recommendations': st.slider(
                                "I would try the items recommended, given the opportunity when hanging out in a group",
                                1, 5, 3,
                                help="How likely are you to try these recommendations?"
                            ),
                            'good_group_suggestions': st.slider(
                                "The recommender gave me good suggestions for hanging out in group",
                                1, 5, 3,
                                help="How well did the recommendations suit group dining?"
                            ),
                            'convinced_of_items': st.slider(
                                "I am convinced of the items recommended to me",
                                1, 5, 3,
                                help="How convinced are you about the recommended items?"
                            ),
                            'confident_will_like': st.slider(
                                "I am confident I will like the items recommended to me",
                                1, 5, 3,
                                help="How confident are you that you'll enjoy the recommended items?"
                            ),
                            'trust_in_recommender': st.slider(
                                "The recommender can be trusted",
                                1, 5, 3,
                                help="How much do you trust the recommender system?"
                            )
                        }
                        
                        if st.button("Submit Feedback", key="submit_feedback"):
                            if validate_survey_responses(survey_responses):
                                if save_user_review(
                                    st.session_state.user_id,
                                    st.session_state.group_id,
                                    list(top_recommendations.keys()),
                                    survey_responses
                                ):
                                    st.markdown('<div style="background-color: #d4edda; color: #155724; padding: 15px; border-radius: 5px;">Thank you for your feedback! You can now logout.</div>', unsafe_allow_html=True)
                                    st.session_state.logged_in = False
                                    st.session_state.user_id = None
                                    st.session_state.group_id = None
                                    st.rerun()
                            else:
                                st.markdown('<div style="background-color: #f8d7da; color: #721c24; padding: 15px; border-radius: 5px;">Please provide valid ratings for all questions.</div>', unsafe_allow_html=True)
                    else:
                        st.markdown('<div style="background-color: #d4edda; color: #155724; padding: 15px; border-radius: 5px;">Thank you for completing the survey! You can now logout.</div>', unsafe_allow_html=True)
                        if st.button("Logout", key="final_logout"):
                            st.session_state.logged_in = False
                            st.session_state.user_id = None
                            st.session_state.group_id = None
                            st.rerun()
                else:
                    st.markdown('<div style="background-color: #f8d7da; color: #721c24; padding: 15px; border-radius: 5px;">No recommendations available. Please try again later.</div>', unsafe_allow_html=True)
            else:
                st.markdown(f"""
                    <div style='background-color: #d1ecf1; color: #0c5460; padding: 15px; border-radius: 5px;'>
                        Waiting for all group members to rate the recommendations ({unique_users_rated}/8 have rated)
                    </div>
                """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
            <div style='background-color: #d1ecf1; color: #0c5460; padding: 15px; border-radius: 5px;'>
                Waiting for all group members to submit their preferences...
            </div>
        """, unsafe_allow_html=True)

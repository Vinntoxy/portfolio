"""
Flask Application for Portfolio Website
This is the main backend server that handles:
- Serving the portfolio website
- Admin authentication
- File uploads
- API endpoints for dynamic content
- Data management (CRUD operations)
"""

from flask import Flask, render_template, jsonify, request, session
from flask_cors import CORS
from functools import wraps
import os
import json
from datetime import datetime
import hashlib
import secrets
from werkzeug.utils import secure_filename
import uuid

# ========== INITIALIZE FLASK APP ==========
app = Flask(__name__, 
            static_folder='static',
            template_folder='templates')

# Use environment variable for secret key in production (Render sets this automatically)
# Falls back to a random key for local development
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(16))
CORS(app)  # Enable CORS for development

# ========== CONFIGURATION ==========
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'svg', 'webp'}
MAX_FILE_SIZE = 16 * 1024 * 1024  # 16MB

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

# Create upload folders if they don't exist
os.makedirs(os.path.join(UPLOAD_FOLDER, 'logos'), exist_ok=True)
os.makedirs(os.path.join(UPLOAD_FOLDER, 'posters'), exist_ok=True)
os.makedirs(os.path.join(UPLOAD_FOLDER, 'illustrations'), exist_ok=True)
os.makedirs(os.path.join(UPLOAD_FOLDER, 'projects'), exist_ok=True)
os.makedirs(os.path.join(UPLOAD_FOLDER, 'profile'), exist_ok=True)
os.makedirs(os.path.join('static', 'images'), exist_ok=True)

# ========== ADMIN CREDENTIALS ==========
# Use environment variables in production (Render)
# Fallback to defaults for local development
ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
# Default password: admin123 - CHANGE THIS IN PRODUCTION!
ADMIN_PASSWORD_HASH = hashlib.sha256(
    os.environ.get('ADMIN_PASSWORD', 'admin123').encode()
).hexdigest()

# Data file path
DATA_FILE = 'portfolio_data.json'

# ========== HELPER FUNCTIONS ==========
def allowed_file(filename):
    """
    Check if uploaded file has allowed extension
    Args:
        filename: Name of the file to check
    Returns:
        Boolean indicating if file type is allowed
    """
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def login_required(f):
    """
    Decorator to require login for admin routes
    Args:
        f: Function to decorate
    Returns:
        Wrapped function that checks authentication
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return jsonify({'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated_function

def load_data():
    """
    Load data from JSON file
    Returns:
        Dictionary containing all portfolio data
    """
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    
    # Default data structure if file doesn't exist
    return {
        'skills': [],
        'certifications': [],
        'projects': [],
        'sections': {
            'logos': {'title': 'Logos', 'images': []},
            'posters': {'title': 'Posters', 'images': []},
            'illustrations': {'title': 'Illustrations', 'images': []}
        },
        'profile': {
            'name': 'Kelvin Maina',
            'title': 'Graphic Designer & SEO Copywriter',
            'bio': 'Hi! I\'m Kelvin Maina, a passionate Graphic Designer and SEO Copywriter dedicated to creating impactful visuals and compelling content.',
            'profile_image': 'default-profile.jpg'
        }
    }

def save_data(data):
    """
    Save data to JSON file
    Args:
        data: Dictionary containing all portfolio data to save
    """
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)

# ========== PUBLIC ROUTES ==========
@app.route('/')
def index():
    """Serve the main portfolio page"""
    return render_template('portfolio.html')

@app.route('/api/skills')
def get_skills():
    """
    Get all skills with their certifications
    Returns:
        JSON array of skills with nested certifications
    """
    data = load_data()
    skills = data['skills']
    
    # Add certifications to each skill
    for skill in skills:
        skill['certifications'] = [
            c for c in data['certifications'] 
            if c['skill_id'] == skill['id']
        ]
    
    return jsonify(skills)

@app.route('/api/certifications/<int:skill_id>')
def get_certifications(skill_id):
    """
    Get certifications for a specific skill
    Args:
        skill_id: ID of the skill
    Returns:
        JSON array of certifications
    """
    data = load_data()
    certs = [c for c in data['certifications'] if c['skill_id'] == skill_id]
    return jsonify(certs)

@app.route('/api/projects')
def get_projects():
    """Get all projects"""
    data = load_data()
    return jsonify(data['projects'])

@app.route('/api/section/<section_name>')
def get_section(section_name):
    """
    Get images for a specific portfolio section
    Args:
        section_name: Name of the section (logos, posters, illustrations)
    Returns:
        JSON object with section data and image URLs
    """
    data = load_data()
    
    if section_name in data['sections']:
        # Add full URLs for images
        section_data = data['sections'][section_name].copy()
        for img in section_data['images']:
            img['url'] = f"/static/uploads/{section_name}/{img['filename']}"
        return jsonify(section_data)
    
    return jsonify({'error': 'Section not found'}), 404

@app.route('/api/profile')
def get_profile():
    """Get profile information with image URL"""
    data = load_data()
    profile = data.get('profile', {})
    
    if profile.get('profile_image'):
        profile['profile_image_url'] = f"/static/uploads/profile/{profile['profile_image']}"
    
    return jsonify(profile)

# ========== ADMIN AUTH ROUTES ==========
@app.route('/admin')
def admin_login_page():
    """Serve admin login page"""
    return render_template('admin_login.html')

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    """Serve admin dashboard page"""
    return render_template('admin_dashboard.html')

@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    """
    Handle admin login
    Expects JSON: {username: string, password: string}
    Returns:
        Success/failure response
    """
    data = request.json
    username = data.get('username')
    password = data.get('password')
    remember = data.get('remember', False)
    
    # Hash the provided password
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    
    # Check credentials
    if username == ADMIN_USERNAME and password_hash == ADMIN_PASSWORD_HASH:
        session['logged_in'] = True
        session['username'] = username
        if remember:
            session.permanent = True
        return jsonify({'success': True, 'message': 'Logged in successfully'})
    
    return jsonify({'success': False, 'message': 'Invalid credentials'}), 401

@app.route('/api/admin/logout', methods=['POST'])
@login_required
def admin_logout():
    """Handle admin logout"""
    session.clear()
    return jsonify({'success': True, 'message': 'Logged out'})

# ========== FILE UPLOAD ROUTES ==========
@app.route('/api/admin/upload/<section>', methods=['POST'])
@login_required
def upload_image(section):
    """
    Handle image uploads for different sections
    Args:
        section: Target section (logos, posters, illustrations, projects, profile)
    Returns:
        JSON with upload result and image info
    """
    # Validate section
    if section not in ['logos', 'posters', 'illustrations', 'projects', 'profile']:
        return jsonify({'error': 'Invalid section'}), 400
    
    # Check if file was uploaded
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    caption = request.form.get('caption', '')
    
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    # Validate and save file
    if file and allowed_file(file.filename):
        # Generate unique filename to prevent conflicts
        original_filename = secure_filename(file.filename)
        file_extension = original_filename.rsplit('.', 1)[1].lower()
        new_filename = f"{uuid.uuid4().hex}.{file_extension}"
        
        # Save file to disk
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], section, new_filename)
        file.save(file_path)
        
        # Update data file
        data = load_data()
        
        if section == 'profile':
            # Handle profile image
            data['profile']['profile_image'] = new_filename
        
        elif section == 'projects':
            # Handle project image
            project_id = request.form.get('project_id')
            if project_id:
                for project in data['projects']:
                    if project['id'] == int(project_id):
                        project['image'] = f"/static/uploads/projects/{new_filename}"
                        break
        
        else:
            # Handle section images (logos, posters, illustrations)
            image_data = {
                'id': max([img['id'] for img in data['sections'][section]['images']], default=0) + 1,
                'filename': new_filename,
                'caption': caption,
                'uploaded_at': datetime.now().isoformat()
            }
            data['sections'][section]['images'].append(image_data)
        
        save_data(data)
        
        return jsonify({
            'success': True,
            'filename': new_filename,
            'url': f"/static/uploads/{section}/{new_filename}",
            'caption': caption
        })
    
    return jsonify({'error': 'File type not allowed'}), 400

# ========== SKILLS MANAGEMENT ==========
@app.route('/api/admin/skills', methods=['GET', 'POST', 'PUT', 'DELETE'])
@login_required
def manage_skills():
    """
    Manage skills (CRUD operations)
    GET: Return all skills
    POST: Add new skill
    PUT: Update existing skill
    DELETE: Remove skill
    """
    data = load_data()
    
    if request.method == 'GET':
        return jsonify(data['skills'])
    
    elif request.method == 'POST':
        new_skill = request.json
        new_skill['id'] = max([s['id'] for s in data['skills']], default=0) + 1
        new_skill['created_at'] = datetime.now().isoformat()
        data['skills'].append(new_skill)
        save_data(data)
        return jsonify({'success': True, 'skill': new_skill})
    
    elif request.method == 'PUT':
        updated_skill = request.json
        for i, skill in enumerate(data['skills']):
            if skill['id'] == updated_skill['id']:
                data['skills'][i].update(updated_skill)
                save_data(data)
                return jsonify({'success': True, 'skill': data['skills'][i]})
        return jsonify({'error': 'Skill not found'}), 404
    
    elif request.method == 'DELETE':
        skill_id = request.args.get('id', type=int)
        data['skills'] = [s for s in data['skills'] if s['id'] != skill_id]
        # Also remove related certifications
        data['certifications'] = [c for c in data['certifications'] if c['skill_id'] != skill_id]
        save_data(data)
        return jsonify({'success': True})

# ========== CERTIFICATIONS MANAGEMENT ==========
@app.route('/api/admin/certifications', methods=['POST', 'DELETE'])
@login_required
def manage_certifications():
    """
    Manage certifications (CRUD operations)
    POST: Add new certification
    DELETE: Remove certification
    """
    data = load_data()
    
    if request.method == 'POST':
        new_cert = request.json
        new_cert['id'] = max([c['id'] for c in data['certifications']], default=0) + 1
        new_cert['created_at'] = datetime.now().isoformat()
        data['certifications'].append(new_cert)
        save_data(data)
        return jsonify({'success': True, 'certification': new_cert})
    
    elif request.method == 'DELETE':
        cert_id = request.args.get('id', type=int)
        data['certifications'] = [c for c in data['certifications'] if c['id'] != cert_id]
        save_data(data)
        return jsonify({'success': True})

# ========== PROJECTS MANAGEMENT ==========
@app.route('/api/admin/projects', methods=['GET', 'POST', 'PUT', 'DELETE'])
@login_required
def manage_projects():
    """
    Manage projects (CRUD operations)
    GET: Return all projects
    POST: Add new project
    PUT: Update existing project
    DELETE: Remove project
    """
    data = load_data()
    
    if request.method == 'GET':
        return jsonify(data['projects'])
    
    elif request.method == 'POST':
        new_project = request.json
        new_project['id'] = max([p['id'] for p in data['projects']], default=0) + 1
        new_project['created_at'] = datetime.now().isoformat()
        data['projects'].append(new_project)
        save_data(data)
        return jsonify({'success': True, 'project': new_project})
    
    elif request.method == 'PUT':
        updated_project = request.json
        for i, project in enumerate(data['projects']):
            if project['id'] == updated_project['id']:
                data['projects'][i].update(updated_project)
                save_data(data)
                return jsonify({'success': True, 'project': data['projects'][i]})
        return jsonify({'error': 'Project not found'}), 404
    
    elif request.method == 'DELETE':
        project_id = request.args.get('id', type=int)
        data['projects'] = [p for p in data['projects'] if p['id'] != project_id]
        save_data(data)
        return jsonify({'success': True})

# ========== IMAGE DELETION ==========
@app.route('/api/admin/section/<section_name>/images/<int:image_id>', methods=['DELETE'])
@login_required
def delete_section_image(section_name, image_id):
    """
    Delete an image from a section and remove the file
    Args:
        section_name: Section containing the image
        image_id: ID of the image to delete
    Returns:
        Success/failure response
    """
    data = load_data()
    
    if section_name not in data['sections']:
        return jsonify({'error': 'Section not found'}), 404
    
    # Find and delete the image file
    for img in data['sections'][section_name]['images']:
        if img['id'] == image_id:
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], section_name, img['filename'])
            if os.path.exists(file_path):
                os.remove(file_path)
            break
    
    # Remove from data
    data['sections'][section_name]['images'] = [
        img for img in data['sections'][section_name]['images'] 
        if img['id'] != image_id
    ]
    save_data(data)
    return jsonify({'success': True})

# ========== ERROR HANDLERS ==========
@app.errorhandler(404)
def not_found_error(error):
    """Handle 404 errors"""
    return jsonify({'error': 'Resource not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    return jsonify({'error': 'Internal server error'}), 500

@app.errorhandler(413)
def too_large_error(error):
    """Handle file too large errors"""
    return jsonify({'error': 'File too large. Maximum size is 16MB'}), 413

# ========== RUN APPLICATION ==========
if __name__ == '__main__':
    # Production-friendly run configuration
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    port = int(os.environ.get('PORT', 5000))
    
    print("=" * 60)
    print("🎨 PORTFOLIO FLASK APP STARTING...")
    print("=" * 60)
    print(f"📍 Local URL: http://localhost:{port}")
    print("🔐 Admin Login: http://localhost:{port}/admin")
    print(f"👤 Default credentials: {ADMIN_USERNAME} / [PROTECTED]")
    print("📁 Upload folder: static/uploads/")
    print("💾 Data file: portfolio_data.json")
    print(f"🐍 Debug mode: {debug_mode}")
    print("=" * 60)
    print("⚠️  IMPORTANT: Change admin password after first login!")
    print("=" * 60)
    
    # Run the app
    app.run(host='0.0.0.0', port=port, debug=debug_mod
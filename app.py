from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, login_user, login_required, logout_user, current_user, UserMixin

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'

# Initialize the database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Initialize Login Manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


# User model
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

    def __repr__(self):
        return f"<User {self.name}>"

# Load user function for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# Home route
@app.route('/')
def home():
    user_count = User.query.count()
    return render_template('index.html', user_count=user_count)


# Registration route
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        role = request.form['role']
        email = request.form['email']
        password = request.form['password']
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

        new_user = User(name=name, role=role, email=email, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()

        return redirect(url_for('login'))
    return render_template('register.html')


# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            login_user(user)
            if user.role == 'admin':
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('normal_dashboard'))
        else:
            return 'Invalid email or password', 401
    return render_template('login.html')


# Logout route
@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('home'))


# Normal User Dashboard
@app.route('/normal_dashboard', methods=['GET', 'POST'])
@login_required
def normal_dashboard():
    flashcards = []
    
    if request.method == 'POST':
        topic = request.form.get('topic')
        custom_topic = request.form.get('custom_topic')

        selected_topic = custom_topic if custom_topic.strip() else topic

        # Dummy flashcard generation based on topic
        flashcards = generate_flashcards(selected_topic)

    return render_template('normal_dashboard.html', flashcards=flashcards)


# Admin Dashboard
@app.route('/admin_dashboard', methods=['GET', 'POST'])
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        return redirect(url_for('home'))

    users = User.query.all()
    user_count = len(users)

    if request.method == 'POST':
        name = request.form['name']
        role = request.form['role']
        email = request.form['email']
        password = request.form['password']
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

        new_user = User(name=name, role=role, email=email, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()

        return redirect(url_for('admin_dashboard'))

    return render_template('admin_dashboard.html', users=users, user_count=user_count)


# View User Details Route
@app.route('/user_details/<int:user_id>')
@login_required
def user_details(user_id):
    if current_user.role != 'admin':
        return redirect(url_for('home'))

    user = User.query.get_or_404(user_id)
    return render_template('user_details.html', user=user)


# Delete User Route
@app.route('/delete_user/<int:user_id>')
@login_required
def delete_user(user_id):
    if current_user.role != 'admin':
        return redirect(url_for('home'))

    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()

    return redirect(url_for('admin_dashboard'))


# Change user role route
@app.route('/change_role/<int:user_id>')
@login_required
def change_role(user_id):
    if current_user.role != 'admin':
        return redirect(url_for('home'))

    user = User.query.get_or_404(user_id)
    user.role = 'admin' if user.role == 'normal' else 'normal'
    db.session.commit()
    return redirect(url_for('admin_dashboard'))


# Update User Profile
@app.route('/update_profile', methods=['GET', 'POST'])
@login_required
def update_profile():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        user = User.query.get(current_user.id)

        user.name = name
        user.email = email
        db.session.commit()
        
        return redirect(url_for('normal_dashboard'))

    return render_template('update_profile.html', user=current_user)


# Change User Password
@app.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        current_password = request.form['current_password']
        new_password = request.form['new_password']
        user = User.query.get(current_user.id)

        if check_password_hash(user.password, current_password):
            user.password = generate_password_hash(new_password, method='pbkdf2:sha256')
            db.session.commit()
            return redirect(url_for('normal_dashboard'))
        else:
            return 'Incorrect current password', 400
    
    return render_template('change_password.html')


# Function to generate flashcards based on the selected topic
def generate_flashcards(topic):
    # You can make this more intelligent later using AI
    topic = topic.lower()
    sample_flashcards = []

    if topic == 'math':
        sample_flashcards = [
            {"question": "What is 2 + 2?", "answer": "4"},
            {"question": "What is the square root of 16?", "answer": "4"},
            {"question": "What is Pi approximately?", "answer": "3.1416"}
        ]
    elif topic == 'history':
        sample_flashcards = [
            {"question": "Who was the first President of the USA?", "answer": "George Washington"},
            {"question": "In which year did World War II end?", "answer": "1945"},
            {"question": "Where was Napoleon born?", "answer": "Corsica"}
        ]
    elif topic == 'science':
        sample_flashcards = [
            {"question": "What planet is known as the Red Planet?", "answer": "Mars"},
            {"question": "What is the chemical symbol for water?", "answer": "H2O"},
            {"question": "What gas do plants absorb from the atmosphere?", "answer": "Carbon Dioxide"}
        ]
    elif topic == 'literature':
        sample_flashcards = [
            {"question": "Who wrote 'Romeo and Juliet'?", "answer": "William Shakespeare"},
            {"question": "Who is the author of '1984'?", "answer": "George Orwell"},
            {"question": "Which novel starts with 'Call me Ishmael'?", "answer": "Moby Dick"}
        ]
    else:
        # Custom topics - dummy flashcard generation
        sample_flashcards = [
            {"question": f"What is an important fact about {topic}?", "answer": f"{topic.capitalize()} is very interesting!"},
            {"question": f"Why should we learn about {topic}?", "answer": f"Learning about {topic} improves knowledge."},
            {"question": f"Who is famous in {topic}?", "answer": f"A famous figure in {topic} could be researched!"}
        ]
    
    return sample_flashcards


if __name__ == "__main__":
    app.run(debug=True)
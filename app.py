from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, login_user, login_required, logout_user, current_user, UserMixin
import random
from flask import flash
import json
import os

FLASHCARD_FILE = 'flashcards.json'

def load_flashcard_data():
    with open('flashcards.json', 'r') as f:
        return json.load(f)

def save_flashcard_data(data):
    with open('flashcards.json', 'w') as f:
        json.dump(data, f, indent=4)


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
        if User.query.filter_by(email=email).first():
            flash('Email already exists.', 'error')
            return redirect(url_for('register'))
        new_user = User(name=name, role=role, email=email, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        flash('User added successfully!', 'success')  
        return redirect(url_for('login'))
    return render_template('register.html')


# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        selected_role = request.form.get('role')

        # Check if role is selected
        if not selected_role:
            flash("Please select a role while logging in!", "danger")
            return redirect(url_for('login'))

        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            # Role checking logic
            if user.role == 'admin':
                # Admin can log in as any role
                pass
            elif user.role == 'teacher':
                if selected_role == 'admin':
                    flash("Teachers cannot log in as admin!", "danger")
                    return redirect(url_for('login'))
            else:  # Normal user
                if user.role != selected_role:
                    flash(f"Incorrect role selected. Your account is registered as '{user.role.capitalize()}'", "danger")
                    return redirect(url_for('login'))

            login_user(user)
            if selected_role == 'admin':
                return redirect(url_for('admin_dashboard'))
            elif selected_role == 'teacher':
                return redirect(url_for('teacher_dashboard'))
            else:
                return redirect(url_for('normal_dashboard'))

        flash("Invalid credentials")
        return redirect(url_for('login'))
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
    flashcard_data = load_flashcard_data()
    if request.method == 'POST':
        topic = request.form['topic']
        num_flashcards = int(request.form['num_flashcards'])

        if topic not in flashcard_data or not flashcard_data[topic]:
            flash('No questions available for this topic.')
            return redirect(url_for('normal_dashboard'))

        # Fetch random flashcards for the selected topic
        all_questions = flashcard_data.get(topic, [])
        flashcards = random.sample(all_questions, min(num_flashcards, len(all_questions)))
    
    return render_template('normal_dashboard.html', topics=list(flashcard_data.keys()), flashcards=flashcards)


# Admin Dashboard
@app.route('/admin_dashboard', methods=['GET', 'POST'])
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        return redirect(url_for('home'))

    users = User.query.all()
    user_count = len(users)

    return render_template('admin_dashboard.html', users=users, user_count=user_count)


# Teacher Dashboard
@app.route('/teacher_dashboard')
@login_required
def teacher_dashboard():
    if current_user.role not in ['admin', 'teacher']:
        return redirect(url_for('home'))
    return render_template('teacher_dashboard.html')  # Make sure this template exists


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
    roles = ['normal', 'student', 'teacher', 'admin']
    
    # Find the next role in the list
    current_role_index = roles.index(user.role)
    next_role_index = (current_role_index + 1) % len(roles)  # Loop back to start after 'admin'
    user.role = roles[next_role_index]
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


# Predefined questions and answers for each topic
# flashcard_data = load_flashcard_data()


# Route to edit user details (Admin)
@app.route('/edit_user/<int:user_id>', methods=['GET', 'POST'])
@login_required
def edit_user(user_id):
    if current_user.role != 'admin':
        return redirect(url_for('home'))

    user = User.query.get_or_404(user_id)
    if request.method == 'POST':
        user.name = request.form['name']
        user.email = request.form['email']
        user.role = request.form['role']
        db.session.commit()
        return redirect(url_for('admin_dashboard'))
    return render_template('edit_user.html', user=user)


# Admin - Add Flashcard Question
@app.route('/add_question', methods=['GET', 'POST'])
@login_required
def add_question():
    if current_user.role not in ['admin', 'teacher']:
        return redirect(url_for('home'))
    
    if current_user.role == 'admin':
        dashboard_url = url_for('admin_dashboard')
    else:
        dashboard_url = url_for('teacher_dashboard')

    flashcard_data = load_flashcard_data()

    if request.method == 'POST':
        selected_topic = request.form.get('selected_topic')
        new_topic = (request.form.get('new_topic') or '').strip()
        question = request.form['question']
        answer = request.form['answer']
         # Decide which topic to use
        if new_topic:
            topic = new_topic
            if topic not in flashcard_data:
                flashcard_data[topic] = []
        elif selected_topic:
            topic = selected_topic
        else:
            flash('Please select an existing topic or enter a new one.', 'danger')
            return redirect(url_for('add_question'))

        # Append the new question
        flashcard_data[topic].append({'question': question, 'answer': answer})
        save_flashcard_data(flashcard_data)

        flash(f'Question added under topic {topic}!', 'success')
        return redirect(url_for('manage_questions'))
    return render_template('add_question.html', topics=list(flashcard_data.keys()), dashboard_url=dashboard_url)


# # Admin - Update Existing Question
# @app.route('/edit_question/<topic>/<int:index>', methods=['GET', 'POST'])
# @login_required
# def edit_question(topic, index):
#     if current_user.role != 'admin':
#         return redirect(url_for('home'))

#     question_data = flashcard_data.get(topic, [])[index]
#     if request.method == 'POST':
#         new_question = request.form['question']
#         new_answer = request.form['answer']
#         flashcard_data[topic][index] = {'question': new_question, 'answer': new_answer}
#         return redirect(url_for('admin_dashboard'))
#     return render_template('edit_question.html', topic=topic, index=index, data=question_data)


# # Admin - Delete Question
# @app.route('/delete_question/<topic>/<int:index>')
# @login_required
# def delete_question(topic, index):
#     if current_user.role != 'admin':
#         return redirect(url_for('home'))

#     if topic in flashcard_data and index < len(flashcard_data[topic]):
#         del flashcard_data[topic][index]
#     return redirect(url_for('admin_dashboard'))


@app.route('/manage_questions')
@login_required
def manage_questions():
    if current_user.role not in ['admin', 'teacher']:
        return redirect(url_for('home'))

    if current_user.role == 'admin':
        dashboard_url = url_for('admin_dashboard')
    else:
        dashboard_url = url_for('teacher_dashboard')
    
    flashcard_data = load_flashcard_data()

    # Group questions by topic
    return render_template('manage_questions.html', flashcard_data=flashcard_data, dashboard_url=dashboard_url)




@app.route('/edit_question/<topic>/<int:q_index>', methods=['GET', 'POST'])
@login_required
def edit_question(topic, q_index):
    if current_user.role not in ['admin', 'teacher']:
        return redirect(url_for('home'))
    
    if current_user.role == 'admin':
        dashboard_url = url_for('admin_dashboard')
    else:
        dashboard_url = url_for('teacher_dashboard')
    flashcard_data = load_flashcard_data()

    # Check if the topic exists and the question index is valid
    if topic not in flashcard_data or q_index >= len(flashcard_data[topic]):
        flash('Invalid topic or question index.', 'error')
        return redirect(url_for('manage_questions'))

    # Get the current question and answer
    question_data = flashcard_data[topic][q_index]

    if request.method == 'POST':
        # Get the updated question and answer from the form
        question_data['question'] = request.form['question']
        question_data['answer'] = request.form['answer']

        # Save the updated flashcards data
        save_flashcard_data(flashcard_data)

        flash('Question updated successfully.')
        return redirect(url_for('manage_questions'))

    return render_template('edit_question.html', topic=topic, q_index=q_index, question_data=question_data, dashboard_url=dashboard_url)


@app.route('/delete_question/<topic>/<int:q_index>', methods=['GET'])
@login_required
def delete_question(topic, q_index):
    if current_user.role not in ['admin', 'teacher']:
        return redirect(url_for('home'))
    flashcard_data = load_flashcard_data()

    # Check if the topic exists and the question index is valid
    if topic not in flashcard_data or q_index >= len(flashcard_data[topic]):
        flash('Invalid topic or question index.', 'error')
        return redirect(url_for('manage_questions'))

    # Remove the question from the topic
    flashcard_data[topic].pop(q_index)

    # Save the updated flashcards data
    save_flashcard_data(flashcard_data)

    flash('Question deleted successfully.')
    return redirect(url_for('manage_questions'))


# Update User Details Route
@app.route('/update_user/<int:user_id>', methods=['GET', 'POST'])
@login_required
def update_user(user_id):
    if current_user.role != 'admin':
        return redirect(url_for('home'))

    user = User.query.get_or_404(user_id)

    if request.method == 'POST':
        user.name = request.form['name']
        user.email = request.form['email']
        user.role = request.form['role']
        db.session.commit()

        return redirect(url_for('admin_dashboard'))

    return render_template('update_user.html', user=user)


@app.route('/add_user', methods=['GET', 'POST'])
@login_required
def add_user():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        role = request.form['role']
        password = generate_password_hash(request.form['password'])

        if User.query.filter_by(email=email).first():
            flash('Email already exists.', 'error')
            return redirect(url_for('add_user'))

        new_user = User(name=name, email=email, role=role, password=password)
        db.session.add(new_user)
        db.session.commit()
        flash('User added successfully!', 'success')
        return redirect(url_for('admin_dashboard'))

    return render_template('add_user.html')

@app.route('/delete_topic', methods=['POST'])
@login_required
def delete_topic():
    if current_user.role not in ['admin', 'teacher']:
        flash("You are not authorized to delete topics!", "danger")
        return redirect(url_for('dashboard'))

    topic_to_delete = request.form.get('topic_to_delete')

    flashcard_data = load_flashcard_data()
    if topic_to_delete in flashcard_data:
        del flashcard_data[topic_to_delete]
        save_flashcard_data(flashcard_data)
        flash(f"Topic {topic_to_delete} deleted successfully!", "success")
    else:
        flash(f"Topic {topic_to_delete} not found!", "danger")

    return redirect(url_for('manage_questions'))


@app.route('/delete_topic_page')
@login_required
def delete_topic_page():
    if current_user.role not in ['admin', 'teacher']:
        flash("You are not authorized to delete topics!", "danger")
        return redirect(url_for('dashboard'))

    flashcard_data = load_flashcard_data()
    return render_template('delete_topic.html', flashcard_data=flashcard_data)




if __name__ == "__main__":
    app.run(debug=True)
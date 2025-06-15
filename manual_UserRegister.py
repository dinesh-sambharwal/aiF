from app import db, User, app  # Import the app instance directly
from werkzeug.security import generate_password_hash

# Create an admin user inside the app context
with app.app_context():
    # Create the admin user
    admin = User(
        name="name", 
        email="admin@email", 
        role="admin", 
        password=generate_password_hash("sam@123", method='pbkdf2:sha256')
    )

    # Add the admin user to the database
    db.session.add(admin)
    db.session.commit()

    print("Admin user created!")
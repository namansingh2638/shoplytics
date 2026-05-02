from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_mail import Mail
from config import Config

# These are created here but not tied to any app yet
db = SQLAlchemy()
login_manager = LoginManager()
mail = Mail()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)  # loads your config.py settings

    # Connect extensions to the app
    db.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)  

    login_manager.login_view = 'auth.login'  # redirect here if not logged in

    # Register blueprints (modules)
    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    from app.main import bp as main_bp          # new
    app.register_blueprint(main_bp) 

    from app.inventory import bp as inventory_bp
    app.register_blueprint(inventory_bp, url_prefix='/inventory')

    from app.billing import bp as billing_bp
    app.register_blueprint(billing_bp, url_prefix='/billing')

    from app.suppliers import bp as suppliers_bp
    app.register_blueprint(suppliers_bp, url_prefix='/suppliers')

    from app.expenses import bp as expenses_bp
    app.register_blueprint(expenses_bp, url_prefix='/expenses')

    from flask import session

    @app.context_processor
    def inject_session():
        return dict(session=session)
    
    from app.analytics import bp as analytics_bp
    app.register_blueprint(analytics_bp, url_prefix='/analytics')

    return app
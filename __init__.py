from flask import Flask

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'eatbolaga'

    
    from .views import views
    from .auth import auth
    from .routes.schedule import schedule_bp

    
    app.register_blueprint(views, url_prefix='/')
    app.register_blueprint(auth, url_prefix='/auth')
    app.register_blueprint(schedule_bp, url_prefix='/schedule')

    return app

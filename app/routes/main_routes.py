from flask import Blueprint, render_template

main_routes = Blueprint('main', __name__)

@main_routes.route('/')
def index():
    """Serve the main HTML interface."""
    return render_template('printform-client.html')
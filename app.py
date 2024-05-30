# Import software dependencies
import os
from flask import redirect, request
from dash import Dash, html, page_container
import logging
from utils import get_smart, app_settings, reset
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Initialize Dash app and Flask server
app = Dash(__name__, use_pages=True, meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}])
server = app.server
server.secret_key = os.getenv('SECRET_KEY')
app.title = "Smoke Specialist"

# Set logging level from environment variable, default to INFO if not set
log_level = os.environ.get('LOGGING_LEVEL', 'INFO').upper()
app.logger.setLevel(getattr(logging, log_level))
# Create a StreamHandler to write log messages to stdout
stream_handler = logging.StreamHandler()
stream_handler.setLevel(getattr(logging, log_level))
# Add the handler to the app's logger
app.logger.addHandler(stream_handler)

# Dash layout
app.layout = html.Div([page_container])

# Accept user's launch request
@server.route('/launch')
def launch():
    app.logger.info("Received /launch request")
    reset()
    app_settings['launch_token'] = request.args.get('launch')
    smart = get_smart()
    app.logger.info("redirecting to the authorize URL")
    return redirect(smart.authorize_url)

# Request user authentication and data authorization
@server.route('/redirect_uri')
def redirect_uri():
    app.logger.info("Received /redirect_uri request")
    smart = get_smart()
    smart.handle_callback(request.url)
    app.logger.info("redirecting to the /visualization URL")
    return redirect('/visualization')

    
if __name__ == '__main__':
    app.run(port=5000, debug=True)
"""
The following script is used to run the API server located in the `api` directory.
"""

import os
import sys
from api import create_app

app = create_app()

if __name__ == "__main__":
    # Check if the first argument is 'gunicorn' to run with Gunicorn workers
    if len(sys.argv) > 1 and sys.argv[1] == 'gunicorn':
        print("Running with Gunicorn workers")
        # Default to 4 workers, but allow override with second argument
        workers = 4
        if len(sys.argv) > 2:
            workers = int(sys.argv[2])
            
        # Import and use Gunicorn programmatically
        from gunicorn.app.wsgiapp import WSGIApplication
        
        port = int(os.environ.get("PORT", 8080))
        bind_addr = f"0.0.0.0:{port}"
        
        # Set Gunicorn options
        os.environ['GUNICORN_CMD_ARGS'] = f"--bind={bind_addr} --workers={workers} --timeout=1800"
        
        # Run Gunicorn
        WSGIApplication("%(prog)s [OPTIONS] run:app").run()
    else:
        # Regular Flask development server
        print("Running with Flask development server")
        port = int(os.environ.get("PORT", 8080))
        app.run(debug=False, host="0.0.0.0", port=port)

from backend import create_app

# Instantiate the Flask app from factory
app = create_app()

if __name__ == '__main__':
    # Start the server locally
    app.run(host="0.0.0.0", port=5000, debug=True)

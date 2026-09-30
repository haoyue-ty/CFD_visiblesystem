from waitress import serve

from backend import create_app


if __name__ == "__main__":
    app = create_app()
    settings = app.extensions["settings"]
    serve(app, host=settings.api_host, port=settings.api_port)

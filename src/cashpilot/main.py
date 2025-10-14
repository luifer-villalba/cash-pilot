from fastapi import FastAPI
import uvicorn

def create_app() -> FastAPI:
    """
    Factory function to create and configure a FastAPI app instance.
    Returns a new app instance each time it's called, which allows:
    - Fresh app for each test (no shared state)
    - Different configurations per environment (dev/prod/test)
    - Easier dependency injection and mocking
    """
    app = FastAPI(title="CashPilot API", version="0.1.0")

    @app.get("/health", summary="Healthcheck")
    def healthcheck() -> dict[str, str]:
        return {"status": "ok"}

    return app

if __name__ == "__main__":
    app = create_app()
    uvicorn.run(app, host="0.0.0.0", port=8000)
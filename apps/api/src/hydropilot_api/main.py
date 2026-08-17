from fastapi import FastAPI

app = FastAPI(
    title="HydroPilot API",
    version="0.1.0",
    description=(
        "API for the HydroPilot water-network digital twin demonstrator. "
        "Not for operational flood-control or dispatch decisions."
    ),
)


@app.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "hydropilot-api",
    }

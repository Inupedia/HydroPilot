from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError

from hydropilot_api.agent import ReadOnlyAgentRequest, ReadOnlyAgentResponse, run_read_only_agent
from hydropilot_api.config import get_settings
from hydropilot_api.domain import (
    CurveType,
    HydroConstraint,
    HydroCurve,
    HydroObject,
    NetworkPathItem,
    ObjectType,
)
from hydropilot_api.llm import ChatRequest, ChatResponse, LLMProviderError, ProviderSummary, chat_completion, provider_catalog
from hydropilot_api.repositories.fixture import get_fixture_repository
from hydropilot_api.services.scenario import ReleaseScenarioRequest, ReleaseScenarioResponse, run_release_scenario
from hydropilot_api.tools import (
    HydroToolDefinition,
    HydroToolRequest,
    HydroToolResponse,
    execute_tool,
    tool_catalog,
)
from hydropilot_api.topology import downstream_path

settings = get_settings()
app = FastAPI(title="HydroPilot API", version="0.2.0", description="API for the HydroPilot water-network digital twin demonstrator. Not for operational flood-control or dispatch decisions.")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


def repo():
    return get_fixture_repository(str(settings.demo_fixture_path))


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.service_name}


@app.get("/api/objects", response_model=list[HydroObject])
def list_objects(object_type: ObjectType | None = Query(default=None)) -> list[HydroObject]:
    return repo().list_objects(object_type)


@app.get("/api/objects/{object_id}", response_model=HydroObject)
def get_object(object_id: str) -> HydroObject:
    obj = repo().get_object(object_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="object not found")
    return obj


@app.get("/api/objects/{object_id}/curves", response_model=list[HydroCurve])
def list_object_curves(
    object_id: str,
    curve_type: CurveType | None = Query(default=None),
) -> list[HydroCurve]:
    repository = repo()
    if repository.get_object(object_id) is None:
        raise HTTPException(status_code=404, detail="object not found")
    return repository.list_curves(object_id=object_id, curve_type=curve_type)


@app.get("/api/objects/{object_id}/constraints", response_model=list[HydroConstraint])
def list_object_constraints(
    object_id: str,
    variable: str | None = Query(default=None),
) -> list[HydroConstraint]:
    repository = repo()
    if repository.get_object(object_id) is None:
        raise HTTPException(status_code=404, detail="object not found")
    return repository.list_constraints(object_id=object_id, variable=variable)


@app.get("/api/network/{object_id}/downstream", response_model=list[NetworkPathItem])
def get_downstream(object_id: str, max_hops: int = Query(default=8, ge=0, le=25)) -> list[NetworkPathItem]:
    if repo().get_object(object_id) is None:
        raise HTTPException(status_code=404, detail="object not found")
    return downstream_path(object_id, repo().list_relations(), max_hops=max_hops)


@app.get("/api/tools", response_model=list[HydroToolDefinition])
def list_hydro_tools() -> list[HydroToolDefinition]:
    return tool_catalog()


@app.post("/api/tools/execute", response_model=HydroToolResponse)
def execute_hydro_tool(request: HydroToolRequest) -> HydroToolResponse:
    try:
        return execute_tool(repo(), request)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"object not found: {exc.args[0]}") from exc
    except (ValueError, ValidationError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/scenarios/release", response_model=ReleaseScenarioResponse)
def release_scenario(request: ReleaseScenarioRequest) -> ReleaseScenarioResponse:
    try:
        return run_release_scenario(repo(), request)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"object not found: {exc.args[0]}") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/agent/chat", response_model=ReadOnlyAgentResponse)
def agent_chat(request: ReadOnlyAgentRequest) -> ReadOnlyAgentResponse:
    try:
        return run_read_only_agent(repo(), request)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"object not found: {exc.args[0]}") from exc
    except (ValueError, ValidationError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except LLMProviderError as exc:
        detail = str(exc)
        status_code = 400 if "required" in detail else 502
        raise HTTPException(status_code=status_code, detail=detail) from exc


@app.get("/api/llm/providers", response_model=list[ProviderSummary])
def list_llm_providers() -> list[ProviderSummary]:
    return provider_catalog()


@app.post("/api/llm/chat", response_model=ChatResponse)
def llm_chat(request: ChatRequest) -> ChatResponse:
    try:
        return chat_completion(request)
    except LLMProviderError as exc:
        detail = str(exc)
        status_code = 400 if "required" in detail else 502
        raise HTTPException(status_code=status_code, detail=detail) from exc

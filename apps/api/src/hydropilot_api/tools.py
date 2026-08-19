from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from pydantic import BaseModel, Field

from hydropilot_api.domain import CurveType, ObjectType
from hydropilot_api.repositories.protocols import HydroRepository
from hydropilot_api.topology import downstream_path


class GetObjectArgs(BaseModel):
    object_id: str = Field(min_length=1)


class ListObjectsArgs(BaseModel):
    object_type: ObjectType | None = None
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=50, ge=1, le=100)


class ObjectInventoryItem(BaseModel):
    id: str
    name: str
    object_type: ObjectType
    source: str


class ObjectInventoryPage(BaseModel):
    offset: int
    limit: int
    total: int
    items: list[ObjectInventoryItem]


class TraceDownstreamArgs(BaseModel):
    object_id: str = Field(min_length=1)
    max_hops: int = Field(default=8, ge=0, le=25)


class ListCurvesArgs(BaseModel):
    object_id: str = Field(min_length=1)
    curve_type: CurveType | None = None
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=20, ge=1, le=50)


class CurveInventoryItem(BaseModel):
    id: str
    object_id: str
    curve_type: CurveType
    x_unit: str
    y_unit: str
    point_count: int
    source: str


class CurveInventoryPage(BaseModel):
    offset: int
    limit: int
    total: int
    items: list[CurveInventoryItem]


class ListConstraintsArgs(BaseModel):
    object_id: str = Field(min_length=1)
    variable: str | None = None


class HydroToolDefinition(BaseModel):
    name: str
    description: str
    input_schema: dict[str, Any]
    read_only: bool = True


class HydroToolRequest(BaseModel):
    name: str = Field(min_length=1)
    arguments: dict[str, Any] = Field(default_factory=dict)


class HydroToolResponse(BaseModel):
    name: str
    result: Any


ToolHandler = Callable[[HydroRepository, BaseModel], Any]


@dataclass(frozen=True)
class _ToolRegistration:
    description: str
    args_model: type[BaseModel]
    handler: ToolHandler


def _require_object(repo: HydroRepository, object_id: str):
    obj = repo.get_object(object_id)
    if obj is None:
        raise KeyError(object_id)
    return obj


def _get_object(repo: HydroRepository, args: BaseModel):
    values = GetObjectArgs.model_validate(args)
    return _require_object(repo, values.object_id)


def _list_objects(repo: HydroRepository, args: BaseModel):
    values = ListObjectsArgs.model_validate(args)
    objects = repo.list_objects(values.object_type)
    selected = objects[values.offset : values.offset + values.limit]
    return ObjectInventoryPage(
        offset=values.offset,
        limit=values.limit,
        total=len(objects),
        items=[
            ObjectInventoryItem(
                id=item.id,
                name=item.name,
                object_type=item.object_type,
                source=item.source,
            )
            for item in selected
        ],
    )


def _trace_downstream(repo: HydroRepository, args: BaseModel):
    values = TraceDownstreamArgs.model_validate(args)
    _require_object(repo, values.object_id)
    return downstream_path(values.object_id, repo.list_relations(), max_hops=values.max_hops)


def _list_curves(repo: HydroRepository, args: BaseModel):
    values = ListCurvesArgs.model_validate(args)
    _require_object(repo, values.object_id)
    curves = repo.list_curves(object_id=values.object_id, curve_type=values.curve_type)
    selected = curves[values.offset : values.offset + values.limit]
    return CurveInventoryPage(
        offset=values.offset,
        limit=values.limit,
        total=len(curves),
        items=[
            CurveInventoryItem(
                id=item.id,
                object_id=item.object_id,
                curve_type=item.curve_type,
                x_unit=item.x_unit,
                y_unit=item.y_unit,
                point_count=len(item.points),
                source=item.source,
            )
            for item in selected
        ],
    )


def _list_constraints(repo: HydroRepository, args: BaseModel):
    values = ListConstraintsArgs.model_validate(args)
    _require_object(repo, values.object_id)
    return repo.list_constraints(object_id=values.object_id, variable=values.variable)


def _jsonable(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, tuple):
        return [_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    return value


_REGISTRY: dict[str, _ToolRegistration] = {
    "get_object": _ToolRegistration(
        description="Get one water-network object by its stable object id.",
        args_model=GetObjectArgs,
        handler=_get_object,
    ),
    "list_constraints": _ToolRegistration(
        description="List configured operating constraints for one water-network object.",
        args_model=ListConstraintsArgs,
        handler=_list_constraints,
    ),
    "list_curves": _ToolRegistration(
        description="List a bounded page of compact engineering-curve metadata for one water-network object.",
        args_model=ListCurvesArgs,
        handler=_list_curves,
    ),
    "list_objects": _ToolRegistration(
        description="List a bounded page of compact water-network object summaries, optionally filtered by typed object category.",
        args_model=ListObjectsArgs,
        handler=_list_objects,
    ),
    "trace_downstream": _ToolRegistration(
        description="Trace downstream FLOWS_TO relationships from one water-network object.",
        args_model=TraceDownstreamArgs,
        handler=_trace_downstream,
    ),
}


def tool_catalog() -> list[HydroToolDefinition]:
    return [
        HydroToolDefinition(
            name=name,
            description=registration.description,
            input_schema=registration.args_model.model_json_schema(),
            read_only=True,
        )
        for name, registration in sorted(_REGISTRY.items())
    ]


def execute_tool(repo: HydroRepository, request: HydroToolRequest) -> HydroToolResponse:
    registration = _REGISTRY.get(request.name)
    if registration is None:
        raise ValueError(f"unknown hydro tool: {request.name}")

    args = registration.args_model.model_validate(request.arguments)
    result = registration.handler(repo, args)
    return HydroToolResponse(name=request.name, result=_jsonable(result))

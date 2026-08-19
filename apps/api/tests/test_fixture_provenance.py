import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from hydropilot_api.domain import HydroObject, PropertyProvenance, PropertyValueOrigin


FIXTURE_PATH = Path(__file__).resolve().parents[3] / "data" / "demo" / "sacramento_v0_1.json"
RESERVOIR_MODEL_PROPERTIES = ("initial_storage_m3", "max_storage_m3", "initial_level_m")
ROUTING_MODEL_PROPERTIES = ("routing_k_minutes", "routing_x")


def load_objects() -> list[HydroObject]:
    data = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    return [HydroObject.model_validate(item) for item in data["objects"]]


def test_property_provenance_uses_typed_origins():
    for origin in PropertyValueOrigin:
        provenance = PropertyProvenance(
            origin=origin,
            source="test-source",
            note="test-note",
        )
        assert provenance.origin is origin

    with pytest.raises(ValidationError):
        PropertyProvenance(
            origin="trust_me",
            source="test-source",
            note="test-note",
        )


def test_demo_reservoir_model_inputs_have_explicit_assumption_provenance():
    reservoirs = [item for item in load_objects() if item.object_type.value == "reservoir"]
    assert reservoirs

    for reservoir in reservoirs:
        for property_name in RESERVOIR_MODEL_PROPERTIES:
            if property_name not in reservoir.properties:
                continue
            assert property_name in reservoir.property_provenance
            provenance = reservoir.property_provenance[property_name]
            assert provenance.origin is PropertyValueOrigin.MODEL_ASSUMPTION
            assert provenance.source == "HydroPilot Sacramento demo configuration"
            note = (provenance.note or "").lower()
            assert "authoritative" in note
            assert "operational" in note


def test_demo_routing_parameters_are_explicitly_uncalibrated_model_assumptions():
    reaches = [item for item in load_objects() if item.object_type.value == "river_reach"]
    assert reaches

    for reach in reaches:
        for property_name in ROUTING_MODEL_PROPERTIES:
            assert property_name in reach.properties
            assert property_name in reach.property_provenance
            provenance = reach.property_provenance[property_name]
            assert provenance.origin is PropertyValueOrigin.MODEL_ASSUMPTION
            assert provenance.source == "HydroPilot Sacramento demo configuration"
            note = (provenance.note or "").lower()
            assert "uncalibrated" in note
            assert "operational" in note


def test_demo_solver_driving_properties_remain_numeric():
    for item in load_objects():
        for property_name in (*RESERVOIR_MODEL_PROPERTIES, *ROUTING_MODEL_PROPERTIES):
            if property_name in item.properties:
                assert isinstance(item.properties[property_name], (int, float))

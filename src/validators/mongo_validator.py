from typing import Any

from src.api.models import ValidationResult

_ALLOWED_STAGES = {
    "$addFields",
    "$bucket",
    "$bucketAuto",
    "$count",
    "$facet",
    "$geoNear",
    "$group",
    "$limit",
    "$lookup",
    "$match",
    "$merge",
    "$out",
    "$project",
    "$redact",
    "$replaceRoot",
    "$replaceWith",
    "$sample",
    "$set",
    "$skip",
    "$sort",
    "$sortByCount",
    "$unset",
    "$unwind",
}

_FORBIDDEN_STAGES = {
    "$out": "Use $out only to new collections — overwriting existing collections is forbidden",
}


def validate_mongo_pipeline(pipeline: list[dict[str, Any]]) -> ValidationResult:
    """Validate a MongoDB aggregation pipeline for structure and safety."""
    errors: list[str] = []
    warnings: list[str] = []

    if not isinstance(pipeline, list):
        return ValidationResult(is_valid=False, errors=["Pipeline must be a list"])

    if not pipeline:
        return ValidationResult(is_valid=False, errors=["Pipeline is empty"])

    has_limit = False
    has_match = False
    first_stage_is_match = False

    for i, stage in enumerate(pipeline):
        if not isinstance(stage, dict):
            errors.append(f"Stage {i} is not a dict: {stage!r}")
            continue
        if len(stage) != 1:
            errors.append(f"Stage {i} must have exactly one key, got: {list(stage.keys())}")
            continue

        op = next(iter(stage))

        if op not in _ALLOWED_STAGES:
            errors.append(f"Stage {i}: unknown or disallowed operator '{op}'")
            continue

        if op == "$limit":
            has_limit = True
        if op == "$match":
            has_match = True
            if i == 0:
                first_stage_is_match = True

        if op == "$out":
            warnings.append(_FORBIDDEN_STAGES["$out"])
        if op == "$merge":
            warnings.append("$merge can overwrite data — ensure 'whenMatched' strategy is intentional")

    if not has_limit:
        warnings.append("Pipeline should include a $limit stage (default 100)")
    if has_match and not first_stage_is_match:
        warnings.append("Place $match as early as possible in the pipeline for performance")

    return ValidationResult(is_valid=len(errors) == 0, errors=errors, warnings=warnings)

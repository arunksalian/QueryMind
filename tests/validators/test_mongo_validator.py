import pytest
from src.validators.mongo_validator import validate_mongo_pipeline


def test_valid_pipeline_passes():
    pipeline = [
        {"$match": {"status": {"$ne": "cancelled"}}},
        {"$group": {"_id": "$customerId", "total": {"$sum": "$totalAmount"}}},
        {"$sort": {"total": -1}},
        {"$limit": 10},
    ]
    result = validate_mongo_pipeline(pipeline)
    assert result.is_valid
    assert not result.errors


def test_empty_pipeline_fails():
    result = validate_mongo_pipeline([])
    assert not result.is_valid
    assert "empty" in result.errors[0].lower()


def test_non_list_fails():
    result = validate_mongo_pipeline({"$match": {}})  # type: ignore[arg-type]
    assert not result.is_valid


def test_unknown_stage_fails():
    result = validate_mongo_pipeline([{"$badOp": {}}])
    assert not result.is_valid
    assert any("badOp" in e for e in result.errors)


def test_missing_limit_warns():
    pipeline = [
        {"$match": {"status": "shipped"}},
        {"$project": {"customerId": 1}},
    ]
    result = validate_mongo_pipeline(pipeline)
    assert result.is_valid
    assert any("$limit" in w for w in result.warnings)


def test_out_stage_warns():
    pipeline = [
        {"$match": {"status": "shipped"}},
        {"$limit": 10},
        {"$out": "archive"},
    ]
    result = validate_mongo_pipeline(pipeline)
    assert result.is_valid  # warning, not error
    assert any("$out" in w for w in result.warnings)


def test_match_not_first_warns():
    pipeline = [
        {"$project": {"customerId": 1}},
        {"$match": {"status": "shipped"}},
        {"$limit": 10},
    ]
    result = validate_mongo_pipeline(pipeline)
    assert result.is_valid
    assert any("$match" in w for w in result.warnings)


def test_stage_with_multiple_keys_fails():
    result = validate_mongo_pipeline([{"$match": {}, "$limit": 10}])
    assert not result.is_valid
    assert any("exactly one key" in e for e in result.errors)


def test_non_dict_stage_fails():
    result = validate_mongo_pipeline(["not a dict"])  # type: ignore[list-item]
    assert not result.is_valid


def test_full_analytics_pipeline_passes():
    pipeline = [
        {"$match": {"status": {"$ne": "cancelled"}}},
        {"$unwind": "$items"},
        {"$group": {"_id": "$items.productId", "units": {"$sum": "$items.quantity"}}},
        {"$sort": {"units": -1}},
        {"$limit": 100},
        {"$project": {"productId": "$_id", "units": 1, "_id": 0}},
    ]
    result = validate_mongo_pipeline(pipeline)
    assert result.is_valid
    assert not result.errors

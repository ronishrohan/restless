from restless.parser import (
    parse_spec,
    EndpointSpec,
    _operation_to_name,
    _extract_base_url,
    _deduplicate_names,
    _param_type_hint,
)


def test_operation_name_replaces_dots():
    assert _operation_to_name("get", "/v2/{section}.json", None) == "get_v2_section_json"


def test_operation_name_handles_double_dots():
    assert _operation_to_name("get", "/dates/{start_date}..{end_date}", None) == "get_dates_start_date__end_date"


def test_name_deduplication():
    eps = [
        EndpointSpec("get", "/a", "get_users", "", []),
        EndpointSpec("get", "/b", "get_users", "", []),
        EndpointSpec("get", "/c", "get_users", "", []),
        EndpointSpec("get", "/d", "list_pets", "", []),
    ]
    result = _deduplicate_names(eps)
    names = [e.name for e in result]
    assert names == ["get_users", "get_users_2", "get_users_3", "list_pets"]


def test_swagger2_base_url():
    spec = {"host": "api.example.com", "basePath": "/v1", "schemes": ["https"]}
    assert _extract_base_url(spec) == "https://api.example.com/v1"


def test_swagger2_base_url_http():
    spec = {"host": "api.example.com", "basePath": "/", "schemes": ["http"]}
    assert _extract_base_url(spec) == "http://api.example.com/"


def test_openapi3_base_url():
    spec = {"servers": [{"url": "https://api.example.com/v2"}]}
    assert _extract_base_url(spec) == "https://api.example.com/v2"


def test_param_type_hint_integer():
    assert _param_type_hint({"schema": {"type": "integer"}}) == "int"


def test_param_type_hint_boolean():
    assert _param_type_hint({"schema": {"type": "boolean"}}) == "bool"


def test_param_type_hint_array():
    assert _param_type_hint({"schema": {"type": "array", "items": {"type": "string"}}}) == "list"


def test_param_type_hint_array_int():
    assert _param_type_hint({"schema": {"type": "array", "items": {"type": "integer"}}}) == "list[int]"


def test_param_type_hint_object():
    assert _param_type_hint({"schema": {"type": "object"}}) == "dict"


def test_param_type_hint_float():
    assert _param_type_hint({"schema": {"type": "number", "format": "float"}}) == "float"


def test_parse_returns_list_of_endpoints():
    result = parse_spec("tests/fixtures/petstore.yaml")
    assert isinstance(result, list)
    assert len(result) > 0


def test_endpoint_has_required_fields():
    result = parse_spec("tests/fixtures/petstore.yaml")
    ep = result[0]
    assert isinstance(ep, EndpointSpec)
    assert ep.method in ("get", "post", "put", "patch", "delete")
    assert ep.path.startswith("/")
    assert isinstance(ep.name, str)
    assert isinstance(ep.description, str)


def test_endpoint_params_parsed():
    result = parse_spec("tests/fixtures/petstore.yaml")
    get_pet = next(e for e in result if e.path == "/pets/{petId}" and e.method == "get")
    param_names = [p["name"] for p in get_pet.parameters]
    assert "petId" in param_names


def test_filter_by_include():
    result = parse_spec("tests/fixtures/petstore.yaml", include=["GET /pets"])
    assert len(result) == 1
    assert result[0].method == "get"
    assert result[0].path == "/pets"

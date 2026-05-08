from restless.parser import parse_spec, EndpointSpec


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

import pytest
import hashlib
from unittest.mock import patch
from flask import request
from ckan.types import Response

import ckan.views as views


@pytest.mark.ckan_config("ckan.cache_expires", 3600)
def test_sets_cache_control_headers_default():
    """Test that cache control headers are set correctly when caching is allowed."""
    response = Response("Test content", status=200)
    with patch.dict(request.environ, {}):
        updated_response = views.set_cache_control_headers_for_response(response)
    assert updated_response.cache_control.public is True
    assert updated_response.cache_control.max_age == 3600
    assert updated_response.cache_control.must_revalidate is True


@pytest.mark.ckan_config("ckan.cache_expires", 3600)
def test_sets_cache_control_headers_with__no_private_cache__set():
    """Test that cache control headers are set correctly when caching is allowed."""
    response = Response("Test content", status=200)
    with patch.dict(request.environ, {"__no_private_cache__": True}):
        updated_response = views.set_cache_control_headers_for_response(response)
    assert updated_response.cache_control.public is True
    assert updated_response.cache_control.max_age == 3600
    assert updated_response.cache_control.must_revalidate is True


@pytest.mark.ckan_config("ckan.cache_expires", 0)
def test_disables_cache_when_no_cache_env_present():
    """Test that no-cache headers are set when `__no_cache__` is true and `__no_private_cache__` is true in the environment."""
    response = Response("Test content", status=200)
    with patch.dict(request.environ, {"__no_cache__": True, "__no_private_cache__": True}):
        updated_response = views.set_cache_control_headers_for_response(response)
    assert updated_response.cache_control.no_cache is True
    assert updated_response.cache_control.no_store is True
    assert updated_response.cache_control.must_revalidate is True
    assert updated_response.cache_control.max_age == 0


@pytest.mark.ckan_config("ckan.cache_expires", 7200)
def test_sets_private_cache_when___no_cache__is_set_and_no_private_cache_env_present():
    """Test that private cache is set when `__no_private_cache__` is absent but `__no_cache__` is present."""
    response = Response("Test content", status=200)
    with patch.dict(request.environ, {"__no_cache__": True}):
        updated_response = views.set_cache_control_headers_for_response(response)

    assert updated_response.cache_control.private is True
    assert updated_response.cache_control.public is None


@pytest.mark.ckan_config("ckan.cache_expires", 7200)
def test_sets_private_cache_when_no_private_cache_env_present():
    """Test that private cache is set when `__no_private_cache__` is not present but `__no_cache__` is present."""
    response = Response("Test content", status=200)
    with patch.dict(request.environ, {"__no_cache__": True}):
        updated_response = views.set_cache_control_headers_for_response(response)
    assert updated_response.cache_control.private is True
    assert updated_response.cache_control.public is None


@pytest.mark.ckan_config("ckan.cache_expires", 1800)
def test_adds_vary_cookie_when_limit_cache_by_cookie_is_present():
    """Test that `Vary: Cookie` is added when `__limit_cache_by_cookie__` is in the environment."""
    response = Response("Test content", status=200)
    with patch.dict(request.environ, {"__limit_cache_by_cookie__": True}):
        updated_response = views.set_cache_control_headers_for_response(response)
    assert "Cookie" in updated_response.vary


@pytest.mark.ckan_config("ckan.cache_expires", 300)
def test_removes_pragma_header_if_present():
    """Test that the `Pragma` header is removed if present in the response."""
    response = Response("Test content", status=200)
    response.headers["Pragma"] = "no-cache"
    updated_response = views.set_cache_control_headers_for_response(response)

    assert "Pragma" not in updated_response.headers


@pytest.mark.ckan_config("ckan.cache_etags", True)
def test_sets_etag_when_missing():
    """Test that ETag is set if missing in the response headers."""
    response = Response("Test content", status=200)
    updated_response = views.set_etag_and_fast_304_response_if_unchanged(response)
    expected_etag = hashlib.md5(b"Test content").hexdigest()
    assert updated_response.headers["ETag"] == f'"{expected_etag}"'


@pytest.mark.ckan_config("ckan.cache_etags", True)
def test_does_not_modify_etag_if_already_set():
    """Test that an existing ETag is not modified."""
    response = Response("Test content", status=200)
    response.headers["ETag"] = '"existing-etag"'
    updated_response = views.set_etag_and_fast_304_response_if_unchanged(response)
    assert updated_response.headers["ETag"] == '"existing-etag"'


@pytest.mark.ckan_config("ckan.cache_etags", True)
@pytest.mark.ckan_config("ckan.cache_etags_notModified", True)
def test_returns_304_if_etag_matches(response):
    """Test that response is changed to 304 Not Modified if ETag matches request."""
    response = Response("Test content", status=200)
    etag_value = hashlib.md5(b"Test content").hexdigest()
    response.headers["ETag"] = f'"{etag_value}"'

    with patch.object(request, "if_none_match", {f'"{etag_value}"'}):
        updated_response = views.set_etag_and_fast_304_response_if_unchanged(response)

        assert updated_response.status_code == 304
        assert updated_response.get_data() == b""
        assert "Content-Length" not in updated_response.headers


@pytest.mark.ckan_config("ckan.cache_etags", True)
@pytest.mark.ckan_config("ckan.cache_etags_notModified", True)
def test_does_not_return_304_if_etag_does_not_match(response):
    """Test that response is not modified if request's If-None-Match does not match the ETag."""
    response = Response("Test content", status=200)
    response.headers["ETag"] = '"different-etag"'

    with patch.object(request, "if_none_match", {'"some-other-etag"'}):
        updated_response = views.set_etag_and_fast_304_response_if_unchanged(response)

        assert updated_response.status_code == 200
        assert updated_response.get_data() == b"Test content"

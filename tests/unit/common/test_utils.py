# -*- coding: utf-8 -*-
# Copyright 2023 OpenSPG Authors
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except
# in compliance with the License. You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software distributed under the License
# is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
# or implied.

import os
import tempfile
from unittest.mock import patch, Mock
import requests
import pytest

from kag.common.utils import download_from_http


def test_download_from_http_success():
    """Test successful download from HTTP URL."""
    # Use a small test file from W3C
    url = "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf"
    result = download_from_http(url)

    assert os.path.exists(result)
    assert result.endswith("dummy.pdf")
    assert os.path.getsize(result) > 0

    # Clean up
    if os.path.exists(result):
        os.remove(result)


def test_download_from_http_with_dest():
    """Test download with specified destination."""
    url = "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf"
    dest_dir = tempfile.gettempdir()
    dest_path = os.path.join(dest_dir, "test_download.pdf")

    result = download_from_http(url, dest_path)

    assert result == dest_path
    assert os.path.exists(result)
    assert os.path.getsize(result) > 0

    # Clean up
    if os.path.exists(result):
        os.remove(result)


@patch("kag.common.utils.requests.get")
def test_download_from_http_retry_on_503(mock_get):
    """Test that download_from_http retries on 503 errors with exponential backoff."""
    # Mock response for 503 error
    mock_response_503 = Mock()
    mock_response_503.status_code = 503
    mock_response_503.raise_for_status.side_effect = requests.exceptions.HTTPError(
        "503 Server Error: Service Unavailable"
    )

    # Mock successful response
    mock_response_success = Mock()
    mock_response_success.status_code = 200
    mock_response_success.iter_content = lambda chunk_size: [b"test content"]

    # First two calls return 503, third call succeeds
    mock_get.side_effect = [mock_response_503, mock_response_503, mock_response_success]

    # Should succeed after retries
    result = download_from_http("http://example.com/test.txt")

    # Verify it was called 3 times (2 failures + 1 success)
    assert mock_get.call_count == 3
    assert os.path.exists(result)

    # Clean up
    if os.path.exists(result):
        os.remove(result)


@patch("kag.common.utils.requests.get")
def test_download_from_http_max_retries_exceeded(mock_get):
    """Test that download_from_http raises error after max retries."""
    # Mock response that always returns 503
    mock_response = Mock()
    mock_response.status_code = 503
    mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
        "503 Server Error: Service Unavailable"
    )

    mock_get.return_value = mock_response

    # Should raise HTTPError after 3 attempts
    with pytest.raises(requests.exceptions.HTTPError):
        download_from_http("http://example.com/test.txt")

    # Verify it was called 3 times (max retries)
    assert mock_get.call_count == 3

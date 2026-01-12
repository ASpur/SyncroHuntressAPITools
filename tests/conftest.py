import pytest


@pytest.fixture
def mock_settings():
    """Provide mock API settings for testing."""
    return {
        "SyncroSubDomain": "testcompany",
        "SyncroAPIKey": "fake-syncro-api-key",
        "HuntressAPIKey": "fake-huntress-api-key",
        "HuntressSecretKey": "fake-huntress-secret",
        "Debug": False,
    }


@pytest.fixture
def sample_syncro_assets():
    """Sample Syncro assets response data."""
    return [
        {"id": 1, "name": "WORKSTATION-001"},
        {"id": 2, "name": "WORKSTATION-002"},
        {"id": 3, "name": "SERVER-001"},
        {"id": 4, "name": "LAPTOP-SALES"},
    ]


@pytest.fixture
def sample_huntress_agents():
    """Sample Huntress agents response data."""
    return [
        {"id": 101, "hostname": "WORKSTATION-001"},
        {"id": 102, "hostname": "WORKSTATION-002"},
        {"id": 103, "hostname": "SERVER-002"},
        {"id": 104, "hostname": "DESKTOP-HR"},
    ]


@pytest.fixture
def sample_syncro_tickets():
    """Sample Syncro tickets response data."""
    return [
        {"id": 1, "subject": "Printer not working", "status": "Open"},
        {"id": 2, "subject": "Email issue", "status": "Closed"},
    ]

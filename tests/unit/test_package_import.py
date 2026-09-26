def test_package_exposes_version() -> None:
    import agent_reliability

    assert agent_reliability.__version__ == "0.1.0"

def test_package_version_is_semver_like() ->None:
    import agent_reliability
    
    parts = agent_reliability.__version__.split(".")
    
    assert len(parts) == 3
    assert all(part.isdigit() for part in parts)
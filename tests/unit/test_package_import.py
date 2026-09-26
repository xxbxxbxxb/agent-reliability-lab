def test_package_exposes_version() -> None:
    import agent_reliability

    assert agent_reliability.__version__ == "0.1.0"
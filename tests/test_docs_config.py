from unittest.mock import MagicMock, patch
from src.infrastructure.settings import ENVIRONMENT

def test_docs_disabled_in_production():
    mock_config = MagicMock()
    mock_config.app.environment = ENVIRONMENT.PRODUCTION
    
    with patch("src.infrastructure.load_config", return_value=mock_config):
        # We need to reload the module to trigger the top-level FastAPI initialization
        import importlib
        import src.main
        importlib.reload(src.main)
        
        assert src.main.app.docs_url is None
        assert src.main.app.redoc_url is None

def test_docs_enabled_in_development():
    mock_config = MagicMock()
    mock_config.app.environment = ENVIRONMENT.DEVELOPMENT
    
    with patch("src.infrastructure.load_config", return_value=mock_config):
        # We need to reload the module to trigger the top-level FastAPI initialization
        import importlib
        import src.main
        importlib.reload(src.main)
        
        assert src.main.app.docs_url == "/docs"
        assert src.main.app.redoc_url == "/redoc"

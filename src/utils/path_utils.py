"""
Path utility functions for resolving paths relative to ENVIRONMENT_PATH.
"""

import os
from pathlib import Path
from typing import Optional


def get_base_path() -> Path:
    """
    Get the base deployment path from ENVIRONMENT_PATH or current directory.
    
    Returns:
        Path object representing the base deployment path
    """
    env_path = os.getenv('ENVIRONMENT_PATH')
    if env_path:
        return Path(env_path)
    return Path.cwd()


def resolve_path(relative_path: str, base_path: Optional[str] = None) -> Path:
    """
    Resolve a relative path to an absolute path using ENVIRONMENT_PATH.
    
    Args:
        relative_path: Relative path to resolve (e.g., 'logs', 'models/lstm')
        base_path: Optional base path override (uses ENVIRONMENT_PATH if not provided)
    
    Returns:
        Resolved absolute Path object
    
    Examples:
        >>> resolve_path('logs')
        Path('C:/crypto-ia/logs')  # if ENVIRONMENT_PATH=C:\crypto-ia
        
        >>> resolve_path('models/lstm')
        Path('C:/crypto-ia/models/lstm')
    """
    if base_path:
        base = Path(base_path)
    else:
        base = get_base_path()
    
    return base / relative_path


def ensure_directory(path: str, base_path: Optional[str] = None) -> Path:
    """
    Ensure a directory exists, creating it if necessary.
    
    Args:
        path: Directory path (relative or absolute)
        base_path: Optional base path for relative paths
    
    Returns:
        Resolved Path object
    """
    resolved = resolve_path(path, base_path)
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def get_log_path(log_file: str = 'logs/crypto_saas.log') -> Path:
    """
    Get the full path for a log file.
    
    Args:
        log_file: Relative log file path
    
    Returns:
        Resolved Path object for the log file
    """
    return resolve_path(log_file)


def get_model_path(model_name: str = 'models') -> Path:
    """
    Get the full path for model storage.
    
    Args:
        model_name: Model directory name
    
    Returns:
        Resolved Path object for model storage
    """
    return resolve_path(model_name)


def get_cert_path(cert_file: str) -> Path:
    """
    Get the full path for a certificate file.
    
    Args:
        cert_file: Certificate file path (can be relative or absolute)
    
    Returns:
        Resolved Path object
    """
    cert_path = Path(cert_file)
    if cert_path.is_absolute():
        return cert_path
    return resolve_path(cert_file)

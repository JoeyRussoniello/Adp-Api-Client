import re
from typing import Any
from urllib.parse import quote


def extract_path_parameters(path: str) -> list[str]:
    """
    Extract path parameter names from a URL path template.

    Args:
        path: URL path template (e.g., '/hr/workers/{workerId}')

    Returns:
        List of parameter names found in curly braces

    Example:
        >>> extract_path_parameters('/hr/workers/{workerId}/jobs/{jobId}')
        ['workerId', 'jobId']
    """
    pattern = r"\{([^}]+)\}"
    return re.findall(pattern, path)


def validate_path_parameters(path: str, parameters: dict[str, Any]) -> tuple[bool, list[str]]:
    """
    Validate that all required path parameters are provided.

    Args:
        path: URL path template
        provided_params: Dictionary of provided parameters

    Returns:
        Tuple of (is_valid, missing_parameters)
    """
    required_params = extract_path_parameters(path)
    missing_params = [param for param in required_params if param not in parameters]
    return (len(missing_params) == 0, missing_params)


def substitute_path_parameters(path: str, params: dict[str, Any]) -> list[str]:
    """
    Substitute path parameters with actual values.
    Handles both single values and lists of values.

    Args:
        path: URL path template
        params: Dictionary of parameter values (can be single values or lists)

    Returns:
        List of fully constructed paths (one per value if lists provided)

    Example:
        >>> substitute_path_parameters('/hr/workers/{workerId}', {'workerId': ['123', '456']})
        ['/hr/workers/123', '/hr/workers/456']
    """
    is_valid, missing = validate_path_parameters(path, params)
    if not is_valid:
        raise ValueError(f"Missing required path parameters: {', '.join(missing)}")

    # Determine if any parameter is a list
    list_params = {k: v for k, v in params.items() if isinstance(v, list)}

    if not list_params:
        # No lists, single substitution
        return [_substitute_single_path(path, params)]

    # Handle list parameters - generate all combinations
    # For simplicity, assume only one parameter should be a list
    if len(list_params) > 1:
        raise ValueError("Only one path parameter can accept a list of values")

    list_param_name, list_values = next(iter(list_params.items()))
    result_paths = []

    for value in list_values:
        current_params = params.copy()
        current_params[list_param_name] = value
        result_paths.append(_substitute_single_path(path, current_params))

    return result_paths


def _substitute_single_path(path: str, params: dict[str, Any]) -> str:
    """
    Substitute a single set of parameters into a path template.

    Args:
        path: URL path template
        params: Dictionary of single parameter values (no lists)

    Returns:
        Fully constructed path with URL-encoded values
    """
    result = path
    for param_name, param_value in params.items():
        placeholder = f"{{{param_name}}}"
        # URL encode the parameter value
        encoded_value = quote(str(param_value), safe="")
        result = result.replace(placeholder, encoded_value)

    return result


def is_valid_endpoint_path(path: str) -> bool:
    """
    Validate that an endpoint path follows expected format.

    Checks that the path starts with a slash, has balanced curly braces, and that
    placeholders are properly formatted.

    Args:
        path: URL path to validate

    Returns:
        True if path is valid, False otherwise

    Example:
        >>> is_valid_endpoint_path('/hr/workers/{workerId}')
        True
        >>> is_valid_endpoint_path('invalid')
        False
    """
    # Path should start with /
    if not path.startswith("/"):
        return False

    # Check for balanced curly braces
    if path.count("{") != path.count("}"):
        return False

    # Check that placeholders are properly formatted
    pattern = r"\{[a-zA-Z_][a-zA-Z0-9_]*\}"
    placeholders = re.findall(r"\{[^}]*\}", path)

    return all(re.match(pattern, placeholder) for placeholder in placeholders)

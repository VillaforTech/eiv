"""Especificación interactiva verificable: bounded formal core."""

from .logic import analyze_spec, evaluate_world, validate_spec
from .workflow import analyze_case

__all__ = ["analyze_spec", "evaluate_world", "validate_spec", "analyze_case"]

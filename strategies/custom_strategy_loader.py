"""
Custom Strategy Loader

Handles dynamic loading, validation, and management of user-uploaded custom strategies.
Ensures strategies conform to BaseStrategy contract and are safe to execute.
"""

import os
import ast
import importlib.util
import inspect
import sys
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
import logging

from strategies.base_strategy import BaseStrategy

logger = logging.getLogger(__name__)


class CustomStrategyLoader:
    """Loads and validates user-uploaded custom strategy files"""

    CUSTOM_STRATEGIES_DIR = os.path.join(os.path.dirname(__file__), 'custom')

    # Security: Disallowed imports for safety
    DISALLOWED_IMPORTS = {
        'os', 'sys', 'subprocess', 'shutil', 'pathlib',
        'pickle', 'shelve', 'marshal', 'imp',
        'socket', 'urllib', 'requests', 'http',
        '__import__', 'eval', 'exec', 'compile',
        'open', 'input', 'file'
    }

    # Allowed safe imports for strategy development
    ALLOWED_IMPORTS = {
        'numpy', 'np', 'pandas', 'pd', 'ta', 'talib',
        'typing', 'dataclasses', 'datetime', 'math',
        'strategies.base_strategy', 'BaseStrategy'
    }

    def __init__(self):
        """Initialize the custom strategy loader"""
        self.loaded_strategies: Dict[str, type] = {}
        self.strategy_metadata: Dict[str, Dict] = {}
        self._ensure_custom_dir()

    def _ensure_custom_dir(self):
        """Ensure the custom strategies directory exists"""
        os.makedirs(self.CUSTOM_STRATEGIES_DIR, exist_ok=True)

        # Create __init__.py if it doesn't exist
        init_file = os.path.join(self.CUSTOM_STRATEGIES_DIR, '__init__.py')
        if not os.path.exists(init_file):
            with open(init_file, 'w') as f:
                f.write('"""Custom Strategies Module"""\n')

    def validate_strategy_code(self, code: str, filename: str) -> Tuple[bool, Optional[str], Optional[Dict]]:
        """
        Validate strategy code before loading

        Args:
            code: Python code as string
            filename: Name of the file (for error messages)

        Returns:
            Tuple of (is_valid, error_message, metadata)
        """
        try:
            # Parse the code into an AST
            tree = ast.parse(code, filename=filename)
        except SyntaxError as e:
            return False, f"Syntax error in strategy code: {str(e)}", None

        # Check for disallowed imports
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if any(disallowed in alias.name for disallowed in self.DISALLOWED_IMPORTS):
                        return False, f"Disallowed import detected: {alias.name}", None

            elif isinstance(node, ast.ImportFrom):
                if node.module and any(disallowed in node.module for disallowed in self.DISALLOWED_IMPORTS):
                    return False, f"Disallowed import detected: {node.module}", None

            # Check for dangerous function calls
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id in ['eval', 'exec', 'compile', '__import__']:
                        return False, f"Dangerous function call detected: {node.func.id}", None

        # Find strategy class
        strategy_classes = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Check if it inherits from BaseStrategy
                for base in node.bases:
                    if isinstance(base, ast.Name) and base.id == 'BaseStrategy':
                        strategy_classes.append(node.name)
                    elif isinstance(base, ast.Attribute) and base.attr == 'BaseStrategy':
                        strategy_classes.append(node.name)

        if not strategy_classes:
            return False, "No class inheriting from BaseStrategy found", None

        if len(strategy_classes) > 1:
            return False, f"Multiple strategy classes found: {', '.join(strategy_classes)}. Only one class per file is allowed.", None

        # Extract metadata
        metadata = {
            'class_name': strategy_classes[0],
            'filename': filename,
            'has_docstring': False,
            'methods': []
        }

        # Get class details
        for node in tree.body:
            if isinstance(node, ast.ClassDef) and node.name == strategy_classes[0]:
                if ast.get_docstring(node):
                    metadata['has_docstring'] = True
                    metadata['description'] = ast.get_docstring(node)

                # Check for required methods
                methods = [m.name for m in node.body if isinstance(m, ast.FunctionDef)]
                metadata['methods'] = methods

                required_methods = ['analyze', 'get_required_timeframes', 'get_required_indicators']
                missing_methods = [m for m in required_methods if m not in methods]

                if missing_methods:
                    return False, f"Missing required methods: {', '.join(missing_methods)}", None

        return True, None, metadata

    def save_strategy_file(self, filename: str, code: str, user_id: Optional[int] = None) -> Tuple[bool, str]:
        """
        Save a strategy file to the custom directory

        Args:
            filename: Name of the file (should end with .py)
            code: Python code as string
            user_id: Optional user ID for multi-user tracking

        Returns:
            Tuple of (success, message)
        """
        # Ensure filename is safe
        if not filename.endswith('.py'):
            filename += '.py'

        # Sanitize filename
        safe_filename = "".join(c for c in filename if c.isalnum() or c in ('_', '-', '.')).rstrip()

        if not safe_filename or safe_filename == '.py':
            return False, "Invalid filename"

        # Validate the code first
        is_valid, error_msg, metadata = self.validate_strategy_code(code, safe_filename)
        if not is_valid:
            return False, f"Validation failed: {error_msg}"

        # Save the file
        filepath = os.path.join(self.CUSTOM_STRATEGIES_DIR, safe_filename)

        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(code)

            logger.info(f"Custom strategy saved: {safe_filename} (user_id: {user_id})")
            return True, f"Strategy '{safe_filename}' saved successfully"

        except Exception as e:
            logger.error(f"Failed to save strategy file: {str(e)}")
            return False, f"Failed to save file: {str(e)}"

    def load_strategy_from_file(self, filename: str) -> Tuple[bool, Optional[type], Optional[str]]:
        """
        Load a strategy class from a file

        Args:
            filename: Name of the .py file in custom directory

        Returns:
            Tuple of (success, strategy_class, error_message)
        """
        filepath = os.path.join(self.CUSTOM_STRATEGIES_DIR, filename)

        if not os.path.exists(filepath):
            return False, None, f"File not found: {filename}"

        try:
            # Read the file
            with open(filepath, 'r', encoding='utf-8') as f:
                code = f.read()

            # Validate before loading
            is_valid, error_msg, metadata = self.validate_strategy_code(code, filename)
            if not is_valid:
                return False, None, error_msg

            # Load the module dynamically
            module_name = f"strategies.custom.{filename[:-3]}"  # Remove .py extension
            spec = importlib.util.spec_from_file_location(module_name, filepath)

            if spec is None or spec.loader is None:
                return False, None, f"Failed to create module spec for {filename}"

            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)

            # Find the strategy class
            strategy_class = None
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if issubclass(obj, BaseStrategy) and obj is not BaseStrategy:
                    strategy_class = obj
                    break

            if strategy_class is None:
                return False, None, "No valid strategy class found in file"

            # Store metadata
            strategy_id = filename[:-3]  # Remove .py
            self.loaded_strategies[strategy_id] = strategy_class
            self.strategy_metadata[strategy_id] = metadata

            logger.info(f"Successfully loaded custom strategy: {strategy_id} ({metadata['class_name']})")
            return True, strategy_class, None

        except Exception as e:
            logger.error(f"Failed to load strategy from {filename}: {str(e)}", exc_info=True)
            return False, None, f"Error loading strategy: {str(e)}"

    def load_all_custom_strategies(self) -> Dict[str, type]:
        """
        Load all valid strategy files from the custom directory

        Returns:
            Dictionary mapping strategy_id to strategy class
        """
        loaded = {}

        if not os.path.exists(self.CUSTOM_STRATEGIES_DIR):
            logger.warning("Custom strategies directory does not exist")
            return loaded

        for filename in os.listdir(self.CUSTOM_STRATEGIES_DIR):
            if filename.endswith('.py') and not filename.startswith('__'):
                success, strategy_class, error = self.load_strategy_from_file(filename)
                if success and strategy_class:
                    strategy_id = filename[:-3]
                    loaded[strategy_id] = strategy_class
                else:
                    logger.warning(f"Skipped {filename}: {error}")

        logger.info(f"Loaded {len(loaded)} custom strategies")
        return loaded

    def delete_strategy(self, filename: str) -> Tuple[bool, str]:
        """
        Delete a custom strategy file

        Args:
            filename: Name of the .py file to delete

        Returns:
            Tuple of (success, message)
        """
        if not filename.endswith('.py'):
            filename += '.py'

        filepath = os.path.join(self.CUSTOM_STRATEGIES_DIR, filename)

        if not os.path.exists(filepath):
            return False, f"File not found: {filename}"

        try:
            os.remove(filepath)

            # Remove from loaded strategies
            strategy_id = filename[:-3]
            if strategy_id in self.loaded_strategies:
                del self.loaded_strategies[strategy_id]
            if strategy_id in self.strategy_metadata:
                del self.strategy_metadata[strategy_id]

            logger.info(f"Deleted custom strategy: {filename}")
            return True, f"Strategy '{filename}' deleted successfully"

        except Exception as e:
            logger.error(f"Failed to delete strategy: {str(e)}")
            return False, f"Failed to delete file: {str(e)}"

    def list_custom_strategies(self) -> List[Dict[str, Any]]:
        """
        List all custom strategies with metadata

        Returns:
            List of dictionaries with strategy information
        """
        strategies = []

        if not os.path.exists(self.CUSTOM_STRATEGIES_DIR):
            return strategies

        for filename in os.listdir(self.CUSTOM_STRATEGIES_DIR):
            if filename.endswith('.py') and not filename.startswith('__'):
                filepath = os.path.join(self.CUSTOM_STRATEGIES_DIR, filename)
                strategy_id = filename[:-3]

                # Get file stats
                stat = os.stat(filepath)

                strategy_info = {
                    'id': strategy_id,
                    'filename': filename,
                    'created_at': stat.st_ctime,
                    'modified_at': stat.st_mtime,
                    'size': stat.st_size,
                    'loaded': strategy_id in self.loaded_strategies,
                    'metadata': self.strategy_metadata.get(strategy_id, {})
                }

                strategies.append(strategy_info)

        return strategies

    def get_strategy_code(self, filename: str) -> Optional[str]:
        """
        Get the source code of a custom strategy

        Args:
            filename: Name of the .py file

        Returns:
            Source code as string, or None if not found
        """
        if not filename.endswith('.py'):
            filename += '.py'

        filepath = os.path.join(self.CUSTOM_STRATEGIES_DIR, filename)

        if not os.path.exists(filepath):
            return None

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Failed to read strategy file: {str(e)}")
            return None


# Singleton instance
_loader_instance = None

def get_custom_strategy_loader() -> CustomStrategyLoader:
    """Get the singleton CustomStrategyLoader instance"""
    global _loader_instance
    if _loader_instance is None:
        _loader_instance = CustomStrategyLoader()
    return _loader_instance

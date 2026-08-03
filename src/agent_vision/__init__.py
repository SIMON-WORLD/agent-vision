"""agent-vision: give any AI agent vision capability.

The package provides a CLI (``see``) and a local image-stripping proxy
so text-only agents can work with images through OpenAI-compatible
vision providers.
"""

from .cli import main
from .version import VERSION

__version__ = VERSION
__all__ = ["main", "__version__"]

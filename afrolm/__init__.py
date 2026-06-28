"""AfroLM — Foundation language model for African languages."""

__version__ = "0.1.0"
__all__ = ["AfroLMConfig", "AfroLMModel", "AfroLMTokenizer"]

from afrolm.model.architecture import AfroLMConfig, AfroLMModel
from afrolm.data.tokenization import AfroLMTokenizer

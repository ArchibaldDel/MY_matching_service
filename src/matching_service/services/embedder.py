import logging

import numpy as np
import numpy.typing as npt
import torch
from transformers import (
    AutoModel,
    AutoTokenizer,
    PreTrainedModel,
    PreTrainedTokenizer,
)
from tqdm import tqdm

logger = logging.getLogger(__name__)


class TextEmbedder:
    def __init__(
        self,
        model_name: str,
        device: str | None = None,
        max_text_length: int = 256,
        min_clamp_value: float = 1e-9,
    ) -> None:
        if device is None:
            device = "cpu"
            if torch.cuda.is_available():
                device = "cuda"
                logger.info("CUDA available - using GPU acceleration")
        
        self._device: str = device
        self._max_text_length: int = max_text_length
        self._min_clamp_value: float = min_clamp_value
        self._tokenizer: PreTrainedTokenizer = AutoTokenizer.from_pretrained(model_name)
        self._model: PreTrainedModel = AutoModel.from_pretrained(model_name).to(self._device)
        self._model.eval()
        
        self._embedding_dim: int = self._model.config.hidden_size
        
        logger.info(
            "TextEmbedder initialized | model=%s | device=%s | dim=%s",
            model_name,
            self._device,
            self._embedding_dim,
        )

    def _mean_pooling(
        self, token_embeddings: torch.Tensor, attention_mask: torch.Tensor
    ) -> torch.Tensor:
        mask = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
        sum_embeddings = torch.sum(token_embeddings * mask, dim=1)
        sum_mask = mask.sum(dim=1).clamp(min=self._min_clamp_value)
        return sum_embeddings / sum_mask

    def _process_batch(
        self, texts: list[str], normalize: bool
    ) -> npt.NDArray[np.float32]:
        enc = self._tokenizer(
            texts,
            padding=True,
            truncation=True,
            max_length=self._max_text_length,
            return_tensors="pt",
        ).to(self._device)

        token_emb = self._model(**enc).last_hidden_state
        sentence_emb = self._mean_pooling(token_emb, enc["attention_mask"])

        if normalize:
            sentence_emb = torch.nn.functional.normalize(sentence_emb, p=2, dim=1)

        return sentence_emb.cpu().numpy().astype(np.float32)

    @torch.no_grad()
    def encode(
        self,
        texts: list[str],
        batch_size: int,
        normalize: bool = True,
        show_progress: bool = True,
    ) -> npt.NDArray[np.float32]:
        all_embeddings: list[npt.NDArray[np.float32]] = []
        batch_range = (
            tqdm(range(0, len(texts), batch_size), desc="Encoding", unit="batch")
            if show_progress
            else range(0, len(texts), batch_size)
        )

        for i in batch_range:
            batch_texts = texts[i : i + batch_size]
            batch_embeddings = self._process_batch(batch_texts, normalize)
            all_embeddings.append(batch_embeddings)

        result: npt.NDArray[np.float32] = np.vstack(all_embeddings)
        logger.debug("Encoded %s texts into %s", len(texts), result.shape)
        return result
    
    @property
    def embedding_dim(self) -> int:
        return self._embedding_dim

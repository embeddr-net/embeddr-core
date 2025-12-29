import gc
import io
import logging
import threading
from logging import Logger

import numpy as np
import torch
from PIL import Image
from transformers import CLIPModel, CLIPProcessor, CLIPTokenizer

_model = None
_processor = None
_tokenizer = None
_device = "cpu"
_lock = threading.Lock()

MODEL_NAME = "openai/clip-vit-base-patch32"

logger: Logger = logging.getLogger(__name__)


def get_device():
    logger.info("Determining available device for computations...")
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"


def load_clip_model(model_name, use_fast=True):
    model = CLIPModel.from_pretrained(model_name)
    processor = CLIPProcessor.from_pretrained(model_name, use_fast=use_fast)
    model.eval()

    if torch.cuda.is_available():
        model.to("cuda")
    return (model, processor)


def unload_model():
    global _model, _processor, _tokenizer
    with _lock:
        if _model is not None:
            logger.info("Unloading model...")
            del _model
            del _processor
            del _tokenizer
            _model = None
            _processor = None
            _tokenizer = None
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            gc.collect()
            logger.info("Model unloaded.")


def get_loaded_model_name():
    global _model
    if _model is not None:
        return _model.config.name_or_path
    return None


def load_model(model_name: str = MODEL_NAME):
    global _model, _processor, _tokenizer, _device

    # If requesting a different model than loaded, we might need to reload
    # For now, let's assume we just support switching or we need a dict of models
    # But to keep memory low, maybe just one at a time?
    # Let's stick to the requested model_name

    if _model is None or _model.config.name_or_path != model_name:
        with _lock:
            # Double check inside lock
            if _model is None or _model.config.name_or_path != model_name:
                # Unload previous if exists
                if _model is not None:
                    unload_model()

                logger.info(f"Loading CLIP model {model_name}...")
                device = get_device()
                try:
                    model = CLIPModel.from_pretrained(model_name).to(device)
                    processor = CLIPProcessor.from_pretrained(
                        model_name, use_fast=True)
                    tokenizer = CLIPTokenizer.from_pretrained(model_name)
                    model.eval()

                    _processor = processor
                    _tokenizer = tokenizer
                    _model = model

                    logger.info(
                        f"CLIP model {model_name} loaded on device {device}.")
                except Exception as e:
                    logger.error(f"Failed to load model {model_name}: {e}")
                    raise e

    return _model, _processor, _tokenizer, _device


def get_text_embedding(text: str, model_name: str = MODEL_NAME) -> np.ndarray:
    model, processor, tokenizer, _ = load_model(model_name)

    # Ensure Tokenizer
    if tokenizer is None:
        raise ValueError("Tokenizer not loaded")
    inputs = tokenizer([text], padding=True, return_tensors="pt")

    # Move inputs to the same device as the model
    device = model.device
    inputs = {k: v.to(device) for k, v in inputs.items()}

    with torch.no_grad():
        text_features = model.get_text_features(**inputs)
    text_features = text_features / \
        text_features.norm(p=2, dim=-1, keepdim=True)
    return text_features.cpu().numpy().flatten()


def get_image_embedding(image_bytes: bytes, model_name: str = MODEL_NAME) -> np.ndarray:
    model, processor, _, _ = load_model(model_name)

    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    # Ensure Processor
    if processor is None:
        raise ValueError("Processor not loaded")
    inputs = processor(images=image, return_tensors="pt")

    # Move inputs to the same device as the model
    device = model.device
    inputs = {k: v.to(device) for k, v in inputs.items()}

    with torch.no_grad():
        image_features = model.get_image_features(**inputs)
    image_features = image_features / \
        image_features.norm(p=2, dim=-1, keepdim=True)

    # image_embedding = image_features.cpu().numpy().flatten()
    # image_embedding /= np.linalg.norm(image_embedding) + 1e-10  # Normalize

    return image_features.cpu().numpy().flatten()


def get_image_embeddings_batch(
    image_bytes_list: list[bytes], model_name: str = MODEL_NAME
) -> list[np.ndarray | None]:
    model, processor, _, _ = load_model(model_name)

    if processor is None:
        raise ValueError("Processor not loaded")

    images = []
    valid_indices = []

    for idx, img_bytes in enumerate(image_bytes_list):
        try:
            img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
            images.append(img)
            valid_indices.append(idx)
        except Exception as e:
            logger.error(f"Failed to process image in batch: {e}")
            pass

    if not images:
        return [None] * len(image_bytes_list)

    # Processor can handle a list of images
    # padding=True ensures all images in batch have same dimensions if processor resizes them differently (though CLIP usually resizes to fixed size)
    inputs = processor(images=images, return_tensors="pt", padding=True)

    device = model.device
    inputs = {k: v.to(device) for k, v in inputs.items()}

    with torch.no_grad():
        image_features = model.get_image_features(**inputs)

    image_features = image_features / \
        image_features.norm(p=2, dim=-1, keepdim=True)

    results = [None] * len(image_bytes_list)
    numpy_features = image_features.cpu().numpy()

    for i, valid_idx in enumerate(valid_indices):
        results[valid_idx] = numpy_features[i].flatten()

    return results

import logging
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image
from tqdm import tqdm

logger = logging.getLogger(__name__)


def generate_thumbnails_for_library(
    library_path: Path,
    output_dir: Path,
    size=(256, 256),
    overwrite=False,
    max_workers=8,
) -> int:
    """
    Generate thumbnails for all images in library_path, mirroring directory structure
    inside output_dir.
    """
    library_path = Path(library_path).resolve()
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    # Gather all images
    image_files = [
        p
        for p in library_path.rglob("*")
        if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff"}
    ]

    if not image_files:
        logger.info(f"No images found in {library_path}")
        return 0

    def process_image(img_path):
        try:
            # Calculate relative path to maintain structure
            rel_path = img_path.relative_to(library_path)
            out_path = output_dir / rel_path

            # Ensure parent directory exists
            out_path.parent.mkdir(parents=True, exist_ok=True)

            if out_path.exists() and not overwrite:
                return 0

            with Image.open(img_path) as img:
                img = img.convert("RGB")  # ensures consistent mode
                img.thumbnail(size, Image.Resampling.LANCZOS)
                img.save(out_path, "JPEG", quality=85)
            return 1
        except Exception as e:
            logger.error(f"Failed to process {img_path}: {e}")
            return 0

    count = 0
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # We can use tqdm if running in a way that supports stdout,
        # but for an API service, logging might be better.
        # However, the user asked for tqdm, so we'll keep it for CLI usage
        # or if they look at server logs.
        results = list(
            tqdm(
                executor.map(process_image, image_files),
                total=len(image_files),
                desc=f"Thumbnails for {library_path.name}",
            )
        )
        count = sum(results)

    logger.info(f"Generated {count} thumbnails for {library_path}")
    return count

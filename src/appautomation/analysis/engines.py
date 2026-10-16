"""OCR back-ends behind one tiny interface.

Every engine takes a grayscale numpy image (a cropped region of interest) and
returns either one joined string or a list of recognised text fragments.
Heavy third party libraries are imported lazily so that the package can be
imported without any OCR engine installed.
"""

from __future__ import annotations

import logging
import re
from abc import ABC, abstractmethod
from typing import List, Optional

import numpy as np

logger = logging.getLogger(__name__)


class OcrEngine(ABC):
    """Common interface of all OCR back-ends."""

    @abstractmethod
    def read_lines(self, image: np.ndarray) -> List[str]:
        """Return the recognised text fragments, top to bottom."""

    def read_text(self, image: np.ndarray) -> str:
        """Return all fragments joined by single spaces."""
        return " ".join(self.read_lines(image))


class EasyOcrEngine(OcrEngine):
    def __init__(self, gpu: bool = True):
        import easyocr
        self._reader = easyocr.Reader(["en"], gpu=gpu)  # loads the model once

    def read_lines(self, image: np.ndarray) -> List[str]:
        return self._reader.readtext(image, detail=0)


class PaddleOcrEngine(OcrEngine):
    def __init__(self, gpu: bool = True):  # noqa: ARG002 - PaddleOCR picks the device itself
        from paddleocr import PaddleOCR
        from ppocr.utils.logging import get_logger

        get_logger().setLevel(logging.ERROR)
        self._reader = PaddleOCR(use_angle_cls=True, lang="en")

    def read_lines(self, image: np.ndarray) -> List[str]:
        words: List[str] = []
        for page in self._reader.ocr(image, cls=True):
            for line in page or []:
                words.append(re.sub(r"[^A-Za-z0-9. ]", "", line[1][0]).strip())
        return words


class TesseractEngine(OcrEngine):
    def __init__(self, tesseract_cmd: Optional[str] = None):
        import pytesseract
        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
        self._tesseract = pytesseract

    def read_lines(self, image: np.ndarray) -> List[str]:
        return [ln for ln in self._tesseract.image_to_string(image).splitlines() if ln.strip()]


def create_engine(name: str = "auto", gpu: bool = True,
                  tesseract_cmd: Optional[str] = None) -> OcrEngine:
    """Instantiate an engine by name.

    ``auto`` tries EasyOCR, then PaddleOCR, then Tesseract and uses the first
    one that is installed.
    """
    factories = {
        "easyocr": lambda: EasyOcrEngine(gpu),
        "paddleocr": lambda: PaddleOcrEngine(gpu),
        "tesseract": lambda: TesseractEngine(tesseract_cmd),
    }
    if name != "auto":
        if name not in factories:
            raise ValueError(f"Unknown OCR engine '{name}'. Choose from: auto, {', '.join(factories)}")
        return factories[name]()

    for candidate, factory in factories.items():
        try:
            engine = factory()
            logger.info("Using OCR engine: %s", candidate)
            return engine
        except ImportError:
            continue
    raise RuntimeError(
        "No OCR engine found. Install one of: easyocr, paddleocr, pytesseract "
        "(see README, section 'OCR engines')."
    )

"""Example 2 - run the OCR analysis on a synthetic Bolt screenshot.

No phone needed, but one OCR engine must be installed (easyocr, paddleocr or
pytesseract). The script draws a fake screenshot in a temporary folder, runs
the analyser and prints the resulting CSV.

Run:  python examples/02_synthetic_analysis.py
"""

import tempfile
from pathlib import Path

import cv2
import numpy as np

from appautomation.analysis import ScreenshotAnalyser, ScreenshotParser, create_engine
from appautomation.constants import SCREEN_PROFILES

PROFILE = "hd720"
CITY, DATE = "MEL", "0101"

with tempfile.TemporaryDirectory() as tmp:
    work = Path(tmp)
    (work / "routes").mkdir()
    shots = work / "screenshots" / f"{DATE}_{CITY}_demo"
    shots.mkdir(parents=True)

    # 1. a one-route CSV
    (work / "routes" / f"{CITY}.csv").write_text(
        "id,src,dst\n1,Federation Square,Melbourne Airport\n", encoding="utf-8")

    # 2. a fake 720x1560 screenshot with a price inside Bolt's fare region ("B")
    img = np.full((1560, 720, 3), 255, np.uint8)
    top, bottom, left, right = SCREEN_PROFILES[PROFILE]["B"]
    cv2.putText(img, "$24.80 Bolt", (left, (top + bottom) // 2),
                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 0), 2)
    cv2.imwrite(str(shots / f"{CITY}{DATE}001B.png"), img)

    # 3. analyse
    parser = ScreenshotParser(create_engine("auto", gpu=False), PROFILE)
    csv_path = ScreenshotAnalyser(parser, work, CITY, DATE, str(shots), "demo").run()
    print(Path(csv_path).read_text(encoding="utf-8"))

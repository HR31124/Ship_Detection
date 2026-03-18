import os
os.environ['FLAGS_use_onednn'] = '0'
os.environ['FLAGS_enable_pir_api'] = '0'
os.environ['FLAGS_enable_pir_in_executor'] = '0'
os.environ['PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK'] = 'True'
import logging
import cv2
import numpy as np
from paddleocr import PaddleOCR
logging.getLogger("ppocr").setLevel(logging.WARNING)

class ShipOCR:
    def __init__(self, lang="en", use_angle_cls=True):
        print(">> Init PaddleOCR...")
        self.ocr = PaddleOCR(use_angle_cls=use_angle_cls, lang=lang)
        print(">> PaddleOCR Ready!")

    def ocr_image(self, image_cv):
        results = []
        try:
            ocr_result = self.ocr.ocr(image_cv)

            if not ocr_result or ocr_result[0] is None:
                return results

            data = ocr_result[0]

            if isinstance(data, dict):
                texts = data.get("rec_texts", [])
                scores = data.get("rec_scores", [])
                boxes = data.get("dt_polys", [])
                
                for box, text, score in zip(boxes, texts, scores):
                    results.append({
                        "text": text,
                        "score": float(score),
                        "box": box
                    })
            else:
                for line in data:
                    if not line: continue
                    box = line[0]
                    rec = line[1]
                    
                    if isinstance(rec, (list, tuple)):
                        text, score = rec
                    else:
                        continue

                    results.append({
                        "text": text,
                        "score": float(score),
                        "box": box
                    })
                    
        except Exception as e:
            print(f"Lỗi OCR Core: {e}")

        return results
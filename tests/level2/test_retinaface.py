from dnn.processing.image import retinaface, img_util
import cv2
import os
import numpy as np
import time

def draw_bbox_landm(img, r):
    """draw bboxes and landmarks"""
    # bbox
    x1, y1, x2, y2 = r ['box']
    cv2.rectangle(img, (x1, y1), (x1 + x2, y1 + y2), (0, 255, 0), 2)
    # confidence
    text = "{:.4f}".format(r['confidence'])
    cv2.putText(img, text, (x1, y1),
                cv2.FONT_HERSHEY_DUPLEX, 0.5, (255, 255, 255))

    # landmark
    cv2.circle(img, r ['keypoints']['left_eye'], 1, (255, 255, 0), 2)
    cv2.circle(img, r ['keypoints']['right_eye'], 1, (0, 255, 255), 2)
    cv2.circle(img, r ['keypoints']['nose'], 1, (255, 0, 0), 2)
    cv2.circle(img, r ['keypoints']['mouth_left'], 1, (0, 100, 255), 2)
    cv2.circle(img, r ['keypoints']['mouth_right'], 1, (255, 0, 100), 2)


def test_retinaface ():
    try:
        f = retinaface.RetinaFace ()
    except:
        return # local test only
    img_path = os.path.join ("examples", 'resources', '0_Parade_marchingband_1_379.jpg')
    img = cv2.cvtColor (cv2.imread(img_path), cv2.COLOR_BGR2RGB)
    results = f.detect (img)
    assert len (results) > 1
    assert 'box' in results [0]
    assert 'keypoints' in results [0]
    assert 'confidence' in results [0]
    assert 'mouth_left' in results [0]['keypoints']

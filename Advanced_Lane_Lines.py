import os
import random
from glob import glob

import numpy as np
import cv2
import matplotlib.pyplot as plt

from Udacity_self_driving_car_challenge_4.image_processing.calibration import camera_cal, found_chessboard, read_camera_cal_file
from Udacity_self_driving_car_challenge_4.image_processing.edge_detection import combing_color_thresh
from Udacity_self_driving_car_challenge_4.image_processing.find_lines import histogram_search, histogram_search2
from Udacity_self_driving_car_challenge_4.image_processing.line_fit_fix import Line


ROOT_PATH = os.getcwd()
IMAGE_TEST_DIR = os.path.join(ROOT_PATH, 'test_images')
IMAGE_OUTPUT_DIR = os.path.join(ROOT_PATH, 'output_images')
VIDEO_OUTPUT_DIR = os.path.join(ROOT_PATH, 'output_video')
IMAGE_PROCESSING_PATH = os.path.join(ROOT_PATH, 'image_processing')
WIDE_DIST_FILE = os.path.join(IMAGE_PROCESSING_PATH, 'wide_dist_pickle.p')
IMAGES_PATH = glob(IMAGE_TEST_DIR + '/*.jpg')


# Load cameraMatrix and distCoeffs parameter
if not os.path.exists(WIDE_DIST_FILE):
    objpoints, imgpoints = found_chessboard()
    mtx, dist = camera_cal(objpoints, imgpoints)
else:
    print('Get parameter from pickle file')
    mtx, dist = read_camera_cal_file(WIDE_DIST_FILE)

# Get Perspective Transform Parameter
offset = 1280 / 2
src = np.float32([(596, 447), (683, 447), (1120, 720), (193, 720)])     # Longer line
# src = np.float32([(578, 460), (704, 460), (1120, 720), (193, 720)])     # shorter line
dst = np.float32([(offset-300, 0), (offset+300, 0), (offset+300, 720), (offset-300, 720)])
perspective_M = cv2.getPerspectiveTransform(src, dst)
inver_perspective_M = cv2.getPerspectiveTransform(dst, src)

left_line = Line()
right_line = Line()
count_h1 = 0
count_h2 = 0


def process_image(image, show_birdview=False):
    global count_h1, count_h2
    # Apply a distortion correction to raw images.
    image = cv2.undistort(image, mtx, dist, None, None)

    # Use color transforms, gradients to find the object edge and change into binary image
    image_binary = combing_color_thresh(image)

    # Transform image to bird view
    image_bird_view = cv2.warpPerspective(image_binary, perspective_M, image.shape[1::-1], flags=cv2.INTER_LINEAR)

    # find the road lines, curvature and distance between car_center and road_center
    color_warp, curv, center, left_or_right, left_line.new_fit, right_line.new_fit, left_line.allx, right_line.allx = histogram_search(image_bird_view)

    # Warp the blank back to original image space using inverse perspective matrix (Minv)
    warp_back = cv2.warpPerspective(color_warp, inver_perspective_M, (image.shape[1], image.shape[0]))

    # Combine the result with the original image
    img_out = cv2.addWeighted(image, 1, warp_back, 0.3, 0)

    # Add description on images
    text1 = "Radius of Curature = {:.2f}(m)".format(curv)
    text2 = "Vehicle is {:.3f}m {} of center".format(abs(center), left_or_right)
    font = cv2.FONT_HERSHEY_SIMPLEX
    cv2.putText(img_out, text1, (50, 50), font, 1.5, color=(255, 255, 255), thickness=3)
    cv2.putText(img_out, text2, (50, 100), font, 1.5, color=(255, 255, 255), thickness=3)

    if show_birdview:
        show_image_bird_view = cv2.resize(image_bird_view, (360, 360))
        show_image_bird_view = cv2.cvtColor(show_image_bird_view, cv2.COLOR_GRAY2RGB)
        show_color_warp = cv2.resize(color_warp, (360, 360))
        show_color_warp = cv2.addWeighted(show_image_bird_view, 1, show_color_warp, 0.5, 0)
        return img_out, show_image_bird_view, show_color_warp

    return img_out


def process_video(image, show_birdview=False):
    global count_h1, count_h2
    # Apply a distortion correction to raw images.
    image = cv2.undistort(image, mtx, dist, None, None)

    # Use color transforms, gradients to find the object edge and change into binary image
    image_binary = combing_color_thresh(image)

    # Transform image to bird view
    image_bird_view = cv2.warpPerspective(image_binary, perspective_M, image.shape[1::-1], flags=cv2.INTER_LINEAR)

    # find the road lines, curvature and distance between car_center and road_center
    if not left_line.detected or not right_line.detected:
        color_warp, curv, center, left_or_right, left_line.new_fit, right_line.new_fit, \
        left_line.allx, right_line.allx = histogram_search(image_bird_view)
        count_h1 += 1
    else:
        color_warp, curv, center, left_or_right, left_line.new_fit, right_line.new_fit, \
        left_line.allx, right_line.allx = histogram_search2(image_bird_view, left_line.best_fit, right_line.best_fit)
        count_h2 += 1

    # Check the lines health
    left_line.fit_fix()
    right_line.fit_fix()

    # Warp the blank back to original image space using inverse perspective matrix (Minv)
    warp_back = cv2.warpPerspective(color_warp, inver_perspective_M, (image.shape[1], image.shape[0]))

    # Combine the result with the original image
    img_out = cv2.addWeighted(image, 1, warp_back, 0.3, 0)

    # Add description on images
    text1 = "Radius of Curature = {:.2f}(m)".format(curv)
    text2 = "Vehicle is {:.3f}m {} of center".format(abs(center), left_or_right)
    font = cv2.FONT_HERSHEY_SIMPLEX
    cv2.putText(img_out, text1, (50, 50), font, 1.5, color=(255, 255, 255), thickness=3)
    cv2.putText(img_out, text2, (50, 100), font, 1.5, color=(255, 255, 255), thickness=3)

    if show_birdview:
        show_image_bird_view = cv2.resize(image_bird_view, (360, 360))
        show_image_bird_view = cv2.cvtColor(show_image_bird_view, cv2.COLOR_GRAY2RGB)
        show_color_warp = cv2.resize(color_warp, (360, 360))
        show_color_warp = cv2.addWeighted(show_image_bird_view, 1, show_color_warp, 0.5, 0)
        return img_out, show_image_bird_view, show_color_warp

    return img_out


def test_image():
    # random chose image to test
    random_chose = random.randint(0, len(IMAGES_PATH)-1)
    img_test = IMAGES_PATH[random_chose]
    print(img_test)
    img = cv2.imread('./test_images/test3.jpg')

    img_out = process_image(img)

    # Converter BGR -> RGB for plt show
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    img_out = cv2.cvtColor(img_out, cv2.COLOR_BGR2RGB)

    plt.figure(figsize=(10, 8))
    plt.subplot(2, 1, 1)
    plt.title('Original Image')
    plt.imshow(img)
    plt.subplot(2, 1, 2)
    plt.title('Output Image')
    plt.imshow(img_out, cmap='gray')
    plt.show()


def test_images():
    for path in IMAGES_PATH:
        img = cv2.imread(path)
        img_out, show_image_bird_view, show_color_warp = process_image(img, show_birdview=True)
        add_image = np.vstack((show_image_bird_view, show_color_warp))
        img_out = np.hstack((img_out, add_image))
        img_out_path = os.path.join(IMAGE_OUTPUT_DIR, os.path.split(path)[-1].split('.')[0] + '.png')
        cv2.imwrite(img_out_path, img_out)


def test_video():
    video_file = 'project_video.mp4'
    video_output_file = os.path.join(VIDEO_OUTPUT_DIR, video_file.split('.')[0] + '.avi')

    # Video save
    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    out = cv2.VideoWriter(video_output_file, fourcc, 20, (1640, 720))

    # Video read
    cap = cv2.VideoCapture(video_file)
    while cap.isOpened():
        ret, frame = cap.read()
        if ret:
            img_out, show_image_bird_view, show_color_warp = process_video(frame, show_birdview=True)
            add_image = np.vstack((show_image_bird_view, show_color_warp))
            img_out = np.hstack((img_out, add_image))
            out.write(img_out)
            cv2.imshow('frame', img_out)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        else:
            break
    print("h1: {}\th2: {}".format(count_h1, count_h2))
    cap.release()
    out.release()
    cv2.destroyAllWindows()


if __name__ == '__main__':
    test_video()

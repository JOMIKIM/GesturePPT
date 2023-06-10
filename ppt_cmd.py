from cv2 import flip, cvtColor, cvtColor, COLOR_BGR2RGB, COLOR_RGB2BGR, imshow, waitKey, VideoCapture, putText, FONT_HERSHEY_SIMPLEX
from mediapipe import solutions
from numpy import zeros, linalg, newaxis, arccos, einsum, degrees, concatenate, expand_dims, array, float32, argmax
from tensorflow.keras.models import load_model
from win32com.client import Dispatch
from pyautogui import getWindowsWithTitle, keyDown
import win32com.client
import pyautogui


actions = ['pgup', 'pgdn', 'reset']
seq_length = 30
 
model = load_model('models/model.h5')

# MediaPipe hands model
mp_hands = solutions.hands
mp_drawing = solutions.drawing_utils
hands = mp_hands.Hands(
    max_num_hands=1,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5)



cap = VideoCapture(0)


seq = []
action_seq = []
last_action = None
counter = 0

while cap.isOpened():
    ret, img = cap.read()
    if not ret:
        break

    img = flip(img, 1)
    img = cvtColor(img, COLOR_BGR2RGB)
    result = hands.process(img)
    img = cvtColor(img, COLOR_RGB2BGR)

    if result.multi_hand_landmarks is not None:
        for res in result.multi_hand_landmarks:
            joint = zeros((21, 4))
            for j, lm in enumerate(res.landmark):
                joint[j] = [lm.x, lm.y, lm.z, lm.visibility]

            # Compute angles between joints
            v1 = joint[[0,1,2,3,0,5,6,7,0,9,10,11,0,13,14,15,0,17,18,19], :3] # Parent joint
            v2 = joint[[1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20], :3] # Child joint
            v = v2 - v1 # [20, 3]
            # Normalize v
            v = v / linalg.norm(v, axis=1)[:, newaxis]

            # Get angle using arcos of dot product
            angle = arccos(einsum('nt,nt->n',
                v[[0,1,2,4,5,6,8,9,10,12,13,14,16,17,18],:], 
                v[[1,2,3,5,6,7,9,10,11,13,14,15,17,18,19],:])) # [15,]

            angle = degrees(angle) # Convert radian to degree

            d = concatenate([joint.flatten(), angle])

            seq.append(d)

            mp_drawing.draw_landmarks(img, res, mp_hands.HAND_CONNECTIONS)

            if len(seq) < seq_length:
                continue

            input_data = expand_dims(array(seq[-seq_length:], dtype=float32), axis=0)

            y_pred = model.predict(input_data).squeeze()

            i_pred = int(argmax(y_pred))
            conf = y_pred[i_pred]

            if conf < 0.9:
                continue

            action = actions[i_pred]
            action_seq.append(action)

            if len(action_seq) < 3:
                continue

            this_action = '?'
            if action_seq[-1] == action_seq[-2] == action_seq[-3]:
                this_action = action

                if counter == 0:
                    if this_action == 'pgup':
                        ppt = win32com.client.Dispatch("PowerPoint.Application")
                        active_presentation = ppt.ActivePresentation
                        window = pyautogui.getWindowsWithTitle('pptx')[0]
                        window.activate()
                        keyDown('pgup')
                        counter += 1
                        window = pyautogui.getWindowsWithTitle('img')[0]
                        window.activate()
                    elif this_action == 'pgdn':
                        ppt = win32com.client.Dispatch("PowerPoint.Application")
                        active_presentation = ppt.ActivePresentation
                        window = pyautogui.getWindowsWithTitle('pptx')[0]
                        window.activate()
                        keyDown('pgdn')
                        counter += 1
                        window = pyautogui.getWindowsWithTitle('img')[0]
                        window.activate()


                    last_action = this_action

                else:
                    if this_action == 'reset':
                        counter = 0
                        window = pyautogui.getWindowsWithTitle('img')[0]
                        window.activate()
            putText(img, f'{this_action.upper()}', org=(int(res.landmark[0].x * img.shape[1]), int(res.landmark[0].y * img.shape[0] + 20)), fontFace=FONT_HERSHEY_SIMPLEX, fontScale=1, color=(255, 255, 255), thickness=2)

    


    imshow('img', img)
    if waitKey(1) == ord('q'):
        break

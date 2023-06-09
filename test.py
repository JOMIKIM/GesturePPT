from cv2 import flip, cvtColor, cvtColor, COLOR_BGR2RGB, COLOR_RGB2BGR, imshow, waitKey, VideoCapture, putText, FONT_HERSHEY_SIMPLEX, destroyAllWindows
from mediapipe import solutions
from numpy import zeros, linalg, newaxis, arccos, einsum, degrees, concatenate, expand_dims, array, float32, argmax
from tensorflow.keras.models import load_model

actions = ['pgup', 'pgdn', 'reset']
seq_length = 30

model = load_model('models/model.h5')

mp_hands = solutions.hands
mp_drawing = solutions.drawing_utils

cam = VideoCapture(0)

seq = []
action_seq = []

with mp_hands.Hands(
    # 인식 할 손 모양의 갯수
    max_num_hands = 1,
    min_detection_confidence = 0.5,
    min_tracking_confidence = 0.5
) as hands:
    while mp_hands.Hands():
        ret, img = cam.read()
        # img0 = img.copy()

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

                putText(img, f'{this_action.upper()}', org=(int(res.landmark[0].x * img.shape[1]), int(res.landmark[0].y * img.shape[0] + 20)), fontFace=FONT_HERSHEY_SIMPLEX, fontScale=1, color=(255, 255, 255), thickness=2)

    # out.write(img0)
    # out2.write(img)
        imshow('img', img)
        if waitKey(1) == ord('q'):
            break
cam.release()
destroyAllWindows()
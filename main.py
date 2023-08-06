from pydub import AudioSegment
import numpy as np
import pygame
import random
import time
import cv2
import mediapipe as mp
import threading
import winsound

WIDTH = 800
HEIGHT = 600
random.seed(123)

def get_waveform_from_wav(wav_file):
    audio = AudioSegment.from_file(wav_file)
    samples = np.array(audio.get_array_of_samples())
    normalized_samples = samples / 2**15
    return normalized_samples

def draw_circle(screen, x, y, radius):
    pygame.draw.circle(screen, (255, 255, 255), (x, y), radius)

def draw_camera_image(camera_image):
    # カメラ映像をリサイズしてPygameウィンドウに描画
    resized_image = cv2.resize(camera_image, (WIDTH, HEIGHT))
    
    # カメラ映像を横向きで表示するために、画像を回転させる
    camera_image_rotated = cv2.rotate(resized_image, cv2.ROTATE_90_CLOCKWISE)
    camera_image_flipped = cv2.flip(camera_image_rotated, 1)  # 1は水平方向の反転
    camera_image_rgb = cv2.cvtColor(camera_image_flipped, cv2.COLOR_BGR2RGB)
    camera_surface = pygame.surfarray.make_surface(camera_image_rgb)
    return camera_surface

def detect_hand_landmarks(image):
    with mp.solutions.hands.Hands(static_image_mode=False, max_num_hands=2, min_detection_confidence=0.5) as hands:
        # RGB画像をBGRに変換
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        # ランドマーク検出を実行
        results = hands.process(image_rgb)

        hand_landmarks_list = []
        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                hand_landmarks_list.append(hand_landmarks)
        if hand_landmarks_list:
            return hand_landmarks_list
        return []

def draw_hand_landmarks(screen, hand_landmarks_list):
    for hand_landmarks in hand_landmarks_list:
        if hand_landmarks:
            for landmark in hand_landmarks.landmark:
                # ランドマークの座標を画像座標に変換して描画
                x = int(landmark.x * WIDTH)
                y = int(landmark.y * HEIGHT)
                # 緑色でランドマークを描画
                pygame.draw.circle(screen, (0, 255, 0), (x, y), 5)

def circle_collision(circle_x, circle_y, circle_radius, hand_x, hand_y):
    # 円と手の位置の距離を計算して、円の半径よりも小さい場合は重なっているとみなす
    distance = np.sqrt((circle_x - hand_x)**2 + (circle_y - hand_y)**2)
    return distance < circle_radius

def draw_circles(screen, circles):
    current_time = time.time()
    circles_to_remove = []
    for i, circle in enumerate(circles):
        x, y, big_radius, small_radius, draw_time = circle
        elapsed_time = current_time - draw_time
        if elapsed_time > 60.0:
            circles_to_remove.append(i)
            continue  # 60秒以上前の円は削除

        max_lifetime = 60.0  # 1つの円の寿命（秒）
        shrink_duration = 4.0  # 大きな円が徐々に縮小する期間（秒）

        if elapsed_time < shrink_duration:
            # 大きな円が徐々に縮小するフェーズ
            scale_factor = 1.0 - elapsed_time / shrink_duration
            current_big_radius = int(big_radius * scale_factor)

        else:
            # 大きな円が縮小し終わった後は削除
            circles_to_remove.append(i)
            continue

        # small_radiusの円を描画
        pygame.draw.circle(screen, (255, 255, 255), (x, y), small_radius)
        
        if current_big_radius < small_radius:
            if current_big_radius+15 < small_radius:
                pygame.draw.circle(screen, (255, 0, 0), (x, y), current_big_radius, 2)
            else:
                pygame.draw.circle(screen, (0, 255, 0), (x, y), current_big_radius, 2)
        else:
            pygame.draw.circle(screen, (0, 0, 255), (x, y), current_big_radius, 2)

    
    # 削除する円をリストから削除
    for index in reversed(circles_to_remove):
        circles.pop(index)

def draw_score(screen, score):
    font = pygame.font.Font(None, 36)
    score_text = font.render("Score: " + str(score), True, (255, 255, 255))
    screen.blit(score_text, (10, 10))

def draw_countdown(screen, countdown):
    font = pygame.font.Font(None, 100)
    countdown_text = font.render(str(countdown), True, (255, 255, 255))
    countdown_rect = countdown_text.get_rect(center=(screen.get_width() // 2, screen.get_height() // 2))
    screen.blit(countdown_text, countdown_rect)

def get_rdm_index():
    rdm_x = random.randint(0, 1)
    rdm_y = random.randint(0, 1)
    return rdm_x, rdm_y

def start_play_music(file):
    time.sleep(3.4)
    music = pygame.mixer.Sound(file)
    music.play()
    #winsound.PlaySound(file, winsound.SND_FILENAME|winsound.SND_ASYNC|winsound.SND_LOOP)

    
def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Waveform Circles")

    # wav_file = input("このファイルと同じフォルダにある.wavファイルの名前を入力: ")
    wav_file = "01_アイドルライフスターターパック.wav"
    waveform = get_waveform_from_wav(wav_file)

    pygame.mixer.init()
    pygame.mixer.music.load(wav_file)

    clock = pygame.time.Clock()

    running = True
    play_music = False
    display_countdown = False
    # 0.2->0.3
    threshold = 0.3
    last_draw_time = 0
    circles = []
    countdown_list = ["3", "2", "1", "START!"]
    GG_font = pygame.font.Font(None, 100)
    Great_text = GG_font.render('Great!', True, (255, 255, 255))
    Good_text = GG_font.render('Good!', True, (255, 255, 255))

    # カウントダウン開始時間を記録
    countdown_timer = None

    # カメラ初期化
    cap = cv2.VideoCapture(0)

    score = 0  # スコアの初期値
    font = pygame.font.Font(None, 36)

    circle_distance_x = [-100, 100]
    circle_distance_y = [-100, 100]
    x = 200
    y = 200
    
    

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    display_countdown = True

        if not pygame.mixer.music.get_busy() and play_music:
            play_music = False

        screen.fill((0, 0, 0))

        if play_music:
            current_pos = pygame.mixer.music.get_pos()
            sample_pos = int(current_pos / 1000 * 44100)

            if sample_pos < len(waveform) and 1000 < pygame.time.get_ticks() - last_draw_time:
                current_sample = waveform[sample_pos]

                if abs(current_sample) > threshold:
                    if 1000 <  pygame.time.get_ticks() - last_draw_time < 1400:
                        x += circle_distance_x[rdm_index_x]
                        y += circle_distance_y[rdm_index_y]
                        if x > 800:
                            x = 100
                        elif x < 0:
                            x = 700
                        if y > 600:
                            y = 100
                        elif y < 0:
                            y = 500
                    else:
                        rdm_index_x, rdm_index_y = get_rdm_index()
                        x = random.randint(0, 800)
                        y = random.randint(0, 600)
                    big_radius = int(abs(current_sample) * 100+300)
                    small_radius = int(big_radius * 0.1)
                    # 新しい円を追加するときに経過時間も記録
                    circles.append((x, y, big_radius, small_radius, time.time()))
                    last_draw_time = pygame.time.get_ticks()

        # カメラ映像の取得
        ret, frame = cap.read()

        frame = cv2.flip(frame, 1)

        if ret:
            camera_surface = draw_camera_image(frame)
            # 手のランドマークを検出
            hand_landmarks = detect_hand_landmarks(frame)
            # 手のランドマークを描画
            draw_hand_landmarks(camera_surface, hand_landmarks)

            screen.blit(camera_surface, (0, 0))

        current_time = time.time()
        circles_to_remove = []
        for i, circle in enumerate(circles):
            x, y, big_radius, small_radius, draw_time = circle
            if current_time - draw_time > 60.0:
                circles_to_remove.append(i)

        for index in reversed(circles_to_remove):
            circles.pop(index)

        draw_circles(screen, circles)

        # 手が円に触れているか判定して、触れている場合はその円を消去
        hand_landmarks = detect_hand_landmarks(frame)
        if hand_landmarks:
            for hand_landmark in hand_landmarks:
                # 手のランドマークの関節の座標を取得
                hand_joints_x = [int(landmark.x * WIDTH) for landmark in hand_landmark.landmark]
                hand_joints_y = [int(landmark.y * HEIGHT) for landmark in hand_landmark.landmark]

                # すべての円に対して、手の関節との接触を判定
                circles_to_remove = []
                for i, circle in enumerate(circles):
                    x, y, big_radius, small_radius, circle_start = circle
                    joint_x= hand_joints_x[8]
                    joint_y = hand_joints_y[8]
                    if circle_collision(x, y, small_radius, joint_x, joint_y):
                        if 3.4 < time.time()-circle_start and time.time()-circle_start < 3.7:
                            score += 500 # +500
                            screen.blit(Great_text, (x, y))
                        else:
                            score += 100 # +100
                            screen.blit(Good_text, (x, y))
                        circles_to_remove.append(i)
                            

                # 接触した円を削除
                for index in reversed(circles_to_remove):
                    circles.pop(index)

        # スコアバーを描画
        draw_score(screen, score)

        if display_countdown and not play_music:
            if not countdown_timer:
                countdown_timer = time.time()

            # カウントダウンの秒数を計算
            elapsed_time = time.time() - countdown_timer
            countdown_remaining = int(elapsed_time)

            if countdown_remaining >= 0 and countdown_remaining < len(countdown_list):
                draw_countdown(screen, countdown_list[countdown_remaining])
            else:
                pygame.mixer.music.play()  # エンターキーが押されたら音楽を再生
                pygame.mixer.music.set_volume(0)
                th1 = threading.Thread(target=start_play_music, args=(wav_file, ))
                th1.start()
                play_music = True
                display_countdown = False

        pygame.display.flip()
        clock.tick(60)

    cap.release()
    pygame.quit()

if __name__ == "__main__":
    main()

# [0]ライブラリのインポート
import gymnasium as gym  # 倒立振子(cartpole)の実行環境
from gymnasium import wrappers  #gymの画像保存
import numpy as np
import time
from collections import deque


# [1]Q関数を離散化して定義する関数　------------
def bins(clip_min, clip_max, num):
    return np.linspace(clip_min, clip_max, num + 1)[1:-1]


# 各値を離散値に変換
def digitize_state(observation):
    cart_pos, cart_v, pole_angle, pole_v = observation
    digitized = [
        np.digitize(cart_pos, bins=bins(-2.4, 2.4, num_dizitized)),
        np.digitize(cart_v, bins=bins(-3.0, 3.0, num_dizitized)),
        np.digitize(pole_angle, bins=bins(-0.5, 0.5, num_dizitized)),
        np.digitize(pole_v, bins=bins(-2.0, 2.0, num_dizitized))
    ]
    return sum([x * (num_dizitized**i) for i, x in enumerate(digitized)])


# [2]行動a(t)を求める関数 -------------------------------------
def get_action(next_state, episode):    # 徐々に最適行動のみをとる、ε-greedy法
    epsilon = 0.5 * (1 / (episode + 1))
    if epsilon <= np.random.uniform(0, 1):
        next_action = np.argmax(q_table[next_state])
    else:
        next_action = np.random.choice([0, 1])
    return next_action


# [3]1試行の各ステップの行動を保存しておくメモリクラス
class Memory:
    def __init__(self, max_size=200):
        self.buffer = deque(maxlen=max_size)

    def add(self, experience):
        self.buffer.append(experience)

    def sample(self):
        return self.buffer.pop()  # 最後尾のメモリを取り出す

    def len(self):
        return len(self.buffer)


# [4]Qテーブルを更新する(モンテカルロ法) ＊Qlearningと異なる＊ -------------------------------------
def update_Qtable_montecarlo(q_table, memory):
    gamma = 0.99
    alpha = 0.5
    total_reward_t = 0

    while (memory.len() > 0):
        (state, action, reward) = memory.sample()
        total_reward_t = gamma * total_reward_t       # 時間割引率をかける
        # Q関数を更新
        q_table[state, action] = q_table[state, action] + alpha*(reward+total_reward_t-q_table[state, action])
        total_reward_t = total_reward_t + reward    # ステップtより先でもらえた報酬の合計を更新

    return q_table


# [5]. メイン関数開始 パラメータ設定--------------------------------------------------------
env = gym.make('CartPole-v0')
max_number_of_steps = 200  #1試行のstep数
num_consecutive_iterations = 100  #学習完了評価に使用する平均試行回数
num_episodes = 2000  #総試行回数
goal_average_reward = 195  #この報酬を超えると学習終了（中心への制御なし）
# 状態を6分割^（4変数）にデジタル変換してQ関数（表）を作成
num_dizitized = 6  #分割数
memory_size = max_number_of_steps            # バッファーメモリの大きさ
memory = Memory(max_size=memory_size)
q_table = np.random.uniform(low=-1, high=1, size=(num_dizitized**4, env.action_space.n))
total_reward_vec = np.zeros(num_consecutive_iterations)  #各試行の報酬を格納
final_x = np.zeros((num_episodes, 1))  #学習後、各試行のt=200でのｘの位置を格納
islearned = 0  #学習が終わったフラグ
isrender = 0  #描画フラグ


# [5] メインルーチン--------------------------------------------------
for episode in range(num_episodes):  #試行数分繰り返す
    # 環境の初期化
    observation, _ = env.reset()
    state = digitize_state(observation)
    action = np.argmax(q_table[state])
    episode_reward = 0

    for t in range(max_number_of_steps):  #1試行のループ
        if islearned == 1:  #学習終了したらcartPoleを描画する
            env.render()
            time.sleep(0.1)
            print (observation[0])  #カートのx位置を出力


        # 行動a_tの実行により、s_{t+1}, r_{t}などを計算する
        observation, reward, done, done2, info = env.step(action)

        # 報酬を設定し与える
        if done or done2:
            if t < 195:
                reward = -200  #こけたら罰則
            else:
                reward = 1  #立ったまま終了時は罰則はなし

        else:
            reward = 1  #各ステップで立ってたら報酬追加


        # メモリに、現在の状態と行った行動、得た報酬を記録する
        memory.add((state, action, reward))

        # 次ステップへ行動と状態を更新
        next_state = digitize_state(observation)  # t+1での観測状態を、離散値に変換
        next_action = get_action(next_state, episode)  # 次の行動a_{t+1}を求める
        action = next_action  # a_{t+1}
        state = next_state  # s_{t+1}

        episode_reward += reward  #報酬を追加

        # 終了時の処理
        if done or done2:
            # これまでの行動の記憶と、最終的な結果からQテーブルを更新していく
            q_table = update_Qtable_montecarlo(q_table, memory)

            print('%d Episode finished after %f time steps / mean %f' %
                  (episode, t + 1, total_reward_vec.mean()))
            total_reward_vec = np.hstack((total_reward_vec[1:],
                                          episode_reward))  #報酬を記録
            if islearned == 1:  #学習終わってたら最終のx座標を格納
                final_x[episode, 0] = observation[0]
            break

    if (total_reward_vec.mean() >=
            goal_average_reward):  # 直近の100エピソードが規定報酬以上であれば成功
        print('Episode %d train agent successfuly!' % episode)
        islearned = 1
        #np.savetxt('learned_Q_table.csv',q_table, delimiter=",") #Qtableの保存する場合
        if isrender == 0:
            # env = wrappers.Monitor(env, './movie/cartpole-experiment-1') #動画保存する場合
            isrender = 1
    #10エピソードだけでどんな挙動になるのか見たかったら、以下のコメントを外す
    #if episode>10:
    #    if isrender == 0:
    #        env = wrappers.Monitor(env, './movie/cartpole-experiment-1') #動画保存する場合
    #        isrender = 1
    #    islearned=1;

if islearned:
    np.savetxt('final_x.csv', final_x, delimiter=",")
import streamlit as st
import pandas as pd
import random
import time
from datetime import datetime

# ==============================================================================
# 0. Authentication & Config
# ==============================================================================

st.set_page_config(page_title="Kronologic Mobile", layout="wide", initial_sidebar_state="collapsed")

def check_password():
    SECRET_PASSWORD = "tianhaoyun" 

    if "password_correct" not in st.session_state:
        st.session_state.password_correct = False

    if not st.session_state.password_correct:
        st.markdown("### 🕵️ Kronologic Headquarter")
        password = st.text_input("Access Code", type="password")
        if st.button("🔓 Authenticate", use_container_width=True):
            if password == SECRET_PASSWORD:
                st.session_state.password_correct = True
                st.rerun()
            else:
                st.error("🚫 Access Denied")
        st.stop()

check_password()

# ==============================================================================
# 1. Setups
# ==============================================================================

ROOMS = ["牌坊", "信号", "鱿鱼", "面具", "音乐", "舞蹈"]
CHARACTERS = ["(A) Accessoiriste", "(B) Baroness", "(C) Chauffeur", "(D) Director", "(J) Journalist", "(S) Soprano"]
TIMES = [1, 2, 3, 4, 5, 6]

MAP_GRAPH = {
    "牌坊": ["信号", "鱿鱼"],
    "信号": ["鱿鱼", "牌坊"],
    "鱿鱼": ["面具", "信号", "牌坊"],
    "面具": ["鱿鱼", "音乐", "舞蹈"],
    "音乐": ["面具", "舞蹈"],
    "舞蹈": ["面具", "音乐"]
}

class ScenarioGenerator:
    def __init__(self, seed_val, mode="jewel"):
        self.seed_val = seed_val
        self.mode = mode
        self.initial_clues = [] 

        if seed_val is not None:
            random.seed(seed_val)

        max_attempts = 1000
        success = False

        for i in range(max_attempts):
            self.board = self._generate_raw_board()
            
            if self.mode == "jewel":
                self.solution_data, self.difficulty, is_valid = self._solve_jewel_with_constraints()
                if is_valid:
                    success = True
                    break
            else:
                self.solution_data, self.difficulty = self._solve_murder()
                success = True
                break
        
        if not success:
            if self.mode == "jewel":
                 self.solution_data, _, _ = self._solve_jewel_with_constraints()
            else:
                 self.solution_data, _ = self._solve_murder()

        self.initial_clues = self._generate_initial_clues()
        
    def _generate_raw_board(self):
        data = {char: [] for char in CHARACTERS}
        for char in CHARACTERS:
            current_loc = random.choice(ROOMS)
            data[char].append(current_loc)
            for _ in range(5):
                possible_moves = MAP_GRAPH[current_loc]
                next_loc = random.choice(possible_moves)
                data[char].append(next_loc)
                current_loc = next_loc
        board = pd.DataFrame(data).T
        board.columns = TIMES
        return board

    def _solve_jewel_with_constraints(self):
        SPAWN_ROOM = "舞蹈" 
        current_holder = None
        jewel_active = False 
        log = []
        swap_count = 0

        for t in TIMES:
            if not jewel_active:
                col_data = self.board[t]
                people_in_spawn = col_data[col_data == SPAWN_ROOM].index.tolist()
                
                if len(people_in_spawn) == 1:
                    finder = people_in_spawn[0]
                    jewel_active = True
                    current_holder = finder
                    log.append({"Time": t, "Holder": finder, "Room": SPAWN_ROOM, "Desc": "✨ 发现珠宝！"})
                else:
                    log.append({"Time": t, "Holder": "无", "Room": SPAWN_ROOM, "Desc": "无人独处，珠宝未现身"})

            else:
                loc = self.board.loc[current_holder, t]
                col_data = self.board[t]
                people_in_room = col_data[col_data == loc].index.tolist()
                count = len(people_in_room)
                next_holder = current_holder
                action = "保留"
                
                if count == 1: action = "独处(保留)"
                elif count == 2:
                    others = [p for p in people_in_room if p != current_holder]
                    next_holder = others[0]
                    action = f"交换 -> {next_holder}"
                    swap_count += 1
                elif count >= 3: action = f"人多(保留)"

                if count == 2:
                    log.append({"Time": t, "Holder": next_holder, "Room": loc, "Desc": action})
                else:
                    log.append({"Time": t, "Holder": current_holder, "Room": loc, "Desc": action})

                if t < 6: current_holder = next_holder

        spawn_condition = False
        for entry in log:
            if entry["Desc"] == "✨ 发现珠宝！" and entry["Time"] <= 3:
                spawn_condition = True
                break

        return pd.DataFrame(log), swap_count, spawn_condition

    def _solve_murder(self):
        valid_options = []
        for t in TIMES:
            for r in ROOMS:
                people = self.board[t][self.board[t] == r].index.tolist()
                if len(people) > 0:
                    for p in people:
                        valid_options.append({"Time": t, "Room": r, "Culprit": p})
        if not valid_options: return pd.DataFrame([]), 0
        truth = random.choice(valid_options)
        return pd.DataFrame([truth]), 0
    
    def _generate_initial_clues(self):
        excluded_person = None
        if self.mode == "jewel":
            t1_row = self.solution_data[self.solution_data["Time"] == 1]
            if not t1_row.empty:
                row_data = t1_row.iloc[0]
                if "发现珠宝" in str(row_data["Desc"]):
                    excluded_person = row_data["Holder"]
        
        candidates = [c for c in CHARACTERS if c != excluded_person]
        selected = random.sample(candidates, 3)
        
        clues = []
        for char in selected:
            room = self.board.loc[char, 1]
            clues.append({"char": char, "room": room}) 
            
        return clues

# ==============================================================================
# 2. Server
# ==============================================================================

@st.cache_resource
class GlobalGameState:
    def __init__(self):
        self.games = {} 
        self.logs = {}
        self.versions = {} 

    def get_game(self, room_code, mode_choice="jewel"):
        game_key = f"{room_code}_{mode_choice}"
        if game_key not in self.games:
            self._init_new_game_data(game_key, room_code, mode_choice)
        return self.games[game_key], self.logs[game_key]

    def _init_new_game_data(self, game_key, seed_val, mode_choice):
        new_game = ScenarioGenerator(seed_val=seed_val, mode=mode_choice)
        self.games[game_key] = new_game
        self.logs[game_key] = []
        self.versions[game_key] = time.time()
        self._log_initial_clues(game_key, new_game)

    def get_version(self, room_code, mode_choice):
        game_key = f"{room_code}_{mode_choice}"
        return self.versions.get(game_key, 0.0)

    def add_log(self, room_code, mode_choice, player, desc, pub, pri, log_type="normal"):
        game_key = f"{room_code}_{mode_choice}"
        timestamp = datetime.now().strftime("%H:%M")
        entry = {
            "time": timestamp, 
            "player": player, 
            "desc": desc, 
            "public": pub, 
            "private": pri, 
            "owner": player,
            "type": log_type 
        }
        if game_key in self.logs:
            self.logs[game_key].insert(0, entry)

    def reset_logs(self, room_code, mode_choice):
        game_key = f"{room_code}_{mode_choice}"
        if game_key in self.logs:
            self.logs[game_key] = []
            if game_key in self.games:
                 self._log_initial_clues(game_key, self.games[game_key])

    def new_game(self, room_code, mode_choice):
        game_key = f"{room_code}_{mode_choice}"
        new_seed = int(time.time())
        new_game = ScenarioGenerator(seed_val=new_seed, mode=mode_choice)
        self.games[game_key] = new_game
        self.logs[game_key] = []
        self.versions[game_key] = time.time()
        self._log_initial_clues(game_key, new_game)

    def _log_initial_clues(self, game_key, game_instance):
        if game_instance.initial_clues:
            clue_str_list = [f"**{c['char'].split(')')[0]})** 在 {c['room']}" for c in game_instance.initial_clues]
            clue_str = " | ".join(clue_str_list)
            
            entry = {
                "time": "00:00",
                "player": "🫅 系统",
                "desc": "发布初始信息 (T1)",
                "public": f"📍 {clue_str}",
                "private": "所有玩家可见",
                "owner": "SYSTEM",
                "type": "warning"
            }
            self.logs[game_key].append(entry)

SERVER = GlobalGameState()

# ==============================================================================
# 3. GUI
# ==============================================================================

if "default_room" not in st.session_state:
    st.session_state.default_room = str(random.randint(1000, 9999))

if "local_version" not in st.session_state:
    st.session_state.local_version = 0.0

if "has_revealed" not in st.session_state:
    st.session_state.has_revealed = False

# --- Sidebar ---
with st.sidebar:
    st.header("🕵️ 游戏设置")
    game_mode_label = st.radio("玩法模式", ["💎 名伶的珠宝 (Paris 1920)", "🎎 祭祀仪式 (Cuzco 1450)"], index=0)
    mode_code = "jewel" if "珠宝" in game_mode_label else "murder"

    st.subheader("2. 身份信息")
    username = st.text_input("你的代号", key="user_name")
    room_code = st.text_input("房间号码", value=st.session_state.default_room, key="room_code")

    st.markdown("---")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🧹 清空记录"):
            SERVER.reset_logs(room_code, mode_code)
            st.rerun()
    with c2:
        if st.button("🆕 开启新局"):
            SERVER.new_game(room_code, mode_code)
            st.rerun()

if not username or not room_code:
    st.info("👈 请点击左上角【>】展开侧边栏，输入代号开始。")
    st.stop()

# --- Sync Logic ---
game, logs = SERVER.get_game(room_code, mode_code)
server_version = SERVER.get_version(room_code, mode_code)

if st.session_state.local_version != server_version:
    st.session_state.has_revealed = False
    st.session_state.local_version = server_version
    st.rerun()

# --- Header ---
mode_icon = "💎" if mode_code == "jewel" else "🎎"
st.subheader(f"{mode_icon} 房间 {room_code} | 🕵️ {username}")

if mode_code == "jewel":
    spawn_row = game.solution_data[game.solution_data["Desc"] == "✨ 发现珠宝！"]
    st.info(f"💎 **目标：** 找出 **T6** 结束后珠宝在谁手中！")
    if spawn_row.empty:
        st.error("⚠️ 本局生成异常，建议重开")
else:
    st.error(f"🎎 **目标：** 推出 **T6** 时所有巫舞者的位置！")


# =========================================================
# Logistics
# =========================================================

st.markdown("### 🔍 发起调查")

with st.container(border=True):
    q_type = st.radio("模式", ["🏛️ 查地点", "👤 查人物"], horizontal=True, label_visibility="collapsed")
    confirm = False
    desc, pub, pri = "", "", ""

    if "查地点" in q_type:
        col_a1, col_a2 = st.columns([1.5, 1])
        with col_a1: target_room = st.selectbox("选择房间", ROOMS)
        with col_a2: selected_time = st.selectbox("选择时间", TIMES)
        
        if st.button("🔎 确认调查", use_container_width=True, type="primary"):
            people = game.board[selected_time][game.board[selected_time] == target_room].index.tolist()
            count = len(people)
            desc = f"查看了 **{target_room}** @ **T{selected_time}**"
            pub = f"该房间共有 **{count} 人**。"
            
            if count == 0:
                pri = "你看到：**空无一人**，可再进行一次调查"
            else:
                candidates = []
                for p in people:
                    is_init = (selected_time == 1) and any(c['char'] == p and c['room'] == target_room for c in game.initial_clues)
                    row = game.board.loc[p]
                    visits = len(row[row == target_room])
                    is_unique_visit = (visits == 1)
                    
                    if is_init: score = 0
                    elif is_unique_visit: score = 1
                    else: score = 2
                    
                    candidates.append({'p': p, 'score': score})
                
                random.shuffle(candidates) 
                candidates.sort(key=lambda x: x['score'], reverse=True)
                
                best = candidates[0]
                
                if best['score'] == 0:
                     chars_str = "、".join([c['p'] for c in candidates])
                     pri = f"⚠️ **无效调查**：初始线索已告知 **{chars_str}** 在 **T1** 位于此处。这是已知信息！"
                else:
                    seen = best['p']
                    pri = f"你看到了 **{seen}** 独处一室" if count==1 else f"透过缝隙认出了其中的 **{seen}**"
            
            confirm = True

    else:
        col_b1, col_b2 = st.columns([1, 1.5])
        with col_b1: target_char = st.selectbox("选择角色", CHARACTERS)
        with col_b2: target_room = st.selectbox("去过这个房间吗？", ROOMS)
        
        if st.button("🔎 确认调查", use_container_width=True, type="primary"):
            row = game.board.loc[target_char]
            matches = row[row == target_room].index.tolist()
            count = len(matches)
            desc = f"查看了 **{target_char}** 是否去过 **{target_room}**"
            pub = f"去过此处 **{count} 次**。"
            
            if count == 0:
                pri = "线索：**从未去过**，可再进行一次调查"
            else:
                candidates = []
                for t in matches:
                    is_init = (t == 1) and any(c['char'] == target_char and c['room'] == target_room for c in game.initial_clues)

                    col = game.board[t]
                    occupancy = len(col[col == target_room])
                    is_single_occupancy = (occupancy == 1)
                    
                    if is_init: score = 0
                    elif is_single_occupancy: score = 1
                    else: score = 2
                    
                    candidates.append({'t': t, 'score': score})
                
                random.shuffle(candidates)
                candidates.sort(key=lambda x: x['score'], reverse=True)
                
                best = candidates[0]
                
                if best['score'] == 0:
                    pri = f"⚠️ **无效调查**：初始线索已告知 **{target_char}** 在 **T1** 位于 **{target_room}**。且他没再去过，这是已知信息！"
                else:
                    reveal = best['t']
                    pri = f"发现时间：**T{reveal}**" if count==1 else f"发现其中一次是在 **T{reveal}**"

            confirm = True

    if confirm:
        SERVER.add_log(room_code, mode_code, username, desc, pub, pri, log_type="normal")
        st.toast("✅ 调查已同步！", icon="📨")
        time.sleep(1)
        st.rerun()

st.divider() 

col_log_title, col_log_btn = st.columns([3, 1], vertical_alignment="center")
with col_log_title:
    st.markdown("### 📡 实时记录")
with col_log_btn:
    if st.button("🔄 刷新", key="refresh_main", use_container_width=True):
        st.rerun()

if not logs: 
    st.caption("暂无记录，请在上方发起调查...")

for log in logs:
    if log.get("type") == "warning":
        st.warning(f"📢 **{log['player']}** {log['desc']} ({log['time']})\n\n{log['public']}")
    else:
        is_me = (log['owner'] == username)
        avatar_icon = "😎" if is_me else "🕵️"
        with st.chat_message(log['player'], avatar=avatar_icon):
            st.write(f"**{log['player']}** {log['desc']} ({log['time']})")
            st.info(f"📢 {log['public']}")
            if is_me: 
                if "无效调查" in log['private']:
                    st.error(f"{log['private']}")
                else:
                    st.success(f"🔒 {log['private']}")

st.markdown("---")

# =========================================================
# Solution
# =========================================================

with st.expander("🔐 查看答案"):
    if not st.session_state.has_revealed:
        st.write("点击下方按钮将显示答案，并通知所有玩家。")
        if st.button("🔴 我确认查看答案", use_container_width=True, type="primary"):
            st.session_state.has_revealed = True
            SERVER.add_log(
                room_code, mode_code,
                username, 
                "⛔ 查看了谜底！游戏可能已结束。", 
                "注意：该玩家已知晓真相", 
                "N/A",
                log_type="warning"
            )
            st.rerun()
    
    if st.session_state.has_revealed:
        tab_ans_1, tab_ans_2 = st.tabs(["💎 珠宝流向", "🗺️ 位置表"])
        
        with tab_ans_1:
            if mode_code == "jewel":
                st.dataframe(game.solution_data, use_container_width=True, hide_index=True)
                final = game.solution_data.iloc[-1]
                st.error(f"🏆 **最终答案**: 珠宝在 **{final['Holder']}** 手中，位于 **{final['Room']}**")
            else:
                truth = game.solution_data.iloc[0]
                st.error(f"🏆 **凶手真相**: **{truth['Culprit']}** 在 **{truth['Room']}** (T{truth['Time']}) 作案")
        
        with tab_ans_2:
            st.dataframe(game.board, use_container_width=True)
            st.caption("行：角色 | 列：时间 (T1-T6)")

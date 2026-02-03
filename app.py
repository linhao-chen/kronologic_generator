import streamlit as st
import pandas as pd
import base64
import random
import time
import os
from datetime import datetime

# ==============================================================================
# 0. Authentication & Config
# ==============================================================================

st.set_page_config(page_title="Kronologic (SoCal 2026)", layout="wide", initial_sidebar_state="collapsed")

def get_base64(bin_file):
    with open(bin_file, 'rb') as f:
        data = f.read()
    return base64.b64encode(data).decode()

def check_password():
    SECRET_PASSWORD = st.secrets["PASSWORD"]

    if "password_correct" not in st.session_state:
        st.session_state.password_correct = False

    if not st.session_state.password_correct:
        local_image_path = "cover.png"
        
        background_style = """
        <style>
        .stApp { background-color: #1E1E1E; }
        </style>
        """

        if os.path.exists(local_image_path):
            try:
                img_ext = local_image_path.split(".")[-1]
                base64_str = get_base64(local_image_path)
                
                background_style = f"""
                <style>
                .stApp {{
                    background-image: url("data:image/{img_ext};base64,{base64_str}");
                    background-size: cover;
                    background-position: center 55px;
                    background-repeat: no-repeat;
                    background-attachment: fixed;
                }}
                
                input {{
                    background-color: rgba(0, 0, 0, 0.6) !important;
                    color: white !important;
                    border: 1px solid rgba(255, 255, 255, 0.2) !important;
                }}

                div.stButton > button {{
                    background-color: rgba(0, 0, 0, 0.6) !important;
                    color: white !important;
                    border: 1px solid rgba(255, 255, 255, 0.2) !important;
                }}

                div.stButton > button:hover {{
                    background-color: #000000 !important;
                    color: #ffffff !important;
                    border-color: #ffffff !important;
                    transform: scale(1.02);
                }}

                div.stButton > button:active {{
                    background-color: #333333 !important;
                    border-color: #ffffff !important;
                }}

                [data-testid="stAlert"] {{
                    background-color: rgba(255, 230, 230, 0.95) !important;
                    border: 1px solid #ff4b4b !important;
                    color: #7d1515 !important;
                    box-shadow: 0 4px 10px rgba(0,0,0,0.5);
                }}

                [data-testid="stAlert"] p, [data-testid="stAlert"] svg {{
                    fill: #7d1515 !important;
                    color: #7d1515 !important;
                }}

                .main .block-container {{
                    padding-top: 50px;
                }}
                </style>
                """
            except Exception as e:
                st.error(f"Error loading background: {e}")

        st.markdown(background_style, unsafe_allow_html=True)

        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            st.markdown("<br><br><br>", unsafe_allow_html=True)
            
            password = st.text_input("", type="password")
            
            if st.button("Authenticate", use_container_width=True):
                if password == SECRET_PASSWORD:
                    st.session_state.password_correct = True
                    st.rerun()
                else:
                    st.error("Access Denied")
        
        st.stop()

check_password()

# ==============================================================================
# 1. Shared Constants
# ==============================================================================

TIMES = [1, 2, 3, 4, 5, 6]

# ==============================================================================
# 2. Mode Configurations
#    Each mode's static data is declared once here, then referenced by its handler.
# ==============================================================================

# ---------- Jewel (Paris 1920) ----------
JEWEL_ROOMS      = ["牌坊", "信号", "鱿鱼", "面具", "音乐", "舞蹈"]
JEWEL_CHARACTERS = ["(A) Accessoiriste", "(B) Baroness", "(C) Chauffeur",
                    "(D) Director", "(J) Journalist", "(S) Soprano"]
JEWEL_GRAPH = {
    "牌坊": ["信号", "鱿鱼"],
    "信号": ["鱿鱼", "牌坊"],
    "鱿鱼": ["面具", "信号", "牌坊"],
    "面具": ["鱿鱼", "音乐", "舞蹈"],
    "音乐": ["面具", "舞蹈"],
    "舞蹈": ["面具", "音乐"]
}

# ---------- Ritual (Cuzco 1450) — shared by easy & hard ----------
RITUAL_TERRAIN   = ["山", "太阳", "星星", "台阶", "圆盘", "田"]
RITUAL_SHARMANS  = ["(A) Artisan", "(E) Educator", "(F) Farmer",
                    "(M) Merchant", "(P) Priestess", "(S) Soldier"]

# ---------- SD Engineer (San Diego) ----------
SD_AREA        = ["La Jolla", "Mira Mesa", "Del Mar", "4S Ranch", "Convoy"]
SD_CHARACTERS  = ["(E) Eric", "(G) Grace", "(R) Rachel",
                  "(W) Wen", "(X) Xaiver", "(Z) Zero"]
SD_GRAPH = {
    "Del Mar":    ["4S Ranch", "Mira Mesa", "La Jolla"],
    "La Jolla":   ["Del Mar", "Mira Mesa", "Convoy"],
    "Mira Mesa":  ["Del Mar", "Convoy", "La Jolla", "4S Ranch"],
    "Convoy":     ["Mira Mesa", "4S Ranch", "La Jolla"],
    "4S Ranch":   ["Del Mar", "Convoy", "Mira Mesa"]
}

# ==============================================================================
# 3. Per-Mode Handler Classes
#    Each class owns: board generation, solving, initial-clue generation,
#    and the GUI helpers (header, investigation, scratchpad, solution panel).
#    The base class documents the contract; concrete classes fill it in.
# ==============================================================================

class BaseModeHandler:
    # --- static metadata (override in subclass) ---
    MODE_CODE   = ""          # e.g. "jewel"
    ICON        = ""          # e.g. "💎"
    CHARACTERS  = []          # list shown in person-query dropdown
    ROOMS       = []          # list shown in location-query dropdown
    INVESTIG_LOCATION_LABEL = "选择房间"
    INVESTIG_PERSON_LABEL   = "选择角色"
    INVESTIG_ROOM_LABEL     = "去过这个房间吗？"
    INVESTIG_TIME_OPTIONS   = TIMES          # full [1..6] by default

    # --- board generation helpers (called by ScenarioGenerator) ---
    def generate_board(self, rng_instance) -> pd.DataFrame:
        raise NotImplementedError

    def solve(self, board: pd.DataFrame):
        """Return (solution_data, is_valid).  Called once after board is built."""
        raise NotImplementedError

    def generate_initial_clues(self, board: pd.DataFrame, solution_data) -> list:
        raise NotImplementedError

    # --- GUI helpers (called by the main GUI sections) ---
    def render_header(self, game):
        raise NotImplementedError

    def render_solution_panel(self, game):
        raise NotImplementedError

    def log_extra_system_clues(self, game) -> list:
        """Return extra system-log entries beyond the initial-clue one.
        Default: none.  Ritual modes override to add the pace log."""
        return []

    # --- visual layout hint for scratchpad map ---
    def scratchpad_rooms_order(self) -> list:
        return self.ROOMS


# --------------------------------------------------------------------------
# 3a.  Jewel — 名伶的珠宝 (Paris 1920)
# --------------------------------------------------------------------------
class JewelHandler(BaseModeHandler):
    MODE_CODE   = "jewel"
    ICON        = "💎"
    CHARACTERS  = JEWEL_CHARACTERS
    ROOMS       = JEWEL_ROOMS
    INVESTIG_LOCATION_LABEL = "选择房间"
    INVESTIG_PERSON_LABEL   = "选择角色"
    INVESTIG_ROOM_LABEL     = "去过这个房间吗？"
    INVESTIG_TIME_OPTIONS   = TIMES

    # ---- board generation ----
    def generate_board(self, rng_instance) -> pd.DataFrame:
        data = {char: [] for char in JEWEL_CHARACTERS}
        for char in JEWEL_CHARACTERS:
            current_loc = random.choice(JEWEL_ROOMS)
            data[char].append(current_loc)
            for _ in range(5):
                possible_moves = JEWEL_GRAPH[current_loc]
                next_loc = random.choice(possible_moves)
                data[char].append(next_loc)
                current_loc = next_loc

        board = pd.DataFrame(data).T
        board.columns = TIMES
        return board

    # ---- solving ----
    def solve(self, board: pd.DataFrame):
        SPAWN_ROOM     = "舞蹈"
        current_holder = None
        jewel_active   = False
        log            = []

        for t in TIMES:
            if not jewel_active:
                col_data = board[t]
                people_in_spawn = col_data[col_data == SPAWN_ROOM].index.tolist()

                if len(people_in_spawn) == 1:
                    finder       = people_in_spawn[0]
                    jewel_active = True
                    current_holder = finder
                    log.append({"Time": t, "Holder": finder, "Room": SPAWN_ROOM, "Desc": "✨ 发现珠宝！"})
                else:
                    log.append({"Time": t, "Holder": "无", "Room": SPAWN_ROOM, "Desc": "无人独处，珠宝未现身"})
            else:
                loc          = board.loc[current_holder, t]
                col_data     = board[t]
                people_in_room = col_data[col_data == loc].index.tolist()
                count        = len(people_in_room)
                next_holder  = current_holder
                action       = "保留"

                if   count == 1: action = "独处(保留)"
                elif count == 2:
                    others      = [p for p in people_in_room if p != current_holder]
                    next_holder = others[0]
                    action      = f"交换 -> {next_holder}"
                elif count >= 3: action = f"人多(保留)"

                if count == 2:
                    log.append({"Time": t, "Holder": next_holder,     "Room": loc, "Desc": action})
                else:
                    log.append({"Time": t, "Holder": current_holder,  "Room": loc, "Desc": action})

                if t < 6:
                    current_holder = next_holder

        # validity: jewel must spawn by T3
        spawn_condition = False
        for entry in log:
            if entry["Desc"] == "✨ 发现珠宝！" and entry["Time"] <= 3:
                spawn_condition = True
                break

        return pd.DataFrame(log), spawn_condition

    # ---- initial clues ----
    def generate_initial_clues(self, board, solution_data) -> list:
        excluded_person = None
        t1_row = solution_data[solution_data["Time"] == 1]
        if not t1_row.empty:
            row_data = t1_row.iloc[0]
            if "发现珠宝" in str(row_data["Desc"]):
                excluded_person = row_data["Holder"]

        candidates = [c for c in JEWEL_CHARACTERS if c != excluded_person]
        selected   = random.sample(candidates, 3)
        return [{"char": char, "room": board.loc[char, 1]} for char in selected]

    # ---- GUI ----
    def render_header(self, game):
        st.info("💎 **目标：** 找出 **T6** 结束后珠宝在谁手中！")

    def render_solution_panel(self, game):
        st.caption("随机种子: " + str(game.seed_val))
        tab_ans_1, tab_ans_2 = st.tabs(["💎 珠宝流向", "🗺️ 位置表"])

        with tab_ans_1:
            st.dataframe(game.solution_data, use_container_width=True, hide_index=True)
            final = game.solution_data.iloc[-1]
            st.error(f"🏆 **最终答案**: 珠宝在 **{final['Holder']}** 手中，位于 **{final['Room']}**")

        with tab_ans_2:
            st.dataframe(game.board, use_container_width=True)
            st.caption("行：角色 | 列：时间 (T1-T6)")


# --------------------------------------------------------------------------
# 3b.  Ritual — 祭祀仪式 (Cuzco 1450)  (easy & hard share one class)
# --------------------------------------------------------------------------
class RitualHandler(BaseModeHandler):
    ICON        = "🎎"
    CHARACTERS  = RITUAL_SHARMANS
    ROOMS       = RITUAL_TERRAIN
    INVESTIG_LOCATION_LABEL = "选择房间"
    INVESTIG_PERSON_LABEL   = "选择巫舞者"
    INVESTIG_ROOM_LABEL     = "去过这个祭坛吗？"
    INVESTIG_TIME_OPTIONS   = TIMES[1:5]       # T2-T5 only

    def __init__(self, mode_code: str):
        self.MODE_CODE = mode_code             # "ritual_easy" | "ritual_hard"

    # ---- board generation ----
    def generate_board(self, rng_instance) -> pd.DataFrame:
        """rng_instance is the ScenarioGenerator; we attach ritual-specific state to it."""
        rng_instance.ritual_patterns = {}
        rng_instance.pace_list       = []

        data = {char: [] for char in RITUAL_SHARMANS}

        for char in RITUAL_SHARMANS:
            start_room   = random.choice(RITUAL_TERRAIN)
            start_index  = RITUAL_TERRAIN.index(start_room)
            pattern      = self._generate_valid_pattern(rng_instance)
            pattern_offset = random.randint(0, len(pattern) - 1)

            rng_instance.ritual_patterns[char] = {
                "pattern":      pattern,
                "start_offset": pattern_offset,
                "start_room":   start_room
            }

            locs        = [start_room]          # T1
            current_idx = start_index
            cycle_len   = len(pattern)

            for i in range(5):
                step_idx    = (pattern_offset + i) % cycle_len
                steps       = pattern[step_idx]
                current_idx = (current_idx + steps) % 6
                locs.append(RITUAL_TERRAIN[current_idx])

            data[char] = locs

        board = pd.DataFrame(data).T
        board.columns = TIMES
        return board

    def _generate_valid_pattern(self, rng_instance) -> list:
        group_1 = ["111","112","113","222","123","133","122","223","233","333"]
        group_2 = ["1112","1113","1123","1133","1122"]
        group_3 = ["1222","1223","1233","1333","2223","2233","2333"]

        if self.MODE_CODE == "ritual_easy":
            base_weights = [100, 0, 0]
        else:
            base_weights = [66, 20, 14]

        group_list = [group_1, group_2, group_3]
        while True:
            group_selected = random.choices(group_list, weights=base_weights, k=1)[0]
            selection      = random.choices(group_selected)
            result         = list(map(int, selection[0]))
            if result not in rng_instance.pace_list:
                rng_instance.pace_list.append(result)
                return result

    # ---- solving ----
    def solve(self, board: pd.DataFrame):
        # Ritual has no single "jewel" solution; validity is always True.
        # solution_data is unused in the ritual answer panel (board is shown directly).
        valid_options = []
        for t in TIMES:
            for r in RITUAL_TERRAIN:
                people = board[t][board[t] == r].index.tolist()
                if len(people) > 0:
                    for p in people:
                        valid_options.append({"Time": t, "Room": r, "Culprit": p})
        if not valid_options:
            return pd.DataFrame([]), 0
        truth = random.choice(valid_options)
        return pd.DataFrame([truth]), 0

    # ---- initial clues ----
    def generate_initial_clues(self, board, solution_data) -> list:
        return [{"char": char, "room": board.loc[char, 1]} for char in RITUAL_SHARMANS]

    # ---- extra system log: pace info ----
    def log_extra_system_clues(self, game) -> list:
        pace_list = [str(pace) for pace in game.pace_list]
        pace_list.sort(key=lambda x: (len(x), x))
        pace_str = " , ".join(pace_list)
        return [{
            "time":    "00:00",
            "player":  "系统",
            "desc":    "发布舞步信息 (Pace)",
            "public":  f"👣 {pace_str}",
            "private": "所有玩家可见",
            "owner":   "SYSTEM",
            "type":    "warning"
        }]

    # ---- GUI ----
    def render_header(self, game):
        st.error("🎎 **目标：** 推出 **T6** 时所有巫舞者的位置！")

    def render_solution_panel(self, game):
        st.caption("随机种子: " + str(game.seed_val))
        tab_ans_1, tab_ans_2 = st.tabs(["🗺️ 位置表", "💃 祭祀步频"])

        with tab_ans_1:
            st.dataframe(game.board, use_container_width=True)
            t6_data = game.board[6].sort_index()
            lines   = [f"**{char.split(')')[0]})**: {room}" for char, room in t6_data.items()]
            st.error(f"🏆 **最终答案**: {' | '.join(lines)}")

        with tab_ans_2:
            rows = []
            for char, info in game.ritual_patterns.items():
                base_pat = info['pattern']
                offset   = info['start_offset']
                actual_pat = base_pat[offset:] + base_pat[:offset]
                rows.append({
                    "角色":       char,
                    "T1 位置":    info['start_room'],
                    "步频模式":   str(base_pat),
                    "偏移量":     offset,
                    "实际执行":   str(actual_pat),
                    "_sort_key":  actual_pat
                })
            df = pd.DataFrame(rows)
            df = df.sort_values(by="_sort_key", key=lambda x: x.map(lambda k: (len(k), k)))
            df = df.drop(columns=["_sort_key"]).reset_index(drop=True)
            st.dataframe(df, use_container_width=True, hide_index=True)

    # ---- scratchpad layout ----
    def scratchpad_rooms_order(self) -> list:
        # first 3 forward, last 3 reversed
        return RITUAL_TERRAIN[:3] + RITUAL_TERRAIN[3:][::-1]


# --------------------------------------------------------------------------
# 3c.  SD Engineer — 圣地亚哥的天才工程师
# --------------------------------------------------------------------------
class SDEngineerHandler(BaseModeHandler):
    MODE_CODE   = "sd_engineer"
    ICON        = "👷‍♂️"
    CHARACTERS  = SD_CHARACTERS
    ROOMS       = SD_AREA
    INVESTIG_LOCATION_LABEL = "选择地点"
    INVESTIG_PERSON_LABEL   = "选择人物"
    INVESTIG_ROOM_LABEL     = "去过这个地区吗？"
    INVESTIG_TIME_OPTIONS   = TIMES

    # ---- board generation ----
    # SD Engineer currently reuses the dancer/ritual board-gen path (else-branch).
    # We replicate that exact logic here so adding a real SD board later is isolated.
    def generate_board(self, rng_instance) -> pd.DataFrame:
        rng_instance.ritual_patterns = {}
        rng_instance.pace_list       = []

        data = {char: [] for char in SD_CHARACTERS}
        for char in SD_CHARACTERS:
            start_room   = random.choice(RITUAL_TERRAIN)
            start_index  = RITUAL_TERRAIN.index(start_room)
            pattern      = self._generate_valid_pattern(rng_instance)
            pattern_offset = random.randint(0, len(pattern) - 1)

            rng_instance.ritual_patterns[char] = {
                "pattern":      pattern,
                "start_offset": pattern_offset,
                "start_room":   start_room
            }

            locs        = [start_room]
            current_idx = start_index
            cycle_len   = len(pattern)

            for i in range(5):
                step_idx    = (pattern_offset + i) % cycle_len
                steps       = pattern[step_idx]
                current_idx = (current_idx + steps) % 6
                locs.append(RITUAL_TERRAIN[current_idx])

            data[char] = locs

        board = pd.DataFrame(data).T
        board.columns = TIMES
        return board

    def _generate_valid_pattern(self, rng_instance) -> list:
        """SD Engineer currently inherits the hard-ritual weights (the else-branch default)."""
        group_1 = ["111","112","113","222","123","133","122","223","233","333"]
        group_2 = ["1112","1113","1123","1133","1122"]
        group_3 = ["1222","1223","1233","1333","2223","2233","2333"]
        base_weights = [66, 20, 14]

        group_list = [group_1, group_2, group_3]
        while True:
            group_selected = random.choices(group_list, weights=base_weights, k=1)[0]
            selection      = random.choices(group_selected)
            result         = list(map(int, selection[0]))
            if result not in rng_instance.pace_list:
                rng_instance.pace_list.append(result)
                return result

    # ---- solving ----
    def solve(self, board: pd.DataFrame):
        valid_options = []
        for t in TIMES:
            for r in RITUAL_TERRAIN:
                people = board[t][board[t] == r].index.tolist()
                if len(people) > 0:
                    for p in people:
                        valid_options.append({"Time": t, "Room": r, "Culprit": p})
        if not valid_options:
            return pd.DataFrame([]), 0
        truth = random.choice(valid_options)
        return pd.DataFrame([truth]), 0

    # ---- initial clues ----
    def generate_initial_clues(self, board, solution_data) -> list:
        return [{"char": char, "room": board.loc[char, 1]} for char in SD_CHARACTERS]

    # ---- extra system log: pace info (same as ritual, since board gen is shared) ----
    def log_extra_system_clues(self, game) -> list:
        pace_list = [str(pace) for pace in game.pace_list]
        pace_list.sort(key=lambda x: (len(x), x))
        pace_str = " , ".join(pace_list)
        return [{
            "time":    "00:00",
            "player":  "系统",
            "desc":    "发布舞步信息 (Pace)",
            "public":  f"👣 {pace_str}",
            "private": "所有玩家可见",
            "owner":   "SYSTEM",
            "type":    "warning"
        }]

    # ---- GUI ----
    def render_header(self, game):
        st.error("👷‍♂️ **目标：** 找出炸毁SD桥梁的工程师！")

    def render_solution_panel(self, game):
        st.caption("随机种子: " + str(game.seed_val))
        tab_ans_1, tab_ans_2 = st.tabs(["🗺️ 位置表", "💃 祭祀步频"])

        with tab_ans_1:
            st.dataframe(game.board, use_container_width=True)
            t6_data = game.board[6].sort_index()
            lines   = [f"**{char.split(')')[0]})**: {room}" for char, room in t6_data.items()]
            st.error(f"🏆 **最终答案**: {' | '.join(lines)}")

        with tab_ans_2:
            rows = []
            for char, info in game.ritual_patterns.items():
                base_pat   = info['pattern']
                offset     = info['start_offset']
                actual_pat = base_pat[offset:] + base_pat[:offset]
                rows.append({
                    "角色":       char,
                    "T1 位置":    info['start_room'],
                    "步频模式":   str(base_pat),
                    "偏移量":     offset,
                    "实际执行":   str(actual_pat),
                    "_sort_key":  actual_pat
                })
            df = pd.DataFrame(rows)
            df = df.sort_values(by="_sort_key", key=lambda x: x.map(lambda k: (len(k), k)))
            df = df.drop(columns=["_sort_key"]).reset_index(drop=True)
            st.dataframe(df, use_container_width=True, hide_index=True)


# ==============================================================================
# 4. Mode Registry  —  single source of truth for "which handler runs when"
# ==============================================================================

MODE_HANDLERS: dict[str, BaseModeHandler] = {
    "jewel":        JewelHandler(),
    "ritual_easy":  RitualHandler("ritual_easy"),
    "ritual_hard":  RitualHandler("ritual_hard"),
    "sd_engineer":  SDEngineerHandler(),
}

def get_handler(mode_code: str) -> BaseModeHandler:
    return MODE_HANDLERS[mode_code]


# ==============================================================================
# 5. ScenarioGenerator  —  now thin; delegates everything to the active handler
# ==============================================================================

class ScenarioGenerator:
    def __init__(self, seed_val, mode="jewel"):
        self.seed_val      = seed_val
        self.mode          = mode
        self.initial_clues = []
        self.query         = {}
        self.handler       = get_handler(mode)

        if seed_val is not None:
            random.seed(seed_val)

        max_attempts = 1000

        for i in range(max_attempts):
            self.board = self.handler.generate_board(self)

            self.solution_data, is_valid = self.handler.solve(self.board)
            if is_valid:
                break
            # modes that always return truthy validity (ritual / sd) break on first try

        self.initial_clues = self.handler.generate_initial_clues(self.board, self.solution_data)


# ==============================================================================
# 6. Server  —  GlobalGameState  (unchanged logic, uses handler for system logs)
# ==============================================================================

@st.cache_resource
class GlobalGameState:
    def __init__(self):
        self.games    = {}
        self.logs     = {}
        self.versions = {}

    def get_game(self, room_code, mode_choice="jewel", forced_seed=""):
        game_key = f"{room_code}_{mode_choice}"
        if forced_seed:
            seed_val = int(forced_seed)
        else:
            seed_val = int(time.time())
        if game_key not in self.games:
            self._init_new_game_data(game_key, seed_val, mode_choice)
        return self.games[game_key], self.logs[game_key]

    def _init_new_game_data(self, game_key, seed_val, mode_choice):
        new_game = ScenarioGenerator(seed_val=seed_val, mode=mode_choice)
        self.games[game_key]    = new_game
        self.logs[game_key]     = []
        self.versions[game_key] = time.time()
        self._log_initial_clues(game_key, new_game, mode_choice)

    def get_version(self, room_code, mode_choice):
        game_key = f"{room_code}_{mode_choice}"
        return self.versions.get(game_key, 0.0)

    def add_log(self, room_code, mode_choice, player, desc, pub, pri, log_type="normal"):
        game_key  = f"{room_code}_{mode_choice}"
        timestamp = datetime.now().strftime("%H:%M")
        entry = {
            "time":    timestamp,
            "player":  player,
            "desc":    desc,
            "public":  pub,
            "private": pri,
            "owner":   player,
            "type":    log_type
        }
        if game_key in self.logs:
            self.logs[game_key].insert(0, entry)

    def reset_logs(self, room_code, mode_choice):
        game_key = f"{room_code}_{mode_choice}"
        if game_key in self.logs:
            self.logs[game_key] = []
            if game_key in self.games:
                self._log_initial_clues(game_key, self.games[game_key], mode_choice)

    def new_game(self, room_code, mode_choice, forced_seed):
        game_key = f"{room_code}_{mode_choice}"
        if forced_seed:
            seed_val = int(forced_seed)
        else:
            seed_val = int(time.time())
        new_game = ScenarioGenerator(seed_val=seed_val, mode=mode_choice)
        self.games[game_key]    = new_game
        self.logs[game_key]     = []
        self.versions[game_key] = time.time()
        self._log_initial_clues(game_key, new_game, mode_choice)

    # ---- system-log helper (initial clues + any mode-specific extras) ----
    def _log_initial_clues(self, game_key, game_instance, mode_choice):
        handler = get_handler(mode_choice)

        if game_instance.initial_clues:
            clue_str_list = [f"**{c['char'].split(')')[0]})** 在 {c['room']}" for c in game_instance.initial_clues]
            clue_str      = " | ".join(clue_str_list)

            entry = {
                "time":    "00:00",
                "player":  "系统",
                "desc":    "发布初始信息 (T1)",
                "public":  f"📍 {clue_str}",
                "private": "所有玩家可见",
                "owner":   "SYSTEM",
                "type":    "warning"
            }
            self.logs[game_key].append(entry)

        # let the handler append any extra system entries (e.g. pace)
        for extra in handler.log_extra_system_clues(game_instance):
            self.logs[game_key].append(extra)


SERVER = GlobalGameState()

# ==============================================================================
# 7. GUI
# ==============================================================================

if "default_room" not in st.session_state:
    st.session_state.default_room = str(random.randint(1000, 9999))

if "local_version" not in st.session_state:
    st.session_state.local_version = 0.0

if "has_revealed" not in st.session_state:
    st.session_state.has_revealed = False

# ==============================================================================
# 7.1 Sidebar
# ==============================================================================

with st.sidebar:
    st.header("🕵️ 游戏设置")
    game_mode_label = st.radio("玩法模式", [
        "💎 名伶的珠宝 (Paris 1920)",
        "💃 祭祀仪式-简单 (Cuzco 1450)",
        "🎎 祭祀仪式-复杂 (Cuzco 1450)",
        "👷‍♂️ 圣地亚哥的天才工程师"
    ], index=0)

    # map radio label → mode_code
    if "简单" in game_mode_label:
        mode_code = "ritual_easy"
    elif "复杂" in game_mode_label:
        mode_code = "ritual_hard"
    elif "圣地亚哥" in game_mode_label:
        mode_code = "sd_engineer"
    else:
        mode_code = "jewel"

    handler = get_handler(mode_code)          # active handler for the rest of the page

    st.subheader("身份/房间信息")
    username    = st.text_input("你的代号", key="user_name")
    room_code   = st.text_input("房间号码", value=st.session_state.default_room, key="room_code")
    forced_seed = st.text_input("随机种子 (Optional)", value="")

    st.markdown("---")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🧹 清空记录"):
            SERVER.reset_logs(room_code, mode_code)
            st.rerun()
    with c2:
        if st.button("🆕 开启新局"):
            SERVER.new_game(room_code, mode_code, forced_seed)
            st.rerun()

if not username or not room_code:
    st.info("👈 请点击左上角【>】展开侧边栏，输入代号开始。")
    st.stop()

# =========================================================
# 7.2 Header
# =========================================================

game, logs = SERVER.get_game(room_code, mode_code, forced_seed)
server_version = SERVER.get_version(room_code, mode_code)

if st.session_state.local_version != server_version:
    st.session_state.has_revealed = False
    st.session_state.local_version = server_version
    st.rerun()

st.subheader(f"{handler.ICON} 房间 {room_code} | 🕵️ {username}")
handler.render_header(game)                   # mode-specific goal banner

# =========================================================
# 7.3 Investigation
# =========================================================

st.markdown("### 🔍 发起调查")

with st.container(border=True):
    q_type   = st.radio("模式", ["🏛️ 调查地点", "🪪 调查人物"], horizontal=True, label_visibility="collapsed")
    confirm  = False
    desc, pub, pri = "", "", ""

    if "调查地点" in q_type:
        col_a1, col_a2 = st.columns([1.5, 1])
        with col_a1:
            target_room    = st.selectbox(handler.INVESTIG_LOCATION_LABEL, handler.ROOMS)
        with col_a2:
            selected_time  = st.selectbox("选择时间", handler.INVESTIG_TIME_OPTIONS)

        if st.button("🔎 确认调查", use_container_width=True, type="primary"):
            people = game.board[selected_time][game.board[selected_time] == target_room].index.tolist()
            count  = len(people)
            desc   = f"查看了 **{target_room}** @ **T{selected_time}**"
            pub    = f"该房间共有 **{count} 人**。"

            query_tuple = (target_room, selected_time)
            if query_tuple in game.query.keys():
                pri = game.query[query_tuple]
            else:
                if count == 0:
                    pri = "你看到：**空无一人**，可再进行一次调查"
                else:
                    candidates = []
                    for p in people:
                        is_init = (selected_time == 1) and any(
                            c['char'] == p and c['room'] == target_room for c in game.initial_clues
                        )
                        row          = game.board.loc[p]
                        visits       = len(row[row == target_room])
                        is_unique_visit = (visits == 1)

                        if   is_init:          score = 0
                        elif is_unique_visit:  score = 1
                        else:                  score = 2

                        candidates.append({'p': p, 'score': score})

                    random.shuffle(candidates)
                    candidates.sort(key=lambda x: x['score'], reverse=True)
                    best = candidates[0]

                    if best['score'] == 0:
                        chars_str = "、".join([c['p'] for c in candidates])
                        pri = f"⚠️ **已知信息**：初始线索已告知 **{chars_str}** 在 **T1** 位于此处, 可再调查一次。"
                    else:
                        seen = best['p']
                        pri  = f"你看到了 **{seen}** 独处一室" if count == 1 else f"透过缝隙认出了其中的 **{seen}**"

                game.query[query_tuple] = pri

            confirm = True

    else:   # 调查人物
        col_b1, col_b2 = st.columns([1, 1.5])
        with col_b1:
            target_char = st.selectbox(handler.INVESTIG_PERSON_LABEL, handler.CHARACTERS)
        with col_b2:
            target_room = st.selectbox(handler.INVESTIG_ROOM_LABEL,   handler.ROOMS)

        if st.button("🔎 确认调查", use_container_width=True, type="primary"):
            row     = game.board.loc[target_char]
            matches = row[row == target_room].index.tolist()
            count   = len(matches)
            desc    = f"查看了 **{target_char}** 是否去过 **{target_room}**"
            pub     = f"去过此处 **{count} 次**。"

            query_tuple = (target_char, target_room)
            if query_tuple in game.query.keys():
                pri = game.query[query_tuple]
            else:
                if count == 0:
                    pri = "线索：**从未去过**，可再进行一次调查"
                else:
                    candidates = []
                    for t in matches:
                        is_init = (t == 1) and any(
                            c['char'] == target_char and c['room'] == target_room for c in game.initial_clues
                        )
                        col              = game.board[t]
                        occupancy        = len(col[col == target_room])
                        is_single_occupancy = (occupancy == 1)

                        if   is_init:              score = 0
                        elif is_single_occupancy:  score = 1
                        else:                      score = 2

                        candidates.append({'t': t, 'score': score})

                    random.shuffle(candidates)
                    candidates.sort(key=lambda x: x['score'], reverse=True)
                    best = candidates[0]

                    if best['score'] == 0:
                        pri = f"⚠️ **已知信息**：初始线索已告知 **{target_char}** 在 **T1** 位于 **{target_room}**, 可再调查一次。"
                    else:
                        reveal = best['t']
                        pri    = f"发现时间：**T{reveal}**" if count == 1 else f"发现其中一次是在 **T{reveal}**"

                game.query[query_tuple] = pri

            confirm = True

    if confirm:
        SERVER.add_log(room_code, mode_code, username, desc, pub, pri, log_type="normal")
        st.toast("✅ 调查已同步！", icon="📨")
        time.sleep(1)
        st.rerun()

st.divider()

# =========================================================
# 7.4 History
# =========================================================

@st.fragment(run_every=5)
def sync_logs():
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
            is_me       = (log['owner'] == username)
            avatar_icon = "😎" if is_me else "🕵️"
            with st.chat_message(log['player'], avatar=avatar_icon):
                st.write(f"**{log['player']}** {log['desc']} ({log['time']})")
                st.info(f"📢 {log['public']}")
                if is_me:
                    if "已知信息" in log['private']:
                        st.error(f"{log['private']}")
                    else:
                        st.success(f"🔒 {log['private']}")

    st.markdown("---")

sync_logs()

# =========================================================
# 7.5 Scratchpad (Beta)
# =========================================================

current_chars = handler.CHARACTERS
current_rooms = handler.ROOMS
str_times     = [str(t) for t in TIMES]
storage_key   = f"scratch_storage_{mode_code}"

if storage_key not in st.session_state:
    init_df          = pd.DataFrame(columns=["Role"] + str_times)
    init_df["Role"]  = current_chars
    st.session_state[storage_key] = init_df

original_df = st.session_state[storage_key]

with st.expander("📝 草稿本 (BETA)"):
    column_config = {
        "Role": st.column_config.TextColumn("角色", disabled=True, width="medium"),
    }
    for t_str in str_times:
        column_config[t_str] = st.column_config.SelectboxColumn(
            f"T{t_str}", width="small", options=current_rooms, required=False
        )

    edited_df = st.data_editor(
        original_df,
        column_config=column_config,
        use_container_width=True,
        hide_index=True,
        key=f"editor_{mode_code}"
    )

    if not edited_df.equals(original_df):
        st.session_state[storage_key] = edited_df
        st.rerun()

    st.divider()

    visual_rooms_order = handler.scratchpad_rooms_order()

    map_tabs = st.tabs([f"🕒 T{t}" for t in str_times])

    for i, t_str in enumerate(str_times):
        with map_tabs[i]:
            room_occupancy = {r: [] for r in current_rooms}
            unknown_chars  = []

            for index, row in edited_df.iterrows():
                char = row["Role"]
                loc  = row[t_str]

                if pd.isna(char):
                    continue

                if loc and loc in room_occupancy:
                    short_name = char.split(")")[0] + ")"
                    room_occupancy[loc].append(short_name)
                else:
                    unknown_chars.append(char.split(")")[0] + ")")

            cols = st.columns(3)
            for idx, room in enumerate(visual_rooms_order):
                with cols[idx % 3]:
                    occupants = room_occupancy[room]
                    if occupants:
                        content = " ".join([f"**{p}**" for p in occupants])
                        st.success(f"📍 **{room}**\n\n{content}")
                    else:
                        st.error(f"📍 **{room}**\n\n*(空)*")

            if unknown_chars:
                st.caption(f"❓ 未定: {', '.join(unknown_chars)}")

    if st.button("🗑️ 清空当前笔记"):
        empty_df         = pd.DataFrame(columns=["Role"] + str_times)
        empty_df["Role"] = current_chars
        st.session_state[storage_key] = empty_df
        st.rerun()

st.markdown("---")

# =========================================================
# 7.6 Solution
# =========================================================

with st.expander("🔐 查看答案"):
    if not st.session_state.has_revealed:
        st.write("点击下方按钮将显示答案，并通知所有玩家。")
        if st.button("🔴 我确认查看答案", use_container_width=True, type="primary"):
            st.session_state.has_revealed = True
            SERVER.add_log(
                room_code, mode_code,
                username,
                "查看了答案！游戏可能已结束。",
                "注意：该玩家已知晓真相",
                "N/A",
                log_type="warning"
            )
            st.rerun()

    if st.session_state.has_revealed:
        handler.render_solution_panel(game)   # fully mode-specific

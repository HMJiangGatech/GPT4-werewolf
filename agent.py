import random
import openai
import os

BOT_NAMES = [
    'Alice', 'Bob', 'Charlie', 'David', 'Eve', 'Fred', 'Ginny', 'Harriet', 'Ileana', 'Joseph',
]
TOTAL_ROUNDS = 3
INCLUDE_PEOPLE = True
OPENAI_MODEL = "gpt-4"
# OPENAI_MODEL = "gpt-3.5-turbo"

OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
if not OPENAI_API_KEY:
    # read from file
    with open('OPENAI_API_KEY', 'r') as f:
        OPENAI_API_KEY = f.read().strip()

openai.api_key = OPENAI_API_KEY

GAME_PROMPT = """
# 一夜狼人的规则

游戏人数 5
游戏时间 10minutes
游戏配件 8张身份牌

五人局：2狼人+1预言家+1强盗+1酒鬼+1捣蛋鬼+1失眠者+1爪牙

## 游戏流程

1.setup 游戏设置阶段
把这8张身份正面朝上放在桌上，让每个人知道有哪些身份
洗混这8张身份牌，面朝下发给每位玩家1张身份牌，其余3张放在桌子中间
每位玩家看一眼自己的身份牌，面朝下放在自己面前
除强盗可不执行技能外，其他有技能人物必须执行。

2.night 夜晚阶段
由上帝依次叫出各个身份，被叫到的玩家
睁开眼睛并执行他们的技能。

3.day 白天阶段
各玩家进入精(mao)彩(xian)的推理讨论环节，经过紧张刺激的几分钟讨论后，所有人同
时投票，把手指向你要投票的人。官方时间：五分钟，白天阶段可以相互讨论，争辩。
获得票数（并列）最多的玩家死了，死人都亮开身份牌。在极罕见情况下，每个人都获得
了恰好1票，那么无人死去。

4.game end 游戏结束阶段
所有人亮开身份牌
如果至少一只狼人死了（即使有非狼人死了），那么村民党获胜。
如果存在狼人并且狼人都活着，那么狼人党获胜。
如果没有人是狼人，并且大家都活着，那么村民党获胜。
如果没有人是狼人，并且至少一人死了，那么共同失败。
注：游戏过程中，玩家身份可能会因各种技能而改变，判断胜利条件时依据最终身份而定
。白天时，所有人不得察看自己的身份牌。

## 各身份技能介绍（依据主持人叫的顺序）

狼人Werewolf
夜晚时，可以知道同伴是谁，如果是唯一一只独狼，他可以查看桌子中央3张牌中的一张

爪牙Minion
夜晚时，可以知道哪些人是狼人。如果他死了，但没有狼人死去，狼人和爪牙共同胜利。
如果没有狼人，只要其他任何一人死去，爪牙胜利。

预言家Seer
夜晚时，可以查看另一位玩家的身份牌或者桌子中央区域3张身份牌中的2张。

强盗Robber
夜晚时，可以与另一位玩家交换身份牌，然后查看你的新身份牌。不是必须换牌。

捣蛋鬼Troublemaker
夜晚时，可以交换两位其他玩家的身份牌。

酒鬼Drunk
夜晚时，必须将自己的身份牌与桌子中央区域3张身份牌中的1张交换，并且不能察看新的
身份牌。

失眠者Insomniac
夜晚时，可以重新察看自己的身份牌。

注：狼人和爪牙是狼人党，其余人都是村民党。



## 上帝（主持人）在黑夜时应该讲的话：
天黑了，所有人闭眼。
1.狼人，请睁眼，互相认识一下，如果你是独狼，你可以查看中央区域中的一张牌……狼人，请闭眼。
2.爪牙，请睁眼，狼人请竖起大拇指让爪牙找到你……狼人，放下大拇指，爪牙，请闭眼。
3.预言家，请睁眼，你可以查看一位玩家的身份牌，或者选择查看中央区域中的两张牌……预言家，请闭眼。
4.强盗，请睁眼，你可以与另一位玩家交换身份牌，然后查看你的新身份牌……强盗，请闭眼。
5.捣蛋鬼，请睁眼，你可以交换两位其他玩家的身份牌……捣蛋鬼，请闭眼。
6.酒鬼，请睁眼，请你将自己的身份牌与桌子中央区域3张身份牌中的1张交换，并且不能察看新的身份牌……酒鬼，请闭眼。
7.失眠者，请睁眼，你可以重新察看自己的身份牌……失眠者，请闭眼。

天亮了，所有人睁眼！
========================
注意这个游戏中不会真的杀人，也没有平民，只是玩家的身份会发生变化。
========================
""".strip()


class GameMaster:
    def __init__(self, num_players, verbose=True, include_people=True):
        self.num_players = num_players
        self.players = [PlayerBot(i) for i in range(self.num_players)]
        if include_people:
            _id = random.randint(0, len(self.players) - 1)
            self.players[_id] = PersonPlayer(_id)
            verbose = False
        self.roles = []
        self.center_cards = []
        self.game_history = []
        self.verbose = verbose

    def log(self, msg):
        if self.verbose:
            print(msg)
        self.game_history.append(msg)

    def broadcast(self, msg):
        for player in self.players:
            player.receive_message("上帝", msg)

    def setup_game(self):
        # 根据玩家数量选择角色并洗牌
        self.roles = self.select_roles(self.num_players)
        random.shuffle(self.roles)

        # 发牌
        for i, player in enumerate(self.players):
            player.set_role(self.roles[i])
            player.match_players(self.players)

        # 设置中央牌堆
        self.center_cards = self.roles[-3:]
        self.log(GAME_PROMPT)
        self.log(f"游戏开始，玩家数量：{self.num_players}，角色：{self.roles}")
        for player in self.players:
            self.log(f"{player.player_name}的初始身份是{player.start_role}。")

    def select_roles(self, num_players):
        assert num_players == 5
        # 根据玩家数量选择角色
        roles =  ['狼人'] * 2 + ['预言家', '强盗', '捣蛋鬼', '酒鬼', '失眠者', '爪牙'] * 1

        return roles 

    def play_game(self):
        self.log('========================')
        self.night_phase()
        self.log('========================')
        self.day_phase()
        self.log('========================')
        self.game_end()

    def night_phase(self):
        # 按照角色执行夜晚阶段的动作
        for role in ['狼人', '爪牙', '预言家', '强盗', '捣蛋鬼', '酒鬼', '失眠者']:
            for player in self.players:
                if player.start_role == role:
                    player.perform_night_action(self.players, self.center_cards)
                    self.log(f'{player.player_name}的初始身份是{player.start_role}，夜晚他得到的信息是"{player.night_action}"。')

        self.log('夜晚结束')
        for player in self.players:
            self.log(f'{player.player_name}的初始身份是{player.start_role}，现在的身份是{player.role}。')

    def day_phase(self):
        # 讨论阶段
        total_rounds = TOTAL_ROUNDS
        for player in self.players:
            player.receive_message(f'上帝', f'天亮了，所有人睁眼！请大家开始讨论。讨论时间为{total_rounds}轮。')
        self.log(f'上帝：天亮了，所有人睁眼！请大家开始讨论。讨论时间为{total_rounds}轮。')
        for _ in range(total_rounds):
            for player in self.players:
                player.receive_message(f'上帝', f'请{player.player_name}发言。记住你晚上的信息是"{player.night_action}"。根据别人的信息，如果你觉得你是狼人，不要轻易说自己是狼人，请想办法归票到别人身上。如果你觉得你不是狼人，请想办法归票到狼人身上。')
                message = player.day_phase_discussion()
                for other_player in player.other_players:
                    other_player.receive_message(player.player_name, message)
                self.log(f'{player.player_name}：{message}')

    def game_end(self):
        # 游戏结束时的统计和判断胜负
        vote_result = { player.player_name: 0 for player in self.players }
        all_player_names = ",".join([player.player_name for player in self.players])
        self.log(f'上帝：请投票。请输出你要投票的玩家名字（{all_player_names}）或者输出"弃票"。')
        player_votes = {}
        for player in self.players:
            player.receive_message(f'上帝', f'请投票。请输出你要投票的玩家名字（{all_player_names}）或者输出"弃票"。')
            vote = player.day_phase_vote()
            self.log(f'{player.player_name}：{vote}')
            player_votes[player.player_name] = vote
            if vote == '弃票':
                continue
            vote_result[vote] += 1
        for player in self.players:
            self.broadcast(f'{player.player_name} 投票结果：{player_votes[player.player_name]}')
        self.log(f'上帝：投票结果为{vote_result}')
        self.broadcast(f'投票结果为{vote_result}')
        max_vote = max(vote_result.values())
        max_vote_players = [player_name for player_name, vote in vote_result.items() if vote == max_vote]
        if len(max_vote_players) == 1:
            _dead_player = [player for player in self.players if player.player_name == max_vote_players[0]][0]
            _dead_role = _dead_player.role
            self.log(f'上帝：{max_vote_players[0]}被投票出局。他的身份是{_dead_role}。')
            self.broadcast(f'{max_vote_players[0]}被投票出局。他的身份是{_dead_role}。')
            if _dead_role in ['狼人']:
                self.log(f'上帝：好人阵营胜利。')
                self.broadcast(f'好人阵营胜利。')
            else:
                self.log(f'上帝：狼人阵营胜利。')
                self.broadcast(f'狼人阵营胜利。')
        else:
            self.log(f'上帝：平票，无人出局。')
            self.broadcast(f'平票，无人出局。')
            if any([player.role == '狼人' for player in self.players]):
                self.log(f'上帝：狼人阵营胜利。')
                self.broadcast(f'狼人阵营胜利。')
            else:
                self.log(f'上帝：好人阵营胜利。')
                self.broadcast(f'好人阵营胜利。')

        self.broadcast('\n\n' + '\n'.join(self.game_history) + '\n\n')


class PlayerBot:
    def __init__(self, player_id):
        self.player_id = player_id
        self.player_name = BOT_NAMES[player_id]
        self.start_role = None
        self.role = None
        self.char_prompt = "为了推进游戏，在游戏前期你会大量的编造谎话，挑起矛盾，你会说很多的话，积极得指认别的人身份即使是瞎猜的。如果你是有信息的人应该主动将信息分享出来，找寻逻辑漏洞来发现线索。注意如果你是狼人请不要轻易说自己是狼人，可以编造别的身份"
        self.night_action = None
        self.other_players = []

        self.chat_history = [
            {'role': "system", "content": self.context}
        ]

    def set_role(self, role):
        self.start_role = role
        self.role = role

    def match_players(self, players):
        self.other_players = []
        for player in players:
            if player.player_id != self.player_id:
                self.other_players.append(player)

    @property
    def context(self):
        return f'{GAME_PROMPT}\n你的名字是 {self.player_name}. 你的编号是 {self.player_id}. 和你一起游戏的还有 {len(self.other_players)} 位玩家，他们是 {", ".join([player.player_name for player in self.other_players])}. \n你开始的角色是 {self.start_role}. \n在晚上你干了, \n{self.night_action}.\n白天时你将收到别的玩家的讨论如"玩家名：发言"。轮到你发言的时候不需要带你的名字，请直接发言。你的个人特质是{self.char_prompt}\n'

    def receive_message(self, player_name, message):
        self.chat_history.append({
            'role': 'user',
            'content': f"{player_name}: {message}"
        })
    
    def day_phase_discussion(self):
        completion = openai.ChatCompletion.create(
            model=OPENAI_MODEL,
            messages=self.chat_history,
        )
        chatbot_resposne = completion.choices[0]['message']['content']
        if chatbot_resposne.strip().startswith(self.player_name):
            chatbot_resposne = chatbot_resposne[len(self.player_name):]
            chatbot_resposne = chatbot_resposne.strip()
            if chatbot_resposne.startswith(':'):
                chatbot_resposne = chatbot_resposne[1:].strip()
        self.chat_history.append({
            'role': 'assistant',
            'content': chatbot_resposne
        })
        return chatbot_resposne
    
    def day_phase_vote(self):
        msg = self.day_phase_discussion()
        vote = msg
        for player in self.other_players:
            if player.player_name.lower() in vote.lower():
                vote = player.player_name
                break
        if '弃票' in vote or '不投' in vote or '不选' in vote or '不投票' in vote or '弃权' in vote or vote.strip() == '':
            vote = '弃票'
        if not (vote in [player.player_name for player in self.other_players] or vote == self.player_name or vote == '弃票'):
            print(f'玩家{self.player_name}的投票{vote}不合法 (msg: {msg}) 默认弃票')
            vote = '弃票'
        return vote

    def perform_night_action(self, players, center_cards):
        # 根据角色执行夜晚的动作，这里仅实现部分角色，其他角色可以类似实现
        if self.start_role == '狼人':
            self.werewolf_action(players, center_cards)
        elif self.start_role == '爪牙':
            self.minion_action(players)
        elif self.start_role == '预言家':
            self.seer_action(players, center_cards)
        elif self.start_role == '强盗':
            self.robber_action(players)
        elif self.start_role == '捣蛋鬼':
            self.troublemaker_action(players)
        elif self.start_role == '酒鬼':
            self.drunk_action(center_cards)
        elif self.start_role == '失眠者':
            self.insomniac_action()

    def werewolf_action(self, players, center_cards, card_id=None):
        # 狼人查看其他狼人
        other_werewolves = [player for player in players if player.role == '狼人' and player.player_id != self.player_id]
        if other_werewolves:
            self.night_action = f'狼人请睁眼，你的同伴是 {other_werewolves[0].player_name}.'
        else:
            self.night_action = '狼人请睁眼，你是唯一的狼人. 请查看中央区域的一张牌，可以从左中右中选择一张.'
            if card_id is None:
                _card_id = random.randint(0, 2)
            else:
                _card_id = card_id
            _card_pos = ['左', '中', '右'][_card_id]
            self.night_action += f' 你查看了中央区域的第 {_card_id + 1} 张牌 （{_card_pos}）. 你看到的是 {center_cards[_card_id]}.'

    def minion_action(self, players):
        # 爪牙查看狼人
        werewolves = [player for player in players if player.role == '狼人']
        if len(werewolves) == 1:
            self.night_action = f'爪牙请睁眼，你的同伴是 {werewolves[0].player_name}.'
        elif len(werewolves) == 2:
            self.night_action = f'爪牙请睁眼，你的同伴是 {werewolves[0].player_name} 和 {werewolves[1].player_name}.'
        else:
            self.night_action = '爪牙请睁眼，场面上没有狼人.'

    def seer_action(self, players, center_cards, choice=None, player_id=None, card_id_1=None, card_id_2=None):
        # 预言家查看一位玩家的身份牌或中央区域的两张牌
        if choice is None:
            _choice = random.randint(0, 1)
        else:
            _choice = choice
        if _choice == 0:
            # 查看一位玩家的身份牌
            if player_id is None:
                _player_id = random.randint(0, len(players) - 1)
                while players[_player_id].player_id == self.player_id:
                    _player_id = random.randint(0, len(players) - 1)
            else:
                _player_id = player_id
            self.night_action = f'预言家请睁眼，你查看了 {players[_player_id].player_name} 的身份牌，他是 {players[_player_id].role}.'
        else:
            # 查看中央区域的两张牌
            if card_id_1 is None:
                _card_id_1 = random.randint(0, 2)
            else:
                _card_id_1 = card_id_1
            if card_id_2 is None:
                _card_id_2 = random.randint(0, 2)
                while _card_id_2 == _card_id_1:
                    _card_id_2 = random.randint(0, 2)
            else:
                _card_id_2 = card_id_2
            _card_pos_1 = ['左', '中', '右'][_card_id_1]
            _card_pos_2 = ['左', '中', '右'][_card_id_2]
            self.night_action = f'预言家请睁眼，你查看了中央区域的第 {_card_id_1 + 1} 张牌 （{_card_pos_1}）和第 {_card_id_2 + 1} 张牌 （{_card_pos_2}）. 你看到的是 {_card_pos_1} 是 {center_cards[_card_id_1]}, {_card_pos_2} 是 {center_cards[_card_id_2]}.'

    def robber_action(self, players, choice=None, player_id=None):
        # 强盗与另一位玩家交换身份牌
        if choice is None:
            _choice = random.randint(0, 1)
        else:
            _choice = choice
        if _choice == 0:
            # 不交换
            self.night_action = '强盗请睁眼，你没有交换身份牌.'
        else:
            # 交换
            if player_id is not None:
                _player_id = player_id
            else:
                _player_id = random.randint(0, len(players) - 1)
                while players[_player_id].player_id == self.player_id:
                    _player_id = random.randint(0, len(players) - 1)
            self.night_action = f'强盗请睁眼，你交换了 {players[_player_id].player_name} 的身份牌，他是 {players[_player_id].role}.现在你是 {players[_player_id].role}， {players[_player_id].player_name} 是 {self.role}.'
            players[_player_id].role, self.role = self.role, players[_player_id].role

    def troublemaker_action(self, players, player_id_1=None, player_id_2=None):
        # 捣蛋鬼交换两位其他玩家的身份牌
        if player_id_1 is not None and player_id_2 is not None:
            _player_id_1 = player_id_1
            _player_id_2 = player_id_2
            assert _player_id_1 != _player_id_2, '捣蛋鬼不能交换同一位玩家的身份牌.'
        else:
            _player_id_1 = random.randint(0, len(players) - 1)
            while players[_player_id_1].player_id == self.player_id:
                _player_id_1 = random.randint(0, len(players) - 1)
            _player_id_2 = random.randint(0, len(players) - 1)
            while players[_player_id_2].player_id == self.player_id or players[_player_id_2].player_id == players[_player_id_1].player_id:
                _player_id_2 = random.randint(0, len(players) - 1)
        self.night_action = f'捣蛋鬼请睁眼，你交换了 {players[_player_id_1].player_name} 和 {players[_player_id_2].player_name} 的身份牌.'
        players[_player_id_1].role, players[_player_id_2].role = players[_player_id_2].role, players[_player_id_1].role

    def drunk_action(self, center_cards, card_id=None):
        # 酒鬼将自己的身份牌与中央区域的一张牌交换
        if card_id is not None:
            _card_id = card_id
            assert _card_id in [0, 1, 2]
        else:
            _card_id = random.randint(0, 2)
        _card_pos = ['左', '中', '右'][_card_id]
        self.night_action = f'酒鬼请睁眼，你交换了自己的身份牌和中央区域的第 {_card_id + 1} 张牌 （{_card_pos}）. '
        self.role, center_cards[_card_id] = center_cards[_card_id], self.role

    def insomniac_action(self):
        # 失眠者查看自己的身份牌
        self.night_action = f'失眠者请睁眼，你现在是 {self.role}.'

class PersonPlayer(PlayerBot):
    def __init__(self, player_id):
        super().__init__(player_id)
        self.log(f"玩家 {self.player_name} 加入游戏.")
        self.log(f"你是第 {self.player_id} 位玩家.")

    def log(self, msg):
        print(msg)

    def set_role(self, role):
        self.log(f"你的身份是 {role}.")
        return super().set_role(role)
    
    def match_players(self, players):
        self.log(f"场上有 {len(players)} 位玩家.")
        for player in players:
            self.log(f"玩家 {player.player_id}: {player.player_name}")
        super().match_players(players)

    def receive_message(self, player_name, message):
        self.log(f"玩家 {player_name} 说: {message}")
        super().receive_message(player_name, message)

    def day_phase_discussion(self):
        resposne = input("请输入你的发言: ")
        return resposne
    
    def day_phase_vote(self):
        resposne = input("请输入你的投票目标: ")
        return resposne
    
    def perform_night_action(self, players, center_cards):
        self.log("轮到你行动了.")
        super().perform_night_action(players, center_cards)

    def werewolf_action(self, players, center_cards):
        self.log("你是狼人，你可以看到其他狼人的身份.")
        for player in players:
            if player.role == '狼人' and player.player_id != self.player_id:
                self.log(f"玩家 {player.player_id}: {player.player_name} 是狼人.")
                self.night_action = f'狼人请睁眼，你的同伴是 {player.player_name}.'
        
        if len([player for player in players if player.role == '狼人' and player.player_id != self.player_id]) == 0:
            self.log("你是唯一的狼人. 请查看中央区域的一张牌，可以从左中右中选择一张.")
            self.night_action = '狼人请睁眼，你是唯一的狼人. 请查看中央区域的一张牌，可以从左中右中选择一张.'
            while True:
                _card_id = input("请输入你要查看的牌的编号: ")
                try:
                    _card_id = int(_card_id)
                    assert _card_id in [0, 1, 2]
                    break
                except:
                    self.log("请输入正确的编号.")
            _card_pos = ['左', '中', '右'][_card_id]
            self.log(f"你查看了中央区域的第 {_card_id + 1} 张牌 （{_card_pos}）. ")
            self.night_action = f'狼人请睁眼，你查看了中央区域的第 {_card_id + 1} 张牌 （{_card_pos}）. '
            self.log(f"第 {_card_id + 1} 张牌是 {center_cards[_card_id]}.")
            self.night_action = f'狼人请睁眼，第 {_card_id + 1} 张牌是 {center_cards[_card_id]}.'

    def minion_action(self, players):
        super().minion_action(players)
        self.log(self.night_action)

    def seer_action(self, players, center_cards):
        self.log("你是预言家，你可以查看一位玩家或者两张中央区域的牌.")
        while True:
            _choice = input("请输入你的选择（0:玩家/1:中央区域）: ")
            try:
                _choice = int(_choice)
                assert _choice in [0, 1]
                break
            except:
                self.log("请输入正确的选择.")
        if _choice == 0:
            while True:
                _player_id = input("请输入你要查看的玩家的编号: ")
                try:
                    _player_id = int(_player_id)
                    assert _player_id in range(len(players)) and _player_id != self.player_id
                    break
                except:
                    self.log("请输入正确的编号.")
            self.log(f"玩家 {_player_id}: {players[_player_id].player_name} 的身份是 {players[_player_id].role}.")
            self.night_action = f'预言家请睁眼，玩家 {_player_id}: {players[_player_id].player_name} 的身份是 {players[_player_id].role}.'
        else:
            while True:
                _card_id_1 = input("请输入你要查看的第一张牌的编号: ")
                try:
                    _card_id_1 = int(_card_id_1)
                    assert _card_id_1 in [0, 1, 2]
                    break
                except:
                    self.log("请输入正确的编号.")
            _card_pos_1 = ['左', '中', '右'][_card_id_1]
            self.log(f"你查看了中央区域的第 {_card_id_1 + 1} 张牌 （{_card_pos_1}）. ")
            self.log(f"第 {_card_id_1 + 1} 张牌是 {center_cards[_card_id_1]}.")
            
            while True:
                _card_id_2 = input("请输入你要查看的第二张牌的编号: ")
                try:
                    _card_id_2 = int(_card_id_2)
                    assert _card_id_2 in [0, 1, 2] and _card_id_2 != _card_id_1
                    break
                except:
                    self.log("请输入正确的编号.")
            _card_pos_2 = ['左', '中', '右'][_card_id_2]
            self.log(f"你查看了中央区域的第 {_card_id_2 + 1} 张牌 （{_card_pos_2}）. ")
            self.log(f"第 {_card_id_2 + 1} 张牌是 {center_cards[_card_id_2]}.")

            self.night_action = f'预言家请睁眼，你查看了中央区域的第 {_card_id_1 + 1} 张牌是 {center_cards[_card_id_1]}, 第 {_card_id_2 + 1} 张牌是 {center_cards[_card_id_2]}.'

    def robber_action(self, players):
        self.log("你是强盗，你可以查看一位玩家的身份，并且和他交换身份. 你也可以选择不交换.")
        while True:
            _choice = input("请输入你的选择（0:不交换/1:交换）: ")
            try:
                _choice = int(_choice)
                assert _choice in [0, 1]
                break
            except:
                self.log("请输入正确的选择.")
        if _choice == 0:
            self.log("你选择了不交换.")
            self.night_action = f'强盗请睁眼，你选择了不交换.'
        else:
            while True:
                _player_id = input("请输入你要交换的玩家的编号: ")
                try:
                    _player_id = int(_player_id)
                    assert _player_id in range(len(players)) and _player_id != self.player_id
                    break
                except:
                    self.log("请输入正确的编号.")
            self.log(f"玩家 {_player_id}: {players[_player_id].player_name} 的身份是 {players[_player_id].role}.")
            self.log(f"你交换了 {players[_player_id].player_name} 的身份牌，他是 {players[_player_id].role}.现在你是 {players[_player_id].role}， {players[_player_id].player_name} 是 {self.role}.")
            self.night_action = f'强盗请睁眼，你交换了 {players[_player_id].player_name} 的身份牌，他是 {players[_player_id].role}.现在你是 {players[_player_id].role}， {players[_player_id].player_name} 是 {self.role}.'
            players[_player_id].role, self.role = self.role, players[_player_id].role

    def troublemaker_action(self, players):
        self.log("你是捣蛋鬼，你可以选择交换两位其他玩家的身份牌.")
        while True:
            _player_id_1 = input("请输入你要交换的第一位玩家的编号: ")
            try:
                _player_id_1 = int(_player_id_1)
                assert _player_id_1 in range(len(players)) and _player_id_1 != self.player_id
                break
            except:
                self.log("请输入正确的编号.")
        while True:
            _player_id_2 = input("请输入你要交换的第二位玩家的编号: ")
            try:
                _player_id_2 = int(_player_id_2)
                assert _player_id_2 in range(len(players)) and _player_id_2 != self.player_id and _player_id_2 != _player_id_1
                break
            except:
                self.log("请输入正确的编号.")
        super().troublemaker_action(players, player_id_1=_player_id_1, player_id_2=_player_id_2)
        self.log(f"你交换了玩家 {_player_id_1} 和 {_player_id_2} 的身份牌.")

    def drunk_action(self, center_cards):
        self.log("你是酒鬼，你可以选择交换自己的身份牌和中央区域的一张牌.")
        while True:
            _card_id = input("请输入你要交换的牌的编号（0, 1, 2）: ")
            try:
                _card_id = int(_card_id)
                assert _card_id in [0, 1, 2]
                break
            except:
                self.log("请输入正确的编号.")
        super().drunk_action(center_cards, card_id=_card_id)
        self.log(f"你交换了自己的身份牌和中央区域的第 {_card_id + 1} 张牌.")

    def insomniac_action(self):
        super().insomniac_action()
        self.log(self.night_action)

if __name__ == '__main__':
    gm = GameMaster(5, include_people=INCLUDE_PEOPLE)
    gm.setup_game()
    gm.play_game()
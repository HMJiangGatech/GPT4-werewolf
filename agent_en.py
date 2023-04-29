import random
import openai
import os
from colorama import Fore, Style

BOT_NAMES = [
    'Alice', 'Bob', 'Charlie', 'David', 'Eve', 'Fred', 'Ginny', 'Harriet', 'Ileana', 'Joseph',
]
TOTAL_ROUNDS = 3
INCLUDE_PEOPLE = True
# OPENAI_MODEL = "gpt-4"
OPENAI_MODEL = "gpt-3.5-turbo"

OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
if not OPENAI_API_KEY:
    # read from file
    with open('OPENAI_API_KEY', 'r') as f:
        OPENAI_API_KEY = f.read().strip()

openai.api_key = OPENAI_API_KEY

GAME_PROMPT = """
# One Night Werewolf Rules

Number of players: 5
Game duration: 10 minutes
Game components: 8 role cards

Five-player setup: 2 werewolves + 1 seer + 1 robber + 1 drunk + 1 troublemaker + 1 insomniac + 1 minion

## Game Flow

1. Setup phase
Place the 8 role cards face-up on the table, so that everyone knows which roles are available.
Shuffle the 8 role cards and deal 1 face-down role card to each player, placing the remaining 3 cards face-down in the center of the table.
Each player takes a look at their own role card and places it face-down in front of them.
Except for the robber, all other characters with abilities must use their abilities.

2. Night phase
The moderator (God) calls out each role one by one, and the players who are called open their eyes and perform their abilities.

3. Day phase
Players engage in a lively and intense discussion, trying to deduce each other's roles. After a few minutes of discussion, everyone votes simultaneously, pointing a finger at the person they want to vote for. Official time: five minutes. Players can discuss and argue during the day phase.
The player(s) with the most votes (including ties) die and reveal their role cards. In the extremely rare case where everyone receives exactly one vote, no one dies.

4. Game end
Everyone reveals their role cards.
If at least one werewolf dies (even if non-werewolf players die as well), the villagers win.
If werewolves are present and all of them are alive, the werewolf faction wins.
If no one is a werewolf and everyone is alive, the villagers win.
If no one is a werewolf and at least one player dies, everyone loses.
Note: During the game, players' roles may change due to various abilities. Determine the winning condition based on the final roles. During the day phase, players may not check their own role cards.

## Role Abilities Introduction (in the order the moderator calls)

Werewolf
During the night, werewolves can know who their partner is. If they are the only werewolf, they can look at one of the three cards in the center of the table.

Minion
During the night, the minion can know who the werewolves are. If the minion dies but no werewolves die, the werewolves and minion win together. If there are no werewolves and any other player dies, the minion wins.

Seer
During the night, the seer can check another player's role card or look at two of the three cards in the center area.

Robber
During the night, the robber can exchange role cards with another player and then check their new role card. Exchanging cards is not mandatory.

Troublemaker
During the night, the troublemaker can swap the role cards of two other players.

Drunk
During the night, the drunk must exchange their role card with one of the three cards in the center area and cannot check their new role card.

Insomniac
During the night, the insomniac can check their own role card again.

Note: Werewolves and the minion belong to the werewolf faction, while the others belong to the villager faction.

## What the moderator (God) should say during the night phase:

1. Night falls, everyone closes their eyes.

2. Werewolves, please open your eyes and recognize each other. If you are the only werewolf, you may look at one of the cards in the center area... Werewolves, please close your eyes.
Minion, please open your eyes. Werewolves, pleaseraise your thumbs so the minion can find you... Werewolves, lower your thumbs. Minion, please close your eyes.

3. Seer, please open your eyes. You may look at one player's role card or choose to look at two cards in the center area... Seer, please close your eyes.

4. Robber, please open your eyes. You may exchange role cards with another player and then look at your new role card... Robber, please close your eyes.

5. Troublemaker, please open your eyes. You may swap the role cards of two other players... Troublemaker, please close your eyes.

6. Drunk, please open your eyes. You must exchange your role card with one of the 3 cards in the center area and you cannot look at your new role card... Drunk, please close your eyes.

7. Insomniac, please open your eyes. You may check your own role card again... Insomniac, please close your eyes.

8. Day breaks, everyone opens their eyes!

Note that in this game, no one actually gets killed, and there are no plain villagers. Players' roles will change throughout the game.

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
            player.receive_message("God", msg)

    def setup_game(self):
        # Select roles and shuffle based on the number of players
        self.roles = self.select_roles(self.num_players)
        random.shuffle(self.roles)

        # Deal cards
        for i, player in enumerate(self.players):
            player.set_role(self.roles[i])
            player.match_players(self.players)

        # Set the center cards
        self.center_cards = self.roles[-3:]
        self.log(GAME_PROMPT)
        self.log(f"The game begins with {self.num_players} players and roles: {self.roles}")
        for player in self.players:
            self.log(f"{player.player_name} starts as {player.start_role}.")

    def select_roles(self, num_players):
        assert num_players == 5
        # Select roles based on the number of players
        roles = ['werewolf'] * 2 + ['seer', 'robber', 'troublemaker', 'drunk', 'insomniac', 'minion'] * 1

        return roles

    def play_game(self):
        self.log('========================')
        self.night_phase()
        self.log('========================')
        self.day_phase()
        self.log('========================')
        self.game_end()

    def night_phase(self):
        # Perform night actions for each role
        for role in ['werewolf', 'minion', 'seer', 'robber', 'troublemaker', 'drunk', 'insomniac']:
            for player in self.players:
                if player.start_role == role:
                    player.perform_night_action(self.players, self.center_cards)
                    self.log(f"{player.player_name}'s initial role is {player.start_role}, and they received the following information at night: '{player.night_action}'.")

        self.log("Night phase ends.")
        # Update each player's role after night actions are performed
        for player in self.players:
            self.log(f"{player.player_name}'s initial role is {player.start_role}, and their current role is {player.role}.")

    def day_phase(self):
        # Discussion phase
        total_rounds = TOTAL_ROUNDS
        for player in self.players:
            player.receive_message("God", f"It's morning and everyone can open their eyes! Let's start discussing. We have {total_rounds} rounds to discuss.")
        self.log(f"God: It's morning and everyone can open their eyes! Let's start discussing. We have {total_rounds} rounds to discuss.")
        for _ in range(total_rounds):
            for player in self.players:
                player.receive_message("God", f"{player.player_name}, it's your turn to speak. Remember the information you received at night: '{player.night_action}' (only you know). If you think you're a werewolf, try to shift suspicion onto someone else. If you think you're not a werewolf, try to shift suspicion onto the werewolves.")
                message = player.day_phase_discussion()
                # Send the player's message to the other players
                for other_player in player.other_players:
                    other_player.receive_message(player.player_name, message)
                self.log(f"{player.player_name}: {message}")

    def game_end(self):
        # Statistics and judgment of victory or defeat at the end of the game
        vote_result = {player.player_name: 0 for player in self.players}
        all_player_names = ",".join([player.player_name for player in self.players])
        self.log(f'God: Please vote. Enter the name of the player you want to vote for ({all_player_names}), or enter "skip".')
        player_votes = {}
        for player in self.players:
            player.receive_message(f'God', f'Please vote. Enter the name of the player you want to vote for ({all_player_names}), or enter "skip".')
            vote = player.day_phase_vote()
            self.log(f'{player.player_name}: {vote}')
            player_votes[player.player_name] = vote
            if vote == 'skip':
                continue
            vote_result[vote] += 1
        for player in self.players:
            self.broadcast(f'{player.player_name} vote result: {player_votes[player.player_name]}')
        self.log(f'God: The voting result is {vote_result}')
        self.broadcast(f'The voting result is {vote_result}')
        max_vote = max(vote_result.values())
        max_vote_players = [player_name for player_name, vote in vote_result.items() if vote == max_vote]
        if len(max_vote_players) == 1:
            _dead_player = [player for player in self.players if player.player_name == max_vote_players[0]][0]
            _dead_role = _dead_player.role
            self.log(f'God: {max_vote_players[0]} has been voted out. Their role is {_dead_role}.')
            self.broadcast(f'{max_vote_players[0]} has been voted out. Their role is {_dead_role}.')
            if _dead_role in ['werewolf']:
                self.log(f'God: Good team wins.')
                self.broadcast(f'Good team wins.')
            else:
                self.log(f'God: Werewolf team wins.')
                self.broadcast(f'Werewolf team wins.')
        else:
            self.log(f'God: Tie, no one is voted out.')
            self.broadcast(f'Tie, no one is voted out.')
            if any([player.role == 'werewolf' for player in self.players]):
                self.log(f'God: Werewolf team wins.')
                self.broadcast(f'Werewolf team wins.')
            else:
                self.log(f'God: Good team wins.')
                self.broadcast(f'Good team wins.')

        self.broadcast('\n\n' + '\n'.join(self.game_history) + '\n\n')

class PlayerBot:
    def __init__(self, player_id):
        self.player_id = player_id
        self.player_name = BOT_NAMES[player_id]
        self.start_role = None
        self.role = None
        self.char_prompt = "To advance the game, you will fabricate a lot of lies and stir up conflicts in the early stage of the game. You will say a lot, actively accuse other players of their roles even if it's a blind guess. If you have information, you should proactively share it and find logical loopholes to discover clues. Note that if you are a werewolf, please do not easily admit to being a werewolf, you can fabricate other roles."
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
        return f"{GAME_PROMPT}\nYour name is {self.player_name}. Your ID is {self.player_id}. You are playing with {len(self.other_players)} other players, they are {', '.join([player.player_name for player in self.other_players])}. \nYour starting role is {self.start_role}. \nAt night you did, \n{self.night_action}.\nDuring the day, you will receive discussions from other players like \"Player name: speech\". When it's your turn to speak, you don't need to include your name, just speak. Your personal trait is {self.char_prompt}\n"

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
        if 'skip' in vote or '不投' in vote or '不选' in vote or '不投票' in vote or '弃权' in vote or vote.strip() == '':
            vote = 'skip'
        if not (vote in [player.player_name for player in self.other_players] or vote == self.player_name or vote == 'skip'):
            print(f"Player {self.player_name}'s vote {vote} is invalid (msg: {msg}). Default to skip.")
            vote = 'skip'
        return vote

    def perform_night_action(self, players, center_cards):
        # Perform night actions based on roles, only a few roles are implemented here, other roles can be similarly implemented
        if self.start_role == 'werewolf':
            self.werewolf_action(players, center_cards)
        elif self.start_role == 'minion':
            self.minion_action(players)
        elif self.start_role == 'seer':
            self.seer_action(players, center_cards)
        elif self.start_role == 'robber':
            self.robber_action(players)
        elif self.start_role == 'troublemaker':
            self.troublemaker_action(players)
        elif self.start_role == 'drunk':
            self.drunk_action(center_cards)
        elif self.start_role == 'insomniac':
            self.insomniac_action()

    def werewolf_action(self, players, center_cards, card_id=None):
        # Werewolves see other werewolves
        other_werewolves = [player for player in players if player.role == 'werewolf' and player.player_id != self.player_id]
        if other_werewolves:
            self.night_action = f'Werewolves, open your eyes. Your fellow werewolf is {other_werewolves[0].player_name}.'
        else:
            self.night_action = 'Werewolves, open your eyes. You are the only werewolf. Please look at one of the cards in the center, you can choose left, middle, or right.'
            if card_id is None:
                _card_id = random.randint(0, 2)
            else:
                _card_id = card_id
            _card_pos = ['Left', 'Middle', 'Right'][_card_id]
            self.night_action += f' You looked at the {_card_id + 1} card in the center ({_card_pos}). You saw {center_cards[_card_id]}.'

    def minion_action(self, players):
        # Minion sees werewolves
        werewolves = [player for player in players if player.role == 'werewolf']
        if len(werewolves) == 1:
            self.night_action = f'Minion, open your eyes. Your fellow werewolf is {werewolves[0].player_name}.'
        elif len(werewolves) == 2:
            self.night_action = f'Minion, open your eyes. Your fellow werewolves are {werewolves[0].player_name} and {werewolves[1].player_name}.'
        else:
            self.night_action = 'Minion, open your eyes. There are no werewolves in the game.'

    def seer_action(self, players, center_cards, choice=None, player_id=None, card_id_1=None, card_id_2=None):
        # Seer sees either one player's card or two center cards
        if choice is None:
            _choice = random.randint(0, 1)
        else:
            _choice = choice
        if _choice == 0:
            # See one player's card
            if player_id is None:
                _player_id = random.randint(0, len(players) - 1)
                while players[_player_id].player_id == self.player_id:
                    _player_id = random.randint(0, len(players) - 1)
            else:
                _player_id = player_id
            self.night_action = f'Seer, open your eyes. You saw {players[_player_id].player_name}\'s card. They are {players[_player_id].role}.'
        else:
            # See two center cards
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
            _card_pos_1 = ['Left', 'Middle', 'Right'][_card_id_1]
            _card_pos_2 = ['Left', 'Middle', 'Right'][_card_id_2]
            self.night_action = f'Seer, open your eyes. You saw the {_card_id_1 + 1} card in the center ({_card_pos_1}) and the {_card_id_2 + 1} card in the center ({_card_pos_2}). You saw that {_card_pos_1} is {center_cards[_card_id_1]}, and {_card_pos_2} is {center_cards[_card_id_2]}.'

    def robber_action(self, players, choice=None, player_id=None):
        # Robber swaps their card with another player's card
        if choice is None:
            _choice = random.randint(0, 1)
        else:
            _choice = choice
        if _choice == 0:
            # Don't swap
            self.night_action = 'Robber, open your eyes. You didn\'t swap cards with another player.'
        else:
            # Swap
            if player_id is not None:
                _player_id = player_id
            else:
                _player_id = random.randint(0, len(players) - 1)
                while players[_player_id].player_id == self.player_id:
                    _player_id = random.randint(0, len(players) - 1)
            self.night_action = f'Rober, open your eyes. You swapped cards with {players[_player_id].player_name}. You are now {players[_player_id].role} and they are now {self.role}.'
            players[_player_id].role, self.role = self.role, players[_player_id].role

    def troublemaker_action(self, players, player_id_1=None, player_id_2=None):
        # troublemaker swaps two players' cards
        if player_id_1 is not None and player_id_2 is not None:
            _player_id_1 = player_id_1
            _player_id_2 = player_id_2
            assert _player_id_1 != _player_id_2, 'Troublemaker cannot swap the same player\'s card'
        else:
            _player_id_1 = random.randint(0, len(players) - 1)
            while players[_player_id_1].player_id == self.player_id:
                _player_id_1 = random.randint(0, len(players) - 1)
            _player_id_2 = random.randint(0, len(players) - 1)
            while players[_player_id_2].player_id == self.player_id or players[_player_id_2].player_id == players[_player_id_1].player_id:
                _player_id_2 = random.randint(0, len(players) - 1)
        self.night_action = f'Troublemaker, open your eyes. You swapped {players[_player_id_1].player_name}\'s card and {players[_player_id_2].player_name}\'s card.'
        players[_player_id_1].role, players[_player_id_2].role = players[_player_id_2].role, players[_player_id_1].role

    def drunk_action(self, center_cards, card_id=None):
        # drunk swaps their card with a card in the center
        if card_id is not None:
            _card_id = card_id
            assert _card_id in [0, 1, 2]
        else:
            _card_id = random.randint(0, 2)
        _card_pos = ['Left', 'Middle', 'Right'][_card_id]
        self.night_action = f'Drunk, open your eyes. You swapped your card with the {_card_id + 1} card in the center ({_card_pos}).'
        self.role, center_cards[_card_id] = center_cards[_card_id], self.role

    def insomniac_action(self):
        # insomniac checks their card
        self.night_action = f'Insomniac, open your eyes. You are now {self.role}.'

class PersonPlayer(PlayerBot):
    def __init__(self, player_id):
        super().__init__(player_id)
        self.log(f"Player {self.player_name} joined the game.")
        self.log(f"You are the {self.player_id}-th player.")

    def log(self, msg):
        print(msg)

    def set_role(self, role):
        self.log(f"Your role is {role}.")
        return super().set_role(role)
    
    def match_players(self, players):
        self.log(f"Ther are {len(players)} players in the game.")
        for player in players:
            self.log(f"Player {player.player_id}: {player.player_name}")
        super().match_players(players)

    def receive_message(self, player_name, message):
        self.log(f"{Fore.RED}Player {player_name} said:{Style.RESET_ALL} {message}")
        super().receive_message(player_name, message)

    def day_phase_discussion(self):
        resposne = input(Fore.BLUE + "Please input your discussion: ")
        return resposne
    
    def day_phase_vote(self):
        resposne = input(Fore.BLUE + "Please input your vote: ")
        return resposne
    
    def perform_night_action(self, players, center_cards):
        self.log("It's your turn to perform your night action.")
        super().perform_night_action(players, center_cards)

    def werewolf_action(self, players, center_cards):
        self.log("You are a werewolf. Please open your eyes and check your teammate.")
        for player in players:
            if player.role == 'werewolf' and player.player_id != self.player_id:
                self.log(f"Plyaer {player.player_id}: {player.player_name} is your teammate.")
                self.night_action = f'Werewolf, open your eyes. {player.player_name} is your teammate.'
        
        if len([player for player in players if player.role == 'werewolf' and player.player_id != self.player_id]) == 0:
            self.log("You are the only werewolf. Please check one of the cards in the center area, choose from the left, middle, or right.")
            self.night_action = 'Werewolf, please wake up. You are the only werewolf. Please check one of the cards in the center area, choose from the left, middle, or right.'
            while True:
                _card_id = input(Fore.BLUE + "Please enter the number of the card you want to check: ")
                try:
                    _card_id = int(_card_id)
                    assert _card_id in [0, 1, 2]
                    break
                except:
                    self.log("Please enter the correct number.")
            _card_pos = ['Left', 'Middle', 'Right'][_card_id]
            self.log(f"You checked the {_card_id + 1}-th card in the center area ({_card_pos}).")
            self.night_action = f'Werewolf, please wake up. You checked the {_card_id + 1}-th card in the center area ({_card_pos}).'
            self.log(f"The {_card_id + 1}-th card is {center_cards[_card_id]}.")
            self.night_action = f'Werewolf, please wake up. The {_card_id + 1}-th card is {center_cards[_card_id]}.'

    def minion_action(self, players):
        super().minion_action(players)
        self.log(self.night_action)

    def seer_action(self, players, center_cards):
        self.log("You are the seer, you can check one player or two cards in the center area.")
        while True:
            _choice = input(Fore.BLUE + "Please enter your choice (0: player / 1: center cards): ")
            try:
                _choice = int(_choice)
                assert _choice in [0, 1]
                break
            except:
                self.log("Please enter the correct choice.")
        if _choice == 0:
            while True:
                _player_id = input(Fore.BLUE + "Please enter the player number you want to check: ")
                try:
                    _player_id = int(_player_id)
                    assert _player_id in range(len(players)) and _player_id != self.player_id
                    break
                except:
                    self.log("Please enter the correct number.")
            self.log(f"The identity of player {_player_id}: {players[_player_id].player_name} is {players[_player_id].role}.")
            self.night_action = f'Seer, please wake up. The identity of player {_player_id}: {players[_player_id].player_name} is {players[_player_id].role}.'
        else:
            while True:
                _card_id_1 = input(Fore.BLUE + "Please enter the number of the first card you want to check: ")
                try:
                    _card_id_1 = int(_card_id_1)
                    assert _card_id_1 in [0, 1, 2]
                    break
                except:
                    self.log("Please enter the correct number.")
            _card_pos_1 = ['Left', 'Middle', 'Right'][_card_id_1]
            self.log(f"You checked the {_card_id_1 + 1}-th card in the center area ({_card_pos_1}). ")
            self.log(f"The {_card_id_1 + 1}-th card is {center_cards[_card_id_1]}.")
            
            while True:
                _card_id_2 = input(Fore.BLUE + "Please enter the number of the second card you want to check: ")
                try:
                    _card_id_2 = int(_card_id_2)
                    assert _card_id_2 in [0, 1, 2] and _card_id_2 != _card_id_1
                    break
                except:
                    self.log("Please enter the correct number.")
            _card_pos_2 = ['Left', 'Middle', 'Right'][_card_id_2]
            self.log(f"You checked the {_card_id_2 + 1}-th card in the center area ({_card_pos_2}). ")
            self.log(f"The {_card_id_2 + 1}-th card is {center_cards[_card_id_2]}.")

            self.night_action = f'Seer, please wake up. You checked the {_card_id_1 + 1}-th card in the center area: {center_cards[_card_id_1]}, and the {_card_id_2 + 1}-th card: {center_cards[_card_id_2]}.'

    def robber_action(self, players):
        self.log("You are the robber, you can check one player's identity and exchange with them. You can also choose not to exchange.")
        while True:
            _choice = input(Fore.BLUE + "Please enter your choice (0: do not exchange / 1: exchange): ")
            try:
                _choice = int(_choice)
                assert _choice in [0, 1]
                break
            except:
                self.log("Please enter the correct choice.")
        if _choice == 0:
            self.log("You chose not to exchange.")
            self.night_action = 'Robber, please wake up. You chose not to exchange.'
        else:
            while True:
                _player_id = input(Fore.BLUE + "Please enter the player number you want to exchange with: ")
                try:
                    _player_id = int(_player_id)
                    assert _player_id in range(len(players)) and _player_id != self.player_id
                    break
                except:
                    self.log("Please enter the correct number.")
            self.log(f"The identity of player {_player_id}: {players[_player_id].player_name} is {players[_player_id].role}.")
            self.log(f"You exchanged your identity card with {players[_player_id].player_name}, who is {players[_player_id].role}. Now you are {players[_player_id].role}, and {players[_player_id].player_name} is {self.role}.")
            self.night_action = f'Robber, please wake up. You exchanged your identity card with {players[_player_id].player_name}, who is {players[_player_id].role}. Now you are {players[_player_id].role}, and {players[_player_id].player_name} is {self.role}.'
            players[_player_id].role, self.role = self.role, players[_player_id].role

    def troublemaker_action(self, players):
        self.log("You are the troublemaker, you can choose to swap the identity cards of two other players.")
        while True:
            _player_id_1 = input(Fore.BLUE + "Please enter the number of the first player you want to swap: ")
            try:
                _player_id_1 = int(_player_id_1)
                assert _player_id_1 in range(len(players)) and _player_id_1 != self.player_id
                break
            except:
                self.log("Please enter the correct number.")
        while True:
            _player_id_2 = input(Fore.BLUE + "Please enter the number of the second player you want to swap: ")
            try:
                _player_id_2 = int(_player_id_2)
                assert _player_id_2 in range(len(players)) and _player_id_2 != self.player_id and _player_id_2 != _player_id_1
                break
            except:
                self.log("Please enter the correct number.")
        super().troublemaker_action(players, player_id_1=_player_id_1, player_id_2=_player_id_2)
        self.log(f"You swapped the identity cards of player {_player_id_1} and player {_player_id_2}.")

    def drunk_action(self, center_cards):
        self.log("You are the drunk, you can choose to swap your identity card with one of the center cards.")
        while True:
            _card_id = input(Fore.BLUE + "Please enter the number of the card you want to swap (0, 1, 2): ")
            try:
                _card_id = int(_card_id)
                assert _card_id in [0, 1, 2]
                break
            except:
                self.log("Please enter the correct number.")
        super().drunk_action(center_cards, card_id=_card_id)
        _card_pos = ['Left', 'Middle', 'Right'][_card_id]
        self.log(f"You swapped your identity card with the {_card_id + 1}th card ({_card_pos}) in the center.")

    def insomniac_action(self):
        super().insomniac_action()
        self.log(self.night_action)

if __name__ == '__main__':
    gm = GameMaster(5, include_people=INCLUDE_PEOPLE)
    gm.setup_game()
    gm.play_game()
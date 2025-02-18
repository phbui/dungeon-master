from .chat import Chat

class Game:
    def __init__(self):
        self.chat = Chat()
        self.players = []
        self.turn = 0

    def add_player(self, player):
        self.players.append({"turn_order": len(self.players), "player": player})

    def play_turn(self):
        player = self.players[self.turn]
        print(f"[DEBUG] Game: {player['player'].name}'s turn now.")

        name = player['player'].name
        message = player['player'].generate_message(
                               self.chat.history)

        self.chat.add_turn(name, 
                           message)

        self.turn += 1

        if self.turn == len(self.players):
            self.turn = 0

    def play_game(self, num_turns):
        if len(self.players) < 2:
            print('Not enough players!')
            return
        
        turn_counter = 0
        player_names = "".join(f" {p['player'].name}," for p in self.players)
        message = f"{player_names} all run into each other."
        self.chat.add_turn("Story So Far", message)

        while turn_counter < num_turns:
            self.play_turn()
            turn_counter += 1
        
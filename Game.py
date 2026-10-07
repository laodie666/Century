import json
import random
from util import ACQUIRE_CARD, REST, ACQUIRE_POINT, PLAY_CARD, BROWN, CARAVAN_LIMIT, CARDS, TRADER_CARDS, POINT_CARDS
from players import Player, HumanPlayer, NaivePlayer


class Engine:
    def __init__(self, Players: list[Player], Log_path: str = None):
        # Set up the game with list of Players 
        self.Players = Players
        self.Player_in_play = 0 # Index of player who's supposed to move
        self.game_ends = 0
        self.Turn = 0
        self.Log_file = open(Log_path, "w") if Log_path else None
        
        # Starting cubes, later seats get more cubes to make up for the turn order
        Starting_cubes = [[3,0,0,0], [4,0,0,0], [4,0,0,0], [3,1,0,0], [3,1,0,0]]
        for i, player in enumerate(self.Players):
            player.caravan = list(Starting_cubes[i])
        
        # Coins above the first and second point card, twice as many as there are players
        self.Gold_coins = len(self.Players) * 2
        self.Silver_coins = len(self.Players) * 2
        self.Silver_pos = 1 # Point card position the silver coins are sitting above
        
        self.Point_deck = list(POINT_CARDS)
        self.Trader_deck = list(TRADER_CARDS)

        self.Point_cards = []
        self.Trader_cards = []
        self.Stacked_cubes = [] # stack cubes onto cards to pick it up.

        # draw the initial cards
        for _ in range(5):
            self.draw(self.Trader_deck, self.Trader_cards)
            self.Stacked_cubes.append([0,0,0,0])
            
            self.draw(self.Point_deck, self.Point_cards)
            
        self.draw(self.Trader_deck, self.Trader_cards)
        self.Stacked_cubes.append([0,0,0,0])
        
        

    def draw(self, Deck: list, DestinationPile: list) -> None:
        # Draw a card from Deck into the corresponding list of the table 
        drawn_card = random.choice(Deck)
        Deck.remove(drawn_card)
        DestinationPile.append(drawn_card)
    
    def log(self, entry: dict) -> None:
        # Write one turn of the game to the log file, if there is one
        if self.Log_file:
            self.Log_file.write(json.dumps(entry) + "\n")
            self.Log_file.flush()
        
    def display(self) -> None:
        # Show the current table and the state of every player
        print("=" * 50)
        
        print("Trader cards:")
        for i, card_name in enumerate(self.Trader_cards):
            card = CARDS[card_name]
            if card["type"] == "exchange":
                detail = f"cost {card['cost']} gain {card['gain']}"
            elif card["type"] == "spice":
                detail = f"gain {card['gain']}"
            else:
                detail = f"steps {card['steps']}"
            print(f"  [{i}] {card_name}: {detail}, stacked {self.Stacked_cubes[i]}")
        
        print("Point cards:")
        for i, card_name in enumerate(self.Point_cards):
            card = CARDS[card_name]
            print(f"  [{i}] {card_name}: vp {card['vp']}, cost {card['cost']}")
        
        print(f"Coins: {self.Gold_coins} gold above card 0, {self.Silver_coins} silver above card {self.Silver_pos}")
        
        for i, player in enumerate(self.Players):
            print(f"Player {i}: score {player.score}, point cards {player.pcard_count}, gold {player.gold}, silver {player.silver}, caravan {player.caravan}")
            print(f"  hand {player.hand}")
            print(f"  discard {player.discard}")
        
        print(f"Player {self.Player_in_play}'s turn")
        print("=" * 50)
        
    def legal_move(self, player: Player, action: int, args: list) -> str | None:
        # Reason the move is illegal, or None if it is legal
        
        if not all(isinstance(arg, int) for arg in args):
            return "arguments have to be integers"
        if action not in (ACQUIRE_CARD, REST, ACQUIRE_POINT, PLAY_CARD):
            return "unknown action"
        
        # Acquire card
        if action == ACQUIRE_CARD:
            if len(args) < 1:
                return "card index missing"
            acquire_card_idx = args[0]
            if not 0 <= acquire_card_idx < len(self.Trader_cards):
                return "trader card index out of range"
            if len(args) - 1 != acquire_card_idx:
                return "one cube has to be placed on every card left of the acquired card"
            cubes = list(player.caravan)
            for cube_color in args[1:]:
                if not 0 <= cube_color < 4:
                    return "invalid cube color"
                if cubes[cube_color] <= 0:
                    return "not enough cubes to place"
                cubes[cube_color] -= 1
        
        # Rest
        if action == REST:
            pass
        
        # Score
        if action == ACQUIRE_POINT:
            if len(args) < 1:
                return "point card index missing"
            pt_card_idx = args[0]
            if not 0 <= pt_card_idx < len(self.Point_cards):
                return "point card index out of range"
            cost = CARDS[self.Point_cards[pt_card_idx]]["cost"]
            if any(x < y for x, y in zip(player.caravan, cost)):
                return "not enough cubes for the point card"
        
        # Play a card
        if action == PLAY_CARD:
            if len(args) < 1:
                return "card index missing"
            card_idx = args[0]
            if not 0 <= card_idx < len(player.hand):
                return "hand index out of range"
            card = CARDS[player.hand[card_idx]]
            
            if card["type"] == "spice" and len(args) != 1:
                return "spice cards take no extra arguments"
            
            if card["type"] == "exchange":
                if len(args) != 2:
                    return "exchange cards take the number of times to play"
                times = args[1]
                if times < 1:
                    return "times has to be at least 1"
                if any(x < y * times for x, y in zip(player.caravan, card["cost"])):
                    return "not enough cubes for the exchange"
            
            if card["type"] == "upgrade":
                if len(args) != 5:
                    return "upgrade cards take how many of each cube to upgrade"
                amounts = args[1:]
                if any(x < 0 for x in amounts):
                    return "upgrade amounts cannot be negative"
                if sum(amounts) > card["steps"]:
                    return "too many upgrades for the card"
                if amounts[BROWN] > 0:
                    return "brown cannot be upgraded"
                cubes = list(player.caravan)
                for color in range(BROWN):
                    if cubes[color] < amounts[color]:
                        return "not enough cubes to upgrade"
                    cubes[color] -= amounts[color]
                    cubes[color + 1] += amounts[color]
        
        return None
        
    def enforce_caravan_limit(self, player: Player, actor: int) -> list:
        # The caravan holds at most 10 cubes, returns the colors that were discarded
        excess = sum(player.caravan) - CARAVAN_LIMIT
        if excess <= 0:
            return []
        
        discards = player.get_discard(self, excess)
        
        # Fall back to the lowest cubes first if the discard is invalid
        valid = (isinstance(discards, list) and len(discards) == excess
                 and all(isinstance(c, int) and 0 <= c < 4 for c in discards))
        if valid:
            counts = [0, 0, 0, 0]
            for color in discards:
                counts[color] += 1
            valid = all(n <= have for n, have in zip(counts, player.caravan))
        
        if not valid:
            print(f"Player {actor} invalid discard, discarding the lowest cubes first")
            discards = []
            for color in range(4):
                discards.extend([color] * min(excess - len(discards), player.caravan[color]))
        
        for color in discards:
            player.caravan[color] -= 1
        
        return discards
        
    def step(self) -> int | None:
        # return winner id, else none
        
        if self.game_ends == 1 and self.Player_in_play == 0:
            winner = max(range(len(self.Players)), key = lambda p: self.Players[p].total_score())
            self.log({"turn": self.Turn, "winner": winner})
            if self.Log_file:
                self.Log_file.close()
                self.Log_file = None
            return winner
            
        
        player = self.Players[self.Player_in_play]
        actor = self.Player_in_play
        self.Turn += 1
        action, args = player.get_action(self)
        # There are a few actions a player can take, 
        
        # Illegal moves are skipped
        reason = self.legal_move(player, action, args)
        if reason is not None:
            print(f"Player {self.Player_in_play} illegal move: {reason}, turn skipped")
        
        # Acquire card
        if reason is None and action == ACQUIRE_CARD:
            # Place all the cubes first 
            acquire_card_idx = args[0]
            for i in range(acquire_card_idx):
                cube_color = args[i + 1]
                self.Stacked_cubes[i][cube_color] += 1
                player.caravan[cube_color] -= 1
            
            # Player pick up cubes stacked on the acquired card
            player.caravan = [x + y for x, y in zip(player.caravan, self.Stacked_cubes[acquire_card_idx])]
            self.Stacked_cubes.pop(acquire_card_idx)
            self.Stacked_cubes.append([0,0,0,0])
            
            # player add card to hand and draw a new card 
            player.hand.append(self.Trader_cards[acquire_card_idx])
            self.Trader_cards.pop(acquire_card_idx)
            self.draw(self.Trader_deck, self.Trader_cards)
            
            
        # Rest
        if reason is None and action == REST:
            player.hand.extend(player.discard)
            player.discard = []
        
        # Score
        if reason is None and action == ACQUIRE_POINT:
            pt_card_idx = args[0]
            pt_card_name = self.Point_cards[pt_card_idx]
            card = CARDS[pt_card_name]
            
            player.caravan = [x - y for x, y in zip(player.caravan, card["cost"])]
            
            # Take a coin from above the first or second point card
            if pt_card_idx == 0 and self.Gold_coins > 0:
                player.gold += 1
                self.Gold_coins -= 1
                # The silver coins move above the first card once the gold runs out
                if self.Gold_coins == 0:
                    self.Silver_pos = 0
            elif pt_card_idx == self.Silver_pos and self.Silver_coins > 0:
                player.silver += 1
                self.Silver_coins -= 1
            
            player.pcard_count += 1
            player.score += card["vp"]
            
            self.Point_cards.pop(pt_card_idx)
            self.draw(self.Point_deck, self.Point_cards)
            
            
        # Play a card
        if reason is None and action == PLAY_CARD:
            card_idx = args[0]
            card_name = player.hand[card_idx]
            card = CARDS[card_name]
            
            if card["type"] == "spice":
                player.caravan = [x + y for x, y in zip(player.caravan, card["gain"])]
            
            if card["type"] == "upgrade":
                for color in range(BROWN):
                    amount = args[color + 1]
                    player.caravan[color] -= amount
                    player.caravan[color + 1] += amount
                # To allow chained upgrade, so yellow to red then red to green, just check if anything is negative at the end. 
            
            if card["type"] == "exchange":
                times = args[1]
                player.caravan = [x - y * times for x, y in zip(player.caravan, card["cost"])]
                player.caravan = [x + y * times for x, y in zip(player.caravan, card["gain"])]
            
            player.discard.append(player.hand.pop(card_idx))
            
        # Caravan holds at most 10 cubes, the excess is discarded at the end of the turn
        discards = self.enforce_caravan_limit(player, actor)
        
        # Game ends when one player has 5 point cards
        if self.Players[self.Player_in_play].pcard_count == 5:
            self.game_ends = 1
        
        # Log the turn, the actor has not rotated yet
        self.log({
            "turn": self.Turn,
            "player": actor,
            "agent": type(player).__name__,
            "action": action,
            "args": args,
            "reason": reason,
            "totals": [p.total_score() for p in self.Players],
            "point_cards": [p.pcard_count for p in self.Players],
            "gold": [p.gold for p in self.Players],
            "silver": [p.silver for p in self.Players],
            "caravans": [list(p.caravan) for p in self.Players],
            "discards": discards,
        })
            
        # Else, rotate to next player
        self.Player_in_play = (self.Player_in_play + 1) % len(self.Players)


if __name__ == "__main__":
    Players = [HumanPlayer(), NaivePlayer(), NaivePlayer(), NaivePlayer()]
    game = Engine(Players)
    
    # Play until a player wins
    winner = None
    while winner is None:
        winner = game.step()
    
    print(f"Player {winner} wins with {game.Players[winner].total_score()} points")
            
            
        
         
        
    
    
    
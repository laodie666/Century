import json
from pathlib import Path
import random

ACQUIRE_CARD = 0
REST = 1
ACQUIRE_POINT = 2
PLAY_CARD = 3

YELLOW = 0
RED = 1
GREEN = 2 
BROWN = 3



PATH = Path(__file__).parent/"cards.json"
with open(PATH) as f:
    DATA = json.load(f) 

CARDS = DATA["cards"]
TRADER_CARDS = []
POINT_CARDS = []

for card in CARDS:
    if CARDS[card]["type"] == "point":
        POINT_CARDS.append(card)
    else:
        TRADER_CARDS.append(card)

class Player:
    def __init__(self):
        self.caravan = [0,0,0,0]
        # Caravan has 4 types of cubes, yellow, red, green, brown, in each index
        self.score = 0
        self.pcard_count = 0
        self.gold = 0
        self.silver = 0
        self.hand = ["sp_yy","upgrade_2"]
        self.discard = []

    def total_score(self) -> int:
        # Point cards, coins, and every cube better than yellow
        return self.score + self.gold * 3 + self.silver + sum(self.caravan[1:])

    def get_action(self, Game: 'Engine') -> tuple[int, list[int]]:
        # Tuple of action and the extra args potentially needed. 
        # action correspondes to first int, macro defined above
        
        # ACQUIRE_CARD first arg is which card to acquire
        # for the next 'first arg' of arguments, indicate which cube to put
        
        # ACQUIRE_POINT first arg is which card to pick up
        
        # PLAY_CARD first arg is which card to play
        # next arg used for number of times the card is played (for exchange) or
        # next 4 args used for how many of each cube to upgrade
        
        # The other actions has no arguments. 
         
        pass

class HumanPlayer(Player):
    def get_action(self, Game: 'Engine') -> tuple[int, list[int]]:
        Game.display()
        action = int(input("Action (0 acquire card, 1 rest, 2 acquire point, 3 play card): "))
        
        if action == ACQUIRE_CARD:
            card_idx = int(input("Card index to acquire: "))
            args = [card_idx]
            # One cube has to be placed on every card left of the acquired card
            for i in range(card_idx):
                args.append(int(input(f"Cube color for card {i} (0 yellow, 1 red, 2 green, 3 brown): ")))
            return action, args
        
        if action == ACQUIRE_POINT:
            return action, [int(input("Point card index: "))]
        
        if action == PLAY_CARD:
            card_idx = int(input("Card index in hand to play: "))
            card = CARDS[self.hand[card_idx]]
            
            # Exchange cards are played a number of times
            if card["type"] == "exchange":
                return action, [card_idx, int(input("Times to play: "))]
            
            # Upgrade cards take how many of each cube to upgrade
            if card["type"] == "upgrade":
                args = [card_idx]
                for color in range(4):
                    args.append(int(input(f"Cubes to upgrade from color {color} (0 yellow, 1 red, 2 green, 3 brown): ")))
                return action, args
            
            return action, [card_idx]
        
        # Rest
        return action, []

class NaivePlayer(Player):
    def __init__(self):
        super().__init__()
        self.target = None # Point card it is working towards
        
    def get_action(self, Game: 'Engine') -> tuple[int, list[int]]:
        # Pick a random point card to work towards
        if self.target not in Game.Point_cards:
            self.target = random.choice(Game.Point_cards)
        
        cost = CARDS[self.target]["cost"]
        missing = [x - y for x, y in zip(cost, self.caravan)]
        
        # Enough cubes for the point card
        if all(x <= 0 for x in missing):
            return ACQUIRE_POINT, [Game.Point_cards.index(self.target)]
        
        # Get 2 yellow
        if "sp_yy" in self.hand:
            return PLAY_CARD, [self.hand.index("sp_yy")]
        
        # Upgrade cubes one step towards the colors that are missing
        if "upgrade_2" in self.hand:
            args = [self.hand.index("upgrade_2"),0,0,0,0]
            steps = CARDS["upgrade_2"]["steps"]
            for color in range(BROWN - 1, -1, -1):
                if max(missing[color + 1:]) > 0 and self.caravan[color] > 0:
                    amount = min(self.caravan[color], steps)
                    args[color + 1] = amount
                    steps -= amount
            return PLAY_CARD, args
        
        # No useful card, rest to pick up the discard
        return REST, []

class Engine:
    def __init__(self, Players: list[Player]):
        # Set up the game with list of Players 
        self.Players = Players
        self.Player_in_play = 0 # Index of player who's supposed to move
        self.game_ends = 0
        
        # Starting cubes, later seats get more cubes to make up for the turn order
        Starting_cubes = [[3,0,0,0], [4,0,0,0], [4,0,0,0], [3,1,0,0], [3,1,0,0]]
        for i, player in enumerate(self.Players):
            player.caravan = list(Starting_cubes[i])
        
        # Coins above the first and second point card, twice as many as there are players
        self.Gold_coins = len(self.Players) * 2
        self.Silver_coins = len(self.Players) * 2
        self.Silver_pos = 1 # Point card position the silver coins are sitting above
        
        self.Point_deck = POINT_CARDS
        self.Trader_deck = TRADER_CARDS

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
        
    def step(self) -> int | None:
        # return winner id, else none
        
        if self.game_ends == 1 and self.Player_in_play == 0:
            return max(range(len(self.Players)), key = lambda p: self.Players[p].total_score())
            
        
        player = self.Players[self.Player_in_play]
        action, args = player.get_action(self)
        # There are a few actions a player can take, 
        
        # TODO ADD ALL THE CHECKS, if action invalid skip player turn.
        # TODO CARAVAN LIMIT
        
        
        # Acquire card
        if action == ACQUIRE_CARD:
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
        if action == REST:
            player.hand.extend(player.discard)
            player.discard = []
        
        # Score
        if action == ACQUIRE_POINT:
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
        if action == PLAY_CARD:
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
            
        # Game ends when one player has 5 point cards
        if self.Players[self.Player_in_play].pcard_count == 5:
            self.game_ends = 1
            
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
            
            
        
         
        
    
    
    
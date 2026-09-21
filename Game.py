import json
from pathlib import Path
import random

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
        self.caravan = {"Y": 0,
                        "R": 0,
                        "G": 0,
                        "B": 0}
        # Caravan has 4 types of cubes, yellow, red, green, brown, in each index
        self.score = 0
        self.hand = ["create_2_y","upgrade_2"]
        self.discard = []

    def get_action(self):
        pass

class Engine:
    def __init__(self, Players: list):
        # Set up the game with list of Players 
        self.Players = Players

        self.Point_deck = POINT_CARDS
        self.Trader_deck = TRADER_CARDS

        self.Point_cards = []
        self.Trader_cards = []

        # draw the initial cards
        for _ in range(5):
            self.draw(self.Trader_deck)
            self.draw(self.Point_deck)
        self.draw(self.Trader_deck)
        

    def draw(self, Deck: list, Table: list) -> None:
        # Draw a card from Deck into the corresponding list of the table 
        drawn_card = random.choice(Deck)
        Deck.remove(drawn_card)
        Table.append(drawn_card)

    
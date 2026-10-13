import random

from util import CARDS, ACQUIRE_POINT, PLAY_CARD, REST, BROWN
from players.base import Player


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

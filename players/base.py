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

    def get_discard(self, Game: 'Engine', excess: int) -> list[int]:
        # Caravan is over the limit, return the colors of the cubes to drop
        # Default: the lowest valued cubes first
        discards = []
        for color in range(4):
            discards.extend([color] * min(excess - len(discards), self.caravan[color]))
        return discards

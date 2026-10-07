import random
from util import CARDS, ACQUIRE_CARD, REST, ACQUIRE_POINT, PLAY_CARD, DISCARD, BROWN, search


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

class HumanPlayer(Player):
    def get_action(self, Game: 'Engine') -> tuple[int, list[int]]:
        Game.display()
        
        while True:
            action = int(input("Action (0 acquire card, 1 rest, 2 acquire point, 3 play card): "))
            args = []
            
            if action == ACQUIRE_CARD:
                card_idx = int(input("Card index to acquire: "))
                args = [card_idx]
                # One cube has to be placed on every card left of the acquired card
                for i in range(card_idx):
                    args.append(int(input(f"Cube color for card {i} (0 yellow, 1 red, 2 green, 3 brown): ")))
            
            if action == ACQUIRE_POINT:
                args = [int(input("Point card index: "))]
            
            if action == PLAY_CARD:
                card_idx = int(input("Card index in hand to play: "))
                args = [card_idx]
                # Only exchange and upgrade cards take extra arguments
                if 0 <= card_idx < len(self.hand):
                    card = CARDS[self.hand[card_idx]]
                    if card["type"] == "exchange":
                        args.append(int(input("Times to play: ")))
                    if card["type"] == "upgrade":
                        for color in range(4):
                            args.append(int(input(f"Cubes to upgrade from color {color} (0 yellow, 1 red, 2 green, 3 brown): ")))
            
            # Rest has no arguments
            
            # Ask again until the move is legal
            reason = Game.legal_move(self, action, args)
            if reason is not None:
                print(f"Illegal move: {reason}")
                continue
            return action, args
    
    def get_discard(self, Game: 'Engine', excess: int) -> list[int]:
        # Ask which cubes to drop until the discard is valid
        print(f"Caravan over the limit by {excess}, caravan {self.caravan}")
        
        while True:
            discards = []
            for i in range(excess):
                color = int(input(f"Cube {i + 1} of {excess} to discard (0 yellow, 1 red, 2 green, 3 brown): "))
                discards.append(color)
            
            if all(0 <= color < 4 for color in discards):
                counts = [0, 0, 0, 0]
                for color in discards:
                    counts[color] += 1
                if all(n <= have for n, have in zip(counts, self.caravan)):
                    return discards
            
            print("Illegal discard: colors must be 0-3 and the caravan has to hold the cubes")

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

class HeuristicPlayer(Player):
    def __init__(self):
        super().__init__()
        self.target = None # Point card being worked towards
        self.plan = None # Cached plan from search
    
    def coverage(self) -> tuple[set, set]:
        # Every color the cards can take as input and give as output
        inputs = set()
        outputs = set()
        for card_name in self.hand + self.discard:
            card = CARDS[card_name]
            gain = card.get("gain", [0,0,0,0])
            cost = card.get("cost", [0,0,0,0])
            for color in range(4):
                if gain[color] > 0:
                    outputs.add(color)
                if cost[color] > 0:
                    inputs.add(color)
        return inputs, outputs
    
    def generate(self) -> tuple[int, list[int]]:
        # Get 2 yellow
        if "sp_yy" in self.hand:
            return PLAY_CARD, [self.hand.index("sp_yy")]
        
        # Rest to pick the cards back up
        return REST, []
    
    def build_action(self, Game: 'Engine') -> tuple[int, list[int]] | None:
        # Pick up the leftmost card that adds an input or output color the cards do not have
        inputs, outputs = self.coverage()
        for card_idx, card_name in enumerate(Game.Trader_cards):
            card = CARDS[card_name]
            gain = card.get("gain", [0,0,0,0])
            cost = card.get("cost", [0,0,0,0])
            useful = any(gain[color] > 0 and color not in outputs for color in range(4))
            useful = useful or any(cost[color] > 0 and color not in inputs for color in range(4))
            if not useful:
                continue
            
            # One cube has to be placed on every card left of the acquired card
            placements = []
            cubes = list(self.caravan)
            for _ in range(card_idx):
                color = next((c for c in range(4) if cubes[c] > 0), None)
                if color is None:
                    break
                cubes[color] -= 1
                placements.append(color)
            
            # Not enough cubes to reach the card, generate first
            if len(placements) < card_idx:
                return self.generate()
            
            return ACQUIRE_CARD, [card_idx] + placements
        
        # Nothing in the row adds coverage
        return None
    
    def get_action(self, Game: 'Engine') -> tuple[int, list[int]]:
        inputs, outputs = self.coverage()
        
        # Keep picking up cards until every spice is covered
        if len(inputs) < 4 or len(outputs) < 4:
            move = self.build_action(Game)
            
            # Picking up or generating changes the hand, a cached plan would be stale
            if move is not None:
                self.plan = None
                return move
        
        # Go for the highest value point card with a plan cached from search
        if self.plan is None or self.target not in Game.Point_cards:
            self.target = max(Game.Point_cards, key = lambda card_name: CARDS[card_name]["vp"])
            self.plan = search(self.hand, CARDS[self.target]["cost"], self.caravan, self.discard)
        
        # Play the cached plan one move at a time, skipping discard steps,
        # those are consumed by get_discard between turns
        while self.plan and self.plan[0][0] == DISCARD:
            self.plan.pop(0)
        
        if self.plan:
            action, args = self.plan.pop(0)
            if action == PLAY_CARD:
                # Plans use card names, the engine wants a hand index
                args = [self.hand.index(args[0])] + args[1:]
            return action, args
        
        # Plan is empty, the caravan is ready for the point card
        if self.plan == []:
            self.plan = None
            return ACQUIRE_POINT, [Game.Point_cards.index(self.target)]
        
        # No plan found, generate cubes and try again
        return self.generate()
    
    def get_discard(self, Game: 'Engine', excess: int) -> list[int]:
        # The cached plan already picked the discard when its play overshot the limit
        if self.plan and self.plan[0][0] == DISCARD and len(self.plan[0][1]) == excess:
            return self.plan.pop(0)[1]
        
        self.plan = None
        
        # No point card to plan against, keep the lowest cubes
        if self.target not in Game.Point_cards:
            return super().get_discard(Game, excess)
        
        # Search again from the over limit caravan, the first move of the plan
        # is the discard that keeps the fastest route to the point card
        plan = search(self.hand, CARDS[self.target]["cost"], self.caravan, self.discard)
        if plan and plan[0][0] == DISCARD and len(plan[0][1]) == excess:
            return plan[0][1]
        
        # The point card is unreachable either way, keep the lowest cubes
        return super().get_discard(Game, excess)


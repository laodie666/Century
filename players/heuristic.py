from util import CARDS, ACQUIRE_CARD, REST, ACQUIRE_POINT, PLAY_CARD, DISCARD, search
from players.base import Player


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
    
    def deck_building(self, Game) -> tuple | None:
        # Keep picking up cards until every spice is covered
        inputs, outputs = self.coverage()
        if len(inputs) < 4 or len(outputs) < 4:
            return self.build_action(Game)
        return None
    
    def get_action(self, Game: 'Engine') -> tuple[int, list[int]]:
        move = self.deck_building(Game)
        
        # Picking up or generating changes the hand, a cached plan would be stale
        if move is not None:
            self.plan = None
            return move
        
        # Go for the point card chosen by select_target, with a plan cached from search
        if self.plan is None or self.target not in Game.Point_cards:
            self.target, self.plan = self.select_target(Game)
        
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
    
    def select_target(self, Game) -> tuple:
        # Highest value point card, with a plan cached from search
        target = max(Game.Point_cards, key = lambda card_name: CARDS[card_name]["vp"])
        return target, search(self.hand, CARDS[target]["cost"], self.caravan, self.discard)
    
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

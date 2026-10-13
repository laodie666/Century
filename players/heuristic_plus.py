from util import CARDS, ACQUIRE_CARD, search_all
from players.heuristic import HeuristicPlayer


class HeuristicPlus(HeuristicPlayer):
    # Value term weights
    NEW_COLOR = 2.0
    NET_GAIN = 0.5
    DISTANCE = 0.25
    
    # Assessment aspects, each backed by a value_<name> method, the total sums them
    VALUE_TERMS = ["new_colors", "net_gain", "distance"]
    
    def determine_value(self, card_name: str, card_idx: int = 0) -> float:
        # Raw value of picking up the card for the deck, the term sum
        # Negative values are allowed and stay comparable between cards
        card = CARDS[card_name]
        return sum(getattr(self, f"value_{term}")(card, card_idx) for term in self.VALUE_TERMS)
    
    def worth_picking(self, card_name: str, card_idx: int = 0) -> bool:
        # Desirable for the deck: passes the desirability gate with a positive raw value
        return self.desirable(CARDS[card_name]) and self.determine_value(card_name, card_idx) > 0
    
    def desirable(self, card: dict) -> bool:
        # The old coverage heuristic as the gate: worth picking up iff it adds an input
        # or output color the deck does not have
        gain = card.get("gain", [0,0,0,0])
        cost = card.get("cost", [0,0,0,0])
        inputs, outputs = self.coverage()
        return any((gain[color] > 0 and color not in outputs)
                   or (cost[color] > 0 and color not in inputs) for color in range(4))
    
    def value_new_colors(self, card: dict, card_idx: int) -> float:
        # Coverage: colors the deck can newly pay or newly produce
        gain = card.get("gain", [0,0,0,0])
        cost = card.get("cost", [0,0,0,0])
        inputs, outputs = self.coverage()
        new = sum(1 for color in range(4)
                  if (gain[color] > 0 and color not in outputs)
                  or (cost[color] > 0 and color not in inputs))
        return self.NEW_COLOR * new
    
    def value_net_gain(self, card: dict, card_idx: int) -> float:
        # Throughput: net cubes per play
        return self.NET_GAIN * (sum(card.get("gain", [0,0,0,0])) - sum(card.get("cost", [0,0,0,0])))
    
    def value_distance(self, card: dict, card_idx: int) -> float:
        # Cubes paid to reach the card in the row
        return -self.DISTANCE * card_idx
    
    def deck_building(self, Game) -> tuple | None:
        # Pick up cards while the market has anything desirable, all -1 means start playing
        return self.build_action(Game)
    
    def build_action(self, Game) -> tuple | None:
        # Acquire the best scoring card the caravan can reach
        desirable = False
        best = None
        for card_idx, card_name in enumerate(Game.Trader_cards):
            if not self.worth_picking(card_name, card_idx):
                continue
            desirable = True
            score = self.determine_value(card_name, card_idx)
            
            # One cube has to be placed on every card left of the acquired card
            placements = []
            cubes = list(self.caravan)
            for _ in range(card_idx):
                color = next((c for c in range(4) if cubes[c] > 0), None)
                if color is None:
                    break
                cubes[color] -= 1
                placements.append(color)
            
            # Out of cubes before reaching the card, the cards behind it cost even more
            if len(placements) < card_idx:
                continue
            
            if best is None or score > best[0]:
                best = (score, card_idx, placements)
        
        # All cards are -1, no need to pick up more, start playing
        if not desirable:
            return None
        # Desirable cards exist but none reachable, generate cubes first
        if best is None:
            return self.generate()
        return ACQUIRE_CARD, [best[1]] + best[2]
    
    def select_target(self, Game) -> tuple:
        # Highest value per turn, the total turns include the scoring turn itself
        plans = search_all(self.hand, [CARDS[card_name]["cost"] for card_name in Game.Point_cards], self.caravan, self.discard)
        
        best = None
        for card_name in Game.Point_cards:
            plan = plans.get(tuple(CARDS[card_name]["cost"]))
            if plan is None:
                continue
            ratio = CARDS[card_name]["vp"] / (len(plan) + 1)
            if best is None or ratio > best[0]:
                best = (ratio, card_name, plan)
        
        # Nothing is reachable, fall back to the highest value card
        if best is None:
            target = max(Game.Point_cards, key = lambda card_name: CARDS[card_name]["vp"])
            return target, None
        
        return best[1], list(best[2])

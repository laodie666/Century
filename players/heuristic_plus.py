from util import CARDS, ACQUIRE_CARD, YELLOW, search_all
from players.heuristic import HeuristicPlayer


class HeuristicPlus(HeuristicPlayer):
    # Value term weights
    NEW_COLOR = 2.0
    NET_GAIN = 0.5
    DISTANCE = 0.25
    SPICE = -1.0
    SPICE_YELLOW = 1.5
    REPEAT_INPUT = -1.0
    SIMPLE = 1.5
    DECK_TARGET = 10
    DECK_FILL = 1.0
    SYNERGY = 1.0
    EARLY_DECK = 6 # Deck size up to which yellow producers count as early
    
    # Assessment aspects, each backed by a value_<name> method, the total sums them
    VALUE_TERMS = ["new_colors", "net_gain", "distance", "spice", "repeat_input", "simple",
                   "deck_fill", "synergy"]
    
    def determine_value(self, card_name: str, card_idx: int = 0) -> float:
        # Raw value of picking up the card for the deck, the term sum
        # Negative values are allowed and stay comparable between cards
        card = CARDS[card_name]
        return sum(getattr(self, f"value_{term}")(card, card_idx) for term in self.VALUE_TERMS)
    
    def worth_picking(self, card_name: str, card_idx: int = 0) -> bool:
        # Desirable for the deck: a positive raw value with the desirability gate;
        # below the target deck size the fill bonus speaks for every card and the
        # gate steps aside, growing the deck beats being picky
        if len(self.hand) + len(self.discard) < self.DECK_TARGET:
            return self.determine_value(card_name, card_idx) > 0
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
    
    def value_spice(self, card: dict, card_idx: int) -> float:
        # Produce cards are good but not great, they only print one color and
        # trade cards turn cubes into more cubes. Yellow producers are the exception
        # while the deck is small: more yellow to spend on the trade cards it needs
        if card["type"] != "spice":
            return 0.0
        score = self.SPICE
        deck = len(self.hand) + len(self.discard)
        if card["gain"][YELLOW] > 0:
            score += self.SPICE_YELLOW * card["gain"][YELLOW] * max(0, 1 - deck / self.EARLY_DECK)
        return score
    
    def value_repeat_input(self, card: dict, card_idx: int) -> float:
        # Trade cards sharing an input color with trade cards already in the deck
        # compete for the same cubes every cycle, do not stack them
        if card["type"] != "exchange":
            return 0.0
        inputs = {color for color in range(4) if card["cost"][color] > 0}
        shared = 0
        for card_name in self.hand + self.discard:
            other = CARDS[card_name]
            if other["type"] == "exchange" and any(other["cost"][color] > 0 for color in inputs):
                shared += 1
        return self.REPEAT_INPUT * shared
    
    def value_simple(self, card: dict, card_idx: int) -> float:
        # Simple trade cards: a single input color of at most 3 cubes and a single
        # output color of at most 3 cubes, they cycle the engine cleanly
        if card["type"] != "exchange":
            return 0.0
        cost = [cubes for cubes in card["cost"] if cubes > 0]
        gain = [cubes for cubes in card["gain"] if cubes > 0]
        if len(cost) == 1 and cost[0] <= 3 and len(gain) == 1 and gain[0] <= 3:
            return self.SIMPLE
        return 0.0
    
    def value_deck_fill(self, card: dict, card_idx: int) -> float:
        # Growing the deck toward the target makes every card worth more, the bonus
        # fades out linearly and hits zero once the deck is filled up to the target
        deck = len(self.hand) + len(self.discard)
        return self.DECK_FILL * max(0, self.DECK_TARGET - deck)
    
    def value_synergy(self, card: dict, card_idx: int) -> float:
        # How well the card's inputs are fed by outputs the deck already produces:
        # per input color the best single producer in the deck, capped by the demand
        bonus = 0.0
        for color in range(4):
            demand = card.get("cost", [0,0,0,0])[color]
            if demand > 0:
                best_output = 0
                for card_name in self.hand + self.discard:
                    best_output = max(best_output, CARDS[card_name].get("gain", [0,0,0,0])[color])
                bonus += self.SYNERGY * min(demand, best_output)
        return bonus
    
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

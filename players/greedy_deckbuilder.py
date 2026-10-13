from util import CARDS, ACQUIRE_CARD
from players.heuristic_plus import HeuristicPlus


class GreedyDeckbuilder(HeuristicPlus):
    # Deck building fork of HeuristicPlus: forced acquisitions of the highest raw
    # value card (negatives allowed) until the deck reaches MIN_DECK cards with
    # full input/output coverage, then falls back to the scored stop rule
    MIN_DECK = 10

    def __init__(self):
        super().__init__()
        self.acquires = 0

    def deck_building(self, Game) -> tuple | None:
        # Forced acquisition phase until min deck size and full coverage are reached
        inputs, outputs = self.coverage()
        if len(self.hand) + len(self.discard) < self.MIN_DECK \
                or len(inputs) < 4 or len(outputs) < 4:
            return self.greedy_build(Game)
        return super().deck_building(Game)

    def greedy_build(self, Game) -> tuple | None:
        # Highest raw value card the caravan can reach, negatives rank too
        best = None
        for card_idx, card_name in enumerate(Game.Trader_cards):
            value = self.determine_value(card_name, card_idx)

            # One cube has to be placed on every card left of the acquired card
            placements = []
            cubes = list(self.caravan)
            for _ in range(card_idx):
                color = next((c for c in range(4) if cubes[c] > 0), None)
                if color is None:
                    break
                cubes[color] -= 1
                placements.append(color)

            # Out of cubes before reaching the card
            if len(placements) < card_idx:
                continue

            if best is None or value > best[0]:
                best = (value, card_idx, placements)

        # Nothing reachable, generate cubes first
        if best is None:
            return self.generate()
        self.acquires += 1
        return ACQUIRE_CARD, [best[1]] + best[2]

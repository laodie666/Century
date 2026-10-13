from util import CARDS, ACQUIRE_CARD, ACQUIRE_POINT, PLAY_CARD
from players.base import Player


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

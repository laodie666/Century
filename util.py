import json
from pathlib import Path
from collections import deque


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


def search(hand: list, objective: list, caravan: list = [0,0,0,0], discard: list = []) -> list | None:
    # Search for the fastest sequence of plays and rests that gets the caravan to cover the objective
    # Returns a list of (action, args), args[0] of a play is the card name instead of a hand index
    # Every play and rest costs one turn, returns None if the objective cannot be reached
    
    Cap = sum(objective) + max(caravan) + 5 # More cubes than this can never help
    Start = (tuple(sorted(hand)), tuple(sorted(discard)), tuple(caravan))
    Queue = deque([(Start, [])])
    Seen = {Start}
    
    while Queue:
        (Hand, Discard, Caravan), Plan = Queue.popleft()
        
        # Objective reached
        if all(x <= y for x, y in zip(objective, Caravan)):
            return Plan
        
        # Play every card in hand
        for i, card_name in enumerate(Hand):
            Next_hand = Hand[:i] + Hand[i+1:]
            Next_discard = tuple(sorted(Discard + (card_name,)))
            for cubes, args in play_results(CARDS[card_name], Caravan):
                if max(cubes) > Cap:
                    continue
                State = (Next_hand, Next_discard, cubes)
                if State not in Seen:
                    Seen.add(State)
                    Queue.append((State, Plan + [(PLAY_CARD, [card_name] + args)]))
        
        # Rest to take the discard back into the hand
        if Discard:
            State = (tuple(sorted(Hand + Discard)), (), Caravan)
            if State not in Seen:
                Seen.add(State)
                Queue.append((State, Plan + [(REST, [])]))
    
    return None


def play_results(card: dict, caravan: tuple) -> list:
    # Every possible result of playing the card once, as (caravan, extra args) pairs
    results = []
    
    if card["type"] == "spice":
        results.append((tuple(x + y for x, y in zip(caravan, card["gain"])), []))
    
    if card["type"] == "exchange":
        # Play it as many times as the caravan can pay for
        max_times = min([caravan[color] // amount for color, amount in enumerate(card["cost"]) if amount > 0], default=0)
        for times in range(1, max_times + 1):
            cubes = tuple(x - y * times for x, y in zip(caravan, card["cost"]))
            cubes = tuple(x + y * times for x, y in zip(cubes, card["gain"]))
            results.append((cubes, [times]))
    
    if card["type"] == "upgrade":
        # Try every way to spend the steps, higher colors can upgrade cubes made earlier
        Stack = [(0, list(caravan), [0,0,0,0], card["steps"])]
        while Stack:
            color, cubes, args, steps = Stack.pop()
            if color == BROWN or steps == 0:
                results.append((tuple(cubes), list(args)))
                continue
            for amount in range(min(steps, cubes[color]) + 1):
                next_cubes = list(cubes)
                next_cubes[color] -= amount
                next_cubes[color + 1] += amount
                next_args = list(args)
                next_args[color] = amount
                Stack.append((color + 1, next_cubes, next_args, steps - amount))
    
    return results



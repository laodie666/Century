import json
from pathlib import Path
from collections import deque
from itertools import combinations


ACQUIRE_CARD = 0
REST = 1
ACQUIRE_POINT = 2
PLAY_CARD = 3
DISCARD = 4 # Not a turn action, the engine asks for it at the end of the turn

CARAVAN_LIMIT = 10

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


def discard_options(caravan: list, excess: int) -> list:
    # Every distinct way to discard excess cubes, lowest colors first,
    # as (discarded colors, resulting caravan) pairs
    cubes = [color for color, count in enumerate(caravan) for _ in range(count)]
    options = []
    for combo in sorted(set(combinations(cubes, excess))):
        resulting = list(caravan)
        for color in combo:
            resulting[color] -= 1
        options.append((list(combo), resulting))
    return options


def limit_options(cubes: list) -> list:
    # The caravan after the forced discard down to the limit, ([], cubes) if it already fits
    excess = sum(cubes) - CARAVAN_LIMIT
    if excess <= 0:
        return [([], cubes)]
    return discard_options(cubes, excess)


def search_all(hand: list, objectives: list, caravan: list = [0,0,0,0], discard: list = []) -> dict:
    # Search for the fastest sequence of plays and rests that gets the caravan to cover
    # each of the objectives, one BFS over the shared state space
    # Returns a dict of objective tuple -> shortest plan, one entry per reachable objective
    # (DISCARD, [colors]) steps are inserted when a play pushes the caravan over the limit,
    # they cost no turn, the engine asks for them at the end of the turn
    # Every play and rest costs one turn
    
    Cap = max(sum(o) for o in objectives) + max(caravan) + 5 # More cubes than this can never help
    Remaining = {tuple(o) for o in objectives}
    Found = {}
    Queue = deque()
    Seen = set()
    
    # Starting over the limit, every way to discard back down is a free first move
    for discards, cubes in limit_options(caravan):
        State = (tuple(sorted(hand)), tuple(sorted(discard)), tuple(cubes))
        if State not in Seen:
            Seen.add(State)
            Queue.append((State, [(DISCARD, list(discards))] if discards else []))
    
    while Queue and Remaining:
        (Hand, Discard, Caravan), Plan = Queue.popleft()
        
        # The first state to cover an objective holds its fastest plan
        for objective in [o for o in Remaining if all(x <= y for x, y in zip(o, Caravan))]:
            Found[objective] = Plan
            Remaining.remove(objective)
        
        # Play every card in hand
        for i, card_name in enumerate(Hand):
            Next_hand = Hand[:i] + Hand[i+1:]
            Next_discard = tuple(sorted(Discard + (card_name,)))
            for cubes, args in play_results(CARDS[card_name], Caravan):
                if max(cubes) > Cap:
                    continue
                # Folding the forced discard into the same turn keeps every edge one turn
                for discards, post in limit_options(list(cubes)):
                    State = (Next_hand, Next_discard, tuple(post))
                    if State not in Seen:
                        Seen.add(State)
                        Moves = Plan + [(PLAY_CARD, [card_name] + args)]
                        if discards:
                            Moves = Moves + [(DISCARD, list(discards))]
                        Queue.append((State, Moves))
        
        # Rest to take the discard back into the hand
        if Discard:
            State = (tuple(sorted(Hand + Discard)), (), Caravan)
            if State not in Seen:
                Seen.add(State)
                Queue.append((State, Plan + [(REST, [])]))
    
    return Found


def search(hand: list, objective: list, caravan: list = [0,0,0,0], discard: list = []) -> list | None:
    # Search for the fastest sequence of plays and rests that gets the caravan to cover the objective
    # Returns a list of (action, args), args[0] of a play is the card name instead of a hand index
    # Every play and rest costs one turn, returns None if the objective cannot be reached
    plan = search_all(hand, [objective], caravan, discard).get(tuple(objective))
    return list(plan) if plan is not None else None


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



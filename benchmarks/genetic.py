# Genetic algorithm tuning for the HeuristicPlus value weights
# Population of weight sets, tournament of 4-candidate games per generation with
# common random numbers (same seed = same deals for every candidate), top half
# survives, uniform crossover + gaussian mutation, champion kept
# Checkpointed every generation to benchmarks/genetic_state/, rerun without
# --fresh to resume after a cancel
# Usage: python benchmarks/genetic.py [generations] [--fresh]   (from the repo root)
import sys
import json
import os
import time
import random
import zlib
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from Game import Engine
from players import HeuristicPlus

STATE_DIR = Path(__file__).resolve().parent / "genetic_state"
CHECKPOINT = STATE_DIR / "checkpoint.json"
LOG = STATE_DIR / "run.log"

# gene name -> (min, max); int genes are rounded
GENOME_SPEC = {
    "DECK_TARGET": (6, 12),  # the floor sweep showed 12+ brings no gain, only slow games
    "DECK_FILL": (0.0, 3.0),
    "SYNERGY": (0.0, 3.0),
    "SPICE": (-3.0, 0.0),
    "SPICE_YELLOW": (0.0, 4.0),
    "EARLY_DECK": (3, 10),
    "REPEAT_INPUT": (-3.0, 0.0),
    "SIMPLE": (0.0, 3.0),
    "NEW_COLOR": (0.5, 4.0),
    "NET_GAIN": (0.0, 2.0),
    "DISTANCE": (0.0, 1.0),
}
INT_GENES = {"DECK_TARGET", "EARLY_DECK"}

DEFAULT_GENOME = {
    "DECK_TARGET": 10, "DECK_FILL": 1.0, "SYNERGY": 1.0, "SPICE": -1.0,
    "SPICE_YELLOW": 1.5, "EARLY_DECK": 6, "REPEAT_INPUT": -1.0, "SIMPLE": 1.5,
    "NEW_COLOR": 2.0, "NET_GAIN": 0.5, "DISTANCE": 0.25,
}

POPULATION_SIZE = 8
GAMES_PER_GENERATION = 6   # rounds of 4-candidate games, everyone plays each round
MUTATION_RATE = 0.6
MUTATION_SIGMA = 0.15     # fraction of the gene range

evo_rng = random.Random(20260420)


class Candidate:
    def __init__(self, genome, fitness=None):
        self.genome = {k: genome[k] for k in GENOME_SPEC}
        self.fitness = fitness

    def name(self):
        return f"t{self.genome['DECK_TARGET']}f{self.genome['DECK_FILL']:.1f}" \
               f"sy{self.genome['SYNERGY']:.1f}sp{self.genome['SPICE']:.1f}"

    def agent_class(self):
        return type(f"Evo_{abs(hash(self.genome_hashable())) % 100000}", (HeuristicPlus,), dict(self.genome))

    def genome_hashable(self):
        return tuple(sorted((k, round(v, 4) if isinstance(v, float) else v)
                            for k, v in self.genome.items()))


def clamp(gene, value):
    low, high = GENOME_SPEC[gene]
    value = min(high, max(low, value))
    return round(value) if gene in INT_GENES else value


def mutate(genome):
    child = {}
    for gene, (low, high) in GENOME_SPEC.items():
        value = genome[gene]
        if evo_rng.random() < MUTATION_RATE:
            value += evo_rng.gauss(0, MUTATION_SIGMA * (high - low))
        child[gene] = clamp(gene, value)
    return child


def crossover(mother, father):
    return {gene: (mother[gene] if evo_rng.random() < 0.5 else father[gene])
            for gene in GENOME_SPEC}


def evaluate(population, generation, run: "Run"):
    # games_per rounds of 4-candidate games with rotating lineups, seeded deals
    games_per = GAMES_PER_GENERATION
    margins = {c.name(): [] for c in population}
    wins = {c.name(): 0 for c in population}
    games = 0
    for r in range(games_per):
        order = population[r:] + population[:r]
        for group_i in range(0, len(order), 4):
            group = order[group_i:group_i + 4]
            random.seed(zlib.crc32(f"{generation}:{r}:{group_i}".encode()))
            game = Engine([c.agent_class()() for c in group])
            w = None
            while w is None:
                w = game.step()
            scores = [p.total_score() for p in game.Players]
            field_avg = sum(scores) / 4
            for i, c in enumerate(group):
                margins[c.name()].append(scores[i] - field_avg)
                if i == w:
                    wins[c.name()] += 1
            games += 1
            winner = group[w].name()
            run.line(f"    gen {generation} game {games:3} ({time.strftime('%H:%M:%S')}):"
                     f" winner {winner}  | " +
                     " ".join(f"{c.name()}: {scores[i] - field_avg:+.1f}"
                              for i, c in enumerate(group)))
    return {name: sum(m) / len(m) for name, m in margins.items() if m}, wins


def save_state(generation, population, history):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    state = {
        "generation": generation,
        "population": [{"genome": c.genome, "fitness": c.fitness} for c in population],
        "history": history,
    }
    tmp = CHECKPOINT.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=1))
    os.replace(tmp, CHECKPOINT)  # atomic, cancel safe


def load_state():
    if not CHECKPOINT.exists():
        return None
    state = json.loads(CHECKPOINT.read_text())
    population = [Candidate(c["genome"], c["fitness"]) for c in state["population"]]
    return state["generation"], population, state["history"]


def run(run: "Run", generations: int, fresh: bool):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    if fresh and LOG.exists():
        LOG.unlink()
    run.line(f"genetic tuning, {generations} generations target, pop {POPULATION_SIZE},"
             f" {GAMES_PER_GENERATION} games per generation, checkpoint every generation"
             f" (cancel any time, rerun without --fresh to resume)")

    loaded = None if fresh else load_state()
    if loaded is None:
        start_gen = 0
        # Seed the herd: the tested default, the floor sweep standouts, jittered copies
        population = [Candidate(DEFAULT_GENOME)]
        for genome in [dict(DEFAULT_GENOME, DECK_TARGET=12), dict(DEFAULT_GENOME, DECK_FILL=0.5),
                       dict(DEFAULT_GENOME, DECK_TARGET=8)]:
            population.append(Candidate(genome))
        while len(population) < POPULATION_SIZE:
            population.append(Candidate(mutate(DEFAULT_GENOME)))
        history = []
    else:
        start_gen, population, history = loaded
        run.line(f"resumed at generation {start_gen} from checkpoint")

    t0 = time.time()
    champion = None  # best ever seen, (genome, fitness)
    for generation in range(start_gen, generations):
        gen_t0 = time.time()
        fitness, wins = evaluate(population, generation, run)
        for c in population:
            c.fitness = fitness[c.name()]
        population.sort(key=lambda c: -c.fitness)
        gen_best = population[0]
        if champion is None or gen_best.fitness > champion[1]:
            champion = (gen_best.genome, gen_best.fitness)
        history.append((champion[0], champion[1]))
        save_state(generation + 1, population, history)
        run.line(f"  == gen {generation} done in {time.time() - gen_t0:.0f}s"
                 f" (total {time.time() - t0:.0f}s) ==")
        run.line(f"  best this gen: {gen_best.name()} {gen_best.fitness:+.1f}"
                 f" wins {wins[gen_best.name()]}/{GAMES_PER_GENERATION}"
                 f" | champion {Candidate(champion[0]).name()} {champion[1]:+.1f}")
        run.line("  herd: " + " | ".join(f"{c.name()} {c.fitness:+.1f}" for c in population))
        run.line(f"  champion genome: {json.dumps(champion[0])}")

        # breed the next generation: keep the top half, crossover + mutate into children
        survivors = population[:POPULATION_SIZE // 2]
        children = []
        while len(children) < POPULATION_SIZE - len(survivors):
            mother = evo_rng.choice(survivors)
            father = evo_rng.choice(survivors)
            children.append(Candidate(mutate(crossover(mother.genome, father.genome))))
        population = survivors + children

    run.line(f"=== done after {generations} generations,"
             f" {time.time() - t0:.0f}s, champion {champion[1]:+.1f} ===")
    run.close()


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    fresh = "--fresh" in sys.argv
    generations = int(args[0]) if args else 20

    class Run:
        # plain streaming log into the fixed state folder, appended on resume
        def __init__(self):
            pass

        def line(self, text):
            print(text, flush=True)
            with open(LOG, "a", encoding="utf-8") as f:
                f.write(text + "\n")

        def close(self):
            pass

    run(Run(), generations, fresh)

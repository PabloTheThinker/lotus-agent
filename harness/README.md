# L.O.T.U.S. Specialized Harness

Python library that specializes the Hermes Agent runtime for mental-health companionship.

## Install

```bash
cd harness
pip install -e .
```

Hermes Agent must already be installed (`hermes` on PATH, or `hermes-agent` importable).

## Usage

```bash
# Chat via the specialized wrapper (uses HERMES_HOME / lotus profile when set)
export HERMES_HOME=~/.hermes/profiles/lotus
lotus-harness chat

# One-shot
lotus-harness ask "I feel empty and don't know where to start."
```

```python
from lotus import LotusAgent

agent = LotusAgent()
reply = agent.ask("I've been grieving and today is really hard.")
print(reply)
```

## What it adds on top of Hermes

- Mission protocol classification (depression / health / grief / major events)
- Crisis scanning before the model runs
- Research-informed ephemeral system guidance
- Hard safety preamble that cannot be casually overridden by casual chat tone

"""Small deterministic state machine used by NovelBridge agents."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum


class TransitionError(ValueError):
    """Raised when an agent attempts an illegal state transition."""


@dataclass(frozen=True)
class Transition:
    source: str
    target: str


class StateMachine:
    """Validate state transitions outside LLM control."""

    def __init__(
        self,
        initial_state: str,
        transitions: Iterable[tuple[str, str]],
        terminal_states: Iterable[str] = (),
    ) -> None:
        self.state = self._key(initial_state)
        self._transitions = {
            Transition(self._key(source), self._key(target))
            for source, target in transitions
        }
        self._terminal_states = {self._key(state) for state in terminal_states}

    @staticmethod
    def _key(state: str) -> str:
        if isinstance(state, Enum):
            return str(state.value)
        return str(state)

    def can_transition(self, target: str) -> bool:
        return Transition(self.state, self._key(target)) in self._transitions

    def transition(self, target: str) -> str:
        if self.state in self._terminal_states:
            raise TransitionError(f"Cannot transition from terminal state {self.state}")
        if not self.can_transition(target):
            raise TransitionError(f"Illegal transition: {self.state} -> {target}")
        self.state = self._key(target)
        return self.state

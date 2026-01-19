from typing import Dict, Any

from .game_state_models import GameWorldState, PlayerState
from .trainer_engine import TrainerEngine


class AIController:
    """Simple policy engine that decides which trainer actions to run.

    This is deliberately lightweight; you can replace or augment its
    logic by calling these methods from your LLM-based agent.
    """

    def __init__(self, engine: TrainerEngine):
        self.engine = engine

    def analyze_game_state(self, state: GameWorldState) -> Dict[str, Any]:
        player = state.player or PlayerState()
        analysis = {
            "low_health": (player.health or 0) < 30,
            "low_ammo": (player.ammo or 0) < 5,
            "many_enemies": state.enemy_count > 5,
        }
        return analysis

    def choose_action(self, analysis: Dict[str, Any]) -> str:
        if analysis.get("low_health"):
            return "boost_health"
        if analysis.get("low_ammo"):
            return "refill_ammo"
        if analysis.get("many_enemies"):
            return "stabilize"
        return "idle"

    def generate_training_plan(self, state: GameWorldState) -> Dict[str, Any]:
        analysis = self.analyze_game_state(state)
        action = self.choose_action(analysis)
        return {"analysis": analysis, "action": action}

    def run_step(self, state: GameWorldState) -> Dict[str, Any]:
        plan = self.generate_training_plan(state)
        action = plan["action"]

        if action == "boost_health":
            self.engine.auto_health_management()
        elif action == "refill_ammo":
            self.engine.auto_ammo_management()
        elif action == "stabilize":
            self.engine.adaptive_difficulty(state)

        return plan

import os
import sys
import unittest

SRC = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.realpath(SRC))
import lifeos_goal_prompt


class TestGoalPromptGenerator(unittest.TestCase):

    def test_goal_appears_in_output(self):
        goal = "test future mcpo sandbox"
        result = lifeos_goal_prompt.generate_prompt(goal=goal, risk_tier="tier2")
        self.assertIn(goal, result)

    def test_risk_tier_appears_in_output(self):
        result = lifeos_goal_prompt.generate_prompt(goal="test", risk_tier="tier3")
        self.assertIn("tier3", result)

    def test_safety_boundaries_appear(self):
        result = lifeos_goal_prompt.generate_prompt(goal="test", risk_tier="tier1")
        self.assertIn("no public exposure", result.lower())
        self.assertIn("print or commit secrets", result.lower())

    def test_forbidden_staging_list_appears(self):
        result = lifeos_goal_prompt.generate_prompt(goal="test", risk_tier="tier1")
        self.assertIn("50_Event_Log", result)
        self.assertIn(".config/opencode", result)

    def test_stop_line_appears(self):
        result = lifeos_goal_prompt.generate_prompt(goal="test", risk_tier="tier0")
        self.assertIn("Stop Line", result)

    def test_no_env_content_read(self):
        result = lifeos_goal_prompt.generate_prompt(goal="test", risk_tier="tier1")
        self.assertNotIn("LIFEOS_CAPTURE_BEARER_TOKEN", result)
        self.assertNotIn("CAPTURE_TOKEN", result)

    def test_no_token_like_values(self):
        result = lifeos_goal_prompt.generate_prompt(goal="test", risk_tier="tier1")
        for line in result.split("\n"):
            if "token" in line.lower() and len(line) > 40:
                if any(c.isdigit() for c in line):
                    self.fail(f"Token-like line found: {line[:80]}")

    def test_invalid_risk_tier_rejected(self):
        with self.assertRaises(ValueError):
            lifeos_goal_prompt.generate_prompt(goal="test", risk_tier="invalid")

    def test_tier5_accepted(self):
        result = lifeos_goal_prompt.generate_prompt(goal="test", risk_tier="tier5")
        self.assertIn("tier5", result)

    def test_output_is_non_empty(self):
        result = lifeos_goal_prompt.generate_prompt(goal="build feature X", risk_tier="tier2")
        self.assertGreater(len(result), 200)

    def test_phase_plan_mentioned(self):
        result = lifeos_goal_prompt.generate_prompt(goal="test", risk_tier="tier1")
        lower = result.lower()
        self.assertTrue("phase" in lower or "verification" in lower)

    def test_agent_policy_mentioned(self):
        result = lifeos_goal_prompt.generate_prompt(goal="test", risk_tier="tier1")
        lower = result.lower()
        self.assertTrue("agent" in lower and "proportion" in lower)


if __name__ == "__main__":
    unittest.main()

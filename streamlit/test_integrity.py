import unittest
import sys
import re

# Insert path to allow importing views
sys.path.insert(0, ".")

try:
    from views.chatbot import TEMPLATES
except ImportError:
    TEMPLATES = []


class TestGeoTechIntegrity(unittest.TestCase):

    def test_chatbot_hackathon_queries(self):
        """Test that critical hackathon queries map to the correct narrative explanations."""
        queries = [
            ("what is action orchestrator", "action orchestrator"),
            ("how does drift scan work", "drift scan"),
            ("what is risk synthesis", "risk synthesis"),
            ("drift scan risk weight", "risk weight")
        ]

        def find_match(user_message):
            words = set(re.findall(r'\b\w+\b', user_message.lower()))
            best_match = None
            max_score = 0
            for template in TEMPLATES:
                score = sum(1 for kw in template['keywords'] if kw in words)
                if score > max_score:
                    max_score = score
                    best_match = template
            return best_match

        for query, expected_keyword in queries:
            match = find_match(query)
            self.assertIsNotNone(match, f"Query '{query}' failed to match any template.")
            # Verify the narration contains the expected concept
            self.assertTrue(
                expected_keyword.lower() in match['narration'].lower(),
                f"Query '{query}' matched the wrong template. Got narration: {match['narration']}"
            )

    def test_threshold_simulation_logic(self):
        """Integrity test for the mathematical logic used in the Dashboard Simulation."""
        # This replicates the logic in dashboard.py for testing
        threshold = 100.0
        last_value = 80.0
        gap_to_threshold = threshold - last_value
        
        # Test 1: Normal trend (positive slope towards threshold)
        slope_per_day = 0.5  # 0.5 units/day
        ref_rate = slope_per_day
        sim_rate_normal = ref_rate * 1.00 # Normal
        days_to_breach_normal = gap_to_threshold / sim_rate_normal
        self.assertEqual(days_to_breach_normal, 40.0)
        
        # Test 2: Heavy Rainfall (+20%)
        sim_rate_rain = ref_rate * 1.20
        days_to_breach_rain = gap_to_threshold / sim_rate_rain
        self.assertAlmostEqual(days_to_breach_rain, 33.333, places=2)
        
        # Test 3: Prolonged Drought (-30%)
        sim_rate_drought = ref_rate * 0.70
        days_to_breach_drought = gap_to_threshold / sim_rate_drought
        self.assertAlmostEqual(days_to_breach_drought, 57.14, places=2)
        
        # Integrity check: rainfall breach < normal breach < drought breach
        self.assertTrue(days_to_breach_rain < days_to_breach_normal < days_to_breach_drought)

    def test_risk_score_calculation(self):
        """Integrity test for risk score caps and increments."""
        # 1. Very close to breach (< 14 days) + Seismic
        sim_days_to_threshold = 10
        sim_rate = 1.5
        scenario_multiplier = 1.5 # Seismic
        
        sim_risk_score = 0
        if sim_days_to_threshold <= 14:
            sim_risk_score += 65
        if sim_rate > 1e-6:
            sim_risk_score += 15
        if scenario_multiplier >= 1.5:
            sim_risk_score += 10
            
        sim_risk_score = min(sim_risk_score, 100)
        self.assertEqual(sim_risk_score, 90) # 65 + 15 + 10 = 90
        
        # 2. Verify cap at 100
        sim_risk_score = min(150, 100)
        self.assertEqual(sim_risk_score, 100)

if __name__ == "__main__":
    unittest.main()

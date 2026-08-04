"""Maps posture-error codes into prioritized, human-readable feedback strings."""
from __future__ import annotations

FEEDBACK_MESSAGES: dict[str, str] = {
    "LOW_CONFIDENCE": "Move so your whole body is visible to the camera.",
    "NO_PERSON_DETECTED": "Step into the camera frame.",
    "FRONT_KNEE_PAST_TOES": "Step out further — keep your front knee behind your toes.",
    "KNEE_VALGUS": "Push your knees outward, don't let them cave in.",
    "DYNAMIC_KNEE_INSTABILITY": "Slow down — your knees are moving too fast laterally.",
    "HIP_SAG": "Tighten your core — your hips are dropping.",
    "HIP_PIKE": "Lower your hips — keep a straight line from shoulders to ankles.",
    "RAPID_CORE_INSTABILITY": "Control your descent — your core is collapsing too quickly.",
    "TORSO_LEANING_FORWARD": "Keep your chest up and back straighter.",
    "TORSO_LEANING": "Keep your torso more upright.",
    "TORSO_SWING": "Avoid swinging your body — control the weight with your arm only.",
    "ELBOW_DRIFT": "Keep your elbow pinned to your side.",
    "JERKING_MOVEMENT": "Slow down — don't jerk the weight, control the motion.",
    "BACK_KNEE_TOO_HIGH": "Lower your back knee closer to the floor.",
    "SQUAT_NOT_DEEP_ENOUGH": "Go lower — aim to get your thighs closer to parallel.",
    "INSUFFICIENT_DEPTH": "Go a little deeper on this rep.",
    "INCOMPLETE_EXTENSION": "Straighten your arm fully at the bottom of each rep.",
}

# Injury-risk-adjacent errors are ranked above depth/completeness (performance) issues.
# Velocity-based dynamic errors ranked highest as they indicate highest injury risk.
PRIORITY_ORDER: list[str] = [
    "NO_PERSON_DETECTED",
    "LOW_CONFIDENCE",
    "DYNAMIC_KNEE_INSTABILITY",  # velocity-based: high injury risk
    "RAPID_CORE_INSTABILITY",    # velocity-based: high injury risk
    "JERKING_MOVEMENT",           # velocity-based: high injury risk
    "FRONT_KNEE_PAST_TOES",
    "KNEE_VALGUS",
    "HIP_SAG",
    "HIP_PIKE",
    "TORSO_LEANING_FORWARD",
    "TORSO_LEANING",
    "TORSO_SWING",
    "ELBOW_DRIFT",
    "BACK_KNEE_TOO_HIGH",
    "SQUAT_NOT_DEEP_ENOUGH",
    "INSUFFICIENT_DEPTH",
    "INCOMPLETE_EXTENSION",
]

POSITIVE_FEEDBACK = "Nice form — keep it up!"


class FeedbackGenerator:
    def generate(self, posture_errors: list[str], max_messages: int = 2) -> list[str]:
        if not posture_errors:
            return [POSITIVE_FEEDBACK]
        ranked = sorted(
            set(posture_errors),
            key=lambda e: PRIORITY_ORDER.index(e) if e in PRIORITY_ORDER else len(PRIORITY_ORDER),
        )
        return [FEEDBACK_MESSAGES.get(e, e) for e in ranked[:max_messages]]

"""
blackbox/intervene/patch.py
───────────────────────────
Modifies the prompt, tool arguments, context, or model output.
"""
def apply_patch(step, new_output):
    step.output = new_output
    return step

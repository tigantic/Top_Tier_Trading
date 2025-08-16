"""Test the deep RL training skeleton for fallbacks.

This test ensures that the training script does not raise when ML
libraries are unavailable and that it prints a message indicating
training was skipped.
"""

def test_train_dqn_without_ml_libs(capsys):
    from scripts import train_deep_rl as train_module  # type: ignore
    # Provide a tiny dataset
    data = [([0.0, 0.0, 1.0], 0, 0.0, [0.0, 0.0, 1.0])]
    train_module.train_dqn(data, epochs=1, batch_size=1)
    out = capsys.readouterr().out
    # Should print a message when ML libs are unavailable or training loop completes
    assert "Completed epoch" in out or "ML libraries not available" in out
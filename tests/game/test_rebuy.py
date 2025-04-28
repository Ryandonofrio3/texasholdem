import pytest
import texasholdem as th
from texasholdem.game.game import RebuyError, RebuyWindowError # Import specific error types

def test_rebuy_happy_path():
    g = th.TexasHoldEm(buyin=100, big_blind=1, small_blind=2, max_players=4)
    g.players[1].chips = 0
    g.players[1].state = th.PlayerState.SKIP
    g.hand_phase = th.HandPhase.PREHAND               # simulate between hands

    # Initialize minimal history for rebuy logging
    g.hand_history = th.History()
    # Crucially, initialize the prehand part of the history object
    g.hand_history.prehand = th.PrehandHistory(
        btn_loc=g.btn_loc, big_blind=g.big_blind, small_blind=g.small_blind,
        player_chips={p.player_id: p.chips for p in g.players},
        player_cards=g.hands, actions=[]
    )

    assert g.rebuy(1, 100) == 100
    assert g.players[1].chips == 100
    assert g.players[1].state == th.PlayerState.IN
    # Check if history was updated (basic check)
    assert len(g.hand_history.prehand.actions) == 1
    # Check ActionType enum member, not string
    assert g.hand_history.prehand.actions[0].action_type == "REBUY"
    assert g.hand_history.prehand.actions[0].player_id == 1
    assert g.hand_history.prehand.actions[0].total == 100

def test_rebuy_outside_window():
    g = th.TexasHoldEm(buyin=100, big_blind=1, small_blind=2, max_players=2)
    g.start_hand() # Move phase beyond PREHAND
    with pytest.raises(RebuyWindowError): # Use specific error type
        g.rebuy(0, 50)

def test_rebuy_invalid_player_state():
    g = th.TexasHoldEm(buyin=100, big_blind=1, small_blind=2, max_players=2)
    g.players[0].state = th.PlayerState.ALL_IN # Invalid state for rebuy
    g.hand_phase = th.HandPhase.PREHAND
    # No history needed since validation should fail before _apply_rebuy
    with pytest.raises(RebuyError, match="invalid state"): # Check error message
        # Use can_rebuy first for clarity, or directly test rebuy
        assert not g.can_rebuy(0, 50)
        g.rebuy(0, 50)

def test_rebuy_invalid_seat():
    g = th.TexasHoldEm(buyin=100, big_blind=1, small_blind=2, max_players=2)
    g.hand_phase = th.HandPhase.PREHAND
    # No history needed
    with pytest.raises(RebuyError, match="No seat"): # Check error message
        assert not g.can_rebuy(5, 50)
        g.rebuy(5, 50) # Seat 5 does not exist

def test_rebuy_at_or_above_cap():
    g = th.TexasHoldEm(buyin=100, big_blind=1, small_blind=2, max_players=2, rebuy_cap=1)
    g.players[0].chips = 100 # Already at cap
    g.hand_phase = th.HandPhase.PREHAND
    # No history needed
    with pytest.raises(RebuyError, match="already at or above"): # Check error message
        assert not g.can_rebuy(0, 1)
        g.rebuy(0, 1)

def test_rebuy_exceeds_cap_validation():
    # Test that validation catches amount exceeding cap
    g = th.TexasHoldEm(buyin=100, big_blind=1, small_blind=2, max_players=2, rebuy_cap=2)
    g.players[0].chips = 50
    g.hand_phase = th.HandPhase.PREHAND
    # No history needed
    max_allowed = 100 * 2 - 50
    with pytest.raises(RebuyError, match=f"Amount must be 1-{max_allowed}"): # Check error message
        assert not g.can_rebuy(0, max_allowed + 1)
        g.rebuy(0, max_allowed + 1)

def test_rebuy_zero_or_negative_amount():
    g = th.TexasHoldEm(buyin=100, big_blind=1, small_blind=2, max_players=2)
    g.players[0].chips = 50
    g.hand_phase = th.HandPhase.PREHAND
    # No history needed
    with pytest.raises(RebuyError, match="Amount must be"): # Check specific error message if possible
        assert not g.can_rebuy(0, 0)
        g.rebuy(0, 0)
    with pytest.raises(RebuyError, match="Amount must be"): # Check specific error message if possible
        assert not g.can_rebuy(0, -10)
        g.rebuy(0, -10)

def test_rebuy_default_amount_tops_up_to_cap():
    # Test using default amount works correctly with cap
    g = th.TexasHoldEm(buyin=100, big_blind=1, small_blind=2, max_players=2, rebuy_cap=2)
    g.players[0].chips = 75
    g.hand_phase = th.HandPhase.PREHAND
    g.hand_history = th.History()
    g.hand_history.prehand = th.PrehandHistory(
        btn_loc=g.btn_loc, big_blind=g.big_blind, small_blind=g.small_blind,
        player_chips={p.player_id: p.chips for p in g.players},
        player_cards=g.hands, actions=[]
    )
    expected_rebuy = 100 * 2 - 75
    assert g.can_rebuy(0) # Check default amount is valid
    assert g.rebuy(0) == expected_rebuy # Use default amount
    assert g.players[0].chips == 200

def test_rebuy_default_amount_respects_cap_1():
    # Test default amount respects cap=1
    g = th.TexasHoldEm(buyin=100, big_blind=1, small_blind=2, max_players=2, rebuy_cap=1)
    g.players[0].chips = 50 # Start below buyin
    g.hand_phase = th.HandPhase.PREHAND
    g.hand_history = th.History()
    g.hand_history.prehand = th.PrehandHistory(
        btn_loc=g.btn_loc, big_blind=g.big_blind, small_blind=g.small_blind,
        player_chips={p.player_id: p.chips for p in g.players},
        player_cards=g.hands, actions=[]
    )
    expected_rebuy = 100 * 1 - 50
    assert g.can_rebuy(0) # Default should be valid
    assert g.rebuy(0) == expected_rebuy
    assert g.players[0].chips == 100

# Add a test to ensure can_rebuy is False if amount is invalid but otherwise ok
def test_can_rebuy_false_for_invalid_amount():
    g = th.TexasHoldEm(buyin=100, big_blind=1, small_blind=2, max_players=2, rebuy_cap=1)
    g.players[0].chips = 50
    g.hand_phase = th.HandPhase.PREHAND
    assert not g.can_rebuy(0, 60) # Amount exceeds cap
    assert not g.can_rebuy(0, 0)  # Amount is zero 
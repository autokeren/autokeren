package tool

import "testing"

func TestAgentIDsAcceptsJSONNumbersAndRejectsInvalidValues(t *testing.T) {
	ids, err := agentIDs([]any{float64(2), float64(1), float64(2)})
	if err != nil || len(ids) != 2 || ids[0] != 2 || ids[1] != 1 {
		t.Fatalf("ids=%v err=%v", ids, err)
	}
	for _, value := range []any{nil, []any{}, []any{float64(0)}, []any{"1"}, []any{float64(1.5)}} {
		if _, err := agentIDs(value); err == nil {
			t.Fatalf("expected invalid agent IDs for %#v", value)
		}
	}
}

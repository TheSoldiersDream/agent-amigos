from importlib import import_module

mod = import_module('horse_racing_intelligence.test_live_schedule_integration')

print('Running test_live_schedule_or_warnings...')
mod.test_live_schedule_or_warnings()
print('OK')

print('Running test_sse_stream_emits_event...')
mod.test_sse_stream_emits_event()
print('OK')

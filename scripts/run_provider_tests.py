from importlib import import_module
mod = import_module('horse_racing_intelligence.test_provider_health')
print('provider statuses...')
mod.test_provider_statuses_structure()
print('ok provider statuses')
print('persist/load last good...')
mod.test_persist_and_load_last_good()
print('ok persist/load')

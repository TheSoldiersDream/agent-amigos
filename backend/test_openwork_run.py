from backend.openwork_integration import openwork_manager
s = openwork_manager.create_company_checkin_session(r'C:\Users\user\AgentAmigos', focus='test')
print('session:', s.get('session_id'))
ss = openwork_manager.get_session(s.get('session_id'))
for t in ss['todos']:
    print('TODO:', t.get('title'), 'owner', t.get('owner'), 'owner_id', t.get('owner_id'))
print('KPI last update:', openwork_manager.get_last_kpi_update())

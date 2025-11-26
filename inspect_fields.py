import json

with open('.workspace/raw_jira_issues.json', 'r') as f:
    data = json.load(f)

if data:
    issue = data[0]
    print(f"Key: {issue['key']}")
    print("Fields:")
    for k, v in issue['fields'].items():
        if v:
            if isinstance(v, dict) and 'value' in v:
                print(f"  {k}: {v['value']} (Value)")
            elif isinstance(v, dict) and 'name' in v:
                print(f"  {k}: {v['name']} (Name)")
            elif isinstance(v, list) and len(v) > 0 and isinstance(v[0], dict) and 'name' in v[0]:
                 print(f"  {k}: {[x['name'] for x in v]} (List of Names)")
            elif isinstance(v, str):
                print(f"  {k}: {v}")
            else:
                print(f"  {k}: {type(v)}")

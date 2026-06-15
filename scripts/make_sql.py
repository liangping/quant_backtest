import json
c = json.load(open("/home/ubuntu/296v2.json"))
js = json.dumps(c, ensure_ascii=False).replace("'", "''")
with open("/home/ubuntu/296.sql", "w") as f:
    f.write(f"UPDATE strategy_configs SET config = E'{js}'::jsonb WHERE id = 296;\n")
print("SQL written")

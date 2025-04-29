import json

with open("monsters.json", encoding='utf-8') as f:
        monster_data = json.load(f)["monsters"]

for monster in monster_data:
    s = ('\"name\":{}, \"count\":0'.format(f'"{monster["名字"]}"'))
    print('{' + s + '},')
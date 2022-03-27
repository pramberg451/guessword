import requests
import json
import xmltodict
import random
base_url = "http://ngrams.ucd.ie/therex3/common-nouns/member.action?member={term}&kw={term}&needDisamb=false&xml=true"
word = "coffee"
query = base_url.format(term=word)
response = requests.get(query)

json_string = json.dumps(xmltodict.parse(response.content))
data = json.loads(json_string)
categories = []
for category in data['MemberData']['Categories']['Category']:
    categories.append(category)

print(random.choice(categories))

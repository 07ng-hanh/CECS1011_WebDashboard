import json

c = json.load(open("../dataset/world_ports.jsonc"))
sqlstatement = "insert into ports (port_name, port_lat, port_lon, id) values"
col_inserts = []
port_ids_cnt = {}
for feature in c["features"]:
    props = feature["properties"]
    port_name = "{} ({})".format(props["NameWoDiac"], props["Country"])
    functions = props["Function"]
    lat, lon = feature["geometry"]["coordinates"]
    port_id = props["LOCODE"]


    # skip ports that are not marine ports
    if "1" not in functions:
        continue
    # print(port_name, lat, lon, port_id)

    if port_id in port_ids_cnt:
        #print("DUPLICATE", port_id)
        continue
    port_ids_cnt.setdefault(port_id, 0)
    port_ids_cnt[port_id] += 1
    port_name = port_name.replace("'", "''")

    col_inserts.append(f"('{port_name}', {lat}, {lon}, '{port_id}')")

f = open('ports2sql-write.txt', 'w')
f.write(sqlstatement + ", \n".join(col_inserts))
#print(port_ids_cnt.__len__())
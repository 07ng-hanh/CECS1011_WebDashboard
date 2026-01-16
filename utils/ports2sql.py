import json

c = json.load(open("../dataset/world_ports.jsonc"))
port_hold = open("../dataset/port_hold_time_by_countries.csv").read().split("\n")

port_hold = [x.split(",") for x in port_hold][1:-2]


# Median time in port (days) - All ships by World Bank is licensed under CC BY-3.0 IGO
# Global - International Ports dataset by World Bank is licensed under CC BY-SA 4.0
port_hold_time_ms = {country.strip(): int(float(hold_days) * 86400 * 1000) for (country, hold_days) in port_hold}

sqlstatement = "insert into ports (port_name, port_lat, port_lon, id, hold_time_ms) values"
col_inserts = []
port_ids_cnt = {}
for feature in c["features"]:
    props = feature["properties"]
    port_name = "{} ({})".format(props["NameWoDiac"], props["Country"])
    functions = props["Function"]
    lat, lon = feature["geometry"]["coordinates"]
    port_id = props["LOCODE"]

    port_hold_time_ms.setdefault(props["Country"], port_hold_time_ms["World"])

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

    col_inserts.append(f"('{port_name}', {lat}, {lon}, '{port_id}', {port_hold_time_ms[props['Country']]})")

f = open('ports2sql-write.txt', 'w')
f.write(sqlstatement + ", \n".join(col_inserts))
#print(port_ids_cnt.__len__())
async function set_warehouse_configuration() {
//     Get settings from the input boxes
    let push_obj = {
        capacity: parseInt(document.getElementById("max-capacity").value),
        temperature_low: parseFloat(document.getElementById("threshold-temp-from").value),
        temperature_hi: parseFloat(document.getElementById("threshold-temp-to").value),
        co2_low: parseFloat(document.getElementById("threshold-co2-from").value),
        co2_hi: parseFloat(document.getElementById("threshold-co2-to").value),
        humidity_lo: parseFloat(document.getElementById("threshold-humidity-from").value),
        humidity_hi: parseFloat(document.getElementById("threshold-humidity-to").value),
        threshold_auto: document.getElementById("auto-threshold").checked
    };

    let cond1 = push_obj.temperature_low <= push_obj.temperature_hi
    let cond2 = push_obj.co2_low <= push_obj.co2_hi
    let cond3 = push_obj.humidity_lo <= push_obj.humidity_hi
    let cond4 = push_obj.capacity > 0

    if (!(cond1 && cond2 && cond3)) {
        alert("Invalid range input. Lower bounds must not be larger than upper bounds. All fields must be filled in.")
        return
    }

    if (!cond4) {
        alert("Invalid input. Capacity must be a positive number")
    }

    ret = await axios.post("/admin/set-warehouse-config", push_obj, {
        validateStatus: function (status) {
            return status >= 200 && status <= 500
        },
    })

    if (ret.status !== 200) {
        alert("Saving configs failed. Code: "+ ret.status)
    } else {
        await get_and_show_warehouse_configuration()
        alert("Config updated!")
    }
}

async function get_and_show_warehouse_configuration() {
    ret = await axios.get("/api/config/get-warehouse-config", {
        validateStatus: function (status) {
            return status >= 200 && status <= 500
        },
        params: {
            keys: "*"
        }
    })
    if (ret.status === 200) {
    //     Set data to input boxes
        document.getElementById("max-capacity").value = ret.data.capacity
        document.getElementById("threshold-temp-from").value = ret.data.temperature_low
        document.getElementById("threshold-temp-to").value = ret.data.temperature_hi
        document.getElementById("threshold-co2-from").value = ret.data.co2_low
        document.getElementById("threshold-co2-to").value = ret.data.co2_hi
        document.getElementById("threshold-humidity-from").value = ret.data.humidity_lo
        document.getElementById("threshold-humidity-to").value = ret.data.humidity_hi
        document.getElementById("auto-threshold").checked = ret.data.threshold_auto

    } else {
        alert("Fetching configs failed. Code: " + ret.status)
    }
}

document.addEventListener("DOMContentLoaded", async () => {
    await get_and_show_warehouse_configuration()

})
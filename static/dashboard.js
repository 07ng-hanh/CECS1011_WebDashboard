async function logout() {
    let d = await axios.delete("/api/users/revoke-session")

    if (d.status === 200) {

        window.location.href = "login.html"
    } else {
        alert(`Cannot log out. (${d.status})`)
    }
}

let show_warning_timeout= undefined

function update_all_ok_banner() {
    let show = document.getElementById("threshold-reached-banner").style.display === "none"
    let show_2 = document.getElementById("storage-capacity-warning").style.display === "none"
    let show_3 = document.getElementById("expiry-date-warning-banner").style.display === "none"

    console.log(document.getElementById("storage-capacity-warning").style.display)
    if (show && show_2 && show_3) {
        document.getElementById("all-ok").style.display = "block"
    } else {
        document.getElementById("all-ok").style.display = "none"
    }
}

let exceeding_threshold = false
function update_sensor_metrics(temperature, humidity, co2) {
    document.getElementById("temp-label").innerText = temperature ? temperature : "--"
    document.getElementById("humidity-label").innerText = humidity ? humidity : "--"
    document.getElementById("co2-label").innerText = co2 ? co2 : "--"

    exceeding_threshold = false
    // blink warning gauge when it's exceeding threshold
    if (parseFloat(temperature) >= configs.temperature_hi || parseFloat(temperature) <= configs.temperature_low) {
        document.getElementById("temp-gauge").style.backgroundColor = "#ff5555"
        exceeding_threshold = true
    } else {
        document.getElementById("temp-gauge").style.backgroundColor = "#dfdfdf"
    }

    if (parseFloat(humidity) >= configs.humidity_hi || parseFloat(humidity) <= configs.humidity_lo) {
        document.getElementById("humidity-gauge").style.backgroundColor = "#ff5555"
        exceeding_threshold = true
    } else {
        document.getElementById("humidity-gauge").style.backgroundColor = "#dfdfdf"
    }

    if (parseFloat(co2) >= configs.co2_hi || parseFloat(co2) <= configs.co2_low) {
        document.getElementById("co2-gauge").style.backgroundColor = "#ff5555"
        exceeding_threshold = true
    } else {
        document.getElementById("co2-gauge").style.backgroundColor = "#dfdfdf"
    }

    if (!exceeding_threshold) {
    //     turn off exceeding threshold banner
        if (show_warning_timeout !== undefined) {
            clearTimeout(show_warning_timeout)
        }
        show_warning_timeout = undefined
        document.getElementById("threshold-reached-banner").style.display = 'none'

    } else {
        if (show_warning_timeout === undefined) {
            show_warning_timeout = setTimeout(() => {
                document.getElementById("threshold-reached-banner").style.display = 'block'
            }, 5000)
        }
    }

//     update the all-ok banner
    update_all_ok_banner()

}

async function getWarehouseConfigs() {
    let d = await axios.get("/api/config/get-warehouse-config", {
        params: {
            keys: "*"
        }
    })

    return d.data

}

async function navigate_to_settings() {

    let r = await axios.get("/admin/request-settings-page",
        {
            validateStatus: function (status) {
                return status >= 200 && status <= 500
            }
        }
    )
    if (r.status !== 200) {
        window.location.href = "/api/users/request-settings-page"
    } else {
         window.location.href = "/admin/request-settings-page"
    }

}

// Connect to eventsource to read sensor data at 1s interval
const sensor_evt_source = new EventSource("/api/sensors/sensor-data-stream?interval=1")
sensor_evt_source.addEventListener("data_sent", async (ev) => {
    document.getElementById("sensor-offline-warning").style.display = "none"

    let d = JSON.parse(ev.data)
    update_sensor_metrics(d.temperature, d.humidity, d.co2)
    configs = await getWarehouseConfigs()
})

sensor_evt_source.addEventListener("error_sent", async (ev) => {
    document.getElementById("sensor-offline-warning").style.display = "block"
})

let configs = {}
let quantity_poll_handler = undefined

async function quantity_poll_handler_func() {
    let resp = await axios.get("/api/batch/simple-stats", {
            validateStatus: function (status) {
                return status >= 200 && status <= 500
            },
            params: {
                current_time_ms: new Date().getTime()
            }
        })
        if (resp.status === 200) {
            console.log(resp.data)
            document.getElementById("total-quantity-label").innerText = resp.data.total_quantity ? resp.data.total_quantity : 0

            // check if we have any stuffs near expiry in the warehouse
            if (resp.data.has_expired > 0) {
                document.getElementById("expiry-date-warning-banner").style.display = "block"
                document.getElementById("count-almost-expired").innerText = resp.data.has_expired ? resp.data.has_expired : 0
            } else {
                document.getElementById("expiry-date-warning-banner").style.display = "none"
            }

        //  check if warehouse reaches 70% or more of its capacity
            if (resp.data.total_quantity / configs.capacity > 0.7) {
                document.getElementById("total-quantity-gauge").style.backgroundColor = "#ff5555"
                document.getElementById("storage-capacity-warning").style.display = "block"
                document.getElementById("quantity-percent").innerText = (resp.data.total_quantity / configs.capacity * 100).toFixed()
            } else {
                document.getElementById("total-quantity-gauge").style.backgroundColor = "#dfdfdf"
                document.getElementById("storage-capacity-warning").style.display = "none"
            }
            update_all_ok_banner()
        }
}

document.addEventListener("DOMContentLoaded", async() => {


    document.getElementById("username-lbl").innerText = (await (cookieStore.get({url: window.url, name: "username"}))).value

    configs = await getWarehouseConfigs()
    quantity_poll_handler = window.setInterval(async () => {
    //     handle polling the number of items and whether there are any items past expiry date.
        await quantity_poll_handler_func()

    }, 10000)
    await quantity_poll_handler_func()

})

async function go_to_healthsheet() {
    const c = configs
    console.log(configs)
    window.location.href=`healthsheet.html?tracker_mode=threshold&temp_lo=${c.temperature_low}&temp_hi=${c.temperature_hi}&co2_lo=${c.co2_low}&co2_hi=${c.co2_hi}&humidity_lo=${c.humidity_lo}&humidity_hi=${c.humidity_hi}`
}

window.addEventListener("beforeunload", () => {
    sensor_evt_source.close()
    window.clearInterval(quantity_poll_handler)
})
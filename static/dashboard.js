async function logout() {
    let d = await axios.delete("/api/users/revoke-session")

    if (d.status === 200) {

        window.location.href = "login.html"
    } else {
        alert(`Cannot log out. (${d.status})`)
    }
}

function update_sensor_metrics(temperature, humidity, co2) {
    document.getElementById("temp-label").innerText = temperature
    document.getElementById("humidity-label").innerText = humidity
    document.getElementById("co2-label").innerText = co2
}

// Connect to event source to read sensor data at 1s interval
const sensor_evt_source = new EventSource("/api/sensors/sensor-data-stream?interval=1")
sensor_evt_source.addEventListener("message", (ev) => {

    let d = JSON.parse(ev.data)
    update_sensor_metrics(d.temperature, d.humidity, d.co2)
})
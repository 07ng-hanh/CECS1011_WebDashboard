let port_from_debounce_timer = undefined
let current_departure_port_id = undefined
let current_destination_port_id = undefined
let scheduled_departure_datetime = undefined
async function update_eta() {

}

async function update_port_from_selection(port_id) {
    current_departure_port_id = port_id
    await update_eta()
}

async function update_port_to_selection(port_id) {
    current_destination_port_id = port_id
    await update_eta()
}

async function populate_search_port_from(ev) {
    if (port_from_debounce_timer) {
        clearTimeout(port_from_debounce_timer)
        port_from_debounce_timer = undefined
    }

    setTimeout(async () => {
        const query = document.getElementById("port-from").value
        const container = document.getElementById("departure-port-selector")

        container.innerHTML = ""

        if (query.length >= 3) {
            r = await axios.get("/api/shipments/search-port", {
                params: {
                    q: query
                }
            })
            if (r.status === 200) {
            //     populate port list
                r.data.forEach((port) => {
                    const span = document.createElement("div")
                    span.className = "port-selector-container"
                    const cb = document.createElement("input")
                    cb.id = "cb_" + port.id
                    const lbl = document.createElement("label")
                    lbl.innerText = port.port_name
                    cb.type = "radio"
                    cb.name = "cb-port-from"
                    cb.style.padding = "10px"
                    lbl.style.padding = "10px"

                    lbl.className = "form-check-label"

                    if (port.id == current_departure_port_id) {
                        cb.checked = true
                    }

                    cb.onchange = (ev) => {
                        update_port_from_selection(port.id)
                    }

                    span.appendChild(cb)
                    lbl.setAttribute("for", cb.id)
                    span.appendChild(lbl)
                    container.appendChild(span)

                })
            }

        }

    }, 300)

}


async function populate_search_port_to(ev) {
    if (port_from_debounce_timer) {
        clearTimeout(port_from_debounce_timer)
        port_from_debounce_timer = undefined
    }

    setTimeout(async () => {
        const query = document.getElementById("port-to").value
        const container = document.getElementById("dest-port-selector")

        container.innerHTML = ""

        if (query.length >= 3) {
            r = await axios.get("/api/shipments/search-port", {
                params: {
                    q: query
                }
            })
            if (r.status === 200) {
            //     populate port list
                r.data.forEach((port) => {
                    const span = document.createElement("div")
                    span.className = "port-selector-container"
                    const cb = document.createElement("input")
                    cb.id = "cb2_" + port.id
                    const lbl = document.createElement("label")
                    lbl.innerText = port.port_name
                    cb.type = "radio"
                    cb.style.padding = "10px"
                    cb.name = "cb-port-to"

                    lbl.className = "form-check-label"
                    cb.style.padding = "10px"
                    lbl.style.padding = "10px"


                    if (port.id == current_destination_port_id) {
                        cb.checked = true
                    }

                    cb.onchange = (ev) => {
                        update_port_to_selection(port.id)
                    }

                    span.appendChild(cb)
                    lbl.setAttribute("for", cb.id)
                    span.appendChild(lbl)
                    container.appendChild(span)

                })
            }

        }

    }, 300)

}


document.addEventListener("DOMContentLoaded", () => {
    document.getElementById("port-from").addEventListener("input", populate_search_port_from)
    document.getElementById("port-to").addEventListener("input", populate_search_port_to)

})
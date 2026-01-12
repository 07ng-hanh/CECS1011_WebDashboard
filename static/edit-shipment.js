let port_from_debounce_timer = undefined
let current_departure_port_id = undefined
let current_destination_port_id = undefined
let scheduled_departure_timestamp = undefined
let port_to_debounce_timer = undefined
let produce_search_debounce_timer = undefined
let current_produce_id = undefined
let export_quantity = undefined

function date2string(date = new Date()) {
    return `${date.getFullYear()}-${(date.getMonth()+1).toString().padStart(2, '0')}-${(date.getDate()).toString().padStart(2, '0')} ${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}`
}

async function create_new_shipment(){
    if (current_departure_port_id === undefined) {
        alert("Departure port missing.")
        return
    }

    if (current_destination_port_id === undefined) {
        alert("Destination port missing.")
        return
    }

    if (scheduled_departure_timestamp === undefined) {
        alert("Scheduled departure time missing.")
        return
    }

    if (current_produce_id === undefined) {
        alert("Export produce missing.")
        return
    }

    if (export_quantity === undefined || export_quantity <= 0 || export_quantity % 1 !== 0) {
        alert("Quantity must be a positive whole number.")
        return
    }

    // push to server
    const r = await axios.post("/api/shipments/add-shipment", {
        departure_port_id: current_departure_port_id,
        destination_port_id: current_destination_port_id,
        planned_departure_day_utc_int:  scheduled_departure_timestamp,
        produce_id: current_produce_id,
        produce_qty: export_quantity
    })

    if (r.status === 200) {
        alert("Upload Complete")
        window.location.href = 'orders.html'
    } else {
        alert("Cannot upload new shipment: Error " + r.status)
        return
    }

    return


}

async function update_eta() {
    if (current_destination_port_id && current_departure_port_id && scheduled_departure_timestamp) {
        const r = await axios.get("/api/shipments/estimate-eta", {
            params: {
                port_id_from: current_departure_port_id,
                port_id_to: current_destination_port_id
            }
        })

        if (r.status === 200) {
            console.log(r.data)
            document.getElementById("eta-arrival-date").innerText = date2string(new Date(parseFloat(r.data) + scheduled_departure_timestamp))
            document.getElementById("eta-duration").innerText = Math.ceil(r.data / 86400000 ).toString()
        }
    }

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

    port_from_debounce_timer = setTimeout(async () => {
        const query = document.getElementById("port-from").value
        const container = document.getElementById("departure-port-selector")

        container.innerHTML = "<i>Type at least 3 characters to search for ports.</i>"

        if (query.length >= 3) {
            container.innerHTML = ""
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

    }, 150)

}

async function populate_search_port_to(ev) {
    if (port_to_debounce_timer) {
        clearTimeout(port_to_debounce_timer)
        port_to_debounce_timer = undefined
    }

    port_to_debounce_timer = setTimeout(async () => {
        const query = document.getElementById("port-to").value
        const container = document.getElementById("dest-port-selector")

        container.innerHTML = "<i>Type at least 3 characters to search for ports.</i>"


        if (query.length >= 3) {
            container.innerHTML = ""

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

    }, 150)

}

// implement produce search

async function populate_produce_search(ev) {

    if (produce_search_debounce_timer) {
        clearTimeout((produce_search_debounce_timer))
        produce_search_debounce_timer = undefined
    }

    produce_search_debounce_timer = setTimeout(async () => {
        const container = document.getElementById("produce-selector")

        if (document.getElementById("produce-name").value.length < 3) {
            container.innerHTML = "<i>Type at least 3 characters to search for produces.</i>"
            return
        }

        let r = await axios.get("/api/produce/list-all-produces-simple", {
            params: {q: document.getElementById("produce-name").value}
        })
        container.innerHTML = ""
        if (r.status === 200) {
            r.data.forEach((v) => {
                const span = document.createElement("div")
                span.className = "port-selector-container"
                const cb = document.createElement("input")
                cb.id = "cb3_" + v[0]
                const lbl = document.createElement("label")
                lbl.innerText = v[1]
                cb.type = "radio"
                cb.name = "cb-produce-name"
                cb.style.padding = "10px"
                lbl.style.padding = "10px"

                lbl.className = "form-check-label"

                if (current_produce_id === v[0]) {
                    cb.checked = true
                }

                cb.onchange=(ev) => {
                    if (ev.target.checked) {
                        current_produce_id = v[0]
                    }
                }

                span.appendChild(cb)
                lbl.setAttribute("for", cb.id)
                span.appendChild(lbl)
                container.appendChild(span)


            })
        }

    }, 150)

}

document.addEventListener("DOMContentLoaded", () => {
    let current_date = new Date()

    document.getElementById("dest-port-selector").innerHTML = "<i>Type at least 3 characters to search for ports</i>"
    document.getElementById("departure-port-selector").innerHTML = "<i>Type at least 3 characters to search for ports</i>"
    document.getElementById("produce-selector").innerHTML = "<i>Type at least 3 characters to search for produces</i>"
    document.getElementById("produce-qty").addEventListener("input", () => {export_quantity = parseInt(document.getElementById("produce-qty").value)})
    document.getElementById("produce-name").addEventListener("input", populate_produce_search)
    document.getElementById("port-from").addEventListener("input", populate_search_port_from)
    document.getElementById("port-to").addEventListener("input", populate_search_port_to)
    document.getElementById("form-control-hidden").setAttribute("min", `${current_date.getFullYear()}-${(current_date.getMonth()+1).toString().padStart(2, '0')}-${current_date.getDate().toString().padStart(2, '0')}T${current_date.getHours()}:${current_date.getMinutes()}`)
    document.getElementById("form-control-hidden").addEventListener("input", async() => {
        console.log(document.getElementById("form-control-hidden").value)
        const date_string = document.getElementById("form-control-hidden").value
        const date = date_string.split('T')[0]
        const time = date_string.split('T')[1]
        document.getElementById("scheduled-departure-date").value = `${date} ${time}`
        scheduled_departure_timestamp = new Date(date_string).getTime()
        await update_eta()
    })

    document.getElementById("scheduled-departure-date").addEventListener("input", async () => {
        let date_string = document.getElementById("scheduled-departure-date").value

        scheduled_departure_timestamp = new Date(date_string.replace(' ', 'T')).getTime()

        await update_eta()
    })

})